"""
Keymap Visualizer – Keymap query, conflict detection, rebinding, search filter
"""

import bpy
from . import state
from .constants import OPERATOR_ABBREVIATIONS, OPERATOR_CATEGORIES, OPERATOR_CATEGORY_ORDER, OPERATOR_CATEGORY_KEYMAPS


def _kmi_matches_modifiers(kmi, effective):
    """Check if a KMI's modifier flags match the effective modifiers."""
    return (kmi.ctrl == effective['ctrl'] and kmi.shift == effective['shift'] and
            kmi.alt == effective['alt'] and kmi.oskey == effective['oskey'])


def _build_mod_string(kmi):
    """Build a human-readable modifier string like 'Ctrl+Shift' from a KMI."""
    mod_parts = []
    if kmi.ctrl:
        mod_parts.append("Ctrl")
    if kmi.shift:
        mod_parts.append("Shift")
    if kmi.alt:
        mod_parts.append("Alt")
    if kmi.oskey:
        mod_parts.append("OS")
    return "+".join(mod_parts) if mod_parts else ""


def _iter_filtered_kmis(check_active=True, check_modifiers=True, effective=None):
    """Yield (km, kmi) pairs from user keyconfig, applying filter/active/modifier checks."""
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return
    if check_modifiers and effective is None:
        effective = state._get_effective_modifiers()
    for km in kc.keymaps:
        if not _km_passes_filter(km):
            continue
        for kmi in km.keymap_items:
            if check_active and not kmi.active:
                continue
            if check_modifiers and not _kmi_matches_modifiers(kmi, effective):
                continue
            yield km, kmi


def _humanize_op_id(idname):
    """'mesh.extrude_region_move' -> 'Extrude Region Move' (drop category prefix)."""
    parts = idname.split('.')
    if len(parts) == 2:
        return parts[1].replace('_', ' ').title()
    return idname.replace('_', ' ').title()


def _km_passes_filter(km):
    """Check if a keymap passes the current editor/mode filters."""
    if 'ALL' not in state._filter_space_types:
        if km.space_type not in state._filter_space_types and km.space_type != 'EMPTY':
            return False
    if 'ALL' not in state._filter_modes:
        if not any(mode in km.name for mode in state._filter_modes):
            return False
    return True


def _get_bindings_for_key(event_type, modifiers):
    """Return list of (keymap_name, operator_idname, modifier_string, kmi, is_active)."""
    effective = state._get_effective_modifiers()
    mod_tuple = (effective['ctrl'], effective['shift'], effective['alt'], effective['oskey'])
    cache_key = (event_type, mod_tuple, frozenset(state._filter_space_types),
                 frozenset(state._filter_modes), state._modifier_source)
    if state._bindings_key == cache_key:
        return state._cached_bindings

    results = []
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        state._cached_bindings = results
        state._bindings_key = cache_key
        return results

    for km in kc.keymaps:
        if not _km_passes_filter(km):
            continue
        for kmi in km.keymap_items:
            if kmi.type != event_type:
                continue
            if not _kmi_matches_modifiers(kmi, effective):
                continue

            mod_str = _build_mod_string(kmi)
            results.append((km.name, kmi.idname, mod_str, kmi, kmi.active, km.space_type))
            if len(results) >= 20:
                break
        if len(results) >= 20:
            break

    state._cached_bindings = results
    state._bindings_key = cache_key
    return results


def _get_all_bindings_for_key(event_type):
    """Return ALL bindings for a key (no modifier filtering), sorted with matching ones first.

    Returns (results_list, n_matching) where n_matching is the count of
    bindings that match the current effective modifiers.
    """
    effective = state._get_effective_modifiers()
    mod_tuple = (effective['ctrl'], effective['shift'], effective['alt'], effective['oskey'])
    cache_key = (event_type, mod_tuple, frozenset(state._filter_space_types),
                 frozenset(state._filter_modes), state._modifier_source)
    if state._all_bindings_key == cache_key:
        return state._cached_all_bindings

    matching = []
    non_matching = []
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        result = ([], 0)
        state._cached_all_bindings = result
        state._all_bindings_key = cache_key
        return result

    for km in kc.keymaps:
        if not _km_passes_filter(km):
            continue
        for kmi in km.keymap_items:
            if kmi.type != event_type:
                continue

            mod_str = _build_mod_string(kmi)
            entry = (km.name, kmi.idname, mod_str, kmi, kmi.active, km.space_type)
            if _kmi_matches_modifiers(kmi, effective):
                matching.append(entry)
            else:
                non_matching.append(entry)

            if len(matching) + len(non_matching) >= 40:
                break
        if len(matching) + len(non_matching) >= 40:
            break

    results = matching + non_matching
    n_matching = len(matching)
    result = (results, n_matching)
    state._cached_all_bindings = result
    state._all_bindings_key = cache_key
    return result


def _group_bindings(bindings, n_matching):
    """Group flat binding list by (op_id, mod_str). Returns list of group tuples.

    Each group: (group_key, human_name, mod_str, entries, best_color_rank)
      - group_key: (op_id, mod_str) for expand/collapse tracking
      - entries: list of (orig_index, binding_tuple) preserving original order
      - best_color_rank: 0=matching, 1=non_matching, 2=inactive (for header color)
    """
    from collections import OrderedDict
    groups_dict = OrderedDict()
    for i, binding in enumerate(bindings):
        op_id = binding[1]
        mod_str = binding[2]
        key = (op_id, mod_str)
        if key not in groups_dict:
            groups_dict[key] = []
        groups_dict[key].append((i, binding))

    result = []
    for group_key, entries in groups_dict.items():
        op_id, mod_str = group_key
        human_name = _humanize_op_id(op_id)
        # Compute best color rank: 0=matching, 1=non_matching_active, 2=inactive
        best_rank = 2
        for orig_idx, b in entries:
            is_active = b[4]
            if not is_active:
                rank = 2
            elif orig_idx < n_matching:
                rank = 0
            else:
                rank = 1
            if rank < best_rank:
                best_rank = rank
        result.append((group_key, human_name, mod_str, entries, best_rank))
    return result


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
    for km, kmi in _iter_filtered_kmis():
        state._bound_keys_cache.add(kmi.type)
    state._bound_keys_dirty = False


def _update_search_filter():
    """Update state._search_matching_keys based on state._search_text."""
    state._search_matching_keys = set()

    if not state._search_text:
        state._batch_dirty = True
        return

    query = state._search_text.lower()
    for km, kmi in _iter_filtered_kmis(check_modifiers=False):
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
    for km, kmi in _iter_filtered_kmis():
        # Only store first (highest priority) binding per key
        if kmi.type not in state._key_labels_cache:
            state._key_labels_cache[kmi.type] = _get_operator_abbreviation(kmi.idname)
    state._key_labels_dirty = False


# ---------------------------------------------------------------------------
# Icon feature: Per-key editor icon cache
# ---------------------------------------------------------------------------
def _compute_key_editor_icons():
    """Compute the primary editor icon (space_type) for each key."""
    if not state._key_editor_icons_dirty:
        return
    state._key_editor_icons_cache = {}
    for km, kmi in _iter_filtered_kmis():
        # Only store first (highest priority) binding's space_type per key
        if kmi.type not in state._key_editor_icons_cache:
            if km.space_type and km.space_type != 'EMPTY':
                state._key_editor_icons_cache[kmi.type] = km.space_type
    state._key_editor_icons_dirty = False


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
    for km, kmi in _iter_filtered_kmis():
        if kmi.type not in state._key_categories_cache:
            cat = _get_operator_category(kmi.idname)
            if cat:
                state._key_categories_cache[kmi.type] = cat
    state._key_categories_dirty = False


# ---------------------------------------------------------------------------
# Key modifier badge computation
# ---------------------------------------------------------------------------
def _compute_key_modifier_badges():
    """Compute count of additional modifier combos per key (beyond current modifiers)."""
    if not state._key_modifier_badge_dirty:
        return
    state._key_modifier_badge_cache = {}
    effective = state._get_effective_modifiers()
    eff_tuple = (effective['ctrl'], effective['shift'], effective['alt'], effective['oskey'])

    # For each key, collect the set of modifier combos that have bindings
    key_mod_combos = {}  # {event_type: set of mod_tuples}
    for km, kmi in _iter_filtered_kmis(check_modifiers=False):
        mod_t = (kmi.ctrl, kmi.shift, kmi.alt, kmi.oskey)
        if mod_t == eff_tuple:
            continue  # Skip the currently-active combo
        if kmi.type not in key_mod_combos:
            key_mod_combos[kmi.type] = set()
        key_mod_combos[kmi.type].add(mod_t)

    for event_type, combos in key_mod_combos.items():
        state._key_modifier_badge_cache[event_type] = len(combos)

    state._key_modifier_badge_dirty = False


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


# ---------------------------------------------------------------------------
# Operator List panel: data collection and binding management
# ---------------------------------------------------------------------------

def _collect_all_operators():
    """Collect all user-facing operators from bpy.ops, categorized."""
    categories = {cat: [] for cat in OPERATOR_CATEGORY_ORDER}
    seen = set()
    for submod_name in sorted(dir(bpy.ops)):
        if submod_name.startswith('_'):
            continue
        submod = getattr(bpy.ops, submod_name, None)
        if submod is None:
            continue
        for op_name in sorted(dir(submod)):
            if op_name.startswith('_'):
                continue
            op_id = f"{submod_name}.{op_name}"
            if op_id in seen:
                continue
            seen.add(op_id)
            # Categorize
            cat = _get_operator_category(op_id)
            if cat is None:
                cat = "Other"
            # Human-readable name
            if op_id in OPERATOR_ABBREVIATIONS:
                human_name = OPERATOR_ABBREVIATIONS[op_id]
            else:
                human_name = _humanize_op_id(op_id)
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((op_id, human_name))
    # Sort each category alphabetically by human name
    for cat in categories:
        categories[cat].sort(key=lambda x: x[1].lower())
    state._operator_list_categories = categories
    state._operator_list_dirty = False


def _compute_bound_operators():
    """Compute the set of operator idnames that have active keybindings."""
    if not state._operator_list_bound_ops_dirty:
        return
    state._operator_list_bound_ops = set()
    for km, kmi in _iter_filtered_kmis(check_active=True, check_modifiers=False):
        state._operator_list_bound_ops.add(kmi.idname)
    state._operator_list_bound_ops_dirty = False


def _get_target_keymap_for_op(op_id):
    """Return (km_name, km_ref) for the best keymap to add a binding to."""
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return ("Window", None)
    # Match longest prefix
    best_km_name = "Window"
    best_len = 0
    for prefix, km_name in OPERATOR_CATEGORY_KEYMAPS.items():
        if op_id.startswith(prefix) and len(prefix) > best_len:
            best_km_name = km_name
            best_len = len(prefix)
    km_ref = kc.keymaps.get(best_km_name)
    if km_ref is None:
        km_ref = kc.keymaps.get("Window")
        best_km_name = "Window"
    return (best_km_name, km_ref)


def _create_new_binding(op_id, key_type, ctrl, shift, alt, oskey):
    """Create a new keybinding for an operator. Returns the new KMI or None."""
    km_name, km = _get_target_keymap_for_op(op_id)
    if km is None:
        return None
    new_kmi = km.keymap_items.new(op_id, key_type, 'PRESS',
                                   ctrl=ctrl, shift=shift, alt=alt, oskey=oskey)
    _push_undo([new_kmi])
    state._invalidate_cache()
    return new_kmi


def _remove_all_bindings_for_op(op_id):
    """Deactivate all keybindings for a given operator across all keymaps."""
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return
    matching = []
    for km in kc.keymaps:
        for kmi in km.keymap_items:
            if kmi.idname == op_id and kmi.active:
                matching.append(kmi)
    if matching:
        _push_undo(matching)
        for kmi in matching:
            kmi.active = False
        state._invalidate_cache()
