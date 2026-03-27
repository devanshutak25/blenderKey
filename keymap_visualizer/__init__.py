"""
Keymap Visualizer – Visual keyboard-based keymap editor for Blender.
Requires Blender 4.2+ (tested against 5.0 API).
"""

import logging
import bpy
from .operators import WM_OT_keymap_viz_modal, WM_OT_keymap_viz_launch, _draw_header_button
from .preferences import KeymapVizPreferences
from . import state

_log = logging.getLogger("keymap_visualizer")

_classes = (
    KeymapVizPreferences,
    WM_OT_keymap_viz_modal,
    WM_OT_keymap_viz_launch,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_edit.append(_draw_header_button)


def unregister():
    # Clean up draw handler if still active
    if state._draw_handle is not None:
        try:
            bpy.types.SpaceTextEditor.draw_handler_remove(state._draw_handle, 'WINDOW')
        except Exception:
            _log.debug("Draw handler already removed", exc_info=True)
    state._reset_all_state()
    state._visualizer_running = False

    from .icons import cleanup_icons
    cleanup_icons()

    bpy.types.TOPBAR_MT_edit.remove(_draw_header_button)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
