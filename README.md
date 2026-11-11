# Tinkers' Construct for Horizon

An unofficial port of [Tinkers' Construct](https://github.com/SlimeKnights/TinkersConstruct) 1.20.1-3.12.1.231 (by
SlimeKnights, MIT) to [Horizon](https://github.com/horizon-rust/horizon) and Minecraft 26.x, as one native mod. The
Java mod was rewritten in Rust for Horizon's hooks, so no original code runs. Textures, models, recipes, books and
language files are the original mod's.

- `mixins/tconstruct`: the mod, and `data/tconstruct-content.hmod` its 360 blocks, 679 items, fluids and recipes.
- `tools/`: make the content and the W guide from the original jar (`make_content.py`, `tconstruct_guide.py`), and
  write the bundle (`make_bundle.py`).

## What's there

- The smeltery and foundry as formed multiblocks (controller, drains, ducts, chutes, tanks, glass), the melter and
  heater, the alloyer, faucets, channels, casting tables and basins, casts and sand casts, with Java's screens.
- Tool building: part builder, tinker station, tinker's anvil and modifier worktable, every tool and part drawn by
  material, modifiers and traits, armour and ranged tools (longbow, crossbow, fishing rod, staffs).
- 72 fluids to the mB; the buckets and copper can draw their fluid; recipes in JEI draw fluids as textures.
- Slime islands and geodes, slime foliage tinted from Java's colour maps, mob heads, gadgets and foods.
- The W guide: the five books, translated, every item opening its page, 149 pages with 3D scenes you can turn.
- Jade, and server authority for every action.

## What differs from the Java mod

- The Experienced and Ricochet effects don't act yet, and the cheese block uses honey's behaviour; both are being
  written as engine mixins (`tools/paused.py`).
- The fancy item frames and armour stands aren't there yet (same reason).
- Built for Horizon fdc87ae (Nightly 2026-11-08); see `horizon-native.json`.

## Tested

In game on Horizon `fdc87ae` builds this week (the last, `native-fdc87ae-83d10460ef68`, with the nine other ports): the W guide's pages and 3D scenes
(smeltery, foundry, stations, islands, geodes), the fluid buckets and copper cans, JEI's casting and melting cards, slime foliage tinted
by position, the fishing rod catching fish, the longbow and ballista, foods and the cheese block, mob heads, and the geodes, cobalt
and trees in the world.
