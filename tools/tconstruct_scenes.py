"""3D scenes for the Tinkers' guide pages about blocks, each block placed with what it works with: a part in its
smeltery or foundry wall, a faucet on the tank it drains, a station with its chest, an island or a geode in small.
Blocks are [x, y, z, block, {property: value}]; the guide first shows a scene from the north (-z), so fronts face
north (a faucet's or gauge's `facing` points away from the block it hangs on)."""

T = "tconstruct:"
N = "north"


def b(x, y, z, block, props=None):
    return [x, y, z, block if ":" in block else T + block, props or {}]


def furnace(kind, front=None, extra=(), height=2):
    """A small formed smeltery ("seared") or foundry ("scorched"), 3 by 3 inside, `height` walls high, as the
    book's structures are (the foundry with its corners and edges). Its controller and a fuel tank stand in the north
    wall; `front` puts other blocks in that wall ({(x, y): (block, props)}), `extra` adds blocks outside."""
    foundry = kind == "scorched"
    at = {}
    for x in range(5):
        for z in range(5):
            edge = x in (0, 4) or z in (0, 4)
            corner = x in (0, 4) and z in (0, 4)
            if not edge or foundry:
                at[(x, 0, z)] = (f"{kind}_bricks", {})
            for y in range(1, height + 1):
                if edge and (foundry or not corner):
                    at[(x, y, z)] = (f"{kind}_bricks", {})
    controller = "foundry_controller" if foundry else "smeltery_controller"
    at[(2, 1, 0)] = (controller, {"in_structure": "true", "active": "true", "facing": N})
    at[(3, 1, 0)] = (f"{kind}_fuel_tank", {})
    for (x, y), block in (front or {}).items():
        at[(x, y, 0)] = block
    return [b(x, y, z, *at[(x, y, z)]) for (x, y, z) in sorted(at)] + [b(*e) for e in extra]


FORMED = {"in_structure": "true", "facing": N}   # a part of a formed structure, its face outward


def part_scenes(kind, book, glass_pages):
    """The pages about the parts of a smeltery or foundry: each part in place, with what it works with."""
    drain, duct, chute = f"{kind}_drain", f"{kind}_duct", f"{kind}_chute"
    out = {
        # The drain, a faucet on it pouring into a casting table.
        f"{book}/{drain}.md": furnace(kind, {(1, 1): (drain, FORMED)},
                                      [(1, 1, -1, f"{kind}_faucet", {"facing": N}), (1, 0, -1, f"{kind}_table", {"facing": N})]),
        # The duct, the faucet on it filling a basin with the fluid it filters.
        f"{book}/{duct}.md": furnace(kind, {(1, 1): (duct, FORMED)},
                                     [(1, 1, -1, f"{kind}_faucet", {"facing": N}), (1, 0, -1, f"{kind}_basin", {"facing": N})]),
        # The chute, a hopper (under a barrel) feeding it items.
        f"{book}/{chute}.md": furnace(kind, {(1, 1): (chute, FORMED)},
                                      [(1, 1, -1, "minecraft:hopper", {"facing": "south", "enabled": "true"}),
                                       (1, 2, -1, "minecraft:barrel", {"facing": "up", "open": "false"})]),
        # A ladder up the wall, three high.
        f"{book}/{kind}_ladder.md": furnace(kind, {(1, y): (f"{kind}_ladder", {"facing": N, "bottom": str(y == 1).lower()})
                                                   for y in (1, 2, 3)}, height=3),
        # Tanks and gauges in the wall: the fuel and the extra capacity.
        f"{book}/{kind}_tanks.md": furnace(kind, {(1, 1): (f"{kind}_ingot_tank", {}), (1, 2): (f"{kind}_fuel_gauge", {}),
                                                  (3, 2): (f"{kind}_ingot_gauge", {})}),
    }
    # A window of each glass along the top of the front wall.
    for page, glass in glass_pages.items():
        out[f"{book}/{page}.md"] = furnace(kind, {(x, 2): (glass, {}) for x in (1, 2, 3)})
    return out


def tank_faucet(tank, faucet, below, below_props=None, extra=()):
    """A tank on a brick, a faucet on its front pouring into `below` (the block under the faucet)."""
    kind = tank.split("_")[0]
    return [b(0, 1, 1, tank), b(0, 0, 1, f"{kind}_bricks"), b(0, 1, 0, faucet, {"facing": N}),
            b(0, 0, 0, below, below_props or {})] + [b(*e) for e in extra]


def station(*row):
    """Stations and chests side by side (a station uses the chests next to it), facing north."""
    return [b(x, 0, 0, block, {"facing": N}) for x, block in enumerate(row)]


def island(grass, dirt, base, log, leaves, plants, under=()):
    """A slime island in small: a congealed core, slime dirt, slime grass on top, a tree and some plants."""
    out = []
    for x in range(5):
        for z in range(5):
            if x in (0, 4) and z in (0, 4):
                continue
            out.append(b(x, 1, z, dirt))
            out.append(b(x, 2, z, grass, {"snowy": "false"}))
            if 1 <= x <= 3 and 1 <= z <= 3:
                out.append(b(x, 0, z, base))
    for y in (3, 4, 5):
        out.append(b(2, y, 2, log, {"axis": "y"}))
    for x, y, z in [(1, 5, 2), (3, 5, 2), (2, 5, 1), (2, 5, 3), (1, 4, 2), (3, 4, 2), (2, 4, 1), (2, 4, 3), (2, 6, 2)]:
        out.append(b(x, y, z, leaves))
    for (x, z), plant in zip([(1, 1), (3, 3), (0, 2)], plants):
        out.append(b(x, 3, z, plant))
    # `under` replaces what stands at its places.
    return list({tuple(o[:3]): o for o in out + [b(*u) for u in under]}.values())


def geode(slime, middle, outer, extra=()):
    """A geode cut open: its outer shell, calcite, then slime crystal with budding crystal and buds growing."""
    crystal, budding = f"{slime}_slime_crystal_block", f"budding_{slime}_slime_crystal"
    out = []
    for x in range(3):
        for z in range(3):
            out += [b(x, 0, z, outer), b(x, 1, z, middle),
                    b(x, 2, z, budding if (x, z) in ((0, 0), (1, 0), (2, 1)) else crystal)]
    # The back wall, crystal on the inside.
    for x in range(3):
        for y in (3, 4):
            out += [b(x, y, 3, budding if (x, y) == (1, 3) else crystal), b(x, y, 4, middle), b(x, y, 5, outer)]
    up = {"facing": "up"}
    out += [b(0, 3, 0, f"{slime}_slime_crystal_cluster", up), b(2, 3, 1, f"large_{slime}_slime_crystal_bud", up),
            b(1, 3, 0, f"small_{slime}_slime_crystal_bud", up), b(1, 3, 2, f"medium_{slime}_slime_crystal_bud", {"facing": N})]
    return out + [b(*e) for e in extra]


def shard(slime, cluster):
    """A metal cluster grown on a geode's crystal, beside the slime crystal's own buds."""
    up = {"facing": "up"}
    return [b(0, 0, 0, f"{slime}_slime_crystal_block"), b(1, 0, 0, f"budding_{slime}_slime_crystal"),
            b(2, 0, 0, f"{slime}_slime_crystal_block"), b(1, 0, 1, f"{slime}_slime_crystal_block"),
            b(0, 1, 0, cluster, up), b(1, 1, 0, f"{slime}_slime_crystal_cluster", up), b(2, 1, 0, f"large_{slime}_slime_crystal_bud", up)]


SEARED = {"seared_glass": "seared_glass", "tinted_glass": "seared_tinted_glass", "soul_glass": "seared_soul_glass"}
SCORCHED = {"scorched_glass": "scorched_glass", "tinted_glass": "scorched_tinted_glass", "soul_glass": "scorched_soul_glass"}

SCENES = {
    **part_scenes("seared", "mighty_smelting/smeltery", SEARED),
    **part_scenes("scorched", "fantastic_foundry/foundry", SCORCHED),
    # The melter on a fuel tank in place of its heater, pouring into a basin.
    "puny_smelting/melter/features.md": [
        b(0, 0, 0, "seared_fuel_tank"), b(0, 1, 0, "seared_melter", {"facing": N, "in_structure": "false"}),
        b(0, 1, -1, "seared_faucet", {"facing": N}), b(0, 0, -1, "seared_basin", {"facing": N})],
    # Getting metal out: the melter's faucet into a channel that carries it to a table.
    "puny_smelting/moving_fluids/moving_fluids.md": [
        b(0, 0, 0, "seared_heater", {"facing": N, "active": "false"}),
        b(0, 1, 0, "seared_melter", {"facing": N, "in_structure": "false"}), b(0, 1, -1, "seared_faucet", {"facing": N}),
        b(0, 0, -1, "seared_channel", {"east": "out"}), b(1, 0, -1, "seared_channel", {"west": "in", "down": "true"}),
        b(0, -1, -1, "seared_bricks"), b(1, -1, -1, "seared_table", {"facing": N}), b(0, -1, 0, "seared_bricks")],
    # A faucet fills the first channel from the top; the channels carry the fluid along and pour down into a table.
    "puny_smelting/moving_fluids/channels.md": tank_faucet("seared_fuel_tank", "seared_faucet", "seared_channel", {"east": "out"}, [
        (1, 0, 0, "seared_channel", {"west": "in", "east": "out"}), (2, 0, 0, "seared_channel", {"west": "in", "down": "true"}),
        (0, -1, 0, "seared_bricks", {}), (1, -1, 0, "seared_bricks", {}), (2, -1, 0, "seared_table", {"facing": N}),
        (0, -1, 1, "seared_bricks", {})]),
    # Gauges on the fronts of tanks.
    "puny_smelting/moving_fluids/gauge.md": [
        b(0, 0, 0, "seared_fuel_tank"), b(0, 0, -1, "copper_gauge", {"facing": N}),
        b(1, 0, 0, "seared_ingot_tank"), b(1, 0, -1, "obsidian_gauge", {"facing": N})],
    # A fluid cannon filled from a tank by a faucet, a lever beside it to fire.
    "puny_smelting/moving_fluids/fluid_cannon.md": tank_faucet("seared_fuel_tank", "seared_faucet", "seared_fluid_cannon", {"facing": N}, [
        (1, 0, 0, "minecraft:lever", {"face": "wall", "facing": "east", "powered": "false"})]),
    "fantastic_foundry/alloyer/fluid_cannon.md": tank_faucet("scorched_fuel_tank", "scorched_faucet", "scorched_fluid_cannon", {"facing": N}, [
        (1, 0, 0, "minecraft:lever", {"face": "wall", "facing": "east", "powered": "false"})]),
    "tinkers_gadgetry/gadgets/fluid_cannon.md": tank_faucet("scorched_fuel_tank", "scorched_faucet", "end_fluid_cannon", {"facing": N}, [
        (1, 0, 0, "minecraft:lever", {"face": "wall", "facing": "east", "powered": "false"})]),
    # The casting tank filled by a faucet, a hopper under it emptying into a barrel.
    "puny_smelting/casting/casting_tank.md": tank_faucet("seared_fuel_tank", "seared_faucet", "seared_casting_tank", {"facing": N}, [
        (0, -1, 0, "minecraft:hopper", {"facing": "down", "enabled": "true"}), (0, -2, 0, "minecraft:barrel", {"facing": "up", "open": "false"}),
        (0, -1, 1, "seared_bricks", {}), (0, -2, 1, "seared_bricks", {})]),
    # A table and a basin, each with a hopper under it taking out what cooled.
    "puny_smelting/casting/automation.md": [
        b(0, 2, 1, "seared_fuel_tank"), b(1, 2, 1, "seared_fuel_tank"),
        b(0, 2, 0, "seared_faucet", {"facing": N}), b(1, 2, 0, "seared_faucet", {"facing": N}),
        b(0, 1, 0, "seared_table", {"facing": N}), b(1, 1, 0, "seared_basin", {"facing": N}),
        b(0, 0, 0, "minecraft:hopper", {"facing": "down", "enabled": "true"}), b(1, 0, 0, "minecraft:hopper", {"facing": "down", "enabled": "true"}),
        b(0, -1, 0, "minecraft:barrel", {"facing": "up", "open": "false"}), b(1, -1, 0, "minecraft:barrel", {"facing": "up", "open": "false"})]
        + [b(x, y, 1, "seared_bricks") for x in (0, 1) for y in (-1, 0, 1)],
    # The tinker tank filled by a faucet.
    "fantastic_foundry/alloyer/proxy_tank.md": tank_faucet("scorched_ingot_tank", "scorched_faucet", "scorched_proxy_tank"),
    # Casting in the foundry's way: a scorched table and basin under faucets.
    "fantastic_foundry/alloyer/casting.md": tank_faucet("scorched_ingot_tank", "scorched_faucet", "scorched_table", {"facing": N}, [
        (1, 1, 1, "scorched_ingot_tank", {}), (1, 0, 1, "scorched_bricks", {}), (1, 1, 0, "scorched_faucet", {"facing": N}),
        (1, 0, 0, "scorched_basin", {"facing": N})]),
    # The alloyer on its fuel tank, tanks of what it alloys around it, its faucet over a table.
    "fantastic_foundry/alloyer/alloy.md": [
        b(1, 0, 0, "scorched_fuel_tank"), b(1, 1, 0, "scorched_alloyer", {"facing": N, "active": "true"}),
        b(0, 1, 0, "scorched_ingot_tank"), b(2, 1, 0, "scorched_ingot_tank"), b(1, 1, 1, "scorched_ingot_tank"),
        b(1, 0, 1, "scorched_bricks"), b(0, 0, 0, "scorched_bricks"), b(2, 0, 0, "scorched_bricks"),
        b(1, 1, -1, "scorched_faucet", {"facing": N}), b(1, 0, -1, "scorched_table", {"facing": N})],
    # Stations with the chests they use beside them.
    "materials_and_you/intro/partbuilder.md": station("part_chest", "part_builder", "tinkers_chest"),
    "materials_and_you/intro/tinkerstation.md": station("part_chest", "tinker_station", "tinkers_chest"),
    "materials_and_you/intro/storage.md": station("part_chest", "part_builder", "tinker_station", "tinkers_chest", "cast_chest"),
    "mighty_smelting/intro/tinkers_anvil.md": station("part_chest", "tinkers_anvil", "tinkers_chest"),
    "puny_smelting/worktable/index.md": station("modifier_worktable", "tinkers_chest"),
    # The slime islands in small.
    "tinkers_gadgetry/exploration/earthslime_island.md": island(
        "earth_earth_slime_grass", "earth_slime_dirt", "earth_congealed_slime", "greenheart_log", "earth_slime_leaves",
        ["earth_slime_tall_grass", "earth_slime_fern", "earth_slime_sapling"]),
    "tinkers_gadgetry/exploration/skyslime_island.md": island(
        "sky_sky_slime_grass", "sky_slime_dirt", "sky_congealed_slime", "skyroot_log", "sky_slime_leaves",
        ["sky_slime_tall_grass", "sky_slime_fern", "sky_slime_sapling"]),
    "tinkers_gadgetry/exploration/enderslime_island.md": island(
        "ender_ender_slime_grass", "ender_slime_dirt", "ender_congealed_slime", "enderbark_log", "ender_slime_leaves",
        ["ender_slime_tall_grass", "ender_slime_fern", "ender_slime_sapling"], under=[(2, 0, 0, "enderbark_roots", {})]),
    "tinkers_gadgetry/exploration/blood_island.md": island(
        "blood_ichor_slime_grass", "ichor_slime_dirt", "minecraft:magma_block", "bloodshroom_log", "blood_slime_leaves",
        ["blood_slime_tall_grass", "blood_slime_fern", "blood_slime_sapling"]),
    "tinkers_gadgetry/exploration/clay_island.md": island(
        "minecraft:grass_block", "minecraft:dirt", "minecraft:clay", "minecraft:oak_log", "minecraft:oak_leaves",
        ["minecraft:short_grass", "minecraft:fern"], under=[(0, 1, 1, "minecraft:clay", {}), (4, 1, 3, "minecraft:clay", {})]),
    # The geodes cut open.
    "tinkers_gadgetry/exploration/earthslime_geode.md": geode("earth", "minecraft:calcite", "minecraft:clay"),
    "tinkers_gadgetry/exploration/skyslime_geode.md": geode("sky", "minecraft:calcite", "minecraft:moss_block"),
    "tinkers_gadgetry/exploration/ichor_geode.md": geode("ichor", "minecraft:calcite", "minecraft:netherrack"),
    "tinkers_gadgetry/exploration/enderslime_geode.md": geode("ender", "minecraft:calcite", "minecraft:end_stone"),
    # Metal clusters grown in geodes.
    "tinkers_gadgetry/exploration/steel_shard.md": shard("sky", "steel_cluster"),
    "tinkers_gadgetry/exploration/knightmetal_shard.md": shard("ender", "knightmetal_cluster"),
    "tinkers_gadgetry/exploration/cobalt_shard.md": shard("ichor", "cobalt_cluster"),
    # Cobalt ore in a Nether wall beside ancient debris.
    "tinkers_gadgetry/exploration/cobalt_ore.md": [b(x, y, z, "minecraft:netherrack") for x in range(3) for y in range(2) for z in (1, 2)
                                                  if (x, y, z) not in ((1, 1, 1), (2, 0, 1))]
        + [b(1, 1, 1, "cobalt_ore"), b(2, 0, 1, "cobalt_ore"), b(0, 0, 0, "cobalt_ore"), b(1, 0, 0, "minecraft:ancient_debris"),
           b(2, 0, 0, "minecraft:netherrack"), b(0, 1, 0, "minecraft:netherrack")],
    # Slime grass on plain and slimy dirt, from slimy seeds.
    "tinkers_gadgetry/exploration/grass_seeds.md": [
        b(0, 0, 0, "earth_vanilla_slime_grass", {"snowy": "false"}), b(1, 0, 0, "sky_earth_slime_grass", {"snowy": "false"}),
        b(2, 0, 0, "ender_sky_slime_grass", {"snowy": "false"}), b(3, 0, 0, "blood_ichor_slime_grass", {"snowy": "false"}),
        b(4, 0, 0, "ichor_ender_slime_grass", {"snowy": "false"}),
        b(0, 1, 0, "earth_slime_tall_grass"), b(1, 1, 0, "sky_slime_fern"), b(2, 1, 0, "ender_slime_tall_grass"),
        b(3, 1, 0, "blood_slime_fern"), b(4, 1, 0, "ichor_slime_tall_grass")],
    # The slime cakes, one bitten.
    "tinkers_gadgetry/gadgets/cake.md": [b(x, 0, 0, f"{c}_cake", {"bites": "3" if x == 1 else "0"})
                                          for x, c in enumerate(["earth", "sky", "ichor", "blood", "ender", "magma"])],
}


# Pages about items, not blocks (tools, armour, modifiers, materials, casts): the blocks that make or change them, as
# a player would set them up. Small tools and armour are built in the tinker station, large tools and staffs need the
# anvil, modifiers go on at the station (the worktable extracts and sorts them), parts and materials come from the part
# builder, casts from the casting table and basin. The first pattern that matches a page wins.
TOPIC_SCENES = [
    (r"^(encyclopedia/tools/group_(large|staff|ancient)|tinkers_gadgetry/ancient_tools/)",
     station("part_chest", "tinkers_anvil", "tinkers_chest")),
    (r"^(encyclopedia/(tools|armor)/|materials_and_you/tools/|mighty_smelting/tools/)",
     station("part_chest", "tinker_station", "tinkers_chest")),
    (r"^puny_smelting/worktable/", station("modifier_worktable", "tinkers_chest")),
    (r"^(encyclopedia/(abilities|upgrades|defense|slotless)/|materials_and_you/modifiers/|"
     r"puny_smelting/(upgrades|slotless)/|mighty_smelting/(abilities|defense)/)",
     station("modifier_worktable", "tinker_station", "tinkers_chest")),
    (r"^(materials_and_you/intro/(hidden|introduction|.*_craft)|materials_and_you/further_reading/)",
     station("part_chest", "part_builder", "tinker_station", "tinkers_chest")),
    (r"^puny_smelting/casting/(gold_cast|other_cast|sand_cast|sand_cast3|sand_cast_craft)",
     [b(0, 0, 0, "seared_table", {"facing": N}), b(1, 0, 0, "seared_basin", {"facing": N}),
      b(2, 0, 0, "cast_chest", {"facing": N})]),
]


def topic_scene(page):
    """The scene for an item page (TOPIC_SCENES), or None."""
    import re
    return next((blocks for pattern, blocks in TOPIC_SCENES if re.search(pattern, page)), None)
