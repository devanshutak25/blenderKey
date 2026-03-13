"""
Keymap Visualizer – State machine event handlers
"""

import time
from . import state
from .hit_testing import (
    _hit_test_key, _hit_test_export,
    _hit_test_conflict_buttons, _hit_test_gpu_menu, _hit_test_flyout,
    _hit_test_close, _hit_test_resize,
    _hit_test_editor_list, _hit_test_mode_list,
    _hit_test_presets_button, _hit_test_preset_dropdown,
    _hit_test_info_panel_group,
)
from .keymap_data import (
    _get_bindings_for_key, _find_conflicts, _apply_rebind,
    _reset_kmi_to_default, _update_search_filter,
    _push_undo, _do_undo, _do_redo,
)
from .export import _do_export
from .drawing import _build_gpu_menu, _build_flyout, _build_preset_dropdown
from .constants import _CAPTURABLE_KEYS, MODIFIER_KEY_TO_DICT


def _tag_redraw():
    """Request a redraw of the target area if available."""
    if state._target_area is not None:
        state._target_area.tag_redraw()


def _dismiss_menu():
    """Clear GPU menu and flyout state and redraw."""
    state._gpu_menu_items.clear()
    state._gpu_menu_hovered = -1
    state._gpu_flyout_items.clear()
    state._gpu_flyout_hovered = -1
    state._flyout_target_index = -1
    state._batch_dirty = True
    _tag_redraw()


def _dismiss_conflict():
    """Clear conflict dialog state and redraw."""
    state._conflict_hovered_button = -1
    state._conflict_button_rects.clear()
    state._conflict_data['conflicts'] = []
    state._menu_context.clear()
    state._batch_dirty = True
    _tag_redraw()


def _dismiss_preset_dropdown():
    """Clear preset dropdown state and redraw."""
    state._preset_dropdown_open = False
    state._preset_dropdown_rects = []
    state._preset_dropdown_hovered = -1
    state._modal_state = 'IDLE'
    state._batch_dirty = True
    _tag_redraw()


def _toggle_filter_item(filter_set, value):
    """Toggle an item in a filter set with ALL-aware logic, then redraw."""
    if value == 'ALL':
        filter_set.clear()
        filter_set.add('ALL')
    elif value in filter_set:
        filter_set.discard(value)
        if not filter_set:
            filter_set.add('ALL')
    else:
        filter_set.discard('ALL')
        filter_set.add(value)
    state._invalidate_cache()
    _tag_redraw()


def _get_unit_px():
    """Compute current unit_px from cached region size and user scale."""
    rw, rh = state._cached_region_size
    if rw == 0 or rh == 0:
        return 40  # fallback
    unit_from_w = rw / 24
    unit_from_h = rh / 12
    return min(unit_from_w, unit_from_h) * state._user_scale


# ---------------------------------------------------------------------------
# v0.9 Feature 2: Physical modifier reactivity
# ---------------------------------------------------------------------------
def _update_physical_modifiers(event):
    """Update physical modifier state from event. Returns True if changed."""
    changed = False
    for attr, key in [('ctrl', 'ctrl'), ('shift', 'shift'), ('alt', 'alt'), ('oskey', 'oskey')]:
        val = getattr(event, attr, False)
        if val != state._physical_modifiers[key]:
            state._physical_modifiers[key] = val
            changed = True
    if changed:
        new_source = 'PHYSICAL' if any(state._physical_modifiers.values()) else 'TOGGLE'
        if new_source != state._modifier_source:
            state._modifier_source = new_source
        state._invalidate_cache()
        _tag_redraw()
    return changed


def _navigate_key(direction):
    """Move keyboard focus in the given direction ('UP','DOWN','LEFT','RIGHT').
    Updates state._nav_key_index. Returns True if moved."""
    if not state._key_row_map or not state._key_rects:
        return False
    current = state._nav_key_index
    if current < 0 or current >= len(state._key_rects):
        state._nav_key_index = 0
        return True
    kr = state._key_rects[current]
    center_x = kr.x + kr.w / 2

    current_row = -1
    current_col = -1
    for ri, row in enumerate(state._key_row_map):
        if current in row:
            current_row = ri
            current_col = row.index(current)
            break
    if current_row < 0:
        return False

    if direction == 'LEFT':
        row = state._key_row_map[current_row]
        if current_col > 0:
            state._nav_key_index = row[current_col - 1]
            return True
    elif direction == 'RIGHT':
        row = state._key_row_map[current_row]
        if current_col < len(row) - 1:
            state._nav_key_index = row[current_col + 1]
            return True
    elif direction == 'UP':
        if current_row < len(state._key_row_map) - 1:
            target_row = state._key_row_map[current_row + 1]
            best = min(target_row, key=lambda i: abs(state._key_rects[i].x + state._key_rects[i].w/2 - center_x))
            state._nav_key_index = best
            return True
    elif direction == 'DOWN':
        if current_row > 0:
            target_row = state._key_row_map[current_row - 1]
            best = min(target_row, key=lambda i: abs(state._key_rects[i].x + state._key_rects[i].w/2 - center_x))
            state._nav_key_index = best
            return True
    return False


def _handle_resize_drag(context, event):
    """Handle events during resize drag."""
    if event.type == 'MOUSEMOVE':
        dx = event.mouse_region_x - state._resize_drag_start_x
        # Scale change proportional to horizontal delta
        scale_delta = dx / 200.0
        new_scale = state._resize_drag_start_scale + scale_delta
        new_scale = max(0.5, min(3.0, new_scale))
        if new_scale != state._user_scale:
            state._user_scale = new_scale
            state._cached_region_size = (0, 0)  # Force layout recompute
            state._invalidate_cache()
            _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
        state._resize_dragging = False
        return {'RUNNING_MODAL'}

    if event.type == 'ESC' and event.value == 'PRESS':
        state._user_scale = state._resize_drag_start_scale
        state._resize_dragging = False
        state._cached_region_size = (0, 0)
        state._invalidate_cache()
        _tag_redraw()
        return {'RUNNING_MODAL'}

    return {'RUNNING_MODAL'}


def _handle_idle(context, event):
    """Handle events in IDLE state. Returns Blender modal return set."""
    # Feature 2: Resize dragging takes priority
    if state._resize_dragging:
        return _handle_resize_drag(context, event)

    # v0.9 Feature 2: Update physical modifiers on every event
    _update_physical_modifiers(event)

    # v0.9 Feature 4: Undo/redo (before other key handling)
    if event.type == 'Z' and event.value == 'PRESS' and event.ctrl and not event.shift:
        if _do_undo():
            state._invalidate_cache()
            _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'Z' and event.value == 'PRESS' and event.ctrl and event.shift:
        if _do_redo():
            state._invalidate_cache()
            _tag_redraw()
        return {'RUNNING_MODAL'}

    # v0.9 Feature 5: Shortcut search activation (Shift+/)
    if event.type == 'SLASH' and event.value == 'PRESS' and event.shift:
        state._shortcut_search_active = True
        _tag_redraw()
        return {'RUNNING_MODAL'}

    # Scroll drag handling (middle mouse)
    if state._filter_scroll_drag_target is not None:
        if event.type == 'MOUSEMOVE':
            dy = state._filter_scroll_drag_start_y - event.mouse_region_y
            new_scroll = state._filter_scroll_drag_start_offset + dy
            item_h = max(20, _get_unit_px() * 0.5)
            header_h = max(16, _get_unit_px() * 0.35)
            if state._filter_scroll_drag_target == 'EDITOR':
                total_h = len(state._filter_editor_list_rects) * item_h + header_h
                px, py, pw, ph = state._filter_editor_list_rect
                max_scroll = max(0, total_h - ph)
                state._filter_editor_scroll = max(0, min(max_scroll, new_scroll))
            elif state._filter_scroll_drag_target == 'INFO':
                state._info_panel_scroll = max(0, min(state._info_panel_max_scroll, new_scroll))
            else:
                total_h = len(state._filter_mode_list_rects) * item_h + header_h
                px, py, pw, ph = state._filter_mode_list_rect
                max_scroll = max(0, total_h - ph)
                state._filter_mode_scroll = max(0, min(max_scroll, new_scroll))
            _tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type == 'MIDDLEMOUSE' and event.value == 'RELEASE':
            state._filter_scroll_drag_target = None
            return {'RUNNING_MODAL'}

    # Mouse wheel scrolling for list panels
    if event.type in ('WHEELUPMOUSE', 'WHEELDOWNMOUSE'):
        mx, my = event.mouse_region_x, event.mouse_region_y
        item_h = max(20, _get_unit_px() * 0.5)
        header_h = max(16, _get_unit_px() * 0.35)
        scroll_step = item_h
        for panel_rect, item_rects, is_editor in [
            (state._filter_editor_list_rect, state._filter_editor_list_rects, True),
            (state._filter_mode_list_rect, state._filter_mode_list_rects, False),
        ]:
            if panel_rect is None:
                continue
            px, py, pw, ph = panel_rect
            if px <= mx <= px + pw and py <= my <= py + ph:
                total_h = len(item_rects) * item_h + header_h
                max_scroll = max(0, total_h - ph)
                delta = -scroll_step if event.type == 'WHEELUPMOUSE' else scroll_step
                if is_editor:
                    state._filter_editor_scroll = max(0, min(max_scroll, state._filter_editor_scroll + delta))
                else:
                    state._filter_mode_scroll = max(0, min(max_scroll, state._filter_mode_scroll + delta))
                _tag_redraw()
                return {'RUNNING_MODAL'}

        # Info panel scroll
        if state._info_panel_rect is not None:
            px, py, pw, ph = state._info_panel_rect
            if px <= mx <= px + pw and py <= my <= py + ph:
                info_line_h = max(10, int(_get_unit_px() * 0.28)) + 3
                delta = -info_line_h if event.type == 'WHEELUPMOUSE' else info_line_h
                state._info_panel_scroll = max(0, min(state._info_panel_max_scroll, state._info_panel_scroll + delta))
                _tag_redraw()
                return {'RUNNING_MODAL'}

    # Middle-click drag start for list panels
    if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
        mx, my = event.mouse_region_x, event.mouse_region_y
        for panel_rect, scroll_val, target_name in [
            (state._filter_editor_list_rect, state._filter_editor_scroll, 'EDITOR'),
            (state._filter_mode_list_rect, state._filter_mode_scroll, 'MODE'),
            (state._info_panel_rect, state._info_panel_scroll, 'INFO'),
        ]:
            if panel_rect is None:
                continue
            px, py, pw, ph = panel_rect
            if px <= mx <= px + pw and py <= my <= py + ph:
                state._filter_scroll_drag_target = target_name
                state._filter_scroll_drag_start_y = my
                state._filter_scroll_drag_start_offset = scroll_val
                return {'RUNNING_MODAL'}

    if event.type == 'MOUSEMOVE':
        mx, my = event.mouse_region_x, event.mouse_region_y
        new_hover = _hit_test_key(mx, my)
        new_export_hover = _hit_test_export(mx, my)
        new_close_hover = _hit_test_close(mx, my)
        new_resize_hover = _hit_test_resize(mx, my)
        new_presets_hover = _hit_test_presets_button(mx, my)

        changed = False
        if new_hover != state._hovered_key_index:
            state._hovered_key_index = new_hover
            state._batch_dirty = True
            changed = True
        if new_export_hover != state._export_hovered:
            state._export_hovered = new_export_hover
            changed = True
        if new_close_hover != state._close_hovered:
            state._close_hovered = new_close_hover
            changed = True
        if new_resize_hover != state._resize_hovered:
            state._resize_hovered = new_resize_hover
            changed = True
        # Editor/Mode list hover
        new_editor_hover = _hit_test_editor_list(mx, my)
        new_mode_hover = _hit_test_mode_list(mx, my)
        if new_editor_hover != state._filter_editor_hovered:
            state._filter_editor_hovered = new_editor_hover
            changed = True
        if new_mode_hover != state._filter_mode_hovered:
            state._filter_mode_hovered = new_mode_hover
            changed = True
        # Presets button hover
        if new_presets_hover != state._presets_hovered:
            state._presets_hovered = new_presets_hover
            changed = True

        # L4: Tooltip tracking
        tooltip = ""
        if new_export_hover:
            tooltip = "Export keymap to file (see Addon Preferences for path)"
        elif new_presets_hover:
            tooltip = "Save/load keymap presets"
        elif new_close_hover:
            tooltip = "Close visualizer (Esc)"
        if tooltip != state._tooltip_text:
            state._tooltip_text = tooltip
            state._tooltip_hover_start = time.monotonic()
            changed = True
        elif not tooltip:
            state._tooltip_text = ""

        if changed:
            _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
        mx, my = event.mouse_region_x, event.mouse_region_y

        # Feature 1: Check close button
        if _hit_test_close(mx, my):
            state._should_close = True
            return {'RUNNING_MODAL'}

        # Feature 2: Check resize handle
        if _hit_test_resize(mx, my):
            state._resize_dragging = True
            state._resize_drag_start_x = mx
            state._resize_drag_start_scale = state._user_scale
            return {'RUNNING_MODAL'}

        # Feature 4: Check editor list click
        editor_hit = _hit_test_editor_list(mx, my)
        if editor_hit >= 0:
            item = state._filter_editor_list_rects[editor_hit]
            _toggle_filter_item(state._filter_space_types, item[1])
            return {'RUNNING_MODAL'}

        # Check mode list click
        mode_hit = _hit_test_mode_list(mx, my)
        if mode_hit >= 0:
            item = state._filter_mode_list_rects[mode_hit]
            _toggle_filter_item(state._filter_modes, item[1])
            return {'RUNNING_MODAL'}

        # Check info panel group header click
        group_key = _hit_test_info_panel_group(mx, my)
        if group_key is not None:
            if group_key in state._info_panel_expanded_groups:
                state._info_panel_expanded_groups.discard(group_key)
            else:
                state._info_panel_expanded_groups.add(group_key)
            _tag_redraw()
            return {'RUNNING_MODAL'}

        # v0.9 Feature 6: Check presets button
        if _hit_test_presets_button(mx, my):
            region_w, region_h = state._cached_region_size
            _build_preset_dropdown(state._presets_btn_rect, region_w, region_h)
            state._preset_dropdown_open = True
            state._modal_state = 'PRESET_DROPDOWN'
            _tag_redraw()
            return {'RUNNING_MODAL'}

        # Check export button
        if _hit_test_export(mx, my):
            success, msg = _do_export()
            print(f"[Keymap Visualizer] {msg}")
            _tag_redraw()
            return {'RUNNING_MODAL'}

        # Check key hit
        key_hit = _hit_test_key(mx, my)
        if key_hit >= 0:
            kr = state._key_rects[key_hit]
            # Modifier keys toggle their modifier instead of selecting
            if kr.event_type in MODIFIER_KEY_TO_DICT:
                dict_key = MODIFIER_KEY_TO_DICT[kr.event_type]
                state._active_modifiers[dict_key] = not state._active_modifiers[dict_key]
                state._invalidate_cache()
                state._batch_dirty = True
                _tag_redraw()
                return {'RUNNING_MODAL'}
            # Normal key selection (toggle on re-click)
            if key_hit == state._selected_key_index:
                state._selected_key_index = -1
            else:
                state._selected_key_index = key_hit
            state._info_panel_scroll = 0  # Reset scroll on key change
            state._info_panel_expanded_groups.clear()
            state._batch_dirty = True
            _tag_redraw()
        return {'RUNNING_MODAL'}

    # Right-click: context menu (Feature 5: enhanced with all bindings)
    if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
        mx, my = event.mouse_region_x, event.mouse_region_y
        key_hit = _hit_test_key(mx, my)
        if key_hit >= 0:
            kr = state._key_rects[key_hit]
            if kr.event_type in MODIFIER_KEY_TO_DICT:
                return {'RUNNING_MODAL'}  # no context menu for modifier keys
            bindings = _get_bindings_for_key(kr.event_type, state._active_modifiers)
            if bindings:
                state._menu_context.clear()
                state._menu_context['target_key_index'] = key_hit
                state._menu_context['target_event_type'] = kr.event_type
                # Store all bindings for Feature 5
                state._menu_context['all_bindings'] = bindings
                # Keep first binding as default target for backward compat
                km_name, op_id, mod_str, kmi, is_active = bindings[0][:5]
                state._menu_context['target_kmi'] = kmi
                state._menu_context['target_km_name'] = km_name
                state._menu_context['pending_action'] = None

                # Get region dimensions for menu positioning
                region_w, region_h = state._cached_region_size
                _build_gpu_menu(mx, my, region_w, region_h, bindings=bindings)
                state._modal_state = 'MENU_OPEN'
                _tag_redraw()
            return {'RUNNING_MODAL'}

    # Search activation: / key or Ctrl+F (but not Shift+/ which is shortcut search)
    if event.type == 'SLASH' and event.value == 'PRESS' and not event.ctrl and not event.shift:
        state._search_active = True
        state._search_text = ''
        _update_search_filter()
        _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'F' and event.value == 'PRESS' and event.ctrl:
        state._search_active = True
        state._search_text = ''
        _update_search_filter()
        _tag_redraw()
        return {'RUNNING_MODAL'}

    # C2: Keyboard navigation — arrow keys
    if event.type in ('LEFT_ARROW', 'RIGHT_ARROW', 'UP_ARROW', 'DOWN_ARROW') and event.value == 'PRESS':
        if not event.ctrl and not event.shift and not event.alt:
            direction_map = {
                'LEFT_ARROW': 'LEFT', 'RIGHT_ARROW': 'RIGHT',
                'UP_ARROW': 'UP', 'DOWN_ARROW': 'DOWN',
            }
            if state._nav_focus == 'KEYS':
                if _navigate_key(direction_map[event.type]):
                    state._hovered_key_index = state._nav_key_index
                    state._batch_dirty = True
                    _tag_redraw()
                return {'RUNNING_MODAL'}
            elif state._nav_focus in ('EDITOR_LIST', 'MODE_LIST'):
                if event.type in ('UP_ARROW', 'DOWN_ARROW'):
                    delta = -1 if event.type == 'UP_ARROW' else 1
                    if state._nav_focus == 'EDITOR_LIST':
                        max_idx = len(state._filter_editor_list_rects) - 1
                        state._filter_editor_hovered = max(0, min(max_idx, state._filter_editor_hovered + delta))
                    else:
                        max_idx = len(state._filter_mode_list_rects) - 1
                        state._filter_mode_hovered = max(0, min(max_idx, state._filter_mode_hovered + delta))
                    _tag_redraw()
                return {'RUNNING_MODAL'}
            elif state._nav_focus == 'INFO_PANEL':
                if event.type in ('UP_ARROW', 'DOWN_ARROW'):
                    info_line_h = max(10, int(_get_unit_px() * 0.28)) + 3
                    delta = -info_line_h if event.type == 'UP_ARROW' else info_line_h
                    state._info_panel_scroll = max(0, min(state._info_panel_max_scroll, state._info_panel_scroll + delta))
                    _tag_redraw()
                return {'RUNNING_MODAL'}

    # C2: Tab to cycle panels
    if event.type == 'TAB' and event.value == 'PRESS' and not event.ctrl and not event.alt:
        panels = ['KEYS', 'EDITOR_LIST', 'MODE_LIST', 'INFO_PANEL']
        idx = panels.index(state._nav_focus) if state._nav_focus in panels else 0
        if event.shift:
            idx = (idx - 1) % len(panels)
        else:
            idx = (idx + 1) % len(panels)
        state._nav_focus = panels[idx]
        if state._nav_focus == 'KEYS':
            state._hovered_key_index = state._nav_key_index
        elif state._nav_focus == 'EDITOR_LIST':
            state._filter_editor_hovered = max(0, state._filter_editor_hovered)
        elif state._nav_focus == 'MODE_LIST':
            state._filter_mode_hovered = max(0, state._filter_mode_hovered)
        state._batch_dirty = True
        _tag_redraw()
        return {'RUNNING_MODAL'}

    # C2: Enter to select/toggle in focused panel
    if event.type == 'RET' and event.value == 'PRESS' and not event.ctrl:
        if state._nav_focus == 'KEYS':
            idx = state._nav_key_index
            if 0 <= idx < len(state._key_rects):
                kr = state._key_rects[idx]
                if kr.event_type in MODIFIER_KEY_TO_DICT:
                    dict_key = MODIFIER_KEY_TO_DICT[kr.event_type]
                    state._active_modifiers[dict_key] = not state._active_modifiers[dict_key]
                    state._invalidate_cache()
                elif idx == state._selected_key_index:
                    state._selected_key_index = -1
                else:
                    state._selected_key_index = idx
                state._info_panel_scroll = 0
                state._info_panel_expanded_groups.clear()
                state._batch_dirty = True
                _tag_redraw()
            return {'RUNNING_MODAL'}
        elif state._nav_focus == 'EDITOR_LIST':
            hi = state._filter_editor_hovered
            if 0 <= hi < len(state._filter_editor_list_rects):
                item = state._filter_editor_list_rects[hi]
                _toggle_filter_item(state._filter_space_types, item[1])
            return {'RUNNING_MODAL'}
        elif state._nav_focus == 'MODE_LIST':
            hi = state._filter_mode_hovered
            if 0 <= hi < len(state._filter_mode_list_rects):
                item = state._filter_mode_list_rects[hi]
                _toggle_filter_item(state._filter_modes, item[1])
            return {'RUNNING_MODAL'}

    return None  # Not handled


def _dispatch_flyout_action(action, binding_index):
    """Execute a flyout action for the given binding. Returns True if handled."""
    all_bindings = state._menu_context.get('all_bindings', [])
    if 0 <= binding_index < len(all_bindings):
        km_name, op_id, mod_str, kmi, is_active = all_bindings[binding_index][:5]
    else:
        kmi = state._menu_context.get('target_kmi')
        km_name = state._menu_context.get('target_km_name')

    if action == 'REBIND' and kmi:
        state._menu_context['target_kmi'] = kmi
        state._menu_context['target_km_name'] = km_name
        state._modal_state = 'CAPTURE'
        state._menu_context['pending_action'] = 'REBIND'
    elif action == 'UNBIND' and kmi:
        _push_undo([kmi])
        kmi.active = False
        state._invalidate_cache()
        state._modal_state = 'IDLE'
    elif action == 'RESET' and kmi and km_name:
        _push_undo([kmi])
        _reset_kmi_to_default(kmi, km_name)
        state._modal_state = 'IDLE'
    elif action == 'TOGGLE' and kmi:
        _push_undo([kmi])
        kmi.active = not kmi.active
        state._invalidate_cache()
        state._modal_state = 'IDLE'
    else:
        state._modal_state = 'IDLE'
    return True


def _handle_menu_open(context, event):
    """Handle events while GPU context menu is open (with flyout sub-menus)."""
    if event.type == 'MOUSEMOVE':
        mx, my = event.mouse_region_x, event.mouse_region_y
        changed = False

        # Hit-test flyout first (it's on top)
        flyout_hover = _hit_test_flyout(mx, my) if state._gpu_flyout_items else -1
        if flyout_hover != state._gpu_flyout_hovered:
            state._gpu_flyout_hovered = flyout_hover
            changed = True

        # Hit-test main menu
        menu_hover = _hit_test_gpu_menu(mx, my)
        if menu_hover != state._gpu_menu_hovered:
            state._gpu_menu_hovered = menu_hover
            changed = True

        # Flyout logic: hover-based with ~200ms delay
        if flyout_hover >= 0:
            # Mouse is on flyout — keep it open, don't change target
            pass
        elif menu_hover >= 0:
            if menu_hover != state._flyout_target_index:
                # Hovering a different main item — start timer for new flyout
                if state._flyout_hover_timer == 0.0 or menu_hover != getattr(state, '_flyout_pending_index', -1):
                    state._flyout_hover_timer = time.monotonic()
                    state._flyout_pending_index = menu_hover
                # Check if delay has passed
                if time.monotonic() - state._flyout_hover_timer >= 0.2:
                    state._flyout_target_index = menu_hover
                    _build_flyout(menu_hover)
                    changed = True
            # else: same target, keep flyout
        else:
            # Mouse not on menu or flyout — dismiss flyout
            if state._gpu_flyout_items:
                state._gpu_flyout_items.clear()
                state._gpu_flyout_hovered = -1
                state._flyout_target_index = -1
                state._flyout_hover_timer = 0.0
                changed = True

        if changed:
            _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
        mx, my = event.mouse_region_x, event.mouse_region_y

        # Hit-test flyout first (it's on top)
        flyout_hit = _hit_test_flyout(mx, my) if state._gpu_flyout_items else -1
        if flyout_hit >= 0:
            fitem = state._gpu_flyout_items[flyout_hit]
            flabel, faction, fx, fy, fw, fh, fbind_idx = fitem
            _dispatch_flyout_action(faction, fbind_idx)
            _dismiss_menu()
            return {'RUNNING_MODAL'}

        # Hit-test main menu — click = instant flyout open
        menu_hit = _hit_test_gpu_menu(mx, my)
        if menu_hit >= 0:
            state._flyout_target_index = menu_hit
            _build_flyout(menu_hit)
            _tag_redraw()
            return {'RUNNING_MODAL'}

        # Clicked outside — dismiss everything
        state._modal_state = 'IDLE'
        _dismiss_menu()
        return {'RUNNING_MODAL'}

    if event.type == 'ESC' and event.value == 'PRESS':
        state._modal_state = 'IDLE'
        _dismiss_menu()
        return {'RUNNING_MODAL'}

    if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
        state._modal_state = 'IDLE'
        _dismiss_menu()
        return {'RUNNING_MODAL'}

    return {'RUNNING_MODAL'}


def _handle_capture(context, event):
    """Handle events in CAPTURE state (waiting for key press)."""
    if event.value != 'PRESS':
        return {'RUNNING_MODAL'}

    if event.type == 'ESC':
        state._modal_state = 'IDLE'
        state._menu_context.clear()
        state._batch_dirty = True
        _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type in _CAPTURABLE_KEYS:
        new_type = event.type
        new_ctrl = event.ctrl
        new_shift = event.shift
        new_alt = event.alt
        new_oskey = event.oskey

        kmi = state._menu_context.get('target_kmi')
        km_name = state._menu_context.get('target_km_name')
        if kmi is None:
            state._modal_state = 'IDLE'
            return {'RUNNING_MODAL'}

        # Check for conflicts
        conflicts = _find_conflicts(new_type, new_ctrl, new_shift, new_alt, new_oskey,
                                    exclude_kmi=kmi)
        if not conflicts:
            # No conflicts — apply directly
            _push_undo([kmi])  # v0.9: undo support
            _apply_rebind(kmi, new_type, new_ctrl, new_shift, new_alt, new_oskey)
            state._modal_state = 'IDLE'
            state._menu_context.clear()
        else:
            # Conflicts found — enter CONFLICT state
            state._conflict_data['new_type'] = new_type
            state._conflict_data['new_ctrl'] = new_ctrl
            state._conflict_data['new_shift'] = new_shift
            state._conflict_data['new_alt'] = new_alt
            state._conflict_data['new_oskey'] = new_oskey
            state._conflict_data['source_kmi'] = kmi
            state._conflict_data['source_km_name'] = km_name
            state._conflict_data['conflicts'] = conflicts
            state._modal_state = 'CONFLICT'

        state._batch_dirty = True
        _tag_redraw()
        return {'RUNNING_MODAL'}

    # Ignore non-capturable keys silently
    return {'RUNNING_MODAL'}


def _handle_conflict(context, event):
    """Handle events in CONFLICT state."""
    if event.type == 'MOUSEMOVE':
        new_hover = _hit_test_conflict_buttons(event.mouse_region_x, event.mouse_region_y)
        if new_hover != state._conflict_hovered_button:
            state._conflict_hovered_button = new_hover
            _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
        mx, my = event.mouse_region_x, event.mouse_region_y
        btn_hit = _hit_test_conflict_buttons(mx, my)

        if btn_hit >= 0:
            action = state._conflict_button_rects[btn_hit][1]
            src_kmi = state._conflict_data.get('source_kmi')
            new_type = state._conflict_data.get('new_type')
            new_ctrl = state._conflict_data.get('new_ctrl', False)
            new_shift = state._conflict_data.get('new_shift', False)
            new_alt = state._conflict_data.get('new_alt', False)
            new_oskey = state._conflict_data.get('new_oskey', False)
            conflicts = state._conflict_data.get('conflicts', [])

            if action == 'SWAP' and src_kmi:
                # v0.9: undo support — snapshot all affected KMIs
                _push_undo([src_kmi] + [ckmi for _, ckmi in conflicts])

                # Save source's current binding
                old_type = src_kmi.type
                old_ctrl = src_kmi.ctrl
                old_shift = src_kmi.shift
                old_alt = src_kmi.alt
                old_oskey = src_kmi.oskey

                # Apply new binding to source
                _apply_rebind(src_kmi, new_type, new_ctrl, new_shift, new_alt, new_oskey)

                # Set conflicting KMIs to old binding
                for ckm_name, ckmi in conflicts:
                    _apply_rebind(ckmi, old_type, old_ctrl, old_shift, old_alt, old_oskey)

            elif action == 'OVERRIDE' and src_kmi:
                # v0.9: undo support
                _push_undo([src_kmi] + [ckmi for _, ckmi in conflicts])

                # Deactivate conflicting KMIs
                for ckm_name, ckmi in conflicts:
                    ckmi.active = False

                # Apply new binding to source
                _apply_rebind(src_kmi, new_type, new_ctrl, new_shift, new_alt, new_oskey)

            # CANCEL or fallthrough: just dismiss

        state._modal_state = 'IDLE'
        state._invalidate_cache()
        _dismiss_conflict()
        return {'RUNNING_MODAL'}

    if event.type == 'ESC' and event.value == 'PRESS':
        state._modal_state = 'IDLE'
        _dismiss_conflict()
        return {'RUNNING_MODAL'}

    return {'RUNNING_MODAL'}


def _handle_search(context, event):
    """Handle keyboard input during search mode. Returns modal return set or None."""
    if not state._search_active:
        return None

    if event.type == 'ESC' and event.value == 'PRESS':
        state._search_active = False
        state._search_text = ''
        _update_search_filter()
        _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'RET' and event.value == 'PRESS':
        state._search_active = False
        _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'BACK_SPACE' and event.value == 'PRESS':
        if state._search_text:
            state._search_text = state._search_text[:-1]
            now = time.monotonic()
            if now - state._search_last_update > 0.15:
                _update_search_filter()
                state._search_last_update = now
            _tag_redraw()
        return {'RUNNING_MODAL'}

    # Printable character input via event.unicode
    if event.value == 'PRESS' and event.unicode and event.unicode.isprintable():
        state._search_text += event.unicode
        now = time.monotonic()
        if now - state._search_last_update > 0.15:
            _update_search_filter()
            state._search_last_update = now
        _tag_redraw()
        return {'RUNNING_MODAL'}

    return None  # Not handled by search


# ---------------------------------------------------------------------------
# v0.9 Feature 5: Shortcut search handler
# ---------------------------------------------------------------------------
def _handle_shortcut_search(context, event):
    """Handle events in shortcut search mode. Returns modal return set or None."""
    if not state._shortcut_search_active:
        return None

    if event.type == 'ESC' and event.value == 'PRESS':
        state._shortcut_search_active = False
        _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.value == 'PRESS' and event.type in _CAPTURABLE_KEYS:
        # Find key index by matching event.type against key_rects
        found_idx = -1
        for i, kr in enumerate(state._key_rects):
            if kr.event_type == event.type:
                found_idx = i
                break

        if found_idx >= 0:
            state._selected_key_index = found_idx
            # Set modifier toggles from the pressed modifiers
            state._active_modifiers['ctrl'] = event.ctrl
            state._active_modifiers['shift'] = event.shift
            state._active_modifiers['alt'] = event.alt
            state._active_modifiers['oskey'] = event.oskey
            state._invalidate_cache()

        state._shortcut_search_active = False
        state._batch_dirty = True
        _tag_redraw()
        return {'RUNNING_MODAL'}

    return {'RUNNING_MODAL'}


# ---------------------------------------------------------------------------
# v0.9 Feature 6: Preset dropdown handler
# ---------------------------------------------------------------------------
def _handle_preset_dropdown(context, event):
    """Handle events while the preset dropdown is open."""
    if event.type == 'MOUSEMOVE':
        new_hover = _hit_test_preset_dropdown(event.mouse_region_x, event.mouse_region_y)
        if new_hover != state._preset_dropdown_hovered:
            state._preset_dropdown_hovered = new_hover
            _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
        mx, my = event.mouse_region_x, event.mouse_region_y
        dd_hit = _hit_test_preset_dropdown(mx, my)

        if dd_hit >= 0:
            item = state._preset_dropdown_rects[dd_hit]
            label, action = item[0], item[1]

            if action == 'SAVE_AS':
                # Enter name input mode
                state._preset_name_input_active = True
                state._preset_name_text = ''
                state._preset_dropdown_open = False
                state._preset_dropdown_rects = []
                state._preset_dropdown_hovered = -1
                state._modal_state = 'IDLE'
                _tag_redraw()
                return {'RUNNING_MODAL'}
            elif action == 'DELETE':
                # Delete current preset
                from .presets import _delete_preset
                if state._active_preset_name:
                    success, msg = _delete_preset(state._active_preset_name)
                    print(f"[Keymap Visualizer] {msg}")
                    if success:
                        state._active_preset_name = ""
            elif action.startswith('LOAD:'):
                preset_name = action[5:]
                from .presets import _load_preset
                # Push full undo snapshot before loading
                _push_undo_all_keymaps()
                success, msg = _load_preset(preset_name)
                print(f"[Keymap Visualizer] {msg}")

        # Close dropdown
        _dismiss_preset_dropdown()
        return {'RUNNING_MODAL'}

    if event.type in ('ESC', 'RIGHTMOUSE') and event.value == 'PRESS':
        _dismiss_preset_dropdown()
        return {'RUNNING_MODAL'}

    return {'RUNNING_MODAL'}


def _handle_preset_name_input(context, event):
    """Handle text input for preset name. Returns modal return set or None."""
    if not state._preset_name_input_active:
        return None

    if event.type == 'ESC' and event.value == 'PRESS':
        state._preset_name_input_active = False
        state._preset_name_text = ''
        _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'RET' and event.value == 'PRESS':
        name = state._preset_name_text.strip()
        if name:
            from .presets import _save_preset
            success, msg = _save_preset(name)
            print(f"[Keymap Visualizer] {msg}")
            if success:
                state._active_preset_name = name
        state._preset_name_input_active = False
        state._preset_name_text = ''
        _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'BACK_SPACE' and event.value == 'PRESS':
        if state._preset_name_text:
            state._preset_name_text = state._preset_name_text[:-1]
            _tag_redraw()
        return {'RUNNING_MODAL'}

    if event.value == 'PRESS' and event.unicode and event.unicode.isprintable():
        state._preset_name_text += event.unicode
        _tag_redraw()
        return {'RUNNING_MODAL'}

    return {'RUNNING_MODAL'}


def _push_undo_all_keymaps():
    """Push a partial undo snapshot (first few KMIs from each keymap) before preset load."""
    import bpy
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return
    # Collect first KMI from each keymap as a representative sample
    kmis = []
    for km in kc.keymaps:
        for kmi in km.keymap_items:
            kmis.append(kmi)
            if len(kmis) >= 50:
                break
        if len(kmis) >= 50:
            break
    if kmis:
        _push_undo(kmis)
