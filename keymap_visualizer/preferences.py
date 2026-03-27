"""
Keymap Visualizer – Addon Preferences
"""

import os as _os
import bpy
from bpy.props import StringProperty, EnumProperty, FloatVectorProperty, BoolProperty
from . import state
from .constants import (
    CATEGORY_COLORS,
    BASE_ACCENT, BASE_BACKGROUND, BASE_SURFACE, BASE_TEXT,
    BASE_SUCCESS, BASE_WARNING, BASE_DANGER, BASE_INFO,
)

_addon_dir = _os.path.dirname(_os.path.abspath(__file__))


def _invalidate(self, ctx):
    state._invalidate_cache()


def _invalidate_layout(self, ctx):
    """Force full relayout when keyboard layout preferences change."""
    state._cached_region_size = (0, 0)
    state._invalidate_cache()


class KeymapVizPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # --- Keyboard Layout ---
    keyboard_logical_layout: EnumProperty(
        name="Keyboard Layout",
        items=[
            ('AUTO', "Auto-Detect", "Detect from OS"),
            ('QWERTY', "QWERTY (US)", ""),
            ('AZERTY', "AZERTY (French)", ""),
            ('QWERTZ', "QWERTZ (German)", ""),
            ('DVORAK', "Dvorak", ""),
            ('COLEMAK', "Colemak", ""),
            ('NORDIC', "Nordic (DK/SE/NO)", ""),
        ],
        default='AUTO',
        update=_invalidate_layout,
    )
    keyboard_form_factor: EnumProperty(
        name="Form Factor",
        items=[('ANSI', "ANSI", ""), ('ISO', "ISO", "")],
        default='ANSI',
        update=_invalidate_layout,
    )
    keyboard_physical_size: EnumProperty(
        name="Keyboard Size",
        items=[
            ('100', "Full Size (100%)", ""),
            ('96', "Compact Full (96%)", ""),
            ('80', "TKL (80%)", ""),
            ('75', "75%", ""),
            ('65', "65%", ""),
            ('60', "60%", ""),
        ],
        default='100',
        update=_invalidate_layout,
    )

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

    # --- Import ---
    import_path: StringProperty(
        name="Import Path",
        description="File path for keymap import (Python script exported by this addon)",
        subtype='FILE_PATH',
        default="",
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

    # ======================================================================
    # Base theme tokens (8 colors that drive all derived colors)
    # ======================================================================
    col_accent: FloatVectorProperty(
        name="Accent", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=BASE_ACCENT,
        update=_invalidate,
    )
    col_background: FloatVectorProperty(
        name="Background", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=BASE_BACKGROUND,
        update=_invalidate,
    )
    col_surface: FloatVectorProperty(
        name="Surface", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=BASE_SURFACE,
        update=_invalidate,
    )
    col_text: FloatVectorProperty(
        name="Text", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=BASE_TEXT,
        update=_invalidate,
    )
    col_success: FloatVectorProperty(
        name="Success", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=BASE_SUCCESS,
        update=_invalidate,
    )
    col_warning: FloatVectorProperty(
        name="Warning", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=BASE_WARNING,
        update=_invalidate,
    )
    col_danger: FloatVectorProperty(
        name="Danger", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=BASE_DANGER,
        update=_invalidate,
    )
    col_info: FloatVectorProperty(
        name="Info", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=BASE_INFO,
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

    # ======================================================================
    # Advanced color overrides (hidden behind toggle, override derived colors)
    # ======================================================================
    show_advanced_colors: BoolProperty(
        name="Advanced Color Overrides",
        description="Show individual color overrides (derived from base tokens by default)",
        default=False,
    )

    # Key overrides
    use_key_unbound_override: BoolProperty(name="", default=False, update=_invalidate)
    col_key_unbound: FloatVectorProperty(
        name="Key Unbound", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.25, 0.25, 0.28, 1.0),
        update=_invalidate,
    )
    use_key_selected_override: BoolProperty(name="", default=False, update=_invalidate)
    col_key_selected: FloatVectorProperty(
        name="Key Selected", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.2, 0.5, 0.9, 1.0),
        update=_invalidate,
    )
    use_key_hovered_override: BoolProperty(name="", default=False, update=_invalidate)
    col_key_hovered: FloatVectorProperty(
        name="Key Hovered", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.35, 0.45, 0.6, 1.0),
        update=_invalidate,
    )
    use_key_bound_override: BoolProperty(name="", default=False, update=_invalidate)
    col_key_bound: FloatVectorProperty(
        name="Key Bound", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.28, 0.30, 0.38, 1.0),
        update=_invalidate,
    )
    use_key_modifier_override: BoolProperty(name="", default=False, update=_invalidate)
    col_key_modifier: FloatVectorProperty(
        name="Modifier Key", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.3, 0.28, 0.25, 1.0),
        update=_invalidate,
    )

    # UI overrides
    use_text_dim_override: BoolProperty(name="", default=False, update=_invalidate)
    col_text_dim: FloatVectorProperty(
        name="Text Dim", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.74, 0.74, 0.74, 1.0),
        update=_invalidate,
    )
    use_panel_bg_override: BoolProperty(name="", default=False, update=_invalidate)
    col_panel_bg: FloatVectorProperty(
        name="Panel BG", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.17, 0.17, 0.18, 0.95),
        update=_invalidate,
    )
    use_shadow_override: BoolProperty(name="", default=False, update=_invalidate)
    col_shadow: FloatVectorProperty(
        name="Shadow", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.0, 0.0, 0.0, 0.3),
        update=_invalidate,
    )
    use_border_override: BoolProperty(name="", default=False, update=_invalidate)
    col_border: FloatVectorProperty(
        name="Border", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.4, 0.4, 0.42, 1.0),
        update=_invalidate,
    )
    use_border_highlight_override: BoolProperty(name="", default=False, update=_invalidate)
    col_border_highlight: FloatVectorProperty(
        name="Border Highlight", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.7, 0.8, 1.0, 1.0),
        update=_invalidate,
    )
    use_toggle_active_override: BoolProperty(name="", default=False, update=_invalidate)
    col_toggle_active: FloatVectorProperty(
        name="Toggle Active", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.2, 0.5, 0.9, 1.0),
        update=_invalidate,
    )
    use_toggle_inactive_override: BoolProperty(name="", default=False, update=_invalidate)
    col_toggle_inactive: FloatVectorProperty(
        name="Toggle Inactive", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.22, 0.22, 0.25, 1.0),
        update=_invalidate,
    )
    use_button_normal_override: BoolProperty(name="", default=False, update=_invalidate)
    col_button_normal: FloatVectorProperty(
        name="Button", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.3, 0.3, 0.35, 1.0),
        update=_invalidate,
    )
    use_button_hover_override: BoolProperty(name="", default=False, update=_invalidate)
    col_button_hover: FloatVectorProperty(
        name="Button Hover", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.4, 0.5, 0.65, 1.0),
        update=_invalidate,
    )
    use_export_button_override: BoolProperty(name="", default=False, update=_invalidate)
    col_export_button: FloatVectorProperty(
        name="Export Button", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.25, 0.35, 0.25, 1.0),
        update=_invalidate,
    )
    use_export_button_hover_override: BoolProperty(name="", default=False, update=_invalidate)
    col_export_button_hover: FloatVectorProperty(
        name="Export Button Hover", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.3, 0.5, 0.3, 1.0),
        update=_invalidate,
    )
    use_search_bg_override: BoolProperty(name="", default=False, update=_invalidate)
    col_search_bg: FloatVectorProperty(
        name="Search Background", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.18, 0.18, 0.22, 0.95),
        update=_invalidate,
    )
    use_search_border_override: BoolProperty(name="", default=False, update=_invalidate)
    col_search_border: FloatVectorProperty(
        name="Search Border", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.4, 0.5, 0.7, 1.0),
        update=_invalidate,
    )
    use_menu_bg_override: BoolProperty(name="", default=False, update=_invalidate)
    col_menu_bg: FloatVectorProperty(
        name="Menu Background", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.15, 0.15, 0.18, 0.98),
        update=_invalidate,
    )
    use_menu_hover_override: BoolProperty(name="", default=False, update=_invalidate)
    col_menu_hover: FloatVectorProperty(
        name="Menu Hover", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.3, 0.4, 0.55, 1.0),
        update=_invalidate,
    )
    use_menu_border_override: BoolProperty(name="", default=False, update=_invalidate)
    col_menu_border: FloatVectorProperty(
        name="Menu Border", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.4, 0.4, 0.45, 1.0),
        update=_invalidate,
    )
    use_capture_overlay_override: BoolProperty(name="", default=False, update=_invalidate)
    col_capture_overlay: FloatVectorProperty(
        name="Capture Overlay", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.0, 0.0, 0.0, 0.6),
        update=_invalidate,
    )
    use_capture_text_override: BoolProperty(name="", default=False, update=_invalidate)
    col_capture_text: FloatVectorProperty(
        name="Capture Text", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(1.0, 0.9, 0.3, 1.0),
        update=_invalidate,
    )
    use_conflict_bg_override: BoolProperty(name="", default=False, update=_invalidate)
    col_conflict_bg: FloatVectorProperty(
        name="Conflict Panel", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.1, 0.1, 0.12, 0.95),
        update=_invalidate,
    )
    use_conflict_header_override: BoolProperty(name="", default=False, update=_invalidate)
    col_conflict_header: FloatVectorProperty(
        name="Conflict Header", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(1.0, 0.4, 0.3, 1.0),
        update=_invalidate,
    )
    use_shortcut_search_text_override: BoolProperty(name="", default=False, update=_invalidate)
    col_shortcut_search_text: FloatVectorProperty(
        name="Shortcut Search Text", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.3, 0.9, 0.8, 1.0),
        update=_invalidate,
    )
    use_active_highlight_override: BoolProperty(name="", default=False, update=_invalidate)
    col_active_highlight: FloatVectorProperty(
        name="Active Highlight", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.22, 0.28, 0.35, 1.0),
        update=_invalidate,
    )
    use_text_inactive_override: BoolProperty(name="", default=False, update=_invalidate)
    col_text_inactive: FloatVectorProperty(
        name="Inactive Text", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.55, 0.55, 0.55, 1.0),
        update=_invalidate,
    )
    use_badge_text_override: BoolProperty(name="", default=False, update=_invalidate)
    col_badge_text: FloatVectorProperty(
        name="Badge Text", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.79, 0.79, 0.79, 1.0),
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

        # Keyboard Layout
        box = layout.box()
        box.label(text="Keyboard Layout")
        box.prop(self, "keyboard_logical_layout")
        row = box.row()
        row.prop(self, "keyboard_form_factor")
        row.prop(self, "keyboard_physical_size")

        # Export settings
        box = layout.box()
        box.label(text="Export / Import Settings")
        box.prop(self, "export_path")
        box.prop(self, "export_scope")
        box.prop(self, "import_path")

        # Presets
        box = layout.box()
        box.label(text="Presets")
        box.prop(self, "presets_directory")

        # Fonts
        box = layout.box()
        box.label(text="Fonts")
        box.prop(self, "main_font_path")
        box.prop(self, "condensed_font_path")

        # Theme (8 base tokens)
        box = layout.box()
        box.label(text="Theme")
        row = box.row()
        row.prop(self, "col_accent")
        row.prop(self, "col_background")
        row.prop(self, "col_surface")
        row.prop(self, "col_text")
        row = box.row()
        row.prop(self, "col_success")
        row.prop(self, "col_warning")
        row.prop(self, "col_danger")
        row.prop(self, "col_info")

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

        # Advanced Color Overrides (collapsed by default)
        box = layout.box()
        box.prop(self, "show_advanced_colors", icon='TRIA_DOWN' if self.show_advanced_colors else 'TRIA_RIGHT')
        if self.show_advanced_colors:
            box.label(text="Enable overrides to customize individual derived colors:")
            _OVERRIDES = [
                ("key_unbound", "Key Unbound"),
                ("key_selected", "Key Selected"),
                ("key_hovered", "Key Hovered"),
                ("key_bound", "Key Bound"),
                ("key_modifier", "Modifier Key"),
                ("text_dim", "Text Dim"),
                ("panel_bg", "Panel BG"),
                ("shadow", "Shadow"),
                ("border", "Border"),
                ("border_highlight", "Border Highlight"),
                ("toggle_active", "Toggle Active"),
                ("toggle_inactive", "Toggle Inactive"),
                ("button_normal", "Button"),
                ("button_hover", "Button Hover"),
                ("export_button", "Export Button"),
                ("export_button_hover", "Export Hover"),
                ("search_bg", "Search BG"),
                ("search_border", "Search Border"),
                ("menu_bg", "Menu BG"),
                ("menu_hover", "Menu Hover"),
                ("menu_border", "Menu Border"),
                ("capture_overlay", "Capture Overlay"),
                ("capture_text", "Capture Text"),
                ("conflict_bg", "Conflict BG"),
                ("conflict_header", "Conflict Header"),
                ("shortcut_search_text", "Search Text"),
                ("active_highlight", "Active Highlight"),
                ("text_inactive", "Inactive Text"),
                ("badge_text", "Badge Text"),
            ]
            for prop_suffix, label in _OVERRIDES:
                row = box.row(align=True)
                row.prop(self, f"use_{prop_suffix}_override", text="")
                sub = row.row()
                sub.enabled = getattr(self, f"use_{prop_suffix}_override")
                sub.prop(self, f"col_{prop_suffix}")
