"""
Keymap Visualizer – Addon Preferences
"""

import os as _os
import bpy
from bpy.props import StringProperty, EnumProperty, FloatVectorProperty, BoolProperty
from . import state
from .constants import CATEGORY_COLORS

_addon_dir = _os.path.dirname(_os.path.abspath(__file__))


def _invalidate(self, ctx):
    state._invalidate_cache()


class KeymapVizPreferences(bpy.types.AddonPreferences):
    bl_idname = "keymap_visualizer"

    # --- Export ---
    export_path: StringProperty(
        name="Export Path",
        description="File path for keymap export",
        subtype='FILE_PATH',
        default=_os.path.join(_addon_dir, "exports", "custom_keymap.py"),
    )
    export_scope: EnumProperty(
        name="Export Scope",
        items=[
            ('MODIFIED', "Modified Only", "Export only modified keybindings"),
            ('ALL', "All", "Export all keybindings"),
        ],
        default='MODIFIED',
    )

    # --- Fonts ---
    main_font_path: StringProperty(
        name="Key Label Font",
        description="TTF font for key labels (leave empty for Blender default)",
        subtype='FILE_PATH',
        default="",
    )
    condensed_font_path: StringProperty(
        name="Command Label Font",
        description="TTF font for command labels (leave empty for bundled Roboto Condensed)",
        subtype='FILE_PATH',
        default="",
    )

    # --- Key colors ---
    col_key_unbound: FloatVectorProperty(
        name="Key Unbound", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.25, 0.25, 0.28, 1.0),
        update=_invalidate,
    )
    col_key_selected: FloatVectorProperty(
        name="Key Selected", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.2, 0.5, 0.9, 1.0),
        update=_invalidate,
    )
    col_key_hovered: FloatVectorProperty(
        name="Key Hovered", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.35, 0.45, 0.6, 1.0),
        update=_invalidate,
    )
    col_key_bound: FloatVectorProperty(
        name="Key Bound", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.28, 0.30, 0.38, 1.0),
        update=_invalidate,
    )
    col_key_modifier: FloatVectorProperty(
        name="Modifier Key", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.3, 0.28, 0.25, 1.0),
        update=_invalidate,
    )

    # --- General UI colors ---
    col_background: FloatVectorProperty(
        name="Background", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.12, 0.12, 0.12, 0.95),
        update=_invalidate,
    )
    col_text: FloatVectorProperty(
        name="Text", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(1.0, 1.0, 1.0, 1.0),
        update=_invalidate,
    )
    col_text_dim: FloatVectorProperty(
        name="Text Dim", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.7, 0.7, 0.7, 0.9),
        update=_invalidate,
    )
    col_panel_bg: FloatVectorProperty(
        name="Info Panel", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.15, 0.15, 0.18, 0.9),
        update=_invalidate,
    )
    col_shadow: FloatVectorProperty(
        name="Shadow", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.0, 0.0, 0.0, 0.3),
        update=_invalidate,
    )

    # --- Borders ---
    col_border: FloatVectorProperty(
        name="Border", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.4, 0.4, 0.42, 1.0),
        update=_invalidate,
    )
    col_border_highlight: FloatVectorProperty(
        name="Border Highlight", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.7, 0.8, 1.0, 1.0),
        update=_invalidate,
    )

    # --- Toggle buttons ---
    col_toggle_active: FloatVectorProperty(
        name="Toggle Active", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.2, 0.5, 0.9, 1.0),
        update=_invalidate,
    )
    col_toggle_inactive: FloatVectorProperty(
        name="Toggle Inactive", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.22, 0.22, 0.25, 1.0),
        update=_invalidate,
    )

    # --- Buttons ---
    col_button_normal: FloatVectorProperty(
        name="Button", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.3, 0.3, 0.35, 1.0),
        update=_invalidate,
    )
    col_button_hover: FloatVectorProperty(
        name="Button Hover", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.4, 0.5, 0.65, 1.0),
        update=_invalidate,
    )
    col_export_button: FloatVectorProperty(
        name="Export Button", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.25, 0.35, 0.25, 1.0),
        update=_invalidate,
    )
    col_export_button_hover: FloatVectorProperty(
        name="Export Button Hover", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.3, 0.5, 0.3, 1.0),
        update=_invalidate,
    )

    # --- Search ---
    col_search_bg: FloatVectorProperty(
        name="Search Background", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.18, 0.18, 0.22, 0.95),
        update=_invalidate,
    )
    col_search_border: FloatVectorProperty(
        name="Search Border", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.4, 0.5, 0.7, 1.0),
        update=_invalidate,
    )

    # --- Context menu ---
    col_menu_bg: FloatVectorProperty(
        name="Menu Background", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.15, 0.15, 0.18, 0.98),
        update=_invalidate,
    )
    col_menu_hover: FloatVectorProperty(
        name="Menu Hover", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.3, 0.4, 0.55, 1.0),
        update=_invalidate,
    )
    col_menu_border: FloatVectorProperty(
        name="Menu Border", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.4, 0.4, 0.45, 1.0),
        update=_invalidate,
    )

    # --- Overlays ---
    col_capture_overlay: FloatVectorProperty(
        name="Capture Overlay", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.0, 0.0, 0.0, 0.6),
        update=_invalidate,
    )
    col_capture_text: FloatVectorProperty(
        name="Capture Text", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(1.0, 0.9, 0.3, 1.0),
        update=_invalidate,
    )
    col_conflict_bg: FloatVectorProperty(
        name="Conflict Panel", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.1, 0.1, 0.12, 0.95),
        update=_invalidate,
    )
    col_conflict_header: FloatVectorProperty(
        name="Conflict Header", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(1.0, 0.4, 0.3, 1.0),
        update=_invalidate,
    )
    col_shortcut_search_text: FloatVectorProperty(
        name="Shortcut Search Text", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.3, 0.9, 0.8, 1.0),
        update=_invalidate,
    )

    # --- Category colors ---
    enable_category_colors: BoolProperty(
        name="Category Colors",
        description="Color keys by operator category (Transform, Navigation, etc.)",
        default=True,
        update=_invalidate,
    )
    col_cat_transform: FloatVectorProperty(
        name="Transform", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.45, 0.30, 0.15, 0.90),
        update=_invalidate,
    )
    col_cat_navigation: FloatVectorProperty(
        name="Navigation", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.15, 0.35, 0.38, 0.90),
        update=_invalidate,
    )
    col_cat_mesh: FloatVectorProperty(
        name="Mesh", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.30, 0.20, 0.40, 0.90),
        update=_invalidate,
    )
    col_cat_object: FloatVectorProperty(
        name="Object", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.25, 0.35, 0.25, 0.90),
        update=_invalidate,
    )
    col_cat_playback: FloatVectorProperty(
        name="Playback", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.20, 0.28, 0.45, 0.90),
        update=_invalidate,
    )
    col_cat_animation: FloatVectorProperty(
        name="Animation", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.40, 0.35, 0.15, 0.90),
        update=_invalidate,
    )
    col_cat_nodes: FloatVectorProperty(
        name="Nodes", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.35, 0.25, 0.30, 0.90),
        update=_invalidate,
    )
    col_cat_uv: FloatVectorProperty(
        name="UV", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.20, 0.38, 0.30, 0.90),
        update=_invalidate,
    )
    col_cat_sculpt: FloatVectorProperty(
        name="Sculpt", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.38, 0.22, 0.22, 0.90),
        update=_invalidate,
    )
    col_cat_paint: FloatVectorProperty(
        name="Paint", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.35, 0.30, 0.20, 0.90),
        update=_invalidate,
    )
    col_cat_system: FloatVectorProperty(
        name="System", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.25, 0.25, 0.30, 0.90),
        update=_invalidate,
    )
    col_cat_edit: FloatVectorProperty(
        name="Edit", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.30, 0.30, 0.35, 0.90),
        update=_invalidate,
    )
    col_cat_file: FloatVectorProperty(
        name="File", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.22, 0.30, 0.28, 0.90),
        update=_invalidate,
    )

    # --- Presets ---
    presets_directory: StringProperty(
        name="Presets Folder",
        description="Directory to store keymap presets",
        subtype='DIR_PATH',
        default=_os.path.join(_addon_dir, "presets"),
    )

    def draw(self, context):
        layout = self.layout

        # Export settings
        box = layout.box()
        box.label(text="Export Settings")
        box.prop(self, "export_path")
        box.prop(self, "export_scope")

        # Presets
        box = layout.box()
        box.label(text="Presets")
        box.prop(self, "presets_directory")

        # Fonts
        box = layout.box()
        box.label(text="Fonts")
        box.prop(self, "main_font_path")
        box.prop(self, "condensed_font_path")

        # Key colors
        box = layout.box()
        box.label(text="Key Colors")
        row = box.row()
        row.prop(self, "col_key_unbound")
        row.prop(self, "col_key_selected")
        row.prop(self, "col_key_hovered")
        row = box.row()
        row.prop(self, "col_key_bound")
        row.prop(self, "col_key_modifier")

        # General UI
        box = layout.box()
        box.label(text="General UI")
        row = box.row()
        row.prop(self, "col_background")
        row.prop(self, "col_panel_bg")
        row.prop(self, "col_shadow")
        row = box.row()
        row.prop(self, "col_text")
        row.prop(self, "col_text_dim")

        # Borders
        box = layout.box()
        box.label(text="Borders")
        row = box.row()
        row.prop(self, "col_border")
        row.prop(self, "col_border_highlight")

        # Toggles & Buttons
        box = layout.box()
        box.label(text="Toggles & Buttons")
        row = box.row()
        row.prop(self, "col_toggle_active")
        row.prop(self, "col_toggle_inactive")
        row = box.row()
        row.prop(self, "col_button_normal")
        row.prop(self, "col_button_hover")
        row = box.row()
        row.prop(self, "col_export_button")
        row.prop(self, "col_export_button_hover")

        # Search
        box = layout.box()
        box.label(text="Search")
        row = box.row()
        row.prop(self, "col_search_bg")
        row.prop(self, "col_search_border")

        # Context Menu
        box = layout.box()
        box.label(text="Context Menu")
        row = box.row()
        row.prop(self, "col_menu_bg")
        row.prop(self, "col_menu_hover")
        row.prop(self, "col_menu_border")

        # Overlays
        box = layout.box()
        box.label(text="Overlays")
        row = box.row()
        row.prop(self, "col_capture_overlay")
        row.prop(self, "col_capture_text")
        row = box.row()
        row.prop(self, "col_conflict_bg")
        row.prop(self, "col_conflict_header")
        row = box.row()
        row.prop(self, "col_shortcut_search_text")

        # Category colors
        box = layout.box()
        box.label(text="Category Colors")
        box.prop(self, "enable_category_colors")
        if self.enable_category_colors:
            row = box.row()
            row.prop(self, "col_cat_transform")
            row.prop(self, "col_cat_navigation")
            row.prop(self, "col_cat_mesh")
            row = box.row()
            row.prop(self, "col_cat_object")
            row.prop(self, "col_cat_playback")
            row.prop(self, "col_cat_animation")
            row = box.row()
            row.prop(self, "col_cat_nodes")
            row.prop(self, "col_cat_uv")
            row.prop(self, "col_cat_sculpt")
            row = box.row()
            row.prop(self, "col_cat_paint")
            row.prop(self, "col_cat_system")
            row.prop(self, "col_cat_edit")
            row = box.row()
            row.prop(self, "col_cat_file")
