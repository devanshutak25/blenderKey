"""
Keymap Visualizer – Keymap query, conflict detection, rebinding, search filter
"""

import bpy
import time
from . import state
from .constants import OPERATOR_ABBREVIATIONS, OPERATOR_CATEGORIES


def _km_passes_filter(km):
    """Check if a keymap passes the current editor/mode filters."""
    if state._filter_space_type != 'ALL':
        if km.space_type != state._filter_space_type and km.space_type != 'EMPTY':
            return False
    if state._filter_mode != 'ALL':
        if state._filter_mode not in km.name:
            return False
    return True


def _get_bindings_for_key(event_type, modifiers):
    """Return list of (keymap_name, operator_idname, modifier_string, kmi, is_active)."""
    effective = state._get_effective_modifiers()
    mod_tuple = (effective['ctrl'], effective['shift'], effective['alt'], effective['oskey'])
    cache_key = (event_type, mod_tuple, state._filter_space_type, state._filter_mode,
                 state._modifier_source)
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
        if not _km_passes_filter(km):
            continue
        for kmi in km.keymap_items:
            if kmi.type != event_type:
                continue
            # Filter by modifiers if any toggle is active
            if any_mod_active:
                if kmi.ctrl != effective['ctrl']:
                    continue
                if kmi.shift != effective['shift']:
                    continue
                if kmi.alt != effective['alt']:
                    continue
                if kmi.oskey != effective['oskey']:
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


def _compute_bound_keys():
    """Compute the set of event_type strings that have active bindings (respects filters)."""
    if not state._bound_keys_dirty:
        return
    state._bound_keys_cache = set()
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        state._bound_keys_dirty = False
        return
    effective = state._get_effective_modifiers()
    any_mod_active = any(effective.values())
    for km in kc.keymaps:
        if not _km_passes_filter(km):
            continue
        for kmi in km.keymap_items:
            if kmi.active:
                if any_mod_active:
                    if (kmi.ctrl != effective['ctrl'] or kmi.shift != effective['shift'] or
                            kmi.alt != effective['alt'] or kmi.oskey != effective['oskey']):
                        continue
                state._bound_keys_cache.add(kmi.type)
    state._bound_keys_dirty = False


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
        if not _km_passes_filter(km):
            continue
        for kmi in km.keymap_items:
            if not kmi.active:
                continue
            if query in kmi.idname.lower() or query in kmi.name.lower():
                state._search_matching_keys.add(kmi.type)

    state._batch_dirty = True


# ---------------------------------------------------------------------------
# v0.9 Feature 1: On-key command labels
# ---------------------------------------------------------------------------
def _get_operator_abbreviation(idname):
    """Get abbreviated name for an operator idname."""
    if idname in OPERATOR_ABBREVIATIONS:
        return OPERATOR_ABBREVIATIONS[idname]
    # Fallback: last segment, replace _ with space, title-case, truncate
    parts = idname.split('.')
    name = parts[-1] if parts else idname
    name = name.replace('_', ' ').title()
    if len(name) > 12:
        name = name[:12]
    return name


def _compute_key_labels():
    """Compute command labels for each key based on current modifiers and filters."""
    if not state._key_labels_dirty:
        return
    state._key_labels_cache = {}
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        state._key_labels_dirty = False
        return

    effective = state._get_effective_modifiers()
    any_mod_active = any(effective.values())

    for km in kc.keymaps:
        if not _km_passes_filter(km):
            continue
        for kmi in km.keymap_items:
            if not kmi.active:
                continue
            if any_mod_active:
                if (kmi.ctrl != effective['ctrl'] or kmi.shift != effective['shift'] or
                        kmi.alt != effective['alt'] or kmi.oskey != effective['oskey']):
                    continue
            # Only store first (highest priority) binding per key
            if kmi.type not in state._key_labels_cache:
                state._key_labels_cache[kmi.type] = _get_operator_abbreviation(kmi.idname)

    state._key_labels_dirty = False


# ---------------------------------------------------------------------------
# v0.9 Feature 3: Category color-coding
# ---------------------------------------------------------------------------
def _get_operator_category(idname):
    """Get category for an operator using longest-prefix match."""
    best_match = None
    best_len = 0
    for prefix, category in OPERATOR_CATEGORIES.items():
        if idname.startswith(prefix) and len(prefix) > best_len:
            best_match = category
            best_len = len(prefix)
    return best_match


def _compute_key_categories():
    """Compute category for each key based on primary binding."""
    if not state._key_categories_dirty:
        return
    state._key_categories_cache = {}
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        state._key_categories_dirty = False
        return

    effective = state._get_effective_modifiers()
    any_mod_active = any(effective.values())

    for km in kc.keymaps:
        if not _km_passes_filter(km):
            continue
        for kmi in km.keymap_items:
            if not kmi.active:
                continue
            if any_mod_active:
                if (kmi.ctrl != effective['ctrl'] or kmi.shift != effective['shift'] or
                        kmi.alt != effective['alt'] or kmi.oskey != effective['oskey']):
                    continue
            if kmi.type not in state._key_categories_cache:
                cat = _get_operator_category(kmi.idname)
                if cat:
                    state._key_categories_cache[kmi.type] = cat

    state._key_categories_dirty = False


# ---------------------------------------------------------------------------
# v0.9 Feature 4: Undo/redo for keymap changes
# ---------------------------------------------------------------------------
def _snapshot_kmi(kmi):
    """Capture current state of a KMI."""
    return {
        'type': kmi.type, 'value': kmi.value,
        'ctrl': kmi.ctrl, 'shift': kmi.shift,
        'alt': kmi.alt, 'oskey': kmi.oskey,
        'active': kmi.active,
    }


def _restore_kmi(kmi, snapshot):
    """Restore a KMI from a snapshot."""
    for attr, val in snapshot.items():
        setattr(kmi, attr, val)
    state._invalidate_cache()


def _push_undo(affected_kmis):
    """Push an undo entry BEFORE mutating KMIs. affected_kmis = list of kmi refs."""
    entry = [{'kmi': kmi, 'before': _snapshot_kmi(kmi)} for kmi in affected_kmis]
    state._undo_stack.append(entry)
    if len(state._undo_stack) > state._undo_max:
        state._undo_stack.pop(0)
    state._redo_stack.clear()


def _do_undo():
    """Undo the last keymap change. Returns True if successful."""
    if not state._undo_stack:
        return False
    entry = state._undo_stack.pop()
    redo_entry = []
    for item in entry:
        try:
            redo_entry.append({'kmi': item['kmi'], 'before': _snapshot_kmi(item['kmi'])})
            _restore_kmi(item['kmi'], item['before'])
        except ReferenceError:
            pass
    state._redo_stack.append(redo_entry)
    return True


def _do_redo():
    """Redo the last undone keymap change. Returns True if successful."""
    if not state._redo_stack:
        return False
    entry = state._redo_stack.pop()
    undo_entry = []
    for item in entry:
        try:
            undo_entry.append({'kmi': item['kmi'], 'before': _snapshot_kmi(item['kmi'])})
            _restore_kmi(item['kmi'], item['before'])
        except ReferenceError:
            pass
    state._undo_stack.append(undo_entry)
    return True
