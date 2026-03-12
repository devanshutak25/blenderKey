# DaVinci Resolve — Keyboard Shortcuts Editor: Design Document

## 1. Overview

The Keyboard Customization dialog is a system-level UI in DaVinci Resolve that provides full remapping of every bindable command across all application contexts. It is accessed via `DaVinci Resolve > Keyboard Customization` (macOS: `⌥⌘K`, Windows/Linux: `Ctrl+Alt+K`).

The editor serves three functions:
1. Visual introspection of all current bindings.
2. Remapping, adding, and removing bindings per-command or per-key.
3. Preset management — loading, saving, importing, exporting, and switching between named keyboard layout profiles.

---

## 2. System Architecture

### 2.1 Data Model

#### Keyboard Preset (Layout Profile)

A preset is the top-level container. It is a named, serializable collection of all key bindings across every context scope.

```
Preset
├── name: string                    // e.g., "DaVinci Resolve", "Adobe Premiere Pro"
├── isFactory: bool                 // true for built-in presets, false for user-created
├── isModified: bool                // dirty flag — true if any binding differs from saved state
└── bindings: Map<CommandID, List<Binding>>
```

#### Binding

A single mapping from a physical key combination to a command, within a context scope.

```
Binding
├── commandId: string               // internal unique identifier, e.g., "trim.ripple_delete"
├── key: PhysicalKey                 // the base key (A-Z, 0-9, F1-F12, punctuation, special keys)
├── modifiers: Set<Modifier>         // subset of {Ctrl/Cmd, Shift, Alt/Option}
├── scope: ContextScope              // which page/context this binding is active in
└── isConflicting: bool              // computed — true if another command in the same scope uses the same combo
```

#### PhysicalKey

An abstraction over the keyboard's physical layout. Resolve uses a US QWERTY reference layout internally. The visual keyboard display reflects this regardless of the user's actual OS keyboard layout (with caveats — see §5.3).

#### ContextScope (enum)

Scopes determine when a binding is active. A binding can be:

| Scope | Active When |
|---|---|
| `Global` | Always, across all pages. Lowest priority if a page-specific binding exists for the same combo. |
| `Media` | Media page is focused |
| `Cut` | Cut page is focused |
| `Edit` | Edit page is focused |
| `Fusion` | Fusion page is focused |
| `Color` | Color page is focused |
| `Fairlight` | Fairlight page is focused |
| `Deliver` | Deliver page is focused |

Additionally, some scopes are sub-page contexts:

| Sub-Scope | Active When |
|---|---|
| `Color.Nodes` | Node graph within Color page has focus |
| `Fusion.Comp` | Composition viewer in Fusion has focus |
| `Edit.Timeline` | Timeline panel in Edit page has focus |
| `Edit.SourceViewer` | Source viewer in Edit page has focus |
| `Fairlight.Mixer` | Mixer panel in Fairlight has focus |

**Scope Resolution Order**: When a key combo is pressed, Resolve resolves the binding by searching the most specific active scope first, then falls back to broader scopes:

```
Sub-page scope → Page scope → Global scope
```

The first match wins. This means a page-level binding shadows a global binding for the same key combo without removing it.

#### CommandID

Every bindable action has a unique internal identifier. Commands are organized hierarchically:

```
Application
├── Playback
│   ├── playback.play_forward
│   ├── playback.play_reverse
│   ├── playback.stop
│   ├── playback.play_around_current
│   └── ...
├── Timeline
│   ├── timeline.razor
│   ├── timeline.select_clips_forward
│   └── ...
├── Trimming
│   ├── trim.ripple_delete
│   ├── trim.slip_left_one_frame
│   └── ...
├── Marking
│   ├── mark.set_in
│   ├── mark.set_out
│   └── ...
├── Color
│   ├── color.toggle_bypass
│   ├── color.grab_still
│   └── ...
├── Fusion
│   ├── fusion.add_tool
│   └── ...
├── Fairlight
│   ├── fairlight.record_arm
│   └── ...
├── Application-wide
│   ├── app.save_project
│   ├── app.undo
│   ├── app.redo
│   ├── app.fullscreen
│   └── ...
└── ...
```

The total command count is approximately 700–900 depending on Resolve version and whether it's Studio or Free.

### 2.2 Persistence

| Artifact | Location | Format |
|---|---|---|
| Active preset selection | User preferences DB (PostgreSQL or disk DB depending on config) | Key-value |
| Built-in presets | Application bundle / installation directory | Read-only binary or XML |
| User presets | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Presets/Keyboard/` (macOS) or equivalent | `.txt` file (actually a proprietary key-value format, not plain text) |
| Exported presets | User-chosen path | `.drk` file (DaVinci Resolve Keyboard) — a portable file that can be shared |

The `.drk` export format is a self-contained serialization of the entire `Preset` object, including metadata. It can be imported on any platform (cross-platform compatible, with platform-specific modifier key remapping: `Cmd` ↔ `Ctrl`).

---

## 3. UI Structure

The Keyboard Customization dialog is a modal window with three primary regions stacked vertically, plus a toolbar.

### 3.1 Toolbar (Top Bar)

```
┌─────────────────────────────────────────────────────────────────┐
│ [Preset Dropdown ▾]  [Save] [Save As] [Delete] [Import] [Export]│
│                                              [Reset] [Close]    │
└─────────────────────────────────────────────────────────────────┘
```

**Preset Dropdown**: Lists all available presets. Factory presets are listed first, followed by user presets. The active preset is shown. Selecting a different preset instantly switches all bindings (with a confirmation dialog if the current preset has unsaved changes).

Factory presets (non-exhaustive):
- DaVinci Resolve (default)
- Adobe Premiere Pro
- Final Cut Pro X
- Avid Media Composer
- Pro Tools (Fairlight-focused)
- Smoke

**Save**: Writes current binding state to the active preset. Disabled for factory presets (forces Save As).

**Save As**: Creates a new user preset from the current state. Prompts for a name.

**Delete**: Removes the active user preset. Disabled for factory presets.

**Import / Export**: File dialog for `.drk` files.

**Reset**: Reverts the active preset to its last saved state (if user preset) or to factory defaults (if factory preset). Confirmation dialog.

### 3.2 Visual Keyboard (Middle Region)

A rendered representation of a full-size keyboard (approximately 104 keys, US QWERTY layout). Each key is a clickable, interactive element.

#### Key Visual States

Each key on the visual keyboard is color-coded:

| Color | Meaning |
|---|---|
| Dark gray (default) | No binding assigned in the currently selected scope filter |
| Solid color fill (teal/orange/etc.) | Binding exists in the currently selected scope filter |
| Red/orange highlight | Conflict — multiple commands bound to this key+modifier combo in the same scope |
| Bright highlight ring | Currently selected key (clicked by user) |

#### Modifier Key Interaction

The visual keyboard is **modifier-reactive**. The display updates in real-time based on which modifier keys the user is currently holding down (physically on their keyboard) or has toggled via on-screen modifier buttons:

- **No modifier held**: Shows all unmodified key bindings.
- **Ctrl/Cmd held**: Shows all Ctrl/Cmd+key bindings. Unbound keys revert to dark gray.
- **Shift held**: Shows all Shift+key bindings.
- **Alt/Option held**: Shows all Alt/Option+key bindings.
- **Compound modifiers** (e.g., Ctrl+Shift): Shows bindings for that specific compound modifier combination.

Each key tile displays a truncated command name label when a binding exists for the current modifier state. The label is typically abbreviated (e.g., "Ripple Del" instead of "Ripple Delete").

#### Clicking a Key

Clicking a key on the visual keyboard:
1. Selects that key.
2. Filters the command list (§3.3) to show only commands bound to that physical key (across all modifier combinations and scopes).
3. Highlights the key with a selection ring.
4. Populates a detail area showing all bindings for that key.

### 3.3 Command List (Bottom Region)

A filterable, scrollable table of all commands. This is the primary interface for assigning and removing bindings.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Search: [________________________]   Scope Filter: [All ▾]              │
│                                                                          │
│ Command                          │ Shortcut          │ Scope             │
│ ─────────────────────────────────┼───────────────────┼──────────────────│
│ ▾ Playback                       │                   │                   │
│   Play Forward                   │ L                 │ Global            │
│   Play Reverse                   │ J                 │ Global            │
│   Stop                           │ K                 │ Global            │
│   Play Around Current (to Out)   │ /                 │ Edit              │
│   Play In to Out                 │ Alt+/             │ Edit              │
│ ▾ Timeline                       │                   │                   │
│   Razor                          │ Ctrl+B            │ Edit              │
│   Razor                          │ Ctrl+B            │ Cut               │
│   Select All Clips Forward       │ Y                 │ Edit              │
│ ▾ Trimming                       │                   │                   │
│   Ripple Delete                  │ Delete            │ Edit              │
│   Ripple Delete                  │ Backspace         │ Edit              │
│   ...                            │                   │                   │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Search

Text search filters the command list by command name (substring, case-insensitive). The filter is applied live as the user types.

Additionally, you can search by shortcut key: typing a key combination into the search field while a "search by shortcut" toggle is active will filter to all commands currently bound to that combination.

#### Scope Filter Dropdown

Filters the command list to show only bindings in a specific scope, or all scopes. Options:

- All
- Global
- Media
- Cut
- Edit
- Fusion
- Color
- Fairlight
- Deliver

When a specific scope is selected, the visual keyboard also updates to reflect only bindings in that scope.

#### Command Row Interaction

Each row in the command list represents one command + binding pair. A single command can appear multiple times if it has multiple bindings or exists in multiple scopes.

**To assign a new shortcut**:
1. Select (click) the command row.
2. Click the shortcut cell, or press a designated "Assign Shortcut" button — the cell enters a capture state.
3. Press the desired key combination physically. The keystroke is captured (not acted upon by the OS or Resolve).
4. The binding is assigned immediately. If a conflict exists (another command already has that key combo in the same scope), a conflict dialog appears.

**To remove a shortcut**:
1. Select the command row.
2. Click the `X` button next to the existing shortcut, or press `Delete`/`Backspace` while the binding is selected.
3. The binding is removed. The command becomes unbound (unless it has other bindings).

**To add an additional shortcut to a command**:
1. Select the command row.
2. Click a `+` button in the shortcut column.
3. Capture the new keystroke.
4. The command now has two (or more) bindings.

There is no hard limit on the number of bindings per command, but practically more than 3 is unusual.

---

## 4. Conflict Resolution

### 4.1 Conflict Detection

A conflict occurs when two or more commands are bound to the same key combination within overlapping scopes. Conflict is computed in real-time as bindings change.

**Same scope, same key combo** → Hard conflict. Resolve displays a warning. The user must decide which command retains the binding.

**Parent/child scope overlap** (e.g., Global and Edit both have `Ctrl+B`) → Soft conflict. This is intentional behavior — the page-specific binding shadows the global one. No warning needed, but the visual keyboard may display both with a "shadowed" indicator.

### 4.2 Conflict Dialog

When a hard conflict is detected during assignment:

```
┌─────────────────────────────────────────────────────┐
│ Shortcut Conflict                                   │
│                                                     │
│ "Ctrl+B" is already assigned to:                    │
│                                                     │
│   "Razor" in scope "Edit"                           │
│                                                     │
│ Do you want to:                                     │
│                                                     │
│ [Assign Anyway (remove from Razor)]  [Cancel]       │
└─────────────────────────────────────────────────────┘
```

"Assign Anyway" removes the binding from the conflicting command and assigns it to the new one. The old command does not automatically receive a replacement binding.

---

## 5. Behavioral Details

### 5.1 Multi-Press Keys (JKL Transport)

Some bindings are velocity/repeat-sensitive. The JKL shuttle control is a notable example:

- `L` once = play forward 1x
- `L` twice = play forward 2x
- `L` three times = play forward 4x
- etc.

These multi-press behaviors are hardcoded into the command implementation, not the keyboard shortcut system. Rebinding `L` to a different command removes the shuttle behavior. Binding shuttle to a different key inherits the multi-press logic.

### 5.2 Held-Key vs. Pressed-Key Commands

Some commands differentiate between press and hold:

- **Press**: Triggered on key-down, fires once.
- **Hold**: Triggered on key-down, reverts on key-up (toggle while held). Example: `Shift` for snapping behavior inversion during a drag.

The binding system does not expose this distinction in the UI — it is a property of the command itself. The user cannot change a press-command into a hold-command.

### 5.3 Platform-Specific Modifier Mapping

| macOS | Windows/Linux | Notes |
|---|---|---|
| `⌘` (Command) | `Ctrl` | Primary action modifier |
| `⌥` (Option) | `Alt` | Secondary modifier |
| `⌃` (Control) | — | Rare, used for some viewport controls |
| `⇧` (Shift) | `Shift` | Same |

When importing a preset across platforms, modifiers are automatically remapped. `Cmd+C` on a macOS preset becomes `Ctrl+C` on Windows.

### 5.4 Reserved / Non-Bindable Keys

Certain keys are reserved and cannot be rebound:

- `Escape` — universally used for cancel/deselect (though some secondary Escape behaviors are bindable)
- OS-level shortcuts intercepted before they reach Resolve (e.g., `Cmd+Tab`, `Ctrl+Alt+Del`)
- Mouse buttons — not bindable through the keyboard shortcut editor (some mouse behaviors are configurable elsewhere in preferences)

### 5.5 Context Sensitivity Within a Page

Within a single page, focus determines which sub-scope is active. For example, on the Edit page:

- If the timeline panel has focus → `Edit.Timeline` scope is checked first.
- If the source viewer has focus → `Edit.SourceViewer` scope is checked first.
- If neither specific panel has focus → `Edit` scope is used.

The keyboard shortcut editor exposes these sub-scopes as filterable categories, but they are not always visually obvious. Many users operate entirely at the page scope level.

---

## 6. Visual Keyboard Rendering Details

### 6.1 Layout

The rendered keyboard uses a fixed US QWERTY 104-key layout:

```
Row 0: Esc  F1 F2 F3 F4  F5 F6 F7 F8  F9 F10 F11 F12    PrtSc ScrLk Pause
Row 1: `  1  2  3  4  5  6  7  8  9  0  -  =  Backspace   Ins  Home  PgUp    NumLk  /  *  -
Row 2: Tab  Q  W  E  R  T  Y  U  I  O  P  [  ]  \         Del  End   PgDn    7  8  9  +
Row 3: Caps  A  S  D  F  G  H  J  K  L  ;  '  Enter                           4  5  6
Row 4: Shift  Z  X  C  V  B  N  M  ,  .  /  Shift               Up            1  2  3  Enter
Row 5: Ctrl  Win  Alt  Space  Alt  Win  Menu  Ctrl        Left  Down  Right    0     .
```

Each key tile is rendered as a rounded rectangle with:
- Background fill (state-dependent color)
- Primary label (key character, centered or top-left)
- Secondary label (abbreviated command name, smaller font, bottom-center, only visible when a binding exists for the current modifier state)

### 6.2 Color Coding System

The visual keyboard uses a categorical color scheme to indicate which command category a bound key belongs to:

| Category | Color (approximate) |
|---|---|
| Playback/Transport | Blue |
| Timeline Navigation | Teal/Cyan |
| Editing/Trimming | Orange |
| Marking (In/Out) | Yellow |
| Tools | Green |
| Color Grading | Purple/Magenta |
| Application/System | Gray |
| Unbound | Dark Gray (near-background) |

These colors are consistent across all modifier states and help the user visually identify clusters of related bindings.

### 6.3 Tooltip on Hover

Hovering over a key tile shows a tooltip with:
- Full command name (unabbreviated)
- Full key combination (e.g., "Ctrl+Shift+B")
- Scope
- If conflicting: list of conflicting commands

---

## 7. Undo/Redo Within the Editor

The Keyboard Customization dialog has its own local undo stack, separate from the project undo. Each binding change (assign, remove, reassign due to conflict resolution) is an undoable operation.

- `Ctrl+Z` / `Cmd+Z` within the dialog undoes the last binding change.
- `Ctrl+Shift+Z` / `Cmd+Shift+Z` redoes.
- The undo stack is cleared when the dialog is closed or when a preset is switched.
- "Save" commits the current state. Undo after save still works within the session but "Reset" reverts to the last saved state, not the undo history.

---

## 8. Factory Preset Differences

Each factory preset remaps bindings to match the muscle memory of editors coming from other NLEs. Key structural differences:

| Behavior | DaVinci Default | Premiere Pro Preset | FCP X Preset | Avid Preset |
|---|---|---|---|---|
| Blade/Razor | `Ctrl+B` | `C` | `B` | — (uses different paradigm) |
| Ripple Delete | `Delete` | `Shift+Delete` | `Shift+Delete` | `Z` |
| Mark In | `I` | `I` | `I` | `I` (same across all) |
| Mark Out | `O` | `O` | `O` | `O` (same across all) |
| JKL Transport | J/K/L | J/K/L | J/K/L | J/K/L (universal convention) |
| Undo | `Ctrl+Z` | `Ctrl+Z` | `Cmd+Z` | `Ctrl+Z` |
| Source/Record Toggle | `Q` | — | — | — |

Factory presets only remap the bindings — they do not change Resolve's actual editing paradigm or behavior. A "Premiere Pro" preset makes the keys familiar, but the underlying trim/edit model is still Resolve's.

---

## 9. Search Modes

The search bar in the command list supports two distinct modes:

### 9.1 Search by Command Name (Default)

Standard substring search. Typing "ripple" shows all commands containing "ripple" in their name. Case-insensitive.

### 9.2 Search by Shortcut Key

Activated by clicking a "keyboard" icon toggle next to the search bar. In this mode, pressing a key combination in the search field filters to all commands currently bound to that combination (across all scopes). Useful for answering "what does Ctrl+Shift+X do?"

---

## 10. Edge Cases and Limitations

1. **Numpad vs. main keyboard**: Numpad keys are treated as distinct from their main keyboard equivalents. `Numpad 1` and `1` (top row) are separate bindable keys. Many factory presets bind numpad keys to specific functions (e.g., numpad for switching viewer layouts).

2. **No per-project keyboard presets**: Keyboard presets are application-level, not project-level. Switching projects does not switch presets.

3. **No conditional bindings**: The system does not support "bind X only when a clip is selected" or "bind X only during playback." The scope system is purely page/panel-based.

4. **No macro support**: The keyboard shortcut system maps one key combo to one command. There is no built-in macro recorder or multi-command binding. (Scripting and Fusion macros exist but are separate systems.)

5. **No hold-duration bindings**: There is no "short press vs. long press" distinction exposed in the binding system. Some commands internally implement tap-vs-hold behavior, but this is not user-configurable.

6. **International keyboard layouts**: The visual keyboard always renders US QWERTY. Users on AZERTY, QWERTZ, JIS, or other layouts must mentally translate. The physical key position is what matters — binding to "the key in the Q position" works regardless of what character that key produces in the user's locale. This is a known UX limitation.

7. **Maximum shortcut display in visual keyboard**: If a key has bindings across multiple modifier states, the visual keyboard only shows the label for the currently active modifier state. There is no way to see "all bindings for the A key" on the visual keyboard simultaneously — you must cycle through modifier states or use the command list.

---

## 11. File Format — .drk Export

The `.drk` file is a text-based serialization. Approximate structure (not officially documented by BMD):

```
[Header]
Version=2
PresetName=My Custom Layout
Platform=macOS
ResolveVersion=19.1

[Bindings]
playback.play_forward=L|Global
playback.play_reverse=J|Global
playback.stop=K|Global
trim.ripple_delete=Delete|Edit
trim.ripple_delete=Backspace|Edit
timeline.razor=Ctrl+B|Edit
timeline.razor=Ctrl+B|Cut
color.toggle_bypass=Shift+D|Color
...
```

Key observations:
- One line per binding (not per command — multi-bound commands have multiple lines).
- Modifier keys are serialized in a canonical order: `Ctrl+Shift+Alt+Key`.
- Platform field enables automatic modifier remapping on import.
- The format is forward-compatible; unknown command IDs are preserved but inactive.

---

## 12. Interaction Flow Diagrams

### 12.1 Assigning a New Shortcut

```
User selects command in list
    → User clicks shortcut cell or presses "Assign"
        → UI enters key capture mode (visual indicator: pulsing cell)
            → User presses key combination
                → System checks for conflicts in the target scope
                    → No conflict:
                        │ Binding is assigned
                        │ Visual keyboard updates
                        │ Preset marked as modified
                    → Conflict found:
                        │ Conflict dialog shown
                            → User selects "Assign Anyway":
                            │   Old binding removed from conflicting command
                            │   New binding assigned
                            │   Both entries update in command list
                            → User selects "Cancel":
                                │ No change
```

### 12.2 Switching Presets

```
User opens preset dropdown
    → Selects a different preset
        → Current preset has unsaved changes?
            → Yes:
            │   "Save changes?" dialog
            │       → Save: writes current state, then switches
            │       → Don't Save: discards changes, switches
            │       → Cancel: stays on current preset
            → No:
                │ Preset switches immediately
                │ All bindings reload
                │ Visual keyboard re-renders
                │ Command list re-populates
```

---

## 13. Performance Considerations

- The command list contains 700–900 entries. Filtering and rendering uses virtualized scrolling — only visible rows are rendered in the DOM/widget tree.
- Visual keyboard re-rendering on modifier state change is immediate (<16ms) — it is a lookup into the binding map, not a re-parse.
- Preset switching involves a full reload of the binding map. On modern hardware this is imperceptible (<50ms), but on disk-backed preset storage there may be a brief I/O stall.
- Search filtering is debounced (typically ~150ms after last keystroke) to avoid excessive re-renders.
