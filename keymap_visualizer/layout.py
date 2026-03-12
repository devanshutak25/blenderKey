"""
Keymap Visualizer – Keyboard layout computation
"""

from . import state
from .constants import KeyRect, KEYBOARD_ROWS, NAV_CLUSTER_ROWS, NAV_ROW_ALIGNMENT


def _compute_keyboard_layout(region_width, region_height):
    """Compute KeyRect list for all keys, centered in the region."""
    state._key_rects = []
    state._modifier_rects = []
    state._batch_dirty = True

    # Unit size: fit ~20 units across with padding, cap at 50px
    unit_px = min(region_width / 22, 50)
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
    total_width_units = main_width + nav_gap + nav_width

    # Center the whole keyboard
    total_width_px = total_width_units * unit_px
    start_x = (region_width - total_width_px) / 2
    # Position keyboard ~40% from bottom, leaving room for info panel below
    info_panel_height = unit_px * 3
    start_y = info_panel_height + unit_px * 0.5

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

    # Build modifier toggle rects (above keyboard)
    toggle_labels = [("Ctrl", "ctrl"), ("Shift", "shift"), ("Alt", "alt"), ("OS", "oskey")]
    toggle_y = start_y + len(KEYBOARD_ROWS) * unit_px + unit_px * 0.3
    toggle_w = unit_px * 2
    toggle_h = unit_px * 0.7
    toggle_gap = unit_px * 0.3
    total_toggle_w = len(toggle_labels) * toggle_w + (len(toggle_labels) - 1) * toggle_gap
    toggle_start_x = (region_width - total_toggle_w) / 2
    for i, (label, key) in enumerate(toggle_labels):
        tx = toggle_start_x + i * (toggle_w + toggle_gap)
        state._modifier_rects.append((label, key, tx, toggle_y, toggle_w, toggle_h))

    # Export button (to the right of modifier toggles)
    if state._modifier_rects:
        last_mod = state._modifier_rects[-1]
        ex_x = last_mod[2] + last_mod[4] + toggle_gap * 2
        ex_w = unit_px * 2.5
        state._export_button_rect = (ex_x, toggle_y, ex_w, toggle_h)
    else:
        state._export_button_rect = None
