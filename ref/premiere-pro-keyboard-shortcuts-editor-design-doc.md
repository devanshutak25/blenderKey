# Design Document: Adobe Premiere Pro — Keyboard Shortcuts Editor

**Scope:** Complete behavioral and architectural specification of the Keyboard Shortcuts editor dialog in Adobe Premiere Pro (current as of v25.x).

---

## 1. Entry Points

The editor is a modal dialog invoked via:

- **Windows:** `Edit > Keyboard Shortcuts` or the hotkey `Ctrl + Alt + K`
- **macOS:** `Premiere Pro > Keyboard Shortcuts` or `Cmd + Opt + K`

The dialog blocks interaction with the rest of the application until closed. It is not dockable, not a panel — it is a standalone modal window.

---

## 2. Dialog Layout — Top to Bottom

The editor window is divided into four vertically-stacked zones:

### 2.1 Keyboard Layout Preset Selector (Top Bar)

A dropdown at the top-left of the dialog. This is the **preset selector**, which controls which shortcut mapping is currently active.

**Built-in presets include:**

- `Adobe Premiere Pro Default` — the factory mapping
- `Final Cut Pro 7.0` — compatibility mapping for editors migrating from FCP7
- `Avid Media Composer 5` — compatibility mapping for Avid editors
- `Custom` — automatically selected the moment any binding is modified from the active preset

**Behavioral rules:**

- Selecting a preset loads its entire keybinding set into the editor immediately. The visual keyboard and command list update in real time.
- Modifying any single binding from a named preset causes the dropdown to change to `Custom`. The custom preset is ephemeral until explicitly saved.
- The `Save As...` button (adjacent to the dropdown) writes the current state to a new named preset. This creates a `.kys` file on disk.
- There is no "Save" for overwriting built-in presets — only `Save As` to create a derivative.
- The `Delete` button removes user-created presets. Built-in presets cannot be deleted.

### 2.2 Visual Keyboard Layout (Upper Half)

A rendered, interactive representation of a physical keyboard occupying roughly the top half of the dialog.

**Hardware detection:** Premiere detects the connected keyboard hardware and renders the appropriate physical layout. If the hardware is unrecognized, it defaults to the US English QWERTY layout.

**Key color coding — the core visual language:**

| Color | Meaning |
|---|---|
| **Gray** | Unassigned — no shortcut is bound to this key (with the current modifier combination). |
| **Purple** | Application shortcut — a command bound at the application scope (works regardless of which panel has focus). |
| **Green** | Panel-specific shortcut — a command bound to a specific panel (only active when that panel has focus). |
| **Purple + Green (split)** | Dual assignment — the key has both an application-scope and a panel-scope binding. Premiere resolves conflicts by giving priority to the panel-specific binding when that panel is focused; otherwise the application binding fires. |

**Modifier key interaction:** The visual keyboard is _modifier-sensitive_. Holding `Shift`, `Ctrl`/`Cmd`, `Alt`/`Opt`, or any combination of these while viewing the keyboard _dynamically recolors_ all keys to reflect the bindings for that modified state. This means:

- Pressing nothing shows the base-layer bindings.
- Holding `Shift` shows all `Shift + <key>` bindings.
- Holding `Ctrl + Shift` shows all `Ctrl + Shift + <key>` bindings.
- Every modifier permutation is a distinct addressable layer.

**Tooltip behavior:** Hovering over any key displays a tooltip containing the command name(s) assigned to that key in the current modifier context.

**Click behavior:** Clicking a key in the visual keyboard selects it and populates the **Key Modifier List** (section 2.3) with all commands assigned to that physical key across all modifier combinations.

### 2.3 Key Modifier List (Below the Keyboard)

When a key is selected (clicked) on the visual keyboard, this region displays a list of _every_ command assigned to that physical key, broken down by modifier combination:

```
Key: K
  (none)      → Stop (Application)
  Ctrl        → Cut (Application)
  Shift       → [unassigned]
  Ctrl+Shift  → [unassigned]
  Alt         → [unassigned]
  ...
```

This is the fastest way to audit all modifier layers for a given key.

### 2.4 Command List and Search (Lower Half)

The bottom half of the dialog is a scrollable, searchable table of _all commands_ in Premiere Pro. There are hundreds of commands.

**Table columns:**

| Column | Content |
|---|---|
| **Command** | The human-readable name of the command (e.g., `Ripple Delete`, `Add Edit`, `Zoom In`). |
| **Shortcut** | The currently-assigned key combination. If unassigned, this cell is empty. Multiple shortcuts can exist per command. |
| **Application/Panel** | Indicates the scope — either `Application` or a named panel such as `Timeline`, `Program Monitor`, `Effects`, `Capture Panel`, etc. |

**Search bar:** A text field at the top of the command list. Typing filters the list in real time by command name substring match. This is the primary way users find commands to rebind.

**Two search paradigms exist in the editor:**

1. **Search by command name** — type in the search bar, the command list filters.
2. **Search by key** — click a key on the visual keyboard, the command list highlights/filters to commands using that key.

---

## 3. Shortcut Scoping System

This is the most architecturally significant aspect of the editor. Premiere Pro implements a two-tier scoping model for all keyboard shortcuts.

### 3.1 Application Shortcuts

These are global bindings. They fire regardless of which panel currently has focus. Examples: `Ctrl + S` (Save), `Ctrl + Z` (Undo), `Space` (Play/Stop).

Application shortcuts are _always available_ unless overridden by a panel-specific shortcut on the same key.

### 3.2 Panel Shortcuts

These are context-sensitive bindings. They only fire when a specific panel has focus. Premiere Pro has many panels, each of which can have its own shortcut namespace:

- Timeline
- Program Monitor
- Source Monitor
- Effects Panel
- Effects Control Panel
- Audio Mixer
- Project Panel
- Capture Panel
- Essential Graphics
- Titler (legacy)
- Media Browser
- Metadata Panel
- History Panel
- Audio Clip Mixer
- Essential Sound

### 3.3 Conflict Resolution and Priority

The scoping system enables a single physical key to do different things depending on context. The resolution order is:

1. **Panel-specific binding exists, and that panel has focus** → panel shortcut fires.
2. **No panel-specific binding for the focused panel** → application shortcut fires.
3. **Neither exists** → key is passed through (no action).

This means the same key can be reused across panels without conflict. For example:

- `F` as an application shortcut maps to `Match Frame`.
- `F` as a Capture Panel shortcut maps to `Fast Forward`.

When the Capture Panel is active, pressing `F` fast-forwards. When any other panel is active, `F` triggers Match Frame.

**Conflict warning behavior:** If a user assigns a shortcut that collides with an existing binding _in the same scope_, Premiere displays a yellow warning in the lower portion of the dialog. The warning identifies the conflicting command by name, and the `Undo` and `Clear` buttons become active. The user can then choose to:

- **Undo** — revert the assignment.
- **Clear** — remove the conflicting binding from the other command, leaving only the new assignment.
- **Ignore** — leave both in place (the newer assignment takes precedence, but this creates an ambiguity the editor warns about).

---

## 4. Assignment Mechanics

There are three methods to assign a shortcut:

### 4.1 Inline Editing (Click and Type)

1. Locate the command in the command list (via search or scroll).
2. Click the **Shortcut** column cell for that command. It enters an editable state.
3. Press the desired key combination. The cell captures the keystroke(s) including modifiers.
4. If a conflict exists, the warning appears. Otherwise, the binding is accepted immediately.

### 4.2 Drag and Drop

1. Locate the command in the command list.
2. Drag the command row onto a key in the visual keyboard layout.
3. To assign with a modifier (e.g., `Shift + G`), hold the modifier key _while dragging_ and drop onto the target key.
4. Alternatively, drag the command onto a specific modifier combination in the Key Modifier List.

### 4.3 Direct Key Click + Assignment

1. Click a key on the visual keyboard.
2. The Key Modifier List populates with all current assignments.
3. Click an empty modifier slot and select a command from the dropdown or type to search.

### 4.4 Removing Shortcuts

- Select the command in the command list, click the existing shortcut cell, and press `Delete` or `Backspace` to clear it.
- In the Key Modifier List, click the `×` next to an assignment to remove it.
- On the visual keyboard: click a colored key, inspect its assignments, and delete from the resulting list.

### 4.5 Multiple Shortcuts Per Command

Premiere allows a single command to have multiple shortcut bindings. For example, `Play/Stop` could be bound to both `Space` and `Enter` simultaneously. When viewing a command in the command list, a `+` button next to the shortcut cell allows adding additional bindings.

---

## 5. Preset Management and Persistence

### 5.1 The `.kys` File Format

All keyboard shortcut presets — both built-in and custom — are stored as `.kys` files. This is Premiere's proprietary keyboard shortcut serialization format (XML-based internally).

**File system locations:**

- **Windows:** `C:\Users\<username>\Documents\Adobe\Premiere Pro\<version>\Profile-<profilename>\Win\`
- **macOS:** `/Users/<username>/Documents/Adobe/Premiere Pro/<version>/Profile-<profilename>/Mac/`

If Creative Cloud Sync Settings is enabled, the path may vary slightly, with the profile folder named `Profile-CreativeCloud-` instead of `Profile-<computername>`.

### 5.2 Preset Operations

| Operation | Mechanism |
|---|---|
| **Save As** | Creates a new `.kys` file with a user-specified name. Appears in the preset dropdown on next open. |
| **Delete** | Removes a user-created `.kys` file. Built-in presets are protected. |
| **Reset to Default** | Selecting `Adobe Premiere Pro Default` from the dropdown restores factory bindings. |
| **Transfer between machines** | Copy the `.kys` file from the source machine's profile folder to the same relative path on the target machine. Restart Premiere. The preset appears in the dropdown. |
| **Cross-platform transfer** | `.kys` files are _not_ directly cross-platform. Ctrl-based bindings on Windows need to be remapped to Cmd on macOS. Third-party tools (e.g., Knights of the Editing Table's .kys converter) automate this remapping. |

### 5.3 Creative Cloud Sync

When Creative Cloud Sync Settings is enabled in Premiere's preferences, keyboard shortcut presets sync across machines logged into the same Adobe account. The synced `.kys` file lives under the `Profile-CreativeCloud-` directory and is uploaded/downloaded automatically.

---

## 6. Command Taxonomy

Commands in the shortcut editor are not flat — they are implicitly grouped by functional domain, though the UI presents them as a single sorted list. The major command categories are:

| Category | Examples |
|---|---|
| **File** | New Project, Open, Save, Save As, Import, Export |
| **Edit** | Undo, Redo, Cut, Copy, Paste, Paste Insert, Paste Attributes, Clear, Ripple Delete, Select All, Deselect All, Find |
| **Clip** | Speed/Duration, Audio Gain, Audio Channels, Make Subclip, Edit Subclip, Enable, Link, Group, Ungroup |
| **Sequence** | Render Effects, Match Frame, Reverse Match Frame, Add Edit, Add Edit to All Tracks, Trim Edit, Extend Selected Edit to Playhead, Apply Transitions |
| **Marker** | Add Marker, Go to Next Marker, Go to Previous Marker, Clear Current Marker, Clear All Markers |
| **Navigation** | Go to In, Go to Out, Play/Stop, Shuttle Left/Right (J/K/L), Step Forward/Back, Go to Sequence Start/End |
| **Tool Selection** | Selection Tool (V), Track Select Forward (A), Ripple Edit (B), Rolling Edit (N), Rate Stretch (R), Razor (C), Slip (Y), Slide (U), Pen (P), Hand (H), Zoom (Z) |
| **Panel Navigation** | Activate panels in rotation, maximize panel, toggle panel focus |
| **Timeline** | Zoom In/Out, Zoom to Sequence (\\), Zoom to Frame, Expand/Minimize tracks, Snap, Linked Selection |
| **Playback** | Play Around, Loop, Play In to Out, Shuttle Stop, Step Forward/Back (frame-level or multi-frame) |
| **Audio** | Add/Remove Audio Keyframe, Show Audio Time Units, Audio Mixer controls |
| **Source Monitor / Program Monitor** | Mark In, Mark Out, Clear In, Clear Out, Insert, Overwrite, Lift, Extract |
| **Multi-Camera** | Switch cameras (1-9), Record On/Off |
| **Workspace** | Switch between saved workspace layouts |
| **Unmapped (hundreds)** | Many commands ship with no default binding. These include: Join All Through Edits, Zoom to Frame, Move All Sources Up/Down, Add/Remove Video Keyframe, Replace with Clip From Source Monitor, etc. |

The existence of hundreds of unmapped commands is a deliberate design choice — it keeps the default layout minimal while giving power users the ability to surface deeply buried functionality via custom bindings.

---

## 7. Interaction Model — State Machine

The editor dialog behaves as a stateful editor with the following transitions:

```
[Launch Dialog]
    → Load active preset from disk
    → Render visual keyboard with base-layer coloring
    → Populate command list from internal command registry
    → Set preset dropdown to current preset name

[User holds modifier key(s)]
    → Recolor visual keyboard for that modifier layer

[User clicks key on visual keyboard]
    → Populate Key Modifier List for that key
    → Highlight/filter command list to show commands using that key

[User searches in search bar]
    → Filter command list by substring match on command name
    → Visual keyboard does not change

[User clicks shortcut cell in command list]
    → Cell enters capture mode (waiting for keystroke)
    → User presses key combo
    → If no conflict → binding accepted, keyboard recolors
    → If conflict → warning displayed, Undo/Clear buttons activate

[User drags command to keyboard key]
    → If modifier held → assigns to modifier+key
    → If no modifier → assigns to bare key
    → Same conflict resolution as above

[User clicks Save As]
    → Prompt for preset name
    → Write .kys file to profile folder
    → Dropdown updates to show new preset name

[User clicks OK]
    → Commit all changes to memory
    → Write active preset to .kys on disk
    → Close dialog

[User clicks Cancel]
    → Discard all uncommitted changes
    → Close dialog
```

---

## 8. Visual Keyboard Rendering Details

### 8.1 Layout Fidelity

The visual keyboard attempts to match the physical layout of the connected hardware. This includes:

- Standard ANSI 104-key layout (US)
- ISO layouts (European)
- JIS layouts (Japanese)
- Laptop-specific compressed layouts

If hardware detection fails, the US ANSI layout is used as fallback.

### 8.2 Key Size and Spacing

Keys are rendered proportionally — wider keys (Space, Shift, Enter, Backspace, Tab) are rendered at their correct relative widths. The number pad, arrow keys, and function row are all present and interactive.

### 8.3 Modifier Key Rendering

Modifier keys themselves (`Shift`, `Ctrl`/`Cmd`, `Alt`/`Opt`) are rendered on the visual keyboard but behave differently from character keys:

- They cannot receive direct command bindings.
- Holding them changes the modifier layer displayed across all other keys.
- They are rendered in a neutral color (not purple/green/gray).

---

## 9. Edge Cases and Noteworthy Behaviors

### 9.1 Same Key, Different Scope

A key can simultaneously hold an application shortcut and multiple panel shortcuts (one per panel). This is by design. The visual keyboard shows this as a split purple/green color.

### 9.2 Modifier-Only Shortcuts

Premiere does not support modifier-only shortcuts (e.g., pressing `Shift` alone to trigger a command). At least one non-modifier key must be part of the combination.

### 9.3 Multi-Key Sequences (Chords)

Premiere does **not** support chord-based shortcuts (e.g., `Ctrl+K` followed by `Ctrl+U` as a two-step sequence). All shortcuts are single key combinations (a key plus zero or more simultaneous modifiers).

### 9.4 Reserved Keys

Certain key combinations are reserved by the operating system and cannot be captured by Premiere's shortcut editor:

- `Ctrl + Alt + Delete` (Windows)
- `Cmd + Tab` (macOS)
- `Cmd + Space` (macOS Spotlight, unless remapped at OS level)
- Various OS-level accessibility shortcuts

### 9.5 Numpad vs. Main Keyboard

The number pad keys are treated as distinct from the number row keys above the letter keys. `Numpad 1` and `1` are separate bindable keys.

### 9.6 Print Keyboard Shortcuts

The editor includes a `Copy to Clipboard` or `Print` function that exports the current shortcut layout as a formatted text list. This is useful for creating physical reference cards.

---

## 10. Data Model (Conceptual)

The internal representation of a keyboard shortcut mapping can be modeled as:

```
ShortcutBinding {
    command_id: String           // Internal unique command identifier
    command_name: String         // Human-readable name
    scope: ApplicationScope | PanelScope(panel_id)
    key: PhysicalKey             // The physical key (e.g., KEY_K, KEY_F1, NUMPAD_5)
    modifiers: Set<Modifier>     // {CTRL, SHIFT, ALT} — empty set for bare key
}

Preset {
    name: String
    bindings: List<ShortcutBinding>
    source: BuiltIn | UserCreated
    file_path: Path              // .kys file location
}

KeyboardLayout {
    hardware_id: String
    layout_type: ANSI | ISO | JIS | Unknown
    key_positions: Map<PhysicalKey, (x, y, width, height)>
}
```

The `.kys` file serializes the `Preset` structure as XML. Each binding is an element containing the command ID, scope, key code, and modifier flags.

---

## 11. Accessibility

The keyboard shortcuts editor itself is navigable via keyboard (Tab, Arrow keys, Enter to confirm). Screen reader support is available for the command list and search bar. The visual keyboard is primarily a mouse-driven interface but exposes its state through the command list, which is fully keyboard-navigable.

---

## 12. Comparison with Other NLE Shortcut Editors

| Feature | Premiere Pro | DaVinci Resolve | Avid Media Composer | Final Cut Pro |
|---|---|---|---|---|
| Visual keyboard | Yes (color-coded) | Yes | No (list only) | Yes |
| Panel-scoped shortcuts | Yes (multi-panel) | Yes (page-based) | Yes (context-based) | Limited |
| Drag-and-drop assignment | Yes | No | No | No |
| Multiple shortcuts per command | Yes | Yes | Yes | Yes |
| .kys file portability | Yes (per-platform) | .txt import/export | Yes | plist-based |
| Cross-platform preset conversion | Third-party tools | Built-in | N/A | N/A |
| Hardware layout detection | Yes | No | No | No |
| Built-in NLE compatibility presets | FCP7, Avid | Premiere, FCP | Premiere (limited) | None |

---

## 13. Summary of Key Design Decisions

1. **Two-tier scoping (application + panel)** is the foundational design choice. It multiplies the effective keyspace by allowing reuse of keys across panel contexts without collision.

2. **Color-coded visual keyboard** provides immediate spatial awareness of binding density and scope distribution, letting editors spot unassigned keys and scope conflicts at a glance.

3. **Modifier-layer switching** (hold modifier to see that layer's bindings) makes the visual keyboard a live, explorable reference rather than a static cheat sheet.

4. **Hundreds of unmapped commands** is intentional — the default layout is deliberately sparse to avoid overwhelming new users, while the editor exposes the full command surface for power users to mine.

5. **`.kys` file as the persistence format** enables manual backup, cross-machine transfer, and community sharing of shortcut profiles, at the cost of requiring third-party tools for cross-platform conversion.

6. **No chord/sequence shortcuts** keeps the input model simple and latency-free — every shortcut is a single simultaneous key combination, which is critical for real-time editing workflows where millisecond response matters.
