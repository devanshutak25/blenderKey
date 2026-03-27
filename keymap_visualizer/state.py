"""
Keymap Visualizer – Mutable shared state
All modules import this as a module and read/write attributes directly.
No imports from other addon modules (leaf node).
"""

import bpy
from enum import IntFlag, auto


class DirtyFlag(IntFlag):
    BATCH = auto()
    BOUND_KEYS = auto()
    KEY_LABELS = auto()
    KEY_CATEGORIES = auto()
    KEY_EDITOR_ICONS = auto()
    KEY_MODIFIER_BADGES = auto()
    OPERATOR_LIST = auto()
    OPERATOR_BOUND_OPS = auto()
    DIFF = auto()
    ALL = BATCH | BOUND_KEYS | KEY_LABELS | KEY_CATEGORIES | KEY_EDITOR_ICONS | KEY_MODIFIER_BADGES | OPERATOR_LIST | OPERATOR_BOUND_OPS | DIFF


# ---------------------------------------------------------------------------
# Addon package name (used for preferences lookup)
# ---------------------------------------------------------------------------
_addon_package = __package__


def _get_prefs():
    """Return addon preferences using the runtime package name."""
    return bpy.context.preferences.addons[_addon_package].preferences


# ---------------------------------------------------------------------------
# Re-entrant guard
# ---------------------------------------------------------------------------
_visualizer_running = False


def _set_running(val: bool):
    global _visualizer_running
    _visualizer_running = val


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_draw_handle = None
_target_area = None
_key_rects = []                    # list of KeyRect
_cached_region_size = (0, 0)
_hovered_key_index = -1
_selected_key_index = -1
_active_modifiers = {'ctrl': False, 'shift': False, 'alt': False, 'oskey': False}
_modifier_rects = []               # list of (label, dict_key, x, y, w, h)
_cached_bindings = []              # cached binding results
_bindings_key = None               # (event_type, mod_tuple) used to cache
_cached_all_bindings = ([], 0)     # cached all-bindings results for info panel
_all_bindings_key = None           # cache key for all-bindings

# Phase 5: State machine
_modal_state = 'IDLE'  # IDLE, MENU_OPEN, CAPTURE, CONFLICT
_menu_context = {}
_conflict_data = {
    'new_type': None, 'new_ctrl': False, 'new_shift': False, 'new_alt': False,
    'new_oskey': False, 'source_kmi': None, 'source_km_name': None, 'conflicts': []
}
_conflict_button_rects = []  # list of (label, action, x, y, w, h)
_conflict_hovered_button = -1

# GPU-drawn context menu
_gpu_menu_items = []  # list of (label, binding_index, x, y, w, h, is_active) — 7-tuple
_gpu_menu_hovered = -1

# Flyout sub-menu
_gpu_flyout_items = []      # list of (label, action, x, y, w, h, binding_index)
_gpu_flyout_hovered = -1
_flyout_hover_timer = 0.0   # time.monotonic() when hover on main menu item started
_flyout_target_index = -1   # which main menu item is showing its flyout
_flyout_pending_index = -1  # which main menu item we're waiting to open flyout for

# Phase 6: Export button
_export_button_rect = None  # (x, y, w, h)
_export_hovered = False

# Import button
_import_button_rect = None  # (x, y, w, h)
_import_hovered = False

# Phase 7: Search
_search_text = ''
_search_active = False
_search_matching_keys = set()  # set of event_type strings
_search_results_count = 0      # number of matched keys (updated by _update_search_filter)
_search_last_update = 0.0

# Phase 7: Batch cache / dirty flags
_dirty_flags = DirtyFlag.ALL

# Phase 7: Hover transition
_hover_transition = 0.0
_hover_transition_target = -1
_last_frame_time = 0.0

# Feature 1: Close button
_close_button_rect = None   # (x, y, w, h)
_close_hovered = False
_should_close = False        # signal from handler → modal

# Feature 2: Resizable keyboard frame
_user_scale = 1.0
_resize_handle_rect = None   # (x, y, w, h)
_resize_hovered = False
_resize_dragging = False
_resize_drag_start_x = 0
_resize_drag_start_scale = 1.0

# Feature 3: Bound-key highlighting
_bound_keys_cache = set()    # set of event_type strings with active bindings

# v0.9 Feature 1: On-key command labels
_key_labels_cache = {}       # {event_type: "Short Name"}

# v0.9 Feature 2: Real-time physical modifier reactivity
_physical_modifiers = {'ctrl': False, 'shift': False, 'alt': False, 'oskey': False}
_modifier_source = 'TOGGLE'  # 'TOGGLE' or 'PHYSICAL'

# v0.9 Feature 3: Category color-coding
_key_categories_cache = {}   # {event_type: "category_name"}
_category_colors_enabled = True

# Icon feature: Per-key editor icon cache
_key_editor_icons_cache = {}   # {event_type: space_type}

# v0.9 Feature 4: Undo/redo for keymap changes
_undo_stack = []    # list of [{'kmi': kmi_ref, 'before': {snapshot}}, ...]
_redo_stack = []
_undo_max = 50

# v0.9 Feature 5: Shortcut search (reverse lookup)
_shortcut_search_active = False

# v0.9 Feature 6: Preset management
_presets_list = []
_active_preset_name = ""
_presets_btn_rect = None
_presets_hovered = False
_preset_dropdown_open = False
_preset_dropdown_rects = []
_preset_dropdown_hovered = -1
_preset_name_input_active = False
_preset_name_text = ""

# Feature 4: Editor/Mode filters (list panels)
_filter_space_types = {'ALL'}       # set of selected values
_filter_modes = {'ALL'}             # set of selected values
_filter_editor_list_rects = []      # [(label, value, x, y, w, h), ...]
_filter_mode_list_rects = []        # [(label, value, x, y, w, h), ...]
_filter_editor_list_rect = None     # bounding box (x, y, w, h) of editor list panel
_filter_mode_list_rect = None       # bounding box (x, y, w, h) of mode list panel
_filter_editor_hovered = -1         # index of hovered item (-1 = none)
_filter_mode_hovered = -1           # index of hovered item (-1 = none)
_filter_editor_scroll = 0           # scroll offset (pixels) for overflow
_filter_mode_scroll = 0
_filter_scroll_drag_target = None    # 'EDITOR', 'MODE', 'INFO', or None
_filter_scroll_drag_start_y = 0      # mouse Y when drag started
_filter_scroll_drag_start_offset = 0.0  # scroll offset when drag started

# Info panel scroll state
_info_panel_scroll = 0              # scroll offset for info panel bindings
_info_panel_rect = None             # (x, y, w, h) for hit testing
_info_panel_max_scroll = 0          # set during drawing, read by handlers

# Collapsible grouped bindings
_info_panel_expanded_groups = set()       # set of (op_id, mod_str) keys currently expanded
_info_panel_group_header_rects = []       # [(group_key, x, y, w, h), ...] rebuilt each frame

# Keyboard navigation (C2)
_nav_focus = 'KEYS'  # 'KEYS', 'EDITOR_LIST', 'MODE_LIST', 'INFO_PANEL'
_nav_key_index = 0   # keyboard-navigated key index (separate from mouse hover)
_key_row_map = []    # list of lists: _key_row_map[row] = [key_index, ...]

# Tooltips (L4)
_tooltip_text = ""
_tooltip_hover_start = 0.0  # time.monotonic() when hover began

# Key modifier badge
_key_modifier_badge_cache = {}   # {event_type: int} — count of additional modifier combos

# Operator List panel
_operator_list_rect = None              # (x, y, w, h) panel bounding box
_operator_list_categories = {}          # {category: [(op_id, human_name), ...]} cached
_operator_list_expanded = set()         # set of category names currently expanded
_operator_list_group_rects = []         # [(category, x, y, w, h), ...] rebuilt each frame
_operator_list_item_rects = []          # [(op_id, human_name, x, y, w, h), ...] rebuilt each frame
_operator_list_scroll = 0
_operator_list_max_scroll = 0
_operator_list_hovered_group = -1       # index into group_rects
_operator_list_hovered_item = -1        # index into item_rects
_operator_list_search_text = ''
_operator_list_search_active = False
_operator_list_bound_ops = set()        # op_ids with active bindings

# Operator flyout
_op_flyout_items = []                   # [(label, action, x, y, w, h), ...]
_op_flyout_hovered = -1
_op_flyout_target_op_id = None
_op_flyout_visible = False

# Capture-for-new-binding mode
_capture_new_binding = False
_capture_target_op_id = None
_capture_target_km_name = None

# Phase 5: Capture target key for dimmed overlay
_capture_target_key_index = -1

# Phase 7: Rebind success flash
_rebind_flash_key_index = -1
_rebind_flash_time = 0.0

# Diff view mode
_diff_mode_active = False
_diff_modified_keys = set()    # event_types with modified bindings
_diff_removed_keys = set()     # event_types with deactivated bindings

# Launch: deferred modal start (stored here because operator instances are
# freed after execute() returns, so self._xxx is invalid in timer callbacks)
_launch_window = None
_launch_retry_count = 0

# Watchdog: track the visualizer window for close detection
_target_window = None


def _reset_all_state():
    """Reset all mutable state to defaults. Callers handle draw handler removal,
    _set_running(), icon cleanup, and area redraws separately."""
    global _draw_handle, _target_area, _target_window, _launch_window
    global _hovered_key_index, _selected_key_index, _cached_region_size
    global _cached_bindings, _bindings_key, _cached_all_bindings, _all_bindings_key
    global _modal_state, _conflict_hovered_button, _gpu_menu_hovered
    global _gpu_flyout_hovered, _flyout_hover_timer, _flyout_target_index, _flyout_pending_index
    global _export_button_rect, _export_hovered
    global _import_button_rect, _import_hovered
    global _search_text, _search_active, _search_matching_keys, _search_results_count, _search_last_update
    global _dirty_flags, _hover_transition, _hover_transition_target, _last_frame_time
    global _close_button_rect, _close_hovered, _should_close
    global _user_scale, _resize_handle_rect, _resize_hovered, _resize_dragging
    global _resize_drag_start_x, _resize_drag_start_scale
    global _bound_keys_cache
    global _key_labels_cache
    global _physical_modifiers, _modifier_source
    global _key_categories_cache, _category_colors_enabled
    global _key_editor_icons_cache
    global _shortcut_search_active
    global _active_preset_name, _presets_btn_rect, _presets_hovered
    global _preset_dropdown_open, _preset_dropdown_hovered
    global _preset_name_input_active, _preset_name_text
    global _filter_space_types, _filter_modes
    global _filter_editor_list_rect, _filter_mode_list_rect
    global _filter_editor_hovered, _filter_mode_hovered
    global _filter_editor_scroll, _filter_mode_scroll
    global _filter_scroll_drag_target, _filter_scroll_drag_start_y, _filter_scroll_drag_start_offset
    global _info_panel_scroll, _info_panel_rect, _info_panel_max_scroll
    global _info_panel_expanded_groups, _info_panel_group_header_rects
    global _key_modifier_badge_cache
    global _launch_retry_count
    global _nav_focus, _nav_key_index
    global _tooltip_text, _tooltip_hover_start
    global _operator_list_rect
    global _operator_list_scroll, _operator_list_max_scroll
    global _operator_list_hovered_group, _operator_list_hovered_item
    global _operator_list_search_text, _operator_list_search_active
    global _operator_list_bound_ops
    global _op_flyout_hovered, _op_flyout_target_op_id, _op_flyout_visible
    global _capture_new_binding, _capture_target_op_id, _capture_target_km_name
    global _capture_target_key_index, _rebind_flash_key_index, _rebind_flash_time
    global _diff_mode_active, _diff_modified_keys, _diff_removed_keys

    _draw_handle = None
    _target_area = None
    _target_window = None
    _launch_window = None
    _launch_retry_count = 0
    _hovered_key_index = -1
    _selected_key_index = -1
    _key_rects.clear()
    _cached_region_size = (0, 0)
    _modifier_rects.clear()
    _active_modifiers.update({'ctrl': False, 'shift': False, 'alt': False, 'oskey': False})
    _cached_bindings.clear()
    _bindings_key = None
    _cached_all_bindings = ([], 0)
    _all_bindings_key = None
    _modal_state = 'IDLE'
    _menu_context.clear()
    _conflict_data['conflicts'] = []
    _conflict_button_rects.clear()
    _conflict_hovered_button = -1
    _gpu_menu_items.clear()
    _gpu_menu_hovered = -1
    _gpu_flyout_items.clear()
    _gpu_flyout_hovered = -1
    _flyout_hover_timer = 0.0
    _flyout_target_index = -1
    _flyout_pending_index = -1
    _export_button_rect = None
    _export_hovered = False
    _import_button_rect = None
    _import_hovered = False
    _search_text = ''
    _search_active = False
    _search_matching_keys = set()
    _search_results_count = 0
    _search_last_update = 0.0
    _dirty_flags = DirtyFlag.ALL
    _hover_transition = 0.0
    _hover_transition_target = -1
    _last_frame_time = 0.0
    _close_button_rect = None
    _close_hovered = False
    _should_close = False
    _user_scale = 1.0
    _resize_handle_rect = None
    _resize_hovered = False
    _resize_dragging = False
    _resize_drag_start_x = 0
    _resize_drag_start_scale = 1.0
    _bound_keys_cache = set()
    _key_labels_cache = {}
    _physical_modifiers = {'ctrl': False, 'shift': False, 'alt': False, 'oskey': False}
    _modifier_source = 'TOGGLE'
    _key_categories_cache = {}
    _key_editor_icons_cache = {}
    _undo_stack.clear()
    _redo_stack.clear()
    _shortcut_search_active = False
    _presets_list.clear()
    _active_preset_name = ""
    _presets_btn_rect = None
    _presets_hovered = False
    _preset_dropdown_open = False
    _preset_dropdown_rects.clear()
    _preset_dropdown_hovered = -1
    _preset_name_input_active = False
    _preset_name_text = ""
    _filter_space_types = {'ALL'}
    _filter_modes = {'ALL'}
    _filter_editor_list_rects.clear()
    _filter_mode_list_rects.clear()
    _filter_editor_list_rect = None
    _filter_mode_list_rect = None
    _filter_editor_hovered = -1
    _filter_mode_hovered = -1
    _filter_editor_scroll = 0
    _filter_mode_scroll = 0
    _filter_scroll_drag_target = None
    _filter_scroll_drag_start_y = 0
    _filter_scroll_drag_start_offset = 0.0
    _info_panel_scroll = 0
    _info_panel_rect = None
    _info_panel_max_scroll = 0
    _info_panel_expanded_groups = set()
    _info_panel_group_header_rects = []
    _key_modifier_badge_cache = {}
    _nav_focus = 'KEYS'
    _nav_key_index = 0
    _key_row_map.clear()
    _tooltip_text = ""
    _tooltip_hover_start = 0.0
    _operator_list_rect = None
    _operator_list_categories.clear()
    _operator_list_expanded.clear()
    _operator_list_group_rects.clear()
    _operator_list_item_rects.clear()
    _operator_list_scroll = 0
    _operator_list_max_scroll = 0
    _operator_list_hovered_group = -1
    _operator_list_hovered_item = -1
    _operator_list_search_text = ''
    _operator_list_search_active = False
    _operator_list_bound_ops = set()
    _op_flyout_items.clear()
    _op_flyout_hovered = -1
    _op_flyout_target_op_id = None
    _op_flyout_visible = False
    _capture_new_binding = False
    _capture_target_op_id = None
    _capture_target_km_name = None
    _capture_target_key_index = -1
    _rebind_flash_key_index = -1
    _rebind_flash_time = 0.0
    _diff_mode_active = False
    _diff_modified_keys = set()
    _diff_removed_keys = set()


def _invalidate_cache():
    """Invalidate binding cache and mark batches dirty."""
    global _bindings_key, _all_bindings_key, _dirty_flags
    _bindings_key = None
    _all_bindings_key = None
    _dirty_flags = DirtyFlag.ALL


def _get_effective_modifiers():
    """Return active modifiers accounting for physical key state."""
    if any(_physical_modifiers.values()):
        return _physical_modifiers
    return _active_modifiers
