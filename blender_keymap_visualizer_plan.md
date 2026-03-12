# Blender Keymap Visualizer — Addon Development Plan

## Overview

A Blender 5.0+ addon that provides a visual keyboard-based keymap editor, comparable to the hotkey editors in Premiere Pro, DaVinci Resolve, and Houdini. Opens in a dedicated window with GPU-drawn keyboard, full keymap browsing, editing, conflict resolution, and export — replacing (and superset of) Blender's built-in keymap preferences panel.

**Target:** Personal use, Blender 5.0+, QWERTY ANSI layout.

---

## Architecture

### Components

| Component | Implementation |
|---|---|
| Entry point | Button appended to `VIEW3D_HT_header` in 3D Viewport |
| Visualizer window | New Blender window, area set to `TEXT_EDITOR` (neutral dark background) |
| Keyboard + UI rendering | `gpu` module + `blf`, `POST_PIXEL` draw handler on `SpaceTextEditor` |
| Event handling | Blocking modal operator running in the text editor window |
| Context menus | Native `bpy.types.Menu` via `wm.call_menu()` |
| Conflict resolution | GPU-drawn overlay state within the modal (not a nested dialog) |
| Dropdowns (editor filter) | Native `bpy.types.Menu` via `wm.call_menu()` |
| Data source | `wm.keyconfigs.user` for read/write |
| Export | Custom Python script generator matching Blender's `keyconfig_data` format |

### Modal Operator States

```
IDLE → default state, keyboard displayed, hover/click active
SELECTED → a key is selected, bottom panel shows bindings
CAPTURE → waiting for next keypress to rebind
CONFLICT → conflict detected, overlay shows Swap/Override/Cancel buttons
MENU_OPEN → native menu invoked, modal passes through until menu dismissed
```

### Draw Handler Scoping

`SpaceTextEditor.draw_handler_add` registers globally for ALL text editor spaces. The draw callback must check that `context.area` matches the addon's dedicated window/area before drawing. Store the area reference at launch time and compare on each draw call.

---

## Known Risks & Mitigations

### RISK 1 — Window creation + modal event routing (CRITICAL)

**Problem:** `bpy.ops.wm.window_new()` duplicates the current screen. The new window starts as a clone, not a text editor. The modal handler must be added to the *new* window's context, not the original, otherwise events in the new window don't reach the modal.

**Mitigation:** Two-stage launch:
1. Operator in 3D viewport calls `wm.window_new()`, finds the new window (last in `wm.windows`), changes its area type to `TEXT_EDITOR`.
2. Uses `bpy.app.timers.register()` with a one-shot deferred callback (~0.05s) that invokes the actual modal operator via `context.temp_override(window=new_window, area=new_area)`.

**Fallback:** If `wm.window_new()` fails or the area type switch doesn't stick, open the modal in an existing text editor area (user must have one open) or fall back to the 3D viewport with a semi-transparent background overlay.

**Validation:** Phase 1 exists solely to prove this works before any other code is written.

### RISK 2 — `wm.call_menu()` from inside a modal

**Problem:** Calling a native menu from within a modal creates a nested event handler. The menu captures events until dismissed. Does the modal resume correctly?

**Mitigation:** The modal sets a `MENU_OPEN` state before calling `wm.call_menu()`. The menu item operators are separate classes that modify module-level state (a dict storing the action and target binding). When the modal receives its next event after menu dismissal, it checks the shared state, processes the action, and returns to `IDLE`. The modal returns `{'PASS_THROUGH'}` for events while in `MENU_OPEN` state to avoid swallowing the menu's events.

**Fallback:** If native menus cause issues, replace with GPU-drawn popup rects (more code, but fully within the modal's control).

### RISK 3 — No scissor test in `gpu.state`

**Problem:** The Python GPU API doesn't expose scissor testing. The binding list at the bottom needs clipping when it overflows.

**Mitigation:** Don't draw items outside the visible scroll bounds. Calculate per-item visibility based on scroll offset and panel bounds. Text partially overlapping the boundary gets skipped (acceptable visual tradeoff). `blf.CLIPPING` can clip text labels at the boundary.

### RISK 4 — Export requires Preferences context

**Problem:** `bpy.ops.preferences.keyconfig_export()` polls for Preferences area context. Our modal runs in a Text Editor.

**Mitigation:** Write our own export function. The format is a Python script containing a `keyconfig_data` list of tuples: `(keymap_name, keymap_params_dict, {"items": [...]})`, plus an `if __name__ == "__main__"` block calling `keyconfig_import_from_data()`. We already have all the keymap data introspected, so generating this is straightforward formatting.

### RISK 5 — Multi-key sequence detection is heuristic

**Problem:** Blender doesn't expose a formal "key sequence" concept. Sequences like G → X (grab, then constrain to X) are actually modal operator keymaps — the first key triggers the operator, which enters modal mode and defines its own internal keymap for subsequent keys.

**Mitigation:** For v1, identify these by checking which keymaps have `is_modal` set, and which operators spawn modal keymaps. Display them as a note on the key ("has modal follow-ups") rather than a full drill-down. Document the limitation. Phase 7 item 5 can improve this with a drill-down view.

---

## Phase 1 — Window Management Proof-of-Concept

**Goal:** Validate the highest-risk technical component. Open a new window, set it to text editor, launch a modal, draw a rectangle, confirm events flow correctly.

### Steps

1. **Addon skeleton** (H confidence)
   - `bl_info`, register/unregister, single-file structure
   - Launcher operator class (`WM_OT_keymap_viz_launch`)
   - Modal operator class (`WM_OT_keymap_viz_modal`) — stub
   - Header draw function appended to `VIEW3D_HT_header`
   - **Re-entrant guard:** module-level boolean `_visualizer_running = False`. Launcher checks this in `poll()` — returns `False` if already running. Modal sets it `True` on invoke, `False` on finish/cancel. This prevents multiple instances.

2. **Window creation** (L confidence — this is the thing being validated)
   - Launcher operator: call `bpy.ops.wm.window_new()`
   - Find the new window: compare `wm.windows` before/after, or take the last one
   - Set `area.ui_type = 'TEXT_EDITOR'` on the new window's first area
   - Register a one-shot timer via `bpy.app.timers.register()` that invokes the modal operator with `temp_override` pointing at the new window + area

3. **Minimal draw handler** (H confidence)
   - `SpaceTextEditor.draw_handler_add(callback, args, 'WINDOW', 'POST_PIXEL')`
   - Draw callback: check `context.area` matches our target area, draw a colored rectangle and "Hello Keymap" text via `blf`
   - Store area reference for scoping

4. **Minimal modal** (H confidence)
   - `modal()`: handle `MOUSEMOVE` (update a position), `ESC` (cleanup + close)
   - On ESC: remove draw handler, close the spawned window (`bpy.ops.wm.window_close()` with temp_override), return `{'FINISHED'}`
   - **Window close guard:** on every modal event, verify the target window/area still exists (user may close the window via OS controls). If the window is gone, clean up draw handler and return `{'CANCELLED'}`. Check by testing if `self._target_window` is still in `context.window_manager.windows`.
   - Confirm: mouse move updates are received, rectangle redraws, ESC cleans up

### Checkpoint

- Button appears in 3D viewport header
- Clicking it opens a new window set to text editor
- A colored rectangle and text renders in the new window
- Mouse movement is tracked (draw a dot at cursor position)
- ESC closes the window and cleans up handlers
- Closing the window via OS controls (X button) does not crash — modal detects window loss and cleans up
- Clicking the header button while the visualizer is already open does NOT open a second instance (re-entrant guard)
- No orphaned draw handlers or windows on repeated open/close cycles

### Risks at this phase

- Area type switch may not take effect immediately → test with different timer delays (0.01s, 0.05s, 0.1s)
- Modal may not receive events in the new window → if so, explore calling `modal_handler_add` with a temp_override, or invoking the modal operator directly in the new window via temp_override
- Window close on ESC may fail if the context isn't right → use temp_override

---

## Phase 2 — Keyboard Layout & Rendering

**Goal:** Draw a complete QWERTY ANSI keyboard with proper key sizing, labels, and modifier toggle buttons.

### Steps

1. **Keyboard layout data structure** (H confidence)
   - Static Python dict/list defining the ANSI QWERTY layout
   - Each key: `(label, blender_event_type, width_units)`
   - Rows: Function row (Esc, F1-F12), number row, QWERTY row, home row, bottom row, space bar row
   - Sections: main block, navigation cluster (Ins/Del/Home/End/PgUp/PgDn), arrow keys, numpad
   - Width units: 1u = standard key, Tab = 1.5u, Caps = 1.75u, Shift = 2.25u/2.75u, Space = 6.25u, etc.

2. **Layout engine** (H confidence)
   - Function: given `(start_x, start_y, unit_size_px)`, compute pixel rects for every key
   - Account for gaps between sections (main block ↔ nav cluster ↔ numpad)
   - Store computed rects in a list: `[(key_id, blender_event_type, Rect(x, y, w, h)), ...]`
   - Responsive: recalculate on window resize (read `context.region.width/height` in draw callback)

3. **Key rendering** (H confidence)
   - Each key: filled rect (gpu UNIFORM_COLOR, `'TRIS'` with 2 triangles per quad) + border rect (POLYLINE_UNIFORM_COLOR) + centered label (blf)
   - Use `'TRIS'` with index buffer from the start — `'TRI_FAN'` only draws one polygon per batch and prevents batching all keys into a single draw call
   - Color states: unbound (dark gray), bound (theme blue), hovered (lighter), selected (highlight)
   - Pre-build batches for the entire keyboard once, rebuild only when state changes
   - Labels via `blf.dimensions()` for centering, `blf.draw()` for rendering

4. **Modifier toggle bar** (H confidence)
   - Draw 4 toggle buttons above the keyboard: Ctrl, Shift, Alt, OS
   - Each is a clickable rect with on/off state
   - Active modifiers filter which bindings are shown on the keyboard
   - Visual: filled when active, outlined when inactive

5. **Window resize handling** (M confidence)
   - The draw callback checks `context.region.width/height` each frame against cached values
   - If changed: recalculate all key rects and rebuild GPU batches, update cached dimensions
   - Do NOT detect resize in the modal event handler — the draw callback is the right place since it fires on every redraw and has access to current region dimensions
   - Risk: batch rebuild on resize could cause a frame hitch → acceptable, resizing is infrequent

### Checkpoint

- Full QWERTY keyboard renders in the text editor window
- Keys are properly sized and spaced (looks like a real keyboard layout)
- Modifier toggles are visible and render correctly (clickability wired in Phase 4 when hit testing is built)
- Keyboard scales with window size
- Labels are readable at various window sizes

---

## Phase 3 — Keymap Data Layer

**Goal:** Extract all keybinding data from Blender and display it on the visual keyboard.

### Steps

1. **Keymap index builder** (H confidence)
   - Iterate `wm.keyconfigs.user.keymaps`
   - For each keymap, iterate `keymap.keymap_items`
   - Build index: `dict[(event_type, ctrl, shift, alt, oskey)] → list[BindingInfo]`
   - `BindingInfo`: namedtuple/dataclass with `kmi` reference, `keymap_name`, `space_type`, `region_type`, `operator_idname`, `operator_name`, `is_active`
   - Rebuild index on any modification

2. **Editor/mode filter** (M confidence)
   - Collect all unique keymap names from `wm.keyconfigs.user.keymaps`
   - Group by space type: "3D View", "Node Editor", "UV Editor", "Timeline", "Global", etc.
   - Store active filter as a plain Python attribute on `self` in the modal operator (not a `bpy.props` property — RNA properties on operators are set at invoke time and shouldn't be mutated during modal execution)
   - Filter the index: only show bindings from keymaps matching the active filter
   - "All Keymaps" option shows everything (with color-coded overlap indicators)

3. **Editor selector menu** (M confidence)
   - Register a `bpy.types.Menu` subclass with all keymap categories
   - Drawn as a clickable button in the toolbar area above the keyboard
   - On click: `wm.call_menu(name="KEYVIZ_MT_editor_select")`
   - Menu items: each calls an operator that sets the filter and triggers index rebuild
   - Modal handles the `MENU_OPEN` → `IDLE` transition

4. **Color-code keys based on bindings** (H confidence)
   - On each draw: for each key rect, check the index with current modifier state
   - Colors: unbound (dark gray), single binding (blue), multiple bindings/conflict (orange/red), selected (bright highlight)
   - Show binding count badge on keys with 2+ bindings under current modifiers

5. **Key tooltip on hover** (H confidence)
   - On `MOUSEMOVE`: check which key rect the cursor is over
   - Draw a small tooltip near the cursor showing the primary binding's operator name
   - Use `blf` with a background rect for readability

6. **Multi-key sequence indicators** (M confidence)
   - Scan keymaps for `is_modal == True`
   - For operators that have associated modal keymaps, mark their trigger key with a small dot/indicator
   - Tooltip appends "has follow-up keys" note
   - No drill-down in this phase

### Checkpoint

- Keys are color-coded by binding status
- Modifier filtering works: holding Ctrl/Shift/Alt on the keyboard (detected via `event.ctrl`/`event.shift`/`event.alt` in the modal) updates the keyboard to show bindings for that modifier combo. Mouse-click toggling of modifier buttons comes in Phase 4.
- Editor selector dropdown works and filters to specific editor keymaps
- Hovering a key shows which operator is bound to it
- Keys with multiple bindings are visually distinct
- Switching editor filter updates the keyboard display immediately

---

## Phase 4 — Interaction System

**Goal:** Click keys, view binding details, scroll through binding lists.

### Steps

1. **Hit testing framework** (H confidence)
   - Key rects and UI element rects are computed once by the layout engine (Phase 2) and stored on the modal operator as a shared data structure
   - The draw callback reads from this structure to draw; the modal event handler reads from it to hit-test
   - Do NOT rebuild the hit list during the draw pass — the draw callback should be read-only against layout data
   - Hit list structure: `[(Rect, element_id, element_type), ...]`
   - Element types: `KEY`, `MODIFIER_TOGGLE`, `TOOLBAR_BUTTON`, `BINDING_LIST_ITEM`, `PANEL_BUTTON`
   - On `LEFTMOUSE PRESS`: iterate hit list, find first rect containing `(mouse_region_x, mouse_region_y)`
   - On `RIGHTMOUSE PRESS`: same hit test, dispatch to context menu if target is a key or binding
   - On `MOUSEMOVE`: update hover state for visual feedback, `tag_redraw()` if hover target changed
   - All coordinates in region-space (bottom-left origin, Y-up)

2. **Key selection** (H confidence)
   - Left-click on a key: set `selected_key` on the modal
   - Selected key gets highlight color
   - Triggers the bottom panel to show all bindings for that key (under current modifier state and editor filter)

3. **Bottom panel — binding list** (M confidence)
   - Occupies bottom ~30% of the window, below the keyboard
   - Horizontal divider line between keyboard and panel
   - List columns: Operator Name | Keymap Context | Modifiers | Active (checkbox visual)
   - Column headers drawn as static text
   - Each row is a hit-testable rect
   - Selected row shows details (operator idname, full keymap path, map type)
   - Scroll: `WHEELUPMOUSE`/`WHEELDOWNMOUSE` adjust scroll offset when cursor is within panel bounds
   - Clipping: skip drawing items outside visible bounds, `blf.CLIPPING` for text at boundaries

4. **Binding list row interaction** (M confidence)
   - Left-click: select row, show full details
   - Right-click: open context menu for that binding
   - Double-click (optional, defer if complex): enter rebind mode for that binding

5. **Toolbar rendering** (H confidence)
   - Top bar above keyboard: Editor filter button, Modifier toggles, Search placeholder (grayed out for now), Export button
   - Each is a hit-testable rect with label
   - Active editor filter shows its name on the button

### Checkpoint

- Clicking a key selects it and shows bindings in the bottom panel
- Binding list scrolls when there are many bindings
- Clicking a binding row shows full details
- Right-click on a key or binding is detected and logged (context menu wiring happens in Phase 5)
- Toolbar buttons are clickable and functional (editor filter, modifier toggles)
- Hit testing doesn't false-positive on overlapping elements

---

## Phase 5 — Editing & Context Menu

**Goal:** Rebind keys, resolve conflicts, modify keymaps.

### Steps

1. **Context menu — native Menu** (M confidence)
   - Register `KEYVIZ_MT_key_context` menu class
   - Items: "Rebind", "Unbind", "Reset to Default", "Toggle Active"
   - Before calling `wm.call_menu()`: store the target key and binding index in a module-level dict
   - Two action patterns:
     - **Immediate actions** (Unbind, Reset, Toggle): menu item operator executes the change directly, sets a "dirty" flag so modal rebuilds the index on next event
     - **Deferred state change** (Rebind): menu item operator only sets a "pending_action = REBIND" flag; modal reads this on next event and enters `CAPTURE` state
   - Modal checks the shared state dict on every event cycle after `MENU_OPEN` state

2. **Rebind capture mode** (M confidence)
   - User selects "Rebind" from context menu
   - Modal enters `CAPTURE` state
   - Draw callback shows overlay text: "Press new key combination..." with Cancel hint
   - Status bar: `context.area.header_text_set("Press new key | ESC to cancel")`
   - Next `PRESS` event is checked against a whitelist of valid key types (letters A-Z, numbers, F1-F24, special keys like TAB/SPACE/DEL, numpad, arrows, punctuation). Reject mouse events, timer events, NDOF events, modifier-only keys (LEFT_CTRL etc.), and MOUSEMOVE. This prevents accidental capture of non-keyboard input.
   - **ESC is explicitly excluded from capture** — it always cancels and returns to IDLE
   - On capture: check for conflicts before applying

3. **Conflict detection** (H confidence)
   - After capturing new key+modifiers: query the index for existing bindings on that combo
   - Filter conflicts to same keymap scope (same editor context)
   - If no conflicts: apply immediately
   - If conflicts: enter `CONFLICT` state

4. **Conflict resolution overlay** (M confidence)
   - GPU-drawn overlay panel in center of window (semi-transparent background)
   - Shows: "Conflict detected" header
   - List of conflicting bindings: operator name, keymap, current key combo
   - Three buttons: "Swap" (exchange bindings), "Override" (unbind old, bind new), "Cancel"
   - Hit testing on the overlay buttons
   - Swap: set old binding to our previous key, set our binding to new key
   - Override: set old binding inactive or remove, set our binding to new key
   - Cancel: return to IDLE, no changes

5. **Apply keymap changes** (H confidence)
   - Modify the `KeyMapItem` directly: `kmi.type`, `kmi.ctrl`, `kmi.shift`, `kmi.alt`, `kmi.oskey`
   - For unbind: `kmi.active = False` or `keymap.keymap_items.remove(kmi)`
   - For reset: call `keymap.restore_to_default()` resets the entire keymap (too broad). For per-item reset: compare against `wm.keyconfigs.default` to find the original values, then set `kmi.type`, `kmi.value`, modifiers back to defaults manually. Alternatively, remove the user-modified kmi and let the default fall through.
   - After any change: rebuild the binding index, redraw keyboard
   - Blender auto-saves keymap changes to user preferences on quit

6. **Unbind and Toggle Active** (H confidence)
   - Unbind: set `kmi.active = False` (keeps the binding but disables it)
   - Toggle Active: flip `kmi.active`
   - Visual feedback: inactive bindings shown as dimmed/striped on the keyboard

### Checkpoint

- Right-click on a bound key opens context menu with Rebind/Unbind/Reset/Toggle options
- Rebind capture mode works: press a new key, it gets assigned
- Conflicts are detected and the resolution overlay appears
- Swap and Override both work correctly
- Changes persist (visible in Blender's own keymap preferences)
- **Note:** Keymap changes are user preference modifications, NOT part of Blender's undo stack. Ctrl+Z will not revert binding changes. The "Reset to Default" option in the context menu is the user's recovery path.

---

## Phase 6 — Export

**Goal:** Export modified keybindings in Blender's native keyconfig format.

### Steps

1. **Generate keyconfig_data structure** (H confidence)
   - Iterate all keymaps in `wm.keyconfigs.user`
   - For each keymap with user modifications, generate a tuple:
     ```python
     (keymap.name,
      {"space_type": keymap.space_type, "region_type": keymap.region_type},
      {"items": [(kmi.idname, {"type": kmi.type, "value": kmi.value, ...}, properties_dict), ...]})
     ```
   - Match Blender's own export format exactly (compare against a Blender-generated export)

2. **Write Python script** (H confidence)
   - Template:
     ```python
     keyconfig_data = [...]

     if __name__ == "__main__":
         import os
         from bl_keymap_utils.io import keyconfig_import_from_data
         keyconfig_import_from_data(
             os.path.splitext(os.path.basename(__file__))[0],
             keyconfig_data)
     ```
   - **Verify during Phase 1:** confirm `bl_keymap_utils.io.keyconfig_import_from_data` exists in Blender 5.0 (`import bl_keymap_utils.io` in the console). This function has existed since 2.80 but is not guaranteed stable across major versions.
   - File save dialog: invoke `wm.invoke_props_dialog` or use a simple file path property with `INVOKE_DEFAULT` to get a file browser — OR since we're in a modal, use a hardcoded path with user-configurable export directory in addon preferences

3. **Export button in toolbar** (H confidence)
   - Click "Export" in toolbar → triggers export logic
   - For file browser: temporarily exit modal, invoke file browser operator, re-launch modal on completion — complex
   - Simpler: write to a default path (e.g., `~/.config/blender/5.0/scripts/presets/keyconfig/custom_keymap.py`) and show a report message
   - Or: add an export path property to addon preferences, export to that path on click

4. **Export scope options** (M confidence)
   - "Modified only" (default): only keymaps/items that differ from the addon keyconfig defaults
   - "All": full keyconfig dump
   - Toggle in toolbar or addon preferences

### Checkpoint

- Export button produces a valid `.py` file
- The exported file can be imported via Blender's Edit > Preferences > Keymap > Import
- Round-trip: export → import on a fresh Blender → same bindings

---

## Phase 7 — Polish & Deferred Features

**Goal:** Quality of life improvements, visual polish, and features deferred from earlier phases.

### Steps

1. **Search/filter text input** (M confidence)
   - GPU-drawn text input in toolbar
   - Keystroke capture: alphanumeric → append to search string, Backspace → delete, Enter → confirm, ESC → clear
   - Filter binding list and keyboard highlighting by operator name substring match
   - Risk: custom text input widget is a mini-project; consider limiting to simple substring (no cursor positioning, no selection)

2. **Color scheme in addon preferences** (H confidence)
   - AddonPreferences with `FloatVectorProperty(subtype='COLOR')` for: key_unbound, key_bound, key_conflict, key_selected, key_hovered, background, text, panel_bg
   - Defaults to a dark theme matching Blender's default

3. **Visual polish** (M confidence)
   - Rounded key corners (triangulated arc geometry or chamfered rects)
   - Subtle drop shadows on keys (second rect offset by 1-2px, darker color)
   - Smooth hover transitions (if performance allows — animate color over 2-3 frames using timer)
   - Key press animation (brief scale pulse when a binding is changed)

4. **Performance optimization** (M confidence)
   - Batch all key rects into a single GPU batch (one draw call for all key backgrounds)
   - Separate batch for borders, separate for selected/hovered (overlay)
   - Only rebuild batches when state changes, not every frame
   - Profile `blf.draw()` calls — if slow with 100+ labels, consider caching to a texture (advanced, likely unnecessary)

5. **Multi-key sequence drill-down** (L confidence)
   - When clicking a key that triggers a modal operator, show a second keyboard view filtered to that operator's modal keymap
   - Requires mapping operators to their modal keymaps (no direct API, must scan by convention)
   - Defer unless specifically needed

6. **Window close edge case hardening** (H confidence)
   - Phase 1 adds the basic window-gone check. This phase hardens it:
   - Handle `WINDOW_DEACTIVATE` events (user switches to another window)
   - Handle rapid open/close cycles without orphaning handlers
   - Test: close window via OS controls while in CAPTURE or CONFLICT state — ensure clean teardown

---

## Cross-Cutting Concerns

These patterns apply across all phases and should be followed from Phase 1 onward.

### `tag_redraw()` discipline

The modal must call `context.area.tag_redraw()` on every event that changes visual state (hover target change, selection change, scroll offset change, state transition). Without this, the viewport won't redraw and the UI appears frozen. Call it in the modal, NOT in the draw callback (draw callbacks should be side-effect-free).

### Stale area/window references

The plan stores a reference to the target area/window at launch time. Blender area references can become stale after undo or file load. Since this is a blocking modal, the user shouldn't be able to trigger undo or file load during operation. However, as a defensive measure: before using stored area/window references, verify they still exist in `context.window_manager.windows` / `window.screen.areas`. If stale, abort cleanly.

### GPU state restoration

Every draw callback must restore GPU state after modifying it. Pattern:
```
gpu.state.blend_set('ALPHA')
# ... draw ...
gpu.state.blend_set('NONE')
```
Failing to restore state corrupts Blender's own drawing in the same region.

### Module-level shared state

Communication between the modal operator and native Menu operators uses a module-level dict (e.g., `_menu_context = {}`). This is the only clean way to pass context from a modal to a menu and back. Keep this dict minimal: `target_key`, `target_binding_index`, `pending_action`, `dirty_flag`. Clear it on modal finish/cancel.

---

## File Structure

```
keymap_visualizer/
├── __init__.py              # bl_info, register/unregister, operator & class registration
├── keyboard_layout.py       # QWERTY ANSI layout data, rect computation
├── keymap_data.py           # Keymap extraction, indexing, modification, export
├── drawing.py               # GPU drawing: keyboard, panels, toolbar, overlays
├── ui_framework.py          # Hit testing, scroll state, element rects, hover/selection
├── modal_operator.py        # Main modal operator, state machine, event dispatch
├── menus.py                 # Native Menu classes (context menu, editor selector)
├── operators.py             # Small operators (rebind action, unbind, toggle, export trigger)
└── preferences.py           # AddonPreferences, color scheme, export path
```

Single-file for Phase 1-2 prototyping. Split into multi-file at Phase 3 when complexity warrants it.

**Registration note:** All classes (operators, menus, panels, AddonPreferences) must be imported and registered in `__init__.py`. `AddonPreferences.bl_idname` must equal `__package__`. PropertyGroups must be registered before classes that reference them. Unregister in reverse order.

---

## Execution Order Summary

| Phase | Deliverable | Primary Risk | Lines (est.) |
|---|---|---|---|
| 1 | Window + draw + modal proof-of-concept | Window creation timing, event routing | ~250 |
| 2 | Full keyboard rendering + modifier toggles | Batch performance, resize handling | ~500 |
| 3 | Keymap data extraction + color-coded display | Data completeness, filter UX | ~600 |
| 4 | Hit testing + selection + binding list panel | Scroll clipping, hit test accuracy | ~700 |
| 5 | Context menu + rebind + conflict resolution | Modal↔menu interaction, state transitions | ~650 |
| 6 | Export in Blender-native format | Format matching, file path handling | ~300 |
| 7 | Search, color scheme, visual polish | Text input widget, performance | ~500 |
| **Total** | | | **~3500** |

Each phase has a defined checkpoint. Do not proceed to the next phase until the current checkpoint passes. Phase 1 is the critical gate — if it fails, the architecture must be reconsidered before continuing.
