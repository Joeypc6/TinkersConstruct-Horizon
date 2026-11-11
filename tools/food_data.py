"""Tinkers' foods and drinks (TinkerFood, TinkerFluids, TinkerCommons) as 26.3 item components.

Java gives these items FoodProperties (nutrition, the saturation modifier, always-edible, fast, effects with a chance)
and a crafting remainder; the port had declared them as plain paper, so none could be eaten or drunk and a bottle used
in the crafting grid (the overslime recipe) gave no glass bottle back. Here each is a vanilla template of its kind
(honey bottle for the drinks: Mantle's ContainerFoodItem drinks, 32 ticks, the bottle given back; cooked porkchop,
mushroom stew, golden apple) with Java's numbers in `minecraft:food` / `minecraft:consumable`. 26.3's saturation is
nutrition x modifier x 2 (FoodProperties.Builder.saturationModifier in 1.20).

The two effects the earth and sky bottles give are declared too (TinkerEffects: experienced, ricochet); their
attribute modifiers (Tinkers' experience and knockback multipliers) are mod attributes Horizon can't add.
The magma bottle sets the drinker on fire for 15 s (MagmaBottleItem.finishUsingItem): no 26.3 consume effect does that,
so it carries a `tconstruct:set_fire` effect the native mod's `consume_effect` does.

Usage (from make_content.py): food_data.write(files)
"""

import json

from paused import PAUSED

ID = "tconstruct"
GLASS = "minecraft:glass_bottle"


def eff(effect, duration, amplifier=0):
    return {"id": effect, "duration": duration, "amplifier": amplifier}


# (item, template, stack, remainder, nutrition, saturation modifier, always edible, fast, [effects], drink)
FOODS = [
    ("bacon", "minecraft:cooked_porkchop", None, None, 4, 0.6, False, False, [], False),
    ("cheese_ingot", "minecraft:bread", None, None, 3, 0.4, False, False, [], False),
    ("jeweled_apple", "minecraft:golden_apple", None, None, 4, 1.2, True, False,
     [eff("minecraft:haste", 1200), eff("minecraft:resistance", 2400)], False),
    ("meat_soup", "minecraft:mushroom_stew", 1, "minecraft:bowl", 8, 0.6, False, False, [], True),
    ("earth_slime_bottle", "minecraft:honey_bottle", 16, GLASS, 0, 0.0, True, False,
     [eff(f"{ID}:experienced", 2400), eff("minecraft:slowness", 2400, 1)], True),
    ("sky_slime_bottle", "minecraft:honey_bottle", 16, GLASS, 0, 0.0, True, False,
     [eff(f"{ID}:ricochet", 2400), eff("minecraft:slowness", 2400, 1)], True),
    ("ichor_slime_bottle", "minecraft:honey_bottle", 16, GLASS, 0, 0.0, True, False,
     [eff("minecraft:levitation", 200), eff("minecraft:slowness", 200, 1)], True),
    ("ender_slime_bottle", "minecraft:honey_bottle", 16, GLASS, 0, 0.0, True, False,
     [eff(f"{ID}:enderference", 1200), eff("minecraft:slowness", 1200, 1)], True),
    ("venom_bottle", "minecraft:honey_bottle", 16, GLASS, 0, 0.0, True, False,
     [eff("minecraft:strength", 600), eff("minecraft:poison", 250)], True),
    ("magma_bottle", "minecraft:honey_bottle", 16, GLASS, 0, 0.0, True, False, [], True),  # fire: CONSUME_EXTRA
]

# Effects of Tinkers' own kinds, done by the native mod's `consume_effect` (MagmaBottleItem: setSecondsOnFire(15)).
CONSUME_EXTRA = {"magma_bottle": {"type": f"{ID}:set_fire", "seconds": 15},
                 # CheeseItem.removeRandomEffect: one of the eater's milk-curable effects, at random.
                 "cheese_ingot": {"type": f"{ID}:remove_random_effect"}}

# TinkerEffects: (category, colour).
EFFECTS = {"experienced": ("beneficial", 8570995), "ricochet": ("neutral", 117709)}


def write(files):
    for item, template, stack, remainder, nutrition, modifier, always, fast, effects, drink in FOODS:
        food = {"nutrition": nutrition, "saturation": round(nutrition * modifier * 2.0, 4)}
        if always:
            food["can_always_eat"] = True
        consumable = {
            "consume_seconds": 0.8 if fast else 1.6,
            "animation": "drink" if drink else "eat",
            "sound": "minecraft:entity.generic.drink" if drink else "minecraft:entity.generic.eat",
            "has_consume_particles": not drink,
        }
        if effects:
            consumable["on_consume_effects"] = [{"type": "minecraft:apply_effects", "effects": effects, "probability": 1.0}]
        if item in CONSUME_EXTRA:
            consumable.setdefault("on_consume_effects", []).append(CONSUME_EXTRA[item])
        components = {"minecraft:food": food, "minecraft:consumable": consumable}
        if remainder:
            components["minecraft:use_remainder"] = {"id": remainder}
        doc = {"template": template, "components": components}
        if stack:
            doc["max_stack_size"] = stack
        if remainder:
            doc["crafting_remainder"] = remainder
        files[f"data/{ID}/horizon/item/{item}.json"] = json.dumps(doc, indent=1).encode()
    # The cheese block (TinkerCommons.cheeseBlock: HalfTransparentBlock, strength 1.5 / 3, speed factor 0.4, jump factor
    # 0.5, slime sounds, no occlusion, MapColor.COLOR_YELLOW) and its item (CheeseBlockItem: CHEESE food, a random effect
    # removed, 3 cheese ingots back). The template is a plain full block with Block's defaults (packed mud: the default
    # instrument, no tool needed, no behaviour of its own), so the cheese is a redstone conductor, suffocates, blocks the
    # view and takes spawns as Java's; `occludes: false` gives noOcclusion's light (1 dampening, no sky light down).
    # The speed and jump factors are the native mod's (tc_cheese.rs): content properties have none.
    cheese = {"nutrition": 3, "saturation": round(3 * 0.4 * 2.0, 4)}
    files[f"data/{ID}/horizon/block/cheese_block.json"] = json.dumps({
        # The honey block's template while tc_cheese.rs (the 0.4 / 0.5 factors on a plain block) is paused in
        # make_bundle.py: honey has the same factors, but also its sliding and stickiness.
        "template": "minecraft:honey_block" if "effects" in PAUSED else "minecraft:packed_mud",
        "properties": {"hardness": 1.5, "explosion_resistance": 3.0, "sounds": "minecraft:slime_block", "occludes": False,
                       "map_color": 18},
        "components": {
            "minecraft:food": cheese,
            "minecraft:consumable": {"consume_seconds": 1.6, "animation": "eat", "sound": "minecraft:entity.generic.eat",
                                     "on_consume_effects": [{"type": f"{ID}:remove_random_effect"},
                                                            # Horizon's use remainder keeps one item: the 3 ingots are
                                                            # given by the native mod (none in creative, as Java).
                                                            {"type": f"{ID}:give_item", "item": f"{ID}:cheese_ingot", "count": 3}]},
        },
    }, indent=1).encode()
    for name, (category, colour) in EFFECTS.items():
        files[f"data/{ID}/horizon/mob_effect/{name}.json"] = json.dumps({"category": category, "color": colour}).encode()
