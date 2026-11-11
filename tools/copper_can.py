"""The copper can's look: Tinkers' `tconstruct:fluid_container` model (FluidContainerModel) as 26.3 item models.

Java bakes the can's `base` texture as a plain item layer and, when the can holds a fluid, the fluid's still sprite
(IClientFluidTypeExtensions.getStillTexture, animated) in the shape of the `fluid` mask texture
(UnbakedGeometryHelper.createUnbakedItemMaskElements): the mask's opaque pixels become the quads, the fluid sprite
their texture. The quads are tinted by the fluid's tint colour (when not -1), lit by its light level, and pushed out
a little (FLUID_TRANSFORM, z * 1.002); a fluid lighter than air turns the whole can upside down (`flip_gas`).

Here the same as models: one shared mask model (elements from the mask, the texture `#fluid`; one per light level),
one model per fluid naming its still sprite, and the item definition selects by `minecraft:custom_model_data` string
0, which the native mod sets to the can's fluid on every fill and empty (tconstruct.rs `with_can_fluid`). A can
without one (empty, or a fluid not listed here) is the plain can.

The 70 fluid buckets are the same loader with a fixed `fluid` and Forge's `forge:item/bucket_drip` parent (base
`minecraft:item/bucket`, mask `forge:item/mask/bucket_fluid_drip`), so each bucket's item definition is the one
composite straight away: the vanilla bucket, then that fluid's layer in the drip mask (`write_buckets`).
"""

import io
import json
import re

import smeltery_data
import tool_data

ID = "tconstruct"
CAN = f"{ID}:item/copper_can"
MASK = f"assets/{ID}/textures/item/copper_can_fluid.png"
FOLDER = f"{ID}:item/hz_copper_can"
# Vanilla's two fluids: Forge's water and lava client extensions (the item tint of water: 0x3F76E4; lava's light 15).
VANILLA = {
    "minecraft:water": {"still": "minecraft:block/water_still", "color": 0x3F76E4, "light": 0},
    "minecraft:lava": {"still": "minecraft:block/lava_still", "color": 0xFFFFFF, "light": 15},
}
# FLUID_TRANSFORM; and flip_gas's turn about z.
NONE = [0.0, 0.0, 0.0, 1.0]
FLUID_TRANSFORM = {"translation": [0.0, 0.0, 0.0], "left_rotation": NONE, "scale": [1.0, 1.0, 1.002], "right_rotation": NONE}
# Half a turn about the model's middle, as Java's flip turns the baked quads: the turn about z maps (x, y) to (-x, -y),
# and the translation (applied after it) brings it back to (1 - x, 1 - y) in the 0..1 model space.
FLIP = {"translation": [1.0, 1.0, 0.0], "left_rotation": [0.0, 0.0, 1.0, 0.0], "scale": [1.0, 1.0, 1.0], "right_rotation": NONE}


def _mask_elements(png, light):
    """createUnbakedItemMaskElements: the mask's edge faces (ItemModelGenerator's, as tool_data._extruded makes
    them) and its opaque pixels as front and back rectangles, each row's run grown down while the rows below are
    opaque under it; every face the fluid sprite (`#fluid`), tint index 0, lit by `light`."""
    from PIL import Image
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    w, h = image.size
    alpha = image.getchannel("A").load()
    opaque = {(x, y) for y in range(h) for x in range(w) if alpha[x, y] != 0}
    face = {"texture": "#fluid", "tintindex": 0}
    out = []
    for e in tool_data._extruded(png, None, light)[1:]:
        for f in e["faces"].values():
            f.update(face)
        if not light:
            e.pop("light_emission", None)
        out.append(e)
    r = lambda v: round(v, 4)  # noqa: E731
    for y in range(h):
        x = 0
        while x < w:
            if (x, y) not in opaque:
                x += 1
                continue
            start = x
            while x < w and (x, y) in opaque:
                x += 1
            end = y + 1
            while end < h and all((i, end) in opaque for i in range(start, x)):
                end += 1
            for row in range(y, end):
                for i in range(start, x):
                    opaque.discard((i, row))
            x0, x1, y0, y1 = 16 * start / w, 16 * x / w, 16 * y / h, 16 * end / h
            element = {"from": [r(x0), r(16 - y1), 7.5], "to": [r(x1), r(16 - y0), 8.5],
                       "faces": {"south": {**face, "uv": [r(x0), r(y0), r(x1), r(y1)]},
                                 "north": {**face, "uv": [r(x1), r(y0), r(x0), r(y1)]}}}
            if light:
                element["light_emission"] = light
            out.append(element)
    return out


def _gases():
    """The fluids lighter than air (FluidType density <= 0: TinkerFluids' `density(-...)`)."""
    try:
        text = smeltery_data.DECOMP_FLUIDS.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return {f"{ID}:{name}" for _, name, rest in re.findall(r'\b(hot|cool|slime)\("(\w+)"\)([^\n]*)', text)
            if re.search(r"density\(-\d", rest)}


def _fluids(jar):
    """Each fluid's still sprite, tint (RGB, white for none) and light: Mantle's fluid_texture files, as the
    smeltery's fluid table reads them, and vanilla's two."""
    light, _ = smeltery_data.fluid_props()
    out = dict(VANILLA)
    for name in sorted(jar.namelist()):
        m = re.match(rf"assets/{ID}/mantle/fluid_texture/(\w+)\.json$", name)
        if not m:
            continue
        try:
            doc = json.loads(jar.read(name).decode("utf-8-sig"))
        except ValueError:
            continue
        still = doc.get("still", "").replace(f"{ID}:fluid/", f"{ID}:block/fluid/", 1)
        if not still:
            continue
        fluid = f"{ID}:{m.group(1)}"
        color = int(doc.get("color", "FFFFFFFF"), 16)
        out[fluid] = {"still": still, "color": 0xFFFFFF if color == 0xFFFFFFFF else color & 0xFFFFFF,
                      "light": light.get(fluid, 0)}
    return out


def _layers(files, fluids, mask, folder):
    """Each fluid's layer in `mask`'s shape: the shared mask models (`folder`/fluid[_glowN], one per light level),
    one model per fluid naming its still sprite, and the item model node drawing it (FLUID_TRANSFORM, the tint)."""
    parents = {}
    out = {}
    for fluid, info in sorted(fluids.items()):
        light = info["light"]
        if light not in parents:
            parent = f"{folder}/fluid" + (f"_glow{light}" if light else "")
            doc = {"parent": "minecraft:item/generated", "textures": {"particle": "#fluid"},
                   "elements": _mask_elements(mask, light)}
            files[f"assets/{ID}/models/{parent.split(':', 1)[1]}.json"] = json.dumps(doc, separators=(",", ":")).encode()
            parents[light] = parent
        ns, path = fluid.split(":", 1)
        model = f"{folder}/{path if ns == ID else f'{ns}_{path}'}"
        files[f"assets/{ID}/models/{model.split(':', 1)[1]}.json"] = json.dumps(
            {"parent": parents[light], "textures": {"fluid": info["still"]}}, indent=1).encode()
        layer = {"type": "minecraft:model", "model": model, "transformation": FLUID_TRANSFORM}
        if info["color"] != 0xFFFFFF:
            layer["tints"] = [{"type": "minecraft:constant", "value": info["color"]}]
        out[fluid] = layer
    return out, len(parents)


def write(files, jar):
    names = set(jar.namelist())
    if MASK not in names:
        print("copper can: no fluid mask, the can stays plain")
        return
    fluids = _fluids(jar)
    gases = _gases()
    layers, levels = _layers(files, fluids, jar.read(MASK), FOLDER)
    can = {"type": "minecraft:model", "model": CAN}
    cases = []
    for fluid, layer in layers.items():
        node = {"type": "minecraft:composite", "models": [can, layer]}
        if fluid in gases:
            node["transformation"] = FLIP
        cases.append({"when": fluid, "model": node})
    files[f"assets/{ID}/items/copper_can.json"] = json.dumps(
        {"model": {"type": "minecraft:select", "property": "minecraft:custom_model_data", "index": 0,
                   "cases": cases, "fallback": can}}, indent=1).encode()
    print(f"copper can: {len(cases)} fluids, {levels} light levels, {len(gases & set(fluids))} upside down")


# Forge's `forge:item/mask/bucket_fluid_drip` (16x16; `#` is the fluid). Forge isn't here, so it is derived from 26.3's
# vanilla textures (`derive_drip_mask`): the pixels where `item/water_bucket` or `item/lava_bucket` differ from
# `item/bucket` and the filled colour is not grey. Water fills the bucket's mouth (rows 2-5); lava adds the deeper
# rows and its drips down the right side (x 10, rows 7 and 9). The grey test drops the rim pixels lava_bucket merely
# reshades (x 3 and 12 of row 5, x 12 of row 7), which are the bucket's, not the fluid's.
DRIP_MASK = (
    "................",
    "................",
    ".....######.....",
    "...##########...",
    "...##########...",
    "....########....",
    ".....######.....",
    "..........#.....",
    "................",
    "..........#.....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
)
BUCKET = "minecraft:item/bucket"


def derive_drip_mask(client_jar):
    """The rows of DRIP_MASK from a vanilla client jar (run this module with the jar's path to print them)."""
    import zipfile
    from PIL import Image
    with zipfile.ZipFile(client_jar) as j:
        def load(name):
            return Image.open(io.BytesIO(j.read(f"assets/minecraft/textures/item/{name}.png"))).convert("RGBA")
        empty, filled = load("bucket"), [load("water_bucket"), load("lava_bucket")]
    w, h = empty.size

    def fluid(x, y):
        return any(f.getpixel((x, y)) != empty.getpixel((x, y)) and len(set(f.getpixel((x, y))[:3])) > 1
                   for f in filled)
    return tuple("".join("#" if fluid(x, y) else "." for x in range(w)) for y in range(h))


def _drip_png():
    from PIL import Image
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(DRIP_MASK):
        for x, c in enumerate(row):
            if c == "#":
                image.putpixel((x, y), (255, 255, 255, 255))
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()


def _bucket_fluids(jar):
    """The items whose model is FluidContainerModel over Forge's drip bucket with a fixed fluid: {item: (fluid,
    flip_gas)} (flip_gas defaults to true, as FluidContainerModel.deserialize reads it)."""
    out = {}
    for name in sorted(jar.namelist()):
        m = re.match(rf"assets/{ID}/models/item/(\w+)\.json$", name)
        if not m:
            continue
        try:
            doc = json.loads(jar.read(name).decode("utf-8-sig"))
        except ValueError:
            continue
        if doc.get("loader") != f"{ID}:fluid_container" or "fluid" not in doc:
            continue
        if doc.get("parent") != "forge:item/bucket_drip":
            print(f"fluid buckets: {m.group(1)} has parent {doc.get('parent')}, left as it is")
            continue
        fluid = doc["fluid"]
        if isinstance(fluid, dict):
            fluid = fluid.get("name", "")
        out[m.group(1)] = (fluid if ":" in fluid else f"minecraft:{fluid}", bool(doc.get("flip_gas", True)))
    return out


def write_buckets(files, jar):
    """Each fluid bucket's item definition: the vanilla bucket and its fluid's layer in the drip mask, turned upside
    down when `flip_gas` and the fluid is lighter than air."""
    buckets = _bucket_fluids(jar)
    fluids = _fluids(jar)
    missing = sorted(i for i, (f, _) in buckets.items() if f not in fluids)
    for item in missing:
        print(f"fluid buckets: {item}'s fluid {buckets[item][0]} has no still texture, the bucket stays plain")
    wanted = {f for i, (f, _) in buckets.items() if i not in missing}
    layers, levels = _layers(files, {f: fluids[f] for f in wanted}, _drip_png(), f"{ID}:item/hz_bucket")
    gases = _gases()
    flipped = 0
    for item, (fluid, flip_gas) in buckets.items():
        if item in missing:
            continue
        node = {"type": "minecraft:composite", "models": [{"type": "minecraft:model", "model": BUCKET}, layers[fluid]]}
        if flip_gas and fluid in gases:
            node["transformation"] = FLIP
            flipped += 1
        files[f"assets/{ID}/items/{item}.json"] = json.dumps({"model": node}, indent=1).encode()
    print(f"fluid buckets: {len(buckets) - len(missing)} of {len(buckets)} drawn with their fluid, {levels} light "
          f"levels, {flipped} upside down")


if __name__ == "__main__":
    import sys
    print("\n".join(f'    "{row}",' for row in derive_drip_mask(sys.argv[1])))
