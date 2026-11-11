"""Tinkers' mob heads as block and item models (WorldClientEvents.registerRenderers / clientSetup).

Java draws them with SkullBlockRenderer: a SkullModel (or PiglinHeadModel) of a layer Tinkers registers, with the mob's
texture. Horizon draws only vanilla's skull kinds there, so the heads were invisible. Here each head's layer is turned
into a JSON model with the same quads and UVs, one element per quad, for every placement SkullBlockRenderer has: the
16 floor rotations (translate (0.5, 0, 0.5), the head's yRot = rotation x 22.5) and the 4 wall facings (translate
(0.5 - step x 0.25, 0.25, 0.5 - step z 0.25)), and the item (vanilla's skull item transform: (0.5, 0, 0.5), then 180
degrees about X; vanilla's template_skull display).

Layers (WorldClientEvents.registerRenderers):
- blaze: SkullModel.createMobHeadLayer, vanilla's `skeleton_skull#main`;
- piglin_brute, zombified_piglin: PiglinHeadModel, vanilla's `piglin_head#main`;
- enderman: SkullModelHelper.createHeadLayer(0, 0, 32, 16); husk: (0, 0, 64, 64); spider and cave_spider:
  (32, 4, 64, 32); stray and drowned: createHeadHatLayer(0, 16, 32, 32), the head at 0, 0 and the hat at 0, 16 grown
  by 0.25.
Vanilla's layers are read from the prepared game (`entity-models.json`); the box UVs of the others follow
ModelPart.Cube, checked against vanilla's skeleton layer (`box_polygons` reproduces it).

The textures (vanilla's mobs' and Tinkers' entity/skull ones) are added to the blocks atlas as `single` sources, so
the models can use them; vanilla's are referenced, never copied.

Usage (from make_content.py): heads.write(files, skipped)
"""

import glob
import json
import math

ID = "tconstruct"

# (layer, texture, the texture's size for a built layer)
HEADS = {
    "blaze": (("vanilla", "minecraft:skeleton_skull#main"), "minecraft:entity/blaze/blaze"),
    "enderman": (("box", [(0, 0, 0.0)], 32, 16), f"{ID}:entity/skull/enderman"),
    "stray": (("box", [(0, 0, 0.0), (0, 16, 0.25)], 32, 32), f"{ID}:entity/skull/stray"),
    "husk": (("box", [(0, 0, 0.0)], 64, 64), "minecraft:entity/zombie/husk"),
    "drowned": (("box", [(0, 0, 0.0), (0, 16, 0.25)], 32, 32), f"{ID}:entity/skull/drowned"),
    "spider": (("box", [(32, 4, 0.0)], 64, 32), "minecraft:entity/spider/spider"),
    "cave_spider": (("box", [(32, 4, 0.0)], 64, 32), "minecraft:entity/spider/cave_spider"),
    "piglin_brute": (("vanilla", "minecraft:piglin_head#main"), "minecraft:entity/piglin/piglin_brute"),
    "zombified_piglin": (("vanilla", "minecraft:piglin_head#main"), "minecraft:entity/piglin/zombified_piglin"),
}

# Vanilla's models/item/template_skull.json display (the skull items' base model).
SKULL_DISPLAY = {
    "gui": {"rotation": [30, 45, 0], "translation": [0, 3, 0], "scale": [1, 1, 1]},
    "fixed": {"rotation": [0, 180, 0], "translation": [0, 4, 0], "scale": [1, 1, 1]},
    "on_shelf": {"rotation": [0, 0, 0], "translation": [0, 8, 0], "scale": [2, 2, 2]},
    "ground": {"rotation": [0, 0, 0], "translation": [0, 3, 0], "scale": [0.5, 0.5, 0.5]},
    "thirdperson_righthand": {"rotation": [45, 45, 0], "translation": [0, 3, 0], "scale": [0.5, 0.5, 0.5]},
}

WALLS = {"north": (0, -1, 180.0), "south": (0, 1, 0.0), "west": (-1, 0, 90.0), "east": (1, 0, 270.0)}


def entity_models():
    for path in sorted(glob.glob("C:/Users/*/AppData/Roaming/horizon-launcher/versions/nightly-*/.local/horizon-client/26.3/entity-models.json"), reverse=True):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    raise SystemExit("entity-models.json of a prepared Nightly is needed for the mob heads")


def box_polygons(x0, y0, z0, w, h, d, u, v, tw, th, grow=0.0):
    """ModelPart.Cube's six quads of a box at (x0, y0, z0) sized w, h, d with texture offset (u, v) on a tw x th
    texture, grown by `grow` (its UVs are the ungrown box's): ([x, y, z, u, v] x 4, normal), as entity-models.json
    stores them."""
    X0, Y0, Z0 = x0 - grow, y0 - grow, z0 - grow
    X1, Y1, Z1 = x0 + w + grow, y0 + h + grow, z0 + d + grow

    def tx(a, lo, hi, size):  # where a point of the grown box falls on the ungrown size
        return (a - lo) / (hi - lo) * size

    out = []

    def quad(points, uvf, normal):
        out.append(([[px, py, pz, uu / tw, vv / th] for (px, py, pz) in points for (uu, vv) in [uvf(px, py, pz)]], normal))

    # top (model y min), bottom (y max), west (x min), north (z min), east (x max), south (z max)
    quad([(X1, Y0, Z1), (X0, Y0, Z1), (X0, Y0, Z0), (X1, Y0, Z0)],
         lambda x, y, z: (u + d + tx(x, X0, X1, w), v + d - tx(z, Z0, Z1, d)), [0.0, -1.0, 0.0])
    quad([(X1, Y1, Z0), (X0, Y1, Z0), (X0, Y1, Z1), (X1, Y1, Z1)],
         lambda x, y, z: (u + d + w + tx(x, X0, X1, w), v + d - tx(z, Z0, Z1, d)), [0.0, 1.0, 0.0])
    quad([(X0, Y0, Z0), (X0, Y0, Z1), (X0, Y1, Z1), (X0, Y1, Z0)],
         lambda x, y, z: (u + d - tx(z, Z0, Z1, d), v + d + tx(y, Y0, Y1, h)), [-1.0, 0.0, 0.0])
    quad([(X1, Y0, Z0), (X0, Y0, Z0), (X0, Y1, Z0), (X1, Y1, Z0)],
         lambda x, y, z: (u + d + tx(x, X0, X1, w), v + d + tx(y, Y0, Y1, h)), [0.0, 0.0, -1.0])
    quad([(X1, Y0, Z1), (X1, Y0, Z0), (X1, Y1, Z0), (X1, Y1, Z1)],
         lambda x, y, z: (u + d + w + tx(z, Z0, Z1, d), v + d + tx(y, Y0, Y1, h)), [1.0, 0.0, 0.0])
    quad([(X0, Y0, Z1), (X1, Y0, Z1), (X1, Y1, Z1), (X0, Y1, Z1)],
         lambda x, y, z: (u + 2 * d + w + tx(X1 - x + X0, X0, X1, w), v + d + tx(y, Y0, Y1, h)), [0.0, 0.0, 1.0])
    return out


def layer_parts(models, layer):
    """[(pose chain, polygons)]: every part of a layer with the poses from the root down, and its quads."""
    if layer[0] == "vanilla":
        root = models[layer[1]]
        out = []

        def walk(part, chain):
            chain = chain + [part["pose"]]
            polys = list(zip(part["polygons"], part.get("normals", [])))
            if polys:
                out.append((chain, polys))
            for child in part.get("children", {}).values():
                walk(child, chain)

        walk(root, [])
        return out
    _, boxes, tw, th = layer
    ident = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
    return [([ident], box_polygons(-4.0, -8.0, -4.0, 8, 8, 8, u, v, tw, th, grow)) for (u, v, grow) in boxes]


# 3x3 matrices as row lists.
def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def apply(m, p):
    return [sum(m[i][k] * p[k] for k in range(3)) for i in range(3)]


def rx(t):
    c, s = math.cos(t), math.sin(t)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def ry(t):
    c, s = math.cos(t), math.sin(t)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def rz(t):
    c, s = math.cos(t), math.sin(t)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def pose_matrix(pose):
    """ModelPart.translateAndRotate: translate by the offset, then rotationZYX(zRot, yRot, xRot)."""
    x, y, z, a, b, c = pose[:6]
    return mul(rz(c), mul(ry(b), rx(a))), [x, y, z]


def euler_xyz(m):
    """Angles (degrees) of Horizon's EulerXyz rotation, Rz(z) . Ry(y) . Rx(x), equal to `m`."""
    sy = -m[2][0]
    sy = max(-1.0, min(1.0, sy))
    y = math.asin(sy)
    if abs(math.cos(y)) > 1e-6:
        x = math.atan2(m[2][1], m[2][2])
        z = math.atan2(m[1][0], m[0][0])
    else:
        x = math.atan2(-m[1][2], m[1][1])
        z = 0.0
    return [round(math.degrees(a), 4) for a in (x, y, z)]


FACE = {(0, -1, 0): "down", (0, 1, 0): "up", (-1, 0, 0): "west", (1, 0, 0): "east", (0, 0, -1): "north", (0, 0, 1): "south"}


def corner(face, lo, hi):
    """The face's top-left and bottom-right corners (box frame) in a JSON model's uv order (BlockElement's defaults)."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    return {
        "north": ((x1, y1, z0), (x0, y0, z0)), "south": ((x0, y1, z1), (x1, y0, z1)),
        "west": ((x0, y1, z0), (x0, y0, z1)), "east": ((x1, y1, z1), (x1, y0, z0)),
        "up": ((x0, y1, z0), (x1, y1, z1)), "down": ((x0, y0, z1), (x1, y0, z0)),
    }[face]


def placement_elements(parts, base, yaw_deg):
    """The JSON elements of a layer placed as SkullBlockRenderer does: world = base + Mirror . Ry(yaw) . chain . p,
    Mirror = scale(-1, -1, 1) (a half turn about Z). One flat element per quad, its box in its part's frame and turned
    there by an Euler rotation about its centre."""
    mirror = rz(math.pi)
    head = mul(mirror, ry(math.radians(yaw_deg)))
    out = []
    for chain, polys in parts:
        rot, off = head, [0.0, 0.0, 0.0]
        for pose in chain:
            m, t = pose_matrix(pose)
            off = [off[i] + apply(rot, t)[i] for i in range(3)]
            rot = mul(rot, m)
        for verts, normal in polys:
            pts = [v[:3] for v in verts]
            lo = [min(p[i] for p in pts) for i in range(3)]
            hi = [max(p[i] for p in pts) for i in range(3)]
            face = FACE[tuple(int(round(n)) for n in normal)]
            tl, br = corner(face, lo, hi)

            def uv_at(c):
                best = min(verts, key=lambda v: sum((v[i] - c[i]) ** 2 for i in range(3)))
                return best[3], best[4]

            (u1, v1), (u2, v2) = uv_at(tl), uv_at(br)
            # Where the element's centre goes: base + off + rot . c (px).
            c = [(lo[i] + hi[i]) / 2 for i in range(3)]
            wc = [base[i] + off[i] + apply(rot, c)[i] for i in range(3)]
            frm = [round(wc[i] + lo[i] - c[i], 4) for i in range(3)]
            to = [round(wc[i] + hi[i] - c[i], 4) for i in range(3)]
            x, y, z = euler_xyz(rot)
            out.append({
                "from": frm, "to": to,
                "rotation": {"origin": [round(v, 4) for v in wc], "x": x, "y": y, "z": z},
                "faces": {face: {"uv": [round(u1 * 16, 4), round(v1 * 16, 4), round(u2 * 16, 4), round(v2 * 16, 4)], "texture": "#skin"}},
            })
    return out


def model(texture, elements, item=False):
    doc = {"textures": {"skin": texture, "particle": texture}, "elements": elements}
    if item:
        doc["display"] = SKULL_DISPLAY
    return json.dumps(doc, indent=1).encode()


def write(files, skipped):
    models = entity_models()
    # The check: the built box reproduces vanilla's skeleton head quad for quad.
    built = box_polygons(-4.0, -8.0, -4.0, 8, 8, 8, 0, 0, 64, 32)
    vanilla = models["minecraft:skeleton_skull#main"]["children"]["head"]["polygons"]
    for (bq, _), vq in zip(built, vanilla):
        for bv, vv in zip(bq, vq):
            if any(abs(a - b) > 1e-4 for a, b in zip(bv, vv)):
                raise SystemExit(f"heads.py: box UVs differ from vanilla's skeleton head: {bv} vs {vv}")
    textures = set()
    for name, (layer, tex) in HEADS.items():
        parts = layer_parts(models, layer)
        textures.add(tex)
        floor = {}
        for r in range(16):
            path = f"block/head/{name}_{r}"
            files[f"assets/{ID}/models/{path}.json"] = model(tex, placement_elements(parts, [8.0, 0.0, 8.0], r * 22.5))
            floor[f"rotation={r}"] = {"model": f"{ID}:{path}"}
        files[f"assets/{ID}/blockstates/{name}_head.json"] = json.dumps({"variants": floor}, indent=1).encode()
        wall = {}
        for facing, (sx, sz, to_yrot) in WALLS.items():
            path = f"block/head/{name}_wall_{facing}"
            base = [8.0 - sx * 4.0, 4.0, 8.0 - sz * 4.0]
            files[f"assets/{ID}/models/{path}.json"] = model(tex, placement_elements(parts, base, (to_yrot + 180.0) % 360.0))
            wall[f"facing={facing}"] = {"model": f"{ID}:{path}"}
        files[f"assets/{ID}/blockstates/{name}_wall_head.json"] = json.dumps({"variants": wall}, indent=1).encode()
        # The item: vanilla's skull item transform, the same as the floor head turned half round.
        files[f"assets/{ID}/models/item/{name}_head.json"] = model(tex, placement_elements(parts, [8.0, 0.0, 8.0], 180.0), item=True)
    # The textures on the blocks atlas, after the sources already there.
    atlas_name = "assets/minecraft/atlases/blocks.json"
    atlas = json.loads(files[atlas_name].decode()) if atlas_name in files else {"sources": []}
    for tex in sorted(textures):
        src = {"type": "minecraft:single", "resource": tex}
        if src not in atlas["sources"]:
            atlas["sources"].append(src)
    files[atlas_name] = json.dumps(atlas, indent=2).encode()
    skipped.setdefault("notes", []).append(f"mob heads: {len(HEADS)} drawn from their layers as block and item models")
