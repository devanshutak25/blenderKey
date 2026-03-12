"""
Keymap Visualizer – Preset management (save/load/delete named keymap profiles)
"""

import bpy
import os
import json
import time
from . import state
from .export import _generate_keyconfig_data


def _get_presets_dir():
    """Return absolute path to presets directory, creating it if needed."""
    try:
        prefs = bpy.context.preferences.addons["keymap_visualizer"].preferences
        raw = prefs.presets_directory
    except Exception:
        raw = "//keymap_presets/"
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
        pass
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
        return False, f"Failed to save preset: {e}"


def _load_preset(name):
    """Read a JSON preset and apply keyconfig data to user keymaps."""
    presets_dir = _get_presets_dir()
    filepath = os.path.join(presets_dir, f"{name}.json")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            preset = json.load(f)
    except Exception as e:
        return False, f"Failed to load preset: {e}"

    keyconfig_data = preset.get("keyconfig_data", [])
    if not keyconfig_data:
        return False, "Preset contains no keyconfig data"

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return False, "No user keyconfig available"

    # Apply keyconfig data
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
                        pass
                    break

    state._invalidate_cache()
    state._active_preset_name = name
    return True, f"Loaded preset '{name}' ({applied} bindings applied)"


def _delete_preset(name):
    """Remove a preset file."""
    presets_dir = _get_presets_dir()
    filepath = os.path.join(presets_dir, f"{name}.json")
    try:
        os.remove(filepath)
        return True, f"Deleted preset '{name}'"
    except Exception as e:
        return False, f"Failed to delete preset: {e}"
