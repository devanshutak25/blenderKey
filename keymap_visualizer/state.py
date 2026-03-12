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

# Feature 4: Editor/Mode filters
_filter_space_type = 'ALL'
_filter_mode = 'ALL'
_filter_editor_btn_rect = None   # (x, y, w, h)
_filter_mode_btn_rect = None     # (x, y, w, h)
_filter_editor_hovered = False
_filter_mode_hovered = False
_filter_dropdown_open = None     # None, 'EDITOR', or 'MODE'
_filter_dropdown_rects = []      # [(label, value, x, y, w, h), ...]
_filter_dropdown_hovered = -1

# Launch: deferred modal start (stored here because operator instances are
# freed after execute() returns, so self._xxx is invalid in timer callbacks)
_launch_window = None
_launch_retry_count = 0


def _invalidate_cache():
    """Invalidate binding cache and mark batches dirty."""
    global _bindings_key, _batch_dirty, _bound_keys_dirty
    _bindings_key = None
    _batch_dirty = True
    _bound_keys_dirty = True
