"""
Keymap Visualizer – Lightweight profiler for draw callback and event handling.

Usage:
    from .profiler import prof

    # In draw callback sections:
    with prof("draw_key_rects"):
        _draw_key_rectangles(ctx)

    # Toggle profiling on/off:
    prof.enabled = True   # start collecting
    prof.report()         # print stats to console
    prof.reset()          # clear all stats

    # Auto-report every N frames:
    prof.auto_report_interval = 120  # print every 120 frames (~ 2 sec at 60fps)
"""

import time


class _Profiler:
    __slots__ = (
        'enabled', '_timers', '_frame_count', '_frame_start',
        'auto_report_interval', '_last_report_frame',
    )

    def __init__(self):
        self.enabled = False
        self._timers = {}       # name -> [total_ns, count, min_ns, max_ns]
        self._frame_count = 0
        self._frame_start = 0
        self.auto_report_interval = 0  # 0 = no auto-report
        self._last_report_frame = 0

    def __call__(self, name):
        """Context manager: `with prof("section_name"): ...`"""
        return _TimerCtx(self, name) if self.enabled else _NullCtx

    def begin_frame(self):
        """Call at the start of _draw_callback."""
        if not self.enabled:
            return
        self._frame_start = time.perf_counter_ns()
        self._frame_count += 1

    def end_frame(self):
        """Call at the end of _draw_callback. Records total frame time."""
        if not self.enabled:
            return
        elapsed = time.perf_counter_ns() - self._frame_start
        self._record("TOTAL_FRAME", elapsed)

        if (self.auto_report_interval > 0
                and self._frame_count - self._last_report_frame >= self.auto_report_interval):
            self.report()
            self._last_report_frame = self._frame_count

    def _record(self, name, elapsed_ns):
        entry = self._timers.get(name)
        if entry is None:
            self._timers[name] = [elapsed_ns, 1, elapsed_ns, elapsed_ns]
        else:
            entry[0] += elapsed_ns
            entry[1] += 1
            if elapsed_ns < entry[2]:
                entry[2] = elapsed_ns
            if elapsed_ns > entry[3]:
                entry[3] = elapsed_ns

    def reset(self):
        self._timers.clear()
        self._frame_count = 0
        self._last_report_frame = 0

    def report(self):
        """Print profiling stats to stdout (Blender system console)."""
        if not self._timers:
            print("[Profiler] No data collected. Set prof.enabled = True first.")
            return

        print(f"\n{'='*72}")
        print(f"  Keymap Visualizer Profiler — {self._frame_count} frames")
        print(f"{'='*72}")
        print(f"  {'Section':<30s} {'Avg ms':>8s} {'Min ms':>8s} {'Max ms':>8s} {'Calls':>7s}")
        print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*8} {'-'*7}")

        # Sort: TOTAL_FRAME first, then by avg descending
        items = sorted(self._timers.items(),
                       key=lambda kv: (kv[0] != "TOTAL_FRAME", -(kv[1][0] / kv[1][1])))
        for name, (total_ns, count, min_ns, max_ns) in items:
            avg_ms = (total_ns / count) / 1_000_000
            min_ms = min_ns / 1_000_000
            max_ms = max_ns / 1_000_000
            print(f"  {name:<30s} {avg_ms:>8.3f} {min_ms:>8.3f} {max_ms:>8.3f} {count:>7d}")

        print(f"{'='*72}\n")


class _TimerCtx:
    __slots__ = ('_prof', '_name', '_start')

    def __init__(self, prof, name):
        self._prof = prof
        self._name = name

    def __enter__(self):
        self._start = time.perf_counter_ns()
        return self

    def __exit__(self, *_):
        self._prof._record(self._name, time.perf_counter_ns() - self._start)


class _NullCtxClass:
    """No-op context manager when profiling is disabled."""
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass

_NullCtx = _NullCtxClass()


# Singleton
prof = _Profiler()
