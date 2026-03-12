"""
Keymap Visualizer – Addon Preferences
"""

import bpy
from bpy.props import StringProperty, EnumProperty, FloatVectorProperty
from . import state


class KeymapVizPreferences(bpy.types.AddonPreferences):
    bl_idname = "keymap_visualizer"

    export_path: StringProperty(
        name="Export Path",
        description="File path for keymap export",
        subtype='FILE_PATH',
        default="//custom_keymap.py",
    )
    export_scope: EnumProperty(
        name="Export Scope",
        items=[
            ('MODIFIED', "Modified Only", "Export only modified keybindings"),
            ('ALL', "All", "Export all keybindings"),
        ],
        default='MODIFIED',
    )

    # Color scheme (Phase 7)
    col_key_unbound: FloatVectorProperty(
        name="Key Unbound",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.25, 0.25, 0.28, 1.0),
        update=lambda self, ctx: state._invalidate_cache(),
    )
    col_key_selected: FloatVectorProperty(
        name="Key Selected",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.2, 0.5, 0.9, 1.0),
        update=lambda self, ctx: state._invalidate_cache(),
    )
    col_key_hovered: FloatVectorProperty(
        name="Key Hovered",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.35, 0.45, 0.6, 1.0),
        update=lambda self, ctx: state._invalidate_cache(),
    )
    col_background: FloatVectorProperty(
        name="Background",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.12, 0.12, 0.12, 0.95),
        update=lambda self, ctx: state._invalidate_cache(),
    )
    col_text: FloatVectorProperty(
        name="Text",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=lambda self, ctx: state._invalidate_cache(),
    )
    col_panel_bg: FloatVectorProperty(
        name="Panel Background",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.15, 0.15, 0.18, 0.9),
        update=lambda self, ctx: state._invalidate_cache(),
    )

    def draw(self, context):
        layout = self.layout

        # Export settings
        box = layout.box()
        box.label(text="Export Settings")
        box.prop(self, "export_path")
        box.prop(self, "export_scope")

        # Color scheme
        box = layout.box()
        box.label(text="Color Scheme")
        row = box.row()
        row.prop(self, "col_key_unbound")
        row.prop(self, "col_key_selected")
        row = box.row()
        row.prop(self, "col_key_hovered")
        row.prop(self, "col_background")
        row = box.row()
        row.prop(self, "col_text")
        row.prop(self, "col_panel_bg")
