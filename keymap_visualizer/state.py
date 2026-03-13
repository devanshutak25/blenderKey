"""
Keymap Visualizer – Mutable shared state
All modules import this as a module and read/write attributes directly.
No imports from other addon modules (leaf node).
"""

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
_gpu_menu_items = []  # list of (label, action, x, y, w, h)
_gpu_menu_hovered = -1

# Phase 6: Export button
_export_button_rect = None  # (x, y, w, h)
_export_hovered = False

# Phase 7: Search
_search_text = ''
_search_active = False
_search_matching_keys = set()  # set of event_type strings
_search_last_update = 0.0

# Phase 7: Batch cache
_batch_dirty = True

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
_bound_keys_dirty = True

# v0.9 Feature 1: On-key command labels
_key_labels_cache = {}       # {event_type: "Short Name"}
_key_labels_dirty = True

# v0.9 Feature 2: Real-time physical modifier reactivity
_physical_modifiers = {'ctrl': False, 'shift': False, 'alt': False, 'oskey': False}
_modifier_source = 'TOGGLE'  # 'TOGGLE' or 'PHYSICAL'

# v0.9 Feature 3: Category color-coding
_key_categories_cache = {}   # {event_type: "category_name"}
_key_categories_dirty = True
_category_colors_enabled = True

# Icon feature: Per-key editor icon cache
_key_editor_icons_cache = {}   # {event_type: space_type}
_key_editor_icons_dirty = True

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
_filter_scroll_drag_target = None    # 'EDITOR', 'MODE', or None
_filter_scroll_drag_start_y = 0      # mouse Y when drag started
_filter_scroll_drag_start_offset = 0.0  # scroll offset when drag started

# Key modifier badge
_key_modifier_badge_cache = {}   # {event_type: int} — count of additional modifier combos
_key_modifier_badge_dirty = True

# Launch: deferred modal start (stored here because operator instances are
# freed after execute() returns, so self._xxx is invalid in timer callbacks)
_launch_window = None
_launch_retry_count = 0

# Watchdog: track the visualizer window for close detection
_target_window = None


def _invalidate_cache():
    """Invalidate binding cache and mark batches dirty."""
    global _bindings_key, _all_bindings_key, _batch_dirty, _bound_keys_dirty, _key_labels_dirty, _key_categories_dirty, _key_editor_icons_dirty, _key_modifier_badge_dirty
    _bindings_key = None
    _all_bindings_key = None
    _batch_dirty = True
    _bound_keys_dirty = True
    _key_labels_dirty = True
    _key_categories_dirty = True
    _key_editor_icons_dirty = True
    _key_modifier_badge_dirty = True


def _get_effective_modifiers():
    """Return active modifiers accounting for physical key state."""
    if any(_physical_modifiers.values()):
        return _physical_modifiers
    return _active_modifiers
