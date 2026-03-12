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
