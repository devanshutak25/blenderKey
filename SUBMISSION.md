# Blender Extensions Platform — Submission Fields

Everything you need to paste into https://extensions.blender.org when submitting. Copy each field verbatim.

---

## Core fields

### Name
```
Keymap Visualizer
```

### Tagline
*(≤64 chars, no trailing punctuation)*
```
Visual keyboard-based keymap editor
```

### Short description
*(≤512 chars, one paragraph — shown in search results and cards)*

```
See every Blender shortcut on a full-size interactive keyboard. Hover a key to preview its bindings, right-click to rebind, press a shortcut to find which key owns it. Search operators by name, filter by editor or mode, compare your keymap against Blender defaults, and save your whole setup as a preset. 50-level undo, JSON presets, exportable .py keyconfigs. Seven keyboard layouts including auto-detect, six form factors from full-size to 60%, and a GPU-rendered UI with full theming.
```

### Long description / body
*(markdown, shown on the extension's page)*

```markdown
## What it does

Blender's shortcut system is powerful, but the built-in keymap editor makes you dig through nested menus to find anything. Keymap Visualizer shows you the whole keyboard on one screen: every shortcut on every key, color-coded, searchable, rebindable with a right-click.

- **Hover** a key — the info panel shows what's bound to it
- **Left-click** — lock the info panel to that key
- **Right-click** — rebind, unbind, reset to default, or toggle a binding on/off
- **Press `?`** then any shortcut — the visualizer jumps to the key that owns it
- **Press `/`** — search operators by name; matching keys stay bright, others dim
- **Press `D`** — compare against Blender defaults (green = modified, red = deactivated)
- **Press `Ctrl+Z`** — undo (up to 50 levels)

## Features

**Visual keyboard**

- GPU-rendered with drop shadows and smooth hover animations
- 6 sizes: 100% full, 96% compact, 80% TKL, 75%, 65%, 60%
- 2 physical layouts: ANSI or ISO
- 7 logical layouts: auto-detect, QWERTY, AZERTY, QWERTZ, Dvorak, Colemak, Nordic
- Resizable 0.5×–3×
- All sections: alphanumeric, numpad, function row, navigation cluster, and mouse buttons

**Rebinding**

- Right-click any key to list its bindings, pick one, press a new combo
- Capture mode dims everything except the target key and prompts for a combo
- Conflict resolution with Swap / Override / Cancel options
- Undo up to 50 levels

**Search**

- Operator search by name (`/` or `Ctrl+F`) with fuzzy matching
- Reverse shortcut lookup (`?`) — press a combo to find the key
- Operator browser on the left with 13 categories and a blue dot indicator for bound operators

**Filters**

- Editor filter (3D View, UV, Node, Text, Sequencer, Clip, Dopesheet, Graph, NLA, Properties, Outliner, Console, Spreadsheet, Global)
- Mode filter (Object, Edit Mesh, Sculpt, Pose, Weight Paint, Vertex Paint, Texture Paint, Grease Pencil, Curves)
- Multi-select, any combination

**Presets, import, export**

- Save whole keyconfig as a JSON preset. Load, delete, copy to clipboard, paste from clipboard.
- Export to Blender-importable `.py` keyconfig — modified-only or full dump
- Import previously exported `.py` files (safe parsing, no code execution)

**Diff view**

- Press `D` to see what you've changed from defaults
- Green = modified, Red = deactivated, Dim = untouched

**Theming**

- 8 base color tokens drive all derived colors
- 13 individually configurable category colors
- 29 advanced per-element color overrides (collapsed by default)
- WCAG-aware adaptive text contrast

**Accessibility**

- Full keyboard-only navigation (Tab to cycle focus, arrows to move, Enter to select)
- Focus ring on the currently selected key

## Requires

Blender 5.1 or newer.

## How to open

**Edit → Keymap Viz** in the top menu bar. A new window opens with the keyboard overlay.

## Notes for reviewers

- Uses `subprocess` once in `keyboards.py` to auto-detect the OS keyboard layout on macOS (`defaults read`) and Linux (`setxkbmap -query`). Falls back to QWERTY silently on any failure. Users can override the detection in preferences.
- Declares `files` permission — used for export (.py keyconfig), preset save/load (JSON), and optional custom font TTF paths chosen by the user.
- No network access. No subprocess calls on Windows (uses `winreg` instead).
- Bundled font: Roboto Condensed (Apache-2.0, © Google). License included at `fonts/LICENSE.txt`.
```

---

## Metadata fields

| Field | Value |
|-------|-------|
| **Category** | User Interface |
| **Secondary tag** | System |
| **License** | GPL-3.0-or-later *(required by platform — Blender is GPL)* |
| **Bundled license** | Apache-2.0 (Roboto Condensed font) |
| **Blender version min** | 5.1.0 |
| **Blender version max** | *(leave empty)* |
| **Website** | https://github.com/devanshutak25/blenderKey |
| **Source code** | https://github.com/devanshutak25/blenderKey |
| **Issue tracker** | https://github.com/devanshutak25/blenderKey/issues |
| **Maintainer** | Devanshu Tak |
| **Maintainer email** | charutak.davc@gmail.com |

---

## Version history

### 1.0.0 — first release

First public release.

---

## Permission justifications

When the platform asks why the extension needs each permission:

**`files`** — Users can export their keymap to a `.py` script, import previously exported `.py` scripts, and save/load presets as JSON. All file paths are user-configured in preferences. The addon never writes outside directories the user has explicitly chosen.

---

## Media checklist (prepare before submitting)

| Asset | Spec | Status |
|-------|------|--------|
| **Cover image** | 1920×1080, PNG/JPG, ≤2 MB — hero shot, full keyboard with color coding visible | [ ] |
| **Icon** | 256×256, PNG with transparent bg — recognizable at 64×64 | [ ] |
| **Screenshot 1** — Overview | 1920×1080 — full keyboard, category colors on, info panel visible | [ ] |
| **Screenshot 2** — Rebind flow | 1920×1080 — right-click context menu + flyout on a key | [ ] |
| **Screenshot 3** — Search | 1920×1080 — `/` search active, non-matches dimmed, or `?` reverse-lookup | [ ] |
| **Screenshot 4** — Diff view | 1920×1080 — `D` pressed, green/red keys visible | [ ] |
| **Screenshot 5 (optional)** — Preferences | 1920×1080 — theming, category colors, advanced overrides | [ ] |
| **Video** | YouTube (unlisted ok), 1080p+, 30s–2min. `Keymap.mp4` works as-is | [ ] |

---

## Pre-submission checklist

- [x] Manifest validates (`blender --command extension validate keymap_visualizer-1.0.0.zip`)
- [x] Tested install from zip in clean Blender 5.1
- [x] LICENSE bundled inside addon folder
- [x] Font license bundled at `fonts/LICENSE.txt`
- [x] Print statements converted to logger (except opt-in profiler report)
- [x] `bl_info` absent (using manifest only — correct for 4.2+ extensions)
- [x] No network calls
- [x] Version warning on older Blender
- [x] Min Blender version bumped to 5.1.0
- [x] README humanized
- [x] Preference labels/descriptions humanized
- [x] SUBMISSION.md drafted with all field values
- [x] v1.0.0 committed and tagged locally
- [ ] v1.0.0 tag pushed to GitHub (`git push origin master --tags`)
- [ ] GitHub Release created with zip attached
- [ ] Cover image + icon prepared
- [ ] Screenshots (2–4) prepared
- [ ] Video uploaded to YouTube, URL saved

---

## Submission URL

https://extensions.blender.org/add-ons/submit/
