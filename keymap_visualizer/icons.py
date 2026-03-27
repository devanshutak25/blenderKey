"""
Keymap Visualizer – Icon loading, caching, and lookup helpers.
Loads PNG icons from the icons/ directory and packs them into a single
texture atlas for efficient batched rendering.
"""

import logging
import os
import bpy
import gpu

_log = logging.getLogger("keymap_visualizer.icons")

_icons_loaded = False
_atlas_texture = None          # Single GPUTexture for all icons
_atlas_uvs = {}                # {rel_path: (u0, v0, u1, v1)}
_ATLAS_COLS = 5
_ICON_SIZE = 64                # All icons are 64x64

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
    """Load all icon PNGs and pack them into a single texture atlas."""
    global _icons_loaded, _atlas_texture
    if _icons_loaded:
        return
    _icons_loaded = True

    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    all_mappings = {}
    all_mappings.update(EDITOR_ICON_FILES)
    all_mappings.update(MODE_ICON_FILES)

    # Collect unique icon paths and load images
    loaded_images = {}  # {rel_path: bpy.types.Image}
    unique_paths = []
    for key, rel_path in all_mappings.items():
        if rel_path in loaded_images:
            continue
        filepath = os.path.join(icons_dir, rel_path + ".png")
        if not os.path.exists(filepath):
            continue
        try:
            img = bpy.data.images.load(filepath, check_existing=True)
            img.colorspace_settings.name = 'Non-Color'
            loaded_images[rel_path] = img
            unique_paths.append(rel_path)
        except Exception:
            _log.debug("Could not load icon %s", rel_path, exc_info=True)

    if not unique_paths:
        return

    # Compute atlas dimensions
    n = len(unique_paths)
    cols = _ATLAS_COLS
    rows = (n + cols - 1) // cols
    atlas_w = cols * _ICON_SIZE
    atlas_h = rows * _ICON_SIZE

    # Create atlas image
    atlas_name = "__keymap_viz_atlas__"
    if atlas_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[atlas_name])
    atlas_img = bpy.data.images.new(atlas_name, atlas_w, atlas_h, alpha=True)
    atlas_img.colorspace_settings.name = 'Non-Color'

    # Initialize atlas pixels to transparent black
    atlas_pixels = [0.0] * (atlas_w * atlas_h * 4)

    # Copy each icon into the atlas grid
    for idx, rel_path in enumerate(unique_paths):
        img = loaded_images[rel_path]
        col = idx % cols
        row = idx // cols

        # Icon pixel data (RGBA floats, row-major from bottom-left)
        try:
            icon_px = list(img.pixels)
        except Exception:
            _log.debug("Could not read pixels for %s", rel_path, exc_info=True)
            continue

        if len(icon_px) != _ICON_SIZE * _ICON_SIZE * 4:
            _log.debug("Icon %s has unexpected pixel count: %d", rel_path, len(icon_px))
            continue

        # Copy into atlas at (col * ICON_SIZE, row * ICON_SIZE) from bottom-left
        # Atlas rows are bottom-to-top in Blender's image coordinate system
        dest_x = col * _ICON_SIZE
        dest_y = row * _ICON_SIZE
        for iy in range(_ICON_SIZE):
            src_start = iy * _ICON_SIZE * 4
            dst_start = ((dest_y + iy) * atlas_w + dest_x) * 4
            atlas_pixels[dst_start:dst_start + _ICON_SIZE * 4] = icon_px[src_start:src_start + _ICON_SIZE * 4]

        # Compute UV coordinates (normalized 0-1)
        u0 = dest_x / atlas_w
        v0 = dest_y / atlas_h
        u1 = (dest_x + _ICON_SIZE) / atlas_w
        v1 = (dest_y + _ICON_SIZE) / atlas_h
        _atlas_uvs[rel_path] = (u0, v0, u1, v1)

    # Write pixels to atlas image and create GPU texture
    atlas_img.pixels.foreach_set(atlas_pixels)
    atlas_img.update()
    try:
        _atlas_texture = gpu.texture.from_image(atlas_img)
    except Exception:
        _log.error("Could not create atlas GPU texture", exc_info=True)
        _atlas_texture = None

    # Remove individual source images from bpy.data (atlas is all we need)
    for rel_path, img in loaded_images.items():
        try:
            bpy.data.images.remove(img)
        except Exception:
            pass


def get_atlas_texture():
    """Return the atlas GPUTexture, or None if not loaded."""
    return _atlas_texture


def get_editor_icon(space_type):
    """Return (atlas_texture, u0, v0, u1, v1) for an editor type, or None."""
    key = EDITOR_ICON_FILES.get(space_type)
    if key and key in _atlas_uvs and _atlas_texture:
        return (_atlas_texture,) + _atlas_uvs[key]
    return None


def get_mode_icon(mode):
    """Return (atlas_texture, u0, v0, u1, v1) for a mode, or None."""
    key = MODE_ICON_FILES.get(mode)
    if key and key in _atlas_uvs and _atlas_texture:
        return (_atlas_texture,) + _atlas_uvs[key]
    return None


def get_km_icon(km_space_type):
    """Return (atlas_texture, u0, v0, u1, v1) for a keymap's space_type."""
    key = SPACE_TYPE_TO_ICON_KEY.get(km_space_type)
    if key and key in _atlas_uvs and _atlas_texture:
        return (_atlas_texture,) + _atlas_uvs[key]
    return None


def cleanup_icons():
    """Remove atlas image and texture on addon cleanup."""
    global _icons_loaded, _atlas_texture
    atlas_name = "__keymap_viz_atlas__"
    if atlas_name in bpy.data.images:
        try:
            bpy.data.images.remove(bpy.data.images[atlas_name])
        except Exception:
            pass
    _atlas_texture = None
    _atlas_uvs.clear()
    _icons_loaded = False
