"""Tinkers' Construct's blocks, items, recipes, tags and textures as a Horizon content mod, from the 1.20.1 jar.

Usage: python make_content.py <TConstruct jar> <out.hmod> [--report report.json]

The jar's assets go in as they are (block states, models, textures, lang, the books). On top, what 26.3 and Horizon
need:
- an item definition (`assets/tconstruct/items/<id>.json`) for every item model;
- each block's declaration: the vanilla template of its family (Tinkers' wood sets, glass, slime plants and the rest copy
  vanilla's blocks, as their Java classes extend them), and for the smeltery's parts and the stations the machine
  template the native mod gives a block entity;
- the recipes: vanilla's types in 26.3's form (an ingredient an id or a #tag, a result an `id`); Tinkers' own types
  (melting, casting, alloying, part building, tool building, modifiers...) unchanged, for the native mod to read;
- tags, loot tables and advancements in 26.3's folders (`tags/item`, `loot_table`, `advancement`), Forge's `forge:`
  tags as `c:` ones.

Not as blocks: Tinkers' molten fluids and their fluid blocks. On Horizon a mod's fluid lives in tanks only (the world has
vanilla's water and lava alone, native_fluids.rs), so `molten_*_fluid` and the other fluid blocks have no block here;
the native mod keeps the fluids in its tanks, and their buckets fill and empty tanks. The report lists them.
"""

import io
import json
import pathlib
import re
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import smeltery_data  # noqa: E402
import tool_data  # noqa: E402

ID = "tconstruct"

MANIFEST = """# Tinkers' Construct's blocks and items, from TConstruct-1.20.1-3.12.1.231.jar by
# tconstruct-horizon/tools/make_content.py.
id = "tconstruct"
name = "Tinkers' Construct (blocks and items)"
version = "3.12.1.231"
description = "Tinkers' Construct's blocks, items, recipes and textures."
authors = ["SlimeKnights"]
api = "0.2"
side = "both"
capabilities = ["registries"]
# Mantle's assets (the book's textures, its models) ship in the jar under its own namespace.
namespaces = ["mantle", "trimmed"]
"""

WOOD = ("greenheart", "skyroot", "bloodshroom", "enderbark")
# The smeltery's and foundry's parts, the casting blocks and the stations: block entities the native mod keeps.
MACHINES = (
    "smeltery_controller", "foundry_controller", "_drain", "_chute", "_duct", "_fuel_tank", "_fuel_gauge",
    "_ingot_tank", "_ingot_gauge", "_casting_tank", "_proxy_tank", "_faucet", "_channel", "_table", "_basin",
    "_melter", "_heater", "_alloyer", "_fluid_cannon", "crafting_station", "part_builder", "tinker_station",
    "tinkers_anvil", "scorched_anvil", "modifier_worktable", "tinkers_chest", "part_chest", "cast_chest",
)

# (suffix or exact name, vanilla template), checked in order: the first that matches.
FAMILIES = [
    ("potted_", "minecraft:potted_fern"),
    ("small_", "minecraft:small_amethyst_bud"),
    ("medium_", "minecraft:medium_amethyst_bud"),
    ("large_", "minecraft:large_amethyst_bud"),
    ("blazewood", "minecraft:oak_planks"),
    ("nahuatl", "minecraft:oak_planks"),
    ("grout", "minecraft:clay"),
    ("nether_grout", "minecraft:clay"),
    ("knightslime_block", "minecraft:iron_block"),
    ("fake_storage_block", "minecraft:iron_block"),
    ("_wall_hanging_sign", "minecraft:oak_wall_hanging_sign"),
    ("_hanging_sign", "minecraft:oak_hanging_sign"),
    ("_wall_sign", "minecraft:oak_wall_sign"),
    ("_sign", "minecraft:oak_sign"),
    ("_fence_gate", "minecraft:oak_fence_gate"),
    ("_pressure_plate", "minecraft:oak_pressure_plate"),
    ("_trapdoor", "minecraft:oak_trapdoor"),
    ("_door", "minecraft:oak_door"),
    ("_button", "minecraft:oak_button"),
    ("_planks_stairs", "minecraft:oak_stairs"),
    ("_planks_slab", "minecraft:oak_slab"),
    ("_planks", "minecraft:oak_planks"),
    ("_fence", "minecraft:oak_fence"),
    ("_wall_head", "minecraft:skeleton_wall_skull"),
    ("_head", "minecraft:skeleton_skull"),
    ("_stairs", "minecraft:stone_brick_stairs"),
    ("_slab", "minecraft:stone_brick_slab"),
    ("_wall", "minecraft:cobblestone_wall"),
    ("_log", "minecraft:oak_log"),
    ("_wood", "minecraft:oak_wood"),
    ("_leaves", "minecraft:oak_leaves"),
    ("_sapling", "minecraft:oak_sapling"),
    ("_slime_grass", "minecraft:grass_block"),
    ("_slime_dirt", "minecraft:dirt"),
    ("_slime_fern", "minecraft:fern"),
    ("_slime_tall_grass", "minecraft:short_grass"),
    ("_slime_vine", "minecraft:vine"),
    ("_roots", "minecraft:mangrove_roots"),
    ("_crystal_cluster", "minecraft:amethyst_cluster"),
    ("_cluster", "minecraft:amethyst_cluster"),
    ("_crystal_block", "minecraft:amethyst_block"),
    ("_crystal", "minecraft:amethyst_cluster"),
    ("_cake", "minecraft:cake"),
    ("congealed_", "minecraft:slime_block"),
    ("_slime", "minecraft:slime_block"),
    ("_glass_pane", "minecraft:glass_pane"),
    ("clear_stained_glass_pane", "minecraft:white_stained_glass_pane"),
    ("_pane", "minecraft:glass_pane"),
    ("tinted_glass", "minecraft:tinted_glass"),
    ("_glass", "minecraft:glass"),
    ("_ladder", "minecraft:ladder"),
    ("_lantern", "minecraft:lantern"),
    ("_lamp", "minecraft:glowstone"),
    ("_bars", "minecraft:iron_bars"),
    ("_platform", "minecraft:iron_block"),
    ("_ore", "minecraft:iron_ore"),
    ("raw_cobalt_block", "minecraft:raw_iron_block"),
    ("punji", "minecraft:sweet_berry_bush"),
    ("glow", "minecraft:glow_lichen"),
    ("cheese_block", "minecraft:slime_block"),
]
METAL = ("cobalt", "manyullyn", "hepatizon", "amethyst_bronze", "rose_gold", "pig_iron", "steel", "soulsteel",
         "knightmetal", "slimesteel", "queens_slime", "cinderslime")


# Blocks whose states the template lacks: their own state properties are declared (platforms join up, down and around;
# punji face six ways; slime vines grow in stages).
OWN_STATES = ("_platform", "punji", "_slime_vine")
# Tinkers' fancy item frames are entities (FancyItemFrameEntity) whose models the block state files name: no block.
ENTITY_MODELS = ("_frame",)
TEMPLATE_STATES = {"minecraft:vine": ("up", "north", "east", "south", "west"),
                   "minecraft:sweet_berry_bush": ("age",)}


def template_of(name):
    if name.endswith("_fluid") or name.endswith(ENTITY_MODELS):
        return None
    if any(name == m or name.endswith(m) for m in MACHINES if m.startswith("_")) or name in MACHINES:
        return "minecraft:beacon"
    for suffix, template in FAMILIES:
        if suffix.endswith("_") and name.startswith(suffix) or name.endswith(suffix) or name == suffix:
            return template
    if name.endswith("_block") and any(name.startswith(m) for m in METAL):
        return "minecraft:iron_block"
    return "minecraft:stone_bricks"


def state_properties(blockstate):
    """The properties a block state file names, with their values in the order it first gives them."""
    props = {}

    def add(k, v):
        props.setdefault(k, [])
        if v not in props[k]:
            props[k].append(v)

    for key in blockstate.get("variants", {}):
        for part in filter(None, key.split(",")):
            k, v = part.split("=")
            add(k, v)
    for part in blockstate.get("multipart", []):
        when = part.get("when", {})
        for clause in when.get("OR", [when]):
            for k, v in clause.items():
                for one in str(v).lower().split("|"):
                    add(k, one)
    out = {}
    for k, values in props.items():
        out[k] = {"type": "boolean"} if set(values) <= {"true", "false"} else {"type": "enum", "values": values}
    return out


# The melter and the heater (TinkerSmeltery: the `seared` controller properties): strength 8 / 28, metal's sounds, a
# pickaxe; the melter occludes nothing (noOcclusion). ControllerBlock's states: facing, active, in_structure (the
# heater's block state file names only facing and active; the property is declared all the same).
CONTROLLERS = ("seared_melter", "seared_heater")
CONTROLLER_STATES = {
    "facing": {"type": "enum", "values": ["north", "south", "west", "east"]},
    "active": {"type": "boolean"},
    "in_structure": {"type": "boolean"},
}


def block_decl(name, blockstate):
    template = template_of(name)
    decl = {"template": template}
    # A flower pot with a plant has no item of its own (vanilla's potted_* don't).
    if template.startswith("minecraft:potted_"):
        decl["item"] = False
    if name in CONTROLLERS:
        decl["properties"] = {"hardness": 8.0, "explosion_resistance": 28.0, "sounds": "minecraft:iron_block",
                              "requires_tool": True, "light": 0}
        if name == "seared_melter":
            decl["properties"]["occludes"] = False
        props = dict(CONTROLLER_STATES)
        props.update({k: v for k, v in state_properties(blockstate).items() if k not in props})
        decl["state_properties"] = props
        decl["default_state"] = {"facing": "north", "active": "false", "in_structure": "false"}
        # Light 13 while active: the furnace's template, whose `lit` the native mod keeps equal to `active`.
        return smeltery_data.lit_decl(name, decl)
    if name.endswith(OWN_STATES):
        # Declared properties come on top of the template's: only those it lacks.
        props = {k: v for k, v in state_properties(blockstate).items() if k not in TEMPLATE_STATES.get(template, ())}
        decl["state_properties"] = props
        decl["default_state"] = {k: ("false" if v["type"] == "boolean" else v["values"][0]) for k, v in props.items()}
    if template == "minecraft:beacon":
        # SearedBlock / the stations: stone strength (seared 3/9, scorched 2.5/8), a pickaxe; the native mod's block
        # entity. Their state properties come from their block state files (facing, in_structure, active...).
        # No light of the beacon's own (15): these blocks give none.
        decl["properties"] = {"hardness": 3.0, "explosion_resistance": 9.0, "sounds": "minecraft:stone",
                              "requires_tool": True, "light": 0}
        if name in ("crafting_station", "part_builder", "tinker_station", "tinkers_chest", "part_chest", "cast_chest",
                    "modifier_worktable"):
            decl["properties"] = {"hardness": 1.0, "explosion_resistance": 5.0, "sounds": "minecraft:oak_planks",
                                  "requires_tool": False, "light": 0}
        props = state_properties(blockstate)
        if props:
            decl["state_properties"] = props
            decl["default_state"] = {k: ("false" if v["type"] == "boolean" else
                                         "north" if k == "facing" and "north" in v["values"] else v["values"][0])
                                     for k, v in props.items()}
        # The faucets, casting tables and basins, channels and the casting tank: their own strength, states and shapes.
        decl = smeltery_data.casting_decl(name, decl)
        # The stations: TinkerTables' strength and sounds, no occlusion, their shapes.
        decl = tool_data.station_decl(name, decl)
    return decl


FORGE_PARENTS = {"forge:item/default": "minecraft:item/generated", "forge:item/bucket_drip": "minecraft:item/generated",
                 "forge:item/bucket": "minecraft:item/generated", "forge:item/default-tool": "minecraft:item/handheld"}


def vanilla_model(data, skipped):
    """A model Mantle's or Tinkers' loaders build as one vanilla reads, until the native mod draws the real one:
    a tool or part from its own layers (Tinkers tints them by material in code), a fluid container as its container
    (the fluid is drawn by the native mod), a connected or retextured block from its base textures."""
    try:
        doc = json.loads(data.decode("utf-8-sig"))
    except ValueError:
        return data
    if not isinstance(doc, dict):
        return data
    loader = doc.pop("loader", None)
    parent = doc.get("parent")
    if parent in FORGE_PARENTS:
        doc["parent"] = FORGE_PARENTS[parent]
    if loader is None:
        return json.dumps(doc, indent=1).encode() if parent in FORGE_PARENTS else data
    skipped.setdefault("loader_models", {}).setdefault(loader, 0)
    skipped["loader_models"][loader] += 1
    textures = doc.get("textures", {})
    if loader in ("tconstruct:tool", "tconstruct:material", "mantle:item_layer"):
        order = [p["name"] for p in sorted(doc.get("parts", []), key=lambda p: p.get("index", 0)) if p.get("name") in textures]
        order += [k for k in textures if k not in order and k != "particle"]
        doc = {"parent": "minecraft:item/handheld" if loader == "tconstruct:tool" else "minecraft:item/generated",
               "textures": {f"layer{i}": textures[k] for i, k in enumerate(order)}}
    elif loader == "tconstruct:fluid_container":
        doc = {"parent": "minecraft:item/generated", "textures": {"layer0": textures.get("base", "minecraft:item/bucket")}}
    elif loader in ("mantle:connected", "mantle:retextured", "mantle:colored_block", "mantle:nbt_key",
                    "tconstruct:material_block", "tconstruct:tank", "tconstruct:fluid_texture", "tconstruct:gui", "forge:composite"):
        for k in ("connection", "colors", "retextured", "render_type", "fluids", "gui", "children", "item_order"):
            doc.pop(k, None)
    return json.dumps(doc, indent=1).encode()


def item_predicate(p):
    """A 1.20 item predicate in 26.3's form, or None when vanilla can't express it (Tinkers' tool_stack, Mantle's
    predicates, NBT): such a criterion must never match by accident."""
    if not isinstance(p, dict):
        return None
    if "type" in p or "nbt" in p or "potion" in p:
        return None
    out = {}
    if "tag" in p:
        out["items"] = "#" + p["tag"].replace("forge:", "c:")
    if "items" in p:
        out["items"] = p["items"][0] if isinstance(p["items"], list) and len(p["items"]) == 1 else p["items"]
    for k in ("count", "durability"):
        if k in p:
            out[k] = p[k]
    if "enchantments" in p or "stored_enchantments" in p:
        return None
    return out


def advancement(doc, skipped):
    """An advancement's criteria in 26.3's form. A criterion that can't be (Tinkers' own triggers and predicates)
    becomes `minecraft:impossible`: it never fires on its own, and the native mod grants it when Java would."""
    for name, crit in list(doc.get("criteria", {}).items()):
        trigger = crit.get("trigger", "")
        cond = crit.get("conditions", {}) or {}
        ok = True
        if trigger == "minecraft:inventory_changed":
            items = [item_predicate(p) for p in cond.get("items", [])]
            if any(i is None for i in items):
                ok = False
            else:
                cond["items"] = items
        elif trigger == "minecraft:placed_block":
            if "block" in cond:
                block = cond.pop("block")
                pred = {"blocks": block}
                if "state" in cond:
                    pred["state"] = cond.pop("state")
                cond["location"] = [{"condition": "minecraft:location_check", "predicate": {"block": pred}}]
            if "item" in cond:
                ok = False
        elif trigger == "minecraft:location":
            loc = cond.pop("location", None)
            if loc is not None:
                if "biome" in loc:
                    loc["biomes"] = loc.pop("biome")
                if "structure" in loc:
                    loc["structures"] = loc.pop("structure")
                cond["player"] = [{"condition": "minecraft:entity_properties", "entity": "this", "predicate": {"location": loc}}]
        elif trigger == "minecraft:recipe_unlocked":
            pass
        else:
            ok = False
        if ok:
            crit["conditions"] = cond
        else:
            doc["criteria"][name] = {"trigger": "minecraft:impossible"}
            skipped.setdefault("advancement_criteria_native", []).append(f"{doc.get('_name', '?')}#{name}")
    # Location predicates anywhere in the criteria: 1.20's `structure` / `biome` are 26.3's `structures` / `biomes`.
    def locations(v):
        if isinstance(v, dict):
            if "location" in v and isinstance(v["location"], dict):
                loc = v["location"]
                if "structure" in loc:
                    loc["structures"] = loc.pop("structure")
                if "biome" in loc:
                    loc["biomes"] = loc.pop("biome")
            for x in v.values():
                locations(x)
        elif isinstance(v, list):
            for x in v:
                locations(x)
    locations(doc.get("criteria", {}))
    background = doc.get("display", {}).get("background")
    if isinstance(background, str):
        doc["display"]["background"] = background.replace("textures/", "", 1).removesuffix(".png")
    icon = doc.get("display", {}).get("icon")
    if isinstance(icon, dict) and "item" in icon:
        doc["display"]["icon"] = {"id": icon["item"], **({"count": icon["count"]} if "count" in icon else {})}
    doc.pop("_name", None)
    return doc


def ingredient(v):
    """1.20's {"item"} / {"tag"} (or a list of them) as 26.3's id / #tag."""
    if isinstance(v, list):
        return [ingredient(x) for x in v]
    if not isinstance(v, dict):
        return v
    if "item" in v:
        return v["item"]
    if "tag" in v:
        return "#" + v["tag"].replace("forge:", "c:")
    return v


def vanilla_recipe(doc):
    out = dict(doc)
    if "key" in out:
        out["key"] = {k: ingredient(v) for k, v in out["key"].items()}
    if "ingredients" in out:
        out["ingredients"] = [ingredient(v) for v in out["ingredients"]]
    if "ingredient" in out:
        out["ingredient"] = ingredient(out["ingredient"])
    r = out.get("result")
    if isinstance(r, str):
        r = {"item": r}
    if isinstance(r, dict) and "item" in r:
        out["result"] = {"id": r["item"], **({"count": r["count"]} if r.get("count", 1) != 1 else {})}
    if out.get("type") in ("minecraft:crafting_shaped", "minecraft:crafting_shapeless"):
        out.setdefault("category", "misc")
    return out


def unwrap(doc):
    """`forge:conditional`: the first recipe whose conditions hold without other mods (none of `mod_loaded`)."""
    for entry in doc.get("recipes", []):
        conds = entry.get("conditions", [])
        if all(c.get("type") != "forge:mod_loaded" and c.get("type") != "forge:not" or c.get("type") == "forge:not"
               for c in conds):
            if not any(c.get("type") == "forge:mod_loaded" for c in conds):
                return entry.get("recipe")
    return None


TAG_KINDS = {"blocks": "block", "items": "item", "fluids": "fluid", "entity_types": "entity_type",
             "game_events": "game_event", "worldgen": "worldgen", "damage_type": "damage_type",
             "banner_pattern": "banner_pattern", "painting_variant": "painting_variant", "enchantment": "enchantment"}


# The sprite source types Horizon reads (horizon-client-render atlas_sources::decode_source). One it doesn't read
# makes it drop the whole atlas file, and with Tinkers' blocks atlas merged over vanilla's that took vanilla's
# `block/` directory with it: every mod's block textures left the GUI atlas and their item icons drew blank.
READABLE_SOURCES = {"minecraft:directory", "minecraft:single", "minecraft:filter", "minecraft:unstitch",
                    "minecraft:paletted_permutations"}


def readable_atlas(name, data, skipped):
    """An atlas file with only the sprite sources Horizon reads. Tinkers' own source type
    (`tconstruct:shield_banner_to_modifier`, the shield banner modifier's large sprites cropped from the shield
    pattern textures) is its Java client's; the banner layers it is for aren't drawn yet (PLAN.md)."""
    doc = json.loads(data.decode("utf-8-sig"))
    keep = []
    for s in doc.get("sources", []):
        kind = s.get("type", "")
        kind = kind if ":" in kind else f"minecraft:{kind}"
        if kind in READABLE_SOURCES:
            keep.append(s)
        else:
            skipped.setdefault("atlas_sources", []).append(f"{name}: {kind}")
    return json.dumps({**doc, "sources": keep}, indent=2).encode()


def main(jar, out, report_path=None, fluids_path=None):
    source = zipfile.ZipFile(jar)
    files = {}
    blocks, items, skipped = [], [], {"fluid_blocks": [], "entity_models": [], "recipes_conditional": [], "unreadable": []}
    recipe_types = {}
    for name in source.namelist():
        if name.endswith("/") or name.endswith(".class") or name.startswith("META-INF") or name == "pack.mcmeta":
            continue
        if name.startswith("slimeknights/"):
            continue
        data = source.read(name)
        if name.startswith(f"assets/{ID}/blockstates/"):
            block = name.rsplit("/", 1)[1][:-5]
            try:
                bs = json.loads(data.decode("utf-8-sig"))
            except ValueError:
                skipped["unreadable"].append(name)
                continue
            if template_of(block) is None:
                skipped["fluid_blocks" if block.endswith("_fluid") else "entity_models"].append(block)
                continue
            blocks.append(block)
            files[f"data/{ID}/horizon/block/{block}.json"] = json.dumps(block_decl(block, bs), indent=1).encode()
            files[name] = data
            continue
        # An item is a model directly in models/item/; the sub-folders (tool/, part/, broken/...) hold the layers and
        # states other models use, not items of their own.
        if name.startswith(f"assets/{ID}/models/item/") and name.endswith(".json") and name.count("/") == 4:
            items.append(name.rsplit("/", 1)[1][:-5])
        if name.startswith(f"assets/{ID}/models/") and name.endswith(".json"):
            data = vanilla_model(data, skipped)
        if name.startswith("assets/"):
            # Horizon takes plain asset paths only: assets/<ns>/<kind>/..., or a file like sounds.json at the top.
            parts = name.split("/")
            if len(parts) < 3 or (len(parts) == 3 and not name.endswith((".json", ".mcmeta"))):
                skipped["unreadable"].append(name)
                continue
            if name.startswith("assets/minecraft/atlases/") and name.endswith(".json"):
                data = readable_atlas(name, data, skipped)
            files[name] = data
            continue
        if not name.startswith("data/"):
            continue  # logo.png and the like: not part of a pack.
        parts = name.split("/")
        ns, kind = parts[1], parts[2]
        rest = "/".join(parts[3:])
        # Horizon takes a mod's own namespaces, and vanilla's and convention (c) tags. Tags for other mods
        # (Create, Ceramics, Twilight Forest...) are their integration and stay out; so do Forge's global loot
        # modifiers (the native mod does their work).
        if ns not in (ID, "mantle", "minecraft", "forge", "c") or (ns in ("minecraft", "forge") and kind != "tags"):
            skipped.setdefault("other_namespaces", []).append(name)
            continue
        if kind == "recipes" and name.endswith(".json"):
            try:
                doc = json.loads(data.decode("utf-8-sig"))
            except ValueError:
                skipped["unreadable"].append(name)
                continue
            if doc.get("type") == "forge:conditional" and smeltery_data.keeps_conditional(doc):
                # The melter's recipes keep every alternative: the native mod takes the first whose conditions hold
                # (mantle:tag_filled and the like ask the game's tags, which this script can't).
                doc = smeltery_data.conditional(doc)
            elif doc.get("type") == "forge:conditional":
                doc = unwrap(doc)
                if doc is None:
                    skipped["recipes_conditional"].append(name)
                    continue
            t = doc.get("type", "")
            recipe_types[t] = recipe_types.get(t, 0) + 1
            if t.startswith("minecraft:"):
                doc = vanilla_recipe(doc)
            files[f"data/{ns}/recipe/{rest}"] = json.dumps(doc, indent=1).encode()
            continue
        if kind == "tags":
            sub, tail = rest.split("/", 1)
            sub = TAG_KINDS.get(sub, sub)
            target_ns = "c" if ns == "forge" else ns
            try:
                doc = json.loads(data.decode("utf-8-sig"))
                doc["values"] = [v.replace("forge:", "c:") if isinstance(v, str) else
                                 {**v, "id": v["id"].replace("forge:", "c:")} if isinstance(v, dict) and "id" in v else v
                                 for v in doc.get("values", [])]
                data = json.dumps(doc, indent=1).encode()
            except ValueError:
                pass
            files[f"data/{target_ns}/tags/{sub}/{tail}"] = data
            continue
        if kind == "loot_tables":
            files[f"data/{ns}/loot_table/{rest}"] = data
            continue
        if kind == "advancements":
            try:
                doc = json.loads(data.decode("utf-8-sig"))
                doc["_name"] = rest
                data = json.dumps(advancement(doc, skipped), indent=1).encode()
            except ValueError:
                pass
            files[f"data/{ns}/advancement/{rest}"] = data
            continue
        if kind == "structures":
            files[f"data/{ns}/structure/{rest}"] = data
            continue
        files[name] = data
    block_set = set(blocks)
    item_ids = sorted(set(items))
    for item in item_ids:
        files[f"assets/{ID}/items/{item}.json"] = json.dumps(
            {"model": {"type": "minecraft:model", "model": f"{ID}:item/{item}"}}).encode()
        if item in block_set:
            continue
        files[f"data/{ID}/horizon/item/{item}.json"] = json.dumps({"template": "minecraft:paper"}, indent=1).encode()
    # The W guide, from Tinkers' own books, in every language they are written in.
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    import tconstruct_guide
    guide_pages, guide_langs = tconstruct_guide.write(files, jar)
    print(f"guide: {guide_pages} pages, translated into {len(guide_langs)} languages")
    # The melter, the heater and the tanks: their menus, the fluids' textures, the `c:` tags the melting recipes
    # name with vanilla's items, and the fluid table the native mod compiles in.
    smeltery_data.write(files, source, fluids_path)
    # The copper can drawn with its fluid (FluidContainerModel): the mask models and the item definition's cases.
    import copper_can
    copper_can.write(files, source)
    # The fluid buckets the same way, each with its own fluid in Forge's drip mask.
    copper_can.write_buckets(files, source)
    # Materials and tool parts: the material table the native mod compiles in, the parts drawn by material.
    tool_data.write(files, source, fluids_path)
    # The gadgets: punji, glow, platforms and cakes declared as they act, stack sizes, effects, thrown types.
    import gadget_data
    gadget_data.write(files)
    # The foods and drinks: Java's FoodProperties, the bottles' glass bottle back (after the gadgets' stack sizes).
    import food_data
    food_data.write(files)
    # The world: features in 26.3's form, biome modifiers Horizon reads, geode and slime plant declarations.
    import world_data
    world_data.write(files, skipped)
    # The mob heads: Java's skull renderer drew them; here block and item models of the same quads.
    import heads
    heads.write(files, skipped)
    __import__("foliage_colors").write(files, skipped)  # Slime foliage: item tints (the blocks are tinted at run time).
    files["horizon-mod.toml"] = MANIFEST.encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            z.writestr(name, files[name])
    open(out, "wb").write(buf.getvalue())
    report = {"blocks": len(blocks), "items": len(item_ids), "files": len(files), "recipe_types": recipe_types,
              "skipped": skipped}
    if report_path:
        open(report_path, "w", encoding="utf-8").write(json.dumps(report, indent=1))
    print(f"{len(files)} files, {len(blocks)} blocks, {len(item_ids)} items, {len(buf.getvalue())} bytes; "
          f"{len(skipped['fluid_blocks'])} fluid blocks kept in tanks only, "
          f"{len(skipped['recipes_conditional'])} recipes need other mods")


if __name__ == "__main__":
    args = sys.argv[1:]
    report = None
    if "--report" in args:
        i = args.index("--report")
        report = args[i + 1]
        del args[i:i + 2]
    fluids = None
    if "--fluids" in args:
        i = args.index("--fluids")
        fluids = args[i + 1]
        del args[i:i + 2]
    main(args[0], args[1], report, fluids)
