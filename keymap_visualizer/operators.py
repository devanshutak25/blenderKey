"""
Keymap Visualizer – Blender operators and header draw function
"""

import logging

import bpy
from . import state

_log = logging.getLogger("keymap_visualizer.operators")
from .layout import _compute_keyboard_layout
from .drawing import _draw_callback
from .handlers import dispatch as _dispatch_event


class WM_OT_keymap_viz_modal(bpy.types.Operator):
    bl_idname = "wm.keymap_viz_modal"
    bl_label = "Keymap Visualizer Modal"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        self._target_window = context.window
        state._target_window = context.window
        state._target_area = context.area

        # Compute initial layout
        region_found = False
        for r in context.area.regions:
            if r.type == 'WINDOW':
                _log.debug("invoke: region %dx%d", r.width, r.height)
                _compute_keyboard_layout(r.width, r.height)
                region_found = True
                break
        if not region_found:
            _log.debug("invoke: no WINDOW region found")

        # Register draw handler on the SpaceTextEditor
        state._draw_handle = bpy.types.SpaceTextEditor.draw_handler_add(
            _draw_callback, (), 'WINDOW', 'POST_PIXEL'
        )

        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        _log.debug("invoke: modal started, key_rects=%d", len(state._key_rects))

        # Register watchdog timer to detect window close
        bpy.app.timers.register(_watchdog_timer, first_interval=0.5, persistent=True)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        # Window-close guard
        try:
            if self._target_window not in context.window_manager.windows[:]:
                self._cleanup(context)
                return {'CANCELLED'}
        except ReferenceError:
            _log.debug("Stale reference detected, cleaning up")
            self._cleanup(context)
            return {'CANCELLED'}

        # Auto-close if target area is no longer a TEXT_EDITOR
        try:
            if state._target_area is not None and state._target_area.type != 'TEXT_EDITOR':
                self._cleanup(context)
                return {'CANCELLED'}
        except ReferenceError:
            _log.debug("Stale reference detected, cleaning up")
            self._cleanup(context)
            return {'CANCELLED'}

        # Feature 1: Close button signal
        if state._should_close:
            self._cleanup(context)
            try:
                with context.temp_override(window=self._target_window):
                    bpy.ops.wm.window_close()
            except Exception:
                _log.debug("Window close failed", exc_info=True)
            return {'CANCELLED'}

        # Force redraws while layout hasn't been computed yet.
        if not state._key_rects:
            try:
                if state._target_area is not None:
                    state._target_area.tag_redraw()
            except ReferenceError:
                _log.debug("Stale reference detected, cleaning up")

        # Handle WINDOW_DEACTIVATE (Phase 7 hardening)
        if event.type == 'WINDOW_DEACTIVATE':
            try:
                _ = self._target_window.screen
            except ReferenceError:
                _log.debug("Stale reference detected, cleaning up")
                self._cleanup(context)
                return {'CANCELLED'}
            return {'PASS_THROUGH'}

        # Dispatch through state machine (handlers.dispatch)
        result = _dispatch_event(context, event)
        if result is not None:
            return result

        # ESC to close (only in IDLE and not searching)
        if event.type == 'ESC' and event.value == 'PRESS' and not state._search_active:
            self._cleanup(context)
            try:
                with context.temp_override(window=self._target_window):
                    bpy.ops.wm.window_close()
            except Exception:
                _log.debug("Window close failed", exc_info=True)
            return {'CANCELLED'}

        # Pass through everything else so the window stays responsive
        return {'PASS_THROUGH'}

    def _cleanup(self, context):
        if state._draw_handle is None:
            return  # Already cleaned up (idempotent)

        try:
            bpy.types.SpaceTextEditor.draw_handler_remove(state._draw_handle, 'WINDOW')
        except Exception:
            _log.debug("Draw handler already removed", exc_info=True)
        state._reset_all_state()
        from .icons import cleanup_icons
        cleanup_icons()
        state._set_running(False)

        # Redraw any remaining text-editor areas to clear stale overlay
        try:
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'TEXT_EDITOR':
                        area.tag_redraw()
        except Exception:
            _log.debug("Redraw cleanup failed", exc_info=True)


def _force_cleanup():
    """Force cleanup when the visualizer window is closed externally."""
    _log.debug("Watchdog: window closed, forcing cleanup")
    if state._draw_handle is not None:
        try:
            bpy.types.SpaceTextEditor.draw_handler_remove(state._draw_handle, 'WINDOW')
        except Exception:
            _log.debug("Draw handler already removed", exc_info=True)
    state._reset_all_state()
    try:
        from .icons import cleanup_icons
        cleanup_icons()
    except Exception:
        _log.debug("Icon cleanup failed", exc_info=True)
    state._set_running(False)
    # Redraw text editors to clear stale overlay
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'TEXT_EDITOR':
                    area.tag_redraw()
    except Exception:
        _log.debug("Redraw cleanup failed", exc_info=True)


def _watchdog_timer():
    """Periodic check: if the visualizer window was closed, force cleanup."""
    if not state._visualizer_running:
        return None  # Stop timer
    try:
        wm = bpy.context.window_manager
        if state._target_window not in wm.windows[:]:
            _force_cleanup()
            return None
    except Exception:
        _log.debug("Watchdog check failed", exc_info=True)
        _force_cleanup()
        return None
    return 0.5  # Check again in 0.5s


def _deferred_start_modal():
    """Module-level timer callback to invoke the modal in the new window."""
    window = state._launch_window
    if window is None:
        state._set_running(False)
        return None

    try:
        wm = bpy.context.window_manager
    except Exception as e:
        _log.warning("Timer: context error: %s", e, exc_info=True)
        state._set_running(False)
        state._launch_window = None
        return None

    # Verify window still alive
    try:
        if window not in wm.windows[:]:
            _log.debug("Timer: window gone, aborting")
            state._set_running(False)
            state._launch_window = None
            return None
    except ReferenceError:
        _log.debug("Stale reference detected, cleaning up")
        state._set_running(False)
        state._launch_window = None
        return None

    area = window.screen.areas[0]

    if area.type != 'TEXT_EDITOR':
        state._launch_retry_count += 1
        if state._launch_retry_count < 10:
            _log.debug("Timer: area type is '%s', retry %d/10",
                        area.type, state._launch_retry_count)
            return 0.1
        _log.debug("Timer: area type never became TEXT_EDITOR, aborting")
        state._set_running(False)
        state._launch_window = None
        return None

    # Hide header and footer for clean visualizer display
    space = area.spaces.active
    if space is not None:
        if hasattr(space, 'show_region_header'):
            space.show_region_header = False
        if hasattr(space, 'show_region_footer'):
            space.show_region_footer = False

    region = None
    for r in area.regions:
        if r.type == 'WINDOW':
            region = r
            break
    if region is None:
        state._launch_retry_count += 1
        if state._launch_retry_count < 10:
            _log.debug("Timer: no WINDOW region, retry %d/10",
                        state._launch_retry_count)
            return 0.1
        _log.debug("Timer: no WINDOW region found, aborting")
        state._set_running(False)
        state._launch_window = None
        return None

    if region.width == 0 or region.height == 0:
        state._launch_retry_count += 1
        if state._launch_retry_count < 10:
            _log.debug("Timer: region %dx%d, retry %d/10",
                        region.width, region.height, state._launch_retry_count)
            return 0.1
        _log.debug("Timer: region never got valid size, aborting")
        state._set_running(False)
        state._launch_window = None
        return None

    _log.debug("Timer: invoking modal (area=%s, region=%dx%d)",
               area.type, region.width, region.height)

    try:
        with bpy.context.temp_override(window=window, area=area, region=region):
            result = bpy.ops.wm.keymap_viz_modal('INVOKE_DEFAULT')
        _log.debug("Timer: modal invoke returned %s", result)
        if result != {'RUNNING_MODAL'}:
            _log.debug("Timer: modal did not start, aborting")
            state._set_running(False)
    except Exception as e:
        _log.warning("Timer: failed to start modal: %s", e, exc_info=True)
        state._set_running(False)

    state._launch_window = None
    return None


class WM_OT_keymap_viz_launch(bpy.types.Operator):
    bl_idname = "wm.keymap_viz_launch"
    bl_label = "Open Keymap Visualizer"
    bl_description = "Open a new window with the keymap visualizer overlay"

    def execute(self, context):
        if state._visualizer_running:
            self.report({'WARNING'}, "Keymap Visualizer is already running")
            return {'CANCELLED'}

        state._set_running(True)

        existing_windows = set(context.window_manager.windows[:])

        win_created = False
        for op_name in ('window_new', 'window_duplicate'):
            if win_created:
                break
            op_func = getattr(bpy.ops.wm, op_name, None)
            if op_func is None:
                _log.debug("wm.%s not available", op_name)
                continue
            try:
                result = op_func()
                _log.debug("wm.%s() -> %s", op_name, result)
                if 'FINISHED' in result:
                    win_created = True
            except Exception as e:
                _log.warning("wm.%s() exception: %s", op_name, e, exc_info=True)

        if not win_created:
            state._set_running(False)
            self.report({'ERROR'}, "Failed to create new window")
            return {'CANCELLED'}

        new_window = None
        for w in context.window_manager.windows:
            if w not in existing_windows:
                new_window = w
                break

        if new_window is None:
            state._set_running(False)
            self.report({'ERROR'}, "Failed to find new window")
            return {'CANCELLED'}

        num_areas = len(new_window.screen.areas)
        _log.debug("New window has %d area(s), type='%s'",
                   num_areas, new_window.screen.areas[0].type)
        new_window.screen.areas[0].type = 'TEXT_EDITOR'

        state._launch_window = new_window
        state._launch_retry_count = 0

        bpy.app.timers.register(_deferred_start_modal, first_interval=0.15)

        return {'FINISHED'}


def _draw_header_button(self, context):
    layout = self.layout
    layout.separator()
    row = layout.row(align=True)
    if state._visualizer_running:
        row.enabled = False
        row.operator("wm.keymap_viz_launch", text="Keymap Viz (Running)")
    else:
        row.operator("wm.keymap_viz_launch", text="Keymap Viz")
