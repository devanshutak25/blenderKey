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


def _hit_test_filter_buttons(mx, my):
    """Returns 'EDITOR', 'MODE', or None."""
    if state._filter_editor_btn_rect is not None:
        x, y, w, h = state._filter_editor_btn_rect
        if x <= mx <= x + w and y <= my <= y + h:
            return 'EDITOR'
    if state._filter_mode_btn_rect is not None:
        x, y, w, h = state._filter_mode_btn_rect
        if x <= mx <= x + w and y <= my <= y + h:
            return 'MODE'
    return None


def _hit_test_filter_dropdown(mx, my):
    """Returns index into state._filter_dropdown_rects or -1."""
    for i, item in enumerate(state._filter_dropdown_rects):
        label, value, x, y, w, h = item
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1
