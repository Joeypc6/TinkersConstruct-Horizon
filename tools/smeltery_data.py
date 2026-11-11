"""What the content mod and the native mod need for the melter, the heater and the tanks, from the TConstruct jar.

Called by make_content.py:
- `write(files, jar, fluids_path)` adds the menus (`data/tconstruct/horizon/menu/melter.json`, `heater.json`), copies the
  fluids' textures where the block atlas takes them (`textures/block/fluid/...`; the native mod draws them in the GUI
  and inside the melter and tanks), adds the `c:` item tags the melting recipes name with vanilla's items (Forge's own
  tags, which neither vanilla nor Horizon has), and writes the fluid table the native mod compiles in (`fluids_path`).
- `keeps_conditional` / `conditional`: a `forge:conditional` melting recipe keeps all its alternatives, for the native
  mod to choose from with the game's tags.

The fluid table: each fluid tag resolved to its fluids (Mantle's `FluidOutput` takes a tag's first), each fluid's still
and flowing textures and colour (Mantle's `fluid_texture`), its light and whether it is hot (TinkerFluids, from the
decompiled source when it is there), its bucket, and Mantle's fluid tooltip unit lists (`mantle/fluid_tooltips`).
"""

import json
import pathlib
import re

ID = "tconstruct"
MELTING_TYPES = {"tconstruct:melting", "tconstruct:ore_melting", "tconstruct:damagable_melting",
                 "tconstruct:material_melting", "tconstruct:melting_fuel",
                 # The casting kinds the native mod reads (spec-casting.md).
                 "tconstruct:casting_table", "tconstruct:casting_basin", "tconstruct:retextured_casting_table",
                 "tconstruct:retextured_casting_basin", "tconstruct:table_duplication", "tconstruct:basin_duplication",
                 "tconstruct:table_filling", "tconstruct:basin_filling", "tconstruct:molding_table",
                 # The smeltery's (spec-smeltery.md): netherite's alloy is a `tconstruct:config` conditional.
                 "tconstruct:alloy", "tconstruct:entity_melting",
                 # Materials and tool parts (spec-tools.md 2.3): material values, the part builder, material casting.
                 "tconstruct:material", "tconstruct:material_fluid", "tconstruct:part_builder",
                 "tconstruct:item_part_builder", "tconstruct:part_builder_tool_recycling",
                 "tconstruct:table_casting_material", "tconstruct:basin_casting_material",
                 "tconstruct:table_casting_composite", "tconstruct:basin_casting_composite"}


def _px(*b):
    return [round(v / 16, 5) for v in b]


# The casting blocks' outlines and collisions (FaucetBlock, CastingTableBlock, CastingBasinBlock, ChannelBlock), their
# outer boxes: Horizon's shapes are boxes, and the cut-outs inside them are left whole.
_FAUCET = {"down": [_px(4, 10, 4, 12, 16, 12)], "north": [_px(4, 4, 10, 12, 10, 16)], "south": [_px(4, 4, 0, 12, 10, 6)],
           "west": [_px(10, 4, 4, 16, 10, 12)], "east": [_px(0, 4, 4, 6, 10, 12)]}
_TABLE = [_px(0, 10, 0, 16, 16, 16), _px(0, 0, 0, 4, 10, 4), _px(12, 0, 0, 16, 10, 4), _px(0, 0, 12, 4, 10, 16),
          _px(12, 0, 12, 16, 10, 16)]
_BASIN = [_px(0, 2, 0, 16, 4, 16), _px(0, 4, 0, 2, 16, 16), _px(14, 4, 0, 16, 16, 16), _px(2, 4, 0, 14, 16, 2),
          _px(2, 4, 14, 14, 16, 16), _px(0, 0, 0, 5, 2, 5), _px(11, 0, 0, 16, 2, 5), _px(0, 0, 11, 5, 2, 16),
          _px(11, 0, 11, 16, 2, 16)]
_ARMS = {"north": _px(4, 4, 0, 12, 9, 4), "south": _px(4, 4, 12, 12, 9, 16), "west": _px(0, 4, 4, 4, 9, 12),
         "east": _px(12, 4, 4, 16, 9, 12)}


def _channel_shapes():
    values = {}
    sides = ["north", "south", "west", "east"]
    for down in ("false", "true"):
        for combo in range(81):
            states = [["none", "in", "out"][(combo // 3 ** i) % 3] for i in range(4)]
            boxes = [_px(4, 2 if down == "true" else 4, 4, 12, 9, 12)]
            boxes += [_ARMS[s] for s, v in zip(sides, states) if v != "none"]
            values[",".join([down] + states)] = boxes
    return {"properties": ["down"] + sides, "values": values}


# The smeltery's and foundry's controllers and IO blocks (TinkerSmeltery): the controllers 8 / 28 (seared, metal) and
# 9 / 35 (scorched); the drains, ducts and chutes searedSolidProps(2) 6 / 18 and, by the unused scorchedSolidProps(3)
# the decompiled code sits beside, 7.5 / 24 (spec-smeltery.md 11.4).
STRUCTURE_PROPS = {
    "smeltery_controller": (8.0, 28.0, "minecraft:iron_block"),
    "foundry_controller": (9.0, 35.0, "minecraft:basalt"),
    "seared_drain": (6.0, 18.0, "minecraft:iron_block"), "seared_duct": (6.0, 18.0, "minecraft:iron_block"),
    "seared_chute": (6.0, 18.0, "minecraft:iron_block"),
    "scorched_drain": (7.5, 24.0, "minecraft:basalt"), "scorched_duct": (7.5, 24.0, "minecraft:basalt"),
    "scorched_chute": (7.5, 24.0, "minecraft:basalt"),
}


# The blocks lit 13 while `active` (TinkerSmeltery: the `seared` and `searedBlock` controller properties,
# `lightLevel(s -> s.getValue(ACTIVE) ? 13 : 0)`). A declaration has one light level, so they copy the furnace, whose
# `lit=true` states give 13 and `lit=false` 0; the native mod keeps `lit` equal to `active` (spec-smeltery.md 12.1).
LIT_CONTROLLERS = ("seared_melter", "seared_heater", "smeltery_controller", "foundry_controller", "scorched_alloyer")


def lit_decl(name, decl):
    """A lit controller on the furnace's template: its `facing` (north, south, west, east, as ControllerBlock's) and
    `lit` are the template's, so neither is declared; no light of its own."""
    if name not in LIT_CONTROLLERS:
        return decl
    decl["template"] = "minecraft:furnace"
    decl.setdefault("properties", {}).pop("light", None)
    props = {k: v for k, v in decl.get("state_properties", {}).items() if k not in ("facing", "lit")}
    # The alloyer's block state file names only facing and in_structure; ControllerBlock has `active` all the same.
    props.setdefault("active", {"type": "boolean"})
    props.setdefault("in_structure", {"type": "boolean"})
    decl["state_properties"] = props
    decl["default_state"] = {k: "false" for k in props}
    return decl


def casting_decl(name, decl):
    """The faucets, casting tables and basins, channels and the casting tank (TinkerSmeltery: searedNonSolidProps /
    scorchedNonSolidProps): seared 3 / 9 with metal's sounds, scorched 2.5 / 8 with basalt's; no occlusion; the
    states the native mod sets (`has_item`, a channel's `powered`) and the shapes. The smeltery's controllers and IO
    blocks: their strength, and `in_structure` (and the controllers' `active`) off until a structure forms."""
    if name == "scorched_alloyer":
        # TinkerSmeltery: searedBlock (9 / 35, basalt's sounds) with noOcclusion.
        decl["properties"] = {"hardness": 9.0, "explosion_resistance": 35.0, "sounds": "minecraft:basalt",
                              "requires_tool": True, "occludes": False}
        return lit_decl(name, decl)
    if name in STRUCTURE_PROPS:
        hardness, resistance, sounds = STRUCTURE_PROPS[name]
        decl["properties"] = {"hardness": hardness, "explosion_resistance": resistance, "sounds": sounds,
                              "requires_tool": True, "light": 0}
        default = decl.setdefault("default_state", {})
        for k in ("in_structure", "active"):
            if k in decl.get("state_properties", {}):
                default[k] = "false"
        return lit_decl(name, decl)
    kinds = ("_faucet", "_table", "_basin", "_channel", "_casting_tank")
    if not name.startswith(("seared_", "scorched_")) or not name.endswith(kinds):
        return decl
    scorched = name.startswith("scorched_")
    decl["properties"] = {"hardness": 2.5 if scorched else 3.0, "explosion_resistance": 8.0 if scorched else 9.0,
                          "sounds": "minecraft:basalt" if scorched else "minecraft:iron_block", "requires_tool": True,
                          "light": 0, "occludes": False}
    props = decl.setdefault("state_properties", {})
    default = decl.setdefault("default_state", {})
    if name.endswith(("_table", "_basin")):
        props.setdefault("has_item", {"type": "boolean"})
        default.setdefault("has_item", "false")
        shape = {"default": _TABLE if name.endswith("_table") else _BASIN}
    elif name.endswith("_channel"):
        props.setdefault("powered", {"type": "boolean"})
        default.setdefault("powered", "false")
        shape = _channel_shapes()
    elif name.endswith("_faucet"):
        shape = {"property": "facing", "values": _FAUCET}
    else:
        shape = None
    if shape:
        decl["shapes"] = shape
        decl["collision_shapes"] = shape
    return decl
MANTLE_JAR = pathlib.Path(__file__).resolve().parent.parent.parent / "deps" / "mantle" / "Mantle-1.20.1-1.11.128.jar"
DECOMP_FLUIDS = pathlib.Path(r"Z:\AE2Converter-build\ref\decomp\tconstruct\src\slimeknights\tconstruct\fluids\TinkerFluids.java")

# Forge 1.20.1's tags with vanilla's members, as `c:` tags (the melting recipes name them: iron ingots, raw gold...).
C_TAGS = {
    "ingots/iron": ["minecraft:iron_ingot"], "ingots/gold": ["minecraft:gold_ingot"],
    "ingots/copper": ["minecraft:copper_ingot"], "ingots/netherite": ["minecraft:netherite_ingot"],
    "nuggets/iron": ["minecraft:iron_nugget"], "nuggets/gold": ["minecraft:gold_nugget"],
    "raw_materials/iron": ["minecraft:raw_iron"], "raw_materials/gold": ["minecraft:raw_gold"],
    "raw_materials/copper": ["minecraft:raw_copper"],
    "storage_blocks/iron": ["minecraft:iron_block"], "storage_blocks/gold": ["minecraft:gold_block"],
    "storage_blocks/copper": ["minecraft:copper_block"], "storage_blocks/diamond": ["minecraft:diamond_block"],
    "storage_blocks/emerald": ["minecraft:emerald_block"], "storage_blocks/netherite": ["minecraft:netherite_block"],
    "storage_blocks/quartz": ["minecraft:quartz_block"], "storage_blocks/amethyst": ["minecraft:amethyst_block"],
    "storage_blocks/raw_iron": ["minecraft:raw_iron_block"], "storage_blocks/raw_gold": ["minecraft:raw_gold_block"],
    "storage_blocks/raw_copper": ["minecraft:raw_copper_block"],
    "gems/diamond": ["minecraft:diamond"], "gems/emerald": ["minecraft:emerald"], "gems/quartz": ["minecraft:quartz"],
    "gems/amethyst": ["minecraft:amethyst_shard"],
    "ores/iron": ["minecraft:iron_ore", "minecraft:deepslate_iron_ore"],
    "ores/gold": ["minecraft:gold_ore", "minecraft:deepslate_gold_ore", "minecraft:nether_gold_ore"],
    "ores/copper": ["minecraft:copper_ore", "minecraft:deepslate_copper_ore"],
    "ores/diamond": ["minecraft:diamond_ore", "minecraft:deepslate_diamond_ore"],
    "ores/emerald": ["minecraft:emerald_ore", "minecraft:deepslate_emerald_ore"],
    "ores/quartz": ["minecraft:nether_quartz_ore"], "ores/netherite_scrap": ["minecraft:ancient_debris"],
    "obsidian": ["minecraft:obsidian"], "ender_pearls": ["minecraft:ender_pearl"],
    "mushrooms": ["minecraft:brown_mushroom", "minecraft:red_mushroom"],
}

# Mantle 1.11's own fluid tooltip lists and fluid tags (assets/mantle/mantle/fluid_tooltips, data/mantle/tags/fluids).
MANTLE_LISTS = {
    "mantle:buckets": {"units": [["gui.mantle.fluid.bucket", 1000]]},
    "mantle:fallback": {"redirect": "mantle:buckets"},
    "mantle:honey": {"tag": "c:honey", "units": [["gui.mantle.fluid.bucket", 1000], ["gui.mantle.fluid.bottle", 250],
                                                 ["gui.mantle.fluid.sip", 50]]},
    "mantle:potion": {"tag": "c:potion", "units": [["gui.mantle.fluid.bottle", 250], ["gui.mantle.fluid.sip", 50]]},
    "mantle:soup": {"tag": "mantle:soup", "units": [["gui.mantle.fluid.bowl", 250], ["gui.mantle.fluid.sip", 50]]},
    "mantle:water": {"tag": "mantle:water", "units": [["gui.mantle.fluid.bucket", 1000], ["gui.mantle.fluid.bottle", 250],
                                                      ["gui.mantle.fluid.drop", 50]]},
}
MANTLE_TAGS = {
    "mantle:water": ["minecraft:water", "minecraft:flowing_water"],
    "mantle:lava": ["minecraft:lava", "minecraft:flowing_lava"],
    "mantle:soup": ["#c:beetroot_soup", "#c:mushroom_stew", "#c:rabbit_stew"],
    "minecraft:water": ["minecraft:water", "minecraft:flowing_water"],
    "minecraft:lava": ["minecraft:lava", "minecraft:flowing_lava"],
}


def keeps_conditional(doc):
    return any(isinstance(e.get("recipe"), dict) and e["recipe"].get("type") in MELTING_TYPES
               for e in doc.get("recipes", []))


def conditional(doc):
    entries = [e for e in doc.get("recipes", []) if isinstance(e.get("recipe"), dict)]
    return {"type": entries[0]["recipe"]["type"],
            "hz_conditional": [{"conditions": e.get("conditions", []), "recipe": e["recipe"]} for e in entries]}


def _json(jar, name):
    try:
        return json.loads(jar.read(name).decode("utf-8-sig"))
    except (KeyError, ValueError):
        return None


def _c(tag):
    return tag.replace("forge:", "c:", 1) if tag.startswith("forge:") else tag


def fluid_tags(jar):
    """Every fluid tag of the jar (Forge's as `c:`) and Mantle's and vanilla's, as its raw values."""
    tags = {k: list(v) for k, v in MANTLE_TAGS.items()}
    for name in jar.namelist():
        m = re.match(r"data/([^/]+)/tags/fluids/(.+)\.json$", name)
        if not m:
            continue
        doc = _json(jar, name) or {}
        values = []
        for v in doc.get("values", []):
            v = v["id"] if isinstance(v, dict) else v
            values.append("#" + _c(v[1:]) if v.startswith("#") else _c(v))
        tag = f"{_c(m.group(1) + ':')}{m.group(2)}"
        tags.setdefault(tag, [])
        tags[tag] += [v for v in values if v not in tags[tag]]
    return tags


def resolve(tags, tag, known, seen=None):
    seen = seen if seen is not None else set()
    if tag in seen:
        return []
    seen.add(tag)
    out = []
    for v in tags.get(tag, []):
        for f in (resolve(tags, v[1:], known, seen) if v.startswith("#") else [v]):
            if f in known and f not in out:
                out.append(f)
    return out


def fluid_props():
    """Each Tinkers fluid's light level and whether it is hot (TinkerFluids: `hot(...)` / `cool(...)`)."""
    light, hot = {}, set()
    try:
        text = DECOMP_FLUIDS.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return light, hot
    for kind, name, rest in re.findall(r'\b(hot|cool|slime)\("(\w+)"\)([^\n]*)', text):
        m = re.search(r"lightLevel\((\d+)\)", rest)
        if m:
            light[f"{ID}:{name}"] = int(m.group(1))
        if kind == "hot":
            hot.add(f"{ID}:{name}")
    return light, hot


# Vanilla's entity type tags the entity melting recipes reach through Tinkers' own (26.3's members).
VANILLA_ENTITY_TAGS = {
    "minecraft:skeletons": ["minecraft:skeleton", "minecraft:stray", "minecraft:wither_skeleton", "minecraft:bogged"],
}


def entity_tags(jar):
    """Every entity type tag of the jar (Forge's as `c:`) with vanilla's skeletons, resolved to entity types."""
    raw = {k: list(v) for k, v in VANILLA_ENTITY_TAGS.items()}
    for name in jar.namelist():
        m = re.match(r"data/([^/]+)/tags/entity_types/(.+)\.json$", name)
        if not m:
            continue
        doc = _json(jar, name) or {}
        values = []
        for v in doc.get("values", []):
            v = v["id"] if isinstance(v, dict) else v
            values.append("#" + _c(v[1:]) if v.startswith("#") else _c(v))
        tag = f"{_c(m.group(1) + ':')}{m.group(2)}"
        raw.setdefault(tag, [])
        raw[tag] += [v for v in values if v not in raw[tag]]

    def members(tag, seen):
        if tag in seen:
            return []
        seen.add(tag)
        out = []
        for v in raw.get(tag, []):
            for e in (members(v[1:], seen) if v.startswith("#") else [v]):
                if e not in out:
                    out.append(e)
        return out

    return {t: members(t, set()) for t in sorted(raw)}


def write(files, jar, fluids_path=None):
    names = jar.namelist()
    # The menus: the melter's three inputs and the heater's slot (shown only with a heater below), its 13 data slots
    # (the fuel's four ints, then each input's time, required time and temperature); the heater's one slot.
    files[f"data/{ID}/horizon/menu/melter.json"] = json.dumps({"slots": 4, "data_slots": 13}, indent=2).encode()
    files[f"data/{ID}/horizon/menu/heater.json"] = json.dumps({"slots": 1}, indent=2).encode()
    # The smeltery's and foundry's menu: the bucket input and result, the window of 40 melting slots, the hidden
    # intake; the fuel's 7 ints, each window slot's 3, then the window's first slot, the slot count and the bucket
    # mode. The duct's filter slot.
    files[f"data/{ID}/horizon/menu/smeltery.json"] = json.dumps({"slots": 43, "data_slots": 130}, indent=2).encode()
    files[f"data/{ID}/horizon/menu/duct.json"] = json.dumps({"slots": 1}, indent=2).encode()
    # Mantle's own data-driven fluid container transfers (bowls, honey and water bottles, the wet sponge, potions), read
    # with Tinkers' own from `mantle/fluid_transfer` by the native mod's reload listener (spec-smeltery.md 12.4).
    if MANTLE_JAR.exists():
        import zipfile
        with zipfile.ZipFile(MANTLE_JAR) as mantle:
            for name in mantle.namelist():
                if name.startswith("data/mantle/mantle/fluid_transfer/") and name.endswith(".json"):
                    files[name] = mantle.read(name)
    # The fluids' textures, where the atlas takes a content mod's (textures/block/), the originals kept.
    for name in names:
        if name.startswith(f"assets/{ID}/textures/fluid/") and not name.endswith("/"):
            files[name.replace("/textures/fluid/", "/textures/block/fluid/", 1)] = jar.read(name)
    # The c: tags with vanilla's members, merged into any the jar has.
    for tag, values in C_TAGS.items():
        path = f"data/c/tags/item/{tag}.json"
        doc = json.loads(files[path]) if path in files else {"replace": False, "values": []}
        for v in values:
            if v not in doc["values"]:
                doc["values"].append(v)
        files[path] = json.dumps(doc, indent=1).encode()
    # The fluid table.
    textures = {}
    for name in names:
        m = re.match(rf"assets/{ID}/mantle/fluid_texture/(\w+)\.json$", name)
        if not m:
            continue
        doc = _json(jar, name) or {}
        sprite = lambda key: doc.get(key, "").replace(f"{ID}:fluid/", f"{ID}:block/fluid/", 1)
        textures[f"{ID}:{m.group(1)}"] = {"still": sprite("still"), "flowing": sprite("flowing"),
                                           "color": int(doc.get("color", "FFFFFFFF"), 16)}
    known = set(textures) | {"minecraft:water", "minecraft:lava"}
    raw_tags = fluid_tags(jar)
    tags = {t: resolve(raw_tags, t, known) for t in raw_tags}
    tags = {t: v for t, v in tags.items() if v}
    lists = dict(MANTLE_LISTS)
    for name in names:
        m = re.match(rf"assets/{ID}/mantle/fluid_tooltips/(\w+)\.json$", name)
        if m:
            doc = _json(jar, name) or {}
            entry = {}
            if "redirect" in doc:
                entry["redirect"] = doc["redirect"]
            if "tag" in doc:
                entry["tag"] = _c(doc["tag"])
            if "units" in doc:
                entry["units"] = [[u["key"], u["needed"]] for u in doc["units"]]
            lists[f"{ID}:{m.group(1)}"] = entry

    def units_of(list_id, depth=0):
        e = lists.get(list_id, {})
        if "redirect" in e and depth < 8:
            return units_of(e["redirect"], depth + 1)
        return e.get("units", [])

    unit_lists = [{"id": k, "fluids": tags.get(v["tag"], []), "units": units_of(k)}
                  for k, v in sorted(lists.items()) if "tag" in v]
    named = {k: units_of(k) for k in sorted(lists)}
    buckets = {f: f"{ID}:{f.split(':', 1)[1]}_bucket" for f in textures
               if f"assets/{ID}/models/item/{f.split(':', 1)[1]}_bucket.json" in names}
    light, hot = fluid_props()
    table = {"tags": tags, "textures": textures, "buckets": buckets, "unit_lists": unit_lists, "named": named,
             "fallback": units_of("mantle:fallback"), "light": light, "hot": sorted(hot),
             "entity_tags": entity_tags(jar)}
    if fluids_path:
        pathlib.Path(fluids_path).write_text(json.dumps(table, indent=1, sort_keys=True), encoding="utf8")
    print(f"smeltery: {len(textures)} fluids, {len(tags)} fluid tags, {len(unit_lists)} tooltip lists, "
          f"{len(buckets)} buckets")
