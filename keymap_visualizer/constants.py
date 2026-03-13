"""
Keymap Visualizer – Constants
Keyboard layout data, color tuples, and static lookup tables.
"""

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
        ("\u25C0", "LEFT_ARROW", 1.0),
        ("\u25BC", "DOWN_ARROW", 1.0),
        ("\u25B6", "RIGHT_ARROW", 1.0),
    ],
    # Row 1 (aligned with home row)
    [
        1.0,  # gap to center Up arrow above Down arrow
        ("\u25B2", "UP_ARROW", 1.0),
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

# Numpad layout (rendered to the right of nav cluster)
NUMPAD_ROWS = [
    # Row 0 (bottom, aligned with modifier/space row)
    [("0", "NUMPAD_0", 2.0), (".", "NUMPAD_PERIOD", 1.0), ("Enter", "NUMPAD_ENTER", 1.0)],
    # Row 1 (aligned with shift row)
    [("1", "NUMPAD_1", 1.0), ("2", "NUMPAD_2", 1.0), ("3", "NUMPAD_3", 1.0)],
    # Row 2 (aligned with home row)
    [("4", "NUMPAD_4", 1.0), ("5", "NUMPAD_5", 1.0), ("6", "NUMPAD_6", 1.0), ("+", "NUMPAD_PLUS", 1.0)],
    # Row 3 (aligned with QWERTY row)
    [("7", "NUMPAD_7", 1.0), ("8", "NUMPAD_8", 1.0), ("9", "NUMPAD_9", 1.0)],
    # Row 4 (aligned with number row)
    [("/", "NUMPAD_SLASH", 1.0), ("*", "NUMPAD_ASTERIX", 1.0), ("-", "NUMPAD_MINUS", 1.0)],
]

NUMPAD_ROW_ALIGNMENT = [0, 1, 2, 3, 4]

# Modifier event types for identification
_MODIFIER_EVENTS = {
    "LEFT_CTRL", "RIGHT_CTRL", "LEFT_SHIFT", "RIGHT_SHIFT",
    "LEFT_ALT", "RIGHT_ALT", "OSKEY",
}

# Modifier key event type → toggle dict key mapping
MODIFIER_KEY_TO_DICT = {
    'LEFT_CTRL': 'ctrl', 'RIGHT_CTRL': 'ctrl',
    'LEFT_SHIFT': 'shift', 'RIGHT_SHIFT': 'shift',
    'LEFT_ALT': 'alt', 'RIGHT_ALT': 'alt',
    'OSKEY': 'oskey',
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

# Feature 3: Bound-key highlighting
COL_KEY_BOUND = (0.28, 0.30, 0.38, 1.0)

# Shortcut search overlay color
COL_SHORTCUT_SEARCH_TEXT = (0.3, 0.9, 0.8, 1.0)

# ---------------------------------------------------------------------------
# Feature 1 (v0.9): Operator abbreviations for on-key labels
# ---------------------------------------------------------------------------
OPERATOR_ABBREVIATIONS = {
    "transform.translate": "Move",
    "transform.rotate": "Rotate",
    "transform.resize": "Scale",
    "transform.mirror": "Mirror",
    "transform.shrink_fatten": "Shrink/Fat",
    "transform.push_pull": "Push/Pull",
    "transform.shear": "Shear",
    "transform.tosphere": "To Sphere",
    "mesh.extrude_region_move": "Extrude",
    "mesh.extrude_faces_move": "Extr Face",
    "mesh.inset": "Inset",
    "mesh.bevel": "Bevel",
    "mesh.knife_tool": "Knife",
    "mesh.bisect": "Bisect",
    "mesh.loopcut_slide": "Loop Cut",
    "mesh.offset_edge_loops_slide": "Offset",
    "mesh.subdivide": "Subdivide",
    "mesh.merge": "Merge",
    "mesh.separate": "Separate",
    "mesh.fill": "Fill",
    "mesh.delete": "Delete",
    "mesh.dupli_extrude_cursor": "Spin",
    "mesh.select_all": "Sel All",
    "mesh.select_linked": "Sel Link",
    "mesh.select_loop": "Sel Loop",
    "mesh.hide": "Hide",
    "mesh.reveal": "Reveal",
    "object.delete": "Delete",
    "object.duplicate_move": "Duplicate",
    "object.join": "Join",
    "object.parent_set": "Parent",
    "object.shade_smooth": "Smooth",
    "object.shade_flat": "Flat",
    "object.select_all": "Sel All",
    "object.hide_view_set": "Hide",
    "object.origin_set": "Origin",
    "ed.undo": "Undo",
    "ed.redo": "Redo",
    "ed.undo_history": "Undo Hist",
    "wm.save_mainfile": "Save",
    "wm.save_as_mainfile": "Save As",
    "wm.open_mainfile": "Open",
    "wm.call_menu": "Menu",
    "wm.search_menu": "Search",
    "wm.tool_set_by_id": "Tool",
    "screen.animation_play": "Play",
    "screen.frame_jump": "Jump",
    "screen.keyframe_jump": "Next Key",
    "screen.screen_full_area": "Fullscreen",
    "anim.keyframe_insert": "Key Insert",
    "anim.keyframe_delete": "Key Delete",
    "view3d.rotate": "Orbit",
    "view3d.move": "Pan",
    "view3d.zoom": "Zoom",
    "view3d.view_selected": "Frame Sel",
    "view3d.view_all": "Frame All",
    "view3d.view_camera": "Camera",
    "view3d.snap_menu": "Snap",
    "view3d.localview": "Local View",
    "view3d.toggle_shading": "Shading",
    "node.translate_attach": "Move",
    "node.duplicate_move": "Duplicate",
    "node.links_mute": "Mute Link",
    "sculpt.brush_stroke": "Brush",
    "paint.image_paint": "Paint",
    "uv.select_all": "Sel All",
    "file.save_blendfile": "Save",
}

# ---------------------------------------------------------------------------
# Feature 3 (v0.9): Operator category classification and colors
# ---------------------------------------------------------------------------
OPERATOR_CATEGORIES = {
    "transform.": "Transform",
    "view3d.": "Navigation",
    "mesh.": "Mesh",
    "object.": "Object",
    "screen.": "Playback",
    "anim.": "Animation",
    "node.": "Nodes",
    "uv.": "UV",
    "sculpt.": "Sculpt",
    "paint.": "Paint",
    "wm.": "System",
    "ed.": "Edit",
    "file.": "File",
}

CATEGORY_COLORS = {
    "Transform": (0.45, 0.30, 0.15, 0.90),
    "Navigation": (0.15, 0.35, 0.38, 0.90),
    "Mesh": (0.30, 0.20, 0.40, 0.90),
    "Object": (0.25, 0.35, 0.25, 0.90),
    "Playback": (0.20, 0.28, 0.45, 0.90),
    "Animation": (0.40, 0.35, 0.15, 0.90),
    "Nodes": (0.35, 0.25, 0.30, 0.90),
    "UV": (0.20, 0.38, 0.30, 0.90),
    "Sculpt": (0.38, 0.22, 0.22, 0.90),
    "Paint": (0.35, 0.30, 0.20, 0.90),
    "System": (0.25, 0.25, 0.30, 0.90),
    "Edit": (0.30, 0.30, 0.35, 0.90),
    "File": (0.22, 0.30, 0.28, 0.90),
}

# ---------------------------------------------------------------------------
# Feature 4: Editor/Mode filter lists
# ---------------------------------------------------------------------------
SPACE_TYPE_FILTERS = [
    ('ALL', "All Editors"),
    ('EMPTY', "Global"),
    ('VIEW_3D', "3D Viewport"),
    ('IMAGE_EDITOR', "Image/UV"),
    ('NODE_EDITOR', "Node Editor"),
    ('TEXT_EDITOR', "Text Editor"),
    ('SEQUENCE_EDITOR', "Sequencer"),
    ('CLIP_EDITOR', "Clip Editor"),
    ('DOPESHEET_EDITOR', "Dopesheet"),
    ('GRAPH_EDITOR', "Graph Editor"),
    ('NLA_EDITOR', "NLA"),
    ('PROPERTIES', "Properties"),
    ('OUTLINER', "Outliner"),
    ('CONSOLE', "Console"),
    ('SPREADSHEET', "Spreadsheet"),
]

MODE_FILTERS = [
    ('ALL', "All Modes"),
    ('Object Mode', "Object"),
    ('Mesh', "Edit Mesh"),
    ('Sculpt', "Sculpt"),
    ('Pose', "Pose"),
    ('Weight Paint', "Weight Paint"),
    ('Vertex Paint', "Vertex Paint"),
    ('Texture Paint', "Texture Paint"),
    ('Grease Pencil', "Grease Pencil"),
    ('Curves', "Curves"),
]
