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
    """Returns menu item index or -1."""
    for i, (label, action, x, y, w, h) in enumerate(state._gpu_menu_items):
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1
