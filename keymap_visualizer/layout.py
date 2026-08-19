"""
Keymap Visualizer – Keyboard layout computation
"""

import bpy
from . import state
from .state import DirtyFlag
from .constants import KeyRect, SPACE_TYPE_FILTERS, MODE_FILTERS
from .keyboards import get_resolved_rows, MOUSE_ROWS, MOUSE_ALIGNMENT, MOUSE_WIDTH


# Vertical budget, in units, of everything stacked above y=0. The bottom band
# (filter lists + info panel) sits below the keys; the toolbar sits above them.
BOTTOM_BAND_UNITS = 3.2        # panel_h, see the bottom-panel section below
KEYS_ABOVE_BAND_UNITS = 0.5    # clearance between band and the bottom key row
TOOLBAR_STACK_UNITS = 1.1      # toolbar offset 0.3 + height 0.55 + plate pad 0.25

# Horizontal padding either side is max(10, 0.25 * unit) — the 10px floor takes
# over below this unit size.
_PAD_UNITS = 0.25
_PAD_FLOOR_PX = 10
_PAD_FLOOR_UNIT = _PAD_FLOOR_PX / _PAD_UNITS  # 40.0

# The bottom band is a scrolling viewport, so it does not have to fit its 15
# editors and 10 modes — but it does need room for its header and a few rows.
# These floors mirror layout's own item_h/header_h below.
_LIST_ITEM_FLOOR_PX = 20
_LIST_HEADER_FLOOR_PX = 16
_MIN_VISIBLE_LIST_ITEMS = 3
MIN_BAND_PX = _LIST_HEADER_FLOOR_PX + _MIN_VISIBLE_LIST_ITEMS * _LIST_ITEM_FLOOR_PX  # 76

# Below this unit size the band viewport drops under its floor and key text
# stops drawing (drawing.py gates label rendering at 20px), so the layout is no
# longer usable and we say so instead of drawing a broken one.
MIN_USABLE_UNIT_PX = MIN_BAND_PX / BOTTOM_BAND_UNITS  # 23.75


def _band_height_px(unit_px):
    """Height of the bottom band: proportional, but never below its floor."""
    return max(BOTTOM_BAND_UNITS * unit_px, MIN_BAND_PX)


def _widest_row(rows):
    """Width in units of the widest row, counting bare floats as spacers."""
    widest = 0.0
    for row in rows:
        row_w = 0.0
        for item in row:
            if isinstance(item, (int, float)):
                row_w += item
            else:
                row_w += item[2]
        widest = max(widest, row_w)
    return widest


def _fit_unit_px(region_width, region_height, total_width_units, n_main_rows):
    """Largest unit size at which the whole layout fits inside the region.

    Both axes have a pixel floor that takes over below a certain unit size, so
    each is solved in two branches rather than iterated: assume the
    proportional case, and fall back to the floor case when the first result
    lands in the floor's territory.
    """
    if total_width_units <= 0:
        return 0.0

    # Horizontal: total_width_units * unit + 2 * pad, pad = max(10, 0.25 * unit)
    unit_w = region_width / (total_width_units + 2 * _PAD_UNITS)
    if unit_w < _PAD_FLOOR_UNIT:
        unit_w = (region_width - 2 * _PAD_FLOOR_PX) / total_width_units

    # Vertical: band + clearance + key rows + toolbar stack, and the band has
    # its own pixel floor.
    above_band_units = KEYS_ABOVE_BAND_UNITS + n_main_rows + TOOLBAR_STACK_UNITS
    unit_h = region_height / (BOTTOM_BAND_UNITS + above_band_units)
    if unit_h < MIN_USABLE_UNIT_PX and above_band_units > 0:
        # Band has hit its floor and no longer shrinks with the unit.
        unit_h = (region_height - MIN_BAND_PX) / above_band_units

    return max(0.0, min(unit_w, unit_h))


def _min_region_size(total_width_units, n_main_rows):
    """Smallest region, in pixels, that yields a usable layout."""
    u = MIN_USABLE_UNIT_PX
    pad = max(_PAD_FLOOR_PX, u * _PAD_UNITS)
    w = total_width_units * u + 2 * pad
    h = _band_height_px(u) + (KEYS_ABOVE_BAND_UNITS + n_main_rows + TOOLBAR_STACK_UNITS) * u
    return int(w + 0.5), int(h + 0.5)


def _compute_keyboard_layout(region_width, region_height):
    """Compute KeyRect list for all keys, centered in the region."""
    state._key_rects = []
    state._modifier_rects = []
    state._dirty_flags |= DirtyFlag.BATCH
    # Invalidate geometry-dependent caches
    state._border_batch_cache = None
    state._shadow_batch_cache = None
    state._truncation_cache = {}
    state._keyboard_bounds = None

    # Read keyboard layout preferences
    try:
        prefs = state._get_prefs()
        form_factor = prefs.keyboard_form_factor
        logical_layout = prefs.keyboard_logical_layout
        physical_size = prefs.keyboard_physical_size
    except Exception:
        form_factor = 'ANSI'
        logical_layout = 'QWERTY'
        physical_size = '100'

    main_rows, nav_rows, numpad_rows, nav_alignment, numpad_alignment = \
        get_resolved_rows(form_factor, logical_layout, physical_size)

    # --- Content extents, in units. These depend only on the resolved rows,
    # never on unit_px, so they are known before the unit can be fitted. ---
    main_width = _widest_row(main_rows)

    nav_gap = 1.0  # gap between main block and nav cluster in units
    nav_width = _widest_row(nav_rows)
    numpad_gap = 1.0
    numpad_width = _widest_row(numpad_rows)

    # Mouse block gap
    mouse_gap = 1.0

    # Calculate total width based on which sections are present
    total_width_units = main_width
    if nav_rows:
        total_width_units += nav_gap + nav_width
    if numpad_rows:
        total_width_units += numpad_gap + numpad_width
    total_width_units += mouse_gap + MOUSE_WIDTH

    # Unit size: the largest unit at which the whole keyboard, its toolbar and
    # the bottom band fit inside the region. Feature 2: apply user scale.
    unit_px = _fit_unit_px(region_width, region_height,
                           total_width_units, len(main_rows)) * state._user_scale

    state._cached_region_size = (region_width, region_height)
    if unit_px < MIN_USABLE_UNIT_PX:
        # Too small to draw anything usable. Record why, so the draw callback
        # can say so instead of leaving the window mysteriously blank.
        state._layout_too_small = True
        state._layout_min_region = _min_region_size(total_width_units, len(main_rows))
        state._unit_px = 0.0
        return
    state._layout_too_small = False
    state._unit_px = unit_px
    key_gap = unit_px * 0.08

    # Center the whole keyboard
    total_width_px = total_width_units * unit_px
    start_x = (region_width - total_width_px) / 2
    # Position keyboard above bottom panel (lists + info)
    bottom_panel_height = _band_height_px(unit_px)
    start_y = bottom_panel_height + KEYS_ABOVE_BAND_UNITS * unit_px

    # Build main block key rects (rows stack bottom-to-top)
    for row_idx, row in enumerate(main_rows):
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
    if nav_rows:
        nav_start_x = start_x + (main_width + nav_gap) * unit_px
        for nav_row_idx, nav_row in enumerate(nav_rows):
            if nav_row_idx >= len(nav_alignment):
                break
            main_row_idx = nav_alignment[nav_row_idx]
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
    if numpad_rows:
        if nav_rows:
            numpad_start_x = start_x + (main_width + nav_gap + nav_width + numpad_gap) * unit_px
        else:
            numpad_start_x = start_x + (main_width + numpad_gap) * unit_px
        for np_row_idx, np_row in enumerate(numpad_rows):
            if np_row_idx >= len(numpad_alignment):
                break
            main_row_idx = numpad_alignment[np_row_idx]
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

    # --- Mouse block (right of everything else) ---
    state._mouse_rects_start_index = len(state._key_rects)
    # Find rightmost edge of existing keys
    if state._key_rects:
        existing_max_x = max(kr.x + kr.w for kr in state._key_rects)
    else:
        existing_max_x = start_x + main_width * unit_px
    mouse_start_x = existing_max_x + mouse_gap * unit_px
    for m_row_idx, m_row in enumerate(MOUSE_ROWS):
        if m_row_idx >= len(MOUSE_ALIGNMENT):
            break
        main_row_idx = MOUSE_ALIGNMENT[m_row_idx]
        y = start_y + main_row_idx * unit_px
        x = mouse_start_x
        for item in m_row:
            if isinstance(item, (int, float)):
                x += item * unit_px
            else:
                label, event_type, width_u = item
                w = width_u * unit_px - key_gap
                h = unit_px - key_gap
                state._key_rects.append(KeyRect(label, event_type, x, y, w, h))
                x += width_u * unit_px

    # --- Toolbar row above keyboard (Export + Import + Presets + Close, right-aligned) ---
    toolbar_y = start_y + len(main_rows) * unit_px + unit_px * 0.3
    toolbar_h = unit_px * 0.55
    btn_gap = unit_px * 0.2
    export_btn_w = unit_px * 1.6
    import_btn_w = unit_px * 1.6
    presets_btn_w = unit_px * 1.6
    close_btn_size = toolbar_h

    all_max_x = max(kr.x + kr.w for kr in state._key_rects)
    warning_btn_w = toolbar_h  # square icon button
    total_toolbar_w = (
        warning_btn_w + btn_gap
        + export_btn_w + btn_gap + import_btn_w + btn_gap + presets_btn_w + btn_gap
        + close_btn_size
    )
    toolbar_x = all_max_x - total_toolbar_w

    x = toolbar_x
    state._warning_button_rect = (x, toolbar_y, warning_btn_w, toolbar_h)
    x += warning_btn_w + btn_gap
    state._export_button_rect = (x, toolbar_y, export_btn_w, toolbar_h)
    x += export_btn_w + btn_gap
    state._import_button_rect = (x, toolbar_y, import_btn_w, toolbar_h)
    x += import_btn_w + btn_gap
    state._presets_btn_rect = (x, toolbar_y, presets_btn_w, toolbar_h)
    x += presets_btn_w + btn_gap
    state._close_button_rect = (x, toolbar_y, close_btn_size, close_btn_size)

    all_max_y = toolbar_y + toolbar_h
    pad = max(10, int(unit_px * 0.25))

    # --- Feature 2: Resize handle (bottom-right of keyboard frame) ---
    all_min_y = min(kr.y for kr in state._key_rects)
    handle_size = max(12, unit_px * 0.4)
    state._resize_handle_rect = (all_max_x + pad - handle_size, all_min_y - pad, handle_size, handle_size)

    # --- Bottom panel: Editor list + Mode list + Operators + Info panel ---
    min_x = min(kr.x for kr in state._key_rects)
    gap = unit_px * 0.12
    panel_h = _band_height_px(unit_px)
    panel_y = all_min_y - pad - panel_h - max(3, int(unit_px * 0.06))
    editor_list_w = unit_px * 2.8
    mode_list_w = unit_px * 2.5
    operator_list_w = unit_px * 3.0
    panel_start_x = min_x - pad

    # Editor list panel bounding box
    state._filter_editor_list_rect = (panel_start_x, panel_y, editor_list_w, panel_h)

    # Mode list panel bounding box
    mode_list_x = panel_start_x + editor_list_w + gap
    state._filter_mode_list_rect = (mode_list_x, panel_y, mode_list_w, panel_h)

    # Operator list panel bounding box
    operator_list_x = mode_list_x + mode_list_w + gap
    state._operator_list_rect = (operator_list_x, panel_y, operator_list_w, panel_h)

    # Info panel fills the rest of the band, to the right of the three lists.
    # Computed here rather than at draw time so it shares the band's floor and
    # y position instead of re-deriving them.
    info_x = operator_list_x + operator_list_w + gap
    state._info_panel_rect = (info_x, panel_y, (all_max_x + pad) - info_x, panel_h)

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

    # Cache keyboard bounds for drawing (avoids 4 generator passes per frame)
    if state._key_rects:
        state._keyboard_bounds = (
            min(kr.x for kr in state._key_rects),
            max(kr.x + kr.w for kr in state._key_rects),
            min(kr.y for kr in state._key_rects),
            max(kr.y + kr.h for kr in state._key_rects),
        )
    else:
        state._keyboard_bounds = (0, 0, 0, 0)

    # C2: Build spatial index for keyboard navigation
    _compute_key_grid()

    # Build spatial grid for O(1) hit testing
    from .hit_testing import _build_spatial_grid
    _build_spatial_grid()


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
