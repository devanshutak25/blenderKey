"""
Keymap Visualizer – GPU drawing helpers and main draw callback
"""

import bpy
import gpu
import blf
import time
from gpu_extras.batch import batch_for_shader

from . import state
from .constants import (
    KEYBOARD_ROWS, _MODIFIER_EVENTS,
    COL_BG, COL_KEY_DEFAULT, COL_KEY_HOVER, COL_KEY_SELECTED, COL_KEY_MODIFIER,
    COL_KEY_INACTIVE, COL_BORDER, COL_BORDER_HIGHLIGHT, COL_TEXT, COL_TEXT_DIM,
    COL_TOGGLE_ACTIVE, COL_TOGGLE_INACTIVE, COL_INFO_BG,
    COL_CAPTURE_OVERLAY, COL_CAPTURE_TEXT, COL_CONFLICT_BG, COL_CONFLICT_HEADER,
    COL_BUTTON_NORMAL, COL_BUTTON_HOVER, COL_EXPORT_BUTTON, COL_EXPORT_BUTTON_HOVER,
    COL_SHADOW, COL_SEARCH_BG, COL_SEARCH_BORDER,
    COL_GPU_MENU_BG, COL_GPU_MENU_HOVER, COL_GPU_MENU_BORDER,
)
from .keymap_data import _get_bindings_for_key
from .layout import _compute_keyboard_layout


def _get_colors():
    """Read colors from addon preferences, falling back to defaults."""
    try:
        prefs = bpy.context.preferences.addons["keymap_visualizer"].preferences
        return {
            'key_default': tuple(prefs.col_key_unbound),
            'key_selected': tuple(prefs.col_key_selected),
            'key_hovered': tuple(prefs.col_key_hovered),
            'background': tuple(prefs.col_background),
            'text': tuple(prefs.col_text),
            'panel_bg': tuple(prefs.col_panel_bg),
        }
    except Exception:
        return {
            'key_default': COL_KEY_DEFAULT,
            'key_selected': COL_KEY_SELECTED,
            'key_hovered': COL_KEY_HOVER,
            'background': COL_BG,
            'text': COL_TEXT,
            'panel_bg': COL_INFO_BG,
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


def _lerp_color(a, b, t):
    """Linearly interpolate between two RGBA colors."""
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))


def _build_gpu_menu(mx, my, region_width, region_height):
    """Build GPU-drawn context menu items at mouse position."""
    state._gpu_menu_items = []
    state._gpu_menu_hovered = -1

    items = [
        ("Rebind", "REBIND"),
        ("Unbind", "UNBIND"),
        ("Reset to Default", "RESET"),
        ("Toggle Active", "TOGGLE"),
    ]

    item_w = 180
    item_h = 28
    padding = 4

    # Position menu so it doesn't go off-screen
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
        state._gpu_menu_items.append((label, action, menu_x, iy, item_w, item_h))


_draw_callback_count = 0


def _draw_callback():
    """POST_PIXEL draw callback for the text-editor area."""
    global _draw_callback_count

    try:
        area = state._target_area
        if area is None:
            return
        _ = area.type  # Force access to detect stale reference
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

        # Retry layout if previous attempt failed (e.g., region was 0x0)
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
            _draw_callback_count = -1  # Don't print again

        # Hover transition (Phase 7)
        now = time.monotonic()
        dt = min(now - state._last_frame_time, 0.1) if state._last_frame_time > 0 else 0.016
        state._last_frame_time = now
        if state._hovered_key_index != state._hover_transition_target:
            state._hover_transition_target = state._hovered_key_index
            state._hover_transition = 0.0
        elif state._hover_transition < 1.0:
            state._hover_transition = min(1.0, state._hover_transition + dt * 8.0)

        colors = _get_colors()
        gpu.state.blend_set('ALPHA')

        shader_uniform = gpu.shader.from_builtin('UNIFORM_COLOR')
        shader_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')

        # --- A. Background plate ---
        min_x = min(kr.x for kr in state._key_rects)
        max_x = max(kr.x + kr.w for kr in state._key_rects)
        min_y = min(kr.y for kr in state._key_rects)
        max_y = max(kr.y + kr.h for kr in state._key_rects)

        if state._modifier_rects:
            mod_max_y = max(y + h for _, _, x, y, w, h in state._modifier_rects)
            max_y = max(max_y, mod_max_y)

        pad = 15
        _draw_rect(shader_uniform, min_x - pad, min_y - pad,
                   (max_x - min_x) + 2 * pad, (max_y - min_y) + 2 * pad, colors['background'])

        # --- B. Drop shadows behind keys (Phase 7) ---
        shadow_offset_x = 2
        shadow_offset_y = -2
        shadow_verts = []
        shadow_colors = []
        shadow_indices = []
        sidx = 0
        for kr in state._key_rects:
            sx = kr.x + shadow_offset_x
            sy = kr.y + shadow_offset_y
            shadow_verts.extend([(sx, sy), (sx + kr.w, sy), (sx + kr.w, sy + kr.h), (sx, sy + kr.h)])
            shadow_colors.extend([COL_SHADOW] * 4)
            shadow_indices.extend([(sidx, sidx + 1, sidx + 2), (sidx, sidx + 2, sidx + 3)])
            sidx += 4

        if shadow_verts:
            sb = batch_for_shader(shader_smooth, 'TRIS',
                                  {"pos": shadow_verts, "color": shadow_colors},
                                  indices=shadow_indices)
            shader_smooth.bind()
            sb.draw(shader_smooth)

        # --- C. Key rectangles ---
        verts = []
        key_colors = []
        indices = []
        idx = 0

        # Check which keys have any active bindings (for inactive key coloring)
        search_dimming = state._search_active and state._search_text

        for i, kr in enumerate(state._key_rects):
            # Determine color
            if i == state._selected_key_index:
                col = colors['key_selected']
            elif i == state._hovered_key_index:
                if state._hover_transition < 1.0:
                    col = _lerp_color(colors['key_default'], colors['key_hovered'], state._hover_transition)
                else:
                    col = colors['key_hovered']
            elif kr.event_type in _MODIFIER_EVENTS:
                col = COL_KEY_MODIFIER
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
        shader_uniform.uniform_float("color", COL_BORDER)
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
            shader_uniform.uniform_float("color", COL_BORDER_HIGHLIGHT)
            hl_batch.draw(shader_uniform)
            gpu.state.line_width_set(1.0)

        # --- E. Key labels ---
        unit_px = min(rw / 22, 50)
        font_id = 0
        font_size = max(10, int(unit_px * 0.3))

        if unit_px >= 20:
            blf.size(font_id, font_size)
            blf.color(font_id, *colors['text'])
            for i, kr in enumerate(state._key_rects):
                if search_dimming and kr.event_type not in state._search_matching_keys:
                    blf.color(font_id, *(COL_TEXT_DIM[0] * 0.4, COL_TEXT_DIM[1] * 0.4,
                                         COL_TEXT_DIM[2] * 0.4, COL_TEXT_DIM[3]))
                else:
                    blf.color(font_id, *colors['text'])
                tw, th = blf.dimensions(font_id, kr.label)
                tx = kr.x + (kr.w - tw) / 2
                ty = kr.y + (kr.h - th) / 2
                blf.position(font_id, tx, ty, 0)
                blf.draw(font_id, kr.label)

        # --- F. Modifier toggle bar ---
        for label, dict_key, mx, my, mw, mh in state._modifier_rects:
            is_active = state._active_modifiers.get(dict_key, False)
            col = COL_TOGGLE_ACTIVE if is_active else COL_TOGGLE_INACTIVE
            _draw_rect(shader_uniform, mx, my, mw, mh, col)
            border_col = COL_BORDER_HIGHLIGHT if is_active else COL_BORDER
            _draw_rect_border(shader_uniform, mx, my, mw, mh, border_col)

            if unit_px >= 20:
                blf.size(font_id, font_size)
                blf.color(font_id, *colors['text'])
                tw, th = blf.dimensions(font_id, label)
                blf.position(font_id, mx + (mw - tw) / 2, my + (mh - th) / 2, 0)
                blf.draw(font_id, label)

        # --- F2. Export button (Phase 6) ---
        if state._export_button_rect is not None:
            ex, ey, ew, eh = state._export_button_rect
            ex_col = COL_EXPORT_BUTTON_HOVER if state._export_hovered else COL_EXPORT_BUTTON
            _draw_rect(shader_uniform, ex, ey, ew, eh, ex_col)
            _draw_rect_border(shader_uniform, ex, ey, ew, eh, COL_BORDER)

            if unit_px >= 20:
                blf.size(font_id, font_size)
                blf.color(font_id, *colors['text'])
                elabel = "Export"
                tw, th = blf.dimensions(font_id, elabel)
                blf.position(font_id, ex + (ew - tw) / 2, ey + (eh - th) / 2, 0)
                blf.draw(font_id, elabel)

        # --- F3. Search bar (Phase 7) ---
        if state._search_active:
            sb_w = min(300, rw * 0.4)
            sb_h = unit_px * 0.7
            sb_x = (rw - sb_w) / 2
            sb_y = max_y + pad + 5
            if state._modifier_rects:
                mod_max = max(y + h for _, _, x, y, w, h in state._modifier_rects)
                sb_y = mod_max + 10

            _draw_rect(shader_uniform, sb_x, sb_y, sb_w, sb_h, COL_SEARCH_BG)
            _draw_rect_border(shader_uniform, sb_x, sb_y, sb_w, sb_h, COL_SEARCH_BORDER)

            if unit_px >= 20:
                blf.size(font_id, font_size)
                blf.color(font_id, *COL_CAPTURE_TEXT)
                search_display = state._search_text + "|"
                if not state._search_text:
                    search_display = "Search operators... |"
                    blf.color(font_id, *COL_TEXT_DIM)
                tw, th = blf.dimensions(font_id, search_display)
                blf.position(font_id, sb_x + 8, sb_y + (sb_h - th) / 2, 0)
                blf.draw(font_id, search_display)

        # --- G. Info panel ---
        info_x = min_x - pad
        info_w = (max_x + pad) - info_x
        info_h = unit_px * 2.8
        info_y = min_y - pad - info_h - 5

        _draw_rect(shader_uniform, info_x, info_y, info_w, info_h, colors['panel_bg'])

        # Info text
        active_idx = state._selected_key_index if state._selected_key_index >= 0 else state._hovered_key_index
        info_font_size = max(10, int(unit_px * 0.28))
        blf.size(font_id, info_font_size)

        if 0 <= active_idx < len(state._key_rects):
            kr = state._key_rects[active_idx]
            bindings = _get_bindings_for_key(kr.event_type, state._active_modifiers)

            # Header
            blf.color(font_id, *colors['text'])
            header = f"Key: {kr.label} ({kr.event_type})"
            blf.position(font_id, info_x + 10, info_y + info_h - info_font_size - 5, 0)
            blf.draw(font_id, header)

            if bindings:
                line_h = info_font_size + 3
                max_lines = min(len(bindings), 6)
                for j in range(max_lines):
                    km_name, op_id, mod_str, kmi, is_active = bindings[j]
                    prefix = f"[{mod_str}] " if mod_str else ""
                    active_tag = "" if is_active else "[inactive] "
                    line = f"{active_tag}{prefix}{op_id}  ({km_name})"

                    # Dim inactive bindings
                    if is_active:
                        blf.color(font_id, *COL_TEXT_DIM)
                    else:
                        blf.color(font_id, 0.5, 0.5, 0.5, 0.6)

                    ly = info_y + info_h - info_font_size - 5 - (j + 1) * line_h
                    if ly < info_y + 5:
                        break
                    blf.position(font_id, info_x + 15, ly, 0)
                    blf.draw(font_id, line)
                if len(bindings) > max_lines:
                    blf.color(font_id, *COL_TEXT_DIM)
                    ly = info_y + info_h - info_font_size - 5 - (max_lines + 1) * line_h
                    if ly >= info_y + 5:
                        blf.position(font_id, info_x + 15, ly, 0)
                        blf.draw(font_id, f"... and {len(bindings) - max_lines} more")
            else:
                blf.color(font_id, *COL_TEXT_DIM)
                blf.position(font_id, info_x + 15, info_y + info_h - 2 * info_font_size - 8, 0)
                blf.draw(font_id, "No bindings found")
        else:
            blf.color(font_id, *COL_TEXT_DIM)
            blf.position(font_id, info_x + 10, info_y + info_h / 2 - info_font_size / 2, 0)
            blf.draw(font_id, "Hover over a key to see its bindings  |  Right-click to edit  |  / to search")

        # --- H. Capture overlay (Phase 5) ---
        if state._modal_state == 'CAPTURE':
            _draw_rect(shader_uniform, 0, 0, rw, rh, COL_CAPTURE_OVERLAY)
            cap_font_size = max(14, int(unit_px * 0.5))
            blf.size(font_id, cap_font_size)
            blf.color(font_id, *COL_CAPTURE_TEXT)
            msg = "Press new key combination..."
            tw, th = blf.dimensions(font_id, msg)
            blf.position(font_id, (rw - tw) / 2, rh / 2 + 10, 0)
            blf.draw(font_id, msg)

            blf.size(font_id, info_font_size)
            blf.color(font_id, *COL_TEXT_DIM)
            sub = "ESC to cancel"
            tw2, th2 = blf.dimensions(font_id, sub)
            blf.position(font_id, (rw - tw2) / 2, rh / 2 - 20, 0)
            blf.draw(font_id, sub)

        # --- I. Conflict resolution overlay (Phase 5) ---
        if state._modal_state == 'CONFLICT':
            _draw_rect(shader_uniform, 0, 0, rw, rh, COL_CAPTURE_OVERLAY)

            # Centered panel
            panel_w = min(500, rw * 0.7)
            panel_h = min(300, rh * 0.5)
            panel_x = (rw - panel_w) / 2
            panel_y = (rh - panel_h) / 2

            _draw_rect(shader_uniform, panel_x, panel_y, panel_w, panel_h, COL_CONFLICT_BG)
            _draw_rect_border(shader_uniform, panel_x, panel_y, panel_w, panel_h, COL_BORDER)

            # Header
            hdr_size = max(14, int(unit_px * 0.4))
            blf.size(font_id, hdr_size)
            blf.color(font_id, *COL_CONFLICT_HEADER)
            hdr_text = "Conflict Detected"
            tw, th = blf.dimensions(font_id, hdr_text)
            blf.position(font_id, panel_x + (panel_w - tw) / 2, panel_y + panel_h - 35, 0)
            blf.draw(font_id, hdr_text)

            # Source binding info
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

            # Conflict list
            blf.color(font_id, *COL_TEXT_DIM)
            conflicts = state._conflict_data.get('conflicts', [])
            for ci, (ckm_name, ckmi) in enumerate(conflicts[:5]):
                cy = panel_y + panel_h - 85 - ci * (info_font_size + 4)
                conflict_line = f"  Conflicts with: {ckmi.idname} ({ckm_name})"
                blf.position(font_id, panel_x + 15, cy, 0)
                blf.draw(font_id, conflict_line)

            # Buttons
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
                bcol = COL_BUTTON_HOVER if bi == state._conflict_hovered_button else COL_BUTTON_NORMAL
                _draw_rect(shader_uniform, bx, btn_y, btn_w, btn_h, bcol)
                _draw_rect_border(shader_uniform, bx, btn_y, btn_w, btn_h, COL_BORDER)
                state._conflict_button_rects.append((blabel, baction, bx, btn_y, btn_w, btn_h))

                blf.size(font_id, info_font_size)
                blf.color(font_id, *colors['text'])
                tw, th = blf.dimensions(font_id, blabel)
                blf.position(font_id, bx + (btn_w - tw) / 2, btn_y + (btn_h - th) / 2, 0)
                blf.draw(font_id, blabel)

        # --- J. GPU-drawn context menu (Phase 5) ---
        if state._modal_state == 'MENU_OPEN' and state._gpu_menu_items:
            # Background + border for entire menu
            if state._gpu_menu_items:
                first = state._gpu_menu_items[0]
                last = state._gpu_menu_items[-1]
                menu_bg_x = first[2] - 3
                menu_bg_y = min(item[3] for item in state._gpu_menu_items) - 3
                menu_bg_w = first[4] + 6
                menu_bg_h = (max(item[3] + item[5] for item in state._gpu_menu_items) - menu_bg_y) + 6

                _draw_rect(shader_uniform, menu_bg_x, menu_bg_y, menu_bg_w, menu_bg_h, COL_GPU_MENU_BG)
                _draw_rect_border(shader_uniform, menu_bg_x, menu_bg_y, menu_bg_w, menu_bg_h,
                                  COL_GPU_MENU_BORDER)

            for mi_idx, (mlabel, maction, mx, my, mw, mh) in enumerate(state._gpu_menu_items):
                mcol = COL_GPU_MENU_HOVER if mi_idx == state._gpu_menu_hovered else COL_GPU_MENU_BG
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
