"""
Keymap Visualizer – Multi-keyboard layout support

Separates physical layout (key positions/sizes) from logical layout
(labels + Blender event_types). Supports ANSI/ISO form factors,
multiple logical layouts, and various physical sizes.
"""

import sys
import subprocess

# ---------------------------------------------------------------------------
# Position IDs for keys that vary between logical layouts (~47 keys)
# ---------------------------------------------------------------------------
# Number row
GRAVE_POS = 'GRAVE'
POS_1 = '1'
POS_2 = '2'
POS_3 = '3'
POS_4 = '4'
POS_5 = '5'
POS_6 = '6'
POS_7 = '7'
POS_8 = '8'
POS_9 = '9'
POS_0 = '0'
MINUS_POS = 'MINUS'
EQUAL_POS = 'EQUAL'

# QWERTY row
Q_POS = 'Q'
W_POS = 'W'
E_POS = 'E'
R_POS = 'R'
T_POS = 'T'
Y_POS = 'Y'
U_POS = 'U'
I_POS = 'I'
O_POS = 'O'
P_POS = 'P'
LBRACKET_POS = 'LBRACKET'
RBRACKET_POS = 'RBRACKET'
BSLASH_POS = 'BSLASH'

# Home row
A_POS = 'A'
S_POS = 'S'
D_POS = 'D'
F_POS = 'F'
G_POS = 'G'
H_POS = 'H'
J_POS = 'J'
K_POS = 'K'
L_POS = 'L'
SEMI_POS = 'SEMI'
QUOTE_POS = 'QUOTE'

# Shift row
Z_POS = 'Z'
X_POS = 'X'
C_POS = 'C'
V_POS = 'V'
B_POS = 'B'
N_POS = 'N'
M_POS = 'M'
COMMA_POS = 'COMMA'
PERIOD_POS = 'PERIOD'
SLASH_POS = 'SLASH'

# ISO-specific
ISO_EXTRA_POS = 'ISO_EXTRA'

# ---------------------------------------------------------------------------
# ANSI physical layout (main block)
# 2-tuples (pos_id, width) for varying keys
# 3-tuples (label, event_type, width) for fixed keys
# Bare floats for gaps
# ---------------------------------------------------------------------------
ANSI_MAIN_ROWS = [
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
        (Z_POS, 1.0),
        (X_POS, 1.0),
        (C_POS, 1.0),
        (V_POS, 1.0),
        (B_POS, 1.0),
        (N_POS, 1.0),
        (M_POS, 1.0),
        (COMMA_POS, 1.0),
        (PERIOD_POS, 1.0),
        (SLASH_POS, 1.0),
        ("RShift", "RIGHT_SHIFT", 2.75),
    ],
    # Row 2: home row
    [
        ("Caps", "CAPS_LOCK", 1.75),
        (A_POS, 1.0),
        (S_POS, 1.0),
        (D_POS, 1.0),
        (F_POS, 1.0),
        (G_POS, 1.0),
        (H_POS, 1.0),
        (J_POS, 1.0),
        (K_POS, 1.0),
        (L_POS, 1.0),
        (SEMI_POS, 1.0),
        (QUOTE_POS, 1.0),
        ("Enter", "RET", 2.25),
    ],
    # Row 3: QWERTY row
    [
        ("Tab", "TAB", 1.5),
        (Q_POS, 1.0),
        (W_POS, 1.0),
        (E_POS, 1.0),
        (R_POS, 1.0),
        (T_POS, 1.0),
        (Y_POS, 1.0),
        (U_POS, 1.0),
        (I_POS, 1.0),
        (O_POS, 1.0),
        (P_POS, 1.0),
        (LBRACKET_POS, 1.0),
        (RBRACKET_POS, 1.0),
        (BSLASH_POS, 1.5),
    ],
    # Row 4: number row
    [
        (GRAVE_POS, 1.0),
        (POS_1, 1.0),
        (POS_2, 1.0),
        (POS_3, 1.0),
        (POS_4, 1.0),
        (POS_5, 1.0),
        (POS_6, 1.0),
        (POS_7, 1.0),
        (POS_8, 1.0),
        (POS_9, 1.0),
        (POS_0, 1.0),
        (MINUS_POS, 1.0),
        (EQUAL_POS, 1.0),
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

# ---------------------------------------------------------------------------
# ISO physical layout (main block) — differs in rows 1, 2, 3
# ---------------------------------------------------------------------------
ISO_MAIN_ROWS = [
    # Row 0 (bottom): modifier/space row — same as ANSI
    ANSI_MAIN_ROWS[0],
    # Row 1: shift row — smaller LShift (1.25u), extra ISO key before Z
    [
        ("LShift", "LEFT_SHIFT", 1.25),
        (ISO_EXTRA_POS, 1.0),
        (Z_POS, 1.0),
        (X_POS, 1.0),
        (C_POS, 1.0),
        (V_POS, 1.0),
        (B_POS, 1.0),
        (N_POS, 1.0),
        (M_POS, 1.0),
        (COMMA_POS, 1.0),
        (PERIOD_POS, 1.0),
        (SLASH_POS, 1.0),
        ("RShift", "RIGHT_SHIFT", 2.75),
    ],
    # Row 2: home row — Enter is 1.25u (bottom half of ISO L-shaped enter)
    [
        ("Caps", "CAPS_LOCK", 1.75),
        (A_POS, 1.0),
        (S_POS, 1.0),
        (D_POS, 1.0),
        (F_POS, 1.0),
        (G_POS, 1.0),
        (H_POS, 1.0),
        (J_POS, 1.0),
        (K_POS, 1.0),
        (L_POS, 1.0),
        (SEMI_POS, 1.0),
        (QUOTE_POS, 1.0),
        ("Enter", "RET", 2.25),
    ],
    # Row 3: QWERTY row — no backslash; stub for ISO enter top half
    [
        ("Tab", "TAB", 1.5),
        (Q_POS, 1.0),
        (W_POS, 1.0),
        (E_POS, 1.0),
        (R_POS, 1.0),
        (T_POS, 1.0),
        (Y_POS, 1.0),
        (U_POS, 1.0),
        (I_POS, 1.0),
        (O_POS, 1.0),
        (P_POS, 1.0),
        (LBRACKET_POS, 1.0),
        (RBRACKET_POS, 1.0),
        ("", "RET", 1.5),  # ISO enter stub (top part, same event_type as Enter)
    ],
    # Row 4: number row — same as ANSI
    ANSI_MAIN_ROWS[4],
    # Row 5: function row — same as ANSI
    ANSI_MAIN_ROWS[5],
]

# ---------------------------------------------------------------------------
# Navigation cluster and numpad (unchanged, form-factor independent)
# ---------------------------------------------------------------------------
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

NAV_ROW_ALIGNMENT = [0, 1, 3, 4, 5]

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

# ---------------------------------------------------------------------------
# Compact nav cluster (for 75% layout — single-column arrows + minimal nav)
# ---------------------------------------------------------------------------
_COMPACT_NAV_ROWS = [
    [("\u25C0", "LEFT_ARROW", 1.0), ("\u25BC", "DOWN_ARROW", 1.0), ("\u25B6", "RIGHT_ARROW", 1.0)],
    [("PgDn", "PAGE_DOWN", 1.0), ("\u25B2", "UP_ARROW", 1.0), ("PgUp", "PAGE_UP", 1.0)],
    [("Home", "HOME", 1.0), ("Ins", "INSERT", 1.0), ("End", "END", 1.0)],
    [("Del", "DEL", 1.0)],
]

_COMPACT_NAV_ALIGNMENT = [0, 1, 3, 4]

# Arrows-only nav (for 65% layout)
_ARROWS_ONLY_NAV_ROWS = [
    [("\u25C0", "LEFT_ARROW", 1.0), ("\u25BC", "DOWN_ARROW", 1.0), ("\u25B6", "RIGHT_ARROW", 1.0)],
    [1.0, ("\u25B2", "UP_ARROW", 1.0)],
]

_ARROWS_ONLY_NAV_ALIGNMENT = [0, 1]

# ---------------------------------------------------------------------------
# Logical layouts — each maps position IDs to (label, event_type)
# ---------------------------------------------------------------------------
LOGICAL_QWERTY = {
    # Number row
    GRAVE_POS: ("`", "ACCENT_GRAVE"),
    POS_1: ("1", "ONE"),
    POS_2: ("2", "TWO"),
    POS_3: ("3", "THREE"),
    POS_4: ("4", "FOUR"),
    POS_5: ("5", "FIVE"),
    POS_6: ("6", "SIX"),
    POS_7: ("7", "SEVEN"),
    POS_8: ("8", "EIGHT"),
    POS_9: ("9", "NINE"),
    POS_0: ("0", "ZERO"),
    MINUS_POS: ("-", "MINUS"),
    EQUAL_POS: ("=", "EQUAL"),
    # QWERTY row
    Q_POS: ("Q", "Q"),
    W_POS: ("W", "W"),
    E_POS: ("E", "E"),
    R_POS: ("R", "R"),
    T_POS: ("T", "T"),
    Y_POS: ("Y", "Y"),
    U_POS: ("U", "U"),
    I_POS: ("I", "I"),
    O_POS: ("O", "O"),
    P_POS: ("P", "P"),
    LBRACKET_POS: ("[", "LEFT_BRACKET"),
    RBRACKET_POS: ("]", "RIGHT_BRACKET"),
    BSLASH_POS: ("\\", "BACK_SLASH"),
    # Home row
    A_POS: ("A", "A"),
    S_POS: ("S", "S"),
    D_POS: ("D", "D"),
    F_POS: ("F", "F"),
    G_POS: ("G", "G"),
    H_POS: ("H", "H"),
    J_POS: ("J", "J"),
    K_POS: ("K", "K"),
    L_POS: ("L", "L"),
    SEMI_POS: (";", "SEMI_COLON"),
    QUOTE_POS: ("'", "QUOTE"),
    # Shift row
    Z_POS: ("Z", "Z"),
    X_POS: ("X", "X"),
    C_POS: ("C", "C"),
    V_POS: ("V", "V"),
    B_POS: ("B", "B"),
    N_POS: ("N", "N"),
    M_POS: ("M", "M"),
    COMMA_POS: (",", "COMMA"),
    PERIOD_POS: (".", "PERIOD"),
    SLASH_POS: ("/", "SLASH"),
    # ISO extra key
    ISO_EXTRA_POS: ("<", "BACK_SLASH"),
}

LOGICAL_AZERTY = {
    # Number row — AZERTY shows symbols on number keys
    GRAVE_POS: ("\u00B2", "ACCENT_GRAVE"),
    POS_1: ("&", "ONE"),
    POS_2: ("\u00E9", "TWO"),
    POS_3: ('"', "THREE"),
    POS_4: ("'", "FOUR"),
    POS_5: ("(", "FIVE"),
    POS_6: ("-", "SIX"),
    POS_7: ("\u00E8", "SEVEN"),
    POS_8: ("_", "EIGHT"),
    POS_9: ("\u00E7", "NINE"),
    POS_0: ("\u00E0", "ZERO"),
    MINUS_POS: (")", "MINUS"),
    EQUAL_POS: ("=", "EQUAL"),
    # AZERTY row (swapped A↔Q, Z↔W)
    Q_POS: ("A", "A"),
    W_POS: ("Z", "Z"),
    E_POS: ("E", "E"),
    R_POS: ("R", "R"),
    T_POS: ("T", "T"),
    Y_POS: ("Y", "Y"),
    U_POS: ("U", "U"),
    I_POS: ("I", "I"),
    O_POS: ("O", "O"),
    P_POS: ("P", "P"),
    LBRACKET_POS: ("^", "LEFT_BRACKET"),
    RBRACKET_POS: ("$", "RIGHT_BRACKET"),
    BSLASH_POS: ("*", "BACK_SLASH"),
    # Home row
    A_POS: ("Q", "Q"),
    S_POS: ("S", "S"),
    D_POS: ("D", "D"),
    F_POS: ("F", "F"),
    G_POS: ("G", "G"),
    H_POS: ("H", "H"),
    J_POS: ("J", "J"),
    K_POS: ("K", "K"),
    L_POS: ("L", "L"),
    SEMI_POS: ("M", "M"),
    QUOTE_POS: ("\u00F9", "QUOTE"),
    # Shift row
    Z_POS: ("W", "W"),
    X_POS: ("X", "X"),
    C_POS: ("C", "C"),
    V_POS: ("V", "V"),
    B_POS: ("B", "B"),
    N_POS: ("N", "N"),
    M_POS: (",", "COMMA"),
    COMMA_POS: (";", "SEMI_COLON"),
    PERIOD_POS: (":", "PERIOD"),
    SLASH_POS: ("!", "SLASH"),
    # ISO extra key
    ISO_EXTRA_POS: ("<", "BACK_SLASH"),
}

LOGICAL_QWERTZ = {
    # Number row
    GRAVE_POS: ("^", "ACCENT_GRAVE"),
    POS_1: ("1", "ONE"),
    POS_2: ("2", "TWO"),
    POS_3: ("3", "THREE"),
    POS_4: ("4", "FOUR"),
    POS_5: ("5", "FIVE"),
    POS_6: ("6", "SIX"),
    POS_7: ("7", "SEVEN"),
    POS_8: ("8", "EIGHT"),
    POS_9: ("9", "NINE"),
    POS_0: ("0", "ZERO"),
    MINUS_POS: ("\u00DF", "MINUS"),
    EQUAL_POS: ("\u00B4", "EQUAL"),
    # QWERTZ row (Z↔Y swap)
    Q_POS: ("Q", "Q"),
    W_POS: ("W", "W"),
    E_POS: ("E", "E"),
    R_POS: ("R", "R"),
    T_POS: ("T", "T"),
    Y_POS: ("Z", "Z"),
    U_POS: ("U", "U"),
    I_POS: ("I", "I"),
    O_POS: ("O", "O"),
    P_POS: ("P", "P"),
    LBRACKET_POS: ("\u00DC", "LEFT_BRACKET"),
    RBRACKET_POS: ("+", "RIGHT_BRACKET"),
    BSLASH_POS: ("#", "BACK_SLASH"),
    # Home row
    A_POS: ("A", "A"),
    S_POS: ("S", "S"),
    D_POS: ("D", "D"),
    F_POS: ("F", "F"),
    G_POS: ("G", "G"),
    H_POS: ("H", "H"),
    J_POS: ("J", "J"),
    K_POS: ("K", "K"),
    L_POS: ("L", "L"),
    SEMI_POS: ("\u00D6", "SEMI_COLON"),
    QUOTE_POS: ("\u00C4", "QUOTE"),
    # Shift row
    Z_POS: ("Y", "Y"),
    X_POS: ("X", "X"),
    C_POS: ("C", "C"),
    V_POS: ("V", "V"),
    B_POS: ("B", "B"),
    N_POS: ("N", "N"),
    M_POS: ("M", "M"),
    COMMA_POS: (",", "COMMA"),
    PERIOD_POS: (".", "PERIOD"),
    SLASH_POS: ("-", "SLASH"),
    # ISO extra key
    ISO_EXTRA_POS: ("<", "BACK_SLASH"),
}

LOGICAL_DVORAK = {
    # Number row
    GRAVE_POS: ("`", "ACCENT_GRAVE"),
    POS_1: ("1", "ONE"),
    POS_2: ("2", "TWO"),
    POS_3: ("3", "THREE"),
    POS_4: ("4", "FOUR"),
    POS_5: ("5", "FIVE"),
    POS_6: ("6", "SIX"),
    POS_7: ("7", "SEVEN"),
    POS_8: ("8", "EIGHT"),
    POS_9: ("9", "NINE"),
    POS_0: ("0", "ZERO"),
    MINUS_POS: ("[", "LEFT_BRACKET"),
    EQUAL_POS: ("]", "RIGHT_BRACKET"),
    # Top row (Dvorak: ',.pyfgcrl/=\)
    Q_POS: ("'", "QUOTE"),
    W_POS: (",", "COMMA"),
    E_POS: (".", "PERIOD"),
    R_POS: ("P", "P"),
    T_POS: ("Y", "Y"),
    Y_POS: ("F", "F"),
    U_POS: ("G", "G"),
    I_POS: ("C", "C"),
    O_POS: ("R", "R"),
    P_POS: ("L", "L"),
    LBRACKET_POS: ("/", "SLASH"),
    RBRACKET_POS: ("=", "EQUAL"),
    BSLASH_POS: ("\\", "BACK_SLASH"),
    # Home row (Dvorak: aoeuidhtns-)
    A_POS: ("A", "A"),
    S_POS: ("O", "O"),
    D_POS: ("E", "E"),
    F_POS: ("U", "U"),
    G_POS: ("I", "I"),
    H_POS: ("D", "D"),
    J_POS: ("H", "H"),
    K_POS: ("T", "T"),
    L_POS: ("N", "N"),
    SEMI_POS: ("S", "S"),
    QUOTE_POS: ("-", "MINUS"),
    # Shift row (Dvorak: ;qjkxbmwvz)
    Z_POS: (";", "SEMI_COLON"),
    X_POS: ("Q", "Q"),
    C_POS: ("J", "J"),
    V_POS: ("K", "K"),
    B_POS: ("X", "X"),
    N_POS: ("B", "B"),
    M_POS: ("M", "M"),
    COMMA_POS: ("W", "W"),
    PERIOD_POS: ("V", "V"),
    SLASH_POS: ("Z", "Z"),
    # ISO extra key
    ISO_EXTRA_POS: ("<", "BACK_SLASH"),
}

LOGICAL_COLEMAK = {
    # Number row — same as QWERTY
    GRAVE_POS: ("`", "ACCENT_GRAVE"),
    POS_1: ("1", "ONE"),
    POS_2: ("2", "TWO"),
    POS_3: ("3", "THREE"),
    POS_4: ("4", "FOUR"),
    POS_5: ("5", "FIVE"),
    POS_6: ("6", "SIX"),
    POS_7: ("7", "SEVEN"),
    POS_8: ("8", "EIGHT"),
    POS_9: ("9", "NINE"),
    POS_0: ("0", "ZERO"),
    MINUS_POS: ("-", "MINUS"),
    EQUAL_POS: ("=", "EQUAL"),
    # Top row: qwfpgjluy;
    Q_POS: ("Q", "Q"),
    W_POS: ("W", "W"),
    E_POS: ("F", "F"),
    R_POS: ("P", "P"),
    T_POS: ("G", "G"),
    Y_POS: ("J", "J"),
    U_POS: ("L", "L"),
    I_POS: ("U", "U"),
    O_POS: ("Y", "Y"),
    P_POS: (";", "SEMI_COLON"),
    LBRACKET_POS: ("[", "LEFT_BRACKET"),
    RBRACKET_POS: ("]", "RIGHT_BRACKET"),
    BSLASH_POS: ("\\", "BACK_SLASH"),
    # Home row: arstdhneio
    A_POS: ("A", "A"),
    S_POS: ("R", "R"),
    D_POS: ("S", "S"),
    F_POS: ("T", "T"),
    G_POS: ("D", "D"),
    H_POS: ("H", "H"),
    J_POS: ("N", "N"),
    K_POS: ("E", "E"),
    L_POS: ("I", "I"),
    SEMI_POS: ("O", "O"),
    QUOTE_POS: ("'", "QUOTE"),
    # Shift row: zxcvbkm,./
    Z_POS: ("Z", "Z"),
    X_POS: ("X", "X"),
    C_POS: ("C", "C"),
    V_POS: ("V", "V"),
    B_POS: ("B", "B"),
    N_POS: ("K", "K"),
    M_POS: ("M", "M"),
    COMMA_POS: (",", "COMMA"),
    PERIOD_POS: (".", "PERIOD"),
    SLASH_POS: ("/", "SLASH"),
    # ISO extra key
    ISO_EXTRA_POS: ("<", "BACK_SLASH"),
}

LOGICAL_NORDIC = {
    # Number row — Nordic (same positions but different right-side punctuation)
    GRAVE_POS: ("\u00A7", "ACCENT_GRAVE"),
    POS_1: ("1", "ONE"),
    POS_2: ("2", "TWO"),
    POS_3: ("3", "THREE"),
    POS_4: ("4", "FOUR"),
    POS_5: ("5", "FIVE"),
    POS_6: ("6", "SIX"),
    POS_7: ("7", "SEVEN"),
    POS_8: ("8", "EIGHT"),
    POS_9: ("9", "NINE"),
    POS_0: ("0", "ZERO"),
    MINUS_POS: ("+", "MINUS"),
    EQUAL_POS: ("\u00B4", "EQUAL"),
    # Top row: QWERTY-based
    Q_POS: ("Q", "Q"),
    W_POS: ("W", "W"),
    E_POS: ("E", "E"),
    R_POS: ("R", "R"),
    T_POS: ("T", "T"),
    Y_POS: ("Y", "Y"),
    U_POS: ("U", "U"),
    I_POS: ("I", "I"),
    O_POS: ("O", "O"),
    P_POS: ("P", "P"),
    LBRACKET_POS: ("\u00C5", "LEFT_BRACKET"),
    RBRACKET_POS: ("\u00A8", "RIGHT_BRACKET"),
    BSLASH_POS: ("'", "BACK_SLASH"),
    # Home row: QWERTY-based + Ø/Æ on right
    A_POS: ("A", "A"),
    S_POS: ("S", "S"),
    D_POS: ("D", "D"),
    F_POS: ("F", "F"),
    G_POS: ("G", "G"),
    H_POS: ("H", "H"),
    J_POS: ("J", "J"),
    K_POS: ("K", "K"),
    L_POS: ("L", "L"),
    SEMI_POS: ("\u00D8", "SEMI_COLON"),
    QUOTE_POS: ("\u00C6", "QUOTE"),
    # Shift row
    Z_POS: ("Z", "Z"),
    X_POS: ("X", "X"),
    C_POS: ("C", "C"),
    V_POS: ("V", "V"),
    B_POS: ("B", "B"),
    N_POS: ("N", "N"),
    M_POS: ("M", "M"),
    COMMA_POS: (",", "COMMA"),
    PERIOD_POS: (".", "PERIOD"),
    SLASH_POS: ("-", "SLASH"),
    # ISO extra key
    ISO_EXTRA_POS: ("<", "BACK_SLASH"),
}

# Map layout names to dicts
_LOGICAL_LAYOUTS = {
    'QWERTY': LOGICAL_QWERTY,
    'AZERTY': LOGICAL_AZERTY,
    'QWERTZ': LOGICAL_QWERTZ,
    'DVORAK': LOGICAL_DVORAK,
    'COLEMAK': LOGICAL_COLEMAK,
    'NORDIC': LOGICAL_NORDIC,
}

# ---------------------------------------------------------------------------
# Physical size configuration
# ---------------------------------------------------------------------------
SIZE_CONFIG = {
    '100': {'frow': True, 'nav': True, 'numpad': True},
    '96':  {'frow': True, 'nav': True, 'numpad': True, 'compact': True},
    '80':  {'frow': True, 'nav': True, 'numpad': False},
    '75':  {'frow': True, 'nav': 'compact', 'numpad': False},
    '65':  {'frow': False, 'nav': 'arrows_only', 'numpad': False},
    '60':  {'frow': False, 'nav': False, 'numpad': False},
}

# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------
_cached_auto_layout = None


def auto_detect_layout():
    """Detect the OS keyboard layout and return a logical layout name.

    Returns one of: 'QWERTY', 'AZERTY', 'QWERTZ', 'DVORAK', 'COLEMAK', 'NORDIC'
    Falls back to 'QWERTY' if detection fails.
    """
    global _cached_auto_layout
    if _cached_auto_layout is not None:
        return _cached_auto_layout

    detected = 'QWERTY'

    if sys.platform == 'win32':
        detected = _detect_windows()
    elif sys.platform == 'darwin':
        detected = _detect_macos()
    else:
        detected = _detect_linux()

    _cached_auto_layout = detected
    return detected


def _detect_windows():
    """Read keyboard layout from Windows registry."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Keyboard Layout\Preload",
        )
        layout_id, _ = winreg.QueryValueEx(key, "1")
        winreg.CloseKey(key)
        # Layout IDs: https://docs.microsoft.com/en-us/windows-hardware/manufacture/desktop/default-input-locales
        layout_id = layout_id.lower().lstrip('0')
        _WINDOWS_LAYOUT_MAP = {
            '409': 'QWERTY',     # US
            '809': 'QWERTY',     # UK
            '40c': 'AZERTY',     # French
            '80c': 'AZERTY',     # Belgian French
            '407': 'QWERTZ',     # German
            '807': 'QWERTZ',     # Swiss German
            '406': 'NORDIC',     # Danish
            '41d': 'NORDIC',     # Swedish
            '414': 'NORDIC',     # Norwegian
            '40b': 'NORDIC',     # Finnish
        }
        return _WINDOWS_LAYOUT_MAP.get(layout_id, 'QWERTY')
    except Exception:
        return 'QWERTY'


def _detect_macos():
    """Detect layout on macOS."""
    try:
        result = subprocess.run(
            ['defaults', 'read', 'com.apple.HIToolbox', 'AppleSelectedInputSources'],
            capture_output=True, text=True, timeout=2,
        )
        output = result.stdout.lower()
        if 'azerty' in output or 'french' in output:
            return 'AZERTY'
        if 'qwertz' in output or 'german' in output:
            return 'QWERTZ'
        if 'dvorak' in output:
            return 'DVORAK'
        if 'colemak' in output:
            return 'COLEMAK'
        if any(k in output for k in ('danish', 'swedish', 'norwegian', 'finnish', 'nordic')):
            return 'NORDIC'
        return 'QWERTY'
    except Exception:
        return 'QWERTY'


def _detect_linux():
    """Detect layout on Linux via setxkbmap."""
    try:
        result = subprocess.run(
            ['setxkbmap', '-query'],
            capture_output=True, text=True, timeout=2,
        )
        for line in result.stdout.splitlines():
            if line.strip().startswith('layout:'):
                layout = line.split(':', 1)[1].strip().lower()
                if layout in ('fr',):
                    return 'AZERTY'
                if layout in ('de', 'ch', 'at'):
                    return 'QWERTZ'
                if layout in ('dk', 'se', 'no', 'fi'):
                    return 'NORDIC'
                # Variants
                break
            if line.strip().startswith('variant:'):
                variant = line.split(':', 1)[1].strip().lower()
                if 'dvorak' in variant:
                    return 'DVORAK'
                if 'colemak' in variant:
                    return 'COLEMAK'
        return 'QWERTY'
    except Exception:
        return 'QWERTY'


# ---------------------------------------------------------------------------
# Resolution: combine physical + logical → 3-tuple rows
# ---------------------------------------------------------------------------

def _resolve_rows(physical_rows, logical_map):
    """Resolve position-ID-based rows into concrete 3-tuple rows.

    Items can be:
    - 2-tuple (pos_id, width): variable key, resolved via logical_map
    - 3-tuple (label, event_type, width): fixed key, passed through
    - bare float/int: gap, passed through
    """
    resolved = []
    for row in physical_rows:
        resolved_row = []
        for item in row:
            if isinstance(item, (int, float)):
                resolved_row.append(item)
            elif len(item) == 2:
                pos_id, width = item
                label, event_type = logical_map[pos_id]
                resolved_row.append((label, event_type, width))
            else:
                resolved_row.append(item)
        resolved.append(resolved_row)
    return resolved


def get_resolved_rows(form_factor='ANSI', logical='QWERTY', size='100'):
    """Return (main_rows, nav_rows, numpad_rows, nav_alignment, numpad_alignment).

    All rows are in the resolved 3-tuple format: (label, event_type, width).
    """
    # Resolve logical layout
    if logical == 'AUTO':
        logical = auto_detect_layout()

    logical_map = _LOGICAL_LAYOUTS.get(logical, LOGICAL_QWERTY)

    # Select physical layout
    if form_factor == 'ISO':
        physical_rows = ISO_MAIN_ROWS
    else:
        physical_rows = ANSI_MAIN_ROWS

    # Resolve main rows
    main_rows = _resolve_rows(physical_rows, logical_map)

    # Apply size config
    cfg = SIZE_CONFIG.get(size, SIZE_CONFIG['100'])

    # Function row
    if not cfg['frow']:
        # Remove the last row (function row is row 5, index -1)
        main_rows = main_rows[:-1]

    # Nav cluster
    if cfg['nav'] is True:
        nav_rows = NAV_CLUSTER_ROWS
        nav_alignment = NAV_ROW_ALIGNMENT
    elif cfg['nav'] == 'compact':
        nav_rows = _COMPACT_NAV_ROWS
        nav_alignment = _COMPACT_NAV_ALIGNMENT
    elif cfg['nav'] == 'arrows_only':
        nav_rows = _ARROWS_ONLY_NAV_ROWS
        nav_alignment = _ARROWS_ONLY_NAV_ALIGNMENT
    else:
        nav_rows = []
        nav_alignment = []

    # Numpad
    if cfg.get('numpad', False):
        numpad_rows = NUMPAD_ROWS
        numpad_alignment = NUMPAD_ROW_ALIGNMENT
    else:
        numpad_rows = []
        numpad_alignment = []

    return main_rows, nav_rows, numpad_rows, nav_alignment, numpad_alignment


# ---------------------------------------------------------------------------
# Mouse layout (appended to the right of keyboard)
# ---------------------------------------------------------------------------
MOUSE_ROWS = [
    [("Btn4", "BUTTON4MOUSE", 1.0), ("Btn5", "BUTTON5MOUSE", 1.0)],   # row 0 (side buttons)
    [],                                                                   # row 1 (body gap)
    [("W.Up", "WHEELUPMOUSE", 1.0), ("W.Dn", "WHEELDOWNMOUSE", 1.0)],  # row 2 (scroll)
    [("MMB", "MIDDLEMOUSE", 2.0)],                                       # row 3 (middle click)
    [("LMB", "LEFTMOUSE", 1.0), ("RMB", "RIGHTMOUSE", 1.0)],           # row 4 (primary)
]
MOUSE_ALIGNMENT = [0, 1, 2, 3, 4]
MOUSE_WIDTH = 2.0
