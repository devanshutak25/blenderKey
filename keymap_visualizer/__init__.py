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

_classes = (
    KeymapVizPreferences,
    WM_OT_keymap_viz_modal,
    WM_OT_keymap_viz_launch,
)


def _first_run_notice():
    """Show a one-time popup warning about keymap data safety.

    Scheduled from register() via bpy.app.timers because popup_menu needs a
    valid window-manager context that isn't available during class registration.
    """
    try:
        from . import state
        prefs = state._get_prefs()
    except Exception:
        _log.debug("First-run: could not read preferences", exc_info=True)
        return None
    if prefs is None or getattr(prefs, "first_run_seen", True):
        return None

    def _draw(self, _context):
        col = self.layout.column(align=True)
        col.label(text="Keymap Visualizer is installed.", icon='CHECKMARK')
        col.separator()
        col.label(text="Keymaps are sensitive user data.", icon='ERROR')
        col.label(text="This add-on edits Blender keymaps in place. Keymap loss or corruption is possible, with no guaranteed way to restore them from within Blender.")
        col.separator()
        col.label(text="Back up userpref.blend and any keyconfig files from your Blender config folder before making changes.")
        col.separator()
        col.label(text="You can review this notice anytime under Edit > Preferences > Add-ons > Keymap Visualizer.")

    try:
        bpy.context.window_manager.popup_menu(
            _draw,
            title="Keymap Visualizer — Please read before use",
            icon='ERROR',
        )
        prefs.first_run_seen = True
    except Exception:
        _log.debug("First-run: popup failed, will retry on next enable", exc_info=True)
    return None


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_edit.append(_draw_header_button)
    # Show a one-time warning popup on first install/enable.
    try:
        bpy.app.timers.register(_first_run_notice, first_interval=0.5)
    except Exception:
        _log.debug("Could not schedule first-run notice", exc_info=True)


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
