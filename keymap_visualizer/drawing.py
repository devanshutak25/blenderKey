"""
Keymap Visualizer – GPU drawing helpers and main draw callback
"""

import bpy
import gpu
import blf
import math
import time
import os
from gpu_extras.batch import batch_for_shader

from . import state
from .constants import (
    KEYBOARD_ROWS, _MODIFIER_EVENTS, MODIFIER_KEY_TO_DICT,
    COL_BG, COL_KEY_DEFAULT, COL_KEY_HOVER, COL_KEY_SELECTED, COL_KEY_MODIFIER,
    COL_KEY_INACTIVE, COL_BORDER, COL_BORDER_HIGHLIGHT, COL_TEXT, COL_TEXT_DIM,
    COL_TOGGLE_ACTIVE, COL_TOGGLE_INACTIVE, COL_INFO_BG,
    COL_CAPTURE_OVERLAY, COL_CAPTURE_TEXT, COL_CONFLICT_BG, COL_CONFLICT_HEADER,
    COL_BUTTON_NORMAL, COL_BUTTON_HOVER, COL_EXPORT_BUTTON, COL_EXPORT_BUTTON_HOVER,
    COL_SHADOW, COL_SEARCH_BG, COL_SEARCH_BORDER,
    COL_GPU_MENU_BG, COL_GPU_MENU_HOVER, COL_GPU_MENU_BORDER,
    COL_KEY_BOUND, SPACE_TYPE_FILTERS, MODE_FILTERS,
    COL_SHORTCUT_SEARCH_TEXT, CATEGORY_COLORS,
)

# ---------------------------------------------------------------------------
# Font loading: use bfont.ttf for better Unicode glyph support
# ---------------------------------------------------------------------------
_blender_font_id = 0
_condensed_font_id = 0


def _ensure_font_loaded():
    global _blender_font_id, _condensed_font_id
    if _blender_font_id != 0:
        return _blender_font_id
    bfont_dir = os.path.join(bpy.utils.resource_path('LOCAL'), "datafiles", "fonts")
    bfont_path = os.path.join(bfont_dir, "bfont.ttf")
    if not os.path.exists(bfont_path):
        bfont_path = os.path.join(bfont_dir, "bmonofont-i18n.ttf")
    if os.path.exists(bfont_path):
        loaded = blf.load(bfont_path)
        if loaded != -1:
            _blender_font_id = loaded
    # Load condensed font for command labels
    condensed_path = os.path.join(os.path.dirname(__file__), "fonts", "RobotoCondensed-Regular.ttf")
    if os.path.exists(condensed_path):
        loaded = blf.load(condensed_path)
        if loaded != -1:
            _condensed_font_id = loaded
    return _blender_font_id


def _get_condensed_font():
    """Return condensed font ID, falling back to main font."""
    return _condensed_font_id if _condensed_font_id != 0 else _blender_font_id
from .keymap_data import (
    _get_bindings_for_key, _get_all_bindings_for_key, _compute_bound_keys,
    _compute_key_labels, _compute_key_categories, _compute_key_editor_icons,
)
from .icons import (
    _load_icons, get_editor_icon, get_mode_icon, get_km_icon,
)
from .layout import _compute_keyboard_layout


def _get_colors():
    """Read all colors from addon preferences, falling back to constants."""
    try:
        prefs = bpy.context.preferences.addons["keymap_visualizer"].preferences
        return {
            # Keys
            'key_default': tuple(prefs.col_key_unbound),
            'key_selected': tuple(prefs.col_key_selected),
            'key_hovered': tuple(prefs.col_key_hovered),
            'key_bound': tuple(prefs.col_key_bound),
            'key_modifier': tuple(prefs.col_key_modifier),
            # General UI
            'background': tuple(prefs.col_background),
            'text': tuple(prefs.col_text),
            'text_dim': tuple(prefs.col_text_dim),
            'panel_bg': tuple(prefs.col_panel_bg),
            'shadow': tuple(prefs.col_shadow),
            # Borders
            'border': tuple(prefs.col_border),
            'border_highlight': tuple(prefs.col_border_highlight),
            # Toggles
            'toggle_active': tuple(prefs.col_toggle_active),
            'toggle_inactive': tuple(prefs.col_toggle_inactive),
            # Buttons
            'button_normal': tuple(prefs.col_button_normal),
            'button_hover': tuple(prefs.col_button_hover),
            'export_button': tuple(prefs.col_export_button),
            'export_button_hover': tuple(prefs.col_export_button_hover),
            # Search
            'search_bg': tuple(prefs.col_search_bg),
            'search_border': tuple(prefs.col_search_border),
            # Menu
            'menu_bg': tuple(prefs.col_menu_bg),
            'menu_hover': tuple(prefs.col_menu_hover),
            'menu_border': tuple(prefs.col_menu_border),
            # Overlays
            'capture_overlay': tuple(prefs.col_capture_overlay),
            'capture_text': tuple(prefs.col_capture_text),
            'conflict_bg': tuple(prefs.col_conflict_bg),
            'conflict_header': tuple(prefs.col_conflict_header),
            'shortcut_search_text': tuple(prefs.col_shortcut_search_text),
            # Category colors
            'cat_transform': tuple(prefs.col_cat_transform),
            'cat_navigation': tuple(prefs.col_cat_navigation),
            'cat_mesh': tuple(prefs.col_cat_mesh),
            'cat_object': tuple(prefs.col_cat_object),
            'cat_playback': tuple(prefs.col_cat_playback),
            'cat_animation': tuple(prefs.col_cat_animation),
            'cat_nodes': tuple(prefs.col_cat_nodes),
            'cat_uv': tuple(prefs.col_cat_uv),
            'cat_sculpt': tuple(prefs.col_cat_sculpt),
            'cat_paint': tuple(prefs.col_cat_paint),
            'cat_system': tuple(prefs.col_cat_system),
            'cat_edit': tuple(prefs.col_cat_edit),
            'cat_file': tuple(prefs.col_cat_file),
        }
    except Exception:
        return {
            'key_default': COL_KEY_DEFAULT,
            'key_selected': COL_KEY_SELECTED,
            'key_hovered': COL_KEY_HOVER,
            'key_bound': COL_KEY_BOUND,
            'key_modifier': COL_KEY_MODIFIER,
            'background': COL_BG,
            'text': COL_TEXT,
            'text_dim': COL_TEXT_DIM,
            'panel_bg': COL_INFO_BG,
            'shadow': COL_SHADOW,
            'border': COL_BORDER,
            'border_highlight': COL_BORDER_HIGHLIGHT,
            'toggle_active': COL_TOGGLE_ACTIVE,
            'toggle_inactive': COL_TOGGLE_INACTIVE,
            'button_normal': COL_BUTTON_NORMAL,
            'button_hover': COL_BUTTON_HOVER,
            'export_button': COL_EXPORT_BUTTON,
            'export_button_hover': COL_EXPORT_BUTTON_HOVER,
            'search_bg': COL_SEARCH_BG,
            'search_border': COL_SEARCH_BORDER,
            'menu_bg': COL_GPU_MENU_BG,
            'menu_hover': COL_GPU_MENU_HOVER,
            'menu_border': COL_GPU_MENU_BORDER,
            'capture_overlay': COL_CAPTURE_OVERLAY,
            'capture_text': COL_CAPTURE_TEXT,
            'conflict_bg': COL_CONFLICT_BG,
            'conflict_header': COL_CONFLICT_HEADER,
            'shortcut_search_text': COL_SHORTCUT_SEARCH_TEXT,
            'cat_transform': CATEGORY_COLORS["Transform"],
            'cat_navigation': CATEGORY_COLORS["Navigation"],
            'cat_mesh': CATEGORY_COLORS["Mesh"],
            'cat_object': CATEGORY_COLORS["Object"],
            'cat_playback': CATEGORY_COLORS["Playback"],
            'cat_animation': CATEGORY_COLORS["Animation"],
            'cat_nodes': CATEGORY_COLORS["Nodes"],
            'cat_uv': CATEGORY_COLORS["UV"],
            'cat_sculpt': CATEGORY_COLORS["Sculpt"],
            'cat_paint': CATEGORY_COLORS["Paint"],
            'cat_system': CATEGORY_COLORS["System"],
            'cat_edit': CATEGORY_COLORS["Edit"],
            'cat_file': CATEGORY_COLORS["File"],
        }


def _get_category_colors_enabled():
    """Check if category colors are enabled in preferences."""
    try:
        prefs = bpy.context.preferences.addons["keymap_visualizer"].preferences
        return prefs.enable_category_colors
    except Exception:
        return True


# Map category names to colors dict keys
_CAT_COLOR_KEYS = {
    "Transform": "cat_transform",
    "Navigation": "cat_navigation",
    "Mesh": "cat_mesh",
    "Object": "cat_object",
    "Playback": "cat_playback",
    "Animation": "cat_animation",
    "Nodes": "cat_nodes",
    "UV": "cat_uv",
    "Sculpt": "cat_sculpt",
    "Paint": "cat_paint",
    "System": "cat_system",
    "Edit": "cat_edit",
    "File": "cat_file",
}


def _draw_rect(shader, x, y, w, h, color):
    """Draw a filled rectangle."""
    verts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    batch = batch_for_shader(shader, 'TRIS', {"pos": verts}, indices=[(0, 1, 2), (0, 2, 3)])
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_rect_border(shader, x, y, w, h, color):
    """Draw a rectangle border."""
    verts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    batch = batch_for_shader(shader, 'LINES', {"pos": verts},
                             indices=[(0, 1), (1, 2), (2, 3), (3, 0)])
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_icon(texture, x, y, size):
    """Draw an icon texture at (x, y) with given size."""
    if texture is None:
        return
    try:
        import gpu
        from gpu_extras.batch import batch_for_shader
        shader = gpu.shader.from_builtin('IMAGE')
        coords = ((x, y), (x + size, y), (x + size, y + size), (x, y + size))
        texcoords = ((0, 0), (1, 0), (1, 1), (0, 1))
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": coords, "texCoord": texcoords})
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_sampler("image", texture)
        batch.draw(shader)
    except Exception:
        pass


def _lerp_color(a, b, t):
    """Linearly interpolate between two RGBA colors."""
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))


def _get_filter_label(filter_type):
    """Get the display label for current filter selection."""
    if filter_type == 'EDITOR':
        for value, label in SPACE_TYPE_FILTERS:
            if value == state._filter_space_type:
                return label
        return "All Editors"
    else:
        for value, label in MODE_FILTERS:
            if value == state._filter_mode:
                return label
        return "All Modes"


def _build_filter_dropdown(filter_type, button_rect, region_width, region_height):
    """Build dropdown rects for a filter button."""
    state._filter_dropdown_rects = []
    state._filter_dropdown_hovered = -1

    items = SPACE_TYPE_FILTERS if filter_type == 'EDITOR' else MODE_FILTERS
    bx, by, bw, bh = button_rect

    item_h = 26
    item_w = max(bw, 160)
    padding = 2

    # Position dropdown below the button
    dropdown_x = bx
    dropdown_y = by - len(items) * (item_h + padding) - padding

    # Clamp to screen
    if dropdown_x + item_w > region_width:
        dropdown_x = region_width - item_w - 5
    if dropdown_y < 5:
        dropdown_y = 5

    for i, (value, label) in enumerate(items):
        iy = by - (i + 1) * (item_h + padding)
        if iy < dropdown_y:
            iy = dropdown_y + i * (item_h + padding)
        state._filter_dropdown_rects.append((label, value, dropdown_x, iy, item_w, item_h))


def _build_gpu_menu(mx, my, region_width, region_height, bindings=None):
    """Build GPU-drawn context menu items at mouse position."""
    state._gpu_menu_items = []
    state._gpu_menu_hovered = -1

    if bindings is None:
        items = [
            ("Rebind", "REBIND"),
            ("Unbind", "UNBIND"),
            ("Reset to Default", "RESET"),
            ("Toggle Active", "TOGGLE"),
        ]

        item_w = 180
        item_h = 28
        padding = 4

        menu_x = mx
        menu_y = my - len(items) * (item_h + padding) - padding
        if menu_x + item_w > region_width:
            menu_x = region_width - item_w - 5
        if menu_y < 5:
            menu_y = my + 5

        for i, (label, action) in enumerate(items):
            iy = my - (i + 1) * (item_h + padding)
            if menu_y > my:
                iy = my + 5 + i * (item_h + padding)
            state._gpu_menu_items.append((label, action, menu_x, iy, item_w, item_h, 0, False))
        return

    # Feature 5: Enhanced multi-binding menu
    item_w = 280
    header_h = 24
    action_h = 26
    padding = 2

    menu_entries = []
    max_bindings = min(len(bindings), 5)
    for bi in range(max_bindings):
        km_name, op_id, mod_str, kmi, is_active = bindings[bi][:5]
        prefix = f"[{mod_str}] " if mod_str else ""
        active_tag = "" if is_active else "[inactive] "
        header_label = f"{active_tag}{prefix}{op_id}"
        if len(header_label) > 40:
            header_label = header_label[:37] + "..."
        header_label += f"  ({km_name})"
        if len(header_label) > 50:
            header_label = header_label[:47] + "..."
        menu_entries.append((header_label, "", bi, True, header_h))
        menu_entries.append(("  Rebind", "REBIND", bi, False, action_h))
        if is_active:
            menu_entries.append(("  Unbind", "UNBIND", bi, False, action_h))
        else:
            menu_entries.append(("  Enable", "TOGGLE", bi, False, action_h))
        menu_entries.append(("  Reset to Default", "RESET", bi, False, action_h))
        menu_entries.append(("  Toggle Active", "TOGGLE", bi, False, action_h))

    if not menu_entries:
        menu_entries.append(("No bindings", "", -1, True, header_h))

    total_h = sum(e[4] + padding for e in menu_entries) + padding

    menu_x = mx
    menu_y = my - total_h
    if menu_x + item_w > region_width:
        menu_x = region_width - item_w - 5
    if menu_y < 5:
        menu_y = my + 5

    current_y = my
    going_down = menu_y <= my
    if not going_down:
        current_y = menu_y

    for label, action, bi, is_header, ih in menu_entries:
        if going_down:
            current_y -= (ih + padding)
            iy = current_y
        else:
            iy = current_y
            current_y += ih + padding
        state._gpu_menu_items.append((label, action, menu_x, iy, item_w, ih, bi, is_header))


def _build_preset_dropdown(button_rect, region_width, region_height):
    """Build dropdown rects for the presets button."""
    from .presets import _list_presets

    state._preset_dropdown_rects = []
    state._preset_dropdown_hovered = -1

    presets = _list_presets()
    bx, by, bw, bh = button_rect

    item_h = 26
    item_w = max(bw, 180)
    padding = 2

    # Build items: presets + Save As + Delete
    items = []
    for name in presets:
        items.append((name, f"LOAD:{name}"))
    items.append(("Save As...", "SAVE_AS"))
    if state._active_preset_name:
        items.append((f"Delete '{state._active_preset_name}'", "DELETE"))

    dropdown_x = bx
    dropdown_y = by - len(items) * (item_h + padding) - padding
    if dropdown_x + item_w > region_width:
        dropdown_x = region_width - item_w - 5
    if dropdown_y < 5:
        dropdown_y = 5

    for i, (label, action) in enumerate(items):
        iy = by - (i + 1) * (item_h + padding)
        if iy < dropdown_y:
            iy = dropdown_y + i * (item_h + padding)
        state._preset_dropdown_rects.append((label, action, dropdown_x, iy, item_w, item_h))


_draw_callback_count = 0


def _draw_callback():
    """POST_PIXEL draw callback for the text-editor area."""
    global _draw_callback_count

    try:
        area = state._target_area
        if area is None:
            return
        _ = area.type
    except ReferenceError:
        return

    try:
        region = None
        for r in area.regions:
            if r.type == 'WINDOW':
                region = r
                break
        if region is None:
            return

        rw, rh = region.width, region.height

        # Recompute layout if region size changed
        if (rw, rh) != state._cached_region_size:
            _compute_keyboard_layout(rw, rh)

        # Retry layout if previous attempt failed
        if not state._key_rects and rw > 0 and rh > 0:
            _compute_keyboard_layout(rw, rh)

        if not state._key_rects:
            _draw_callback_count += 1
            if _draw_callback_count <= 5:
                print(f"[Keymap Visualizer] draw: no key_rects "
                      f"(region={rw}x{rh}, call #{_draw_callback_count})")
            return

        if _draw_callback_count > 0:
            print(f"[Keymap Visualizer] draw: first successful draw "
                  f"(region={rw}x{rh}, {len(state._key_rects)} keys)")
            _draw_callback_count = -1

        # Load icon textures (lazy, runs once)
        _load_icons()

        # Hover transition (Phase 7)
        now = time.monotonic()
        dt = min(now - state._last_frame_time, 0.1) if state._last_frame_time > 0 else 0.016
        state._last_frame_time = now
        if state._hovered_key_index != state._hover_transition_target:
            state._hover_transition_target = state._hovered_key_index
            state._hover_transition = 0.0
        elif state._hover_transition < 1.0:
            state._hover_transition = min(1.0, state._hover_transition + dt * 8.0)

        # Feature 3: Compute bound keys, key labels, key categories
        _compute_bound_keys()
        _compute_key_labels()
        _compute_key_categories()
        _compute_key_editor_icons()

        colors = _get_colors()
        category_colors_enabled = _get_category_colors_enabled()
        gpu.state.blend_set('ALPHA')

        shader_uniform = gpu.shader.from_builtin('UNIFORM_COLOR')
        shader_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')

        unit_px = min(rw / 24, rh / 12) * state._user_scale

        # --- A. Background plate ---
        min_x = min(kr.x for kr in state._key_rects)
        max_x = max(kr.x + kr.w for kr in state._key_rects)
        min_y = min(kr.y for kr in state._key_rects)
        max_y = max(kr.y + kr.h for kr in state._key_rects)

        # Include filter buttons / toolbar in bounding box
        if state._filter_editor_btn_rect:
            fx, fy, fw, fh = state._filter_editor_btn_rect
            max_y = max(max_y, fy + fh)
        if state._filter_mode_btn_rect:
            fx, fy, fw, fh = state._filter_mode_btn_rect
            max_y = max(max_y, fy + fh)

        pad = 15
        _draw_rect(shader_uniform, min_x - pad, min_y - pad,
                   (max_x - min_x) + 2 * pad, (max_y - min_y) + 2 * pad, colors['background'])

        # --- Feature 1: Close button ---
        if state._close_button_rect is not None:
            cbx, cby, cbw, cbh = state._close_button_rect
            cb_col = colors['button_hover'] if state._close_hovered else colors['button_normal']
            _draw_rect(shader_uniform, cbx, cby, cbw, cbh, cb_col)
            _draw_rect_border(shader_uniform, cbx, cby, cbw, cbh, colors['border'])
            font_id = _ensure_font_loaded()
            cb_font_size = max(10, int(cbh * 0.5))
            blf.size(font_id, cb_font_size)
            blf.color(font_id, *colors['text'])
            tw, th = blf.dimensions(font_id, "X")
            blf.position(font_id, cbx + (cbw - tw) / 2, cby + (cbh - th) / 2, 0)
            blf.draw(font_id, "X")

        # --- Feature 2: Resize handle ---
        if state._resize_handle_rect is not None:
            rhx, rhy, rhw, rhh = state._resize_handle_rect
            rh_col = colors['button_hover'] if state._resize_hovered else colors['button_normal']
            _draw_rect(shader_uniform, rhx, rhy, rhw, rhh, rh_col)
            line_verts = []
            line_indices = []
            for li in range(3):
                offset = (li + 1) * rhw * 0.25
                line_verts.extend([
                    (rhx + offset, rhy),
                    (rhx + rhw, rhy + rhh - offset),
                ])
                idx = li * 2
                line_indices.append((idx, idx + 1))
            if line_verts:
                lb = batch_for_shader(shader_uniform, 'LINES',
                                      {"pos": line_verts}, indices=line_indices)
                shader_uniform.bind()
                shader_uniform.uniform_float("color", colors['border'])
                lb.draw(shader_uniform)

        # --- B. Drop shadows behind keys (Phase 7) ---
        shadow_offset_x = 2
        shadow_offset_y = -2
        shadow_verts = []
        shadow_colors = []
        shadow_indices = []
        shadow_col = colors['shadow']
        sidx = 0
        for kr in state._key_rects:
            sx = kr.x + shadow_offset_x
            sy = kr.y + shadow_offset_y
            shadow_verts.extend([(sx, sy), (sx + kr.w, sy), (sx + kr.w, sy + kr.h), (sx, sy + kr.h)])
            shadow_colors.extend([shadow_col] * 4)
            shadow_indices.extend([(sidx, sidx + 1, sidx + 2), (sidx, sidx + 2, sidx + 3)])
            sidx += 4

        if shadow_verts:
            sb = batch_for_shader(shader_smooth, 'TRIS',
                                  {"pos": shadow_verts, "color": shadow_colors},
                                  indices=shadow_indices)
            shader_smooth.bind()
            sb.draw(shader_smooth)

        # --- Modifier pulsing (moved before Section C for key coloring) ---
        physical_active = any(state._physical_modifiers.values())
        pulse_t = 0.0
        if physical_active:
            pulse_t = 0.5 + 0.5 * math.sin(now * 2 * math.pi * 2)  # 2Hz sine

        # --- C. Key rectangles ---
        verts = []
        key_colors = []
        indices = []
        idx = 0

        search_dimming = state._search_active and state._search_text

        for i, kr in enumerate(state._key_rects):
            # Color priority:
            # 1. Selected → key_selected
            # 2. Hovered → lerp to key_hovered
            # 3. Modifier → COL_KEY_MODIFIER
            # 4. Category color (v0.9) → CATEGORY_COLORS[cat]
            # 5. Bound → key_bound
            # 6. Unbound → key_default
            if i == state._selected_key_index:
                col = colors['key_selected']
            elif i == state._hovered_key_index:
                if state._hover_transition < 1.0:
                    col = _lerp_color(colors['key_default'], colors['key_hovered'], state._hover_transition)
                else:
                    col = colors['key_hovered']
            elif kr.event_type in _MODIFIER_EVENTS:
                dict_key = MODIFIER_KEY_TO_DICT.get(kr.event_type)
                is_mod_active = state._get_effective_modifiers().get(dict_key, False)
                if is_mod_active and physical_active and state._physical_modifiers.get(dict_key, False):
                    base = colors['toggle_active']
                    col = (min(1.0, base[0] + pulse_t * 0.15),
                           min(1.0, base[1] + pulse_t * 0.15),
                           min(1.0, base[2] + pulse_t * 0.15), base[3])
                elif is_mod_active:
                    col = colors['toggle_active']
                else:
                    col = colors['key_modifier']
            elif category_colors_enabled and kr.event_type in state._key_categories_cache:
                cat = state._key_categories_cache[kr.event_type]
                cat_key = _CAT_COLOR_KEYS.get(cat)
                col = colors.get(cat_key, colors['key_bound']) if cat_key else colors['key_bound']
            elif kr.event_type in state._bound_keys_cache:
                col = colors['key_bound']
            else:
                col = colors['key_default']

            # Dim non-matching keys during search
            if search_dimming and kr.event_type not in state._search_matching_keys:
                col = (col[0] * 0.3, col[1] * 0.3, col[2] * 0.3, col[3])

            x, y, w, h = kr.x, kr.y, kr.w, kr.h
            verts.extend([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
            key_colors.extend([col, col, col, col])
            indices.extend([(idx, idx + 1, idx + 2), (idx, idx + 2, idx + 3)])
            idx += 4

        key_batch = batch_for_shader(shader_smooth, 'TRIS',
                                     {"pos": verts, "color": key_colors},
                                     indices=indices)
        shader_smooth.bind()
        key_batch.draw(shader_smooth)

        # --- D. Key borders ---
        border_verts = []
        border_indices = []
        bidx = 0
        for kr in state._key_rects:
            x, y, w, h = kr.x, kr.y, kr.w, kr.h
            border_verts.extend([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
            border_indices.extend([
                (bidx, bidx + 1), (bidx + 1, bidx + 2),
                (bidx + 2, bidx + 3), (bidx + 3, bidx),
            ])
            bidx += 4

        border_batch = batch_for_shader(shader_uniform, 'LINES',
                                        {"pos": border_verts},
                                        indices=border_indices)
        shader_uniform.bind()
        shader_uniform.uniform_float("color", colors['border'])
        border_batch.draw(shader_uniform)

        # Highlighted border for hovered/selected key
        highlight_idx = state._selected_key_index if state._selected_key_index >= 0 else state._hovered_key_index
        if highlight_idx >= 0:
            kr = state._key_rects[highlight_idx]
            x, y, w, h = kr.x, kr.y, kr.w, kr.h
            hl_verts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
            hl_indices = [(0, 1), (1, 2), (2, 3), (3, 0)]
            hl_batch = batch_for_shader(shader_uniform, 'LINES',
                                        {"pos": hl_verts},
                                        indices=hl_indices)
            gpu.state.line_width_set(2.0)
            shader_uniform.uniform_float("color", colors['border_highlight'])
            hl_batch.draw(shader_uniform)
            gpu.state.line_width_set(1.0)

        # Highlight border for active modifier keys
        for i, kr in enumerate(state._key_rects):
            if kr.event_type in _MODIFIER_EVENTS:
                dict_key = MODIFIER_KEY_TO_DICT.get(kr.event_type)
                if state._get_effective_modifiers().get(dict_key, False):
                    x, y, w, h = kr.x, kr.y, kr.w, kr.h
                    hl_verts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                    hl_indices = [(0, 1), (1, 2), (2, 3), (3, 0)]
                    hl_batch = batch_for_shader(shader_uniform, 'LINES',
                                                {"pos": hl_verts},
                                                indices=hl_indices)
                    gpu.state.line_width_set(2.0)
                    shader_uniform.uniform_float("color", colors['border_highlight'])
                    hl_batch.draw(shader_uniform)
                    gpu.state.line_width_set(1.0)

        # --- E. Key labels (v0.9: two-line — key label top-left, command label below) ---
        font_id = _ensure_font_loaded()
        font_size = max(10, int(unit_px * 0.3))
        cmd_font_size = max(8, int(unit_px * 0.18))

        if unit_px >= 20:
            for i, kr in enumerate(state._key_rects):
                if search_dimming and kr.event_type not in state._search_matching_keys:
                    td = colors['text_dim']
                    text_col = (td[0] * 0.4, td[1] * 0.4, td[2] * 0.4, td[3])
                else:
                    text_col = colors['text']

                cmd_label = state._key_labels_cache.get(kr.event_type)
                if cmd_label and kr.w >= unit_px * 0.8:
                    # Two-line layout: key label top-left, command label bottom
                    blf.size(font_id, font_size)
                    blf.color(font_id, *text_col)
                    blf.position(font_id, kr.x + 3, kr.y + kr.h - font_size - 2, 0)
                    blf.draw(font_id, kr.label)

                    # Command label (smaller, condensed font)
                    cfont = _get_condensed_font()
                    blf.size(cfont, cmd_font_size)
                    blf.color(cfont, *colors['text_dim'])
                    # Truncate if too wide
                    display_cmd = cmd_label
                    tw, th = blf.dimensions(cfont, display_cmd)
                    while tw > kr.w - 6 and len(display_cmd) > 3:
                        display_cmd = display_cmd[:-4] + "..."
                        tw, th = blf.dimensions(cfont, display_cmd)
                    blf.position(cfont, kr.x + 3, kr.y + kr.h * 0.15, 0)
                    blf.draw(cfont, display_cmd)
                else:
                    # Single centered label (original style)
                    blf.size(font_id, font_size)
                    blf.color(font_id, *text_col)
                    tw, th = blf.dimensions(font_id, kr.label)
                    tx = kr.x + (kr.w - tw) / 2
                    ty = kr.y + (kr.h - th) / 2
                    blf.position(font_id, tx, ty, 0)
                    blf.draw(font_id, kr.label)

                # Draw small editor icon in top-right corner for bound keys
                key_space_type = state._key_editor_icons_cache.get(kr.event_type)
                if key_space_type and kr.w >= unit_px * 0.8:
                    key_icon_tex = get_km_icon(key_space_type)
                    if key_icon_tex:
                        key_icon_sz = int(kr.h * 0.3)
                        _draw_icon(key_icon_tex,
                                   kr.x + kr.w - key_icon_sz - 2,
                                   kr.y + kr.h - key_icon_sz - 2,
                                   key_icon_sz)

        # --- F2. Export button (Phase 6) ---
        if state._export_button_rect is not None:
            ex, ey, ew, eh = state._export_button_rect
            ex_col = colors['export_button_hover'] if state._export_hovered else colors['export_button']
            _draw_rect(shader_uniform, ex, ey, ew, eh, ex_col)
            _draw_rect_border(shader_uniform, ex, ey, ew, eh, colors['border'])

            if unit_px >= 20:
                blf.size(font_id, font_size)
                blf.color(font_id, *colors['text'])
                elabel = "Export"
                tw, th = blf.dimensions(font_id, elabel)
                blf.position(font_id, ex + (ew - tw) / 2, ey + (eh - th) / 2, 0)
                blf.draw(font_id, elabel)

        # --- v0.9 Feature 6: Presets button ---
        if state._presets_btn_rect is not None:
            px, py, pw, ph = state._presets_btn_rect
            pr_col = colors['button_hover'] if state._presets_hovered else colors['button_normal']
            _draw_rect(shader_uniform, px, py, pw, ph, pr_col)
            _draw_rect_border(shader_uniform, px, py, pw, ph, colors['border'])

            if unit_px >= 20:
                blf.size(font_id, font_size)
                blf.color(font_id, *colors['text'])
                plabel = state._active_preset_name if state._active_preset_name else "Presets"
                tw, th = blf.dimensions(font_id, plabel)
                # Truncate if needed
                while tw > pw - 10 and len(plabel) > 3:
                    plabel = plabel[:-4] + "..."
                    tw, th = blf.dimensions(font_id, plabel)
                blf.position(font_id, px + (pw - tw) / 2, py + (ph - th) / 2, 0)
                blf.draw(font_id, plabel)

        # --- v0.9 Feature 4: Undo/redo counter ---
        undo_count = len(state._undo_stack)
        redo_count = len(state._redo_stack)
        if (undo_count > 0 or redo_count > 0) and state._export_button_rect is not None:
            ex, ey, ew, eh = state._export_button_rect
            undo_text = f"Undo: {undo_count} | Redo: {redo_count}"
            undo_font_size = max(8, int(unit_px * 0.2))
            blf.size(font_id, undo_font_size)
            blf.color(font_id, *colors['text_dim'])
            tw, th = blf.dimensions(font_id, undo_text)
            # Position below the export button
            blf.position(font_id, ex, ey - th - 4, 0)
            blf.draw(font_id, undo_text)

        # --- Feature 4: Filter buttons ---
        for btn_rect, hovered, filter_type in [
            (state._filter_editor_btn_rect, state._filter_editor_hovered, 'EDITOR'),
            (state._filter_mode_btn_rect, state._filter_mode_hovered, 'MODE'),
        ]:
            if btn_rect is not None:
                fbx, fby, fbw, fbh = btn_rect
                fb_col = colors['button_hover'] if hovered else colors['button_normal']
                _draw_rect(shader_uniform, fbx, fby, fbw, fbh, fb_col)
                _draw_rect_border(shader_uniform, fbx, fby, fbw, fbh, colors['border'])

                if unit_px >= 20:
                    blf.size(font_id, font_size)
                    blf.color(font_id, *colors['text'])
                    flabel = _get_filter_label(filter_type)
                    # Draw PNG icon
                    if filter_type == 'EDITOR':
                        icon_tex = get_editor_icon(state._filter_space_type)
                    else:
                        icon_tex = get_mode_icon(state._filter_mode)
                    icon_size = int(fbh * 0.6)
                    icon_x = fbx + 4
                    icon_y = fby + (fbh - icon_size) / 2
                    _draw_icon(icon_tex, icon_x, icon_y, icon_size)
                    # Shift text right to make room for icon
                    text_x = icon_x + icon_size + 4 if icon_tex else fbx + 4
                    tw, th = blf.dimensions(font_id, flabel)
                    avail_w = fbw - (text_x - fbx) - 4
                    while tw > avail_w and len(flabel) > 3:
                        flabel = flabel[:-4] + "..."
                        tw, th = blf.dimensions(font_id, flabel)
                    blf.position(font_id, text_x + (avail_w - tw) / 2, fby + (fbh - th) / 2, 0)
                    blf.draw(font_id, flabel)

        # --- Feature 4: Filter dropdown ---
        if state._filter_dropdown_open is not None and state._filter_dropdown_rects:
            first_dd = state._filter_dropdown_rects[0]
            dd_min_y = min(item[3] for item in state._filter_dropdown_rects)
            dd_max_y = max(item[3] + item[5] for item in state._filter_dropdown_rects)
            dd_x = first_dd[2] - 3
            dd_w = first_dd[4] + 6
            dd_h = (dd_max_y - dd_min_y) + 6

            _draw_rect(shader_uniform, dd_x, dd_min_y - 3, dd_w, dd_h, colors['menu_bg'])
            _draw_rect_border(shader_uniform, dd_x, dd_min_y - 3, dd_w, dd_h, colors['menu_border'])

            current_value = state._filter_space_type if state._filter_dropdown_open == 'EDITOR' else state._filter_mode
            for di, (dlabel, dvalue, dx, dy, dw, dh) in enumerate(state._filter_dropdown_rects):
                if di == state._filter_dropdown_hovered:
                    dcol = colors['menu_hover']
                elif dvalue == current_value:
                    dcol = (0.22, 0.28, 0.35, 1.0)
                else:
                    dcol = colors['menu_bg']
                _draw_rect(shader_uniform, dx, dy, dw, dh, dcol)

                if unit_px >= 20:
                    blf.size(font_id, font_size)
                    blf.color(font_id, *colors['text'])
                    # Draw PNG icon for dropdown item
                    if state._filter_dropdown_open == 'EDITOR':
                        dd_icon_tex = get_editor_icon(dvalue)
                    else:
                        dd_icon_tex = get_mode_icon(dvalue)
                    dd_icon_size = int(dh * 0.65)
                    dd_icon_x = dx + 4
                    dd_icon_y = dy + (dh - dd_icon_size) / 2
                    _draw_icon(dd_icon_tex, dd_icon_x, dd_icon_y, dd_icon_size)
                    # Shift text right
                    dd_text_x = dd_icon_x + dd_icon_size + 4 if dd_icon_tex else dx + 8
                    prefix = "* " if dvalue == current_value else "  "
                    display_text = f"{prefix}{dlabel}"
                    tw, th = blf.dimensions(font_id, display_text)
                    blf.position(font_id, dd_text_x, dy + (dh - th) / 2, 0)
                    blf.draw(font_id, display_text)

        # --- v0.9 Feature 6: Preset dropdown ---
        if state._preset_dropdown_open and state._preset_dropdown_rects:
            first_dd = state._preset_dropdown_rects[0]
            dd_min_y = min(item[3] for item in state._preset_dropdown_rects)
            dd_max_y = max(item[3] + item[5] for item in state._preset_dropdown_rects)
            dd_x = first_dd[2] - 3
            dd_w = first_dd[4] + 6
            dd_h = (dd_max_y - dd_min_y) + 6

            _draw_rect(shader_uniform, dd_x, dd_min_y - 3, dd_w, dd_h, colors['menu_bg'])
            _draw_rect_border(shader_uniform, dd_x, dd_min_y - 3, dd_w, dd_h, colors['menu_border'])

            for di, item in enumerate(state._preset_dropdown_rects):
                dlabel, daction, dx, dy, dw, dh = item[:6]
                if di == state._preset_dropdown_hovered:
                    dcol = colors['menu_hover']
                elif daction.startswith('LOAD:') and daction[5:] == state._active_preset_name:
                    dcol = (0.22, 0.28, 0.35, 1.0)
                else:
                    dcol = colors['menu_bg']
                _draw_rect(shader_uniform, dx, dy, dw, dh, dcol)

                if unit_px >= 20:
                    blf.size(font_id, font_size)
                    blf.color(font_id, *colors['text'])
                    tw, th = blf.dimensions(font_id, dlabel)
                    blf.position(font_id, dx + 8, dy + (dh - th) / 2, 0)
                    blf.draw(font_id, dlabel)

        # --- v0.9 Feature 3: Category color legend ---
        if category_colors_enabled and state._key_categories_cache:
            active_cats = set(state._key_categories_cache.values())
            if active_cats:
                legend_font_size = max(8, int(unit_px * 0.2))
                blf.size(font_id, legend_font_size)
                swatch_size = max(8, int(unit_px * 0.25))
                swatch_gap = 4
                legend_x = max_x + pad - 5
                legend_y = max_y - 5

                # Draw from top-right, going down
                for cat_name in sorted(active_cats):
                    cat_key = _CAT_COLOR_KEYS.get(cat_name)
                    cat_col = colors.get(cat_key, colors['key_bound']) if cat_key else colors['key_bound']
                    legend_y -= swatch_size + swatch_gap

                    # Color swatch
                    _draw_rect(shader_uniform, legend_x - swatch_size * 6 - swatch_size,
                               legend_y, swatch_size, swatch_size, cat_col)
                    # Label
                    blf.color(font_id, *colors['text_dim'])
                    tw, th = blf.dimensions(font_id, cat_name)
                    blf.position(font_id, legend_x - swatch_size * 6 + swatch_gap,
                                 legend_y + (swatch_size - th) / 2, 0)
                    blf.draw(font_id, cat_name)

        # --- F3. Search bar (Phase 7) ---
        if state._search_active:
            sb_w = min(300, rw * 0.4)
            sb_h = unit_px * 0.7
            sb_x = (rw - sb_w) / 2
            sb_y = max_y + pad + 5
            if state._filter_editor_btn_rect:
                fx, fy, fw, fh = state._filter_editor_btn_rect
                sb_y = max(sb_y, fy + fh + 10)

            _draw_rect(shader_uniform, sb_x, sb_y, sb_w, sb_h, colors['search_bg'])
            _draw_rect_border(shader_uniform, sb_x, sb_y, sb_w, sb_h, colors['search_border'])

            if unit_px >= 20:
                blf.size(font_id, font_size)
                blf.color(font_id, *colors['capture_text'])
                search_display = state._search_text + "|"
                if not state._search_text:
                    search_display = "Search operators... |"
                    blf.color(font_id, *colors['text_dim'])
                tw, th = blf.dimensions(font_id, search_display)
                blf.position(font_id, sb_x + 8, sb_y + (sb_h - th) / 2, 0)
                blf.draw(font_id, search_display)

        # --- v0.9 Feature 6: Preset name input overlay ---
        if state._preset_name_input_active:
            sb_w = min(300, rw * 0.4)
            sb_h = unit_px * 0.7
            sb_x = (rw - sb_w) / 2
            sb_y = rh / 2 - sb_h / 2

            _draw_rect(shader_uniform, 0, 0, rw, rh, colors['capture_overlay'])
            _draw_rect(shader_uniform, sb_x, sb_y, sb_w, sb_h, colors['search_bg'])
            _draw_rect_border(shader_uniform, sb_x, sb_y, sb_w, sb_h, colors['search_border'])

            if unit_px >= 20:
                blf.size(font_id, font_size)
                # Title above input
                blf.color(font_id, *colors['text'])
                title = "Save Preset As:"
                tw, th = blf.dimensions(font_id, title)
                blf.position(font_id, sb_x + (sb_w - tw) / 2, sb_y + sb_h + 8, 0)
                blf.draw(font_id, title)
                # Input text
                blf.color(font_id, *colors['capture_text'])
                input_display = state._preset_name_text + "|"
                if not state._preset_name_text:
                    input_display = "Enter preset name... |"
                    blf.color(font_id, *colors['text_dim'])
                tw, th = blf.dimensions(font_id, input_display)
                blf.position(font_id, sb_x + 8, sb_y + (sb_h - th) / 2, 0)
                blf.draw(font_id, input_display)

        # --- G. Info panel ---
        info_x = min_x - pad
        info_w = (max_x + pad) - info_x
        info_h = unit_px * 4.0
        info_y = min_y - pad - info_h - 5

        _draw_rect(shader_uniform, info_x, info_y, info_w, info_h, colors['panel_bg'])

        active_idx = state._selected_key_index if state._selected_key_index >= 0 else state._hovered_key_index
        info_font_size = max(10, int(unit_px * 0.28))
        blf.size(font_id, info_font_size)

        if 0 <= active_idx < len(state._key_rects):
            kr = state._key_rects[active_idx]
            bindings, n_matching = _get_all_bindings_for_key(kr.event_type)

            blf.color(font_id, *colors['text'])
            header = f"Key: {kr.label} ({kr.event_type})"
            header_has_filter = (state._filter_space_type != 'ALL' or state._filter_mode != 'ALL')
            if header_has_filter:
                filter_parts = []
                if state._filter_space_type != 'ALL':
                    filter_parts.append(_get_filter_label('EDITOR'))
                if state._filter_mode != 'ALL':
                    filter_parts.append(_get_filter_label('MODE'))
                header += f"  [{' / '.join(filter_parts)}]"
            header_x = info_x + 10
            header_y = info_y + info_h - info_font_size - 5
            # Draw filter icons inline before header text
            if header_has_filter:
                hdr_icon_size = int(info_font_size * 1.2)
                if state._filter_space_type != 'ALL':
                    hdr_icon_tex = get_editor_icon(state._filter_space_type)
                    _draw_icon(hdr_icon_tex, header_x, header_y - 1, hdr_icon_size)
                    if hdr_icon_tex:
                        header_x += hdr_icon_size + 2
                if state._filter_mode != 'ALL':
                    hdr_icon_tex = get_mode_icon(state._filter_mode)
                    _draw_icon(hdr_icon_tex, header_x, header_y - 1, hdr_icon_size)
                    if hdr_icon_tex:
                        header_x += hdr_icon_size + 2
            blf.position(font_id, header_x, header_y, 0)
            blf.draw(font_id, header)

            if bindings:
                line_h = info_font_size + 3
                col_w = (info_w - 30) / 2
                col_left_x = info_x + 15
                col_right_x = info_x + 15 + col_w + 10
                max_rows = max(1, int((info_h - info_font_size - 15) / line_h))
                total_shown = min(len(bindings), max_rows * 2)

                bind_icon_size = int(info_font_size * 1.0)
                for j in range(total_shown):
                    km_name, op_id, mod_str, kmi, is_active = bindings[j][:5]
                    km_space_type = bindings[j][5] if len(bindings[j]) > 5 else ''
                    prefix = f"[{mod_str}] " if mod_str else ""
                    active_tag = "" if is_active else "[inactive] "
                    line = f"{active_tag}{prefix}{op_id}  ({km_name})"

                    if not is_active:
                        blf.color(font_id, 0.5, 0.5, 0.5, 0.6)
                    elif j < n_matching:
                        blf.color(font_id, *colors['text'])
                    else:
                        blf.color(font_id, *colors['text_dim'])

                    col = j // max_rows
                    row = j % max_rows
                    cx = col_left_x if col == 0 else col_right_x
                    ly = info_y + info_h - info_font_size - 5 - (row + 1) * line_h
                    if ly < info_y + 5:
                        break
                    # Draw editor icon for this binding
                    bind_icon_tex = get_km_icon(km_space_type)
                    _draw_icon(bind_icon_tex, cx, ly - 1, bind_icon_size)
                    text_offset = bind_icon_size + 3 if bind_icon_tex else 0
                    blf.position(font_id, cx + text_offset, ly, 0)
                    blf.draw(font_id, line)
                if len(bindings) > total_shown:
                    blf.color(font_id, *colors['text_dim'])
                    ly = info_y + 5
                    blf.position(font_id, info_x + 15, ly, 0)
                    blf.draw(font_id, f"... and {len(bindings) - total_shown} more")
            else:
                blf.color(font_id, *colors['text_dim'])
                blf.position(font_id, info_x + 15, info_y + info_h - 2 * info_font_size - 8, 0)
                blf.draw(font_id, "No bindings found")
        else:
            blf.color(font_id, *colors['text_dim'])
            blf.position(font_id, info_x + 10, info_y + info_h / 2 - info_font_size / 2, 0)
            blf.draw(font_id, "Hover over a key to see its bindings  |  Right-click to edit  |  / to search  |  ? to find key")

        # --- H. Capture overlay (Phase 5) ---
        if state._modal_state == 'CAPTURE':
            _draw_rect(shader_uniform, 0, 0, rw, rh, colors['capture_overlay'])
            cap_font_size = max(14, int(unit_px * 0.5))
            blf.size(font_id, cap_font_size)
            blf.color(font_id, *colors['capture_text'])
            msg = "Press new key combination..."
            tw, th = blf.dimensions(font_id, msg)
            blf.position(font_id, (rw - tw) / 2, rh / 2 + 10, 0)
            blf.draw(font_id, msg)

            blf.size(font_id, info_font_size)
            blf.color(font_id, *colors['text_dim'])
            sub = "ESC to cancel"
            tw2, th2 = blf.dimensions(font_id, sub)
            blf.position(font_id, (rw - tw2) / 2, rh / 2 - 20, 0)
            blf.draw(font_id, sub)

        # --- v0.9 Feature 5: Shortcut search overlay ---
        if state._shortcut_search_active:
            _draw_rect(shader_uniform, 0, 0, rw, rh, colors['capture_overlay'])
            cap_font_size = max(14, int(unit_px * 0.5))
            blf.size(font_id, cap_font_size)
            blf.color(font_id, *colors['shortcut_search_text'])
            msg = "Press any key combination to find its binding..."
            tw, th = blf.dimensions(font_id, msg)
            blf.position(font_id, (rw - tw) / 2, rh / 2 + 10, 0)
            blf.draw(font_id, msg)

            blf.size(font_id, info_font_size)
            blf.color(font_id, *colors['text_dim'])
            sub = "ESC to cancel"
            tw2, th2 = blf.dimensions(font_id, sub)
            blf.position(font_id, (rw - tw2) / 2, rh / 2 - 20, 0)
            blf.draw(font_id, sub)

        # --- I. Conflict resolution overlay (Phase 5) ---
        if state._modal_state == 'CONFLICT':
            _draw_rect(shader_uniform, 0, 0, rw, rh, colors['capture_overlay'])

            panel_w = min(500, rw * 0.7)
            panel_h = min(300, rh * 0.5)
            panel_x = (rw - panel_w) / 2
            panel_y = (rh - panel_h) / 2

            _draw_rect(shader_uniform, panel_x, panel_y, panel_w, panel_h, colors['conflict_bg'])
            _draw_rect_border(shader_uniform, panel_x, panel_y, panel_w, panel_h, colors['border'])

            hdr_size = max(14, int(unit_px * 0.4))
            blf.size(font_id, hdr_size)
            blf.color(font_id, *colors['conflict_header'])
            hdr_text = "Conflict Detected"
            tw, th = blf.dimensions(font_id, hdr_text)
            blf.position(font_id, panel_x + (panel_w - tw) / 2, panel_y + panel_h - 35, 0)
            blf.draw(font_id, hdr_text)

            blf.size(font_id, info_font_size)
            blf.color(font_id, *colors['text'])
            src_kmi = state._conflict_data.get('source_kmi')
            if src_kmi:
                src_text = f"Rebinding: {src_kmi.idname} -> {state._conflict_data['new_type']}"
                mod_parts = []
                if state._conflict_data['new_ctrl']:
                    mod_parts.append("Ctrl")
                if state._conflict_data['new_shift']:
                    mod_parts.append("Shift")
                if state._conflict_data['new_alt']:
                    mod_parts.append("Alt")
                if state._conflict_data['new_oskey']:
                    mod_parts.append("OS")
                if mod_parts:
                    src_text += f" ({'+'.join(mod_parts)})"
                blf.position(font_id, panel_x + 15, panel_y + panel_h - 60, 0)
                blf.draw(font_id, src_text)

            blf.color(font_id, *colors['text_dim'])
            conflicts = state._conflict_data.get('conflicts', [])
            for ci, (ckm_name, ckmi) in enumerate(conflicts[:5]):
                cy = panel_y + panel_h - 85 - ci * (info_font_size + 4)
                conflict_line = f"  Conflicts with: {ckmi.idname} ({ckm_name})"
                blf.position(font_id, panel_x + 15, cy, 0)
                blf.draw(font_id, conflict_line)

            btn_w = 100
            btn_h = 30
            btn_y = panel_y + 20
            btn_gap = 20
            total_btn_w = 3 * btn_w + 2 * btn_gap
            btn_start_x = panel_x + (panel_w - total_btn_w) / 2

            btn_labels = [("Swap", "SWAP"), ("Override", "OVERRIDE"), ("Cancel", "CANCEL")]
            state._conflict_button_rects.clear()
            for bi, (blabel, baction) in enumerate(btn_labels):
                bx = btn_start_x + bi * (btn_w + btn_gap)
                bcol = colors['button_hover'] if bi == state._conflict_hovered_button else colors['button_normal']
                _draw_rect(shader_uniform, bx, btn_y, btn_w, btn_h, bcol)
                _draw_rect_border(shader_uniform, bx, btn_y, btn_w, btn_h, colors['border'])
                state._conflict_button_rects.append((blabel, baction, bx, btn_y, btn_w, btn_h))

                blf.size(font_id, info_font_size)
                blf.color(font_id, *colors['text'])
                tw, th = blf.dimensions(font_id, blabel)
                blf.position(font_id, bx + (btn_w - tw) / 2, btn_y + (btn_h - th) / 2, 0)
                blf.draw(font_id, blabel)

        # --- J. GPU-drawn context menu (Phase 5 + Feature 5) ---
        if state._modal_state == 'MENU_OPEN' and state._gpu_menu_items:
            if state._gpu_menu_items:
                all_x = [item[2] for item in state._gpu_menu_items]
                all_y = [item[3] for item in state._gpu_menu_items]
                all_y_max = [item[3] + item[5] for item in state._gpu_menu_items]
                menu_bg_x = min(all_x) - 3
                menu_bg_y = min(all_y) - 3
                menu_bg_w = state._gpu_menu_items[0][4] + 6
                menu_bg_h = (max(all_y_max) - min(all_y)) + 6

                _draw_rect(shader_uniform, menu_bg_x, menu_bg_y, menu_bg_w, menu_bg_h, colors['menu_bg'])
                _draw_rect_border(shader_uniform, menu_bg_x, menu_bg_y, menu_bg_w, menu_bg_h,
                                  colors['menu_border'])

            for mi_idx, item in enumerate(state._gpu_menu_items):
                if len(item) >= 8:
                    mlabel, maction, mx, my, mw, mh, mbind_idx, mis_header = item
                else:
                    mlabel, maction, mx, my, mw, mh = item[:6]
                    mbind_idx, mis_header = 0, False

                if mis_header:
                    mcol = colors['panel_bg']
                    _draw_rect(shader_uniform, mx, my, mw, mh, mcol)
                    blf.size(font_id, info_font_size)
                    blf.color(font_id, *colors['text_dim'])
                    # Draw editor icon before header text
                    menu_icon_size = int(mh * 0.7)
                    menu_text_x = mx + 8
                    all_bindings = state._menu_context.get('all_bindings', [])
                    if 0 <= mbind_idx < len(all_bindings) and len(all_bindings[mbind_idx]) > 5:
                        menu_icon_tex = get_km_icon(all_bindings[mbind_idx][5])
                        _draw_icon(menu_icon_tex, mx + 4, my + (mh - menu_icon_size) / 2, menu_icon_size)
                        if menu_icon_tex:
                            menu_text_x = mx + menu_icon_size + 8
                    tw, th = blf.dimensions(font_id, mlabel)
                    blf.position(font_id, menu_text_x, my + (mh - th) / 2, 0)
                    blf.draw(font_id, mlabel)
                else:
                    mcol = colors['menu_hover'] if mi_idx == state._gpu_menu_hovered else colors['menu_bg']
                    _draw_rect(shader_uniform, mx, my, mw, mh, mcol)
                    blf.size(font_id, info_font_size)
                    blf.color(font_id, *colors['text'])
                    tw, th = blf.dimensions(font_id, mlabel)
                    blf.position(font_id, mx + 10, my + (mh - th) / 2, 0)
                    blf.draw(font_id, mlabel)

        gpu.state.blend_set('NONE')
    except Exception:
        import traceback
        traceback.print_exc()
