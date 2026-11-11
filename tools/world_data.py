"""Tinkers' world (spec-world.md W.2-W.3) in the form Horizon's 26.3 content loader reads.

`write(files, skipped)` runs after make_content has copied the jar's data and declared every block:
- the configured features in 26.3's form (`worldgen/feature/`, `config` unwrapped, block states `{id, properties}`,
  block state providers renamed, int providers without their `value` wrapper), as horizon-port-pack's
  `upgrade-datapack` rewrites them (crates/horizon-port-pack/src/upgrade/features.rs); the 1.20 `configured_feature/`
  copies go. Placed features read the same in 26.3 and stay;
- the Forge biome modifiers with Forge's holder sets (`forge:and`, `forge:or`, `forge:not`) as NeoForge's, which is
  what Horizon reads, and `#forge:` biome tags as the `#c:` ones make_content writes. The three spawn modifiers name
  Tinkers' slimes, which Horizon can't declare yet (no slime template, PLAN "Slimes and the world"): they stay out;
- the declarations the families in make_content get wrong: budding crystals (budding amethyst, not clusters), the
  crystals' light, the nether leaves (no decay), congealed slime (its collision, friction, strength), the slime
  blocks' and plants' strengths.
"""

import json

ID = "tconstruct"
PX = 1 / 16

# 26.2 block state provider types and their 26.3 names (upgrade/features.rs).
PROVIDERS = {
    "simple_state_provider": "simple_state_provider",
    "weighted_state_provider": "weighted",
    "rotated_block_provider": "rotated",
    "randomized_int_state_provider": "randomized_int",
    "rule_based_state_provider": "rule_based",
    "noise_provider": "noise",
    "dual_noise_provider": "dual_noise",
    "noise_threshold_provider": "noise_threshold",
}
# Int providers whose 1.20 form wraps their fields in `value` (26.3 reads them flat).
WRAPPED_INTS = {"uniform", "biased_to_bottom", "clamped", "clamped_normal"}
# Feature types only Tinkers' code places (no Horizon reader): converted all the same, listed in the report.
NATIVE_FEATURES = ("tconstruct:slime_tree", "tconstruct:slime_fungus")


def short(t):
    return t.split(":", 1)[1] if isinstance(t, str) and t.startswith("minecraft:") else t


def states(v):
    """`{"Name", "Properties"}` as 26.3's `{"id", "properties"}`, or the id alone."""
    if isinstance(v, dict):
        if isinstance(v.get("Name"), str) and set(v) <= {"Name", "Properties"}:
            props = v.get("Properties") or {}
            return {"id": v["Name"], "properties": props} if props else v["Name"]
        return {k: states(x) for k, x in v.items()}
    if isinstance(v, list):
        return [states(x) for x in v]
    return v


def nested(v):
    if isinstance(v, list):
        return [nested(x) for x in v]
    if not isinstance(v, dict):
        return v
    t = short(v.get("type"))
    if t in PROVIDERS:
        if t == "simple_state_provider":
            state = v.get("state")
            return {"id": state} if isinstance(state, str) else state
        v = {**v, "type": f"minecraft:{PROVIDERS[t]}"}
    if t in WRAPPED_INTS and isinstance(v.get("value"), dict):
        v = {"type": v["type"], **v["value"]}
    out = {}
    for k, x in v.items():
        if isinstance(x, dict) and "config" in x and "type" in x:
            out[k] = feature(x)
        else:
            out[k] = nested(x)
    return out


def feature(doc):
    out = {"type": doc["type"], **(doc.get("config") or {})}
    return nested(states(out))


def holder_set(v):
    """Forge's holder sets and tags as NeoForge's, which Horizon's biome modifiers read."""
    if isinstance(v, str):
        return "#c:" + v[len("#forge:"):] if v.startswith("#forge:") else v
    if isinstance(v, list):
        return [holder_set(x) for x in v]
    if isinstance(v, dict):
        out = {k: holder_set(x) for k, x in v.items()}
        if isinstance(out.get("type"), str) and out["type"].startswith("forge:"):
            out["type"] = "neoforge:" + out["type"][len("forge:"):]
        return out
    return v


def worldgen(files, skipped):
    prefix = f"data/{ID}/worldgen/configured_feature/"
    for name in [n for n in files if n.startswith(prefix)]:
        doc = json.loads(files.pop(name).decode("utf-8-sig"))
        rest = name[len(prefix):]
        files[f"data/{ID}/worldgen/feature/{rest}"] = json.dumps(feature(doc), indent=1).encode()
        if doc.get("type") in NATIVE_FEATURES or "tconstruct:" in json.dumps(
                [d.get("type") for d in doc.get("config", {}).get("decorators", [])] +
                [doc.get("config", {}).get("root_placer", {}).get("type")]):
            skipped.setdefault("features_native", []).append(rest[:-5])
    prefix = f"data/{ID}/forge/biome_modifier/"
    for name in [n for n in files if n.startswith(prefix)]:
        doc = json.loads(files[name].decode("utf-8-sig"))
        spawners = doc.get("spawners")
        if doc.get("type") == "forge:add_spawns" and any(
                s.get("type", "").startswith(f"{ID}:") for s in (spawners if isinstance(spawners, list) else [spawners])):
            del files[name]
            skipped.setdefault("spawns_need_slime_template", []).append(name[len(prefix):-5])
            continue
        doc["biomes"] = holder_set(doc.get("biomes"))
        files[name] = json.dumps(doc, indent=1).encode()


# GeodeItemObject: each geode's base light; the crystal block and budding block give it, the buds and the cluster more.
GEODES = {"earth": 3, "sky": 0, "ichor": 10, "ender": 7}
# (prefix, suffix, extra light, AmethystClusterBlock height, xz offset).
BUDS = [("small_", "_bud", 1, 3, 3), ("medium_", "_bud", 2, 4, 3), ("large_", "_bud", 4, 5, 3), ("", "_cluster", 5, 7, 3)]
SLIME_LIGHT = {"ichor": 10}


def cluster_shapes(height, offset):
    """AmethystClusterBlock's six shapes by `facing` (px: offset in from the sides, `height` out from the face)."""
    o, h = offset * PX, height * PX
    return {"property": "facing", "values": {
        "up": [[o, 0, o, 1 - o, h, 1 - o]],
        "down": [[o, 1 - h, o, 1 - o, 1, 1 - o]],
        "north": [[o, o, 1 - h, 1 - o, 1 - o, 1]],
        "south": [[o, o, 0, 1 - o, 1 - o, h]],
        "east": [[0, o, o, h, 1 - o, 1 - o]],
        "west": [[1 - h, o, o, 1, 1 - o, 1 - o]],
    }}


def declare(files, block, change):
    path = f"data/{ID}/horizon/block/{block}.json"
    if path not in files:
        return
    decl = json.loads(files[path])
    for k, v in change.items():
        if k == "properties":
            decl.setdefault("properties", {}).update(v)
        else:
            decl[k] = v
    files[path] = json.dumps(decl, indent=1).encode()


def blocks(files):
    for geode, light in GEODES.items():
        name = f"{geode}_slime_crystal"
        declare(files, f"{name}_block", {"template": "minecraft:amethyst_block",
                                         "properties": {"hardness": 1.5, "explosion_resistance": 1.5, "light": light}})
        # BuddingCrystalBlock: budding amethyst's random tick, but growing Tinkers' buds (the native mod's tick).
        declare(files, f"budding_{name}", {"template": "minecraft:budding_amethyst",
                                           "properties": {"hardness": 1.5, "explosion_resistance": 1.5,
                                                          "light": light}})
        for prefix, suffix, extra, height, offset in BUDS:
            declare(files, f"{prefix}{name}{suffix}", {"properties": {"light": min(light + extra, 15)},
                                                        "shapes": cluster_shapes(height, offset)})
    for slime in ("earth", "sky", "ichor", "ender"):
        # CongealedSlimeBlock: strength 0.5, friction 0.5, its 1..15 px collision (the outline stays full).
        declare(files, f"{slime}_congealed_slime", {
            "properties": {"hardness": 0.5, "explosion_resistance": 0.5, "friction": 0.5,
                           "light": SLIME_LIGHT.get(slime, 0)},
            "collision_shapes": {"default": [[PX, 0, PX, 1 - PX, 1 - PX, 1 - PX]]}})
        # SlimeDirtBlock: strength 1.9, slime sounds.
        declare(files, f"{slime}_slime_dirt", {"properties": {"hardness": 1.9, "explosion_resistance": 1.9,
                                                              "sounds": "minecraft:slime_block"}})
    declare(files, "ichor_slime", {"properties": {"light": 10}})
    # Slime grass and nylium: strength 2.0, slime sounds, the right tool.
    for foliage in ("earth", "sky", "ichor", "ender", "blood"):
        for dirt in ("earth", "sky", "ichor", "ender", "vanilla"):
            declare(files, f"{foliage}_{dirt}_slime_grass", {
                "properties": {"hardness": 2.0, "explosion_resistance": 2.0, "sounds": "minecraft:slime_block",
                               "requires_tool": True}})
    # The overworld slime leaves: strength 1.0. The nether ones are plain blocks (no decay): strength 1.5, wart sounds.
    for foliage in ("earth", "sky", "ender"):
        declare(files, f"{foliage}_slime_leaves", {"properties": {"hardness": 1.0, "explosion_resistance": 1.0}})
    for foliage in ("ichor", "blood"):
        declare(files, f"{foliage}_slime_leaves", {"template": "minecraft:nether_wart_block",
                                                   "properties": {"hardness": 1.5, "explosion_resistance": 1.5}})
    # SlimeVineBlock: strength 0.75, grass sounds.
    for vine in ("sky_slime_vine", "ender_slime_vine"):
        declare(files, vine, {"properties": {"hardness": 0.75, "explosion_resistance": 0.75,
                                             "sounds": "minecraft:short_grass"}})


def write(files, skipped):
    worldgen(files, skipped)
    blocks(files)
