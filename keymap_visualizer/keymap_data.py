"""
Keymap Visualizer – Keymap query, conflict detection, rebinding, search filter
"""

import bpy
import time
from . import state


def _get_bindings_for_key(event_type, modifiers):
    """Return list of (keymap_name, operator_idname, modifier_string, kmi, is_active)."""
    mod_tuple = (modifiers['ctrl'], modifiers['shift'], modifiers['alt'], modifiers['oskey'])
    cache_key = (event_type, mod_tuple)
    if state._bindings_key == cache_key:
        return state._cached_bindings

    results = []
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        state._cached_bindings = results
        state._bindings_key = cache_key
        return results

    any_mod_active = any(mod_tuple)

    for km in kc.keymaps:
        for kmi in km.keymap_items:
            if kmi.type != event_type:
                continue
            # Filter by modifiers if any toggle is active
            if any_mod_active:
                if kmi.ctrl != modifiers['ctrl']:
                    continue
                if kmi.shift != modifiers['shift']:
                    continue
                if kmi.alt != modifiers['alt']:
                    continue
                if kmi.oskey != modifiers['oskey']:
                    continue

            # Build modifier string
            mod_parts = []
            if kmi.ctrl:
                mod_parts.append("Ctrl")
            if kmi.shift:
                mod_parts.append("Shift")
            if kmi.alt:
                mod_parts.append("Alt")
            if kmi.oskey:
                mod_parts.append("OS")
            mod_str = "+".join(mod_parts) if mod_parts else ""

            results.append((km.name, kmi.idname, mod_str, kmi, kmi.active))
            if len(results) >= 20:
                break
        if len(results) >= 20:
            break

    state._cached_bindings = results
    state._bindings_key = cache_key
    return results


def _find_conflicts(event_type, ctrl, shift, alt, oskey, exclude_kmi=None):
    """Find active KMIs matching key+modifiers. Returns list of (km_name, kmi)."""
    conflicts = []
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return conflicts

    for km in kc.keymaps:
        for kmi in km.keymap_items:
            if not kmi.active:
                continue
            if kmi is exclude_kmi:
                continue
            if kmi.type == event_type and kmi.ctrl == ctrl and kmi.shift == shift \
                    and kmi.alt == alt and kmi.oskey == oskey:
                conflicts.append((km.name, kmi))
                if len(conflicts) >= 10:
                    return conflicts
    return conflicts


def _apply_rebind(kmi, new_type, new_ctrl, new_shift, new_alt, new_oskey):
    """Set kmi key type and modifiers. Preserves kmi.value (PRESS/RELEASE/CLICK etc.)."""
    kmi.type = new_type
    kmi.ctrl = new_ctrl
    kmi.shift = new_shift
    kmi.alt = new_alt
    kmi.oskey = new_oskey
    state._invalidate_cache()


def _reset_kmi_to_default(kmi, km_name):
    """Find matching KMI in wm.keyconfigs.default by idname, copy type/value/modifiers back."""
    wm = bpy.context.window_manager
    kc_default = wm.keyconfigs.default
    if kc_default is None:
        return False

    for km in kc_default.keymaps:
        if km.name != km_name:
            continue
        for default_kmi in km.keymap_items:
            if default_kmi.idname == kmi.idname:
                kmi.type = default_kmi.type
                kmi.value = default_kmi.value
                kmi.ctrl = default_kmi.ctrl
                kmi.shift = default_kmi.shift
                kmi.alt = default_kmi.alt
                kmi.oskey = default_kmi.oskey
                kmi.active = True
                state._invalidate_cache()
                return True
    return False


def _update_search_filter():
    """Update state._search_matching_keys based on state._search_text."""
    state._search_matching_keys = set()

    if not state._search_text:
        state._batch_dirty = True
        return

    query = state._search_text.lower()
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        state._batch_dirty = True
        return

    for km in kc.keymaps:
        for kmi in km.keymap_items:
            if not kmi.active:
                continue
            if query in kmi.idname.lower() or query in kmi.name.lower():
                state._search_matching_keys.add(kmi.type)

    state._batch_dirty = True
