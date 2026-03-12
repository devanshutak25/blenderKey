"""
Keymap Visualizer – Visual keyboard-based keymap editor for Blender.
Requires Blender 4.2+ (tested against 5.0 API).
"""

bl_info = {
    "name": "Keymap Visualizer",
    "author": "blenderKey",
    "version": (0, 8, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Header",
    "description": "Visual keyboard-based keymap editor",
    "category": "System",
}

import bpy
from .operators import WM_OT_keymap_viz_modal, WM_OT_keymap_viz_launch, _draw_header_button
from .preferences import KeymapVizPreferences
from . import state

_classes = (
    KeymapVizPreferences,
    WM_OT_keymap_viz_modal,
    WM_OT_keymap_viz_launch,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_HT_header.append(_draw_header_button)


def unregister():
    # Clean up draw handler if still active
    if state._draw_handle is not None:
        try:
            bpy.types.SpaceTextEditor.draw_handler_remove(state._draw_handle, 'WINDOW')
        except Exception:
            pass
        state._draw_handle = None
    state._target_area = None
    state._launch_window = None
    state._visualizer_running = False
    state._key_rects = []
    state._cached_region_size = (0, 0)
    state._modifier_rects = []
    state._hovered_key_index = -1
    state._selected_key_index = -1

    bpy.types.VIEW3D_HT_header.remove(_draw_header_button)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
