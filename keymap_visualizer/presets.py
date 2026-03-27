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
from .export import _generate_keyconfig_data


def _get_presets_dir():
    """Return absolute path to presets directory, creating it if needed."""
    try:
        prefs = state._get_prefs()
        raw = prefs.presets_directory
    except Exception:
        _log.debug("Could not read presets directory preference", exc_info=True)
        raw = os.path.join(os.path.dirname(__file__), "presets")
    abs_path = bpy.path.abspath(raw)
    if not abs_path or abs_path == raw:
        # Fallback to user config dir
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


def _apply_keyconfig_data(keyconfig_data):
    """Apply keyconfig_data list to user keymaps. Returns (success, applied_count_or_errmsg)."""
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return False, "No user keyconfig available"

    applied = 0
    for km_name, km_params, km_content in keyconfig_data:
        items = km_content.get("items", [])
        # Find matching user keymap
        km = kc.keymaps.get(km_name)
        if km is None:
            continue
        for idname, kmi_data, props in items:
            # Find matching KMI by idname
            for kmi in km.keymap_items:
                if kmi.idname == idname:
                    try:
                        if isinstance(kmi_data, dict):
                            for attr in ('type', 'value', 'ctrl', 'shift', 'alt', 'oskey'):
                                if attr in kmi_data:
                                    setattr(kmi, attr, kmi_data[attr])
                            applied += 1
                    except Exception:
                        _log.debug("Could not set KMI attribute %s", attr, exc_info=True)
                    break

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
