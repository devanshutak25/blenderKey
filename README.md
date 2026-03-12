# Keymap Visualizer for Blender

A visual keyboard-based keymap editor for Blender 4.2+. Opens a dedicated window with a GPU-drawn keyboard that lets you browse, edit, rebind, and export your keybindings — all without touching the built-in preferences panel.

![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange) ![License](https://img.shields.io/badge/license-MIT-blue)

---

## Features

- **Full QWERTY keyboard** rendered with GPU, including nav cluster and function keys
- **Hover & click** any key to see all its bindings in the info panel
- **Modifier toggles** (Ctrl, Shift, Alt, OS) filter bindings by modifier combination
- **Right-click context menu** to Rebind, Unbind, Reset to Default, or Toggle Active
- **Rebind capture** — press any key to reassign a binding
- **Conflict resolution** — Swap, Override, or Cancel when a rebind conflicts with existing bindings
- **Export** your keymap as a Blender-importable Python script
- **Search/filter** — press `/` or `Ctrl+F` to search operators by name; non-matching keys dim out
- **Custom colors** — pick your own key, background, and text colors in addon preferences
- **Drop shadows & hover transitions** for visual polish

---

## Installation

1. Download or clone this repository
2. In Blender, go to **Edit > Preferences > Add-ons**
3. Click **Install...** and navigate to the `keymap_visualizer` folder (select the folder itself, or zip it first and select the `.zip`)
4. Enable **Keymap Visualizer** in the addon list

Alternatively, copy the `keymap_visualizer` folder directly into your Blender addons directory:

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

### Opening the Visualizer

Click the **Keymap Viz** button in the 3D Viewport header bar. A new window opens with the keyboard overlay.

### Browsing Bindings

| Action | What it does |
|--------|-------------|
| **Hover** over a key | Shows all bindings for that key in the bottom info panel |
| **Left-click** a key | Selects and locks the info panel to that key |
| **Click modifier toggles** (Ctrl/Shift/Alt/OS) | Filters bindings to only show those matching the active modifiers |

### Editing Bindings

**Right-click** any key with bindings to open the context menu:

| Menu Item | What it does |
|-----------|-------------|
| **Rebind** | Enters capture mode — press a new key (with optional modifiers held) to reassign the binding |
| **Unbind** | Deactivates the binding (sets `kmi.active = False`) |
| **Reset to Default** | Restores the binding to Blender's default key and modifiers |
| **Toggle Active** | Flips the binding between active and inactive |

### Rebinding a Key

1. Right-click a key > **Rebind**
2. The screen dims and shows "Press new key combination..."
3. Press the new key (hold Ctrl/Shift/Alt/OS for modifier combos)
4. If no conflict: the binding is reassigned immediately
5. If conflict detected: a resolution overlay appears with three options:
   - **Swap** — exchanges the key assignments between the two bindings
   - **Override** — deactivates the conflicting binding and applies the new one
   - **Cancel** — discards the change
6. Press **ESC** at any time to cancel

### Searching

Press `/` or `Ctrl+F` to activate the search bar. Type an operator name (e.g., `transform`, `mesh.extrude`) to filter — keys without matching bindings dim out. Press **ESC** to clear, **Enter** to confirm and keep the filter active.

### Exporting

Click the **Export** button (to the right of modifier toggles) to save your keybindings as a Python script. Configure the export path and scope in addon preferences:

- **Modified Only** (default) — exports only bindings that differ from Blender's defaults
- **All** — full keyconfig dump

The exported file can be imported back via **Edit > Preferences > Keymap > Import**.

### Closing

Press **ESC** (when not in capture/search mode) or close the window normally.

---

## Addon Preferences

Go to **Edit > Preferences > Add-ons > Keymap Visualizer** to configure:

### Export Settings
- **Export Path** — where the exported `.py` file is saved (supports `//` for blend-relative paths)
- **Export Scope** — Modified Only or All

### Color Scheme
Customize these colors with the built-in color pickers (changes apply live):
- Key Unbound
- Key Selected
- Key Hovered
- Background
- Text
- Panel Background

---

## Keyboard Shortcuts (inside the visualizer)

| Key | Action |
|-----|--------|
| `ESC` | Close visualizer / Cancel current action |
| `/` or `Ctrl+F` | Open search bar |
| `ESC` (in search) | Clear search and close search bar |
| `Enter` (in search) | Confirm search filter |
| Left-click | Select key / Click buttons |
| Right-click | Open context menu on a key |

---

## Notes

- **Changes are permanent** — keymap edits modify `wm.keyconfigs.user` directly and persist in your Blender user preferences. There is no undo (`Ctrl+Z` will not revert binding changes). Use **Reset to Default** from the context menu to restore individual bindings.
- **QWERTY ANSI layout only** — the keyboard layout is hardcoded to standard US ANSI QWERTY. Other layouts (ISO, AZERTY, etc.) are not currently supported.
- **Single instance** — only one visualizer window can be open at a time.
- Tested on Blender 4.2+ and 5.0.

---

## Project Structure

```
keymap_visualizer/
  __init__.py    # Everything — layout, rendering, editing, export, preferences
```

Single-file addon for simplicity. All logic is in `__init__.py` (~1900 lines).

---

## License

MIT
