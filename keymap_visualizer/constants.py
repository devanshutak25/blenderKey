"""
Keymap Visualizer – Constants
Keyboard layout data, color tuples, and static lookup tables.
"""

from collections import namedtuple

# ---------------------------------------------------------------------------
# KeyRect namedtuple
# ---------------------------------------------------------------------------
KeyRect = namedtuple('KeyRect', ['label', 'event_type', 'x', 'y', 'w', 'h'])

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
# Base theme tokens (user-configurable via preferences)
# ---------------------------------------------------------------------------
BASE_ACCENT     = (0.20, 0.50, 0.90, 1.0)
BASE_BACKGROUND = (0.14, 0.14, 0.15, 0.95)   # warmed slightly from 0.12
BASE_SURFACE    = (0.25, 0.25, 0.28, 1.0)
BASE_TEXT       = (0.93, 0.93, 0.93, 1.0)     # softened from 1.0
BASE_SUCCESS    = (0.25, 0.45, 0.25, 1.0)
BASE_WARNING    = (1.00, 0.90, 0.30, 1.0)
BASE_DANGER     = (1.00, 0.40, 0.30, 1.0)
BASE_INFO       = (0.30, 0.90, 0.80, 1.0)

# ---------------------------------------------------------------------------
# Legacy colors (kept for backward compat, prefer base tokens + derivation)
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

OPERATOR_CATEGORY_ORDER = [
    "Transform", "Navigation", "Mesh", "Object", "Edit",
    "Sculpt", "Paint", "UV", "Nodes", "Animation",
    "Playback", "File", "System", "Other",
]

# Maps operator prefix → best-guess keymap name for new bindings
OPERATOR_CATEGORY_KEYMAPS = {
    "transform.": "3D View",
    "view3d.":    "3D View",
    "mesh.":      "Mesh",
    "object.":    "Object Mode",
    "screen.":    "Screen",
    "anim.":      "Dopesheet",
    "node.":      "Node Editor",
    "uv.":        "UV Editor",
    "sculpt.":    "Sculpt",
    "paint.":     "Image Paint",
    "wm.":        "Window",
    "ed.":        "Screen",
    "file.":      "Window",
}

# Category text-safe colors (brightened for 4.5:1+ contrast on dark backgrounds)
CATEGORY_TEXT_COLORS = {
    "Transform":  (0.85, 0.60, 0.35, 1.0),
    "Navigation": (0.40, 0.70, 0.75, 1.0),
    "Mesh":       (0.65, 0.50, 0.80, 1.0),
    "Object":     (0.50, 0.70, 0.50, 1.0),
    "Playback":   (0.50, 0.60, 0.85, 1.0),
    "Animation":  (0.80, 0.70, 0.35, 1.0),
    "Nodes":      (0.70, 0.55, 0.65, 1.0),
    "UV":         (0.45, 0.75, 0.60, 1.0),
    "Sculpt":     (0.75, 0.50, 0.50, 1.0),
    "Paint":      (0.70, 0.60, 0.45, 1.0),
    "System":     (0.60, 0.60, 0.70, 1.0),
    "Edit":       (0.65, 0.65, 0.72, 1.0),
    "File":       (0.50, 0.65, 0.60, 1.0),
    "Other":      (0.65, 0.65, 0.65, 1.0),
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

# ---------------------------------------------------------------------------
# Modal shortcuts — key combos handled inside modal operators, not in keyconfig.
# These can't be detected from bpy.context.window_manager.keyconfigs.
# Format: {event_type: [(sequence_label, description), ...]}
# ---------------------------------------------------------------------------
MODAL_SHORTCUTS = {
    'G': [
        ("G G", "Edge Slide (in Edit Mode)"),
    ],
    'S': [
        ("S S", "Scale along normals / Shrink-Fatten (in Edit Mode)"),
    ],
    'R': [
        ("R R", "Trackball rotation"),
    ],
    'X': [
        ("X X", "Dissolve (in Edit Mode)"),
    ],
    'E': [
        ("E S", "Extrude along normals (in Edit Mode)"),
    ],
    'LEFTMOUSE': [
        ("LMB Drag", "Box Select / Transform confirm drag"),
    ],
    'MIDDLEMOUSE': [
        ("MMB Drag", "Orbit viewport (in 3D View)"),
        ("Shift+MMB", "Pan viewport"),
        ("Ctrl+MMB", "Zoom viewport"),
    ],
}
