# blenderKey

A visual keyboard-based keymap editor for Blender 5.0+. Browse, edit, rebind, search, and export your keybindings through a GPU-rendered keyboard overlay — no digging through the built-in preferences panel. *Completely vibecoded using Claude Code.*

![Blender](https://img.shields.io/badge/Blender-5.0%2B-orange) ![License](https://img.shields.io/badge/license-MIT-blue)

<!-- Add a screenshot here: ![blenderKey screenshot](docs/screenshot.png) -->

<img width="3268" height="1215" alt="blender_OLXUgEh7rF" src="https://github.com/user-attachments/assets/7b4b73d3-99d6-4394-9749-4721b6921cfd" />


---

## Features

### Visual Keyboard

- Full GPU-rendered keyboard with drop shadows, hover transitions, and smooth animations
- **6 form factors**: Full Size (100%), Compact Full (96%), TKL (80%), 75%, 65%, 60%
- **2 physical layouts**: ANSI and ISO (with proper ISO Enter shape)
- **7 logical layouts**: Auto-detect, QWERTY, AZERTY, QWERTZ, Dvorak, Colemak, Nordic
- Auto-detects your OS keyboard layout on launch
- All keyboard sections rendered: alphanumeric block, navigation cluster, numpad, function row, and a mouse block (LMB/RMB/MMB)
- Resizable keyboard — drag the resize handle to scale from 0.5x to 3.0x

### Key Visual States

Keys change appearance based on context:

- **Unbound** — default surface color
- **Bound** — highlighted to indicate active bindings
- **Category-colored** — tinted by operator category (Transform, Mesh, Navigation, etc.)
- **Hovered** — animated transition on mouse-over
- **Selected** — accent-colored when clicked/locked
- **Modifier-active** — physical modifier keys pulse at 2Hz when held
- **Search dimming** — non-matching keys dim to 30% during search
- **Diff mode** — green for modified bindings, red for deactivated, dimmed for unmodified
- **Rebind flash** — brief green flash on successful rebind

### Key Badges and Labels

- **Key label** (top-left) — physical key name (e.g., "G", "Tab", "F5")
- **Command label** (bottom) — abbreviated operator name for the primary binding (e.g., "Move", "Extrude", "Loop Cut") using 80 built-in abbreviations
- **Modifier count badge** (bottom-right) — shows how many additional modifier combos have bindings beyond current modifiers
- **Drag badge** (top-right, amber "D") — appears on keys with click-drag bindings
- WCAG-aware adaptive light/dark text based on background luminance

### Modifier Toggle Bar

- Four virtual modifier toggles: **Ctrl**, **Shift**, **Alt**, **OS/Win**
- Click to toggle on/off — filters visible bindings to that modifier combo
- Physically pressing modifier keys on your keyboard overrides the toggles automatically

### Info Panel

Shows detailed binding information for the hovered or selected key:

- **Header** with key label and active filter summary
- **Binding list** — each entry shows modifier prefix, activation state, operator name, editor icon, and keymap name
- **Grouped bindings** — same operator across multiple keymaps collapses into expandable groups with arrow indicators and editor count
- **Operator descriptions** — shown when a group is expanded
- **Modal shortcuts** — hardcoded hints for modal operators (e.g., "G G → Edge Slide", "S S → Shrink-Fatten", "R R → Trackball")
- **Scrollable** — mouse wheel or middle-drag to scroll, with scrollbar and fade gradients
- **Idle hints** — when no key is selected, shows contextual help and button tooltips

### Editor and Mode Filters

Two scrollable filter panels to scope which keymaps are displayed:

- **Editor filter** — All Editors, Global, 3D Viewport, Image/UV, Node Editor, Text Editor, Sequencer, Clip Editor, Dopesheet, Graph Editor, NLA, Properties, Outliner, Console, Spreadsheet
- **Mode filter** — All Modes, Object Mode, Edit Mesh, Sculpt, Pose, Weight Paint, Vertex Paint, Texture Paint, Grease Pencil, Curves
- Multi-select — any combination of filters active simultaneously
- Each item shows its icon from the texture atlas

### Operator Browser

A categorized, searchable accordion panel listing all Blender operators:

- **13 category groups** — Transform, Navigation, Mesh, Object, Edit, Sculpt, Paint, UV, Nodes, Animation, Playback, File, System — each collapsible with colored sidebar swatch and item count
- **Search box** — type to filter operators by name or idname; all categories auto-expand during search
- **Blue dot indicator** — marks operators that have active bindings
- Click any operator to open a flyout menu with:
  - **Assign Shortcut** — enter capture mode to bind a new key
  - **View Bindings** — jump to the key this operator is bound to
  - **Remove All Bindings** — deactivate all bindings for this operator (undoable)
  - **Open in Preferences** — jump to Blender's built-in keymap preferences

### Context Menu (Right-Click Editing)

Right-click any key to open a context menu listing its bindings (up to 5):

- Hover a binding to open a flyout sub-menu with:
  - **Rebind** — enter capture mode to assign a new key combo
  - **Unbind** / **Enable** — toggle the binding on or off
  - **Reset to Default** — restore Blender's original binding
  - **Toggle On/Off** — activate or deactivate
- All operations are undoable

### Capture Mode (Key Rebinding)

Triggered from "Rebind" or "Assign Shortcut":

- All keys dim except the target key, which pulses with an animated border
- Prompt text: "Press new key combination…" with "ESC to cancel"
- Press any key combo (with any Ctrl/Shift/Alt/OS modifiers) to set the new binding
- Supports letters, digits, F1–F24, Tab, Enter, Space, Backspace, Delete, Insert, Home, End, Page Up/Down, arrows, numpad, punctuation, and more
- **Conflict detection** — if the new combo conflicts, the conflict resolution dialog appears

### Conflict Resolution

When a rebind conflicts with existing bindings:

- Centered modal panel with "Key Conflict" header
- Shows the rebind being attempted and lists conflicting bindings
- Three options:
  - **Swap** — move conflicting bindings to the old key
  - **Override** — apply the new binding and deactivate conflicts
  - **Cancel** — dismiss without changes

### Search

- **Operator search** (`/` or `Ctrl+F`) — token-based fuzzy matching filters keys by operator name. Matching keys stay bright; non-matching dim to 30%. Shows result count badge.
- **Shortcut reverse-lookup** (`?` or `Shift+/`) — press any key combo to instantly jump to that key and show its bindings in the info panel

### Diff View

- Toggle with `D` — compares your keyconfig against Blender defaults
- **Green keys** — modified bindings
- **Red keys** — deactivated bindings
- **Dimmed keys** — unmodified bindings
- "DIFF" badge shown in toolbar when active

### Undo / Redo

- Up to **50 undo levels** for all keymap changes
- `Ctrl+Z` to undo, `Ctrl+Shift+Z` to redo
- Undo counter displayed in the toolbar: "Undo: N | Redo: N"
- Every mutation (rebind, unbind, reset, toggle, preset load, import) pushes an undo snapshot

### Presets

- **Save As…** — name and save your full keyconfig as a JSON preset
- **Load** — click any saved preset to apply it (pushes undo snapshot first)
- **Delete** — remove the active preset
- **Copy to Clipboard** — copy preset JSON to clipboard
- **Paste from Clipboard** — import a preset from clipboard and apply it
- Presets stored as JSON files in a configurable directory

### Export

- Export keybindings as a Blender-importable `.py` keyconfig script
- **Export scope**: modified-only (default) or full keyconfig dump
- Output path configurable in addon preferences
- Generated script is compatible with `keyconfig_import_from_data`

### Import

- Import a previously exported `.py` keyconfig file
- Uses safe parsing (`ast.literal_eval`) — no code execution
- Applies bindings by matching operator idname in each keymap
- Import path configurable in addon preferences

### Keyboard Navigation (Accessibility)

- `Tab` / `Shift+Tab` — cycle focus between panels: Keys → Editor List → Mode List → Operator List → Info Panel
- **Arrow keys** — navigate the keyboard layout row-by-row, or scroll filter lists
- **Enter** — select/deselect key, or toggle filter item
- Focus ring drawn on the currently focused key

### Category Color System
<img width="1127" height="1320" alt="blender_nMHIr6LGG6" src="https://github.com/user-attachments/assets/ff16bbc2-8f1b-4916-9063-516c04df8660" />


- **13 operator categories**: Transform, Navigation, Mesh, Object, Edit, Sculpt, Paint, UV, Nodes, Animation, Playback, File, System
- Keys tinted by the category of their primary binding
- Color legend displayed above the keyboard
- Toggle on/off globally; each category color individually customizable

### Theming

- **8 base color tokens**: Accent, Background, Surface, Text, Success, Warning, Danger, Info — all other colors derived from these
- **13 category colors** — individually configurable
- **29 advanced color overrides** — fine-tune specific UI elements (keys, panels, menus, buttons, search, capture overlay, etc.) with per-element enable toggle + color picker
- WCAG-aware contrast defaults

### Font Customization

- **Key label font** — configurable TTF path (falls back to Blender's bundled font)
- **Command label font** — configurable TTF path (falls back to bundled Roboto Condensed)

### Icon System

- 25 editor and mode icons loaded from PNG files and packed into a single GPU texture atlas for efficient batched rendering
- Icons appear in filter lists, binding entries, and context menus

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `ESC` | Close visualizer / cancel current action |
| `/` or `Ctrl+F` | Open operator search bar |
| `?` (`Shift+/`) | Open shortcut reverse-lookup |
| `D` | Toggle diff view mode |
| `Ctrl+Z` | Undo last keymap change |
| `Ctrl+Shift+Z` | Redo |
| `Tab` / `Shift+Tab` | Cycle focus between panels |
| Arrow keys | Navigate keys / scroll lists |
| `Enter` | Select key / toggle filter item |
| `Enter` (in search) | Commit search filter |
| `ESC` (in search) | Clear and close search bar |
| Left-click | Select key / click UI elements |
| Right-click | Open context menu on a key |

## Mouse Interactions

| Interaction | Result |
|-------------|--------|
| Left-click key | Select/deselect key; show bindings in info panel |
| Left-click modifier key | Toggle that modifier on/off |
| Right-click key | Open context menu with bindings |
| Left-click Export | Export keymap to .py file |
| Left-click Import | Import keymap from .py file |
| Left-click Presets | Open preset dropdown |
| Left-click Close (X) | Close the visualizer |
| Left-drag resize handle | Scale the keyboard up/down |
| Mouse wheel (on any panel) | Scroll that panel's content |
| Middle-drag (on any panel) | Drag-scroll that panel |

---

## Installation

1. Download or clone this repository
2. In Blender: **Edit > Preferences > Add-ons**
3. Click **Install...** and select the `keymap_visualizer` folder (or zip it first)
4. Enable **Keymap Visualizer** in the addon list

Or copy the `keymap_visualizer` folder directly into your addons directory:

```
# Windows
%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\

# macOS
~/Library/Application Support/Blender/<version>/scripts/addons/

# Linux
~/.config/blender/<version>/scripts/addons/
```

---

## Usage

Open the visualizer from **Edit > Keymap Visualizer** in the top menu bar. A new window opens with the keyboard overlay.

- **Hover** a key to preview its bindings
- **Left-click** to lock the info panel to that key
- **Right-click** to rebind, unbind, or reset a binding
- **Toggle modifiers** (Ctrl/Shift/Alt/OS) to filter by modifier combo
- Press `/` or `Ctrl+F` to search operators
- Press `?` to find a key by pressing its shortcut
- Press `D` to see what you've changed from defaults
- Use **Undo** (`Ctrl+Z`) and **Redo** (`Ctrl+Shift+Z`) to revert changes

---

## Configuration

Go to **Edit > Preferences > Add-ons > Keymap Visualizer** to configure:

- **Keyboard Layout** — logical layout (Auto/QWERTY/AZERTY/QWERTZ/Dvorak/Colemak/Nordic), physical layout (ANSI/ISO), form factor (100%–60%)
- **Export / Import** — output path, export scope (modified-only or all), import path
- **Presets** — presets folder path
- **Fonts** — custom TTF paths for key labels and command labels
- **Theme** — 8 base color tokens with color pickers
- **Category Colors** — enable toggle + 13 individually configurable category colors
- **Advanced Color Overrides** — 29 fine-grained UI element color overrides (collapsed by default)

---

## Project Structure

```
keymap_visualizer/
  __init__.py       # Addon registration and bl_info
  constants.py      # Enums, color tokens, layout constants
  drawing.py        # GPU rendering (keys, panels, overlays)
  export.py         # Python keymap script export
  handlers.py       # Event handling and input dispatch
  hit_testing.py    # Mouse-to-key hit detection
  icons.py          # Icon loading and texture atlas
  keyboards.py      # Physical/logical keyboard definitions
  keymap_data.py    # Keymap introspection and diffing
  layout.py         # Key position/size calculations
  operators.py      # Blender operators (modal, launch)
  preferences.py    # Addon preferences and theme settings
  presets.py        # Preset save/load/delete
  state.py          # Runtime state, undo/redo, selections
```

---

## Contributing

1. Fork the repo and create a feature branch
2. Keep changes focused — one feature or fix per PR
3. Test in Blender 5.0+ before submitting
4. Open a pull request with a clear description of what changed and why
