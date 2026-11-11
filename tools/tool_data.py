"""What the content mod and the native mod need for Tinkers' materials and tool parts, from the TConstruct jar
(spec-tools.md sections 1, 2 and 5.1).

Called by make_content.py:
- `station_decl(name, decl)`: the stations' block declarations (TinkerTables: the wood tables 1 / 5 with wood's sounds,
  the anvils 5 / 1200 with the anvil's, no occlusion, TableBlock's and the anvils' shapes);
- `write(files, jar, fluids_path)`:
  - writes `tconstruct-tools.json` beside the fluid table (the bundle's data/), compiled into the native mod: the jar's
    material definitions, stats, traits and material tags as they are (the native mod reads the same files from the
    world's data packs through its reload listeners, and uses these only when no server in this process sent any:
    a client of another server), the text colours of `assets/tconstruct/mantle/colors.json` flattened to their keys,
    and each modifier's `level_display`; the station layouts and the tool definitions as they are (the native mod's
    reload listeners read the world's);
  - the stations' menus (`data/tconstruct/horizon/menu/`): their Java slots, a result slot players only take from, and
    the crafting station's and the part builder's side inventory (a double chest's 54);
  - the tools' stack sizes (TinkerTools: 1, the dagger 2, the arrow 64, the shuriken and throwing axe 16);
  - gives every part item (an item model with Tinkers' `tconstruct:material` loader) an item definition that picks
    the material's sprite from the stack's `minecraft:custom_data` `Material`: a `minecraft:select` on that component,
    one case a material variant (MaterialRenderInfo.getSprite: the generated sprite untinted, else the first fallback
    sprite or the base texture tinted with the render info's colour), the plain model for any other; the part model's
    `offset` as the select's transformation (MaterialModel: x/16, -y/16);
  - gives every tool (the `tconstruct:tool` loader, ToolModel) an item definition drawing its parts in the model's
    order, each a `minecraft:select` on `minecraft:custom_model_data` string i (the native mod mirrors `tic_materials`
    there, and `tic_broken` as flag 0: tconstruct.rs, `set_tool_render`) picking that material's sprite as for parts;
    large tools a `minecraft:display_context` select: the small layers in the GUI, the `large_` 32x32 layers
    (translated ((ox-8)/32, (-oy-8)/32), scaled 2x) everywhere else; broken tools the `tconstruct:broken` override's
    model (its `*_broken` textures). Each layer model's parent is the tool model's own (its hand transforms).
  - a material with `luminosity` draws its layer as explicit elements (the extruded sprite, as ItemModelGenerator
    builds it) with `light_emission` (Mantle's emissive item quads), since `item/generated` can't carry light.
"""

import io
import json
import pathlib
import re

ID = "tconstruct"
MATERIALS = f"data/{ID}/tinkering/materials/"
RENDER = f"assets/{ID}/tinkering/materials/"
TEXTURES = f"assets/{ID}/textures/"

# The part items and the stat type each takes (TinkerToolParts: ToolPartItem(statType)); the repair kit takes any
# material with repairable stats (RepairKitItem), the fake ingot and storage block the compatibility metals.
PART_STATS = {
    "pick_head": "head", "hammer_head": "head", "small_axe_head": "head", "broad_axe_head": "head",
    "small_blade": "head", "broad_blade": "head", "adze_head": "head", "large_plate": "head",
    "bow_limb": "limb", "bow_grip": "grip", "bowstring": "bowstring", "arrow_head": "arrow_head",
    "arrow_shaft": "arrow_shaft", "fletching": "fletching", "tool_binding": "binding", "tough_binding": "binding",
    "tool_handle": "handle", "tough_handle": "handle", "helmet_plating": "plating_helmet",
    "chestplate_plating": "plating_chestplate", "leggings_plating": "plating_leggings", "boots_plating": "plating_boots",
    "maille": "maille", "shield_core": "shield_core", "ribcage": "ribcage", "shell": "shell", "laces": "laces",
}
# MaterialStatType.canRepair (the repairable stat types).
REPAIRABLE = {"head", "limb", "plating_helmet", "plating_chestplate", "plating_leggings", "plating_boots",
              "plating_shield", "slime", "skull", "ribcage", "shell", "laces"}


def _px(*b):
    return [round(v / 16, 5) for v in b]


# TableBlock.TABLE_SHAPE: the top slab and four legs; TinkersAnvilBlock / ScorchedAnvilBlock: per axis of their facing.
_TABLE_SHAPE = [_px(0, 12, 0, 16, 16, 16), _px(0, 0, 0, 4, 15, 4), _px(12, 0, 0, 16, 15, 4), _px(12, 0, 12, 16, 15, 16),
                _px(0, 0, 12, 4, 15, 16)]
_ANVIL_X = [_px(2, 0, 2, 14, 4, 14), _px(4, 4, 3, 12, 5, 13), _px(6, 5, 4, 10, 10, 12), _px(3, 10, 0, 13, 16, 16)]
_ANVIL_Z = [_px(2, 0, 2, 14, 4, 14), _px(3, 4, 4, 13, 5, 12), _px(4, 5, 6, 12, 10, 10), _px(0, 10, 3, 16, 16, 13)]
_SCORCHED_X = [_px(2, 0, 2, 14, 4, 14), _px(4, 4, 5, 12, 7, 11), _px(5, 4, 2.5, 11, 10, 6.5), _px(5, 4, 9.5, 11, 10, 13.5),
               _px(3, 10, 0, 13, 16, 16)]
_SCORCHED_Z = [_px(2, 0, 2, 14, 4, 14), _px(5, 4, 4, 11, 7, 12), _px(2.5, 4, 5, 6.5, 10, 11), _px(9.5, 4, 5, 13.5, 10, 11),
               _px(0, 10, 3, 16, 16, 13)]
TABLES = ("crafting_station", "part_builder", "tinker_station")
# TinkerTables: the modifier worktable is a stone table (GenericTableBlock: stone sound, a tool needed, 3 / 9).
STONE_TABLES = ("modifier_worktable",)
ANVILS = {"tinkers_anvil": (_ANVIL_X, _ANVIL_Z), "scorched_anvil": (_SCORCHED_X, _SCORCHED_Z)}
# The stations' menus: slots, data slots and the result (spec-tools.md 3; tconstruct.rs, "The stations").
MENUS = {"crafting_station": {"slots": 64, "results": [9]}, "part_builder": {"slots": 57, "data_slots": 1, "results": [2]},
         "tinker_station": {"slots": 5, "data_slots": 1, "results": [4]},
         "tinkers_anvil": {"slots": 7, "data_slots": 1, "results": [6]},
         # ModifierWorktableContainerMenu: the tool, two inputs, the result; the selected modifier's index.
         "modifier_worktable": {"slots": 4, "data_slots": 1, "results": [3]}}
TOOL_STACKS = {"dagger": 2, "arrow": 64, "shuriken": 16, "throwing_axe": 16}
# The use states (TinkerItemProperties): the override predicates drawn, and what the native mod mirrors for them in
# `minecraft:custom_model_data` (tconstruct.rs, `set_tool_render`): float 0 the tool's charging value while in use,
# float 1 the crossbow's loaded ammo (1 arrow, 2 firework), string <material count> the ammo stack's item.
USE_KEYS = ("tconstruct:charging", "tconstruct:charge", "tconstruct:ammo", "tconstruct:cast")
USE_KIND_FLOAT, AMMO_KIND_FLOAT = 0, 1
# The ammo items a tool model draws (ToolModel's `ammo`: the stack's own model; Tinkers' arrow as the vanilla one).
AMMO_SPRITES = {"minecraft:arrow": ["minecraft:item/arrow"], "minecraft:spectral_arrow": ["minecraft:item/spectral_arrow"],
                "minecraft:tipped_arrow": ["minecraft:item/tipped_arrow_head", "minecraft:item/tipped_arrow_base"],
                "tconstruct:arrow": ["minecraft:item/arrow"], "minecraft:firework_rocket": ["minecraft:item/firework_rocket"]}
# TinkerEffects / TinkerModifiers' mob effects the traits give (category, colour); icons and names are the jar's.
MOB_EFFECTS = {"pierce": ("harmful", 13751162), "magnetic": ("beneficial", 7471104), "bleeding": ("harmful", 11010048),
               "enderference": ("harmful", 13860095), "momentum_harvest": ("beneficial", 6310251),
               "momentum_ranged": ("beneficial", 6310251), "momentum_armor": ("beneficial", 6310251),
               "insatiable_melee": ("beneficial", 9593292), "insatiable_ranged": ("beneficial", 9593292),
               "insatiable_armor": ("beneficial", 9593292)}


# The armor (TinkerTools, ArmorModelManager; tconstruct.rs, "Armor, shields and staffs"): each worn item's slot and
# armor model. Horizon draws a worn item by its `minecraft:equippable` asset (`assets/tconstruct/equipment/<model>.json`),
# whose layers `<model>_<i>` the native mod answers with the sprite of the piece's material (armor_layer_rect). Slime
# helmet (the skull) and wings are worn without a look of their own.
ARMOR_ITEMS = {
    "plate_helmet": ("head", "plate"), "plate_chestplate": ("chest", "plate"), "plate_leggings": ("legs", "plate"),
    "plate_boots": ("feet", "plate"), "travelers_helmet": ("head", "travelers"),
    "travelers_chestplate": ("chest", "travelers"), "travelers_leggings": ("legs", "travelers"),
    "travelers_boots": ("feet", "travelers"), "slime_helmet": ("head", None), "slimy_chestplate": ("chest", "slime"),
    "slime_leggings": ("legs", "slime"), "slime_boots": ("feet", "slime"), "slime_wings": ("chest", None),
}
# The equip sounds (TinkerArmor's materials: plate iron, travelers leather, slime its own).
ARMOR_SOUNDS = {"plate": "minecraft:item.armor.equip_iron", "travelers": "minecraft:item.armor.equip_leather",
                "slime": "tconstruct:equip.slime", None: "tconstruct:equip.slime"}
ARMOR_TYPES = ("armor", "leggings")


def _armor_location(prefix, kind, suffix=""):
    """ArmorTextureSupplier: `<ns>:tinker_armor/<path><kind><suffix>` as a sprite id."""
    ns, _, path = prefix.partition(":")
    return f"{ns}:tinker_armor/{path}{kind}{suffix}"


def _armor_layer(spec, names, infos):
    """One supplier of an armor model, as the native mod draws it: `fixed` (its sprite per texture type),
    `material` (per material variant the sprite MaterialArmorTextureSupplier picks, and the base), `first_present`
    (its first option that draws without a dye). Dyed layers need the `dyed` modifier and trims the `trim` one:
    none here."""
    def exists(sprite):
        ns, path = sprite.split(":", 1)
        return f"assets/{ns}/textures/{path}.png" in names

    if not isinstance(spec, dict):
        return None
    kind = spec.get("type")
    if kind == "tconstruct:first_present":
        for option in spec.get("options", []):
            layer = _armor_layer(option, names, infos)
            if layer:
                return layer
        return None
    if kind == "tconstruct:fixed" and isinstance(spec.get("prefix"), str):
        fixed = {t: _armor_location(spec["prefix"], t, spec.get("suffix", "")) for t in ARMOR_TYPES}
        fixed = {t: v for t, v in fixed.items() if exists(v)}
        return {"index": -1, "fixed": fixed} if fixed else None
    if kind == "tconstruct:material" and isinstance(spec.get("prefix"), str):
        layer = {"index": spec.get("index", 0), "base": {}, "materials": {}}
        for t in ARMOR_TYPES:
            base = _armor_location(spec["prefix"], t)
            if exists(base):
                layer["base"][t] = base
            own = {}
            for variant_id, info in sorted(infos.items()):
                sprite, _tint = _sprite(names, info, base)
                if sprite != base and exists(sprite):
                    own[variant_id] = sprite
            layer["materials"][t] = own
        return layer
    return None


def _armor_models(jar, names, infos):
    out = {}
    for model in sorted({m for _, m in ARMOR_ITEMS.values() if m}):
        doc = _json(jar, f"assets/{ID}/tinkering/armor_models/{model}.json") or {}
        out[model] = [layer for layer in (_armor_layer(s, names, infos) for s in doc.get("layers", [])) if layer]
    return out


def station_decl(name, decl):
    if name in TABLES:
        decl["properties"] = {"hardness": 1.0, "explosion_resistance": 5.0, "sounds": "minecraft:oak_planks",
                              "requires_tool": False, "light": 0, "occludes": False}
        decl["shapes"] = {"default": _TABLE_SHAPE}
        decl["collision_shapes"] = {"default": _TABLE_SHAPE}
    elif name in STONE_TABLES:
        decl["properties"] = {"hardness": 3.0, "explosion_resistance": 9.0, "sounds": "minecraft:stone",
                              "requires_tool": True, "light": 0, "occludes": False}
        decl["shapes"] = {"default": _TABLE_SHAPE}
        decl["collision_shapes"] = {"default": _TABLE_SHAPE}
    elif name in ANVILS:
        x, z = ANVILS[name]
        decl["properties"] = {"hardness": 5.0, "explosion_resistance": 1200.0, "sounds": "minecraft:anvil",
                              "requires_tool": True, "light": 0, "occludes": False}
        shape = {"property": "facing", "values": {"north": z, "south": z, "west": x, "east": x}}
        decl["shapes"] = shape
        decl["collision_shapes"] = shape
    return decl


def _json(jar, name):
    try:
        return json.loads(jar.read(name).decode("utf-8-sig"))
    except (KeyError, ValueError):
        return None


def _folder(jar, folder):
    """Every JSON file of `data/tconstruct/<folder>/` by its id (`tconstruct:<path>`), as a reload listener gets it."""
    out = {}
    for name in jar.namelist():
        if name.startswith(folder) and name.endswith(".json"):
            doc = _json(jar, name)
            if doc is not None:
                out[f"{ID}:{name[len(folder):-5]}"] = doc
    return dict(sorted(out.items()))


def _enchantment_modifiers(jar):
    """ModifierManager's enchantment map (`tinkering/enchantments_to_modifiers.json`): an enchantment id, or an
    enchantment tag (expanded here from the jar's `tags/enchantment/`), to its modifier; a trailing `?` optional."""
    doc = _json(jar, f"data/{ID}/tinkering/enchantments_to_modifiers.json") or {}

    def members(tag, seen):
        if tag in seen:
            return []
        seen.add(tag)
        ns, path = tag.split(":", 1) if ":" in tag else ("minecraft", tag)
        out = []
        for v in (_json(jar, f"data/{ns}/tags/enchantment/{path}.json") or {}).get("values", []):
            v = v.get("id") if isinstance(v, dict) else v
            if not isinstance(v, str):
                continue
            out += members(v[1:], seen) if v.startswith("#") else [v.rstrip("?")]
        return out

    out = {}
    for key, modifier in doc.items():
        key = key.rstrip("?")
        for enchantment in (members(key[1:], set()) if key.startswith("#") else [key]):
            out.setdefault(enchantment, modifier)
    return out


def _colors(jar):
    """Mantle's ResourceColorManager: nested objects joined with '.', `#RRGGBB` values, nulls skipped."""
    out = {}

    def walk(prefix, v):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(f"{prefix}.{k}" if prefix else k, x)
        elif isinstance(v, str) and re.fullmatch(r"#?[0-9a-fA-F]{6}", v):
            out[prefix] = int(v.lstrip("#"), 16)

    walk("", _json(jar, f"assets/{ID}/mantle/colors.json") or {})
    return out


def _render_infos(jar):
    """MaterialRenderInfoLoader: `<path>[/<variant>].json` as `tconstruct:<path>[#<variant>]` (the variant after the
    last '/'), each with its `parent`'s keys where it lacks them."""
    raw = {}
    for name in jar.namelist():
        if name.startswith(RENDER) and name.endswith(".json"):
            raw[name[len(RENDER):-5]] = _json(jar, name) or {}

    def resolved(path, depth=0):
        doc = dict(raw.get(path, {}))
        parent = doc.pop("parent", None)
        if isinstance(parent, str) and depth < 8:
            for k, v in resolved(parent.split(":", 1)[-1], depth + 1).items():
                doc.setdefault(k, v)
        return doc

    out = {}
    for path in raw:
        material, _, variant = path.rpartition("/")
        key = f"{ID}:{material}#{variant}" if material else f"{ID}:{path}"
        doc = resolved(path)
        # MaterialTextureField: the file's own id as `ns:path_variant` unless it names one (null: none).
        doc.setdefault("texture", key.replace("#", "_"))
        out[key] = doc
    return out


def _suffix(location):
    """MaterialRenderInfo.getSuffix: `path` for minecraft, else `ns_path`."""
    ns, _, path = location.partition(":")
    if not path:
        ns, path = "minecraft", ns
    return path if ns == "minecraft" else f"{ns}_{path}"


def _sprite(names, info, base):
    """MaterialRenderInfo.getSprite: (sprite, tint or None)."""
    texture = info.get("texture")
    color = int(info.get("color", "FFFFFFFF"), 16) & 0xFFFFFF

    def exists(sprite):
        ns, path = sprite.split(":", 1)
        return f"assets/{ns}/textures/{path}.png" in names

    if texture is not None and exists(f"{base}_{_suffix(texture)}"):
        return f"{base}_{_suffix(texture)}", None
    for fallback in info.get("fallbacks", []):
        if exists(f"{base}_{fallback}"):
            return f"{base}_{fallback}", color
    return base, color


def _usable(item, material, stats, tags):
    """IMaterialItem.canUseMaterial for the part items (material is a base id)."""
    have = {k.split(":", 1)[1] for k in (stats.get(material, {}).get("stats") or {})}
    if item in PART_STATS:
        return PART_STATS[item] in have
    if item == "repair_kit":
        return bool(have & (REPAIRABLE | {"repair_kit"}))
    if item == "fake_ingot":
        return material in tags.get(f"{ID}:compatibility_metals", set())
    return False


def _tag_members(tags):
    def members(tag, seen):
        if tag in seen:
            return set()
        seen.add(tag)
        out = set()
        for v in (tags.get(tag) or {}).get("values", []):
            v = v["id"] if isinstance(v, dict) else v
            out |= members(v[1:], seen) if v.startswith("#") else {v}
        return out

    return {t: members(t, set()) for t in tags}


# ---- Rendering (spec-tools.md 5)

# make_content.FORGE_PARENTS: Forge's item parents as vanilla's.
FORGE_PARENTS = {"forge:item/default": "minecraft:item/generated", "forge:item/default-tool": "minecraft:item/handheld"}
GENERATED = "minecraft:item/generated"
_IDENTITY_Q = [0.0, 0.0, 0.0, 1.0]


def _transform(translation, scale=(1.0, 1.0, 1.0)):
    return {"translation": [round(v, 6) for v in translation], "left_rotation": _IDENTITY_Q,
            "scale": list(scale), "right_rotation": _IDENTITY_Q}


# Vanilla 26.x's item/generated and item/handheld display transforms (the parents of every Tinkers' base model).
_VANILLA_DISPLAY = {
    "minecraft:item/generated": {
        "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.5, 0.5, 0.5]},
        "head": {"rotation": [0, 180, 0], "translation": [0, 13, 7], "scale": [1, 1, 1]},
        "thirdperson_righthand": {"rotation": [0, 0, 0], "translation": [0, 3, 1], "scale": [0.55, 0.55, 0.55]},
        "firstperson_righthand": {"rotation": [0, -90, 25], "translation": [1.13, 3.2, 1.13], "scale": [0.68, 0.68, 0.68]},
        "fixed": {"rotation": [0, 180, 0], "scale": [1, 1, 1]}},
    "minecraft:item/handheld": {
        "thirdperson_righthand": {"rotation": [0, -90, 55], "translation": [0, 4.0, 0.5], "scale": [0.85, 0.85, 0.85]},
        "thirdperson_lefthand": {"rotation": [0, 90, -55], "translation": [0, 4.0, 0.5], "scale": [0.85, 0.85, 0.85]},
        "firstperson_righthand": {"rotation": [0, -90, 25], "translation": [1.13, 3.2, 1.13], "scale": [0.68, 0.68, 0.68]},
        "firstperson_lefthand": {"rotation": [0, 90, -25], "translation": [1.13, 3.2, 1.13], "scale": [0.68, 0.68, 0.68]}},
}
_VANILLA_PARENTS = {"minecraft:item/handheld": "minecraft:item/generated"}
_LEFT = {"thirdperson_lefthand": "thirdperson_righthand", "firstperson_lefthand": "firstperson_righthand"}
_CONTEXTS = ("thirdperson_lefthand", "thirdperson_righthand", "firstperson_lefthand", "firstperson_righthand", "head",
             "gui", "ground", "fixed", "on_shelf")


def _chain_display(jar, model, own=None):
    """BlockModel.getTransforms for a model (its own display first, then its parents'): context -> transform, a missing
    left hand taking the right's (ItemTransforms)."""
    found = dict(own or {})
    cur, seen = model, 0
    while isinstance(cur, str) and seen < 16:
        seen += 1
        cur = FORGE_PARENTS.get(cur, cur)
        cur = cur if ":" in cur else f"minecraft:{cur}"
        if cur in _VANILLA_DISPLAY:
            doc = {"display": _VANILLA_DISPLAY[cur], "parent": _VANILLA_PARENTS.get(cur)}
        else:
            ns, path = cur.split(":", 1)
            doc = _json(jar, f"assets/{ns}/models/{path}.json") or {}
        for k, v in (doc.get("display") or {}).items():
            found.setdefault(k, v)
        cur = doc.get("parent")
    for left, right in _LEFT.items():
        if left not in found and right in found:
            found[left] = found[right]
    return found


def _mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _display_matrix(t, left):
    """item_bake.rs `item_transform_matrix` (ItemTransform.apply, then the -0.5 centring) and its inverse."""
    import math
    t = t or {}
    rx, ry, rz = [math.radians(v) for v in (t.get("rotation") or [0, 0, 0])]
    tx, ty, tz = [v / 16 for v in (t.get("translation") or [0, 0, 0])]
    sx, sy, sz = t.get("scale") or [1, 1, 1]
    if left:
        tx, ry, rz = -tx, -ry, -rz
    cx, sxn, cy, syn, cz, szn = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    rxm = [[1, 0, 0], [0, cx, -sxn], [0, sxn, cx]]
    rym = [[cy, 0, syn], [0, 1, 0], [-syn, 0, cy]]
    rzm = [[cz, -szn, 0], [szn, cz, 0], [0, 0, 1]]
    r3 = [[sum(a * b for a, b in zip(row, col)) for col in zip(*rym)] for row in rxm]
    r3 = [[sum(a * b for a, b in zip(row, col)) for col in zip(*rzm)] for row in r3]

    def affine(m3, tr):
        return [m3[0] + [tr[0]], m3[1] + [tr[1]], m3[2] + [tr[2]], [0, 0, 0, 1]]
    ident = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    fwd = _mat_mul(_mat_mul(affine(ident, [tx, ty, tz]), affine(r3, [0, 0, 0])),
                   _mat_mul(affine([[sx, 0, 0], [0, sy, 0], [0, 0, sz]], [0, 0, 0]), affine(ident, [-0.5, -0.5, -0.5])))
    if 0 in (sx, sy, sz):
        return fwd, None
    rt = [list(r) for r in zip(*r3)]
    inv = _mat_mul(_mat_mul(affine(ident, [0.5, 0.5, 0.5]), affine([[1 / sx, 0, 0], [0, 1 / sy, 0], [0, 0, 1 / sz]], [0, 0, 0])),
                   _mat_mul(affine(rt, [0, 0, 0]), affine(ident, [-tx, -ty, -tz])))
    return fwd, inv


def _display_variant(jar, node, parent, display):
    """A display-only override (blocking, throwing): 26.3 draws a layer as its model's display transform times the
    node's, so the base tool's tree is drawn, in each context the variant changes, under base⁻¹ · variant."""
    base = _chain_display(jar, parent)
    variant = _chain_display(jar, parent, display)
    groups = {}
    for ctx in _CONTEXTS:
        if json.dumps(base.get(ctx), sort_keys=True) == json.dumps(variant.get(ctx), sort_keys=True):
            continue
        left = ctx in _LEFT
        _, inv = _display_matrix(base.get(ctx), left)
        fwd, _ = _display_matrix(variant.get(ctx), left)
        if inv is None:
            continue
        m = _mat_mul(inv, fwd)
        flat = [round(v, 6) + 0.0 for row in m for v in row]
        groups.setdefault(json.dumps(flat), (flat, []))[1].append(ctx)
    if not groups:
        return node
    cases = [{"when": ctxs if len(ctxs) > 1 else ctxs[0],
              "model": {"type": "minecraft:composite", "models": [node], "transformation": flat}}
             for flat, ctxs in groups.values()]
    return {"type": "minecraft:select", "property": "minecraft:display_context", "cases": cases, "fallback": node}


def _extruded(png, mcmeta, light):
    """ItemModelGenerator.bakeExtrudedSprite as model elements: the front and back face, and a thin side face per
    opaque pixel edge (over every animation frame), each lit by `light` (Mantle's emissive item quads)."""
    from PIL import Image  # only for the few luminous materials
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    w, h = image.size
    frame_h = w
    try:
        anim = (json.loads(mcmeta.decode("utf-8-sig")) if mcmeta else {}).get("animation", {})
        frame_h = int(anim.get("height", anim.get("width", w))) if mcmeta else h
    except (ValueError, AttributeError):
        frame_h = w if mcmeta else h
    frame_h = max(1, min(frame_h, h))
    alpha = image.getchannel("A").load()
    frames = max(1, h // frame_h)

    def clear(f, x, y):
        return x < 0 or y < 0 or x >= w or y >= frame_h or alpha[x, f * frame_h + y] == 0

    sx, sy = 16 / w, 16 / frame_h
    face = {"texture": "#layer0", "tintindex": 0}
    out = [{"from": [0, 0, 7.5], "to": [16, 16, 8.5], "light_emission": light,
            "faces": {"south": {**face, "uv": [0, 0, 16, 16]}, "north": {**face, "uv": [16, 0, 0, 16]}}}]
    edges = set()
    for f in range(frames):
        for y in range(frame_h):
            for x in range(w):
                if clear(f, x, y):
                    continue
                for side, (dx, dy) in (("up", (0, 1)), ("down", (0, -1)), ("left", (1, 0)), ("right", (-1, 0))):
                    if clear(f, x - dx, y - dy):
                        edges.add((y, x, side))
    r = lambda v: round(v, 4)  # noqa: E731
    for y, x, side in sorted(edges):
        u0, u1 = x + 0.1, x + 0.9
        v0, v1 = (y + 0.1, y + 0.9) if side in ("up", "down") else (y + 0.9, y + 0.1)
        x0, x1, y0, y1 = x * sx, (x + 1) * sx, 16 - y * sy, 16 - (y + 1) * sy
        if side == "up":
            a, b, d = [x0, y0, 7.5], [x1, y0, 8.5], "up"
        elif side == "down":
            a, b, d = [x0, y1, 7.5], [x1, y1, 8.5], "down"
        elif side == "left":  # SpanFacing.LEFT faces EAST, from above to below (vanilla's winding)
            a, b, d = [x0, y0, 7.5], [x0, y1, 8.5], "east"
        else:
            a, b, d = [x1, y0, 7.5], [x1, y1, 8.5], "west"
        out.append({"from": [r(v) for v in a], "to": [r(v) for v in b], "light_emission": light,
                    "faces": {d: {**face, "uv": [r(u0 * sx), r(v0 * sy), r(u1 * sx), r(v1 * sy)]}}})
    return out


class _Layers:
    """The layer models the item definitions name: one per (parent, sprite, light), and the leaf nodes for them."""

    def __init__(self, jar, names):
        self.jar, self.names, self.models = jar, names, {}

    def leaf(self, parent, sprite, tint=None, light=0):
        ns, path = sprite.split(":", 1)
        rel = path.removeprefix("item/") if ns == ID else f"{ns}/{path}"
        if parent == GENERATED:
            folder = "hz_material"
        else:
            pns, ppath = parent.split(":", 1)
            folder = "hz_tool/" + (ppath.removeprefix("item/") if pns == ID else f"{pns}_{ppath.removeprefix('item/')}").replace("/", "_")
        model = f"{ID}:item/{folder}/{rel}" + (f"_glow{light}" if light else "")
        if model not in self.models:
            doc = {"parent": parent, "textures": {"layer0": sprite}}
            png = f"assets/{ns}/textures/{path}.png"
            if light and png in self.names:
                doc["textures"]["particle"] = sprite
                mcmeta = self.jar.read(png + ".mcmeta") if png + ".mcmeta" in self.names else None
                doc["elements"] = _extruded(self.jar.read(png), mcmeta, light)
            self.models[model] = doc
        node = {"type": "minecraft:model", "model": model}
        if tint is not None and tint != 0xFFFFFF:
            node["tints"] = [{"type": "minecraft:constant", "value": tint}]
        return node

    def material(self, parent, base, info):
        """MaterialModel.getMaterialSprite: the render info's sprite (none: the base texture, untinted)."""
        if info is None:
            return self.leaf(parent, base)
        sprite, tint = _sprite(self.names, info, base)
        return self.leaf(parent, sprite, tint, int(info.get("luminosity", 0) or 0))

    def write(self, files):
        for model, doc in self.models.items():
            files[f"assets/{ID}/models/{model.split(':', 1)[1]}.json"] = json.dumps(doc, separators=(",", ":")).encode()


def _cases(layers, parent, base, candidates, infos):
    """A select's cases: the candidate materials grouped by what they draw."""
    groups = {}
    for vid in candidates:
        node = layers.material(parent, base, infos[vid])
        groups.setdefault(json.dumps(node, sort_keys=True), (node, []))[1].append(vid)
    return [{"when": ids if len(ids) > 1 else ids[0], "model": node} for node, ids in groups.values()]


def _tool_stat_types(tool_def):
    """The stat type of each material index (ToolDefinition's part_stats / material_stats), None when unknown."""
    for module in (tool_def or {}).get("modules", []):
        if module.get("type") == "tconstruct:part_stats":
            out = []
            for p in module.get("parts", []):
                item = p if isinstance(p, str) else (p.get("item") or p.get("part") or "")
                out.append(PART_STATS.get(item.split(":", 1)[-1]))
            return out
        if module.get("type") == "tconstruct:material_stats":
            out = []
            for s in module.get("stat_types", []):
                s = s if isinstance(s, str) else s.get("stat", "")
                out.append(s.split(":", 1)[-1] or None)
            return out
    return []


def _modifier_maps(jar):
    """ModifierModelMapManager: `assets/<ns>/tinkering/modifiers/sprites/<path>.json` as map id -> {modifier: model}
    (the `modifiers` part; `constant` models need dyes, materials or fluids and aren't drawn)."""
    out = {}
    for name in sorted(jar.namelist()):
        m = re.match(r"assets/([a-z0-9_.-]+)/tinkering/modifiers/sprites/(.+)\.json$", name)
        if m:
            out[f"{m.group(1)}:{m.group(2)}"] = (_json(jar, name) or {}).get("modifiers") or {}
    return out


def _basic_models(model):
    """ModifierModelLoadable.COMPACT's basic models of `model` (a texture, an object without a type, `basic`, or the
    basic parts of a compound list); fluid, tank, dyed and material layers need the tool's own data and are left out."""
    if isinstance(model, str):
        return [{"texture": model}]
    if isinstance(model, list):
        return [b for m in model for b in _basic_models(m)]
    if isinstance(model, dict) and model.get("type", "tconstruct:basic") in ("tconstruct:basic", "basic"):
        return [model]
    if isinstance(model, dict) and model.get("type") in ("tconstruct:compound", "compound"):
        return _basic_models(model.get("models") or [])
    return []


def modifier_flags(jar):
    """The modifiers with a drawable layer on some tool, in order: modifier i is `minecraft:custom_model_data` flag 1 + i
    (flag 0 is broken), which the native mod sets for the tool's visible upgrades (tconstruct.rs, `set_tool_render`)."""
    ids = set()
    for mods in _modifier_maps(jar).values():
        ids |= {k for k, v in mods.items() if _basic_models(v)}
    legacy = _json(jar, f"assets/{ID}/tinkering/modifiers.json") or {}
    ids |= {k for k, v in legacy.items() if (v if isinstance(v, str) else (v or {}).get("type")) == f"{ID}:normal"}
    return sorted(ids)


def _tool_items(files, jar, names, infos, definition, stats, tool_definitions, layers):
    """ToolModel as 26.3 item definitions (see the module's docstring)."""
    with_stat = {}
    for mid, doc in stats.items():
        for k in (doc.get("stats") or {}):
            with_stat.setdefault(k.split(":", 1)[-1], set()).add(mid)
    drawable = [vid for vid in sorted(infos) if vid.split("#", 1)[0] in definition
                and vid.split("#", 1)[0] != f"{ID}:ui_render"]
    unknown = infos.get(f"{ID}:unknown")
    count = 0
    maps = _modifier_maps(jar)
    flags = {m: i + 1 for i, m in enumerate(modifier_flags(jar))}
    legacy = _json(jar, f"assets/{ID}/tinkering/modifiers.json") or {}

    def layer(parent, base, index, stat):
        if index < 0:
            return layers.leaf(parent, base)
        allowed = with_stat.get(stat) if stat else None
        candidates = [v for v in drawable if allowed is None or v.split("#", 1)[0] in allowed]
        node = {"type": "minecraft:select", "property": "minecraft:custom_model_data", "index": index,
                "fallback": layers.material(parent, base, unknown)}
        cases = _cases(layers, parent, base, candidates, infos)
        if not cases:
            return node["fallback"]
        node["cases"] = cases
        return node

    def composite(nodes, transformation=None):
        if len(nodes) == 1 and transformation is None:
            return nodes[0]
        out = {"type": "minecraft:composite", "models": nodes}
        if transformation:
            out["transformation"] = transformation
        return out

    def merged_models(doc):
        """ToolModel's modifier models: the maps from the last to the first (earlier ones override, `[]` removes),
        then the legacy roots for the `normal` modifiers of `modifiers.json` no map covers (the first root that has
        `<root><ns>_<path>`); each modifier's (small, large) basic layers."""
        merged = {}
        for map_id in reversed(doc.get("modifier_maps") or []):
            merged.update(maps.get(map_id if ":" in map_id else f"minecraft:{map_id}", {}))
        roots = doc.get("modifier_roots") or []
        small_roots, large_roots = (roots.get("small") or [], roots.get("large") or []) if isinstance(roots, dict) else (roots, [])
        out = {}
        for mod, model in merged.items():
            if model != []:
                out[mod] = [(b.get("texture"), b.get("texture_large"), b.get("color", -1), b.get("luminosity", 0)) for b in _basic_models(model)]
        for mod, kind in legacy.items():
            kind_id = kind if isinstance(kind, str) else (kind or {}).get("type")
            if mod in merged or kind_id != f"{ID}:normal":
                continue
            ns, path = mod.split(":", 1)

            def found(rs):
                return next((f"{r}{ns}_{path}" for r in rs if texture_exists(f"{r}{ns}_{path}")), None)
            small, large = found(small_roots), found(large_roots)
            if small or large:
                out[mod] = [(small, large, -1, 0 if isinstance(kind, str) else int(kind.get("luminosity", 0) or 0))]
        return out

    def texture_exists(sprite):
        tns, tpath = sprite.split(":", 1) if ":" in sprite else ("minecraft", sprite)
        return f"assets/{tns}/textures/{tpath}.png" in names

    def modifier_nodes(parent, models, large):
        """ToolModel.addModifierQuads: each modifier's layers over the parts, shown by its custom model data flag."""
        out = []
        for mod in sorted(models, key=lambda m: flags.get(m, 1 << 30)):
            if mod not in flags:
                continue
            leaves = []
            for small, big, color, light in models[mod]:
                sprite = big if large else small
                if not sprite or not texture_exists(sprite):
                    continue
                tint = (color & 0xFFFFFF) if isinstance(color, int) and color != -1 else None
                leaves.append(layers.leaf(parent, sprite, tint, int(light or 0)))
            if leaves:
                out.append({"type": "minecraft:condition", "property": "minecraft:custom_model_data", "index": flags[mod],
                            "on_true": composite(leaves), "on_false": {"type": "minecraft:empty"}})
        return out

    def ammo_node(parent, doc, ammo_index, large):
        """ToolModel's `ammo`: the stack under the persistent key (the drawn arrow, the loaded crossbow's) drawn on the
        tool, rotated -180 about Y when flipped, at the small or large offset (BakedToolModel); the left hand's a pixel
        the other side. The native mod mirrors that stack's item as custom model data string `ammo_index`."""
        ammo = doc.get("ammo")
        if not isinstance(ammo, dict) or ammo_index is None:
            return None
        f = 1.0 if ammo.get("flip") else 0.0
        rot = [0.0, -1.0, 0.0, 0.0] if f else _IDENTITY_Q
        sx, sy = (ammo.get("small_offset") or ammo.get("offset") or [0, 0])[:2]
        if large:
            ox, oy = (doc.get("large_offset") or [0, 0])[:2]
            lx, ly = (ammo.get("large_offset") or ammo.get("offset") or [0, 0])[:2]
            t = [(ox / 2 + lx + 4) / 16 + f, (-oy / 2 - ly + 4) / 16, 0.0625 + f]
        else:
            t = [sx / 16 + f, -sy / 16, 0.0625 + f]

        def placed(z):
            cases = []
            for item, sprites in AMMO_SPRITES.items():
                leaves = [layers.leaf(parent, s) for s in sprites]
                cases.append({"when": item, "model": composite(leaves)})
            return {"type": "minecraft:select", "property": "minecraft:custom_model_data", "index": ammo_index,
                    "cases": cases, "fallback": {"type": "minecraft:empty"},
                    "transformation": {**_transform((t[0], t[1], z)), "left_rotation": rot}}
        right = placed(t[2])
        if not ammo.get("left"):
            return right
        return {"type": "minecraft:select", "property": "minecraft:display_context",
                "cases": [{"when": ["thirdperson_lefthand", "firstperson_lefthand"], "model": placed(-0.0625 + f)}],
                "fallback": right}

    def tool_node(doc, stat_types, parent_override=None):
        parent = doc.get("parent") or GENERATED
        parent = parent_override or FORGE_PARENTS.get(parent, parent)
        textures = doc.get("textures") or {}
        parts = doc.get("parts") or [{"name": "tool"}]
        models = merged_models(doc)
        ammo_index = len(stat_types) if stat_types else None

        def layers_of(prefix):
            out = []
            for p in parts:
                base = textures.get(prefix + p.get("name", ""))
                if isinstance(base, str) and ":" in base:
                    index = int(p.get("index", -1))
                    out.append(layer(parent, base, index, stat_types[index] if 0 <= index < len(stat_types) else None))
            return out

        small_ammo = ammo_node(parent, doc, ammo_index, False)
        small = composite(layers_of("") + modifier_nodes(parent, models, False) + ([small_ammo] if small_ammo else []))
        if not doc.get("large"):
            return small
        large_layers = layers_of("large_")
        if large_layers:
            large_layers += modifier_nodes(parent, models, True)
        if not large_layers:
            return small
        ox, oy = (doc.get("large_offset") or [0, 0])[:2]
        large = composite(large_layers, _transform(((ox - 8) / 32, (-oy - 8) / 32, 0.0), (2.0, 2.0, 1.0)))
        large_ammo = ammo_node(parent, doc, ammo_index, True)
        if large_ammo:
            large = {"type": "minecraft:composite", "models": [large, large_ammo]}
        # BakedToolModel.applyTransform: the GUI draws the small model, every other context the large one.
        return {"type": "minecraft:select", "property": "minecraft:display_context",
                "cases": [{"when": "gui", "model": small}], "fallback": large}

    def variant_node(model_id, stat_types, memo):
        """An override's model: a `tconstruct:tool` model of its own (pulling_1, firework), or a display variant
        (blocking, throwing: a parent chain up to one, with display transforms of its own), drawn as that tool model
        under a parent with the merged display (the layers keep the tool model's hand transforms elsewhere)."""
        if model_id in memo:
            return memo[model_id]
        display, cur, tool_doc = {}, model_id, None
        for _ in range(12):
            if not isinstance(cur, str):
                break
            cns, cpath = cur.split(":", 1) if ":" in cur else ("minecraft", cur)
            vdoc = _json(jar, f"assets/{cns}/models/{cpath}.json")
            if not isinstance(vdoc, dict):
                break
            if vdoc.get("loader") == "tconstruct:tool":
                tool_doc = vdoc
                break
            for k, v in (vdoc.get("display") or {}).items():
                display.setdefault(k, v)
            cur = vdoc.get("parent")
        if tool_doc is None:
            memo[model_id] = None
            return None
        node = tool_node(tool_doc, stat_types)
        if display:
            node = _display_variant(jar, node, tool_doc.get("parent") or GENERATED, display)
        memo[model_id] = node
        return node

    def use_state_node(doc, base, stat_types):
        """TinkerItemProperties' overrides as 26.3 nodes (the last override whose predicates all hold wins, each
        predicate holding at or above its value):
        - `tconstruct:charging`: `minecraft:using_item`, then custom model data float 0 = what the tool's use is
          (1 drawing, 1.75 throwing, 2 blocking; tconstruct.rs, `set_tool_render`);
        - `tconstruct:charge`: `minecraft:crossbow/pull` (held / the drawtime: the native mod answers the charge time
          of a Tinkers' tool, `charge_ticks`), 0 when not in use;
        - `tconstruct:ammo`: custom model data float 1 (1 arrow, 2 firework loaded in a crossbow);
        - `tconstruct:cast`: `minecraft:fishing_rod/cast`."""
        overrides = [(o.get("predicate") or {}, o.get("model")) for o in doc.get("overrides", [])
                     if isinstance(o.get("model"), str) and "tconstruct:broken" not in (o.get("predicate") or {})]
        overrides = [(p, m) for p, m in overrides if p and set(p) <= set(USE_KEYS)]
        if not overrides:
            return base
        memo = {}

        def node_for(mid):
            n = variant_node(mid, stat_types, memo) if mid else None
            return n if n is not None else base

        def values(key):
            return sorted({float(p[key]) for p, _ in overrides if key in p})

        def resolve(state):
            best = None
            for p, m in overrides:
                if all(state.get(k, 0.0) >= float(v) for k, v in p.items()):
                    best = m
            return best

        def ranged(prop, index, thresholds, at):
            """A range_dispatch over `thresholds` of the property, each entry `at(threshold)` (model ids or nodes),
            the fallback `at(0)`; one model everywhere is that model alone."""
            fallback = at(0.0)
            entries = [(t, at(t)) for t in thresholds if t > 0]
            if all(json.dumps(e, sort_keys=True) == json.dumps(fallback, sort_keys=True) for _, e in entries):
                return fallback
            out = {"type": "minecraft:range_dispatch", "property": prop,
                   "entries": [{"threshold": t, "model": e} for t, e in entries], "fallback": fallback}
            if index is not None:
                out["index"] = index
            return out

        def tree(state):
            charge = values("tconstruct:charge")
            if not state.get("tconstruct:charging") or not charge:
                return node_for(resolve(state))
            return ranged("minecraft:crossbow/pull", None, charge,
                          lambda t: node_for(resolve({**state, "tconstruct:charge": t})))

        def using(state):
            kinds = values("tconstruct:charging")
            idle = tree(state)
            if not kinds:
                return idle
            in_use = ranged("minecraft:custom_model_data", USE_KIND_FLOAT, kinds,
                            lambda k: tree({**state, "tconstruct:charging": k}))
            if json.dumps(in_use, sort_keys=True) == json.dumps(idle, sort_keys=True):
                return idle
            return {"type": "minecraft:condition", "property": "minecraft:using_item", "on_true": in_use, "on_false": idle}

        def loaded(state):
            ammo = values("tconstruct:ammo")
            if not ammo:
                return using(state)
            return ranged("minecraft:custom_model_data", AMMO_KIND_FLOAT, ammo,
                          lambda a: using({**state, "tconstruct:ammo": a}))

        if not values("tconstruct:cast"):
            return loaded({})
        return {"type": "minecraft:condition", "property": "minecraft:fishing_rod/cast",
                "on_true": loaded({"tconstruct:cast": 1.0}), "on_false": loaded({})}

    for name in sorted(names):
        m = re.match(rf"assets/{ID}/models/item/([a-z0-9_]+)\.json$", name)
        if not m:
            continue
        doc = _json(jar, name) or {}
        if doc.get("loader") != "tconstruct:tool":
            continue
        item = m.group(1)
        stat_types = _tool_stat_types(tool_definitions.get(f"{ID}:{item}"))
        node = use_state_node(doc, tool_node(doc, stat_types), stat_types)
        broken = next((o.get("model") for o in doc.get("overrides", [])
                       if (o.get("predicate") or {}) == {"tconstruct:broken": 1}), None)
        if isinstance(broken, str):
            bns, bpath = broken.split(":", 1) if ":" in broken else ("minecraft", broken)
            bdoc = _json(jar, f"assets/{bns}/models/{bpath}.json")
            if isinstance(bdoc, dict) and bdoc.get("loader") == "tconstruct:tool":
                # TinkerItemProperties.BROKEN: `tic_broken`, mirrored as custom model data flag 0.
                node = {"type": "minecraft:condition", "property": "minecraft:custom_model_data", "index": 0,
                        "on_true": tool_node(bdoc, stat_types), "on_false": node}
        files[f"assets/{ID}/items/{item}.json"] = json.dumps({"model": node}, separators=(",", ":")).encode()
        count += 1
    return count


def write(files, jar, fluids_path=None):
    names = set(jar.namelist())
    definition = _folder(jar, MATERIALS + "definition/")
    stats = _folder(jar, MATERIALS + "stats/")
    traits = _folder(jar, MATERIALS + "traits/")
    tags = _folder(jar, f"data/{ID}/tinkering/tags/materials/")
    modifiers = {}
    modifier_files = _folder(jar, f"data/{ID}/tinkering/modifiers/")
    for mid, doc in modifier_files.items():
        if isinstance(doc, dict) and "level_display" in doc:
            modifiers[mid] = doc["level_display"]
    layouts = _folder(jar, f"data/{ID}/tinkering/station_layouts/")
    tool_definitions = _folder(jar, f"data/{ID}/tinkering/tool_definitions/")
    # The modifiers (ModifierManager: `tinkering/modifiers`, `tinkering/tags/modifiers`), as the native mod's reload
    # listeners read the world's; these for a client of another server (spec-modifiers.md 1).
    table = {"definition": definition, "stats": stats, "traits": traits, "tags": tags, "colors": _colors(jar),
             "level_display": modifiers, "layouts": layouts, "tool_definitions": tool_definitions,
             "modifiers": modifier_files, "modifier_tags": _folder(jar, f"data/{ID}/tinkering/tags/modifiers/"),
             "enchantment_modifiers": _enchantment_modifiers(jar),
             "modifier_icons": _json(jar, f"assets/{ID}/tinkering/modifier_icons.json") or {},
             # The modifier layers' custom model data flags (flag 1 + i; tconstruct.rs, `set_tool_render`).
             "modifier_model_flags": modifier_flags(jar)}
    for menu, doc in MENUS.items():
        files[f"data/{ID}/horizon/menu/{menu}.json"] = json.dumps(doc, indent=2).encode()
    # The traits' mob effects (TinkerEffects, TinkerModifiers: category and colour); the native mod gives and reads them.
    for name, (category, color) in MOB_EFFECTS.items():
        files[f"data/{ID}/horizon/mob_effect/{name}.json"] = json.dumps({"category": category, "color": color}).encode()
    for tool_id in tool_definitions:
        tool = tool_id.split(":", 1)[1]
        decl = f"data/{ID}/horizon/item/{tool}.json"
        if decl in files:
            doc = json.loads(files[decl])
            doc["max_stack_size"] = TOOL_STACKS.get(tool, 1)
            # Horizon reads a tool's harvest from the item's `minecraft:tool`, not the stack's: one rule makes the
            # definition's `is_effective` tag correct for drops, with no speed and no wear of its own. The native mod
            # gives each stack its speed and tier there, and its wear (tconstruct.rs, "Tools").
            effective = next((m for m in (tool_definitions[tool_id] or {}).get("modules", [])
                              if m.get("type") == "tconstruct:is_effective" and m.get("predicate_type") == "mantle:tag"), None)
            if effective and isinstance(effective.get("tag"), str):
                tag = effective["tag"] if ":" in effective["tag"] else "minecraft:" + effective["tag"]
                tag = "c:" + tag[len("forge:"):] if tag.startswith("forge:") else tag
                doc["components"] = {"minecraft:tool": {"rules": [{"blocks": "#" + tag, "correct_for_drops": True}],
                                                        "default_mining_speed": 1.0, "damage_per_block": 0}}
            if tool in ARMOR_ITEMS:
                slot, model = ARMOR_ITEMS[tool]
                equip = {"slot": slot, "equip_sound": ARMOR_SOUNDS[model], "damage_on_hurt": False}
                if model:
                    equip["asset_id"] = f"{ID}:{model}"
                doc.setdefault("components", {})["minecraft:equippable"] = equip
            files[decl] = json.dumps(doc, indent=1).encode()
    # The worn armor's look: its layers per material, and one equipment asset per model naming them.
    armor_models = _armor_models(jar, names, _render_infos(jar))
    table["armor_models"] = armor_models
    for model, layers in armor_models.items():
        named = [{"texture": f"{ID}:{model}_{i}"} for i in range(len(layers))]
        files[f"assets/{ID}/equipment/{model}.json"] = json.dumps(
            {"layers": {"humanoid": named, "humanoid_leggings": named}}, indent=1).encode()
    if fluids_path:
        pathlib.Path(fluids_path).with_name("tconstruct-tools.json").write_text(
            json.dumps(table, sort_keys=True, separators=(",", ":")), encoding="utf8")
    # The part items' models: a select on the stack's custom data, one case a material variant.
    infos = _render_infos(jar)
    # Variants named only by the material recipes (goat horns...) draw with their base material's render info.
    for name in sorted(names):
        if name.startswith(f"data/{ID}/recipes/") and name.endswith(".json"):
            doc = _json(jar, name) or {}
            for key in ("material", "output"):
                v = doc.get(key)
                if doc.get("type") in ("tconstruct:material", "tconstruct:material_fluid") and isinstance(v, str) \
                        and "#" in v and v not in infos and v.split("#", 1)[0] in infos:
                    infos[v] = infos[v.split("#", 1)[0]]
    members = _tag_members(tags)
    parts = 0
    layers = _Layers(jar, names)
    for name in sorted(names):
        m = re.match(rf"assets/{ID}/models/item/([a-z0-9_]+)\.json$", name)
        if not m:
            continue
        doc = _json(jar, name) or {}
        if doc.get("loader") != "tconstruct:material" or doc.get("material"):
            continue
        item = m.group(1)
        base = (doc.get("textures") or {}).get("texture")
        if not base or (item not in PART_STATS and item not in ("repair_kit", "fake_ingot")):
            continue
        cases = []
        for variant_id, info in sorted(infos.items()):
            material = variant_id.split("#", 1)[0]
            if material == f"{ID}:ui_render" or material not in definition or not _usable(item, material, stats, members):
                continue
            # A variant without its own file reads the base material's (MaterialRenderInfoLoader.getRenderInfo).
            cases.append({"when": {"Material": variant_id}, "model": layers.material(GENERATED, base, info)})
        node = {"type": "minecraft:select", "property": "minecraft:component", "component": "minecraft:custom_data",
                "cases": cases, "fallback": {"type": "minecraft:model", "model": f"{ID}:item/{item}"}}
        offset = doc.get("offset")
        if isinstance(offset, list) and len(offset) == 2 and offset != [0, 0]:
            # MaterialModel.bake: the quads translated (x/16, -y/16, 0).
            node["transformation"] = _transform((offset[0] / 16, -offset[1] / 16, 0.0))
        files[f"assets/{ID}/items/{item}.json"] = json.dumps({"model": node}, indent=1).encode()
        parts += 1
    tools = _tool_items(files, jar, names, infos, definition, stats, tool_definitions, layers)
    layers.write(files)
    glowing = sum(1 for d in layers.models.values() if "elements" in d)
    print(f"tools: {len(definition)} material files, {len(stats)} stats, {len(traits)} traits; {parts} part items and "
          f"{tools} tools drawn by material from {len(layers.models)} layer models ({glowing} emissive)")
