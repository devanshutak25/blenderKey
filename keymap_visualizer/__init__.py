"""
Keymap Visualizer – Visual keyboard-based keymap editor for Blender.
Requires Blender 5.1+.
"""

import logging
import bpy
from .operators import WM_OT_keymap_viz_modal, WM_OT_keymap_viz_launch, _draw_header_button
from .preferences import KeymapVizPreferences
from . import state

_log = logging.getLogger("keymap_visualizer")

MIN_BLENDER_VERSION = (5, 1, 0)

_classes = (
    KeymapVizPreferences,
    WM_OT_keymap_viz_modal,
    WM_OT_keymap_viz_launch,
)


def _check_blender_version():
    if bpy.app.version < MIN_BLENDER_VERSION:
        current = ".".join(str(v) for v in bpy.app.version)
        required = ".".join(str(v) for v in MIN_BLENDER_VERSION)
        msg = (
            f"Keymap Visualizer requires Blender {required}+ "
            f"(running {current}). Some features may not work."
        )
        _log.warning(msg)
        try:
            def _draw(self, _context):
                self.layout.label(text=msg, icon='ERROR')
            bpy.context.window_manager.popup_menu(
                _draw, title="Keymap Visualizer – Unsupported Blender Version",
                icon='ERROR',
            )
        except Exception:
            _log.debug("Could not show popup warning", exc_info=True)
        return False
    return True


def register():
    _check_blender_version()
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
