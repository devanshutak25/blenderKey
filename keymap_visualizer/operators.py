"""
Keymap Visualizer – Blender operators and header draw function
"""

import bpy
from . import state
from .layout import _compute_keyboard_layout
from .drawing import _draw_callback
from .handlers import (
    _handle_idle, _handle_menu_open, _handle_capture,
    _handle_conflict, _handle_search,
    _handle_shortcut_search, _handle_preset_dropdown,
    _handle_preset_name_input,
    _handle_op_flyout, _handle_operator_search,
)


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
                print(f"[Keymap Visualizer] invoke: region {r.width}x{r.height}")
                _compute_keyboard_layout(r.width, r.height)
                region_found = True
                break
        if not region_found:
            print("[Keymap Visualizer] invoke: no WINDOW region found")

        # Register draw handler on the SpaceTextEditor
        state._draw_handle = bpy.types.SpaceTextEditor.draw_handler_add(
            _draw_callback, (), 'WINDOW', 'POST_PIXEL'
        )

        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        print(f"[Keymap Visualizer] invoke: modal started, key_rects={len(state._key_rects)}")

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
            self._cleanup(context)
            return {'CANCELLED'}

        # Auto-close if target area is no longer a TEXT_EDITOR
        try:
            if state._target_area is not None and state._target_area.type != 'TEXT_EDITOR':
                self._cleanup(context)
                return {'CANCELLED'}
        except ReferenceError:
            self._cleanup(context)
            return {'CANCELLED'}

        # Feature 1: Close button signal
        if state._should_close:
            self._cleanup(context)
            try:
                with context.temp_override(window=self._target_window):
                    bpy.ops.wm.window_close()
            except Exception:
                pass
            return {'CANCELLED'}

        # Force redraws while layout hasn't been computed yet.
        if not state._key_rects:
            try:
                if state._target_area is not None:
                    state._target_area.tag_redraw()
            except ReferenceError:
                pass

        # Handle WINDOW_DEACTIVATE (Phase 7 hardening)
        if event.type == 'WINDOW_DEACTIVATE':
            try:
                _ = self._target_window.screen
            except ReferenceError:
                self._cleanup(context)
                return {'CANCELLED'}
            return {'PASS_THROUGH'}

        # v0.9 Feature 6: Preset name input takes priority
        if state._preset_name_input_active and state._modal_state == 'IDLE':
            result = _handle_preset_name_input(context, event)
            if result is not None:
                return result

        # v0.9 Feature 5: Shortcut search takes priority
        if state._shortcut_search_active and state._modal_state == 'IDLE':
            result = _handle_shortcut_search(context, event)
            if result is not None:
                return result

        # Operator list search takes priority when active
        if state._operator_list_search_active and state._modal_state == 'IDLE':
            result = _handle_operator_search(context, event)
            if result is not None:
                return result

        # Search mode takes priority when active (Phase 7)
        if state._search_active and state._modal_state == 'IDLE':
            result = _handle_search(context, event)
            if result is not None:
                return result

        # State machine dispatch (Phase 5 + Feature 4 + v0.9 Feature 6)
        if state._modal_state == 'MENU_OPEN':
            return _handle_menu_open(context, event)
        elif state._modal_state == 'CAPTURE':
            return _handle_capture(context, event)
        elif state._modal_state == 'CONFLICT':
            return _handle_conflict(context, event)
        elif state._modal_state == 'PRESET_DROPDOWN':
            return _handle_preset_dropdown(context, event)
        elif state._modal_state == 'OP_FLYOUT':
            return _handle_op_flyout(context, event)

        # IDLE state
        result = _handle_idle(context, event)
        if result is not None:
            return result

        # ESC to close (only in IDLE and not searching)
        if event.type == 'ESC' and event.value == 'PRESS' and not state._search_active:
            self._cleanup(context)
            try:
                with context.temp_override(window=self._target_window):
                    bpy.ops.wm.window_close()
            except Exception:
                pass
            return {'CANCELLED'}

        # Pass through everything else so the window stays responsive
        return {'PASS_THROUGH'}

    def _cleanup(self, context):
        if state._draw_handle is None:
            return  # Already cleaned up (idempotent)

        try:
            bpy.types.SpaceTextEditor.draw_handler_remove(state._draw_handle, 'WINDOW')
        except Exception:
            pass
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
            pass


def _force_cleanup():
    """Force cleanup when the visualizer window is closed externally."""
    print("[Keymap Visualizer] Watchdog: window closed, forcing cleanup")
    if state._draw_handle is not None:
        try:
            bpy.types.SpaceTextEditor.draw_handler_remove(state._draw_handle, 'WINDOW')
        except Exception:
            pass
    state._reset_all_state()
    try:
        from .icons import cleanup_icons
        cleanup_icons()
    except Exception:
        pass
    state._set_running(False)
    # Redraw text editors to clear stale overlay
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'TEXT_EDITOR':
                    area.tag_redraw()
    except Exception:
        pass


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
        print(f"[Keymap Visualizer] Timer: context error: {e}")
        state._set_running(False)
        state._launch_window = None
        return None

    # Verify window still alive
    try:
        if window not in wm.windows[:]:
            print("[Keymap Visualizer] Timer: window gone, aborting")
            state._set_running(False)
            state._launch_window = None
            return None
    except ReferenceError:
        print("[Keymap Visualizer] Timer: window reference stale, aborting")
        state._set_running(False)
        state._launch_window = None
        return None

    area = window.screen.areas[0]

    if area.type != 'TEXT_EDITOR':
        state._launch_retry_count += 1
        if state._launch_retry_count < 10:
            print(f"[Keymap Visualizer] Timer: area type is '{area.type}', "
                  f"retry {state._launch_retry_count}/10")
            return 0.1
        print("[Keymap Visualizer] Timer: area type never became TEXT_EDITOR, aborting")
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
            print(f"[Keymap Visualizer] Timer: no WINDOW region, "
                  f"retry {state._launch_retry_count}/10")
            return 0.1
        print("[Keymap Visualizer] Timer: no WINDOW region found, aborting")
        state._set_running(False)
        state._launch_window = None
        return None

    if region.width == 0 or region.height == 0:
        state._launch_retry_count += 1
        if state._launch_retry_count < 10:
            print(f"[Keymap Visualizer] Timer: region {region.width}x{region.height}, "
                  f"retry {state._launch_retry_count}/10")
            return 0.1
        print("[Keymap Visualizer] Timer: region never got valid size, aborting")
        state._set_running(False)
        state._launch_window = None
        return None

    print(f"[Keymap Visualizer] Timer: invoking modal "
          f"(area={area.type}, region={region.width}x{region.height})")

    try:
        with bpy.context.temp_override(window=window, area=area, region=region):
            result = bpy.ops.wm.keymap_viz_modal('INVOKE_DEFAULT')
        print(f"[Keymap Visualizer] Timer: modal invoke returned {result}")
        if result != {'RUNNING_MODAL'}:
            print("[Keymap Visualizer] Timer: modal did not start, aborting")
            state._set_running(False)
    except Exception as e:
        print(f"[Keymap Visualizer] Timer: failed to start modal: {e}")
        import traceback
        traceback.print_exc()
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
                print(f"[Keymap Visualizer] wm.{op_name} not available")
                continue
            try:
                result = op_func()
                print(f"[Keymap Visualizer] wm.{op_name}() -> {result}")
                if 'FINISHED' in result:
                    win_created = True
            except Exception as e:
                print(f"[Keymap Visualizer] wm.{op_name}() exception: {e}")

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
        print(f"[Keymap Visualizer] New window has {num_areas} area(s), "
              f"type='{new_window.screen.areas[0].type}'")
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
