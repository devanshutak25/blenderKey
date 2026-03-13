"""
Keymap Visualizer – Hit testing helpers
"""

from . import state


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
    if state._export_button_rect is None:
        return False
    x, y, w, h = state._export_button_rect
    return x <= mx <= x + w and y <= my <= y + h


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
    if state._close_button_rect is None:
        return False
    x, y, w, h = state._close_button_rect
    return x <= mx <= x + w and y <= my <= y + h


def _hit_test_resize(mx, my):
    """Returns True if click is on resize handle."""
    if state._resize_handle_rect is None:
        return False
    x, y, w, h = state._resize_handle_rect
    return x <= mx <= x + w and y <= my <= y + h


def _hit_test_editor_list(mx, my):
    """Returns item index in state._filter_editor_list_rects or -1."""
    # Check if cursor is within the panel bounds first
    if state._filter_editor_list_rect is None:
        return -1
    px, py, pw, ph = state._filter_editor_list_rect
    if not (px <= mx <= px + pw and py <= my <= py + ph):
        return -1
    scroll = state._filter_editor_scroll
    for i, item in enumerate(state._filter_editor_list_rects):
        label, value, x, y, w, h = item
        actual_y = y + scroll
        if x <= mx <= x + w and actual_y <= my <= actual_y + h:
            # Ensure the item is visible within the panel
            if actual_y >= py and actual_y + h <= py + ph:
                return i
    return -1


def _hit_test_mode_list(mx, my):
    """Returns item index in state._filter_mode_list_rects or -1."""
    if state._filter_mode_list_rect is None:
        return -1
    px, py, pw, ph = state._filter_mode_list_rect
    if not (px <= mx <= px + pw and py <= my <= py + ph):
        return -1
    scroll = state._filter_mode_scroll
    for i, item in enumerate(state._filter_mode_list_rects):
        label, value, x, y, w, h = item
        actual_y = y + scroll
        if x <= mx <= x + w and actual_y <= my <= actual_y + h:
            if actual_y >= py and actual_y + h <= py + ph:
                return i
    return -1


def _hit_test_presets_button(mx, my):
    """Returns True if click is on presets button."""
    if state._presets_btn_rect is None:
        return False
    x, y, w, h = state._presets_btn_rect
    return x <= mx <= x + w and y <= my <= y + h


def _hit_test_preset_dropdown(mx, my):
    """Returns index into state._preset_dropdown_rects or -1."""
    for i, item in enumerate(state._preset_dropdown_rects):
        label, action, x, y, w, h = item[:6]
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1
