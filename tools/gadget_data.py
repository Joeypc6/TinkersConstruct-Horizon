"""The gadgets' content (spec-gadgets.md G.5-G.10): declarations make_content.py's families don't get right.

`write(files)` runs after make_content has declared every block and item, and replaces the declarations of punji
sticks, the glow block, the platforms and the cakes, sets the gadget items' stack sizes, and adds the gadgets' mob
effects and thrown entity types. The behaviour is the native mod's (tconstruct.rs, "Gadgets").
"""

import json

ID = "tconstruct"
PX = 1 / 16

DIRECTIONS = ["down", "up", "north", "east", "south", "west"]

# PunjiBlock.BOUNDS (getShape, also its collision), by `facing`.
PUNJI_SHAPES = {
    "down": [[0.1875, 0.0, 0.1875, 0.8125, 0.375, 0.8125]],
    "up": [[0.1875, 0.625, 0.1875, 0.8125, 1.0, 0.8125]],
    "north": [[0.1875, 0.1875, 0.0, 0.8125, 0.8125, 0.375]],
    "south": [[0.1875, 0.1875, 0.625, 0.8125, 0.8125, 1.0]],
    "east": [[0.625, 0.1875, 0.1875, 1.0, 0.8125, 0.8125]],
    "west": [[0.0, 0.1875, 0.1875, 0.375, 0.8125, 0.8125]],
}
# GlowBlock.BOUNDS: a 1 px slab on the side it is stuck to; no collision.
GLOW_SHAPES = {
    "up": [[0.0, 15 * PX, 0.0, 1.0, 1.0, 1.0]],
    "down": [[0.0, 0.0, 0.0, 1.0, PX, 1.0]],
    "north": [[0.0, 0.0, 0.0, 1.0, 1.0, PX]],
    "south": [[0.0, 0.0, 15 * PX, 1.0, 1.0, 1.0]],
    "east": [[15 * PX, 0.0, 0.0, 1.0, 1.0, 1.0]],
    "west": [[0.0, 0.0, 0.0, PX, 1.0, 1.0]],
}

# TinkerCommons: (hardness, explosion resistance) of each platform.
PLATFORMS = {"gold_platform": (3.0, 6.0), "iron_platform": (5.0, 6.0), "cobalt_platform": (5.0, 5.0)}
for _waxed in ("", "waxed_"):
    for _age in ("", "exposed_", "weathered_", "oxidized_"):
        PLATFORMS[f"{_waxed}{_age}copper_platform"] = (3.0, 6.0)

CAKES = ("earth_cake", "sky_cake", "ichor_cake", "ender_cake", "blood_cake", "magma_cake")

# Stack sizes (TinkerGadgets): the backpack, the stands and the throwables 16.
STACK_16 = ("piggy_backpack", "bamboo_armor_stand", "bone_armor_stand", "necrotic_bone_armor_stand",
            "clear_armor_stand", "glow_ball", "efln_ball", "quartz_shuriken", "flint_shuriken")

# TinkerGadgets.carryEffect, TinkerEffects (bouncy, double_jump, antigravity, returning): category and colour.
EFFECTS = {"carry": ("neutral", 0xFFFFFF), "bouncy": ("beneficial", 7449699), "double_jump": ("beneficial", 11115399),
           "antigravity": ("harmful", 16750349), "returning": ("neutral", 11087359)}

# The deprecated throwables as copies of the snowball: their item and the damage of a hit (ShurikenEntityBase).
THROWN = {"glow_ball": 0.0, "efln_ball": 0.0, "quartz_shuriken": 5.0, "flint_shuriken": 3.0}


def platform_shapes():
    """PlatformBlock.SHAPES: corner posts, the top plate unless `up`, the bottom one unless `down`, a side plate for
    each connected side."""
    posts = [[0, 0, 0, 2 * PX, 1, 2 * PX], [14 * PX, 0, 0, 1, 1, 2 * PX], [0, 0, 14 * PX, 2 * PX, 1, 1],
             [14 * PX, 0, 14 * PX, 1, 1, 1]]
    plates = {"north": [0, 2 * PX, 0, 1, 14 * PX, PX], "south": [0, 2 * PX, 15 * PX, 1, 14 * PX, 1],
              "west": [0, 2 * PX, 0, PX, 14 * PX, 1], "east": [15 * PX, 2 * PX, 0, 1, 14 * PX, 1]}
    values = {}
    for i in range(64):
        up, down, north, east, south, west = ((i >> b) & 1 == 1 for b in range(6))
        boxes = [list(b) for b in posts]
        if not up:
            boxes.append([0, 14 * PX, 0, 1, 1, 1])
        if not down:
            boxes.append([0, 0, 0, 1, 2 * PX, 1])
        for side, on in (("north", north), ("east", east), ("south", south), ("west", west)):
            if on:
                boxes.append(plates[side])
        key = ",".join("true" if v else "false" for v in (up, down, north, east, south, west))
        values[key] = boxes
    return {"properties": ["up", "down", "north", "east", "south", "west"], "values": values}


def bools(*names):
    return {n: {"type": "boolean"} for n in names}


def decl(files, name, doc):
    files[f"data/{ID}/horizon/block/{name}.json"] = json.dumps(doc, indent=1).encode()


def write(files):
    decl(files, "punji", {
        "template": "minecraft:heavy_core",
        "properties": {"hardness": 3.0, "explosion_resistance": 3.0, "sounds": "minecraft:short_grass",
                       "requires_tool": False, "light": 0, "occludes": False},
        "state_properties": {"facing": {"type": "enum", "values": DIRECTIONS}, **bools("north", "east", "northeast", "northwest")},
        "default_state": {"facing": "down", "north": "false", "east": "false", "northeast": "false", "northwest": "false"},
        "shapes": {"property": "facing", "values": PUNJI_SHAPES},
    })
    decl(files, "glow", {
        "template": "minecraft:structure_void",
        "properties": {"hardness": 0.0, "explosion_resistance": 0.0, "light": 14, "sounds": "minecraft:white_wool",
                       "render_shape": "MODEL", "occludes": False},
        "state_properties": {"facing": {"type": "enum", "values": DIRECTIONS}},
        "default_state": {"facing": "down"},
        "shapes": {"property": "facing", "values": GLOW_SHAPES},
        "collision_shapes": {"default": []},
    })
    shapes = platform_shapes()
    for name, (hardness, resistance) in PLATFORMS.items():
        doc = {
            "template": "minecraft:heavy_core",
            "properties": {"hardness": hardness, "explosion_resistance": resistance, "sounds": "minecraft:copper_block",
                           "requires_tool": True, "light": 0, "occludes": False},
            "state_properties": bools("up", "down", "north", "east", "south", "west"),
            "default_state": {d: "false" for d in ("up", "down", "north", "east", "south", "west")},
            "shapes": shapes,
        }
        # WeatheringPlatformBlock: the unwaxed copper ones age by random ticks, the oxidized one no further.
        if name.endswith("copper_platform") and not name.startswith("waxed_") and not name.startswith("oxidized_"):
            doc["properties"]["random_ticks"] = True
        decl(files, name, doc)
    for name in CAKES:
        path = f"data/{ID}/horizon/block/{name}.json"
        doc = json.loads(files[path]) if path in files else {"template": "minecraft:cake"}
        doc["template"] = "minecraft:cake"
        doc.setdefault("properties", {}).update({"hardness": 0.5, "explosion_resistance": 0.5,
                                                 "sounds": "minecraft:white_wool"})
        doc["components"] = {"minecraft:max_stack_size": 1}
        if name == "ichor_cake":
            # InvertedCakeBlock.SHAPE_BY_BITE: hanging from the ceiling, eaten from the west.
            doc["shapes"] = {"property": "bites", "values": {
                str(b): [[(1 + 2 * b) * PX, 0.5, PX, 15 * PX, 1.0, 15 * PX]] for b in range(7)}}
        decl(files, name, doc)
    for item in STACK_16:
        files[f"data/{ID}/horizon/item/{item}.json"] = json.dumps({"template": "minecraft:paper", "max_stack_size": 16},
                                                                  indent=1).encode()
    for name, (category, color) in EFFECTS.items():
        files[f"data/{ID}/horizon/mob_effect/{name}.json"] = json.dumps({"category": category, "color": color}).encode()
    for name, damage in THROWN.items():
        files[f"data/{ID}/horizon/entity_type/{name}.json"] = json.dumps(
            {"template": "minecraft:snowball", "item": f"{ID}:{name}", "damage": damage}).encode()
