"""
Keymap Visualizer – Full Implementation (Phases 1-7)
Opens a dedicated window with a full keyboard layout, hover/click interaction,
modifier toggles, binding info panel, context menu editing, conflict resolution,
export, search/filter, and color customization.
Requires Blender 4.2+ (tested against 5.0 API).
"""

bl_info = {
    "name": "Keymap Visualizer",
    "author": "blenderKey",
    "version": (0, 7, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Header",
    "description": "Visual keyboard-based keymap editor",
    "category": "System",
}

import bpy
import gpu
import blf
import os
import time
from bpy.props import StringProperty, EnumProperty, FloatVectorProperty
from gpu_extras.batch import batch_for_shader
from collections import namedtuple

# ---------------------------------------------------------------------------
# KeyRect namedtuple
# ---------------------------------------------------------------------------
KeyRect = namedtuple('KeyRect', ['label', 'event_type', 'x', 'y', 'w', 'h'])

# ---------------------------------------------------------------------------
# Keyboard layout data
# Each row is a list of tuples: (label, blender_event_type, width_units)
# Bare floats represent horizontal gaps in unit widths.
# ---------------------------------------------------------------------------
KEYBOARD_ROWS = [
    # Row 0 (bottom): modifier/space row
    [
        ("Ctrl", "LEFT_CTRL", 1.25),
        ("Win", "OSKEY", 1.25),
        ("Alt", "LEFT_ALT", 1.25),
        ("Space", "SPACE", 6.25),
        ("Alt", "RIGHT_ALT", 1.25),
        ("Win", "OSKEY", 1.25),
        ("Menu", "APP", 1.25),
        ("Ctrl", "RIGHT_CTRL", 1.25),
    ],
    # Row 1: shift row
    [
        ("LShift", "LEFT_SHIFT", 2.25),
        ("Z", "Z", 1.0),
        ("X", "X", 1.0),
        ("C", "C", 1.0),
        ("V", "V", 1.0),
        ("B", "B", 1.0),
        ("N", "N", 1.0),
        ("M", "M", 1.0),
        (",", "COMMA", 1.0),
        (".", "PERIOD", 1.0),
        ("/", "SLASH", 1.0),
        ("RShift", "RIGHT_SHIFT", 2.75),
    ],
    # Row 2: home row
    [
        ("Caps", "CAPS_LOCK", 1.75),
        ("A", "A", 1.0),
        ("S", "S", 1.0),
        ("D", "D", 1.0),
        ("F", "F", 1.0),
        ("G", "G", 1.0),
        ("H", "H", 1.0),
        ("J", "J", 1.0),
        ("K", "K", 1.0),
        ("L", "L", 1.0),
        (";", "SEMI_COLON", 1.0),
        ("'", "QUOTE", 1.0),
        ("Enter", "RET", 2.25),
    ],
    # Row 3: QWERTY row
    [
        ("Tab", "TAB", 1.5),
        ("Q", "Q", 1.0),
        ("W", "W", 1.0),
        ("E", "E", 1.0),
        ("R", "R", 1.0),
        ("T", "T", 1.0),
        ("Y", "Y", 1.0),
        ("U", "U", 1.0),
        ("I", "I", 1.0),
        ("O", "O", 1.0),
        ("P", "P", 1.0),
        ("[", "LEFT_BRACKET", 1.0),
        ("]", "RIGHT_BRACKET", 1.0),
        ("\\", "BACK_SLASH", 1.5),
    ],
    # Row 4: number row
    [
        ("`", "ACCENT_GRAVE", 1.0),
        ("1", "ONE", 1.0),
        ("2", "TWO", 1.0),
        ("3", "THREE", 1.0),
        ("4", "FOUR", 1.0),
        ("5", "FIVE", 1.0),
        ("6", "SIX", 1.0),
        ("7", "SEVEN", 1.0),
        ("8", "EIGHT", 1.0),
        ("9", "NINE", 1.0),
        ("0", "ZERO", 1.0),
        ("-", "MINUS", 1.0),
        ("=", "EQUAL", 1.0),
        ("Bksp", "BACK_SPACE", 2.0),
    ],
    # Row 5: function row
    [
        ("Esc", "ESC", 1.0),
        1.0,  # gap
        ("F1", "F1", 1.0),
        ("F2", "F2", 1.0),
        ("F3", "F3", 1.0),
        ("F4", "F4", 1.0),
        0.5,  # gap
        ("F5", "F5", 1.0),
        ("F6", "F6", 1.0),
        ("F7", "F7", 1.0),
        ("F8", "F8", 1.0),
        0.5,  # gap
        ("F9", "F9", 1.0),
        ("F10", "F10", 1.0),
        ("F11", "F11", 1.0),
        ("F12", "F12", 1.0),
    ],
]

# Navigation cluster rows (rendered to the right of main block)
NAV_CLUSTER_ROWS = [
    # Row 0 (bottom, aligned with shift row)
    [
        ("Left", "LEFT_ARROW", 1.0),
        ("Down", "DOWN_ARROW", 1.0),
        ("Right", "RIGHT_ARROW", 1.0),
    ],
    # Row 1 (aligned with home row)
    [
        1.0,  # gap to center Up arrow above Down arrow
        ("Up", "UP_ARROW", 1.0),
    ],
    # Row 2 (aligned with QWERTY row): End / PgDn
    [
        ("End", "END", 1.0),
        ("PgDn", "PAGE_DOWN", 1.0),
    ],
    # Row 3 (aligned with number row): Home / PgUp
    [
        ("Home", "HOME", 1.0),
        ("PgUp", "PAGE_UP", 1.0),
    ],
    # Row 4 (aligned with function row): Ins / Del
    [
        ("Ins", "INSERT", 1.0),
        ("Del", "DEL", 1.0),
    ],
]

# Nav cluster row alignment: index into KEYBOARD_ROWS
NAV_ROW_ALIGNMENT = [0, 1, 3, 4, 5]

# Modifier event types for identification
_MODIFIER_EVENTS = {
    "LEFT_CTRL", "RIGHT_CTRL", "LEFT_SHIFT", "RIGHT_SHIFT",
    "LEFT_ALT", "RIGHT_ALT", "OSKEY",
}

# ---------------------------------------------------------------------------
# Capturable keys whitelist (Phase 5)
# ---------------------------------------------------------------------------
_CAPTURABLE_KEYS = {
    # Letters
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    # Numbers
    'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE',
    # Function keys
    'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
    'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F20', 'F21', 'F22', 'F23', 'F24',
    # Special
    'TAB', 'RET', 'SPACE', 'BACK_SPACE', 'DEL', 'INSERT', 'HOME', 'END',
    'PAGE_UP', 'PAGE_DOWN',
    # Arrows
    'LEFT_ARROW', 'RIGHT_ARROW', 'UP_ARROW', 'DOWN_ARROW',
    # Punctuation
    'SEMI_COLON', 'PERIOD', 'COMMA', 'QUOTE', 'ACCENT_GRAVE',
    'MINUS', 'EQUAL', 'SLASH', 'BACK_SLASH', 'LEFT_BRACKET', 'RIGHT_BRACKET',
    # Numpad
    'NUMPAD_0', 'NUMPAD_1', 'NUMPAD_2', 'NUMPAD_3', 'NUMPAD_4',
    'NUMPAD_5', 'NUMPAD_6', 'NUMPAD_7', 'NUMPAD_8', 'NUMPAD_9',
    'NUMPAD_PERIOD', 'NUMPAD_ENTER', 'NUMPAD_PLUS', 'NUMPAD_MINUS',
    'NUMPAD_ASTERIX', 'NUMPAD_SLASH',
    # Other
    'CAPS_LOCK', 'APP',
}

# ---------------------------------------------------------------------------
# Re-entrant guard
# ---------------------------------------------------------------------------
_visualizer_running = False


def _set_running(state: bool):
    global _visualizer_running
    _visualizer_running = state


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_draw_handle = None
_target_area = None
_key_rects = []                    # list of KeyRect
_cached_region_size = (0, 0)
_hovered_key_index = -1
_selected_key_index = -1
_active_modifiers = {'ctrl': False, 'shift': False, 'alt': False, 'oskey': False}
_modifier_rects = []               # list of (label, dict_key, x, y, w, h)
_cached_bindings = []              # cached binding results
_bindings_key = None               # (event_type, mod_tuple) used to cache

# Phase 5: State machine
_modal_state = 'IDLE'  # IDLE, MENU_OPEN, CAPTURE, CONFLICT
_menu_context = {}
_conflict_data = {
    'new_type': None, 'new_ctrl': False, 'new_shift': False, 'new_alt': False,
    'new_oskey': False, 'source_kmi': None, 'source_km_name': None, 'conflicts': []
}
_conflict_button_rects = []  # list of (label, action, x, y, w, h)
_conflict_hovered_button = -1

# GPU-drawn context menu
_gpu_menu_items = []  # list of (label, action, x, y, w, h)
_gpu_menu_hovered = -1

# Phase 6: Export button
_export_button_rect = None  # (x, y, w, h)
_export_hovered = False

# Phase 7: Search
_search_text = ''
_search_active = False
_search_matching_keys = set()  # set of event_type strings
_search_last_update = 0.0

# Phase 7: Batch cache
_batch_dirty = True

# Phase 7: Hover transition
_hover_transition = 0.0
_hover_transition_target = -1
_last_frame_time = 0.0

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
COL_BG = (0.12, 0.12, 0.12, 0.95)
COL_KEY_DEFAULT = (0.25, 0.25, 0.28, 1.0)
COL_KEY_HOVER = (0.35, 0.45, 0.6, 1.0)
COL_KEY_SELECTED = (0.2, 0.5, 0.9, 1.0)
COL_KEY_MODIFIER = (0.3, 0.28, 0.25, 1.0)
COL_KEY_INACTIVE = (0.18, 0.18, 0.20, 1.0)
COL_BORDER = (0.4, 0.4, 0.42, 1.0)
COL_BORDER_HIGHLIGHT = (0.7, 0.8, 1.0, 1.0)
COL_TEXT = (1.0, 1.0, 1.0, 1.0)
COL_TEXT_DIM = (0.7, 0.7, 0.7, 0.9)
COL_TOGGLE_ACTIVE = (0.2, 0.5, 0.9, 1.0)
COL_TOGGLE_INACTIVE = (0.22, 0.22, 0.25, 1.0)
COL_INFO_BG = (0.15, 0.15, 0.18, 0.9)
COL_CAPTURE_OVERLAY = (0.0, 0.0, 0.0, 0.6)
COL_CAPTURE_TEXT = (1.0, 0.9, 0.3, 1.0)
COL_CONFLICT_BG = (0.1, 0.1, 0.12, 0.95)
COL_CONFLICT_HEADER = (1.0, 0.4, 0.3, 1.0)
COL_BUTTON_NORMAL = (0.3, 0.3, 0.35, 1.0)
COL_BUTTON_HOVER = (0.4, 0.5, 0.65, 1.0)
COL_EXPORT_BUTTON = (0.25, 0.35, 0.25, 1.0)
COL_EXPORT_BUTTON_HOVER = (0.3, 0.5, 0.3, 1.0)
COL_SHADOW = (0.0, 0.0, 0.0, 0.3)
COL_SEARCH_BG = (0.18, 0.18, 0.22, 0.95)
COL_SEARCH_BORDER = (0.4, 0.5, 0.7, 1.0)
COL_GPU_MENU_BG = (0.15, 0.15, 0.18, 0.98)
COL_GPU_MENU_HOVER = (0.3, 0.4, 0.55, 1.0)
COL_GPU_MENU_BORDER = (0.4, 0.4, 0.45, 1.0)


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


def _invalidate_cache():
    """Invalidate binding cache and mark batches dirty."""
    global _bindings_key, _batch_dirty
    _bindings_key = None
    _batch_dirty = True


# ---------------------------------------------------------------------------
# Layout engine
# ---------------------------------------------------------------------------
def _compute_keyboard_layout(region_width, region_height):
    """Compute KeyRect list for all keys, centered in the region."""
    global _key_rects, _cached_region_size, _modifier_rects, _export_button_rect, _batch_dirty

    _cached_region_size = (region_width, region_height)
    _key_rects = []
    _modifier_rects = []
    _batch_dirty = True

    # Unit size: fit ~20 units across with padding, cap at 50px
    unit_px = min(region_width / 22, 50)
    if unit_px < 8:
        return  # Too small to render
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
                _key_rects.append(KeyRect(label, event_type, x, y, w, h))
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
                _key_rects.append(KeyRect(label, event_type, x, y, w, h))
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
        _modifier_rects.append((label, key, tx, toggle_y, toggle_w, toggle_h))

    # Export button (to the right of modifier toggles)
    if _modifier_rects:
        last_mod = _modifier_rects[-1]
        ex_x = last_mod[2] + last_mod[4] + toggle_gap * 2
        ex_w = unit_px * 2.5
        _export_button_rect = (ex_x, toggle_y, ex_w, toggle_h)
    else:
        _export_button_rect = None


# ---------------------------------------------------------------------------
# Hit testing
# ---------------------------------------------------------------------------
def _hit_test_key(mx, my):
    """Returns index into _key_rects or -1."""
    for i, kr in enumerate(_key_rects):
        if kr.x <= mx <= kr.x + kr.w and kr.y <= my <= kr.y + kr.h:
            return i
    return -1


def _hit_test_modifier(mx, my):
    """Returns dict_key string or None."""
    for label, dict_key, x, y, w, h in _modifier_rects:
        if x <= mx <= x + w and y <= my <= y + h:
            return dict_key
    return None


def _hit_test_export(mx, my):
    """Returns True if click is on export button."""
    if _export_button_rect is None:
        return False
    x, y, w, h = _export_button_rect
    return x <= mx <= x + w and y <= my <= y + h


def _hit_test_conflict_buttons(mx, my):
    """Returns button index or -1."""
    for i, (label, action, x, y, w, h) in enumerate(_conflict_button_rects):
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1


def _hit_test_gpu_menu(mx, my):
    """Returns menu item index or -1."""
    for i, (label, action, x, y, w, h) in enumerate(_gpu_menu_items):
        if x <= mx <= x + w and y <= my <= y + h:
            return i
    return -1


# ---------------------------------------------------------------------------
# Keymap query (Phase 5: returns KMI references + inactive bindings)
# ---------------------------------------------------------------------------
def _get_bindings_for_key(event_type, modifiers):
    """Return list of (keymap_name, operator_idname, modifier_string, kmi, is_active)."""
    global _cached_bindings, _bindings_key

    mod_tuple = (modifiers['ctrl'], modifiers['shift'], modifiers['alt'], modifiers['oskey'])
    cache_key = (event_type, mod_tuple)
    if _bindings_key == cache_key:
        return _cached_bindings

    results = []
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        _cached_bindings = results
        _bindings_key = cache_key
        return results

    any_mod_active = any(mod_tuple)

    for km in kc.keymaps:
        for kmi in km.keymap_items:
            if kmi.type != event_type:
                continue
            # Filter by modifiers if any toggle is active
            if any_mod_active:
                if kmi.ctrl != modifiers['ctrl']:
                    continue
                if kmi.shift != modifiers['shift']:
                    continue
                if kmi.alt != modifiers['alt']:
                    continue
                if kmi.oskey != modifiers['oskey']:
                    continue

            # Build modifier string
            mod_parts = []
            if kmi.ctrl:
                mod_parts.append("Ctrl")
            if kmi.shift:
                mod_parts.append("Shift")
            if kmi.alt:
                mod_parts.append("Alt")
            if kmi.oskey:
                mod_parts.append("OS")
            mod_str = "+".join(mod_parts) if mod_parts else ""

            results.append((km.name, kmi.idname, mod_str, kmi, kmi.active))
            if len(results) >= 20:
                break
        if len(results) >= 20:
            break

    _cached_bindings = results
    _bindings_key = cache_key
    return results


# ---------------------------------------------------------------------------
# Conflict detection (Phase 5)
# ---------------------------------------------------------------------------
def _find_conflicts(event_type, ctrl, shift, alt, oskey, exclude_kmi=None):
    """Find active KMIs matching key+modifiers. Returns list of (km_name, kmi)."""
    conflicts = []
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return conflicts

    for km in kc.keymaps:
        for kmi in km.keymap_items:
            if not kmi.active:
                continue
            if kmi is exclude_kmi:
                continue
            if kmi.type == event_type and kmi.ctrl == ctrl and kmi.shift == shift \
                    and kmi.alt == alt and kmi.oskey == oskey:
                conflicts.append((km.name, kmi))
                if len(conflicts) >= 10:
                    return conflicts
    return conflicts


# ---------------------------------------------------------------------------
# Apply functions (Phase 5)
# ---------------------------------------------------------------------------
def _apply_rebind(kmi, new_type, new_ctrl, new_shift, new_alt, new_oskey):
    """Set kmi key type and modifiers. Preserves kmi.value (PRESS/RELEASE/CLICK etc.)."""
    kmi.type = new_type
    kmi.ctrl = new_ctrl
    kmi.shift = new_shift
    kmi.alt = new_alt
    kmi.oskey = new_oskey
    _invalidate_cache()


def _reset_kmi_to_default(kmi, km_name):
    """Find matching KMI in wm.keyconfigs.default by idname, copy type/value/modifiers back."""
    wm = bpy.context.window_manager
    kc_default = wm.keyconfigs.default
    if kc_default is None:
        return False

    for km in kc_default.keymaps:
        if km.name != km_name:
            continue
        for default_kmi in km.keymap_items:
            if default_kmi.idname == kmi.idname:
                kmi.type = default_kmi.type
                kmi.value = default_kmi.value
                kmi.ctrl = default_kmi.ctrl
                kmi.shift = default_kmi.shift
                kmi.alt = default_kmi.alt
                kmi.oskey = default_kmi.oskey
                kmi.active = True
                _invalidate_cache()
                return True
    return False


# ---------------------------------------------------------------------------
# Search filter (Phase 7)
# ---------------------------------------------------------------------------
def _update_search_filter():
    """Update _search_matching_keys based on _search_text."""
    global _search_matching_keys, _batch_dirty
    _search_matching_keys = set()

    if not _search_text:
        _batch_dirty = True
        return

    query = _search_text.lower()
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        _batch_dirty = True
        return

    for km in kc.keymaps:
        for kmi in km.keymap_items:
            if not kmi.active:
                continue
            if query in kmi.idname.lower() or query in kmi.name.lower():
                _search_matching_keys.add(kmi.type)

    _batch_dirty = True


# ---------------------------------------------------------------------------
# Export functions (Phase 6)
# ---------------------------------------------------------------------------
def _kmi_to_properties_dict(kmi):
    """Extract serializable operator properties from a KMI."""
    props = {}
    try:
        if kmi.properties is not None:
            for prop_name in kmi.properties.bl_rna.properties.keys():
                if prop_name == 'rna_type':
                    continue
                try:
                    val = getattr(kmi.properties, prop_name)
                    # Convert non-serializable types
                    if hasattr(val, 'to_list'):
                        val = val.to_list()
                    elif hasattr(val, 'to_dict'):
                        val = val.to_dict()
                    props[prop_name] = val
                except Exception:
                    pass
    except Exception:
        pass
    return props


def _kmi_is_modified(kmi, km_name):
    """Compare user KMI against default to detect modifications."""
    wm = bpy.context.window_manager
    kc_default = wm.keyconfigs.default
    if kc_default is None:
        return True  # Can't compare, assume modified

    for km in kc_default.keymaps:
        if km.name != km_name:
            continue
        for default_kmi in km.keymap_items:
            if default_kmi.idname == kmi.idname:
                if (kmi.type != default_kmi.type or kmi.value != default_kmi.value or
                        kmi.ctrl != default_kmi.ctrl or kmi.shift != default_kmi.shift or
                        kmi.alt != default_kmi.alt or kmi.oskey != default_kmi.oskey or
                        kmi.active != default_kmi.active):
                    return True
                return False
    return True  # Not found in default, consider modified


def _generate_keyconfig_data(scope='MODIFIED'):
    """Generate Blender-compatible keyconfig_data list."""
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return []

    keyconfig_data = []
    for km in kc.keymaps:
        items = []
        for kmi in km.keymap_items:
            if scope == 'MODIFIED' and not _kmi_is_modified(kmi, km.name):
                continue

            kmi_data = {
                "type": kmi.type,
                "value": kmi.value,
                "ctrl": kmi.ctrl,
                "shift": kmi.shift,
                "alt": kmi.alt,
                "oskey": kmi.oskey,
                "key_modifier": kmi.key_modifier,
                "repeat": kmi.repeat,
            }
            props = _kmi_to_properties_dict(kmi)
            items.append((kmi.idname, kmi_data, props))

        if items:
            km_params = {
                "space_type": km.space_type,
                "region_type": km.region_type,
            }
            keyconfig_data.append((km.name, km_params, {"items": items}))

    return keyconfig_data


def _write_export_file(filepath, keyconfig_data):
    """Write a Python script with keyconfig_import_from_data call."""
    abs_path = bpy.path.abspath(filepath)
    dir_path = os.path.dirname(abs_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write("# Keymap export generated by Keymap Visualizer addon\n")
        f.write("import os\n\n")
        f.write("keyconfig_data = \\\n")
        f.write(repr(keyconfig_data))
        f.write("\n\n")
        f.write('if __name__ == "__main__":\n')
        f.write('    from bl_keymap_utils.io import keyconfig_import_from_data\n')
        f.write('    keyconfig_import_from_data(\n')
        f.write('        os.path.splitext(os.path.basename(__file__))[0],\n')
        f.write('        keyconfig_data)\n')

    return abs_path


def _do_export():
    """Run the export using addon preferences settings. Returns (success, message)."""
    try:
        prefs = bpy.context.preferences.addons["keymap_visualizer"].preferences
        filepath = prefs.export_path
        scope = prefs.export_scope
    except Exception:
        filepath = "//custom_keymap.py"
        scope = 'MODIFIED'

    try:
        data = _generate_keyconfig_data(scope)
        if not data:
            return (False, "No keybindings to export")
        abs_path = _write_export_file(filepath, data)
        return (True, f"Exported to {abs_path}")
    except Exception as e:
        return (False, f"Export failed: {e}")


# ---------------------------------------------------------------------------
# GPU menu builder (Phase 5 — GPU-drawn context menu)
# ---------------------------------------------------------------------------
def _build_gpu_menu(mx, my, region_width, region_height):
    """Build GPU-drawn context menu items at mouse position."""
    global _gpu_menu_items, _gpu_menu_hovered
    _gpu_menu_items = []
    _gpu_menu_hovered = -1

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
        _gpu_menu_items.append((label, action, menu_x, iy, item_w, item_h))


# ---------------------------------------------------------------------------
# Draw helpers
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Draw callback
# ---------------------------------------------------------------------------
def _draw_callback():
    """POST_PIXEL draw callback for the text-editor area."""
    global _hover_transition, _hover_transition_target, _last_frame_time

    area = _target_area
    if area is None:
        return

    region = None
    for r in area.regions:
        if r.type == 'WINDOW':
            region = r
            break
    if region is None:
        return

    rw, rh = region.width, region.height

    # Recompute layout if region size changed
    if (rw, rh) != _cached_region_size:
        _compute_keyboard_layout(rw, rh)

    if not _key_rects:
        return

    # Hover transition (Phase 7)
    now = time.monotonic()
    dt = min(now - _last_frame_time, 0.1) if _last_frame_time > 0 else 0.016
    _last_frame_time = now
    if _hovered_key_index != _hover_transition_target:
        _hover_transition_target = _hovered_key_index
        _hover_transition = 0.0
    elif _hover_transition < 1.0:
        _hover_transition = min(1.0, _hover_transition + dt * 8.0)  # ~3 frames at 60fps

    colors = _get_colors()
    gpu.state.blend_set('ALPHA')

    shader_uniform = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')

    # --- A. Background plate ---
    min_x = min(kr.x for kr in _key_rects)
    max_x = max(kr.x + kr.w for kr in _key_rects)
    min_y = min(kr.y for kr in _key_rects)
    max_y = max(kr.y + kr.h for kr in _key_rects)

    if _modifier_rects:
        mod_max_y = max(y + h for _, _, x, y, w, h in _modifier_rects)
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
    for kr in _key_rects:
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
    search_dimming = _search_active and _search_text

    for i, kr in enumerate(_key_rects):
        # Determine color
        if i == _selected_key_index:
            col = colors['key_selected']
        elif i == _hovered_key_index:
            if _hover_transition < 1.0:
                col = _lerp_color(colors['key_default'], colors['key_hovered'], _hover_transition)
            else:
                col = colors['key_hovered']
        elif kr.event_type in _MODIFIER_EVENTS:
            col = COL_KEY_MODIFIER
        else:
            col = colors['key_default']

        # Dim non-matching keys during search
        if search_dimming and kr.event_type not in _search_matching_keys:
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
    for kr in _key_rects:
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
    highlight_idx = _selected_key_index if _selected_key_index >= 0 else _hovered_key_index
    if highlight_idx >= 0:
        kr = _key_rects[highlight_idx]
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
        for i, kr in enumerate(_key_rects):
            if search_dimming and kr.event_type not in _search_matching_keys:
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
    for label, dict_key, mx, my, mw, mh in _modifier_rects:
        is_active = _active_modifiers.get(dict_key, False)
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
    if _export_button_rect is not None:
        ex, ey, ew, eh = _export_button_rect
        ex_col = COL_EXPORT_BUTTON_HOVER if _export_hovered else COL_EXPORT_BUTTON
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
    if _search_active:
        sb_w = min(300, rw * 0.4)
        sb_h = unit_px * 0.7
        sb_x = (rw - sb_w) / 2
        sb_y = max_y + pad + 5
        if _modifier_rects:
            mod_max = max(y + h for _, _, x, y, w, h in _modifier_rects)
            sb_y = mod_max + 10

        _draw_rect(shader_uniform, sb_x, sb_y, sb_w, sb_h, COL_SEARCH_BG)
        _draw_rect_border(shader_uniform, sb_x, sb_y, sb_w, sb_h, COL_SEARCH_BORDER)

        if unit_px >= 20:
            blf.size(font_id, font_size)
            blf.color(font_id, *COL_CAPTURE_TEXT)
            search_display = _search_text + "|"
            if not _search_text:
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
    active_idx = _selected_key_index if _selected_key_index >= 0 else _hovered_key_index
    info_font_size = max(10, int(unit_px * 0.28))
    blf.size(font_id, info_font_size)

    if 0 <= active_idx < len(_key_rects):
        kr = _key_rects[active_idx]
        bindings = _get_bindings_for_key(kr.event_type, _active_modifiers)

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
    if _modal_state == 'CAPTURE':
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
    if _modal_state == 'CONFLICT':
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
        src_kmi = _conflict_data.get('source_kmi')
        if src_kmi:
            src_text = f"Rebinding: {src_kmi.idname} -> {_conflict_data['new_type']}"
            mod_parts = []
            if _conflict_data['new_ctrl']:
                mod_parts.append("Ctrl")
            if _conflict_data['new_shift']:
                mod_parts.append("Shift")
            if _conflict_data['new_alt']:
                mod_parts.append("Alt")
            if _conflict_data['new_oskey']:
                mod_parts.append("OS")
            if mod_parts:
                src_text += f" ({'+'.join(mod_parts)})"
            blf.position(font_id, panel_x + 15, panel_y + panel_h - 60, 0)
            blf.draw(font_id, src_text)

        # Conflict list
        blf.color(font_id, *COL_TEXT_DIM)
        conflicts = _conflict_data.get('conflicts', [])
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
        _conflict_button_rects.clear()
        for bi, (blabel, baction) in enumerate(btn_labels):
            bx = btn_start_x + bi * (btn_w + btn_gap)
            bcol = COL_BUTTON_HOVER if bi == _conflict_hovered_button else COL_BUTTON_NORMAL
            _draw_rect(shader_uniform, bx, btn_y, btn_w, btn_h, bcol)
            _draw_rect_border(shader_uniform, bx, btn_y, btn_w, btn_h, COL_BORDER)
            _conflict_button_rects.append((blabel, baction, bx, btn_y, btn_w, btn_h))

            blf.size(font_id, info_font_size)
            blf.color(font_id, *colors['text'])
            tw, th = blf.dimensions(font_id, blabel)
            blf.position(font_id, bx + (btn_w - tw) / 2, btn_y + (btn_h - th) / 2, 0)
            blf.draw(font_id, blabel)

    # --- J. GPU-drawn context menu (Phase 5) ---
    if _modal_state == 'MENU_OPEN' and _gpu_menu_items:
        # Background + border for entire menu
        if _gpu_menu_items:
            first = _gpu_menu_items[0]
            last = _gpu_menu_items[-1]
            menu_bg_x = first[2] - 3
            menu_bg_y = min(item[3] for item in _gpu_menu_items) - 3
            menu_bg_w = first[4] + 6
            menu_bg_h = (max(item[3] + item[5] for item in _gpu_menu_items) - menu_bg_y) + 6

            _draw_rect(shader_uniform, menu_bg_x, menu_bg_y, menu_bg_w, menu_bg_h, COL_GPU_MENU_BG)
            _draw_rect_border(shader_uniform, menu_bg_x, menu_bg_y, menu_bg_w, menu_bg_h,
                              COL_GPU_MENU_BORDER)

        for mi_idx, (mlabel, maction, mx, my, mw, mh) in enumerate(_gpu_menu_items):
            mcol = COL_GPU_MENU_HOVER if mi_idx == _gpu_menu_hovered else COL_GPU_MENU_BG
            _draw_rect(shader_uniform, mx, my, mw, mh, mcol)

            blf.size(font_id, info_font_size)
            blf.color(font_id, *colors['text'])
            tw, th = blf.dimensions(font_id, mlabel)
            blf.position(font_id, mx + 10, my + (mh - th) / 2, 0)
            blf.draw(font_id, mlabel)

    gpu.state.blend_set('NONE')


# ---------------------------------------------------------------------------
# State handlers (Phase 5)
# ---------------------------------------------------------------------------
def _handle_idle(context, event):
    """Handle events in IDLE state. Returns Blender modal return set."""
    global _hovered_key_index, _selected_key_index, _batch_dirty
    global _active_modifiers, _bindings_key, _modal_state, _menu_context
    global _export_hovered, _search_active, _search_text

    if event.type == 'MOUSEMOVE':
        new_hover = _hit_test_key(event.mouse_region_x, event.mouse_region_y)
        new_export_hover = _hit_test_export(event.mouse_region_x, event.mouse_region_y)

        changed = False
        if new_hover != _hovered_key_index:
            _hovered_key_index = new_hover
            _batch_dirty = True
            changed = True
        if new_export_hover != _export_hovered:
            _export_hovered = new_export_hover
            changed = True

        if changed and _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
        mx, my = event.mouse_region_x, event.mouse_region_y

        # Check export button
        if _hit_test_export(mx, my):
            success, msg = _do_export()
            print(f"[Keymap Visualizer] {msg}")
            if _target_area is not None:
                _target_area.tag_redraw()
            return {'RUNNING_MODAL'}

        # Check modifier toggles
        mod_hit = _hit_test_modifier(mx, my)
        if mod_hit is not None:
            _active_modifiers[mod_hit] = not _active_modifiers[mod_hit]
            _invalidate_cache()
            if _target_area is not None:
                _target_area.tag_redraw()
            return {'RUNNING_MODAL'}

        # Check key hit
        key_hit = _hit_test_key(mx, my)
        if key_hit != _selected_key_index:
            _selected_key_index = key_hit
            _batch_dirty = True
            if _target_area is not None:
                _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    # Right-click: context menu
    if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
        mx, my = event.mouse_region_x, event.mouse_region_y
        key_hit = _hit_test_key(mx, my)
        if key_hit >= 0:
            kr = _key_rects[key_hit]
            bindings = _get_bindings_for_key(kr.event_type, _active_modifiers)
            if bindings:
                km_name, op_id, mod_str, kmi, is_active = bindings[0]
                _menu_context.clear()
                _menu_context['target_key_index'] = key_hit
                _menu_context['target_event_type'] = kr.event_type
                _menu_context['target_kmi'] = kmi
                _menu_context['target_km_name'] = km_name
                _menu_context['pending_action'] = None

                # Get region dimensions for menu positioning
                region_w, region_h = _cached_region_size
                _build_gpu_menu(mx, my, region_w, region_h)
                _modal_state = 'MENU_OPEN'
                if _target_area is not None:
                    _target_area.tag_redraw()
            return {'RUNNING_MODAL'}

    # Search activation: / key or Ctrl+F
    if event.type == 'SLASH' and event.value == 'PRESS' and not event.ctrl:
        _search_active = True
        _search_text = ''
        _update_search_filter()
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'F' and event.value == 'PRESS' and event.ctrl:
        _search_active = True
        _search_text = ''
        _update_search_filter()
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    return None  # Not handled


def _handle_menu_open(context, event):
    """Handle events while GPU context menu is open."""
    global _modal_state, _gpu_menu_hovered, _batch_dirty

    if event.type == 'MOUSEMOVE':
        new_hover = _hit_test_gpu_menu(event.mouse_region_x, event.mouse_region_y)
        if new_hover != _gpu_menu_hovered:
            _gpu_menu_hovered = new_hover
            if _target_area is not None:
                _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
        mx, my = event.mouse_region_x, event.mouse_region_y
        menu_hit = _hit_test_gpu_menu(mx, my)

        if menu_hit >= 0:
            label, action = _gpu_menu_items[menu_hit][0], _gpu_menu_items[menu_hit][1]
            kmi = _menu_context.get('target_kmi')
            km_name = _menu_context.get('target_km_name')

            if action == 'REBIND' and kmi:
                _modal_state = 'CAPTURE'
                _menu_context['pending_action'] = 'REBIND'
            elif action == 'UNBIND' and kmi:
                kmi.active = False
                _invalidate_cache()
                _modal_state = 'IDLE'
            elif action == 'RESET' and kmi and km_name:
                _reset_kmi_to_default(kmi, km_name)
                _modal_state = 'IDLE'
            elif action == 'TOGGLE' and kmi:
                kmi.active = not kmi.active
                _invalidate_cache()
                _modal_state = 'IDLE'
            else:
                _modal_state = 'IDLE'
        else:
            # Clicked outside menu — dismiss
            _modal_state = 'IDLE'

        _gpu_menu_items.clear()
        _gpu_menu_hovered = -1
        _batch_dirty = True
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'ESC' and event.value == 'PRESS':
        _modal_state = 'IDLE'
        _gpu_menu_items.clear()
        _gpu_menu_hovered = -1
        _batch_dirty = True
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
        # Dismiss on right-click too
        _modal_state = 'IDLE'
        _gpu_menu_items.clear()
        _gpu_menu_hovered = -1
        _batch_dirty = True
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    return {'RUNNING_MODAL'}


def _handle_capture(context, event):
    """Handle events in CAPTURE state (waiting for key press)."""
    global _modal_state, _batch_dirty

    if event.value != 'PRESS':
        return {'RUNNING_MODAL'}

    if event.type == 'ESC':
        _modal_state = 'IDLE'
        _menu_context.clear()
        _batch_dirty = True
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type in _CAPTURABLE_KEYS:
        new_type = event.type
        new_ctrl = event.ctrl
        new_shift = event.shift
        new_alt = event.alt
        new_oskey = event.oskey

        kmi = _menu_context.get('target_kmi')
        km_name = _menu_context.get('target_km_name')
        if kmi is None:
            _modal_state = 'IDLE'
            return {'RUNNING_MODAL'}

        # Check for conflicts
        conflicts = _find_conflicts(new_type, new_ctrl, new_shift, new_alt, new_oskey,
                                    exclude_kmi=kmi)
        if not conflicts:
            # No conflicts — apply directly
            _apply_rebind(kmi, new_type, new_ctrl, new_shift, new_alt, new_oskey)
            _modal_state = 'IDLE'
            _menu_context.clear()
        else:
            # Conflicts found — enter CONFLICT state
            _conflict_data['new_type'] = new_type
            _conflict_data['new_ctrl'] = new_ctrl
            _conflict_data['new_shift'] = new_shift
            _conflict_data['new_alt'] = new_alt
            _conflict_data['new_oskey'] = new_oskey
            _conflict_data['source_kmi'] = kmi
            _conflict_data['source_km_name'] = km_name
            _conflict_data['conflicts'] = conflicts
            _modal_state = 'CONFLICT'

        _batch_dirty = True
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    # Ignore non-capturable keys silently
    return {'RUNNING_MODAL'}


def _handle_conflict(context, event):
    """Handle events in CONFLICT state."""
    global _modal_state, _conflict_hovered_button, _batch_dirty

    if event.type == 'MOUSEMOVE':
        new_hover = _hit_test_conflict_buttons(event.mouse_region_x, event.mouse_region_y)
        if new_hover != _conflict_hovered_button:
            _conflict_hovered_button = new_hover
            if _target_area is not None:
                _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
        mx, my = event.mouse_region_x, event.mouse_region_y
        btn_hit = _hit_test_conflict_buttons(mx, my)

        if btn_hit >= 0:
            action = _conflict_button_rects[btn_hit][1]
            src_kmi = _conflict_data.get('source_kmi')
            new_type = _conflict_data.get('new_type')
            new_ctrl = _conflict_data.get('new_ctrl', False)
            new_shift = _conflict_data.get('new_shift', False)
            new_alt = _conflict_data.get('new_alt', False)
            new_oskey = _conflict_data.get('new_oskey', False)
            conflicts = _conflict_data.get('conflicts', [])

            if action == 'SWAP' and src_kmi:
                # Save source's current binding
                old_type = src_kmi.type
                old_ctrl = src_kmi.ctrl
                old_shift = src_kmi.shift
                old_alt = src_kmi.alt
                old_oskey = src_kmi.oskey

                # Apply new binding to source
                _apply_rebind(src_kmi, new_type, new_ctrl, new_shift, new_alt, new_oskey)

                # Set conflicting KMIs to old binding
                for ckm_name, ckmi in conflicts:
                    _apply_rebind(ckmi, old_type, old_ctrl, old_shift, old_alt, old_oskey)

            elif action == 'OVERRIDE' and src_kmi:
                # Deactivate conflicting KMIs
                for ckm_name, ckmi in conflicts:
                    ckmi.active = False

                # Apply new binding to source
                _apply_rebind(src_kmi, new_type, new_ctrl, new_shift, new_alt, new_oskey)

            # CANCEL or fallthrough: just dismiss

        _modal_state = 'IDLE'
        _conflict_hovered_button = -1
        _conflict_button_rects.clear()
        _conflict_data['conflicts'] = []
        _menu_context.clear()
        _invalidate_cache()
        _batch_dirty = True
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'ESC' and event.value == 'PRESS':
        _modal_state = 'IDLE'
        _conflict_hovered_button = -1
        _conflict_button_rects.clear()
        _conflict_data['conflicts'] = []
        _menu_context.clear()
        _batch_dirty = True
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    return {'RUNNING_MODAL'}


def _handle_search(context, event):
    """Handle keyboard input during search mode. Returns modal return set or None."""
    global _search_active, _search_text, _search_last_update, _batch_dirty

    if not _search_active:
        return None

    if event.type == 'ESC' and event.value == 'PRESS':
        _search_active = False
        _search_text = ''
        _update_search_filter()
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'RET' and event.value == 'PRESS':
        _search_active = False
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    if event.type == 'BACK_SPACE' and event.value == 'PRESS':
        if _search_text:
            _search_text = _search_text[:-1]
            now = time.monotonic()
            if now - _search_last_update > 0.15:
                _update_search_filter()
                _search_last_update = now
            if _target_area is not None:
                _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    # Printable character input via event.unicode
    if event.value == 'PRESS' and event.unicode and event.unicode.isprintable():
        _search_text += event.unicode
        now = time.monotonic()
        if now - _search_last_update > 0.15:
            _update_search_filter()
            _search_last_update = now
        if _target_area is not None:
            _target_area.tag_redraw()
        return {'RUNNING_MODAL'}

    return None  # Not handled by search


# ---------------------------------------------------------------------------
# Modal operator – runs inside the new window
# ---------------------------------------------------------------------------
class WM_OT_keymap_viz_modal(bpy.types.Operator):
    bl_idname = "wm.keymap_viz_modal"
    bl_label = "Keymap Visualizer Modal"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        global _draw_handle, _target_area

        self._target_window = context.window
        _target_area = context.area

        # Compute initial layout
        for r in context.area.regions:
            if r.type == 'WINDOW':
                _compute_keyboard_layout(r.width, r.height)
                break

        # Register draw handler on the SpaceTextEditor
        _draw_handle = bpy.types.SpaceTextEditor.draw_handler_add(
            _draw_callback, (), 'WINDOW', 'POST_PIXEL'
        )

        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        global _modal_state

        # Window-close guard
        try:
            if self._target_window not in context.window_manager.windows[:]:
                self._cleanup(context)
                return {'CANCELLED'}
        except ReferenceError:
            self._cleanup(context)
            return {'CANCELLED'}

        # Handle WINDOW_DEACTIVATE (Phase 7 hardening)
        if event.type == 'WINDOW_DEACTIVATE':
            # Verify window still exists
            try:
                _ = self._target_window.screen
            except ReferenceError:
                self._cleanup(context)
                return {'CANCELLED'}
            return {'PASS_THROUGH'}

        # Search mode takes priority when active (Phase 7)
        if _search_active and _modal_state == 'IDLE':
            result = _handle_search(context, event)
            if result is not None:
                return result

        # State machine dispatch (Phase 5)
        if _modal_state == 'MENU_OPEN':
            return _handle_menu_open(context, event)
        elif _modal_state == 'CAPTURE':
            return _handle_capture(context, event)
        elif _modal_state == 'CONFLICT':
            return _handle_conflict(context, event)

        # IDLE state
        result = _handle_idle(context, event)
        if result is not None:
            return result

        # ESC to close (only in IDLE and not searching)
        if event.type == 'ESC' and event.value == 'PRESS' and not _search_active:
            self._cleanup(context)
            try:
                with context.temp_override(window=self._target_window):
                    bpy.ops.wm.window_close()
            except Exception:
                pass
            return {'CANCELLED'}

        # Pass through everything else so the window stays responsive
        return {'PASS_THROUGH'}

    def _cleanup(self, context):
        global _draw_handle, _target_area
        global _hovered_key_index, _selected_key_index, _key_rects
        global _cached_region_size, _modifier_rects
        global _cached_bindings, _bindings_key, _active_modifiers
        global _modal_state, _menu_context, _conflict_data
        global _conflict_button_rects, _conflict_hovered_button
        global _gpu_menu_items, _gpu_menu_hovered
        global _export_button_rect, _export_hovered
        global _search_text, _search_active, _search_matching_keys
        global _batch_dirty, _hover_transition, _hover_transition_target, _last_frame_time

        if _draw_handle is None:
            return  # Already cleaned up (idempotent)

        try:
            bpy.types.SpaceTextEditor.draw_handler_remove(_draw_handle, 'WINDOW')
        except Exception:
            pass
        _draw_handle = None
        _target_area = None
        _hovered_key_index = -1
        _selected_key_index = -1
        _key_rects = []
        _cached_region_size = (0, 0)
        _modifier_rects = []
        _active_modifiers = {'ctrl': False, 'shift': False, 'alt': False, 'oskey': False}
        _cached_bindings = []
        _bindings_key = None
        _modal_state = 'IDLE'
        _menu_context.clear()
        _conflict_data['conflicts'] = []
        _conflict_button_rects.clear()
        _conflict_hovered_button = -1
        _gpu_menu_items.clear()
        _gpu_menu_hovered = -1
        _export_button_rect = None
        _export_hovered = False
        _search_text = ''
        _search_active = False
        _search_matching_keys = set()
        _batch_dirty = True
        _hover_transition = 0.0
        _hover_transition_target = -1
        _last_frame_time = 0.0
        _set_running(False)

        # Redraw any remaining text-editor areas to clear stale overlay
        try:
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'TEXT_EDITOR':
                        area.tag_redraw()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Launcher operator – opens window, sets area type, starts modal
# ---------------------------------------------------------------------------
class WM_OT_keymap_viz_launch(bpy.types.Operator):
    bl_idname = "wm.keymap_viz_launch"
    bl_label = "Open Keymap Visualizer"
    bl_description = "Open a new window with the keymap visualizer overlay"

    def execute(self, context):
        if _visualizer_running:
            self.report({'WARNING'}, "Keymap Visualizer is already running")
            return {'CANCELLED'}

        _set_running(True)

        # Snapshot existing windows so we can identify the new one
        existing_windows = set(context.window_manager.windows[:])

        # Open a new window (duplicates the current one)
        bpy.ops.wm.window_new()

        # Find the new window
        new_window = None
        for w in context.window_manager.windows:
            if w not in existing_windows:
                new_window = w
                break

        if new_window is None:
            _set_running(False)
            self.report({'ERROR'}, "Failed to create new window")
            return {'CANCELLED'}

        # Set the first area to TEXT_EDITOR
        target_area = new_window.screen.areas[0]
        target_area.type = 'TEXT_EDITOR'

        # Store refs for the timer callback
        self._new_window = new_window
        self._target_area = target_area

        # Use a one-shot timer to invoke the modal after the window is set up
        bpy.app.timers.register(self._deferred_start_modal, first_interval=0.05)

        return {'FINISHED'}

    def _deferred_start_modal(self):
        """Timer callback – invoke the modal operator in the new window."""
        wm = bpy.context.window_manager
        window = self._new_window
        area = self._target_area

        # Verify window still alive
        if window not in wm.windows[:]:
            _set_running(False)
            return None  # Don't reschedule

        # Find a region to use as override
        region = None
        for r in area.regions:
            if r.type == 'WINDOW':
                region = r
                break
        if region is None:
            _set_running(False)
            return None

        try:
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.wm.keymap_viz_modal('INVOKE_DEFAULT')
        except Exception as e:
            print(f"[Keymap Visualizer] Failed to start modal: {e}")
            _set_running(False)

        return None  # One-shot, don't reschedule


# ---------------------------------------------------------------------------
# Addon Preferences (Phase 6 + Phase 7)
# ---------------------------------------------------------------------------
class KeymapVizPreferences(bpy.types.AddonPreferences):
    bl_idname = "keymap_visualizer"

    export_path: StringProperty(
        name="Export Path",
        description="File path for keymap export",
        subtype='FILE_PATH',
        default="//custom_keymap.py",
    )
    export_scope: EnumProperty(
        name="Export Scope",
        items=[
            ('MODIFIED', "Modified Only", "Export only modified keybindings"),
            ('ALL', "All", "Export all keybindings"),
        ],
        default='MODIFIED',
    )

    # Color scheme (Phase 7)
    col_key_unbound: FloatVectorProperty(
        name="Key Unbound",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.25, 0.25, 0.28, 1.0),
        update=lambda self, ctx: _invalidate_cache(),
    )
    col_key_selected: FloatVectorProperty(
        name="Key Selected",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.2, 0.5, 0.9, 1.0),
        update=lambda self, ctx: _invalidate_cache(),
    )
    col_key_hovered: FloatVectorProperty(
        name="Key Hovered",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.35, 0.45, 0.6, 1.0),
        update=lambda self, ctx: _invalidate_cache(),
    )
    col_background: FloatVectorProperty(
        name="Background",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.12, 0.12, 0.12, 0.95),
        update=lambda self, ctx: _invalidate_cache(),
    )
    col_text: FloatVectorProperty(
        name="Text",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=lambda self, ctx: _invalidate_cache(),
    )
    col_panel_bg: FloatVectorProperty(
        name="Panel Background",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.15, 0.15, 0.18, 0.9),
        update=lambda self, ctx: _invalidate_cache(),
    )

    def draw(self, context):
        layout = self.layout

        # Export settings
        box = layout.box()
        box.label(text="Export Settings")
        box.prop(self, "export_path")
        box.prop(self, "export_scope")

        # Color scheme
        box = layout.box()
        box.label(text="Color Scheme")
        row = box.row()
        row.prop(self, "col_key_unbound")
        row.prop(self, "col_key_selected")
        row = box.row()
        row.prop(self, "col_key_hovered")
        row.prop(self, "col_background")
        row = box.row()
        row.prop(self, "col_text")
        row.prop(self, "col_panel_bg")


# ---------------------------------------------------------------------------
# Header button
# ---------------------------------------------------------------------------
def _draw_header_button(self, context):
    layout = self.layout
    layout.separator()
    row = layout.row(align=True)
    if _visualizer_running:
        row.enabled = False
        row.operator("wm.keymap_viz_launch", text="Keymap Viz (Running)")
    else:
        row.operator("wm.keymap_viz_launch", text="Keymap Viz")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
_classes = (
    KeymapVizPreferences,
    WM_OT_keymap_viz_modal,
    WM_OT_keymap_viz_launch,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_HT_header.append(_draw_header_button)


def unregister():
    global _draw_handle, _target_area, _visualizer_running
    global _key_rects, _cached_region_size, _modifier_rects
    global _hovered_key_index, _selected_key_index

    # Clean up draw handler if still active
    if _draw_handle is not None:
        try:
            bpy.types.SpaceTextEditor.draw_handler_remove(_draw_handle, 'WINDOW')
        except Exception:
            pass
        _draw_handle = None
    _target_area = None
    _visualizer_running = False
    _key_rects = []
    _cached_region_size = (0, 0)
    _modifier_rects = []
    _hovered_key_index = -1
    _selected_key_index = -1

    bpy.types.VIEW3D_HT_header.remove(_draw_header_button)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
