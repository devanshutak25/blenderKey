"""
Keymap Visualizer – Hit testing helpers
"""

from . import state


def _point_in_rect(mx, my, rect):
    """Check if point (mx, my) is inside a (x, y, w, h) rectangle."""
    x, y, w, h = rect
    return x <= mx <= x + w and y <= my <= y + h


def _hit_test_scrolled_list(mx, my, panel_rect, item_rects, scroll):
    """Hit test a scrollable list panel. Returns item index or -1."""
    if panel_rect is None:
        return -1
    if not _point_in_rect(mx, my, panel_rect):
        return -1
    px, py, pw, ph = panel_rect
    for i, item in enumerate(item_rects):
        label, value, x, y, w, h = item
        actual_y = y + scroll
        if x <= mx <= x + w and actual_y <= my <= actual_y + h:
            if actual_y >= py and actual_y + h <= py + ph:
                return i
    return -1


def _hit_test_key(mx, my):
    """Returns index into state._key_rects or -1."""
    for i, kr in enumerate(state._key_rects):
        if kr.x <= mx <= kr.x + kr.w and kr.y <= my <= kr.y + kr.h:
            return i
    return -1


def _hit_test_modifier(mx, my):
    """Returns dict_key string or None."""
    for label, dict_key, x, y, w, h in state._modifier_rects:
        if x <= mx <= x + w and y <= my <= y + h:
            return dict_key
    return None


def _hit_test_export(mx, my):
    """Returns True if click is on export button."""
    return state._export_button_rect is not None and _point_in_rect(mx, my, state._export_button_rect)


def _hit_test_conflict_buttons(mx, my):
    """Returns button index or -1."""
    for i, (label, action, x, y, w, h) in enumerate(state._conflict_button_rects):
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1


def _hit_test_gpu_menu(mx, my):
    """Returns menu item index or -1. Skips header items (8-tuple with is_header=True)."""
    for i, item in enumerate(state._gpu_menu_items):
        if len(item) >= 8:
            label, action, x, y, w, h, binding_index, is_header = item
            if is_header:
                continue  # Headers are not clickable
        else:
            label, action, x, y, w, h = item[:6]
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1


def _hit_test_close(mx, my):
    """Returns True if click is on close button."""
    return state._close_button_rect is not None and _point_in_rect(mx, my, state._close_button_rect)


def _hit_test_resize(mx, my):
    """Returns True if click is on resize handle."""
    return state._resize_handle_rect is not None and _point_in_rect(mx, my, state._resize_handle_rect)


def _hit_test_editor_list(mx, my):
    """Returns item index in state._filter_editor_list_rects or -1."""
    return _hit_test_scrolled_list(mx, my, state._filter_editor_list_rect,
                                   state._filter_editor_list_rects, state._filter_editor_scroll)


def _hit_test_mode_list(mx, my):
    """Returns item index in state._filter_mode_list_rects or -1."""
    return _hit_test_scrolled_list(mx, my, state._filter_mode_list_rect,
                                   state._filter_mode_list_rects, state._filter_mode_scroll)


def _hit_test_info_panel_group(mx, my):
    """Returns group_key if click is on a collapsible group header, else None."""
    if not state._info_panel_rect or not _point_in_rect(mx, my, state._info_panel_rect):
        return None
    for group_key, x, y, w, h in state._info_panel_group_header_rects:
        if x <= mx <= x + w and y <= my <= y + h:
            return group_key
    return None


def _hit_test_presets_button(mx, my):
    """Returns True if click is on presets button."""
    return state._presets_btn_rect is not None and _point_in_rect(mx, my, state._presets_btn_rect)


def _hit_test_preset_dropdown(mx, my):
    """Returns index into state._preset_dropdown_rects or -1."""
    for i, item in enumerate(state._preset_dropdown_rects):
        label, action, x, y, w, h = item[:6]
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1
