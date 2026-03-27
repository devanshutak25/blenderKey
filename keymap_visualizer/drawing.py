"""
Keymap Visualizer – GPU drawing helpers and main draw callback
"""

import bpy
import gpu
import blf
import logging
import math
import time
import os
from contextlib import contextmanager
from gpu_extras.batch import batch_for_shader

from . import state
from .state import DirtyFlag
from .profiler import prof

_log = logging.getLogger("keymap_visualizer.drawing")
from dataclasses import dataclass
from .constants import (
    _MODIFIER_EVENTS, MODIFIER_KEY_TO_DICT,
    COL_BG, COL_KEY_DEFAULT, COL_KEY_HOVER, COL_KEY_SELECTED, COL_KEY_MODIFIER,
    COL_KEY_INACTIVE, COL_BORDER, COL_BORDER_HIGHLIGHT, COL_TEXT, COL_TEXT_DIM,
    COL_TOGGLE_ACTIVE, COL_TOGGLE_INACTIVE, COL_INFO_BG,
    COL_CAPTURE_OVERLAY, COL_CAPTURE_TEXT, COL_CONFLICT_BG, COL_CONFLICT_HEADER,
    COL_BUTTON_NORMAL, COL_BUTTON_HOVER, COL_EXPORT_BUTTON, COL_EXPORT_BUTTON_HOVER,
    COL_SHADOW, COL_SEARCH_BG, COL_SEARCH_BORDER,
    COL_GPU_MENU_BG, COL_GPU_MENU_HOVER, COL_GPU_MENU_BORDER,
    COL_KEY_BOUND, SPACE_TYPE_FILTERS, MODE_FILTERS,
    COL_SHORTCUT_SEARCH_TEXT, CATEGORY_COLORS, CATEGORY_TEXT_COLORS,
    OPERATOR_ABBREVIATIONS, OPERATOR_CATEGORIES,
    OPERATOR_CATEGORY_ORDER,
    BASE_ACCENT, BASE_BACKGROUND, BASE_SURFACE, BASE_TEXT,
    BASE_SUCCESS, BASE_WARNING, BASE_DANGER, BASE_INFO,
)

# ---------------------------------------------------------------------------
# Font loading: use bfont.ttf for better Unicode glyph support
# ---------------------------------------------------------------------------
_blender_font_id = 0
_condensed_font_id = 0
_loaded_main_path = ""
_loaded_condensed_path = ""

# ---------------------------------------------------------------------------
# Cached GPU shaders (lazy-init to avoid calling before GPU context ready)
# ---------------------------------------------------------------------------
_shader_uniform = None
_shader_smooth = None


def _get_shader_uniform():
    global _shader_uniform
    if _shader_uniform is None:
        _shader_uniform = gpu.shader.from_builtin('UNIFORM_COLOR')
    return _shader_uniform


def _get_shader_smooth():
    global _shader_smooth
    if _shader_smooth is None:
        _shader_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')
    return _shader_smooth


def _reset_shader_cache():
    global _shader_uniform, _shader_smooth
    _shader_uniform = None
    _shader_smooth = None


# ---------------------------------------------------------------------------
# Pre-allocated key vertex buffers (avoid per-frame list growth)
# ---------------------------------------------------------------------------
_key_verts_buf = None
_key_colors_buf = None
_key_indices_buf = None
_key_buf_count = 0


def _ensure_key_buffers(n_keys):
    global _key_verts_buf, _key_colors_buf, _key_indices_buf, _key_buf_count
    if _key_buf_count == n_keys:
        return
    _key_buf_count = n_keys
    _key_verts_buf = [(0.0, 0.0)] * (n_keys * 4)
    _key_colors_buf = [(0.0, 0.0, 0.0, 0.0)] * (n_keys * 4)
    _key_indices_buf = []
    for i in range(n_keys):
        base = i * 4
        _key_indices_buf.append((base, base + 1, base + 2))
        _key_indices_buf.append((base, base + 2, base + 3))


def _reset_key_buffers():
    global _key_verts_buf, _key_colors_buf, _key_indices_buf, _key_buf_count
    _key_verts_buf = None
    _key_colors_buf = None
    _key_indices_buf = None
    _key_buf_count = 0


def _ensure_font_loaded():
    global _blender_font_id, _condensed_font_id, _loaded_main_path, _loaded_condensed_path

    # Read user prefs
    try:
        prefs = state._get_prefs()
        user_main = prefs.main_font_path
        user_condensed = prefs.condensed_font_path
    except Exception:
        _log.debug("Could not read font preferences, using defaults", exc_info=True)
        user_main = ""
        user_condensed = ""

    # Determine effective main font path
    if user_main and os.path.isfile(bpy.path.abspath(user_main)):
        main_path = bpy.path.abspath(user_main)
    else:
        bfont_dir = os.path.join(bpy.utils.resource_path('LOCAL'), "datafiles", "fonts")
        main_path = os.path.join(bfont_dir, "bfont.ttf")
        if not os.path.exists(main_path):
            main_path = os.path.join(bfont_dir, "bmonofont-i18n.ttf")

    # Determine effective condensed font path
    if user_condensed and os.path.isfile(bpy.path.abspath(user_condensed)):
        condensed_path = bpy.path.abspath(user_condensed)
    else:
        condensed_path = os.path.join(os.path.dirname(__file__), "fonts", "RobotoCondensed-Regular.ttf")

    # Reload main font if path changed or not yet loaded
    if main_path != _loaded_main_path or _blender_font_id == 0:
        if os.path.exists(main_path):
            loaded = blf.load(main_path)
            if loaded != -1:
                _blender_font_id = loaded
                _loaded_main_path = main_path

    # Reload condensed font if path changed or not yet loaded
    if condensed_path != _loaded_condensed_path or _condensed_font_id == 0:
        if os.path.exists(condensed_path):
            loaded = blf.load(condensed_path)
            if loaded != -1:
                _condensed_font_id = loaded
                _loaded_condensed_path = condensed_path

    return _blender_font_id


def _get_condensed_font():
    """Return condensed font ID, falling back to main font."""
    return _condensed_font_id if _condensed_font_id != 0 else _blender_font_id
from .keymap_data import (
    _get_bindings_for_key, _get_all_bindings_for_key, _compute_bound_keys,
    _compute_key_labels, _compute_key_categories, _compute_key_editor_icons,
    _compute_key_modifier_badges, _compute_key_hold_badges,
    _humanize_op_id, _group_bindings,
    _get_operator_description, _compute_diff_keys,
)
from .icons import (
    _load_icons, get_editor_icon, get_mode_icon, get_km_icon,
)
from .layout import _compute_keyboard_layout


def _get_colors():
    """Derive all colors from 8 base tokens, with optional advanced overrides."""
    try:
        prefs = state._get_prefs()
        accent = tuple(prefs.col_accent)
        background = tuple(prefs.col_background)
        surface = tuple(prefs.col_surface)
        text = tuple(prefs.col_text)
        success = tuple(prefs.col_success)
        warning = tuple(prefs.col_warning)
        danger = tuple(prefs.col_danger)
        info = tuple(prefs.col_info)
    except Exception:
        _log.debug("Could not read color preferences, using defaults", exc_info=True)
        accent = BASE_ACCENT
        background = BASE_BACKGROUND
        surface = BASE_SURFACE
        text = BASE_TEXT
        success = BASE_SUCCESS
        warning = BASE_WARNING
        danger = BASE_DANGER
        info = BASE_INFO

    # Helper: scale color channels by factor
    def _scale(c, f):
        return (min(1.0, c[0] * f), min(1.0, c[1] * f), min(1.0, c[2] * f), c[3])

    def _add_lightness(c, d):
        return (min(1.0, c[0] + d), min(1.0, c[1] + d), min(1.0, c[2] + d), c[3])

    # Derive all colors from base tokens
    colors = {
        # Keys
        'key_default': surface,
        'key_selected': accent,
        'key_hovered': _lerp_color(surface, accent, 0.4),
        'key_bound': _lerp_color(surface, accent, 0.15),
        'key_modifier': (min(1.0, surface[0] + 0.05), min(1.0, surface[1] + 0.03),
                         max(0.0, surface[2] - 0.03), 1.0),
        'key_inactive': _scale(surface, 0.72),
        # General UI
        'background': background,
        'text': text,
        'text_dim': _scale(text, 0.80),
        'panel_bg': _add_lightness(background, 0.03),
        'info_panel_bg': _add_lightness(background, 0.06),
        'shadow': (0.0, 0.0, 0.0, 0.3),
        # Borders
        'border': _add_lightness(surface, 0.15),
        'border_highlight': _lerp_color(accent, (1.0, 1.0, 1.0, 1.0), 0.5),
        # Toggles
        'toggle_active': accent,
        'toggle_inactive': _scale(surface, 0.88),
        # Buttons
        'button_normal': _scale(surface, 1.15),
        'button_hover': _lerp_color(surface, accent, 0.45),
        'export_button': success,
        'export_button_hover': _scale(success, 1.30),
        # Search
        'search_bg': _add_lightness(background, 0.06),
        'search_border': _scale(accent, 0.70),
        # Menu
        'menu_bg': _add_lightness(background, 0.03),
        'menu_hover': _lerp_color(surface, accent, 0.35),
        'menu_border': _add_lightness(surface, 0.15),
        # Overlays
        'capture_overlay': (0.0, 0.0, 0.0, 0.6),
        'capture_text': warning,
        'conflict_bg': _add_lightness(background, -0.02),
        'conflict_header': danger,
        'shortcut_search_text': info,
        # Additional UI
        'active_highlight': _lerp_color(surface, accent, 0.2),
        'text_inactive': (0.55, 0.55, 0.55, 1.0),
        'badge_text': _scale(text, 0.85),
        # Category colors (from prefs)
        'cat_transform': CATEGORY_COLORS.get("Transform", surface),
        'cat_navigation': CATEGORY_COLORS.get("Navigation", surface),
        'cat_mesh': CATEGORY_COLORS.get("Mesh", surface),
        'cat_object': CATEGORY_COLORS.get("Object", surface),
        'cat_playback': CATEGORY_COLORS.get("Playback", surface),
        'cat_animation': CATEGORY_COLORS.get("Animation", surface),
        'cat_nodes': CATEGORY_COLORS.get("Nodes", surface),
        'cat_uv': CATEGORY_COLORS.get("UV", surface),
        'cat_sculpt': CATEGORY_COLORS.get("Sculpt", surface),
        'cat_paint': CATEGORY_COLORS.get("Paint", surface),
        'cat_system': CATEGORY_COLORS.get("System", surface),
        'cat_edit': CATEGORY_COLORS.get("Edit", surface),
        'cat_file': CATEGORY_COLORS.get("File", surface),
    }

    # Apply category colors from prefs
    try:
        prefs = state._get_prefs()
        colors['cat_transform'] = tuple(prefs.col_cat_transform)
        colors['cat_navigation'] = tuple(prefs.col_cat_navigation)
        colors['cat_mesh'] = tuple(prefs.col_cat_mesh)
        colors['cat_object'] = tuple(prefs.col_cat_object)
        colors['cat_playback'] = tuple(prefs.col_cat_playback)
        colors['cat_animation'] = tuple(prefs.col_cat_animation)
        colors['cat_nodes'] = tuple(prefs.col_cat_nodes)
        colors['cat_uv'] = tuple(prefs.col_cat_uv)
        colors['cat_sculpt'] = tuple(prefs.col_cat_sculpt)
        colors['cat_paint'] = tuple(prefs.col_cat_paint)
        colors['cat_system'] = tuple(prefs.col_cat_system)
        colors['cat_edit'] = tuple(prefs.col_cat_edit)
        colors['cat_file'] = tuple(prefs.col_cat_file)
    except Exception:
        _log.debug("Could not read category color preferences", exc_info=True)

    # Apply advanced overrides from prefs
    _OVERRIDE_MAP = {
        'key_default': ('use_key_unbound_override', 'col_key_unbound'),
        'key_selected': ('use_key_selected_override', 'col_key_selected'),
        'key_hovered': ('use_key_hovered_override', 'col_key_hovered'),
        'key_bound': ('use_key_bound_override', 'col_key_bound'),
        'key_modifier': ('use_key_modifier_override', 'col_key_modifier'),
        'text_dim': ('use_text_dim_override', 'col_text_dim'),
        'panel_bg': ('use_panel_bg_override', 'col_panel_bg'),
        'shadow': ('use_shadow_override', 'col_shadow'),
        'border': ('use_border_override', 'col_border'),
        'border_highlight': ('use_border_highlight_override', 'col_border_highlight'),
        'toggle_active': ('use_toggle_active_override', 'col_toggle_active'),
        'toggle_inactive': ('use_toggle_inactive_override', 'col_toggle_inactive'),
        'button_normal': ('use_button_normal_override', 'col_button_normal'),
        'button_hover': ('use_button_hover_override', 'col_button_hover'),
        'export_button': ('use_export_button_override', 'col_export_button'),
        'export_button_hover': ('use_export_button_hover_override', 'col_export_button_hover'),
        'search_bg': ('use_search_bg_override', 'col_search_bg'),
        'search_border': ('use_search_border_override', 'col_search_border'),
        'menu_bg': ('use_menu_bg_override', 'col_menu_bg'),
        'menu_hover': ('use_menu_hover_override', 'col_menu_hover'),
        'menu_border': ('use_menu_border_override', 'col_menu_border'),
        'capture_overlay': ('use_capture_overlay_override', 'col_capture_overlay'),
        'capture_text': ('use_capture_text_override', 'col_capture_text'),
        'conflict_bg': ('use_conflict_bg_override', 'col_conflict_bg'),
        'conflict_header': ('use_conflict_header_override', 'col_conflict_header'),
        'shortcut_search_text': ('use_shortcut_search_text_override', 'col_shortcut_search_text'),
        'active_highlight': ('use_active_highlight_override', 'col_active_highlight'),
        'text_inactive': ('use_text_inactive_override', 'col_text_inactive'),
        'badge_text': ('use_badge_text_override', 'col_badge_text'),
    }
    try:
        prefs = state._get_prefs()
        for color_key, (use_prop, col_prop) in _OVERRIDE_MAP.items():
            if getattr(prefs, use_prop, False):
                colors[color_key] = tuple(getattr(prefs, col_prop))
    except Exception:
        _log.debug("Could not read advanced color overrides", exc_info=True)

    return colors


def _get_category_colors_enabled():
    """Check if category colors are enabled in preferences."""
    try:
        prefs = state._get_prefs()
        return prefs.enable_category_colors
    except Exception:
        _log.debug("Could not read enable_category_colors preference")
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


# ---------------------------------------------------------------------------
# Batched rectangle rendering – collects rects and draws them in one GPU call
# ---------------------------------------------------------------------------

class RectBatcher:
    """Accumulates filled rectangles and draws them in a single GPU batch."""
    __slots__ = ('_verts', '_colors', '_indices', '_idx')

    def __init__(self):
        self._verts = []
        self._colors = []
        self._indices = []
        self._idx = 0

    def add(self, x, y, w, h, color):
        i = self._idx
        self._verts.extend(((x, y), (x + w, y), (x + w, y + h), (x, y + h)))
        self._colors.extend((color, color, color, color))
        self._indices.extend(((i, i + 1, i + 2), (i, i + 2, i + 3)))
        self._idx += 4

    def flush(self, shader_smooth):
        if not self._verts:
            return
        batch = batch_for_shader(shader_smooth, 'TRIS',
                                 {"pos": self._verts, "color": self._colors},
                                 indices=self._indices)
        shader_smooth.bind()
        batch.draw(shader_smooth)
        self._verts.clear()
        self._colors.clear()
        self._indices.clear()
        self._idx = 0


class LineBatcher:
    """Accumulates rectangle borders and draws them in a single GPU batch."""
    __slots__ = ('_verts', '_colors', '_indices', '_idx')

    def __init__(self):
        self._verts = []
        self._colors = []
        self._indices = []
        self._idx = 0

    def add(self, x, y, w, h, color):
        i = self._idx
        self._verts.extend(((x, y), (x + w, y), (x + w, y + h), (x, y + h)))
        self._colors.extend((color, color, color, color))
        self._indices.extend(((i, i + 1), (i + 1, i + 2), (i + 2, i + 3), (i + 3, i)))
        self._idx += 4

    def flush(self, shader_smooth):
        if not self._verts:
            return
        batch = batch_for_shader(shader_smooth, 'LINES',
                                 {"pos": self._verts, "color": self._colors},
                                 indices=self._indices)
        shader_smooth.bind()
        batch.draw(shader_smooth)
        self._verts.clear()
        self._colors.clear()
        self._indices.clear()
        self._idx = 0


def _draw_rect(shader, x, y, w, h, color):
    """Draw a filled rectangle (immediate mode – prefer RectBatcher for batching)."""
    verts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    batch = batch_for_shader(shader, 'TRIS', {"pos": verts}, indices=[(0, 1, 2), (0, 2, 3)])
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_rect_border(shader, x, y, w, h, color):
    """Draw a rectangle border (immediate mode – prefer LineBatcher for batching)."""
    verts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    batch = batch_for_shader(shader, 'LINES', {"pos": verts},
                             indices=[(0, 1), (1, 2), (2, 3), (3, 0)])
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _luminance(color):
    """Compute relative luminance of an RGB(A) color (sRGB approximation)."""
    r, g, b = color[0], color[1], color[2]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrasting_text_color(bg_color, light=(1.0, 1.0, 1.0, 1.0), dark=(0.05, 0.05, 0.05, 1.0)):
    """Return light or dark text color based on background luminance for WCAG contrast."""
    return dark if _luminance(bg_color) > 0.35 else light


_shader_image = None


def _get_shader_image():
    global _shader_image
    if _shader_image is None:
        _shader_image = gpu.shader.from_builtin('IMAGE')
    return _shader_image


class IconBatcher:
    """Accumulates textured icon quads and draws them in a single GPU call using the atlas."""
    __slots__ = ('_verts', '_uvs', '_indices', '_idx', '_atlas_tex')

    def __init__(self):
        self._verts = []
        self._uvs = []
        self._indices = []
        self._idx = 0
        self._atlas_tex = None

    def add(self, icon_info, x, y, size):
        """Add an icon. icon_info = (atlas_tex, u0, v0, u1, v1) or None."""
        if icon_info is None:
            return
        atlas_tex, u0, v0, u1, v1 = icon_info
        self._atlas_tex = atlas_tex
        i = self._idx
        self._verts.extend(((x, y), (x + size, y), (x + size, y + size), (x, y + size)))
        self._uvs.extend(((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
        self._indices.extend(((i, i + 1, i + 2), (i, i + 2, i + 3)))
        self._idx += 4

    def flush(self):
        if not self._verts or self._atlas_tex is None:
            return
        shader = _get_shader_image()
        batch = batch_for_shader(shader, 'TRIS',
                                 {"pos": self._verts, "texCoord": self._uvs},
                                 indices=self._indices)
        shader.bind()
        shader.uniform_sampler("image", self._atlas_tex)
        batch.draw(shader)
        self._verts.clear()
        self._uvs.clear()
        self._indices.clear()
        self._idx = 0


def _draw_icon(icon_info, x, y, size):
    """Draw a single icon immediately. icon_info = (atlas_tex, u0, v0, u1, v1) or None.
    Prefer IconBatcher for batched rendering."""
    if icon_info is None:
        return
    try:
        atlas_tex, u0, v0, u1, v1 = icon_info
        shader = _get_shader_image()
        coords = ((x, y), (x + size, y), (x + size, y + size), (x, y + size))
        uvs = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
        batch = batch_for_shader(shader, 'TRIS',
                                 {"pos": coords, "texCoord": uvs},
                                 indices=((0, 1, 2), (0, 2, 3)))
        shader.bind()
        shader.uniform_sampler("image", atlas_tex)
        batch.draw(shader)
    except Exception:
        _log.debug("Icon draw failed", exc_info=True)


@contextmanager
def _scissor_clip(x, y, w, h):
    """Enable GPU scissor test to clip drawing to a rectangle."""
    gpu.state.scissor_test_set(True)
    gpu.state.scissor_set(int(x), int(y), int(w), int(h))
    try:
        yield
    finally:
        gpu.state.scissor_test_set(False)


def _truncate_text(font_id, text, max_width):
    """Truncate text to fit within max_width, adding '\u2026' if needed.
    Uses binary search for efficiency. Returns (display_text, tw, th).
    Results are cached per (text, max_width, font_id) to avoid repeated blf.dimensions() calls."""
    if not text or max_width <= 0:
        return "", 0, 0
    # Check truncation cache
    cache_key = (text, int(max_width), font_id)
    cached = state._truncation_cache.get(cache_key)
    if cached is not None:
        return cached
    tw, th = blf.dimensions(font_id, text)
    if tw <= max_width:
        result = (text, tw, th)
        state._truncation_cache[cache_key] = result
        return result
    ellipsis = "\u2026"
    lo, hi = 1, len(text) - 1
    best = 1
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = text[:mid] + ellipsis
        cw, _ = blf.dimensions(font_id, candidate)
        if cw <= max_width:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    display = text[:best] + ellipsis
    tw, th = blf.dimensions(font_id, display)
    result = (display, tw, th)
    state._truncation_cache[cache_key] = result
    return result


def _draw_scrollbar(shader, x, y, h, scroll_offset, max_scroll, content_h, visible_h,
                     track_w=10, track_color=None, thumb_color=None):
    """Draw a vertical scrollbar track and thumb."""
    if track_color is None:
        track_color = (0.25, 0.25, 0.25, 0.6)
    if thumb_color is None:
        thumb_color = (0.7, 0.7, 0.7, 0.85)
    _draw_rect(shader, x, y, track_w, h, track_color)
    visible_ratio = visible_h / content_h
    thumb_h = max(15, h * visible_ratio)
    scroll_ratio = scroll_offset / max_scroll if max_scroll > 0 else 0
    thumb_y = y + h - thumb_h - scroll_ratio * (h - thumb_h)
    _draw_rect(shader, x, thumb_y, track_w, thumb_h, thumb_color)


def _draw_fade_gradient(shader_smooth, x1, x2, y, fade_h, bg_color, direction):
    """Draw a fade gradient. direction='DOWN': opaque top -> transparent bottom.
    direction='UP': transparent top -> opaque bottom."""
    bg_t = (bg_color[0], bg_color[1], bg_color[2], 0.0)
    fade_verts = [
        (x1, y + fade_h), (x2, y + fade_h),
        (x2, y), (x1, y),
    ]
    if direction == 'DOWN':
        fade_colors = [bg_color, bg_color, bg_t, bg_t]
    else:  # 'UP'
        fade_colors = [bg_t, bg_t, bg_color, bg_color]
    fb = batch_for_shader(shader_smooth, 'TRIS',
        {"pos": fade_verts, "color": fade_colors},
        indices=[(0, 1, 2), (0, 2, 3)])
    shader_smooth.bind()
    fb.draw(shader_smooth)


def _draw_panel(shader, x, y, w, h, bg_color, border_color):
    """Draw a panel with background fill and border."""
    _draw_rect(shader, x, y, w, h, bg_color)
    _draw_rect_border(shader, x, y, w, h, border_color)


def _draw_centered_overlay(shader, font_id, rw, rh, unit_px, info_font_size, colors,
                           main_text, main_color_key, sub_text=None):
    """Draw a fullscreen overlay with centered main text and optional subtitle."""
    _draw_rect(shader, 0, 0, rw, rh, colors['capture_overlay'])
    cap_font_size = max(15, int(unit_px * 0.5))
    blf.size(font_id, cap_font_size)
    blf.color(font_id, *colors[main_color_key])
    tw, th = blf.dimensions(font_id, main_text)
    blf.position(font_id, (rw - tw) / 2, rh / 2 + max(8, int(unit_px * 0.13)), 0)
    blf.draw(font_id, main_text)
    if sub_text:
        blf.size(font_id, info_font_size)
        blf.color(font_id, *colors['text_dim'])
        tw2, th2 = blf.dimensions(font_id, sub_text)
        blf.position(font_id, (rw - tw2) / 2, rh / 2 - max(10, int(unit_px * 0.20)), 0)
        blf.draw(font_id, sub_text)


def _lerp_color(a, b, t):
    """Linearly interpolate between two RGBA colors."""
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))


@dataclass
class Spacing:
    sp1: int    # tiny (0.02u)
    sp2: int    # small (0.04u)
    sp3: int    # medium (0.06u)
    sp4: int    # standard (0.08u)
    sp5: int    # large (0.13u)
    sp6: int    # panel (0.20u)
    pad: int    # plate (0.25u)
    track_w: int  # scrollbar width
    item_h: int   # normal item height
    item_h_sm: int  # compact item height


def _compute_spacing(unit_px):
    return Spacing(
        sp1=max(1, int(unit_px * 0.02)),
        sp2=max(2, int(unit_px * 0.04)),
        sp3=max(3, int(unit_px * 0.06)),
        sp4=max(5, int(unit_px * 0.08)),
        sp5=max(8, int(unit_px * 0.13)),
        sp6=max(10, int(unit_px * 0.20)),
        pad=max(10, int(unit_px * 0.25)),
        track_w=max(8, int(unit_px * 0.15)),
        item_h=max(22, int(unit_px * 0.45)),
        item_h_sm=max(16, int(unit_px * 0.35)),
    )


def _get_filter_summary(filter_type):
    """Get a summary label for current filter selections."""
    if filter_type == 'EDITOR':
        if 'ALL' in state._filter_space_types:
            return "All Editors"
        labels = []
        for value, label in SPACE_TYPE_FILTERS:
            if value in state._filter_space_types:
                labels.append(label)
        return ", ".join(labels) if labels else "All Editors"
    else:
        if 'ALL' in state._filter_modes:
            return "All Modes"
        labels = []
        for value, label in MODE_FILTERS:
            if value in state._filter_modes:
                labels.append(label)
        return ", ".join(labels) if labels else "All Modes"
def _get_category_for_op(op_id):
    """Get category name for an operator id from OPERATOR_CATEGORIES."""
    for prefix, cat in OPERATOR_CATEGORIES.items():
        if op_id.startswith(prefix):
            return cat
    return "Other"


def _build_humanized_label(op_id, mod_str):
    """Build humanized label: '{mod_prefix}{abbrev} [{category}]'."""
    # Get abbreviation
    if op_id in OPERATOR_ABBREVIATIONS:
        abbrev = OPERATOR_ABBREVIATIONS[op_id]
    else:
        abbrev = _humanize_op_id(op_id)

    category = _get_category_for_op(op_id)

    if mod_str:
        return f"{mod_str} + {abbrev} [{category}]"
    return f"{abbrev} [{category}]"


def _build_gpu_menu(mx, my, region_width, region_height, bindings=None):
    """Build GPU-drawn context menu items at mouse position.

    Main menu shows humanized operator names. Flyout sub-menus show actions.
    Menu item tuple: (label, binding_index, x, y, w, h, is_active) — 7-tuple.
    """
    state._gpu_menu_items = []
    state._gpu_menu_hovered = -1
    state._gpu_flyout_items.clear()
    state._gpu_flyout_hovered = -1
    state._flyout_target_index = -1
    state._flyout_hover_timer = 0.0

    if bindings is None:
        return

    # Compute unit_px to match _draw_callback's scaled spacing
    rw, rh = state._cached_region_size
    if rw > 0 and rh > 0:
        unit_from_w = rw / 24
        unit_from_h = rh / 12
        unit_px = min(unit_from_w, unit_from_h) * state._user_scale
    else:
        unit_px = 40

    s = _compute_spacing(unit_px)
    item_h = s.item_h
    padding = s.sp1
    icon_size = int(item_h * 0.7)
    menu_font_size = max(11, int(unit_px * 0.28))

    # Build labels and measure widths
    font_id = _ensure_font_loaded()
    blf.size(font_id, menu_font_size)

    labels = []
    max_bindings = min(len(bindings), 5)
    max_text_w = 0.0
    for bi in range(max_bindings):
        km_name, op_id, mod_str, kmi, is_active = bindings[bi][:5]
        label = _build_humanized_label(op_id, mod_str)
        tw, _ = blf.dimensions(font_id, label)
        if tw > max_text_w:
            max_text_w = tw
        labels.append((label, bi, is_active))

    if not labels:
        return

    menu_width = int(icon_size + s.sp5 + max_text_w + s.sp5 * 2)
    menu_width = max(menu_width, max(120, int(unit_px * 2.0)))
    flyout_est_width = 160  # estimated flyout width for overflow check

    total_h = len(labels) * (item_h + padding) + padding

    # Position menu; shift left if flyout would overflow right edge
    menu_x = mx
    if menu_x + menu_width + flyout_est_width > region_width:
        menu_x = region_width - menu_width - flyout_est_width - 5
    if menu_x < 5:
        menu_x = 5
    if menu_x + menu_width > region_width:
        menu_x = region_width - menu_width - 5

    menu_y = my - total_h
    if menu_y < 5:
        menu_y = my + 5

    current_y = my
    going_down = menu_y <= my
    if not going_down:
        current_y = menu_y

    for label, bi, is_active in labels:
        if going_down:
            current_y -= (item_h + padding)
            iy = current_y
        else:
            iy = current_y
            current_y += item_h + padding
        state._gpu_menu_items.append((label, bi, menu_x, iy, menu_width, item_h, is_active))


def _build_flyout(main_item_index):
    """Build flyout sub-menu for a main menu item."""
    state._gpu_flyout_items.clear()
    state._gpu_flyout_hovered = -1

    if main_item_index < 0 or main_item_index >= len(state._gpu_menu_items):
        return

    main_item = state._gpu_menu_items[main_item_index]
    label, binding_index, mx, my, mw, mh, is_active = main_item

    all_bindings = state._menu_context.get('all_bindings', [])
    if binding_index < 0 or binding_index >= len(all_bindings):
        return

    # Build action items
    actions = [("Rebind", "REBIND")]
    if is_active:
        actions.append(("Unbind", "UNBIND"))
    else:
        actions.append(("Enable", "TOGGLE"))
    actions.append(("Reset to Default", "RESET"))
    actions.append(("Toggle On/Off", "TOGGLE"))

    # Compute scaled spacing to match _draw_callback
    rw, rh = state._cached_region_size
    if rw > 0 and rh > 0:
        unit_from_w = rw / 24
        unit_from_h = rh / 12
        unit_px = min(unit_from_w, unit_from_h) * state._user_scale
    else:
        unit_px = 40
    s = _compute_spacing(unit_px)
    sp2 = s.sp2
    sp5 = s.sp5
    info_font_size = max(11, int(unit_px * 0.28))
    action_font_size = max(10, int(info_font_size * 0.9))

    # Measure text widths
    font_id = _ensure_font_loaded()
    action_h = s.item_h_sm
    padding = s.sp1
    blf.size(font_id, action_font_size)

    max_tw = 0.0
    for alabel, _ in actions:
        tw, _ = blf.dimensions(font_id, alabel)
        if tw > max_tw:
            max_tw = tw

    flyout_w = int(max_tw + sp5 * 4)
    flyout_w = max(flyout_w, 120)

    # Position to the right of main menu item, vertically aligned
    flyout_x = mx + mw + 2
    flyout_y = my + mh  # start from top of main item

    for i, (alabel, aaction) in enumerate(actions):
        iy = flyout_y - (i + 1) * (action_h + padding)
        state._gpu_flyout_items.append((alabel, aaction, flyout_x, iy, flyout_w, action_h, binding_index))


def _build_preset_dropdown(button_rect, region_width, region_height):
    """Build dropdown rects for the presets button."""
    from .presets import _list_presets

    state._preset_dropdown_rects = []
    state._preset_dropdown_hovered = -1

    presets = _list_presets()
    bx, by, bw, bh = button_rect

    # Compute unit_px for scaled sizing
    rw, rh = state._cached_region_size
    if rw > 0 and rh > 0:
        _upx = min(rw / 24, rh / 12) * state._user_scale
    else:
        _upx = 40
    _s = _compute_spacing(_upx)
    item_h = _s.item_h_sm
    item_w = max(bw, max(180, int(_upx * 2.0)))
    padding = _s.sp1

    # Build items: presets + Save As + Delete
    items = []
    for name in presets:
        items.append((name, f"LOAD:{name}"))
    items.append(("Save As\u2026", "SAVE_AS"))
    if state._active_preset_name:
        items.append((f"Delete '{state._active_preset_name}'", "DELETE"))
    if state._active_preset_name:
        items.append(("Copy to Clipboard", "COPY_CLIPBOARD"))
    items.append(("Paste from Clipboard", "PASTE_CLIPBOARD"))

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


def _draw_filter_lists(ctx):
    """Draw the Editor and Mode filter list panels below the keyboard (batched).
    All geometry for both panels is collected first, flushed once, then text is drawn."""
    font_id = ctx.font_id
    colors = ctx.colors
    unit_px = ctx.unit_px
    s = ctx.s
    shader_smooth = ctx.shader_smooth
    rb = ctx.rb
    lb = ctx.lb
    ib = ctx.ib
    list_font_size = max(10, int(unit_px * 0.22))
    sp1, sp2, sp4, sp6 = s.sp1, s.sp2, s.sp4, s.sp6

    # Phase 1: Collect ALL geometry for both panels
    panels_data = []  # [(panel_rect, header_text, visible_items, has_scrollbar, scroll_info, content_top_y)]
    for panel_rect, item_rects, selected_set, hovered_idx, header_text, is_editor in [
        (state._filter_editor_list_rect, state._filter_editor_list_rects,
         state._filter_space_types, state._filter_editor_hovered, "Editors", True),
        (state._filter_mode_list_rect, state._filter_mode_list_rects,
         state._filter_modes, state._filter_mode_hovered, "Modes", False),
    ]:
        if panel_rect is None:
            continue
        px, py, pw, ph = panel_rect
        scroll_offset = state._filter_editor_scroll if is_editor else state._filter_mode_scroll
        soft_border = (colors['border'][0], colors['border'][1], colors['border'][2], colors['border'][3] * 0.5)
        rb.add(px, py, pw, ph, colors['panel_bg'])
        lb.add(px, py, pw, ph, soft_border)

        if (is_editor and state._nav_focus == 'EDITOR_LIST') or (not is_editor and state._nav_focus == 'MODE_LIST'):
            lb.add(px, py, pw, ph, colors['border_highlight'])

        header_h = max(16, unit_px * 0.35)

        if not item_rects:
            panels_data.append((panel_rect, header_text, [], False, None, 0, True))
            continue

        content_top_y = py + ph - header_h
        item_h = max(20, unit_px * 0.5)
        total_content_h = len(item_rects) * item_h + header_h
        has_scrollbar = total_content_h > ph
        max_scroll = (total_content_h - ph) if has_scrollbar else 0

        visible_items = []
        for di, (dlabel, dvalue, dx, dy, dw, dh) in enumerate(item_rects):
            actual_y = dy + scroll_offset
            if actual_y + dh <= py or actual_y >= content_top_y:
                continue
            is_selected = dvalue in selected_set
            is_hovered = (di == hovered_idx)
            if is_hovered:
                dcol = colors['menu_hover']
            elif is_selected:
                dcol = colors['active_highlight']
            else:
                dcol = colors['panel_bg']
            rb.add(dx, actual_y, dw, dh, dcol)
            visible_items.append((dlabel, dvalue, dx, actual_y, dw, dh, is_editor))

        if has_scrollbar:
            track_w = s.track_w
            track_x = px + pw - track_w - sp1
            track_color = _lerp_color(colors['panel_bg'], colors['border'], 0.3)
            rb.add(track_x, py, track_w, ph, track_color)
            visible_ratio = ph / total_content_h
            thumb_h = max(15, ph * visible_ratio)
            scroll_ratio = scroll_offset / max_scroll if max_scroll > 0 else 0
            thumb_y = py + ph - thumb_h - scroll_ratio * (ph - thumb_h)
            rb.add(track_x, thumb_y, track_w, thumb_h, colors['text_dim'])

        panels_data.append((panel_rect, header_text, visible_items, has_scrollbar,
                           (scroll_offset, max_scroll), content_top_y, False))

    # ONE flush for ALL rects + borders across both panels
    rb.flush(shader_smooth)
    lb.flush(shader_smooth)

    # Phase 2: Draw text + icons per panel (with scissor clips)
    for panel_rect, header_text, visible_items, has_scrollbar, scroll_info, content_top_y, is_empty in panels_data:
        px, py, pw, ph = panel_rect

        if is_empty:
            blf.size(font_id, list_font_size)
            blf.color(font_id, *colors['text_dim'])
            no_items = "No matches"
            tw_e, th_e = blf.dimensions(font_id, no_items)
            blf.position(font_id, px + (pw - tw_e) / 2, py + ph / 2 - th_e / 2, 0)
            blf.draw(font_id, no_items)
            continue

        header_h = max(16, unit_px * 0.35)
        with _scissor_clip(px, py, pw, int(content_top_y - py)):
            if unit_px >= 20:
                blf.size(font_id, list_font_size)
                blf.color(font_id, *colors['text'])
                tw, th = blf.dimensions(font_id, header_text)
                blf.position(font_id, px + (pw - tw) / 2, py + ph - list_font_size - sp2, 0)
                blf.draw(font_id, header_text)

                for dlabel, dvalue, dx, actual_y, dw, dh, is_ed in visible_items:
                    blf.color(font_id, *colors['text'])
                    icon_info = get_editor_icon(dvalue) if is_ed else get_mode_icon(dvalue)
                    icon_size = int(dh * 0.65)
                    icon_x = dx + sp2
                    icon_y = actual_y + (dh - icon_size) / 2
                    ib.add(icon_info, icon_x, icon_y, icon_size)
                    text_x = icon_x + icon_size + sp2 if icon_info else dx + sp4
                    avail_w = dw - (text_x - dx) - sp2
                    display, tw, th = _truncate_text(font_id, dlabel, avail_w)
                    blf.position(font_id, text_x, actual_y + (dh - th) / 2, 0)
                    blf.draw(font_id, display)
                ib.flush()

            if has_scrollbar:
                scroll_offset, max_scroll = scroll_info
                fade_h = sp6
                fade_x2 = px + pw - s.track_w - sp2
                if scroll_offset > 0:
                    _draw_fade_gradient(shader_smooth, px, fade_x2,
                                        content_top_y - fade_h, fade_h, colors['panel_bg'], 'DOWN')
                if scroll_offset < max_scroll:
                    _draw_fade_gradient(shader_smooth, px, fade_x2,
                                        py, fade_h, colors['panel_bg'], 'UP')


def _draw_operator_list(ctx):
    """Draw the Operators accordion panel below the keyboard (batched)."""
    from .keymap_data import _collect_all_operators, _compute_bound_operators

    if state._dirty_flags & DirtyFlag.OPERATOR_LIST:
        _collect_all_operators()
    _compute_bound_operators()

    panel_rect = state._operator_list_rect
    if panel_rect is None:
        return

    px, py, pw, ph = panel_rect

    shader_uniform = ctx.shader_uniform
    shader_smooth = ctx.shader_smooth
    font_id = ctx.font_id
    colors = ctx.colors
    unit_px = ctx.unit_px
    s = ctx.s
    rb = ctx.rb
    lb = ctx.lb
    list_font_size = max(10, int(unit_px * 0.22))
    sp1 = s.sp1
    sp2 = s.sp2
    sp3 = s.sp3
    sp4 = s.sp4
    sp5 = s.sp5

    # Panel background (softened border) — batched
    soft_border = (colors['border'][0], colors['border'][1], colors['border'][2], colors['border'][3] * 0.5)
    rb.add(px, py, pw, ph, colors['panel_bg'])
    lb.add(px, py, pw, ph, soft_border)

    if state._nav_focus == 'OPERATOR_LIST':
        lb.add(px, py, pw, ph, colors['border_highlight'])

    header_h = max(16, unit_px * 0.35)
    search_h = s.item_h
    item_h = s.item_h_sm
    group_h = s.item_h
    indent = sp5

    # Search box — batched
    search_y = py + ph - header_h - search_h - sp1
    search_x = px + sp2
    search_w = pw - sp2 * 2
    inactive_search_bg = (colors['search_bg'][0], colors['search_bg'][1], colors['search_bg'][2], 0.7)
    search_bg = colors['search_bg'] if state._operator_list_search_active else inactive_search_bg
    rb.add(search_x, search_y, search_w, search_h, search_bg)
    lb.add(search_x, search_y, search_w, search_h,
           colors['search_border'] if state._operator_list_search_active else colors['border'])

    # Content area
    content_top = search_y - sp1
    content_bottom = py + sp1
    content_h = content_top - content_bottom
    if content_h <= 0:
        return

    # Clear rects for this frame
    state._operator_list_group_rects = []
    state._operator_list_item_rects = []

    search_query = state._operator_list_search_text.lower()
    scroll_offset = state._operator_list_scroll

    # Pre-filter operators once for both height calculation and rendering
    filtered_cats = []
    total_h = 0
    for category in OPERATOR_CATEGORY_ORDER:
        ops = state._operator_list_categories.get(category, [])
        if search_query:
            ops = [(oid, name) for oid, name in ops if search_query in name.lower() or search_query in oid.lower()]
        if not ops:
            continue
        is_expanded = category in state._operator_list_expanded or bool(search_query)
        filtered_cats.append((category, ops, is_expanded))
        total_h += group_h
        if is_expanded:
            total_h += len(ops) * item_h

    max_scroll = max(0, total_h - content_h)
    state._operator_list_max_scroll = max_scroll
    state._operator_list_scroll = max(0, min(state._operator_list_scroll, max_scroll))
    scroll_offset = state._operator_list_scroll

    # Pre-compute item font size once
    item_font_size = max(9, int(unit_px * 0.18))
    dot_size = max(4, int(unit_px * 0.08))

    # Pass 1: Collect all rects + build text draw list
    cursor_y = content_top
    cat_text_draws = []   # (cat_text, cat_text_color, gy, group_h)
    item_text_draws = []  # (human_name, text_x, iy, item_h)

    for category, ops, is_expanded in filtered_cats:
        gy = cursor_y - group_h + scroll_offset
        if content_bottom <= gy + group_h and gy <= content_top:
            cat_bg_color = CATEGORY_COLORS.get(category, colors['text_dim'])
            cat_text_color = CATEGORY_TEXT_COLORS.get(category, colors['text_dim'])
            rb.add(px + sp1, gy, sp2, group_h, cat_bg_color)

            group_idx = len(state._operator_list_group_rects)
            if group_idx == state._operator_list_hovered_group:
                rb.add(px + sp3, gy, pw - sp3 * 2, group_h, colors['menu_hover'])

            if unit_px >= 20:
                arrow = "\u25BE" if is_expanded else "\u25B8"
                cat_text = f"{arrow} {category} ({len(ops)})"
                cat_text_draws.append((cat_text, cat_text_color, gy, group_h))

        state._operator_list_group_rects.append((category, px, cursor_y - group_h, pw, group_h))
        cursor_y -= group_h

        if is_expanded:
            for op_id, human_name in ops:
                iy = cursor_y - item_h + scroll_offset
                if content_bottom <= iy + item_h and iy <= content_top:
                    item_idx = len(state._operator_list_item_rects)
                    if item_idx == state._operator_list_hovered_item:
                        rb.add(px + indent, iy, pw - indent - sp2, item_h, colors['menu_hover'])

                    if unit_px >= 20:
                        is_bound = op_id in state._operator_list_bound_ops
                        if is_bound:
                            dot_x = px + indent
                            dot_y = iy + (item_h - dot_size) / 2
                            rb.add(dot_x, dot_y, dot_size, dot_size, colors['active_highlight'])
                            text_x = dot_x + dot_size + sp2
                        else:
                            text_x = px + indent + dot_size + sp2
                        item_text_draws.append((human_name, text_x, iy, item_h))

                state._operator_list_item_rects.append((op_id, human_name, px + indent, cursor_y - item_h, pw - indent - sp2, item_h))
                cursor_y -= item_h

    # Scrollbar rects (batched)
    has_scrollbar = max_scroll > 0 and total_h > 0
    if has_scrollbar:
        track_w = s.track_w
        track_x = px + pw - track_w - sp1
        track_color = _lerp_color(colors['panel_bg'], colors['border'], 0.3)
        rb.add(track_x, int(content_bottom), track_w, content_h, track_color)
        visible_ratio = content_h / total_h
        thumb_h = max(15, content_h * visible_ratio)
        scroll_ratio = scroll_offset / max_scroll if max_scroll > 0 else 0
        thumb_y = int(content_bottom) + content_h - thumb_h - scroll_ratio * (content_h - thumb_h)
        rb.add(track_x, thumb_y, track_w, thumb_h, colors['text_dim'])

    # Single flush for ALL rects + borders
    rb.flush(shader_smooth)
    lb.flush(shader_smooth)

    # Header text (outside scissor — above content area)
    if unit_px >= 20:
        blf.size(font_id, list_font_size)
        blf.color(font_id, *colors['text'])
        hdr = "Operators"
        tw, th = blf.dimensions(font_id, hdr)
        blf.position(font_id, px + (pw - tw) / 2, py + ph - list_font_size - sp2, 0)
        blf.draw(font_id, hdr)

    # Search box text (outside scissor)
    if unit_px >= 20:
        blf.size(font_id, item_font_size)
        if state._operator_list_search_active or state._operator_list_search_text:
            blf.color(font_id, *colors['capture_text'])
            show_cursor = time.monotonic() % 1.0 > 0.5
            cursor = "|" if show_cursor else " "
            display = state._operator_list_search_text + cursor
        else:
            blf.color(font_id, *colors['text_dim'])
            display = "Search operators\u2026"
        stw, sth = blf.dimensions(font_id, display)
        blf.position(font_id, search_x + sp3, search_y + (search_h - sth) / 2, 0)
        blf.draw(font_id, display)

    # Pass 2: Draw text (inside scissor clip)
    with _scissor_clip(px, int(content_bottom), pw, int(content_h)):
        # Category header text
        if cat_text_draws:
            blf.size(font_id, list_font_size)
            avail_w = pw - sp4 * 2
            for cat_text, cat_text_color, gy, gh in cat_text_draws:
                blf.color(font_id, *cat_text_color)
                display_cat, tw_cat, th_cat = _truncate_text(font_id, cat_text, avail_w)
                blf.position(font_id, px + sp4, gy + (gh - th_cat) / 2, 0)
                blf.draw(font_id, display_cat)

        # Item text
        if item_text_draws:
            blf.size(font_id, item_font_size)
            blf.color(font_id, *colors['text'])
            for human_name, text_x, iy, ih in item_text_draws:
                avail_w = pw - (text_x - px) - sp2
                display_name, tw_n, th_n = _truncate_text(font_id, human_name, avail_w)
                blf.position(font_id, text_x, iy + (ih - th_n) / 2, 0)
                blf.draw(font_id, display_name)

        # Fade gradients
        if has_scrollbar:
            fade_h = s.sp6
            fade_x2 = px + pw - track_w - sp2
            if scroll_offset > 0:
                _draw_fade_gradient(shader_smooth, px, fade_x2,
                                    content_top - fade_h, fade_h, colors['panel_bg'], 'DOWN')
            if scroll_offset < max_scroll:
                _draw_fade_gradient(shader_smooth, px, fade_x2,
                                    int(content_bottom), fade_h, colors['panel_bg'], 'UP')


def _draw_op_flyout(ctx):
    """Draw the operator flyout menu (batched)."""
    if not state._op_flyout_visible or not state._op_flyout_items:
        return

    font_id = ctx.font_id
    colors = ctx.colors
    s = ctx.s
    sp2, sp5 = s.sp2, s.sp5
    rb = ctx.rb
    info_font_size = ctx.font_base

    items = state._op_flyout_items
    y_min = min(item[3] for item in items)
    y_max = max(item[3] + item[5] for item in items)
    bg_x = items[0][2] - sp2
    bg_y = y_min - sp2
    bg_w = items[0][4] + sp2 * 2
    bg_h = (y_max - y_min) + sp2 * 2

    shadow_off = max(3, sp2)
    rb.add(bg_x + shadow_off, bg_y - shadow_off, bg_w, bg_h, colors['shadow'])
    rb.add(bg_x, bg_y, bg_w, bg_h, colors['menu_bg'])

    text_items = []
    for fi_idx, (flabel, faction, fx, fy, fw, fh) in enumerate(items):
        fcol = colors['menu_hover'] if fi_idx == state._op_flyout_hovered else colors['menu_bg']
        rb.add(fx, fy, fw, fh, fcol)
        text_items.append((flabel, fx, fy, fw, fh))

    rb.flush(ctx.shader_smooth)
    _draw_rect_border(ctx.shader_uniform, bg_x, bg_y, bg_w, bg_h, colors['menu_border'])

    action_font_size = max(10, int(info_font_size * 0.9))
    for flabel, fx, fy, fw, fh in text_items:
        blf.size(font_id, action_font_size)
        blf.color(font_id, *colors['text'])
        ftw, fth = blf.dimensions(font_id, flabel)
        blf.position(font_id, fx + sp5, fy + (fh - fth) / 2, 0)
        blf.draw(font_id, flabel)


_draw_callback_count = 0


# ---------------------------------------------------------------------------
# DrawContext: shared state passed to all section-drawing helpers
# ---------------------------------------------------------------------------
from collections import namedtuple

DrawContext = namedtuple('DrawContext', [
    'shader_uniform', 'shader_smooth', 'font_id', 'unit_px',
    'colors', 's', 'rw', 'rh',
    'font_xs', 'font_sm', 'font_base', 'font_lg', 'font_xl',
    'category_colors_enabled', 'now',
    'rb', 'lb', 'ib',
])


# ---------------------------------------------------------------------------
# Section helpers (called from _draw_callback orchestrator)
# ---------------------------------------------------------------------------

def _draw_background_plate(ctx):
    """Section A: background plate + close button + resize handle.

    Returns (min_x, max_x, min_y, max_y) keyboard bounds (including toolbar).
    """
    shader_uniform = ctx.shader_uniform
    font_id = ctx.font_id
    colors = ctx.colors
    pad = ctx.s.pad

    min_x, max_x, min_y, max_y = state._keyboard_bounds

    # Include toolbar in bounding box
    if state._export_button_rect:
        fx, fy, fw, fh = state._export_button_rect
        max_y = max(max_y, fy + fh)
    if state._presets_btn_rect:
        fx, fy, fw, fh = state._presets_btn_rect
        max_y = max(max_y, fy + fh)

    rb = ctx.rb
    lb = ctx.lb
    rb.add(min_x - pad, min_y - pad,
           (max_x - min_x) + 2 * pad, (max_y - min_y) + 2 * pad, colors['background'])

    # --- Feature 1: Close button (L3: enhanced hover) ---
    if state._close_button_rect is not None:
        cbx, cby, cbw, cbh = state._close_button_rect
        if state._close_hovered:
            cb_col = (min(1.0, colors['button_hover'][0] * 1.3),
                      min(1.0, colors['button_hover'][1] * 1.1),
                      min(1.0, colors['button_hover'][2] * 1.1),
                      colors['button_hover'][3])
            x_col = colors['conflict_header']  # Red X on hover
        else:
            cb_col = colors['button_normal']
            x_col = colors['text']
        rb.add(cbx, cby, cbw, cbh, cb_col)
        lb.add(cbx, cby, cbw, cbh, colors['border'])

    # --- Feature 2: Resize handle ---
    rh_col = None
    if state._resize_handle_rect is not None:
        rhx, rhy, rhw, rhh = state._resize_handle_rect
        rh_col = colors['button_hover'] if state._resize_hovered else colors['button_normal']
        rb.add(rhx, rhy, rhw, rhh, rh_col)

    # --- Mouse block outline ---
    si = state._mouse_rects_start_index
    if si >= 0 and si < len(state._key_rects):
        mouse_keys = state._key_rects[si:]
        if mouse_keys:
            mx1 = min(k.x for k in mouse_keys)
            mx2 = max(k.x + k.w for k in mouse_keys)
            my1 = min(k.y for k in mouse_keys)
            my2 = max(k.y + k.h for k in mouse_keys)
            mp = ctx.s.sp3
            outline_col = (colors['border'][0], colors['border'][1], colors['border'][2], 0.4)
            lb.add(mx1 - mp, my1 - mp, (mx2 - mx1) + 2 * mp, (my2 - my1) + 2 * mp, outline_col)

    # Note: do NOT flush here — orchestrator will flush after toolbar geometry is also collected
    # Return text drawing as a closure to be called after flush
    return min_x, max_x, min_y, max_y


def _draw_background_text(ctx):
    """Draw background plate text elements (after global flush)."""
    font_id = ctx.font_id
    colors = ctx.colors
    shader_uniform = ctx.shader_uniform
    if state._close_button_rect is not None:
        cbx, cby, cbw, cbh = state._close_button_rect
        if state._close_hovered:
            x_col = colors['conflict_header']
        else:
            x_col = colors['text']
        cb_font_size = max(10, int(cbh * 0.5))
        blf.size(font_id, cb_font_size)
        blf.color(font_id, *x_col)
        tw, th = blf.dimensions(font_id, "X")
        blf.position(font_id, cbx + (cbw - tw) / 2, cby + (cbh - th) / 2, 0)
        blf.draw(font_id, "X")

    # Resize handle diagonal lines
    if state._resize_handle_rect is not None:
        rhx, rhy, rhw, rhh = state._resize_handle_rect
        line_verts = []
        line_indices = []
        for li in range(3):
            offset = (li + 1) * rhw * 0.25
            line_verts.extend([
                (rhx + offset, rhy),
                (rhx + rhw, rhy + rhh - offset),
            ])
            lidx = li * 2
            line_indices.append((lidx, lidx + 1))
        if line_verts:
            line_batch = batch_for_shader(shader_uniform, 'LINES',
                                          {"pos": line_verts}, indices=line_indices)
            shader_uniform.bind()
            shader_uniform.uniform_float("color", colors['border'])
            line_batch.draw(shader_uniform)

    # Mouse block label
    si = state._mouse_rects_start_index
    if si >= 0 and si < len(state._key_rects):
        mouse_keys = state._key_rects[si:]
        if mouse_keys:
            mx1 = min(k.x for k in mouse_keys)
            mx2 = max(k.x + k.w for k in mouse_keys)
            my2 = max(k.y + k.h for k in mouse_keys)
            mp = ctx.s.sp3
            outline_col = (colors['border'][0], colors['border'][1], colors['border'][2], 0.4)
            label_size = max(9, int(ctx.unit_px * 0.2))
            blf.size(font_id, label_size)
            blf.color(font_id, *outline_col)
            lw, lh = blf.dimensions(font_id, "Mouse")
            blf.position(font_id, mx1 + ((mx2 - mx1) - lw) / 2, my2 + mp + 2, 0)
            blf.draw(font_id, "Mouse")


def _draw_key_shadows(ctx):
    """Section B: drop shadows behind keys."""
    unit_px = ctx.unit_px
    shader_smooth = ctx.shader_smooth
    colors = ctx.colors

    if state._shadow_batch_cache is None:
        shadow_offset_x = max(1, int(unit_px * 0.04))
        shadow_offset_y = -max(1, int(unit_px * 0.04))
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
            state._shadow_batch_cache = batch_for_shader(shader_smooth, 'TRIS',
                                  {"pos": shadow_verts, "color": shadow_colors},
                                  indices=shadow_indices)

    if state._shadow_batch_cache:
        shader_smooth.bind()
        state._shadow_batch_cache.draw(shader_smooth)


def _draw_key_rectangles(ctx):
    """Sections C+D: modifier pulsing + key rectangles + key borders."""
    shader_uniform = ctx.shader_uniform
    shader_smooth = ctx.shader_smooth
    colors = ctx.colors
    unit_px = ctx.unit_px
    now = ctx.now
    category_colors_enabled = ctx.category_colors_enabled

    # --- Modifier pulsing ---
    eff_mods = state._get_effective_modifiers()
    physical_active = any(state._physical_modifiers.values())
    pulse_t = 0.0
    if physical_active:
        pulse_t = 0.5 + 0.5 * math.sin(now * 2 * math.pi * 2)  # 2Hz sine

    # Cache hovered/selected event types outside loop
    hovered_et = state._key_rects[state._hovered_key_index].event_type if state._hovered_key_index >= 0 else None
    selected_et = state._key_rects[state._selected_key_index].event_type if state._selected_key_index >= 0 else None

    # --- C. Key rectangles (pre-allocated buffers) ---
    n_keys = len(state._key_rects)
    _ensure_key_buffers(n_keys)
    verts = _key_verts_buf
    key_colors_buf = _key_colors_buf
    key_bg_colors = []  # cached per-key bg colors for text contrast in _draw_key_labels

    search_dimming = state._search_active and state._search_text

    for i, kr in enumerate(state._key_rects):
        # ISO Enter co-highlighting: if hovered/selected key shares event_type
        _co_highlight = False
        if hovered_et and i != state._hovered_key_index:
            if kr.event_type == hovered_et and hovered_et == 'RET':
                _co_highlight = True
        if selected_et and i != state._selected_key_index:
            if kr.event_type == selected_et and selected_et == 'RET':
                _co_highlight = True

        if i == state._selected_key_index:
            col = colors['key_selected']
        elif _co_highlight and state._selected_key_index >= 0:
            col = colors['key_selected']
        elif i == state._hovered_key_index:
            if state._hover_transition < 1.0:
                col = _lerp_color(colors['key_default'], colors['key_hovered'], state._hover_transition)
            else:
                col = colors['key_hovered']
        elif _co_highlight:
            col = colors['key_hovered']
        elif kr.event_type in _MODIFIER_EVENTS:
            dict_key = MODIFIER_KEY_TO_DICT.get(kr.event_type)
            is_mod_active = eff_mods.get(dict_key, False)
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

        key_bg_colors.append(col)

        # Diff mode color overrides
        if state._diff_mode_active:
            if kr.event_type in state._diff_modified_keys:
                # Green tint for modified bindings
                col = _lerp_color(col, colors['export_button'], 0.5)
            elif kr.event_type in state._diff_removed_keys:
                # Red tint for deactivated bindings
                col = _lerp_color(col, colors['conflict_header'], 0.5)
            else:
                # Dim unmodified keys
                col = (col[0] * 0.35, col[1] * 0.35, col[2] * 0.35, col[3])

        # Dim non-matching keys during search
        if search_dimming and kr.event_type not in state._search_matching_keys:
            col = (col[0] * 0.3, col[1] * 0.3, col[2] * 0.3, col[3])

        # Rebind success flash
        if i == state._rebind_flash_key_index:
            elapsed = now - state._rebind_flash_time
            if elapsed < 0.3:
                flash_t = 1.0 - elapsed / 0.3
                col = _lerp_color(col, (0.2, 0.6, 0.3, 1.0), flash_t * 0.6)
            else:
                state._rebind_flash_key_index = -1

        x, y, w, h = kr.x, kr.y, kr.w, kr.h
        base = i * 4
        verts[base] = (x, y)
        verts[base + 1] = (x + w, y)
        verts[base + 2] = (x + w, y + h)
        verts[base + 3] = (x, y + h)
        key_colors_buf[base] = col
        key_colors_buf[base + 1] = col
        key_colors_buf[base + 2] = col
        key_colors_buf[base + 3] = col

    key_batch = batch_for_shader(shader_smooth, 'TRIS',
                                 {"pos": verts, "color": key_colors_buf},
                                 indices=_key_indices_buf)
    shader_smooth.bind()
    key_batch.draw(shader_smooth)

    # --- D. Key borders (cached — geometry only changes on layout) ---
    if state._border_batch_cache is None:
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
        state._border_batch_cache = batch_for_shader(shader_uniform, 'LINES',
                                        {"pos": border_verts},
                                        indices=border_indices)

    shader_uniform.bind()
    shader_uniform.uniform_float("color", colors['border'])
    state._border_batch_cache.draw(shader_uniform)

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

    # C2: Keyboard focus indicator
    if state._nav_focus == 'KEYS' and 0 <= state._nav_key_index < len(state._key_rects):
        nav_kr = state._key_rects[state._nav_key_index]
        if state._nav_key_index != highlight_idx:
            x, y, w, h = nav_kr.x, nav_kr.y, nav_kr.w, nav_kr.h
            inset = max(1, int(unit_px * 0.02))
            focus_verts = [(x+inset, y+inset), (x+w-inset, y+inset), (x+w-inset, y+h-inset), (x+inset, y+h-inset)]
            focus_indices = [(0, 1), (1, 2), (2, 3), (3, 0)]
            focus_batch = batch_for_shader(shader_uniform, 'LINES', {"pos": focus_verts}, indices=focus_indices)
            gpu.state.line_width_set(1.5)
            shader_uniform.uniform_float("color", colors['capture_text'])
            focus_batch.draw(shader_uniform)
            gpu.state.line_width_set(1.0)

    # Highlight border for active modifier keys
    for i, kr in enumerate(state._key_rects):
        if kr.event_type in _MODIFIER_EVENTS:
            dict_key = MODIFIER_KEY_TO_DICT.get(kr.event_type)
            if eff_mods.get(dict_key, False):
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

    return key_bg_colors


def _draw_key_labels(ctx, key_bg_colors=None):
    """Section E: key labels (two-line key label + command label)."""
    font_id = ctx.font_id
    colors = ctx.colors
    unit_px = ctx.unit_px
    category_colors_enabled = ctx.category_colors_enabled
    s = ctx.s
    sp2 = s.sp2
    font_xs = ctx.font_xs
    font_sm = ctx.font_sm

    font_size = max(11, int(unit_px * 0.3))
    cmd_font_size = font_sm

    search_dimming = state._search_active and state._search_text

    if unit_px >= 20:
        pad_x = max(3, int(unit_px * 0.04))
        pad_y = max(2, int(unit_px * 0.03))
        cfont = _get_condensed_font()
        badge_font_size = font_xs
        blf.size(font_id, font_size)
        blf.size(cfont, cmd_font_size)
        for i, kr in enumerate(state._key_rects):
            # Use pre-computed background color from _draw_key_rectangles
            key_bg = key_bg_colors[i] if key_bg_colors and i < len(key_bg_colors) else colors['key_default']

            # Contrast-aware text colors
            adaptive_text = _contrasting_text_color(key_bg)
            adaptive_dim = _contrasting_text_color(
                key_bg,
                light=(0.78, 0.78, 0.78, 0.95),
                dark=(0.25, 0.25, 0.25, 0.95),
            )

            if search_dimming and kr.event_type not in state._search_matching_keys:
                text_col = (adaptive_text[0] * 0.4, adaptive_text[1] * 0.4, adaptive_text[2] * 0.4, adaptive_text[3])
                cmd_text_col = text_col
            else:
                text_col = adaptive_text
                cmd_text_col = adaptive_dim

            cmd_label = state._key_labels_cache.get(kr.event_type)
            if cmd_label and kr.w >= unit_px * 0.8:
                # Two-line layout: key label top-left, command label bottom
                blf.color(font_id, *text_col)
                display_label, _, _ = _truncate_text(font_id, kr.label, kr.w - pad_x * 2)
                blf.position(font_id, kr.x + pad_x, kr.y + kr.h - font_size - pad_y, 0)
                blf.draw(font_id, display_label)

                # Command label (condensed font, contrast-aware)
                blf.color(cfont, *cmd_text_col)
                display_cmd, tw, th = _truncate_text(cfont, cmd_label, kr.w - pad_x * 2)
                blf.position(cfont, kr.x + pad_x, kr.y + kr.h * 0.15, 0)
                blf.draw(cfont, display_cmd)
            else:
                # Single centered label (original style)
                blf.color(font_id, *text_col)
                display_label, tw, th = _truncate_text(font_id, kr.label, kr.w - pad_x * 2)
                tx = kr.x + (kr.w - tw) / 2
                ty = kr.y + (kr.h - th) / 2
                blf.position(font_id, tx, ty, 0)
                blf.draw(font_id, display_label)

        # --- Badge pass: set badge font size once, draw all badges ---
        blf.size(font_id, badge_font_size)
        # Pre-measure static "D" string once
        d_dims = blf.dimensions(font_id, "D")

        for i, kr in enumerate(state._key_rects):
            key_bg = key_bg_colors[i] if key_bg_colors and i < len(key_bg_colors) else colors['key_default']

            # Modifier badge (bottom-right)
            badge_count = state._key_modifier_badge_cache.get(kr.event_type, 0)
            if badge_count > 0:
                badge_text = str(badge_count)
                tw, th = blf.dimensions(font_id, badge_text)
                badge_x = kr.x + kr.w - tw - sp2
                badge_y = kr.y + sp2
                badge_col = _contrasting_text_color(key_bg,
                    light=colors['badge_text'],
                    dark=(0.15, 0.15, 0.15, 0.85))
                blf.color(font_id, *badge_col)
                blf.position(font_id, badge_x, badge_y, 0)
                blf.draw(font_id, badge_text)

            # Hold/drag badge (top-right, amber "D")
            if kr.event_type in state._key_hold_badge_cache:
                hold_col = (0.85, 0.60, 0.35, 0.8)
                blf.color(font_id, *hold_col)
                dw, dh = d_dims
                blf.position(font_id, kr.x + kr.w - dw - sp2, kr.y + kr.h - dh - sp2, 0)
                blf.draw(font_id, "D")


def _draw_toolbar(ctx, kb_bounds):
    """Sections F2+F3: export/presets buttons + undo counter + search bar + preset name input."""
    shader_uniform = ctx.shader_uniform
    font_id = ctx.font_id
    colors = ctx.colors
    unit_px = ctx.unit_px
    now = ctx.now
    s = ctx.s
    rw, rh = ctx.rw, ctx.rh
    sp2, sp3, sp5, sp6, pad = s.sp2, s.sp3, s.sp5, s.sp6, s.pad
    font_xs = ctx.font_xs
    font_sm = ctx.font_sm
    font_base = ctx.font_base
    font_size = max(11, int(unit_px * 0.3))
    min_x, max_x, min_y, max_y = kb_bounds

    rb = ctx.rb
    lb = ctx.lb

    # --- F2. Toolbar buttons (batched) ---
    if state._export_button_rect is not None:
        ex, ey, ew, eh = state._export_button_rect
        ex_col = colors['export_button_hover'] if state._export_hovered else colors['export_button']
        rb.add(ex, ey, ew, eh, ex_col)
        lb.add(ex, ey, ew, eh, colors['border'])

    if state._import_button_rect is not None:
        ix, iy, iw, ih = state._import_button_rect
        im_col = colors['button_hover'] if state._import_hovered else colors['button_normal']
        rb.add(ix, iy, iw, ih, im_col)
        lb.add(ix, iy, iw, ih, colors['border'])

    if state._presets_btn_rect is not None:
        px, py, pw, ph = state._presets_btn_rect
        pr_col = colors['button_hover'] if state._presets_hovered else colors['button_normal']
        rb.add(px, py, pw, ph, pr_col)
        lb.add(px, py, pw, ph, colors['border'])

    # --- Diff mode badge geometry ---
    badge_rect = None
    if state._diff_mode_active:
        diff_label = "DIFF"
        blf.size(font_id, font_xs)
        dtw, dth = blf.dimensions(font_id, diff_label)
        badge_w = dtw + sp5 * 2
        badge_h = dth + sp3 * 2
        badge_x = max_x - badge_w - sp3
        badge_y = max_y + pad + sp3
        if state._export_button_rect:
            fx, fy, fw, fh = state._export_button_rect
            badge_y = max(badge_y, fy + fh + sp5)
        rb.add(badge_x, badge_y, badge_w, badge_h, colors['export_button'])
        lb.add(badge_x, badge_y, badge_w, badge_h, colors['border'])
        badge_rect = (badge_x, badge_y, badge_w, badge_h)

    # --- F3. Search bar geometry ---
    search_rect = None
    if state._search_active:
        sb_w = min(300, rw * 0.4)
        sb_h = unit_px * 0.7
        sb_x = (rw - sb_w) / 2
        sb_y = max_y + pad + sp3
        if state._export_button_rect:
            fx, fy, fw, fh = state._export_button_rect
            sb_y = max(sb_y, fy + fh + sp5)
        rb.add(sb_x, sb_y, sb_w, sb_h, colors['search_bg'])
        lb.add(sb_x, sb_y, sb_w, sb_h, colors['search_border'])
        search_rect = (sb_x, sb_y, sb_w, sb_h)

    # ONE flush for ALL toolbar geometry (buttons + badge + search bar)
    rb.flush(ctx.shader_smooth)
    lb.flush(ctx.shader_smooth)

    # --- All toolbar text (after flush) ---
    if state._export_button_rect is not None and unit_px >= 20:
        ex, ey, ew, eh = state._export_button_rect
        blf.size(font_id, font_sm)
        blf.color(font_id, *colors['text'])
        elabel = "Export"
        tw, th = blf.dimensions(font_id, elabel)
        blf.position(font_id, ex + (ew - tw) / 2, ey + (eh - th) / 2, 0)
        blf.draw(font_id, elabel)

    if state._import_button_rect is not None and unit_px >= 20:
        ix, iy, iw, ih = state._import_button_rect
        blf.size(font_id, font_sm)
        blf.color(font_id, *colors['text'])
        ilabel = "Import"
        tw, th = blf.dimensions(font_id, ilabel)
        blf.position(font_id, ix + (iw - tw) / 2, iy + (ih - th) / 2, 0)
        blf.draw(font_id, ilabel)

    if state._presets_btn_rect is not None and unit_px >= 20:
        px, py, pw, ph = state._presets_btn_rect
        blf.size(font_id, font_sm)
        blf.color(font_id, *colors['text'])
        plabel = state._active_preset_name if state._active_preset_name else "Presets"
        plabel, tw, th = _truncate_text(font_id, plabel, pw - sp5)
        blf.position(font_id, px + (pw - tw) / 2, py + (ph - th) / 2, 0)
        blf.draw(font_id, plabel)

    # Undo/redo counter
    undo_count = len(state._undo_stack)
    redo_count = len(state._redo_stack)
    if (undo_count > 0 or redo_count > 0) and state._export_button_rect is not None:
        ex, ey, ew, eh = state._export_button_rect
        undo_text = f"Undo: {undo_count} | Redo: {redo_count}"
        blf.size(font_id, font_xs)
        blf.color(font_id, *colors['text_dim'])
        tw, th = blf.dimensions(font_id, undo_text)
        blf.position(font_id, ex, ey - th - sp3, 0)
        blf.draw(font_id, undo_text)

    if badge_rect:
        blf.size(font_id, font_xs)
        blf.color(font_id, *colors['text'])
        blf.position(font_id, badge_rect[0] + sp5, badge_rect[1] + sp3, 0)
        blf.draw(font_id, "DIFF")

    if search_rect and unit_px >= 20:
            blf.size(font_id, font_base)
            blf.color(font_id, *colors['capture_text'])
            show_cursor = now % 1.0 > 0.5
            cursor = "|" if show_cursor else " "
            if state._search_text:
                search_display = state._search_text + cursor
            else:
                search_display = "Search bindings\u2026 " + cursor
                blf.color(font_id, *colors['text_dim'])
            tw, th = blf.dimensions(font_id, search_display)
            blf.position(font_id, sb_x + sp5, sb_y + (sb_h - th) / 2, 0)
            blf.draw(font_id, search_display)

            # Search result count badge
            if state._search_text:
                count = state._search_results_count
                count_text = f"{count} key{'s' if count != 1 else ''}" if count > 0 else "No matches"
                blf.size(font_id, font_xs)
                tc = colors['text']
                blf.color(font_id, tc[0], tc[1], tc[2], tc[3] * 0.5)
                ctw, cth = blf.dimensions(font_id, count_text)
                blf.position(font_id, sb_x + sb_w - ctw - sp5, sb_y + (sb_h - cth) / 2, 0)
                blf.draw(font_id, count_text)

    # --- v0.9 Feature 6: Preset name input overlay ---
    if state._preset_name_input_active:
        sb_w = min(300, rw * 0.4)
        sb_h = unit_px * 0.7
        sb_x = (rw - sb_w) / 2
        sb_y = rh / 2 - sb_h / 2

        rb.add(0, 0, rw, rh, colors['capture_overlay'])
        rb.add(sb_x, sb_y, sb_w, sb_h, colors['search_bg'])
        lb.add(sb_x, sb_y, sb_w, sb_h, colors['search_border'])
        rb.flush(ctx.shader_smooth)
        lb.flush(ctx.shader_smooth)

        if unit_px >= 20:
            blf.size(font_id, font_size)
            # Title above input
            blf.color(font_id, *colors['text'])
            title = "Save Preset As"
            tw, th = blf.dimensions(font_id, title)
            blf.position(font_id, sb_x + (sb_w - tw) / 2, sb_y + sb_h + sp5, 0)
            blf.draw(font_id, title)
            # Input text
            blf.color(font_id, *colors['capture_text'])
            input_display = state._preset_name_text + "|"
            if not state._preset_name_text:
                input_display = "Enter preset name\u2026 |"
                blf.color(font_id, *colors['text_dim'])
            tw, th = blf.dimensions(font_id, input_display)
            blf.position(font_id, sb_x + sp5, sb_y + (sb_h - th) / 2, 0)
            blf.draw(font_id, input_display)


def _draw_side_panels(ctx, kb_bounds):
    """Feature 4 + Operator List + Tooltip + Preset dropdown + Category legend."""
    shader_uniform = ctx.shader_uniform
    shader_smooth = ctx.shader_smooth
    font_id = ctx.font_id
    colors = ctx.colors
    unit_px = ctx.unit_px
    now = ctx.now
    s = ctx.s
    rw = ctx.rw
    sp2, sp3, sp5, sp6, pad = s.sp2, s.sp3, s.sp5, s.sp6, s.pad
    font_xs = ctx.font_xs
    font_size = max(11, int(unit_px * 0.3))
    category_colors_enabled = ctx.category_colors_enabled
    min_x, max_x, min_y, max_y = kb_bounds

    # --- Feature 4: Editor/Mode filter list panels (softened border) ---
    with prof("  filter_lists"):
        _draw_filter_lists(ctx)

    # --- Operator List panel ---
    with prof("  operator_list"):
        _draw_operator_list(ctx)

    # --- L4: Tooltip rendering ---
    if state._tooltip_text and (now - state._tooltip_hover_start) >= 0.5:
        tip_font_size = font_xs
        blf.size(font_id, tip_font_size)
        blf.color(font_id, *colors['text'])
        tw_tip, th_tip = blf.dimensions(font_id, state._tooltip_text)
        tip_pad = sp3
        tip_x = (rw - tw_tip) / 2 - tip_pad
        tip_y = max_y + pad + sp3
        if state._export_button_rect:
            tip_y = max(tip_y, state._export_button_rect[1] + state._export_button_rect[3] + sp3)
        rb = ctx.rb
        rb.add(tip_x, tip_y, tw_tip + tip_pad * 2, th_tip + tip_pad * 2, colors['panel_bg'])
        rb.flush(ctx.shader_smooth)
        _draw_rect_border(shader_uniform, tip_x, tip_y, tw_tip + tip_pad * 2, th_tip + tip_pad * 2, colors['border'])
        blf.position(font_id, tip_x + tip_pad, tip_y + tip_pad, 0)
        blf.draw(font_id, state._tooltip_text)

    # --- v0.9 Feature 6: Preset dropdown ---
    if state._preset_dropdown_open and state._preset_dropdown_rects:
        rb = ctx.rb
        first_dd = state._preset_dropdown_rects[0]
        dd_min_y = min(item[3] for item in state._preset_dropdown_rects)
        dd_max_y = max(item[3] + item[5] for item in state._preset_dropdown_rects)
        dd_x = first_dd[2] - sp2
        dd_w = first_dd[4] + sp2 * 2
        dd_h = (dd_max_y - dd_min_y) + sp2 * 2

        rb.add(dd_x + max(3, sp2), dd_min_y - sp2 - max(3, sp2), dd_w, dd_h, colors['shadow'])
        rb.add(dd_x, dd_min_y - sp2, dd_w, dd_h, colors['menu_bg'])

        dd_text_items = []
        for di, item in enumerate(state._preset_dropdown_rects):
            dlabel, daction, dx, dy, dw, dh = item[:6]
            if di == state._preset_dropdown_hovered:
                dcol = colors['menu_hover']
            elif daction.startswith('LOAD:') and daction[5:] == state._active_preset_name:
                dcol = colors['active_highlight']
            else:
                dcol = colors['menu_bg']
            rb.add(dx, dy, dw, dh, dcol)
            dd_text_items.append((dlabel, dx, dy, dw, dh))

        rb.flush(ctx.shader_smooth)
        _draw_rect_border(shader_uniform, dd_x, dd_min_y - sp2, dd_w, dd_h, colors['menu_border'])

        if unit_px >= 20:
            for dlabel, dx, dy, dw, dh in dd_text_items:
                blf.size(font_id, font_size)
                blf.color(font_id, *colors['text'])
                tw, th = blf.dimensions(font_id, dlabel)
                blf.position(font_id, dx + sp5, dy + (dh - th) / 2, 0)
                blf.draw(font_id, dlabel)

    # --- v0.9 Feature 3: Category color legend ---
    if category_colors_enabled and state._key_categories_cache:
        active_cats = set(state._key_categories_cache.values())
        if active_cats:
            legend_font_size = font_xs
            blf.size(font_id, legend_font_size)
            swatch_size = max(8, int(unit_px * 0.25))
            swatch_gap = max(3, int(unit_px * 0.05))

            # Measure max label width for uniform entry spacing
            sorted_cats = sorted(active_cats)
            max_label_w = 0
            for cat_name in sorted_cats:
                tw, _ = blf.dimensions(font_id, cat_name)
                max_label_w = max(max_label_w, tw)
            entry_w = swatch_size + swatch_gap + max_label_w + swatch_gap

            # Always horizontal, top-left above keyboard (same row as buttons)
            toolbar_y = state._export_button_rect[1]
            toolbar_h = state._export_button_rect[3]
            lx = min_x
            ly = toolbar_y + (toolbar_h - swatch_size) / 2
            legend_rb = ctx.rb
            legend_items = []
            for cat_name in sorted_cats:
                cat_key = _CAT_COLOR_KEYS.get(cat_name)
                cat_col = colors.get(cat_key, colors['key_bound']) if cat_key else colors['key_bound']
                legend_rb.add(lx, ly, swatch_size, swatch_size, cat_col)
                legend_items.append((cat_name, lx))
                lx += entry_w
                if state._export_button_rect and lx + entry_w > state._export_button_rect[0] - sp5:
                    break
            legend_rb.flush(ctx.shader_smooth)
            for cat_name, cat_lx in legend_items:
                blf.color(font_id, *colors['text_dim'])
                tw, th = blf.dimensions(font_id, cat_name)
                blf.position(font_id, cat_lx + swatch_size + swatch_gap, ly + (swatch_size - th) / 2, 0)
                blf.draw(font_id, cat_name)


def _draw_info_panel(ctx, kb_bounds):
    """Section G: info panel with scrolling bindings."""
    shader_uniform = ctx.shader_uniform
    shader_smooth = ctx.shader_smooth
    font_id = ctx.font_id
    colors = ctx.colors
    unit_px = ctx.unit_px
    s = ctx.s
    sp1, sp2, sp3, sp5, sp6, pad = s.sp1, s.sp2, s.sp3, s.sp5, s.sp6, s.pad
    font_base = ctx.font_base
    font_lg = ctx.font_lg
    min_x, max_x, min_y, max_y = kb_bounds

    # --- G. Info panel (to the right of filter lists + operators) ---
    gap = unit_px * 0.12
    editor_list_w = unit_px * 2.8
    mode_list_w = unit_px * 2.5
    operator_list_w = unit_px * 3.0
    info_x = (min_x - pad) + editor_list_w + gap + mode_list_w + gap + operator_list_w + gap
    info_w = (max_x + pad) - info_x
    info_h = unit_px * 3.2
    info_y = min_y - pad - info_h - sp3

    # Panel background + border -- info panel uses brighter bg (batched)
    rb = ctx.rb
    lb = ctx.lb
    rb.add(info_x, info_y, info_w, info_h, colors['info_panel_bg'])
    lb.add(info_x, info_y, info_w, info_h, colors['border'])

    if state._nav_focus == 'INFO_PANEL':
        lb.add(info_x, info_y, info_w, info_h, colors['border_highlight'])

    # Store rect for hit testing (Issue #3)
    state._info_panel_rect = (info_x, info_y, info_w, info_h)

    active_idx = state._selected_key_index if state._selected_key_index >= 0 else state._hovered_key_index
    info_font_size = font_base

    if 0 <= active_idx < len(state._key_rects):
        rb.add(info_x, info_y, 2, info_h, colors['key_selected'])

        kr = state._key_rects[active_idx]

        # Add separator line to batch
        header_font_size = font_lg
        header_y_pre = info_y + info_h - header_font_size - sp3
        sep_y_pre = header_y_pre - sp3
        rb.add(info_x + sp3, sep_y_pre, info_w - sp3 * 2, 1, colors['border'])

    # Flush all info panel rects before text
    rb.flush(shader_smooth)
    lb.flush(shader_smooth)

    blf.size(font_id, info_font_size)

    if 0 <= active_idx < len(state._key_rects):
        kr = state._key_rects[active_idx]
        bindings, n_matching = _get_all_bindings_for_key(kr.event_type)

        # Header: big key name + dim filter summary (Issue #5, #8)
        header_font_size = font_lg
        header_x = info_x + sp5
        header_y = info_y + info_h - header_font_size - sp3
        blf.size(font_id, header_font_size)
        blf.color(font_id, *colors['text'])
        blf.position(font_id, header_x, header_y, 0)
        blf.draw(font_id, kr.label)
        tw_label, _ = blf.dimensions(font_id, kr.label)

        header_has_filter = ('ALL' not in state._filter_space_types or 'ALL' not in state._filter_modes)
        if header_has_filter:
            filter_parts = []
            if 'ALL' not in state._filter_space_types:
                filter_parts.append(_get_filter_summary('EDITOR'))
            if 'ALL' not in state._filter_modes:
                filter_parts.append(_get_filter_summary('MODE'))
            filter_summary_text = ' / '.join(filter_parts)
            blf.size(font_id, info_font_size)
            blf.color(font_id, *colors['text_dim'])
            blf.position(font_id, header_x + tw_label + sp5, header_y, 0)
            blf.draw(font_id, filter_summary_text)

        sep_y = header_y - sp3

        blf.size(font_id, info_font_size)

        if bindings:
            # Single-column layout with scrolling (Issues #2, #3, #12)
            # Group bindings + descriptions are cached per (event_type, modifiers, filters)
            panel_cache_key = state._all_bindings_key
            if state._info_panel_cache_key == panel_cache_key and state._info_panel_groups_cache is not None:
                groups = state._info_panel_groups_cache
                _group_descs = state._info_panel_descs_cache
            else:
                groups = _group_bindings(bindings, n_matching)
                _group_descs = {}
                for group_key, human_name, mod_str, entries, best_rank in groups:
                    op_id = group_key[0]
                    desc = _get_operator_description(op_id)
                    if desc:
                        _group_descs[group_key] = desc
                state._info_panel_groups_cache = groups
                state._info_panel_descs_cache = _group_descs
                state._info_panel_cache_key = panel_cache_key

            line_h = info_font_size + sp2
            content_top = sep_y - sp3
            content_bottom = info_y + sp3
            visible_h = content_top - content_bottom
            max_visible_rows = max(1, int(visible_h / line_h))

            # Count total visible rows (depends on expand state)
            total_rows = 0
            for group_key, human_name, mod_str, entries, best_rank in groups:
                total_rows += 1  # header row
                if len(entries) > 1 and group_key in state._info_panel_expanded_groups:
                    if group_key in _group_descs:
                        total_rows += 1  # description row
                    total_rows += len(entries)  # sub-rows

            info_max_scroll = max(0, (total_rows * line_h) - visible_h)
            state._info_panel_max_scroll = info_max_scroll
            # Clamp scroll
            state._info_panel_scroll = max(0, min(state._info_panel_scroll, info_max_scroll))
            has_scrollbar = total_rows > max_visible_rows
            scrollbar_w = 8 if has_scrollbar else 0
            avail_text_w = info_w - sp5 * 2 - scrollbar_w

            bind_icon_size = int(info_font_size * 1.0)
            cx = info_x + sp5
            indent = int(info_font_size * 1.2)

            scroll_offset = state._info_panel_scroll

            # Clear header rects for this frame
            state._info_panel_group_header_rects = []

            # Scissor clip only the scrollable content area (below header separator)
            with _scissor_clip(info_x, int(content_bottom), info_w, int(content_top - content_bottom)):
                row = 0
                for group_key, human_name, mod_str, entries, best_rank in groups:
                    ly = content_top - (row + 1) * line_h + scroll_offset
                    row += 1

                    if len(entries) == 1:
                        # Single entry -- render like the old flat line
                        if ly <= content_top and ly + line_h >= content_bottom:
                            orig_idx, b = entries[0]
                            km_name, op_id, b_mod_str, kmi, is_active = b[:5]
                            km_space_type = b[5] if len(b) > 5 else ''
                            prefix = f"[{b_mod_str}] " if b_mod_str else ""
                            active_tag = "" if is_active else "[off] "
                            line_text = f"{active_tag}{prefix}{human_name}"

                            if not is_active:
                                blf.color(font_id, *colors['text_inactive'])
                            elif orig_idx < n_matching:
                                blf.color(font_id, *colors['text'])
                            else:
                                blf.color(font_id, *colors['text_dim'])

                            suffix = f" | {km_name}"
                            suffix_w, _ = blf.dimensions(font_id, suffix)
                            main_max_w = max(avail_text_w * 0.4, avail_text_w - suffix_w - bind_icon_size - sp5)
                            display_text, tw_main, _ = _truncate_text(font_id, line_text, main_max_w)

                            blf.position(font_id, cx, ly, 0)
                            blf.draw(font_id, display_text)

                            icon_x_pos = cx + tw_main + sp2
                            bind_icon_tex = get_km_icon(km_space_type)
                            if bind_icon_tex:
                                _draw_icon(bind_icon_tex, icon_x_pos, ly - sp1, bind_icon_size)
                                icon_x_pos += bind_icon_size + sp2

                            suffix = f" | {km_name}"
                            remaining_w = avail_text_w - (icon_x_pos - cx)
                            if remaining_w > sp6:
                                blf.color(font_id, *colors['text_dim'])
                                display_suf, tw_suf, _ = _truncate_text(font_id, suffix, remaining_w)
                                blf.position(font_id, icon_x_pos, ly, 0)
                                blf.draw(font_id, display_suf)
                    else:
                        # Multi-entry collapsible group
                        is_expanded = group_key in state._info_panel_expanded_groups

                        if ly <= content_top and ly + line_h >= content_bottom:
                            # Draw header color based on best_rank
                            if best_rank == 0:
                                blf.color(font_id, *colors['text'])
                            elif best_rank == 1:
                                blf.color(font_id, *colors['text_dim'])
                            else:
                                blf.color(font_id, *colors['text_inactive'])

                            arrow = "\u25BE" if is_expanded else "\u25B8"
                            prefix = f"[{mod_str}] " if mod_str else ""
                            if is_expanded:
                                header_text = f"{arrow} {prefix}{human_name}"
                            else:
                                header_text = f"{arrow} {prefix}{human_name}"
                            count_text = f"  {len(entries)} editors"

                            main_max_w = avail_text_w - blf.dimensions(font_id, count_text)[0] - sp3
                            display_hdr, tw_hdr, _ = _truncate_text(font_id, header_text, max(avail_text_w * 0.5, main_max_w))

                            blf.position(font_id, cx, ly, 0)
                            blf.draw(font_id, display_hdr)

                            if not is_expanded:
                                blf.color(font_id, *colors['text_dim'])
                                blf.position(font_id, cx + tw_hdr, ly, 0)
                                blf.draw(font_id, count_text)

                            # Store rect for click detection
                            state._info_panel_group_header_rects.append(
                                (group_key, cx, ly, avail_text_w, line_h)
                            )

                        if is_expanded:
                            # Draw operator description row if available
                            group_desc = _group_descs.get(group_key, "")
                            if group_desc:
                                ly_desc = content_top - (row + 1) * line_h + scroll_offset
                                row += 1
                                if ly_desc <= content_top and ly_desc + line_h >= content_bottom:
                                    font_xs = ctx.font_xs
                                    blf.size(font_id, font_xs)
                                    tc = colors['text']
                                    blf.color(font_id, tc[0], tc[1], tc[2], 0.5)
                                    desc_max_w = avail_text_w - indent
                                    display_desc, _, _ = _truncate_text(font_id, group_desc, desc_max_w)
                                    blf.position(font_id, cx + indent, ly_desc, 0)
                                    blf.draw(font_id, display_desc)
                                    blf.size(font_id, info_font_size)

                            for orig_idx, b in entries:
                                ly_sub = content_top - (row + 1) * line_h + scroll_offset
                                row += 1

                                if ly_sub > content_top or ly_sub + line_h < content_bottom:
                                    continue

                                km_name, op_id, b_mod_str, kmi, is_active = b[:5]
                                km_space_type = b[5] if len(b) > 5 else ''
                                active_tag = "[off] " if not is_active else ""

                                if not is_active:
                                    blf.color(font_id, *colors['text_inactive'])
                                elif orig_idx < n_matching:
                                    blf.color(font_id, *colors['text'])
                                else:
                                    blf.color(font_id, *colors['text_dim'])

                                sub_text = f"\u00B7 {active_tag}{km_name}"
                                sub_max_w = avail_text_w - indent
                                display_sub, tw_sub, _ = _truncate_text(font_id, sub_text, sub_max_w)

                                # Draw icon then text
                                sub_x = cx + indent
                                bind_icon_tex = get_km_icon(km_space_type)
                                if bind_icon_tex:
                                    _draw_icon(bind_icon_tex, sub_x, ly_sub - sp1, bind_icon_size)
                                    sub_x += bind_icon_size + sp2

                                blf.position(font_id, sub_x, ly_sub, 0)
                                blf.draw(font_id, display_sub)

                # Scrollbar (Issue #3)
                if has_scrollbar:
                    track_w = s.track_w
                    track_x = info_x + info_w - track_w - sp2
                    _draw_scrollbar(shader_uniform, track_x, content_bottom, visible_h,
                                    scroll_offset, info_max_scroll, total_rows * line_h, visible_h,
                                    track_w=track_w, track_color=_lerp_color(colors['info_panel_bg'], colors['border'], 0.3),
                                    thumb_color=colors['text_dim'])

                    # Fade gradients (Issue #9)
                    fade_h = sp6
                    fade_x2 = info_x + info_w - track_w - sp3
                    if scroll_offset > 0:
                        _draw_fade_gradient(shader_smooth, cx, fade_x2,
                                            content_top - fade_h, fade_h, colors['info_panel_bg'], 'DOWN')
                    if scroll_offset < info_max_scroll:
                        _draw_fade_gradient(shader_smooth, cx, fade_x2,
                                            content_bottom, fade_h, colors['info_panel_bg'], 'UP')
        else:
            state._info_panel_max_scroll = 0
            blf.color(font_id, *colors['text_dim'])
            no_bind_text, _, _ = _truncate_text(font_id, "No bindings found", info_w - sp6 * 2)
            blf.position(font_id, info_x + sp6, info_y + info_h - 2 * info_font_size - sp5, 0)
            blf.draw(font_id, no_bind_text)
    else:
        state._info_panel_max_scroll = 0
        blf.color(font_id, *colors['text_dim'])
        help_text = "Hover a key to see bindings  \u00b7  Right-click to edit  \u00b7  / Search  \u00b7  ? Find by shortcut"
        display_help, _, _ = _truncate_text(font_id, help_text, info_w - sp5 * 2)
        blf.position(font_id, info_x + sp5, info_y + info_h / 2 - info_font_size / 2, 0)
        blf.draw(font_id, display_help)


def _draw_capture_overlay(ctx, kb_bounds):
    """Section H: capture overlay + shortcut search overlay."""
    shader_uniform = ctx.shader_uniform
    font_id = ctx.font_id
    colors = ctx.colors
    unit_px = ctx.unit_px
    now = ctx.now
    rw, rh = ctx.rw, ctx.rh
    s = ctx.s
    sp2, sp5, pad = s.sp2, s.sp5, s.pad
    font_base = ctx.font_base
    font_xl = ctx.font_xl
    info_font_size = font_base
    min_x, max_x, min_y, max_y = kb_bounds

    # --- H. Capture overlay (Phase 5: soft dim instead of black overlay) ---
    if state._modal_state == 'CAPTURE':
        rb = ctx.rb
        dim_overlay = (0.0, 0.0, 0.0, 0.5)
        for ki, kr in enumerate(state._key_rects):
            if ki == state._capture_target_key_index:
                continue
            rb.add(kr.x, kr.y, kr.w, kr.h, dim_overlay)
        rb.flush(ctx.shader_smooth)

        # Pulsing border on target key
        if 0 <= state._capture_target_key_index < len(state._key_rects):
            tkr = state._key_rects[state._capture_target_key_index]
            pulse = 0.5 + 0.5 * math.sin(now * 2 * math.pi * 1.5)
            pulse_col = _lerp_color(colors['border_highlight'], colors['capture_text'], pulse)
            gpu.state.line_width_set(2.0)
            _draw_rect_border(shader_uniform, tkr.x, tkr.y, tkr.w, tkr.h, pulse_col)
            gpu.state.line_width_set(1.0)

        # Draw text above keyboard (toolbar area) instead of screen center
        cap_font_size = font_xl
        blf.size(font_id, cap_font_size)
        blf.color(font_id, *colors['capture_text'])
        cap_text = "Press new key combination\u2026"
        tw, th = blf.dimensions(font_id, cap_text)
        text_y = max_y + pad + sp5
        if state._export_button_rect:
            text_y = max(text_y, state._export_button_rect[1] + state._export_button_rect[3] + sp5)
        blf.position(font_id, (rw - tw) / 2, text_y, 0)
        blf.draw(font_id, cap_text)

        # Subtitle
        blf.size(font_id, font_base)
        blf.color(font_id, *colors['text_dim'])
        sub_text = "ESC to cancel"
        tw2, th2 = blf.dimensions(font_id, sub_text)
        blf.position(font_id, (rw - tw2) / 2, text_y - cap_font_size - sp2, 0)
        blf.draw(font_id, sub_text)

    # --- v0.9 Feature 5: Shortcut search overlay ---
    if state._shortcut_search_active:
        _draw_centered_overlay(shader_uniform, font_id, rw, rh, unit_px, info_font_size,
                               colors, "Press any key combination to find its binding\u2026",
                               'shortcut_search_text', "ESC to cancel")


def _draw_conflict_panel(ctx):
    """Section I: conflict resolution overlay."""
    shader_uniform = ctx.shader_uniform
    font_id = ctx.font_id
    colors = ctx.colors
    unit_px = ctx.unit_px
    rw, rh = ctx.rw, ctx.rh
    s = ctx.s
    sp3, sp6 = s.sp3, s.sp6
    font_base = ctx.font_base
    font_lg = ctx.font_lg
    info_font_size = font_base

    if state._modal_state != 'CONFLICT':
        return

    rb = ctx.rb
    lb = ctx.lb

    rb.add(0, 0, rw, rh, colors['capture_overlay'])

    panel_w = min(500, rw * 0.7)
    panel_h = min(300, rh * 0.5)
    panel_x = (rw - panel_w) / 2
    panel_y = (rh - panel_h) / 2

    rb.add(panel_x, panel_y, panel_w, panel_h, colors['conflict_bg'])
    lb.add(panel_x, panel_y, panel_w, panel_h, colors['border'])

    btn_w = max(80, int(unit_px * 1.5))
    btn_h = max(24, int(unit_px * 0.45))
    btn_y = panel_y + sp6
    btn_gap = sp6
    total_btn_w = 3 * btn_w + 2 * btn_gap
    btn_start_x = panel_x + (panel_w - total_btn_w) / 2

    btn_labels = [("Swap", "SWAP"), ("Override", "OVERRIDE"), ("Cancel", "CANCEL")]
    state._conflict_button_rects.clear()
    for bi, (blabel, baction) in enumerate(btn_labels):
        bx = btn_start_x + bi * (btn_w + btn_gap)
        bcol = colors['button_hover'] if bi == state._conflict_hovered_button else colors['button_normal']
        rb.add(bx, btn_y, btn_w, btn_h, bcol)
        lb.add(bx, btn_y, btn_w, btn_h, colors['border'])
        state._conflict_button_rects.append((blabel, baction, bx, btn_y, btn_w, btn_h))

    rb.flush(ctx.shader_smooth)
    lb.flush(ctx.shader_smooth)

    hdr_size = font_lg
    blf.size(font_id, hdr_size)
    blf.color(font_id, *colors['conflict_header'])
    hdr_text = "Key Conflict"
    tw, th = blf.dimensions(font_id, hdr_text)
    blf.position(font_id, panel_x + (panel_w - tw) / 2, panel_y + panel_h - int(unit_px * 0.55), 0)
    blf.draw(font_id, hdr_text)

    blf.size(font_id, info_font_size)
    blf.color(font_id, *colors['text'])
    src_kmi = state._conflict_data.get('source_kmi')
    if src_kmi:
        src_text = f"Rebinding {src_kmi.idname} \u2192 {state._conflict_data['new_type']}"
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
        src_display, _, _ = _truncate_text(font_id, src_text, panel_w - sp6 * 2)
        blf.position(font_id, panel_x + sp6, panel_y + panel_h - int(unit_px * 0.9), 0)
        blf.draw(font_id, src_display)

    blf.color(font_id, *colors['text_dim'])
    conflicts = state._conflict_data.get('conflicts', [])
    for ci, (ckm_name, ckmi) in enumerate(conflicts[:5]):
        cy = panel_y + panel_h - int(unit_px * 1.3) - ci * (info_font_size + sp3)
        conflict_line = f"  \u2022 {ckmi.idname} ({ckm_name})"
        conflict_display, _, _ = _truncate_text(font_id, conflict_line, panel_w - sp6 * 2)
        blf.position(font_id, panel_x + sp6, cy, 0)
        blf.draw(font_id, conflict_display)

    for blabel, baction, bx, _, btn_w, btn_h in state._conflict_button_rects:
        blf.size(font_id, info_font_size)
        blf.color(font_id, *colors['text'])
        tw, th = blf.dimensions(font_id, blabel)
        blf.position(font_id, bx + (btn_w - tw) / 2, btn_y + (btn_h - th) / 2, 0)
        blf.draw(font_id, blabel)


def _draw_context_menu(ctx):
    """Section J + Operator flyout: GPU context menu and flyout."""
    shader_uniform = ctx.shader_uniform
    shader_smooth = ctx.shader_smooth
    font_id = ctx.font_id
    colors = ctx.colors
    unit_px = ctx.unit_px
    s = ctx.s
    sp2, sp3, sp5 = s.sp2, s.sp3, s.sp5
    font_base = ctx.font_base
    info_font_size = font_base
    rb = ctx.rb

    # --- J. GPU-drawn context menu (humanized + flyout) ---
    if state._modal_state == 'MENU_OPEN' and state._gpu_menu_items:
        # Draw main menu background with drop shadow
        menu_items = state._gpu_menu_items
        menu_y_min = min(item[3] for item in menu_items)
        menu_y_max = max(item[3] + item[5] for item in menu_items)
        menu_bg_x = menu_items[0][2] - sp2
        menu_bg_y = menu_y_min - sp2
        menu_bg_w = menu_items[0][4] + sp2 * 2
        menu_bg_h = (menu_y_max - menu_y_min) + sp2 * 2

        shadow_off = max(3, sp2)

        # Batch: shadow + bg + border + all item rects
        rb.add(menu_bg_x + shadow_off, menu_bg_y - shadow_off,
               menu_bg_w, menu_bg_h, colors['shadow'])
        rb.add(menu_bg_x, menu_bg_y, menu_bg_w, menu_bg_h, colors['menu_bg'])

        all_bindings = state._menu_context.get('all_bindings', [])
        menu_font_size = info_font_size

        # Pre-compute text layout data while batching rects
        text_items = []
        for mi_idx, item in enumerate(menu_items):
            mlabel, mbind_idx, mx, my, mw, mh, m_is_active = item
            is_flyout_target = (mi_idx == state._flyout_target_index)
            is_hovered = (mi_idx == state._gpu_menu_hovered)
            mcol = colors['menu_hover'] if (is_flyout_target or is_hovered) else colors['menu_bg']
            rb.add(mx, my, mw, mh, mcol)
            text_items.append((mlabel, mbind_idx, mx, my, mw, mh, m_is_active))

        # Flyout rects (if present)
        fly_text_items = []
        fly_action_font_size = max(10, int(info_font_size * 0.9))
        if state._gpu_flyout_items:
            fly_items = state._gpu_flyout_items
            fly_y_min = min(fi[3] for fi in fly_items)
            fly_y_max = max(fi[3] + fi[5] for fi in fly_items)
            fly_bg_x = fly_items[0][2] - sp2
            fly_bg_y = fly_y_min - sp2
            fly_bg_w = fly_items[0][4] + sp2 * 2
            fly_bg_h = (fly_y_max - fly_y_min) + sp2 * 2

            rb.add(fly_bg_x + shadow_off, fly_bg_y - shadow_off,
                   fly_bg_w, fly_bg_h, colors['shadow'])
            rb.add(fly_bg_x, fly_bg_y, fly_bg_w, fly_bg_h, colors['menu_bg'])

            for fi_idx, fitem in enumerate(fly_items):
                flabel, faction, fx, fy, fw, fh, fbind_idx = fitem
                fcol = colors['menu_hover'] if fi_idx == state._gpu_flyout_hovered else colors['menu_bg']
                rb.add(fx, fy, fw, fh, fcol)
                fly_text_items.append((flabel, fx, fy, fw, fh))

        # Flush all menu/flyout rects + borders in one batch
        rb.flush(shader_smooth)

        # Draw menu borders (lightweight — just 2 line draw calls)
        _draw_rect_border(shader_uniform, menu_bg_x, menu_bg_y, menu_bg_w, menu_bg_h, colors['menu_border'])
        if state._gpu_flyout_items:
            _draw_rect_border(shader_uniform, fly_bg_x, fly_bg_y, fly_bg_w, fly_bg_h, colors['menu_border'])

        # Now draw all text + icons (after rects are rendered)
        for mlabel, mbind_idx, mx, my, mw, mh, m_is_active in text_items:
            menu_icon_size = int(mh * 0.7)
            menu_text_x = mx + sp5
            if 0 <= mbind_idx < len(all_bindings) and len(all_bindings[mbind_idx]) > 5:
                menu_icon_tex = get_km_icon(all_bindings[mbind_idx][5])
                _draw_icon(menu_icon_tex, mx + sp3, my + (mh - menu_icon_size) / 2, menu_icon_size)
                if menu_icon_tex:
                    menu_text_x = mx + menu_icon_size + sp5

            blf.size(font_id, menu_font_size)
            if m_is_active:
                blf.color(font_id, *colors['text'])
            else:
                blf.color(font_id, *colors['text_dim'])
            tw, th = blf.dimensions(font_id, mlabel)
            blf.position(font_id, menu_text_x, my + (mh - th) / 2, 0)
            blf.draw(font_id, mlabel)

        # Draw flyout text
        for flabel, fx, fy, fw, fh in fly_text_items:
            blf.size(font_id, fly_action_font_size)
            blf.color(font_id, *colors['text'])
            ftw, fth = blf.dimensions(font_id, flabel)
            blf.position(font_id, fx + sp5, fy + (fh - fth) / 2, 0)
            blf.draw(font_id, flabel)

    # --- Operator flyout menu ---
    _draw_op_flyout(ctx)


# ---------------------------------------------------------------------------
# Main draw callback (orchestrator)
# ---------------------------------------------------------------------------

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

        # Clear text truncation cache only when labels actually change.
        # Layout changes produce natural cache misses via different max_width keys.
        if state._dirty_flags & DirtyFlag.KEY_LABELS or len(state._truncation_cache) > 500:
            state._truncation_cache = {}

        # Feature 3: Compute bound keys, key labels, key categories, badges
        with prof("compute_caches"):
            _compute_bound_keys()
            _compute_key_labels()
            _compute_key_categories()
            _compute_key_editor_icons()
            _compute_key_modifier_badges()
            _compute_key_hold_badges()
            _compute_diff_keys()

        if state._dirty_flags & DirtyFlag.COLORS or state._colors_cache is None:
            state._colors_cache = _get_colors()
            state._category_colors_enabled_cache = _get_category_colors_enabled()
            state._dirty_flags &= ~DirtyFlag.COLORS
        colors = state._colors_cache
        category_colors_enabled = state._category_colors_enabled_cache
        gpu.state.blend_set('ALPHA')

        shader_uniform = _get_shader_uniform()
        shader_smooth = _get_shader_smooth()

        unit_px = min(rw / 24, rh / 12) * state._user_scale

        # Centralized spacing
        s = _compute_spacing(unit_px)

        # Consolidated font sizes (5 tiers)
        font_xs   = max(9, int(unit_px * 0.18))    # operator items, badges
        font_sm   = max(10, int(unit_px * 0.22))   # list panel items
        font_base = max(11, int(unit_px * 0.28))   # info panel text, menus
        font_lg   = max(13, int(unit_px * 0.38))   # info panel header
        font_xl   = max(15, int(unit_px * 0.50))   # overlay text

        font_id = _ensure_font_loaded()

        # Build shared draw context with batchers
        rb = RectBatcher()
        lb = LineBatcher()
        ib = IconBatcher()
        ctx = DrawContext(
            shader_uniform=shader_uniform,
            shader_smooth=shader_smooth,
            font_id=font_id,
            unit_px=unit_px,
            colors=colors,
            s=s,
            rw=rw,
            rh=rh,
            font_xs=font_xs,
            font_sm=font_sm,
            font_base=font_base,
            font_lg=font_lg,
            font_xl=font_xl,
            category_colors_enabled=category_colors_enabled,
            now=now,
            rb=rb,
            lb=lb,
            ib=ib,
        )

        # --- Draw sections ---
        prof.begin_frame()
        with prof("background_plate"):
            kb_bounds = _draw_background_plate(ctx)
        with prof("toolbar"):
            _draw_toolbar(ctx, kb_bounds)
        # Flush bg + toolbar geometry together, then draw their text
        with prof("bg_toolbar_text"):
            _draw_background_text(ctx)
        with prof("key_shadows"):
            _draw_key_shadows(ctx)
        with prof("key_rectangles"):
            key_bg_colors = _draw_key_rectangles(ctx)
        with prof("key_labels"):
            _draw_key_labels(ctx, key_bg_colors)
        with prof("side_panels"):
            _draw_side_panels(ctx, kb_bounds)
        with prof("info_panel"):
            _draw_info_panel(ctx, kb_bounds)
        with prof("capture_overlay"):
            _draw_capture_overlay(ctx, kb_bounds)
        with prof("conflict_panel"):
            _draw_conflict_panel(ctx)
        with prof("context_menu"):
            _draw_context_menu(ctx)

        gpu.state.blend_set('NONE')
        prof.end_frame()
    except Exception:
        _log.error("Draw callback failed", exc_info=True)
