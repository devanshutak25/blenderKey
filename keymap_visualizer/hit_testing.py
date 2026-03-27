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


# ---------------------------------------------------------------------------
# Spatial grid for O(1) key hit testing
# ---------------------------------------------------------------------------
_grid = None
_grid_cell_size = 0
_grid_origin_x = 0.0
_grid_origin_y = 0.0
_grid_cols = 0
_grid_rows = 0


def _build_spatial_grid():
    """Build a grid-based spatial index from state._key_rects.
    Call this whenever the keyboard layout changes."""
    global _grid, _grid_cell_size, _grid_origin_x, _grid_origin_y, _grid_cols, _grid_rows
    rects = state._key_rects
    if not rects:
        _grid = None
        return

    _grid_cell_size = max(max(kr.w, kr.h) for kr in rects)
    if _grid_cell_size <= 0:
        _grid = None
        return

    min_x = min(kr.x for kr in rects)
    min_y = min(kr.y for kr in rects)
    max_x = max(kr.x + kr.w for kr in rects)
    max_y = max(kr.y + kr.h for kr in rects)

    _grid_origin_x = min_x
    _grid_origin_y = min_y
    cs = _grid_cell_size
    _grid_cols = int((max_x - min_x) / cs) + 2
    _grid_rows = int((max_y - min_y) / cs) + 2
    _grid = [[] for _ in range(_grid_cols * _grid_rows)]

    for i, kr in enumerate(rects):
        c0 = int((kr.x - min_x) / cs)
        c1 = int((kr.x + kr.w - min_x) / cs)
        r0 = int((kr.y - min_y) / cs)
        r1 = int((kr.y + kr.h - min_y) / cs)
        for r in range(r0, min(r1 + 1, _grid_rows)):
            for c in range(c0, min(c1 + 1, _grid_cols)):
                _grid[r * _grid_cols + c].append(i)


def _hit_test_key(mx, my):
    """Returns index into state._key_rects or -1. Uses spatial grid when available."""
    if _grid is not None:
        cs = _grid_cell_size
        c = int((mx - _grid_origin_x) / cs)
        r = int((my - _grid_origin_y) / cs)
        if 0 <= c < _grid_cols and 0 <= r < _grid_rows:
            for i in _grid[r * _grid_cols + c]:
                kr = state._key_rects[i]
                if kr.x <= mx <= kr.x + kr.w and kr.y <= my <= kr.y + kr.h:
                    return i
        return -1

    # Fallback: linear scan
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


def _hit_test_import(mx, my):
    """Returns True if click is on import button."""
    return state._import_button_rect is not None and _point_in_rect(mx, my, state._import_button_rect)


def _hit_test_conflict_buttons(mx, my):
    """Returns button index or -1."""
    for i, (label, action, x, y, w, h) in enumerate(state._conflict_button_rects):
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1


def _hit_test_gpu_menu(mx, my):
    """Returns menu item index or -1. Items are 7-tuples: (label, bind_idx, x, y, w, h, is_active)."""
    for i, item in enumerate(state._gpu_menu_items):
        label, bind_idx, x, y, w, h, is_active = item
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1


def _hit_test_flyout(mx, my):
    """Returns flyout item index or -1."""
    for i, item in enumerate(state._gpu_flyout_items):
        label, action, x, y, w, h, bind_idx = item
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


def _hit_test_operator_group(mx, my):
    """Returns category string if click is on an operator group header, else None."""
    if state._operator_list_rect is None or not _point_in_rect(mx, my, state._operator_list_rect):
        return None
    scroll = state._operator_list_scroll
    for category, x, y, w, h in state._operator_list_group_rects:
        actual_y = y + scroll
        if x <= mx <= x + w and actual_y <= my <= actual_y + h:
            px, py, pw, ph = state._operator_list_rect
            if actual_y >= py and actual_y + h <= py + ph:
                return category
    return None


def _hit_test_operator_item(mx, my):
    """Returns index into state._operator_list_item_rects or -1."""
    if state._operator_list_rect is None or not _point_in_rect(mx, my, state._operator_list_rect):
        return -1
    scroll = state._operator_list_scroll
    for i, (op_id, human_name, x, y, w, h) in enumerate(state._operator_list_item_rects):
        actual_y = y + scroll
        if x <= mx <= x + w and actual_y <= my <= actual_y + h:
            px, py, pw, ph = state._operator_list_rect
            if actual_y >= py and actual_y + h <= py + ph:
                return i
    return -1


def _hit_test_op_flyout(mx, my):
    """Returns index into state._op_flyout_items or -1."""
    for i, (label, action, x, y, w, h) in enumerate(state._op_flyout_items):
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1
