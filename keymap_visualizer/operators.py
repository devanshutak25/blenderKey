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
)


class WM_OT_keymap_viz_modal(bpy.types.Operator):
    bl_idname = "wm.keymap_viz_modal"
    bl_label = "Keymap Visualizer Modal"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        self._target_window = context.window
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

        # Force redraws while layout hasn't been computed yet.
        # This is critical: _handle_idle consumes MOUSEMOVE with RUNNING_MODAL,
        # so the tag_redraw before PASS_THROUGH would never fire during normal
        # interaction, creating a deadlock if the initial layout failed.
        if not state._key_rects:
            try:
                if state._target_area is not None:
                    state._target_area.tag_redraw()
            except ReferenceError:
                pass

        # Handle WINDOW_DEACTIVATE (Phase 7 hardening)
        if event.type == 'WINDOW_DEACTIVATE':
            # Verify window still exists
            try:
                _ = self._target_window.screen
            except ReferenceError:
                self._cleanup(context)
                return {'CANCELLED'}
            return {'PASS_THROUGH'}

        # Search mode takes priority when active (Phase 7)
        if state._search_active and state._modal_state == 'IDLE':
            result = _handle_search(context, event)
            if result is not None:
                return result

        # State machine dispatch (Phase 5)
        if state._modal_state == 'MENU_OPEN':
            return _handle_menu_open(context, event)
        elif state._modal_state == 'CAPTURE':
            return _handle_capture(context, event)
        elif state._modal_state == 'CONFLICT':
            return _handle_conflict(context, event)

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
        state._draw_handle = None
        state._target_area = None
        state._hovered_key_index = -1
        state._selected_key_index = -1
        state._key_rects = []
        state._cached_region_size = (0, 0)
        state._modifier_rects = []
        state._active_modifiers = {'ctrl': False, 'shift': False, 'alt': False, 'oskey': False}
        state._cached_bindings = []
        state._bindings_key = None
        state._modal_state = 'IDLE'
        state._menu_context.clear()
        state._conflict_data['conflicts'] = []
        state._conflict_button_rects.clear()
        state._conflict_hovered_button = -1
        state._gpu_menu_items.clear()
        state._gpu_menu_hovered = -1
        state._export_button_rect = None
        state._export_hovered = False
        state._search_text = ''
        state._search_active = False
        state._search_matching_keys = set()
        state._batch_dirty = True
        state._hover_transition = 0.0
        state._hover_transition_target = -1
        state._last_frame_time = 0.0
        state._launch_window = None
        state._set_running(False)

        # Redraw any remaining text-editor areas to clear stale overlay
        try:
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'TEXT_EDITOR':
                        area.tag_redraw()
        except Exception:
            pass


def _deferred_start_modal():
    """Module-level timer callback to invoke the modal in the new window.

    Must be module-level (not a bound method on the operator) because Blender
    frees operator StructRNA after execute() returns {'FINISHED'}.
    """
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

    # Re-fetch area from window (the original reference may be stale
    # after the area type change from the default to TEXT_EDITOR)
    area = window.screen.areas[0]

    # Retry if area type hasn't changed yet (Blender may need more frames)
    if area.type != 'TEXT_EDITOR':
        state._launch_retry_count += 1
        if state._launch_retry_count < 10:
            print(f"[Keymap Visualizer] Timer: area type is '{area.type}', "
                  f"retry {state._launch_retry_count}/10")
            return 0.1  # Reschedule
        print("[Keymap Visualizer] Timer: area type never became TEXT_EDITOR, aborting")
        state._set_running(False)
        state._launch_window = None
        return None

    # Find a region to use as override
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

    # If region not yet laid out, retry
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
    return None  # One-shot, don't reschedule


class WM_OT_keymap_viz_launch(bpy.types.Operator):
    bl_idname = "wm.keymap_viz_launch"
    bl_label = "Open Keymap Visualizer"
    bl_description = "Open a new window with the keymap visualizer overlay"

    def execute(self, context):
        if state._visualizer_running:
            self.report({'WARNING'}, "Keymap Visualizer is already running")
            return {'CANCELLED'}

        state._set_running(True)

        # Snapshot existing windows so we can identify the new one
        existing_windows = set(context.window_manager.windows[:])

        # Open a new window — try multiple approaches
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

        # Find the new window
        new_window = None
        for w in context.window_manager.windows:
            if w not in existing_windows:
                new_window = w
                break

        if new_window is None:
            state._set_running(False)
            self.report({'ERROR'}, "Failed to find new window")
            return {'CANCELLED'}

        # Set the first area to TEXT_EDITOR
        num_areas = len(new_window.screen.areas)
        print(f"[Keymap Visualizer] New window has {num_areas} area(s), "
              f"type='{new_window.screen.areas[0].type}'")
        new_window.screen.areas[0].type = 'TEXT_EDITOR'

        # Store in module-level state (NOT on self — Blender frees the
        # operator StructRNA after execute returns FINISHED)
        state._launch_window = new_window
        state._launch_retry_count = 0

        # Use a one-shot timer to invoke the modal after the window is set up
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
