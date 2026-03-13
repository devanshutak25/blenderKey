"""
Keymap Visualizer – Keyboard layout computation
"""

from . import state
from .constants import (
    KeyRect, KEYBOARD_ROWS, NAV_CLUSTER_ROWS, NAV_ROW_ALIGNMENT,
    NUMPAD_ROWS, NUMPAD_ROW_ALIGNMENT,
    SPACE_TYPE_FILTERS, MODE_FILTERS,
)


def _compute_keyboard_layout(region_width, region_height):
    """Compute KeyRect list for all keys, centered in the region."""
    state._key_rects = []
    state._modifier_rects = []
    state._batch_dirty = True

    # Unit size: fit keyboard to fill the window in both dimensions.
    # Horizontal: wider divisor for more room per key
    # Vertical: 12 units (no separate toggle bar row)
    # Feature 2: Apply user scale
    unit_from_w = region_width / 24
    unit_from_h = region_height / 12
    unit_px = min(unit_from_w, unit_from_h) * state._user_scale
    if unit_px < 8:
        return  # Don't update _cached_region_size so draw callback retries

    state._cached_region_size = (region_width, region_height)
    key_gap = unit_px * 0.08

    # Calculate main block width (widest row)
    main_width = 0
    for row in KEYBOARD_ROWS:
        row_w = 0
        for item in row:
            if isinstance(item, (int, float)):
                row_w += item
            else:
                row_w += item[2]
        main_width = max(main_width, row_w)

    nav_gap = 1.0  # gap between main block and nav cluster in units
    nav_width = 3.0  # nav cluster is 3 keys wide max
    numpad_gap = 1.0
    numpad_width = 4.0
    total_width_units = main_width + nav_gap + nav_width + numpad_gap + numpad_width

    # Center the whole keyboard
    total_width_px = total_width_units * unit_px
    start_x = (region_width - total_width_px) / 2
    # Position keyboard above bottom panel (lists + info)
    bottom_panel_height = unit_px * 4.0
    start_y = bottom_panel_height + unit_px * 0.5

    # Build main block key rects (rows stack bottom-to-top)
    for row_idx, row in enumerate(KEYBOARD_ROWS):
        x = start_x
        y = start_y + row_idx * unit_px
        for item in row:
            if isinstance(item, (int, float)):
                x += item * unit_px
            else:
                label, event_type, width_u = item
                w = width_u * unit_px - key_gap
                h = unit_px - key_gap
                state._key_rects.append(KeyRect(label, event_type, x, y, w, h))
                x += width_u * unit_px

    # Build nav cluster key rects
    nav_start_x = start_x + (main_width + nav_gap) * unit_px
    for nav_row_idx, nav_row in enumerate(NAV_CLUSTER_ROWS):
        if nav_row_idx >= len(NAV_ROW_ALIGNMENT):
            break
        main_row_idx = NAV_ROW_ALIGNMENT[nav_row_idx]
        y = start_y + main_row_idx * unit_px
        x = nav_start_x
        for item in nav_row:
            if isinstance(item, (int, float)):
                x += item * unit_px
            else:
                label, event_type, width_u = item
                w = width_u * unit_px - key_gap
                h = unit_px - key_gap
                state._key_rects.append(KeyRect(label, event_type, x, y, w, h))
                x += width_u * unit_px

    # Build numpad key rects
    numpad_start_x = nav_start_x + nav_width * unit_px + numpad_gap * unit_px
    for np_row_idx, np_row in enumerate(NUMPAD_ROWS):
        if np_row_idx >= len(NUMPAD_ROW_ALIGNMENT):
            break
        main_row_idx = NUMPAD_ROW_ALIGNMENT[np_row_idx]
        y = start_y + main_row_idx * unit_px
        x = numpad_start_x
        for item in np_row:
            if isinstance(item, (int, float)):
                x += item * unit_px
            else:
                label, event_type, width_u = item
                w = width_u * unit_px - key_gap
                h = unit_px - key_gap
                state._key_rects.append(KeyRect(label, event_type, x, y, w, h))
                x += width_u * unit_px

    # --- Toolbar row above keyboard (Export + Presets only) ---
    toolbar_y = start_y + len(KEYBOARD_ROWS) * unit_px + unit_px * 0.3
    toolbar_h = unit_px * 0.7
    btn_gap = unit_px * 0.3
    export_btn_w = unit_px * 2.5
    presets_btn_w = unit_px * 2.5

    total_toolbar_w = export_btn_w + presets_btn_w + btn_gap
    toolbar_x = (region_width - total_toolbar_w) / 2

    x = toolbar_x
    state._export_button_rect = (x, toolbar_y, export_btn_w, toolbar_h)
    x += export_btn_w + btn_gap
    state._presets_btn_rect = (x, toolbar_y, presets_btn_w, toolbar_h)

    # --- Feature 1: Close button (top-right of keyboard frame) ---
    all_max_x = max(kr.x + kr.w for kr in state._key_rects)
    all_max_y = toolbar_y + toolbar_h  # top of toolbar
    pad = max(10, int(unit_px * 0.25))  # M5: scaled padding (matches drawing.py)
    btn_size = unit_px * 0.6
    state._close_button_rect = (all_max_x + pad - btn_size, all_max_y + pad - btn_size, btn_size, btn_size)

    # --- Feature 2: Resize handle (bottom-right of keyboard frame) ---
    all_min_y = min(kr.y for kr in state._key_rects)
    handle_size = max(12, unit_px * 0.4)
    state._resize_handle_rect = (all_max_x + pad - handle_size, all_min_y - pad, handle_size, handle_size)

    # --- Bottom panel: Editor list + Mode list + Info panel ---
    min_x = min(kr.x for kr in state._key_rects)
    gap = unit_px * 0.15
    panel_h = unit_px * 4.0
    panel_y = all_min_y - pad - panel_h - max(3, int(unit_px * 0.06))
    editor_list_w = unit_px * 3.5
    mode_list_w = unit_px * 3.0
    panel_start_x = min_x - pad

    # Editor list panel bounding box
    state._filter_editor_list_rect = (panel_start_x, panel_y, editor_list_w, panel_h)

    # Mode list panel bounding box
    mode_list_x = panel_start_x + editor_list_w + gap
    state._filter_mode_list_rect = (mode_list_x, panel_y, mode_list_w, panel_h)

    # Compute list item rects (leave room for header at top)
    item_h = max(20, unit_px * 0.5)
    header_h = max(16, unit_px * 0.35)  # space reserved for "Editors"/"Modes" header

    state._filter_editor_list_rects = []
    for i, (value, label) in enumerate(SPACE_TYPE_FILTERS):
        iy = panel_y + panel_h - header_h - (i + 1) * item_h
        state._filter_editor_list_rects.append((label, value, panel_start_x, iy, editor_list_w, item_h))

    state._filter_mode_list_rects = []
    for i, (value, label) in enumerate(MODE_FILTERS):
        iy = panel_y + panel_h - header_h - (i + 1) * item_h
        state._filter_mode_list_rects.append((label, value, mode_list_x, iy, mode_list_w, item_h))

    # C2: Build spatial index for keyboard navigation
    _compute_key_grid()


def _compute_key_grid():
    """Build row-based spatial index from _key_rects for arrow navigation."""
    state._key_row_map = []
    if not state._key_rects:
        return
    from collections import defaultdict
    y_buckets = defaultdict(list)
    for i, kr in enumerate(state._key_rects):
        row_y = round(kr.y, -1)  # round to nearest 10
        y_buckets[row_y].append(i)
    for row_y in sorted(y_buckets.keys()):
        row_indices = sorted(y_buckets[row_y], key=lambda i: state._key_rects[i].x)
        state._key_row_map.append(row_indices)
