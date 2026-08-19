"""
Keymap Visualizer – Export functions
"""

import logging
import ast
import bpy
import os
from . import state

_log = logging.getLogger("keymap_visualizer.export")


# Modifier fields, in the order Blender's own exporter writes them. Each is an
# int, not a bool: -1 means "any state" (the tri-state shown as a dash in the UI).
_KMI_MODIFIER_ATTRS = ('shift', 'ctrl', 'alt', 'oskey', 'hyper')

# Everything that distinguishes one binding from another when comparing against
# the default keyconfig.
_KMI_COMPARE_ATTRS = (
    'type', 'value', 'any', 'shift', 'ctrl', 'alt', 'oskey', 'hyper',
    'key_modifier', 'direction', 'repeat', 'active',
)


def _kmi_to_properties_dict(kmi):
    """Extract every operator property of a KMI as a flat dict.

    Used for *comparison* (telling two bindings of one operator apart), not for
    export - see _kmi_properties_as_data for the serialized form.
    """
    props = {}
    try:
        if kmi.properties is not None:
            for prop_name in kmi.properties.bl_rna.properties.keys():
                if prop_name == 'rna_type':
                    continue
                try:
                    val = getattr(kmi.properties, prop_name)
                    # Convert non-serializable types
                    if hasattr(val, 'to_list'):
                        val = val.to_list()
                    elif hasattr(val, 'to_dict'):
                        val = val.to_dict()
                    props[prop_name] = val
                except Exception:
                    _log.debug("Could not serialize property %s", prop_name, exc_info=True)
    except Exception:
        _log.debug("Could not read KMI properties", exc_info=True)
    return props


def _kmi_properties_as_data(props):
    """Serialize operator properties as Blender's [(name, value), ...] list.

    Only explicitly-set properties are written, matching
    bl_keymap_utils.io._kmi_properties_to_lines. Nested OperatorProperties
    (pointer properties, as used by macros) recurse into a nested list under
    their own name.
    """
    if props is None:
        return None
    try:
        prop_names = props.bl_rna.properties.keys()
    except Exception:
        _log.debug("Could not read KMI properties", exc_info=True)
        return None

    out = []
    for prop_name in prop_names:
        if prop_name == 'rna_type':
            continue
        try:
            if not props.is_property_set(prop_name):
                continue
            val = getattr(props, prop_name)
        except Exception:
            _log.debug("Could not read property %s", prop_name, exc_info=True)
            continue

        if isinstance(val, bpy.types.OperatorProperties):
            nested = _kmi_properties_as_data(val)
            if nested:
                out.append((prop_name, nested))
            continue

        try:
            if hasattr(val, 'to_list'):
                val = val.to_list()
            elif hasattr(val, 'to_dict'):
                val = val.to_dict()
        except Exception:
            _log.debug("Could not serialize property %s", prop_name, exc_info=True)
            continue
        out.append((prop_name, val))
    return out


def _kmi_args_as_data(kmi):
    """Build the kmi_args dict Blender's importer passes to keymap_items.new().

    Mirrors bl_keymap_utils.io.kmi_args_as_data: defaulted fields are omitted so
    the file round-trips through Blender unchanged.
    """
    args = {"type": kmi.type, "value": kmi.value}

    if kmi.any:
        args["any"] = True
    else:
        for attr in _KMI_MODIFIER_ATTRS:
            mod = getattr(kmi, attr, 0)
            if mod:
                args[attr] = -1 if mod == -1 else True

    key_mod = getattr(kmi, 'key_modifier', 'NONE')
    if key_mod and key_mod != 'NONE':
        args["key_modifier"] = key_mod

    direction = getattr(kmi, 'direction', 'ANY')
    if direction and direction != 'ANY':
        args["direction"] = direction

    # Blender only accepts `repeat` for the map types that can repeat.
    if kmi.repeat and (
            (kmi.map_type == 'KEYBOARD' and kmi.value in {'PRESS', 'ANY'}) or
            kmi.map_type == 'TEXTINPUT'):
        args["repeat"] = True

    return args


def _kmi_data_or_none(kmi):
    """Third element of an exported item: {"properties": [...], "active": False} or None."""
    data = {}
    props = _kmi_properties_as_data(kmi.properties)
    if props:
        data["properties"] = props
    if kmi.active is False:
        data["active"] = False
    return data or None


def _kmi_identity(kmi, is_modal):
    """The id an item is stored under: propvalue for modal keymaps, else idname."""
    return kmi.propvalue if is_modal else kmi.idname


def _kmi_is_modified(kmi, km_name):
    """Compare user KMI against default to detect modifications."""
    wm = bpy.context.window_manager
    kc_default = wm.keyconfigs.default
    if kc_default is None:
        return True  # Can't compare, assume modified

    km_default = kc_default.keymaps.get(km_name)
    if km_default is None:
        return True  # Not in defaults at all, consider modified

    is_modal = km_default.is_modal
    ident = _kmi_identity(kmi, is_modal)
    for default_kmi in km_default.keymap_items:
        if _kmi_identity(default_kmi, is_modal) != ident:
            continue
        for attr in _KMI_COMPARE_ATTRS:
            if getattr(kmi, attr, None) != getattr(default_kmi, attr, None):
                return True
        return False
    return True  # Not found in default, consider modified


def _generate_keyconfig_data(scope='MODIFIED'):
    """Generate Blender-compatible keyconfig_data list.

    scope:
      'MODIFIED'         only the individual bindings that differ from defaults.
                         Produces partial keymaps - readable as a diff, but not
                         safe to activate as a keyconfig.
      'MODIFIED_KEYMAPS' every binding of every keymap the user has touched.
                         What Blender's own exporter writes; activatable.
      'ALL'              everything.
    """
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return []

    keyconfig_data = []
    for km in kc.keymaps:
        if scope == 'MODIFIED_KEYMAPS' and not km.is_user_modified:
            continue

        is_modal = km.is_modal
        items = []
        for kmi in km.keymap_items:
            if scope == 'MODIFIED' and not _kmi_is_modified(kmi, km.name):
                continue
            kmi_id = _kmi_identity(kmi, is_modal)
            if not kmi_id:
                continue  # nothing to key the item on
            items.append((kmi_id, _kmi_args_as_data(kmi), _kmi_data_or_none(kmi)))

        if items:
            km_params = {
                "space_type": km.space_type,
                "region_type": km.region_type,
            }
            if is_modal:
                km_params["modal"] = True
            keyconfig_data.append((km.name, km_params, {"items": items}))

    return keyconfig_data


def _write_export_file(filepath, keyconfig_data):
    """Write a Python script with keyconfig_import_from_data call."""
    abs_path = bpy.path.abspath(filepath)
    dir_path = os.path.dirname(abs_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write("# Keymap export generated by Keymap Visualizer addon\n")
        f.write("keyconfig_version = {!r}\n".format(tuple(bpy.app.version_file)))
        f.write("keyconfig_data = \\\n")
        f.write(repr(keyconfig_data))
        f.write("\n\n")
        f.write('if __name__ == "__main__":\n')
        f.write('    import os\n')
        f.write('    from bl_keymap_utils.io import keyconfig_import_from_data\n')
        f.write('    keyconfig_import_from_data(\n')
        f.write('        os.path.splitext(os.path.basename(__file__))[0],\n')
        f.write('        keyconfig_data,\n')
        f.write('        keyconfig_version=keyconfig_version,\n')
        f.write('    )\n')

    return abs_path


def _do_export():
    """Run the export using addon preferences settings. Returns (success, message)."""
    try:
        prefs = state._get_prefs()
        filepath = prefs.export_path
        scope = prefs.export_scope
    except Exception:
        _log.debug("Could not read export preferences, using defaults", exc_info=True)
        filepath = ""
        scope = 'MODIFIED'

    if not filepath:
        filepath = os.path.join(
            bpy.utils.user_resource('CONFIG'), "keymap_exports", "custom_keymap.py"
        )

    try:
        data = _generate_keyconfig_data(scope)
        if not data:
            return (False, "No keybindings to export")
        abs_path = _write_export_file(filepath, data)
        return (True, f"Exported to {abs_path}")
    except Exception as e:
        _log.warning("Export failed", exc_info=True)
        return (False, f"Export failed: {e}")


def _do_import():
    """Import a keyconfig Python file exported by this addon. Returns (success, message)."""
    try:
        prefs = state._get_prefs()
        filepath = prefs.import_path
    except Exception:
        _log.debug("Could not read import preferences", exc_info=True)
        return (False, "Import path not set in addon preferences")

    if not filepath:
        return (False, "Import path is empty")

    abs_path = bpy.path.abspath(filepath)
    if not os.path.isfile(abs_path):
        return (False, f"File not found: {abs_path}")

    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        _log.warning("Could not read import file", exc_info=True)
        return (False, f"Could not read file: {e}")

    # Parse keyconfig_data from the file. Parsing the module and picking the
    # actual assignment beats scanning text: it is immune to formatting, and to
    # the word "keyconfig_data" appearing earlier in a comment or the header.
    keyconfig_data = None
    try:
        tree = ast.parse(content)
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(t, ast.Name) and t.id == "keyconfig_data"
                       for t in node.targets):
                continue
            keyconfig_data = ast.literal_eval(node.value)
            break
    except (ValueError, SyntaxError) as e:
        _log.warning("Failed to parse keyconfig_data from file", exc_info=True)
        return (False, f"Failed to parse keyconfig_data: {e}")

    if keyconfig_data is None:
        return (False, "No keyconfig_data found in file")

    if not isinstance(keyconfig_data, list) or not keyconfig_data:
        return (False, "keyconfig_data is empty or invalid")

    # Apply using shared logic from presets (which pushes undo itself)
    from .presets import _apply_keyconfig_data
    success, result = _apply_keyconfig_data(keyconfig_data)
    if not success:
        return (False, result)

    return (True, f"Imported {result} bindings from {os.path.basename(abs_path)}")
