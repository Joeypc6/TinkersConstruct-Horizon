"""Tinkers' slime foliage colours on the content side: the items' tints.

Java (WorldClientEvents.registerBlockColorHandlers / registerItemColorHandlers) draws the slime grass, nylium, leaves,
ferns, tall grass, potted ferns and vines from grayscale textures whose `tintindex` faces a colour handler colours:
- in the world, `SlimeColorizer.getColorForPos(pos, type)`: the foliage type's colormap
  (`textures/colormap/<type>_grass_color.png`, 256x256) by block x and z, looping every 512 blocks, leaves and vines
  offset by (128, 0, 128);
- with no position (items, and a block drawn with no position): `FoliageType.getColor()`, a fixed colour per type
  (earth 0x8CD782, sky 0x00F4DA, ichor 0xD09800, ender 0xA92DFF, blood 0xB80000). Vines are the sky and ender vines'
  own type.

The blocks keep the jar's tinted models and the colormaps ship as the jar's own textures: the native mod's mesher
module (mixins/tconstruct/tinting.rs) colours their tinted faces as the block handlers do. The items keep the jar's
grayscale models and get `minecraft:constant` tints of FoliageType's colour, which is exactly what Java's item colour
handler returns.

Usage (from make_content.py): foliage_colors.write(files, skipped)
"""

import json

ID = "tconstruct"
TYPES = ("earth", "sky", "ichor", "ender", "blood")
DIRTS = ("earth", "sky", "ichor", "ender", "vanilla")
# FoliageType's constructor colours: the item colour (and a block's with no position).
ITEM_COLORS = {"earth": 0x8CD782, "sky": 0x00F4DA, "ichor": 0xD09800, "ender": 0xA92DFF, "blood": 0xB80000}


def write(files, skipped):
    def load(path):
        return json.loads(files[path].decode("utf-8-sig"))

    for t in TYPES:
        path = f"assets/{ID}/textures/colormap/{t}_grass_color.png"
        if path not in files:
            raise SystemExit(f"foliage_colors.py: the jar has no {path}")

    item_types = {}
    for t in TYPES:
        item_types.update({f"{t}_{d}_slime_grass": t for d in DIRTS})
        item_types.update({f"{t}_slime_{k}": t for k in ("leaves", "fern", "tall_grass")})
    item_types.update({"sky_slime_vine": "sky", "ender_slime_vine": "ender"})
    for item, t in item_types.items():
        path = f"assets/{ID}/items/{item}.json"
        doc = load(path)
        node = doc["model"]
        if node.get("type") != "minecraft:model":
            raise SystemExit(f"foliage_colors.py: {item}'s item model is {node.get('type')}, not a plain model")
        node["tints"] = [{"type": "minecraft:constant", "value": ITEM_COLORS[t]}]
        files[path] = json.dumps(doc, indent=1).encode()

    skipped.setdefault("notes", []).append(
        f"slime foliage: blocks tinted at run time from the colormaps (tinting.rs), {len(item_types)} items with "
        "constant tints of FoliageType's colour")
    print(f"foliage: {len(item_types)} tinted items, blocks tinted by the native mod")
