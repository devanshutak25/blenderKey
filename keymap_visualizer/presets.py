"""
Keymap Visualizer – Preset management (save/load/delete named keymap profiles)
"""

import logging
import bpy
import os
import json
import time
from . import state

_log = logging.getLogger("keymap_visualizer.presets")
from .export import (_generate_keyconfig_data, _kmi_to_properties_dict,
                     _kmi_identity)

# KMI fields a stored binding may set when applied to a user keymap, with the
# value to use when the stored binding omits them. Blender's format omits
# defaulted fields, so an absent key means "reset to default", not "leave alone".
_KMI_APPLY_DEFAULTS = (
    ('shift', False),
    ('ctrl', False),
    ('alt', False),
    ('oskey', False),
    ('hyper', False),
    ('key_modifier', 'NONE'),
    ('direction', 'ANY'),
    ('repeat', False),
)


def _get_presets_dir():
    """Return absolute path to presets directory, creating it if needed.

    When the user has not set a preset directory preference, fall back to
    Blender's user config folder (never the addon's install directory —
    modifying the addon directory is disallowed by the extensions platform).
    """
    raw = ""
    try:
        prefs = state._get_prefs()
        raw = prefs.presets_directory or ""
    except Exception:
        _log.debug("Could not read presets directory preference", exc_info=True)
    abs_path = bpy.path.abspath(raw) if raw else ""
    if not abs_path:
        abs_path = os.path.join(bpy.utils.user_resource('CONFIG'), "keymap_presets")
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def _list_presets():
    """Scan presets dir, return list of preset names."""
    presets_dir = _get_presets_dir()
    names = []
    try:
        for f in sorted(os.listdir(presets_dir)):
            if f.endswith('.json'):
                names.append(os.path.splitext(f)[0])
    except Exception:
        _log.debug("Could not list presets directory", exc_info=True)
    return names


def _save_preset(name):
    """Serialize current user keyconfig to a JSON preset file."""
    presets_dir = _get_presets_dir()
    filepath = os.path.join(presets_dir, f"{name}.json")

    keyconfig_data = _generate_keyconfig_data('ALL')
    preset = {
        "name": name,
        "version": 1,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "keyconfig_data": keyconfig_data,
    }

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(preset, f, indent=2, default=str)
        return True, f"Saved preset '{name}'"
    except Exception as e:
        _log.warning("Failed to save preset '%s'", name, exc_info=True)
        return False, f"Failed to save preset: {e}"


def _load_preset(name):
    """Read a JSON preset and apply keyconfig data to user keymaps."""
    presets_dir = _get_presets_dir()
    filepath = os.path.join(presets_dir, f"{name}.json")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            preset = json.load(f)
    except Exception as e:
        _log.warning("Failed to load preset '%s'", name, exc_info=True)
        return False, f"Failed to load preset: {e}"

    keyconfig_data = preset.get("keyconfig_data", [])
    if not keyconfig_data:
        return False, "Preset contains no keyconfig data"

    success, applied = _apply_keyconfig_data(keyconfig_data)
    if not success:
        return False, applied  # applied is the error message in this case

    state._active_preset_name = name
    return True, f"Loaded preset '{name}' ({applied} bindings applied)"


def _stored_props_as_dict(props):
    """Normalise stored operator properties to a plain dict.

    Accepts the [(name, value), ...] list Blender's keyconfig files use and the
    flat {name: value} dict this addon wrote before 1.0.2.
    """
    if isinstance(props, dict):
        return props
    if isinstance(props, (list, tuple)):
        out = {}
        for pair in props:
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                out[pair[0]] = pair[1]
        return out
    return {}


def _stored_item_extras(extras):
    """Split a stored item's third element into (properties dict, active flag).

    Blender's shape is {"properties": [(name, value), ...], "active": False} or
    None. Files written by this addon before 1.0.2 put a flat property dict
    there instead, so both are accepted; `active` is None when unspecified.
    """
    if extras is None:
        return {}, None
    if isinstance(extras, dict):
        keys = set(extras.keys())
        if keys and keys <= {"properties", "active"}:
            return _stored_props_as_dict(extras.get("properties")), extras.get("active")
        return dict(extras), None
    return _stored_props_as_dict(extras), None


def _iter_apply_fields(kmi_args):
    """Yield (attr, value) pairs to write onto a KMI for one stored binding.

    `type` and `value` are always present. `any` is written before the
    individual modifiers, and suppresses them when set, because Blender derives
    the modifier fields from it.
    """
    for attr in ('type', 'value'):
        if attr in kmi_args:
            yield attr, kmi_args[attr]

    if kmi_args.get('any'):
        yield 'any', True
        skip_modifiers = True
    else:
        yield 'any', False
        skip_modifiers = False

    for attr, default in _KMI_APPLY_DEFAULTS:
        if skip_modifiers and attr in ('shift', 'ctrl', 'alt', 'oskey', 'hyper'):
            continue
        yield attr, kmi_args.get(attr, default)


def _kmi_props_match_score(kmi, stored_props):
    """Count how many of the stored property values this KMI already carries.

    Used to tell apart several bindings of the same operator within one keymap
    (e.g. the three `mesh.select_mode` items, which differ only by `type`).
    """
    if not stored_props:
        return 0
    live = _kmi_to_properties_dict(kmi)
    score = 0
    for name, val in stored_props.items():
        try:
            if name in live and live[name] == val:
                score += 1
        except Exception:
            _log.debug("Could not compare property %s", name, exc_info=True)
    return score


def _apply_keyconfig_data(keyconfig_data):
    """Apply keyconfig_data list to user keymaps. Returns (success, applied_count_or_errmsg)."""
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return False, "No user keyconfig available"

    # Pass 1: resolve every KMI we intend to mutate, without mutating anything.
    targets = []
    for km_name, km_params, km_content in keyconfig_data:
        items = km_content.get("items", [])
        # Find matching user keymap
        km = kc.keymaps.get(km_name)
        if km is None:
            continue
        # Modal keymaps key their items on propvalue; everything else on idname.
        is_modal = km.is_modal
        if not is_modal and isinstance(km_params, dict):
            is_modal = bool(km_params.get("modal"))
        # Pool this keymap's items by that id. Each KMI is consumed by at most
        # one stored binding, so N stored bindings of an operator apply to N
        # items instead of all landing on the first one.
        by_id = {}
        for kmi in km.keymap_items:
            by_id.setdefault(_kmi_identity(kmi, is_modal), []).append(kmi)
        for kmi_id, kmi_args, extras in items:
            if not isinstance(kmi_args, dict):
                continue
            pool = by_id.get(kmi_id)
            if not pool:
                continue
            stored_props, stored_active = _stored_item_extras(extras)
            if len(pool) == 1:
                kmi = pool.pop(0)
            else:
                # Several bindings of this operator here: pick the one whose
                # properties best match what was stored.
                best_i, best_score = 0, -1
                for i, candidate in enumerate(pool):
                    score = _kmi_props_match_score(candidate, stored_props)
                    if score > best_score:
                        best_i, best_score = i, score
                kmi = pool.pop(best_i)
            targets.append((km_name, kmi, kmi_args, stored_active))

    if not targets:
        state._invalidate_cache()
        return True, 0

    # Snapshot exactly what is about to change, before any of it changes.
    # This is the single mutation point for preset load, clipboard paste and
    # file import, so every one of those paths becomes undoable here.
    from .keymap_data import _push_undo
    _push_undo([t[1] for t in targets])

    # Pass 2: apply. Each field is set independently so one rejected value
    # cannot leave a binding half-written.
    applied = 0
    for km_name, kmi, kmi_args, stored_active in targets:
        ok = False
        for attr, value in _iter_apply_fields(kmi_args):
            try:
                setattr(kmi, attr, value)
                ok = True
            except Exception:
                _log.debug("Could not set %s on KMI '%s' in keymap '%s'",
                           attr, kmi.idname, km_name, exc_info=True)
        if stored_active is not None:
            try:
                kmi.active = bool(stored_active)
            except Exception:
                _log.debug("Could not set active on KMI '%s' in keymap '%s'",
                           kmi.idname, km_name, exc_info=True)
        if ok:
            applied += 1

    state._invalidate_cache()
    return True, applied


def _copy_preset_to_clipboard(name):
    """Copy a named preset's JSON to the system clipboard. Returns (success, message)."""
    presets_dir = _get_presets_dir()
    filepath = os.path.join(presets_dir, f"{name}.json")
    try:
        with open(filepath, 'r') as f:
            json_str = f.read()
        bpy.context.window_manager.clipboard = json_str
        return True, f"Preset '{name}' copied to clipboard"
    except Exception as e:
        _log.warning("Failed to copy preset to clipboard", exc_info=True)
        return False, f"Failed to copy: {e}"


def _paste_preset_from_clipboard():
    """Paste a preset from clipboard JSON. Returns (success, message)."""
    try:
        json_str = bpy.context.window_manager.clipboard
        if not json_str or len(json_str) > 1_000_000:
            return False, "Clipboard empty or too large"
        data = json.loads(json_str)
        if 'keyconfig_data' not in data:
            return False, "Invalid preset format (missing keyconfig_data)"
        name = data.get('name', 'Pasted Preset')
        # Save to file
        presets_dir = _get_presets_dir()
        # Avoid name collisions
        base_name = name
        counter = 1
        while os.path.exists(os.path.join(presets_dir, f"{name}.json")):
            name = f"{base_name} ({counter})"
            counter += 1
        filepath = os.path.join(presets_dir, f"{name}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        # Apply the preset
        success, msg = _load_preset(name)
        if success:
            return True, f"Preset '{name}' pasted and applied"
        return True, f"Preset '{name}' saved but could not apply: {msg}"
    except json.JSONDecodeError:
        return False, "Clipboard does not contain valid JSON"
    except Exception as e:
        _log.warning("Failed to paste preset from clipboard", exc_info=True)
        return False, f"Paste failed: {e}"


def _delete_preset(name):
    """Remove a preset file."""
    presets_dir = _get_presets_dir()
    filepath = os.path.join(presets_dir, f"{name}.json")
    try:
        os.remove(filepath)
        return True, f"Deleted preset '{name}'"
    except Exception as e:
        _log.warning("Failed to delete preset '%s'", name, exc_info=True)
        return False, f"Failed to delete preset: {e}"
