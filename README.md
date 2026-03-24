# blenderKey

A visual keyboard-based keymap editor for Blender 5.0+. Browse, edit, rebind, search, and export your keybindings through a GPU-rendered keyboard overlay — no digging through the built-in preferences panel. *Completely vibecoded using Claude Code.*

![Blender](https://img.shields.io/badge/Blender-5.0%2B-orange) ![License](https://img.shields.io/badge/license-MIT-blue)

<!-- Add a screenshot here: ![blenderKey screenshot](docs/screenshot.png) -->

---

## Features

### Visual Keyboard
- GPU-rendered keyboard with drop shadows, hover transitions, and smooth animations
- **6 form factors**: 100%, 96%, 80% (TKL), 75%, 65%, 60%
- **2 physical layouts**: ANSI and ISO
- **6 logical layouts**: QWERTY, AZERTY, QWERTZ, Dvorak, Colemak, Nordic
- Auto-detects your OS keyboard layout on launch

### Keymap Browsing
- Hover or click any key to inspect all its bindings in the info panel
- Modifier toggles (Ctrl, Shift, Alt, OS) filter bindings by combination
- Editor and mode filters to scope bindings to specific contexts
- Keyboard navigation between keys

### Editing
- Right-click context menu: Rebind, Unbind, Reset to Default, Toggle Active
- Rebind capture mode — press any key combo to reassign a binding
- Conflict resolution: Swap, Override, or Cancel
- Undo / Redo for all keymap changes (up to 50 levels)

### Search
- Operator search (`/` or `Ctrl+F`) — filter keys by operator name
- Shortcut reverse-lookup — find which key an operator is bound to

### Operator Browser
- Categorized, filterable list of all Blender operators
- Assign new bindings directly from the browser

### Theming
- 8 base color tokens for key states, backgrounds, and text
- 13 category colors for visual grouping by operator type
- Advanced per-element overrides in addon preferences
- WCAG-aware contrast defaults

### Presets
- Save, load, and delete named keymap presets
- Quick switching between preset configurations

### Export
- Export keybindings as a Blender-importable Python script
- Scope: modified-only (default) or full keyconfig dump

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
- Use **Undo** (`Ctrl+Z`) and **Redo** (`Ctrl+Shift+Z`) to revert changes

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `ESC` | Close visualizer / cancel current action |
| `/` or `Ctrl+F` | Open search bar |
| `Ctrl+Z` | Undo last keymap change |
| `Ctrl+Shift+Z` | Redo |
| `Enter` (in search) | Confirm search filter |
| `ESC` (in search) | Clear and close search bar |
| Left-click | Select key / click UI elements |
| Right-click | Open context menu on a key |

---

## Configuration

Go to **Edit > Preferences > Add-ons > Keymap Visualizer** to configure:

- **Keyboard**: form factor, physical layout (ANSI/ISO), logical layout
- **Export**: output path, scope (modified-only or all)
- **Theme**: 8 base color tokens + 13 category colors with color pickers
- **Category colors**: toggle color-coding by operator category
- **Advanced overrides**: fine-tune individual UI element colors

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
  icons.py          # Icon loading and management
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

---

## License

MIT
