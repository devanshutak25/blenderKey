"""
Keymap Visualizer – Icon loading, caching, and lookup helpers.
Loads PNG icons from the icons/ directory into GPU textures for use in drawing.
"""

import os
import bpy
import gpu

_icon_textures = {}   # {"editors/view3d": GPUTexture, ...}
_icons_loaded = False

# Map space_type → icon filename (no extension)
EDITOR_ICON_FILES = {
    'ALL': 'editors/all_editors',
    'EMPTY': 'editors/global',
    'VIEW_3D': 'editors/view3d',
    'IMAGE_EDITOR': 'editors/image_editor',
    'NODE_EDITOR': 'editors/node_editor',
    'TEXT_EDITOR': 'editors/text_editor',
    'SEQUENCE_EDITOR': 'editors/sequencer',
    'CLIP_EDITOR': 'editors/clip_editor',
    'DOPESHEET_EDITOR': 'editors/dopesheet',
    'GRAPH_EDITOR': 'editors/graph_editor',
    'NLA_EDITOR': 'editors/nla_editor',
    'PROPERTIES': 'editors/properties',
    'OUTLINER': 'editors/outliner',
    'CONSOLE': 'editors/console',
    'SPREADSHEET': 'editors/spreadsheet',
}

MODE_ICON_FILES = {
    'ALL': 'modes/all_modes',
    'Object Mode': 'modes/object_mode',
    'Mesh': 'modes/edit_mesh',
    'Sculpt': 'modes/sculpt',
    'Pose': 'modes/pose',
    'Weight Paint': 'modes/weight_paint',
    'Vertex Paint': 'modes/vertex_paint',
    'Texture Paint': 'modes/texture_paint',
    'Grease Pencil': 'modes/grease_pencil',
    'Curves': 'modes/curves',
}

# For per-binding icons: same mapping as editor icons
SPACE_TYPE_TO_ICON_KEY = EDITOR_ICON_FILES


def _load_icons():
    """Load all icon PNGs into GPU textures. Call once from draw callback."""
    global _icons_loaded
    if _icons_loaded:
        return
    _icons_loaded = True

    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    all_mappings = {}
    all_mappings.update(EDITOR_ICON_FILES)
    all_mappings.update(MODE_ICON_FILES)

    for key, rel_path in all_mappings.items():
        if rel_path in _icon_textures:
            continue
        filepath = os.path.join(icons_dir, rel_path + ".png")
        if not os.path.exists(filepath):
            continue
        try:
            img = bpy.data.images.load(filepath, check_existing=True)
            img.colorspace_settings.name = 'Non-Color'
            img.gl_load()
            tex = gpu.texture.from_image(img)
            _icon_textures[rel_path] = tex
        except Exception:
            pass


def get_editor_icon(space_type):
    """Return GPUTexture for an editor type, or None."""
    key = EDITOR_ICON_FILES.get(space_type)
    return _icon_textures.get(key) if key else None


def get_mode_icon(mode):
    """Return GPUTexture for a mode, or None."""
    key = MODE_ICON_FILES.get(mode)
    return _icon_textures.get(key) if key else None


def get_km_icon(km_space_type):
    """Return GPUTexture for a keymap's space_type (for binding lines)."""
    key = SPACE_TYPE_TO_ICON_KEY.get(km_space_type)
    return _icon_textures.get(key) if key else None


def cleanup_icons():
    """Remove loaded images from bpy.data on addon cleanup."""
    global _icons_loaded
    # Remove images we loaded
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    for rel_path in list(_icon_textures.keys()):
        filepath = os.path.join(icons_dir, rel_path + ".png")
        # Find and remove the image from bpy.data
        for img in bpy.data.images:
            try:
                if img.filepath and os.path.normpath(img.filepath) == os.path.normpath(filepath):
                    bpy.data.images.remove(img)
                    break
            except Exception:
                pass
    _icon_textures.clear()
    _icons_loaded = False
