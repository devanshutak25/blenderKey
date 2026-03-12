"""
Keymap Visualizer – Blender operators and header draw function
"""

import bpy
from . import state
from .layout import _compute_keyboard_layout
from .drawing import _draw_callback
from .handlers import (
    _handle_idle, _handle_menu_open, _handle_capture,
    _handle_conflict, _handle_search, _handle_filter_dropdown,
    _handle_shortcut_search, _handle_preset_dropdown,
    _handle_preset_name_input,
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
        elif state._modal_state == 'FILTER_DROPDOWN':
            return _handle_filter_dropdown(context, event)
        elif state._modal_state == 'PRESET_DROPDOWN':
            return _handle_preset_dropdown(context, event)

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
        state._cached_all_bindings = ([], 0)
        state._all_bindings_key = None
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
        # Feature 1: Close button cleanup
        state._close_button_rect = None
        state._close_hovered = False
        state._should_close = False
        # Feature 2: Resize cleanup
        state._user_scale = 1.0
        state._resize_handle_rect = None
        state._resize_hovered = False
        state._resize_dragging = False
        # Feature 3: Bound keys cleanup
        state._bound_keys_cache = set()
        state._bound_keys_dirty = True
        # Feature 4: Filter cleanup
        state._filter_space_type = 'ALL'
        state._filter_mode = 'ALL'
        state._filter_editor_btn_rect = None
        state._filter_mode_btn_rect = None
        state._filter_editor_hovered = False
        state._filter_mode_hovered = False
        state._filter_dropdown_open = None
        state._filter_dropdown_rects = []
        state._filter_dropdown_hovered = -1
        # v0.9 Feature 1: Key labels cleanup
        state._key_labels_cache = {}
        state._key_labels_dirty = True
        # v0.9 Feature 2: Physical modifiers cleanup
        state._physical_modifiers = {'ctrl': False, 'shift': False, 'alt': False, 'oskey': False}
        state._modifier_source = 'TOGGLE'
        # v0.9 Feature 3: Category colors cleanup
        state._key_categories_cache = {}
        state._key_categories_dirty = True
        # v0.9 Feature 4: Undo/redo cleanup
        state._undo_stack.clear()
        state._redo_stack.clear()
        # v0.9 Feature 5: Shortcut search cleanup
        state._shortcut_search_active = False
        # v0.9 Feature 6: Presets cleanup
        state._presets_list = []
        state._active_preset_name = ""
        state._presets_btn_rect = None
        state._presets_hovered = False
        state._preset_dropdown_open = False
        state._preset_dropdown_rects = []
        state._preset_dropdown_hovered = -1
        state._preset_name_input_active = False
        state._preset_name_text = ""

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
