"""Writes the Tinkers' Construct bundle's horizon-mixin.toml and its one-line hook helpers, and packs the content.

Usage: python make_bundle.py
"""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "mixins" / "tconstruct"
BUILD = ROOT.parent / "native-build" / "main" / "tconstruct"
JAR = ROOT.parent / "TConstruct-1.20.1-3.12.1.231.jar"
if not JAR.exists():
    JAR = ROOT.parent / "Ported" / JAR.name
HORIZON = "fdc87aecdbd116bf1e08adcd062fcbaea8c2e2ca"
MIXINS = "5a64af938ec86b00d53d16a408aabc0038fb3e57"
VERSION = "3.12.1"
M = "crate::game::tconstruct"

GAME_MUT = ("game", "&mut crate::game::Game<'_>", "&mut *self")
GAME = ("game", "&crate::game::Game<'_>", "&*self")
ENTITY_MUT = ("entity", "&mut horizon_client::containers::ModBlockEntity", "&mut *entity")
ENTITY = ("entity", "&horizon_client::containers::ModBlockEntity", "&*entity")
LEVEL = ("level", "&crate::game::GameLevel<'_>", "&*self")
STATE = ("state", "horizon_world::registry::BlockStateId", "state")

# (id, hook, bindings, body); a hook "target:<path>" names a function instead of a catalog hook. The melter, the
# heater and the tanks (tconstruct.rs, "The smeltery's first blocks").
HOOKS = [
    ("kit-frame", "frame", [GAME_MUT], "kit_frame(game)"),
    ("be", "block_entity", [("block", "&str", "block"), ("entity", "&mut Option<(String, horizon_world::nbt::Compound)>", "&mut *entity")], "block_entity(block, entity)"),
    ("be-ticks", "block_entity_ticks", [("block", "&str", "block"), ("ticks", "&mut bool", "&mut *ticks")], "block_entity_ticks(block, ticks)"),
    ("be-container", "block_entity_container", [("block", "&str", "block"), ("container", "&mut Option<horizon_client::containers::ModContainer>", "&mut *container")], "block_entity_container(block, container)"),
    ("be-fluids", "block_entity_fluids", [("block", "&str", "block"), ("fluids", "&mut Option<horizon_client::containers::ModFluidTanks>", "&mut *fluids")], "block_entity_fluids(block, fluids)"),
    ("be-tick", "block_entity_tick", [GAME_MUT, ("pos", "[i32; 3]", "pos"), ENTITY_MUT], "block_entity_tick(game, pos, entity)"),
    ("accepts", "target:horizon_client::game::native_hooks::Game<'_>::native_container_accepts", [GAME, ("pos", "[i32; 3]", "pos"), ENTITY, ("slot", "usize", "slot"), ("stack", "&horizon_client::items::ItemStack", "stack"), ("cancel", "&mut bool", "&mut *cancel")], "container_accepts(game, pos, entity, slot, stack, cancel)"),
    ("quick-move", "menu_quick_move", [GAME_MUT, ("pos", "[i32; 3]", "pos"), ENTITY_MUT, ("container_slots", "usize", "container_slots"), ("slot", "usize", "slot"), ("stack", "&mut horizon_client::items::ItemStack", "&mut *stack"), ("handled", "&mut bool", "&mut *handled")], "quick_move(game, pos, entity, container_slots, slot, stack, handled)"),
    ("opened", "player_container_open", [("player", "u128", "player"), ("dimension", "&str", "dimension"), ("pos", "Option<[i32; 3]>", "pos")], "container_opened(dimension, player, pos, true)"),
    ("closed", "player_container_close", [GAME_MUT, ("player", "u128", "player"), ("dimension", "&str", "dimension"), ("pos", "Option<[i32; 3]>", "pos")], "container_closed(game, dimension, player, pos)"),
    ("screen-pressed", "screen_mouse_button_pressed_pre", [GAME, ("screen", "&crate::game::native_hooks::NativeScreenView<'_>", "screen"), ("canceled", "&mut bool", "&mut *canceled")], "screen_pressed(game, screen, canceled)"),
    ("slot-rules", "menu_slot_rules", [("menu", "&str", "menu"), ("slot", "usize", "slot"), ("stack", "&ItemStack", "stack"), ("may_place", "&mut bool", "&mut *may_place"), ("max_stack", "&mut u32", "&mut *max_stack")], None),
    ("menu-button", "menu_button_v2", [GAME_MUT, ("pos", "[i32; 3]", "pos"), ENTITY_MUT, ("id", "i32", "id"), ("carried", "&mut Option<horizon_client::items::ItemStack>", "&mut *carried")], "menu_button(game, pos, entity, id, carried)"),
    ("viewers", "mod_container_viewers", [GAME_MUT, ("dimension", "&str", "dimension"), ("pos", "[i32; 3]", "pos"), ("viewers", "u32", "viewers")], "container_viewers(game, dimension, pos, viewers)"),
    ("right-click", "right_click_block", [GAME_MUT, ("pos", "[i32; 3]", "pos"), ("face", "[i32; 3]", "face"), ("canceled", "&mut bool", "&mut *canceled")], "right_click(game, pos, face, canceled)"),
    ("placed", "place_block", [GAME_MUT, ("stack", "&ItemStack", "stack"), ("pos", "[i32; 3]", "pos")], "placed(game, stack, pos)"),
    ("placement", "target:horizon_client::game::native_hooks::GameLevel<'_>::native_state_for_placement", [LEVEL, STATE, ("context", "&horizon_world::level::PlacementContext", "context"), ("answer", "&mut Option<Option<horizon_world::registry::BlockStateId>>", "&mut *answer")], "state_for_placement(level, state, context, answer)"),
    ("destroy", "destroy_block", [GAME_MUT, ("pos", "[i32; 3]", "pos")], "destroyed(game, pos)"),
    ("level-tick", "level_tick_post", [GAME_MUT, ("dimension", "&str", "dimension")], "level_tick(game, dimension)"),
    ("has-analog", "has_analog_output", [LEVEL, STATE, ("output", "&mut bool", "&mut *output")], "has_analog_output(level, state, output)"),
    ("analog", "analog_output", [LEVEL, ("pos", "horizon_core::position::BlockPos", "pos"), ("output", "&mut i32", "&mut *output")], "analog_output(level, [pos.x, pos.y, pos.z], output)"),
    ("screen", "screen", [("block", "&str", "block"), ("screen", "&mut Option<crate::game::native_hooks::NativeScreen>", "&mut *screen")], "screen(block, screen)"),
    ("screen-draw", "screen_draw", [GAME, ("block", "&str", "block"), ("data", "&[i32]", "data"), ("batch", "&mut horizon_client::hud::HudBatch", "&mut *batch"), ("origin", "[f32; 2]", "origin")], "screen_draw(game, block, data, batch, origin)"),
    ("screen-click", "screen_click", [GAME, ("block", "&str", "block"), ("data", "&[i32]", "data"), ("at", "[f32; 2]", "at"), ("right", "bool", "right"), ("button", "&mut Option<i32>", "&mut *button")], "screen_click(game, block, data, at, right, button)"),
    ("screen-tooltip", "screen_tooltip", [GAME, ("block", "&str", "block"), ("data", "&[i32]", "data"), ("at", "[f32; 2]", "at"), ("lines", "&mut Vec<String>", "&mut *lines")], "screen_tooltip(game, block, data, at, lines)"),
    ("submit", "block_entity_submit", [GAME, ("pos", "[i32; 3]", "pos"), ("block", "&str", "block"), STATE, ENTITY, ("draw", "&mut crate::game::native_block_entity_draw::BlockEntityDraw", "&mut *draw")], "submit(game, pos, block, state, entity, draw)"),
    ("update-tag", "block_entity_update_tag", [ENTITY, ("tag", "&mut Option<horizon_world::nbt::Compound>", "&mut *tag")], "update_tag(entity, tag)"),
    # The smeltery and the foundry (tconstruct.rs, "The smeltery and the foundry"): a part changed (notifyMasterOfChange),
    # the drains' and ducts' fluid capability (Horizon's custom fluid storage), the side inventory's layout and scroll,
    # and the controller drawing over its whole inside.
    ("block-changed", "block_changed", [LEVEL, ("dimension", "horizon_world::level::Dimension", "dimension"), ("pos", "horizon_core::position::BlockPos", "pos"), ("old", "horizon_world::registry::BlockStateId", "old"), ("new", "horizon_world::registry::BlockStateId", "new")], "block_changed(level, dimension, pos, old, new)"),
    ("custom-fluids", "target:horizon_client::game::native_hooks::Game<'_>::native_custom_block_fluids", [("block", "&str", "block"), ("custom", "&mut bool", "&mut *custom")], "custom_block_fluids(block, custom)"),
    ("custom-tanks", "target:horizon_client::game::native_hooks::Game<'_>::native_custom_fluid_tanks", [GAME, ("pos", "[i32; 3]", "pos"), ("side", "Option<horizon_core::geometry::Direction>", "side"), ("out", "&mut Option<Vec<horizon_client::mod_api::NativeFluidTankView>>", "&mut *out")], "custom_fluid_tanks(game, pos, side, out)"),
    ("custom-fill", "target:horizon_client::game::native_hooks::Game<'_>::native_custom_fluid_fill", [GAME_MUT, ("pos", "[i32; 3]", "pos"), ("side", "Option<horizon_core::geometry::Direction>", "side"), ("resource", "&horizon_client::mod_api::NativeFluidStack", "resource"), ("action", "horizon_client::mod_api::NativeFluidAction", "action"), ("out", "&mut Option<i32>", "&mut *out")], "custom_fluid_fill(game, pos, side, resource, action, out)"),
    ("custom-drain", "target:horizon_client::game::native_hooks::Game<'_>::native_custom_fluid_drain", [GAME_MUT, ("pos", "[i32; 3]", "pos"), ("side", "Option<horizon_core::geometry::Direction>", "side"), ("request", "&horizon_client::mod_api::NativeFluidDrain", "request"), ("action", "horizon_client::mod_api::NativeFluidAction", "action"), ("out", "&mut Option<horizon_client::mod_api::NativeFluidStack>", "&mut *out")], "custom_fluid_drain(game, pos, side, request, action, out)"),
    ("screen-opening", "target:horizon_client::game::native_hooks::Game<'_>::open_native_screen", [GAME, ("target", "Option<(i32, i32, i32)>", "target")], "screen_opening(game, target)"),
    ("screen-scrolled", "screen_mouse_scrolled_pre", [GAME, ("screen", "&crate::game::native_hooks::NativeScreenView<'_>", "screen"), ("scroll", "[f64; 2]", "scroll"), ("modifiers", "u32", "modifiers"), ("canceled", "&mut bool", "&mut *canceled")], "screen_scrolled(game, screen, scroll, canceled)"),
    ("render-bounds", "block_entity_render_bounding_box", [GAME, ("pos", "[i32; 3]", "pos"), ("block", "&str", "block"), STATE, ENTITY, ("bounds", "&mut [f32; 6]", "&mut *bounds")], "render_bounds(pos, entity, bounds)"),
    # Materials and tool parts (tconstruct.rs, "Materials and tool parts"): the material folders read on each data
    # load of the server (MaterialManager and friends), and the parts' names and tooltips.
    ("reload-listeners", "add_server_reload_listeners", [("listeners", "&mut Vec<crate::game::native_reload_listeners::NativeReloadListener>", "&mut *listeners")], "reload_listeners(listeners)"),
    ("reload-apply", "server_reload_listener_apply", [("listener", "&crate::game::native_reload_listeners::NativeReloadListener", "listener"), ("files", "&[(String, serde_json::Value)]", "files")], "reload_apply(listener, files)"),
    ("tooltip", "tooltip", [GAME, ("stack", "&horizon_client::items::ItemStack", "stack"), ("lines", "&mut Vec<(horizon_client::text::Text, u32)>", "&mut *lines")], "tooltip(game, stack, lines)"),
    # The stations (tconstruct.rs, "The stations"): every click in a mod menu checks the clicked station first (the
    # head of the first click handler), a block entity's removal takes a station's result out before its items drop,
    # and the tinker station's text field and the sliders take keys, characters and drags.
    ("click-pre", "target:horizon_client::game::native_quick_move::Game<'_>::lan_mod_quick_move", [GAME_MUT, ("host", "&mut crate::game::lan::LanHost", "&mut *host"), ("conn", "u32", "conn"), ("p", "&horizon_protocol::packets::play::ContainerClick", "p")], "station_click(game, host, conn, p)"),
    ("be-removed", "target:horizon_client::game::<GameLevel<'_> as LevelAccess>::remove_block_entity", [("level", "&mut crate::game::GameLevel<'_>", "&mut *self"), ("pos", "horizon_core::position::BlockPos", "pos")], "block_entity_removed(level, [pos.x, pos.y, pos.z])"),
    ("screen-key", "screen_key_pressed_pre", [GAME, ("screen", "&crate::game::native_hooks::NativeScreenView<'_>", "screen"), ("key", "&str", "key"), ("canceled", "&mut bool", "&mut *canceled")], "screen_key(game, screen, key, canceled)"),
    ("screen-char", "screen_char_typed_pre", [GAME, ("screen", "&crate::game::native_hooks::NativeScreenView<'_>", "screen"), ("c", "char", "c"), ("canceled", "&mut bool", "&mut *canceled")], "screen_char(game, screen, c, canceled)"),
    ("screen-dragged", "screen_mouse_dragged_pre", [GAME, ("screen", "&crate::game::native_hooks::NativeScreenView<'_>", "screen"), ("canceled", "&mut bool", "&mut *canceled")], "screen_dragged(game, screen, canceled)"),
    ("screen-released", "screen_mouse_button_released_pre", [GAME, ("screen", "&crate::game::native_hooks::NativeScreenView<'_>", "screen"), ("canceled", "&mut bool", "&mut *canceled")], "screen_released(game, screen, canceled)"),
    # Tools (tconstruct.rs, "Tools"): Horizon reads a tool's speeds, durability and attributes from the item, not the
    # stack, so the stack's own stats act here: the dig speed (both sides), the wear and the AOE of a break, the drops
    # below the tier, the wear of a hit, the first build of a carried tool, the durability bar. The weapon's attack
    # damage and speed are the cancellable heads below (WEAPON_HOOKS).
    ("break-speed", "target:horizon_client::game::native_hooks::Game<'_>::native_break_speed", [GAME, ("pos", "[i32; 3]", "pos"), STATE, ("speed", "&mut f32", "&mut *speed")], "break_speed(game, pos, state, speed)"),
    ("tool-destroy", "destroy_block", [GAME_MUT, ("pos", "[i32; 3]", "pos"), STATE], "tool_destroy(game, pos, state)"),
    ("tool-drops", "target:horizon_client::game::native_hooks::Game<'_>::native_block_drops", [GAME_MUT, ("pos", "[i32; 3]", "pos"), STATE, ("player", "Option<u128>", "player"), ("tool", "Option<&horizon_client::items::ItemStack>", "tool"), ("drops", "&mut Vec<horizon_client::items::ItemStack>", "&mut *drops")], "tool_drops(game, pos, state, player, tool, drops)"),
    ("hurt-enemy", "hurt_enemy", [GAME_MUT, ("stack", "&horizon_client::items::ItemStack", "stack"), ("entity", "u32", "entity")], "hurt_enemy(game, stack, entity)"),
    ("inventory-tick", "inventory_tick", [GAME_MUT, ("slot", "i32", "slot")], "inventory_tick(game, slot)"),
    ("item-bar", "item_bar", [GAME, ("stack", "&horizon_client::items::ItemStack", "stack"), ("bar", "&mut Option<(i32, u32)>", "&mut *bar")], "item_bar(game, stack, bar)"),
    # Modifiers (tconstruct.rs, "Modifiers"): the target and strength of a melee hit (Player.attack's damage), the
    # server's tick (the mob effects queued as commands, the 20-tick rhythm) and each player's tick (the magnet).
    ("melee-target", "target:horizon_client::game::Game<'_>::melee_damage", [GAME_MUT, ("target_kind", "&str", "target_kind"), ("living", "bool", "living")], "melee_target(game, target_kind, living)"),
    ("modifier-tick", "tick", [GAME_MUT], "modifier_tick(game)"),
    ("magnet", "player_tick", [GAME_MUT], "magnet_tick(game)"),
    # Modifiers (6c-6d) (tconstruct.rs, "Modifier recipes and the Modifier Worktable"): a Tinkers' tool's knockback
    # modifiers on its hit's push, and soulbound tools kept through a death (a dying player's drops) to the respawn.
    ("knockback", "living_knockback_v2", [("attacker_main", "Option<&horizon_client::items::ItemStack>", "attacker_main"), ("strength", "&mut f64", "&mut *strength")], "living_knockback(attacker_main, strength)"),
    ("soulbound-drops", "loot_drops", [GAME, ("context", "&horizon_client::mod_api::NativeLootDrops<'_>", "context"), ("drops", "&mut Vec<horizon_client::items::ItemStack>", "&mut *drops")], "soulbound_drops(game, context, drops)"),
    ("soulbound-respawn", "player_respawned", [GAME_MUT, ("player", "u128", "player")], "soulbound_respawn(game, player)"),
    # Modifiers (6e-6f) (tconstruct.rs, "Tool actions and area attacks"): the right-click transforms (after the block's
    # own use) and the shears on mobs.
    ("use-item-on", "use_item_on", [GAME_MUT, ("stack", "&horizon_client::items::ItemStack", "stack"), ("pos", "[i32; 3]", "pos"), ("face", "[i32; 3]", "face"), ("claimed", "&mut bool", "&mut *claimed")], "use_item_on(game, stack, pos, face, claimed)"),
    # Phase 7d (tconstruct.rs, "Left-click interactions"): the modifiers toggled to the left click act on a dig's start.
    ("left-click", "left_click_block", [GAME_MUT, ("pos", "[i32; 3]", "pos"), ("face", "[i32; 3]", "face"), STATE, ("canceled", "&mut bool", "&mut *canceled")], "left_click(game, pos, face, canceled)"),
    ("consume-effect", "consume_effect", [GAME_MUT, ("kind", "&str", "kind"), ("data", "&serde_json::Value", "data")], "consume_effect(game, kind, data)"),
    ("interact-entity", "interact_entity", [GAME_MUT, ("entity", "i32", "entity"), ("kind", "&str", "kind"), ("stack", "Option<&horizon_client::items::ItemStack>", "stack"), ("claimed", "&mut bool", "&mut *claimed")], "interact_entity(game, entity, stack, claimed)"),
    # Ranged and use states (7a) (tconstruct.rs, "Ranged tools and use states"): a launcher used over time (its use
    # duration and pose, the start with its ammo check and drawing, the full-draw click, the release that shoots or
    # loads), the thrown ammo's throw, and its hits.
    ("use-duration", "use_duration", [("stack", "&horizon_client::items::ItemStack", "stack"), ("duration", "&mut i32", "&mut *duration")], "ranged_use_duration(stack, duration)"),
    ("use-animation", "use_animation", [("stack", "&horizon_client::items::ItemStack", "stack"), ("animation", "&mut horizon_world::consumable::UseAnimation", "&mut *animation")], "ranged_use_animation(stack, animation)"),
    ("use-start", "living_entity_use_item_start", [GAME_MUT, ("stack", "&horizon_client::items::ItemStack", "stack"), ("entity", "Option<i32>", "entity"), ("canceled", "&mut bool", "&mut *canceled")], "ranged_use_start(game, stack, entity, canceled)"),
    ("use-tick", "on_use_tick", [GAME_MUT, ("stack", "&horizon_client::items::ItemStack", "stack"), ("entity", "Option<i32>", "entity"), ("remaining", "i32", "remaining")], "ranged_use_tick(game, stack, entity, remaining)"),
    ("release", "release_using", [GAME_MUT, ("stack", "&horizon_client::items::ItemStack", "stack"), ("entity", "Option<i32>", "entity"), ("time_left", "i32", "time_left")], "ranged_release(game, stack, entity, time_left)"),
    ("use-item", "use_item", [GAME_MUT, ("stack", "&horizon_client::items::ItemStack", "stack"), ("claimed", "&mut bool", "&mut *claimed")], "ranged_use_item(game, stack, claimed)"),
    ("hears-impacts", "hears_projectile_impacts", [("hears", "&mut bool", "&mut *hears")], "ranged_hears_impacts(hears)"),
    ("impact", "projectile_impact", [GAME_MUT, ("projectile", "u32", "projectile"), ("entity", "Option<u32>", "entity"), ("canceled", "&mut bool", "&mut *canceled")], "ranged_impact(game, projectile, entity, canceled)"),
    # Armor, shields and staffs (7b-7c) (tconstruct.rs, "Armor, shields and staffs"): Java's protection on a player's
    # hit, the worn Tinkers' armor's wear (Player.hurtArmor), a Tinkers' shield's wear after a block, and the worn
    # piece whose layers are drawn next.
    ("armor-incoming", "living_incoming_damage", [("entity", "i32", "entity"), ("kind", "&str", "kind"), ("damage_type", "&str", "damage_type"), ("causing", "i32", "causing"), ("direct", "i32", "direct"), ("amount", "&mut f32", "&mut *amount"), ("canceled", "&mut bool", "&mut *canceled")], "armor_incoming_damage(entity, kind, damage_type, causing, direct, amount, canceled)"),
    ("armor-hurt", "target:horizon_client::game::Game<'_>::hurt_armor", [GAME_MUT, ("source", "horizon_world::damage_source::DamageTypeId", "source"), ("damage", "f32", "damage")], "armor_hurt(game, source, damage)"),
    ("worn-drawn", "target:horizon_client::game::armor_stands::Game<'_>::cit_worn_rule", [("stack", "&horizon_client::items::ItemStack", "stack")], "worn_drawn(stack)"),
    # Phase 7d, part 2 (tconstruct.rs, "Phase 7d, part 2"): the helmet and leggings keys and their packet to the server,
    # the zoom and the worn FOV factors, the counters (a living attacker's hit on the player landed: the damage type
    # first, then the head of Horizon's own thorns), and the health a melee hit's mob had before it (damage dealt).
    ("armor-key", "key", [GAME_MUT, ("key", "&str", "key"), ("pressed", "bool", "pressed")], "armor_key(game, key, pressed)"),
    ("armor-net", "net_from_client", [GAME_MUT, ("player", "u128", "player"), ("channel", "&str", "channel"), ("data", "&[u8]", "data")], "armor_net(game, player, channel, data)"),
    ("fov", "compute_fov_modifier", [GAME, ("modifier", "&mut f32", "&mut *modifier")], "fov_modifier(game, modifier)"),
    ("hurt-from", "target:horizon_client::game::creatures::Game<'_>::hurt_player_from", [("damage_type", "&str", "damage_type")], "player_hurt_from(damage_type)"),
    ("counters", "target:horizon_client::game::enchant_effects::Game<'_>::thorns", [GAME_MUT, ("attacker", "u32", "attacker")], "counters(game, attacker)"),
    ("pre-hurt", "target:horizon_client::game::mace::Game<'_>::hurt_by_player", [GAME, ("index", "usize", "index")], "pre_hurt(game, index)"),
    # Gadgets (tconstruct.rs, "Gadgets"): punji sticks', platforms', glow's and the ichor cake's shape updates and
    # survival, the copper platforms' weathering, punji damage, the throwables' dispensing and impacts.
    ("gadget-shape", "update_shape", [LEVEL, ("ticks", "&mut horizon_world::level::Ticks", "&mut *ticks"), ("pos", "horizon_core::position::BlockPos", "pos"), STATE, ("direction", "horizon_core::geometry::Direction", "direction"), ("neighbour_pos", "horizon_core::position::BlockPos", "neighbour_pos"), ("neighbour", "horizon_world::registry::BlockStateId", "neighbour"), ("new", "&mut Option<horizon_world::registry::BlockStateId>", "&mut *new")], "gadget_update_shape(level, ticks, pos, state, direction, neighbour_pos, neighbour, new)"),
    ("gadget-survive", "can_survive", [LEVEL, ("pos", "horizon_core::position::BlockPos", "pos"), STATE, ("survives", "&mut Option<bool>", "&mut *survives")], "gadget_can_survive(level, pos, state, survives)"),
    ("gadget-random-tick", "random_tick", [("level", "&mut crate::game::GameLevel<'_>", "&mut *self"), ("ticks", "&mut horizon_world::level::Ticks", "&mut *ticks"), ("pos", "horizon_core::position::BlockPos", "pos"), STATE, ("handled", "&mut bool", "&mut *handled")], "gadget_random_tick(level, ticks, pos, state, handled)"),
    ("gadget-inside", "block_entity_inside", [("dimension", "&str", "dimension"), ("entity", "i32", "entity"), ("kind", "&str", "kind"), ("position", "[i32; 3]", "position")], "gadget_entity_inside(dimension, entity, kind, position)"),
    ("gadget-dispense", "dispense_item", [GAME_MUT, ("pos", "[i32; 3]", "pos"), ("facing", "horizon_core::geometry::Direction", "facing"), ("stack", "&horizon_client::items::ItemStack", "stack"), ("answer", "&mut Option<horizon_client::mod_api::NativeDispensed>", "&mut *answer")], "gadget_dispense(game, pos, facing, stack, answer)"),
    ("gadget-hears", "hears_projectile_impacts", [("hears", "&mut bool", "&mut *hears")], "gadget_hears_impacts(hears)"),
    ("gadget-impact", "projectile_impact", [GAME_MUT, ("dimension", "&str", "dimension"), ("projectile", "u32", "projectile"), ("kind", "&str", "kind"), ("entity", "Option<u32>", "entity"), ("block", "[i32; 3]", "block"), ("face", "[i32; 3]", "face"), ("at", "[f64; 3]", "at"), ("canceled", "&mut bool", "&mut *canceled")], "gadget_impact(game, dimension, projectile, kind, entity, block, face, at, canceled)"),
    # The slime world (tconstruct.rs, "The slime world"): bone meal on slime grass, nylium and the slime saplings (their
    # random ticks go through gadget-random-tick).
    ("world-bonemeal-valid", "is_valid_bonemeal_target", [LEVEL, ("pos", "horizon_core::position::BlockPos", "pos"), STATE, ("valid", "&mut Option<bool>", "&mut *valid")], "world_bonemeal_valid(level, pos, state, valid)"),
    ("world-bonemeal-success", "is_bonemeal_success", [("level", "&mut crate::game::GameLevel<'_>", "&mut *self"), STATE, ("success", "&mut bool", "&mut *success")], "world_bonemeal_success(level, state, success)"),
    ("world-bonemeal", "perform_bonemeal", [("level", "&mut crate::game::GameLevel<'_>", "&mut *self"), ("ticks", "&mut horizon_world::level::Ticks", "&mut *ticks"), ("pos", "horizon_core::position::BlockPos", "pos"), STATE], "world_bonemeal(level, ticks, pos, state)"),
]

# Cancellable heads (id, target, bindings, return type, body): a tool in the main hand answers with its own attack
# damage and speed (AttributesModifierHook), anything else lets the game's code run.
WEAPON_HOOKS = [
    ("attack-damage", "horizon_client::game::hand::Game<'_>::attack_damage", [GAME_MUT], "f32", "attack_damage(game)"),
    ("attack-speed", "horizon_client::game::hand::Game<'_>::main_hand_attack_speed", [GAME], "f64", "attack_speed(game)"),
    # The sweep of a Tinkers' tool (SweepWeaponAttack): whether it sweeps, then its victims (tconstruct.rs, "Tool actions
    # and area attacks").
    ("sweep-position", "horizon_client::game::Game<'_>::sweep_attack_position", [GAME_MUT, ("scale", "f32", "scale"), ("crit", "bool", "crit")], "Option<[f64; 3]>", "sweep_position(game, scale, crit)"),
    # The hotbar's selected-item name of a Tinkers' tool or part (tconstruct.rs, "Item display names").
    ("held-name", "horizon_client::game::titles::Game<'_>::held_name", [GAME], "Option<HeldName>", "held_name(game)"),
    ("sweep-damage", "horizon_client::game::mace::Game<'_>::sweep_damage", [GAME_MUT, ("target", "horizon_core::geometry::Aabb", "target"), ("spared", "&crate::game::mace::Spared", "&spared"), ("scale", "f32", "scale")], "()", "sweep_damage(game, target, spared)"),
    # The charge time `minecraft:crossbow/pull` divides by (CrossbowItem.getChargeDuration): a Tinkers' tool's drawtime
    # (tconstruct.rs, "Ranged tools and use states").
    ("charge-ticks", "horizon_client::game::crossbow::Game<'_>::charge_ticks", [("stack", "&horizon_client::items::ItemStack", "stack")], "u32", "charge_ticks(stack)"),
    # The worn Tinkers' armor's own attributes (LivingEntity.collectEquipmentChanges), and its layers' sprites by the
    # piece's materials (tconstruct.rs, "Armor, shields and staffs").
    # A Tinkers' shield's wear after a block (BlocksAttacks.hurtBlockingItem -> ItemStack.hurtAndBreak): its own.
    ("shield-wear", "horizon_client::game::enchant_effects::Game<'_>::wear", [GAME_MUT, ("stack", "&horizon_client::items::ItemStack", "stack"), ("amount", "u32", "amount")], "u32", "shield_wear(game, stack, amount)"),
    ("apply-equipment", "horizon_client::game::Game<'_>::apply_equipment", [GAME_MUT], "()", "apply_equipment(game)"),
    ("armor-layer-rect", "horizon_client::game::armor_stands::Game<'_>::armor_layer_rect", [GAME, ("asset", "&str", "asset"), ("kind", "&str", "kind"), ("texture", "&str", "texture")], "Option<[f32; 4]>", "armor_layer_rect(game, asset, kind, texture)"),
    # Phase 7d, part 2: the fishing rod through Horizon's bobber (a Tinkers' rod holds and casts it).
    ("rod-held", "horizon_client::game::fishing::Game<'_>::holds_rod", [GAME], "bool", "rod_held(game)"),
    ("rod-main", "horizon_client::game::fishing::Game<'_>::main_hand_rod", [GAME], "bool", "rod_main_hand(game)"),
    ("rod-use", "horizon_client::game::fishing::Game<'_>::use_fishing_rod", [GAME_MUT, ("stack", "&horizon_client::items::ItemStack", "stack")], "bool", "rod_use(game, stack)"),
    # Gadgets: an EFLN blast breaks EFLNExplosion's sphere of blocks, not vanilla's rays.
    ("efln-positions", "horizon_client::game::explosion::Game<'_>::exploded_positions", [GAME_MUT, ("center", "[f64; 3]", "center"), ("radius", "f32", "radius")], "Vec<[i32; 3]>", "efln_positions(game, center, radius)"),
]

# Cancellable heads whose helper body is written out (id, target, bindings, return type, body with {M}): reflecting
# (ModifierEvents.projectileImpact) skips a projectile's hit on this game's player and sends it back.
RAW_HOOKS = [
    ("reflect", "horizon_client::game::creatures::Game<'_>::projectile_hit", [GAME_MUT, ("p", "&horizon_client::projectiles::Projectile", "p"), ("hit", "&horizon_client::projectiles::Hit", "&hit")], "Result<()>",
     "if {M}::reflect_hit(game, p, hit) {{ core::ops::ControlFlow::Break(Ok(())) }} else {{ core::ops::ControlFlow::Continue(()) }}"),
]

# Heads in the client library's menu engine (menu.rs; its child module `tconstruct_fuel` answers): the crafting grid's
# Tinkers' recipes (tconstruct.rs, "Phase 7d": OverslimeCraftingTableRecipe, ModifierRepairCraftingRecipe). (id, target,
# bindings, return type or None for a plain head, helper call.)
LIB_HOOKS = [
    ("craft-recompute", "horizon_client_lib::menu::Menu::recompute", [("menu", "&mut Menu", "&mut *self"), ("env", "&Env<'_>", "env")], "()", "tconstruct_fuel::craft_recompute(menu, env)"),
    ("craft-taken", "horizon_client_lib::menu::Menu::map_crafted", [("stack", "&ItemStack", "&*stack")], None, "tconstruct_fuel::craft_taken(stack)"),
    # The smeltery's animateTick particles (spec-smeltery.md 12.2), in the client library's ClientLevel.animateTick
    # (animate_tick.rs; its child module `tconstruct_particles` answers).
    ("animate", "horizon_client_lib::animate_tick::animate_tick", [("engine", "&mut ParticleEngine", "&mut *engine"), ("ctx", "&AnimateContext<'_>", "ctx"), ("player", "[i32; 3]", "player")], None, "tconstruct_particles::animate(engine, ctx, player)"),
    # The slime foliage's colours (WorldClientEvents' block colour handlers, SlimeColorizer), in the section mesher (its
    # child module `hz_tconstruct_tint`, tinting.rs): each resource load names the states and reads the colormaps, the
    # mesher's tint source answers with the colormap at the block, and the positionless ones with FoliageType's colour.
    ("tint-bind", "horizon_client::game::PackResources::assemble", [("root", "&std::path::Path", "root"), ("assets", "&Arc<Assets>", "&assets"), ("tables", "&Arc<MeshTables>", "&tables")], None, "tables.hz_tconstruct_foliage(root, assets.registry)"),
    # The tables' tint sources are fixed when built (and `Mesher::tint` takes a destructured position no binding
    # reaches): the section mesher meshes with tinting.rs's copy of the tables, whose slime foliage states read the
    # dry foliage blend at their block; that blend answers with the colormap for the block `offset` placed last.
    ("tint-mesh", "horizon_client_render::mesher::Mesher<'_>::mesh_reusing", [("me", "&mut Mesher<'_>", "&mut *self")], None, "hz_tconstruct_tint::mesh_with_copy(me)"),
    ("tint-place", "horizon_client_render::mesher::offset", [("info", "&Info", "info"), ("x", "i32", "x"), ("z", "i32", "z")], None, "hz_tconstruct_tint::place(info, x, z)"),
    ("tint-blend", "horizon_client_render::mesher::Tints<'_>::get", [("tints", "&Tints<'_>", "&*self"), ("resolver", "Resolver", "resolver"), ("x", "i32", "x"), ("z", "i32", "z")], "u32", "hz_tconstruct_tint::blend(tints, resolver, x, z)"),
    ("tint-particle", "horizon_client_render::mesher::MeshTables::terrain_particle_tint", [("state", "BlockStateId", "state"), ("pos", "[i32; 3]", "pos")], "Option<u32>", "hz_tconstruct_tint::particle(state, pos)"),
    ("tint-default", "horizon_client_render::mesher::MeshTables::default_tint", [("state", "BlockStateId", "state"), ("index", "i32", "index")], "Option<u32>", "hz_tconstruct_tint::default(state, index)"),
    ("tint-source", "horizon_client_render::mesher::MeshTables::tint_source", [("state", "BlockStateId", "state"), ("index", "i32", "index")], "Option<TintSource>", "hz_tconstruct_tint::source(state, index)"),
]

# The Experienced and Ricochet effects (tc_effects.rs, tc_effects_orbs.rs: TinkerEffects' attribute modifiers as
# ModifierEvents reads them) and the cheese block's speed and jump factors (tc_cheese.rs). Modules: (id, file, name,
# source, visibility). Injections: (id, kind HEAD / HEAD-cancel / RETURN, target, bindings, return type, helper body).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from paused import PAUSED  # noqa: E402  features left out until their mixins are finished

EFFECT_MODULES = [
    ("tconstruct-effects", "crates/horizon-client/src/game.rs", "tc_effects", "tc_effects.rs", None),
    ("tconstruct-effects-orbs", "crates/horizon-client/src/mobs/drops.rs", "tc_effects_orbs", "tc_effects_orbs.rs", "pub"),
    ("tconstruct-cheese", "crates/horizon-world/src/movement_properties.rs", "tc_cheese", "tc_cheese.rs", None),
]
EFFECT_HOOKS = [
    # Ricochet (ModifierEvents.onKnockback): the pushed entity's multiplier at LivingEntity.knockback's start, applied
    # at its end, after a Tinkers' tool's knockback (living_knockback_v2). A pushed player is named at
    # knock_back_player, where the game holds them.
    ("ricochet-player", "HEAD", "horizon_client::game::creatures::Game<'_>::knock_back_player", [GAME], None,
     "crate::game::tc_effects::knocked_player(game);"),
    ("ricochet-start", "HEAD", "horizon_client::game::native_hooks::knockback", [("pushed", "&horizon_client::health::Hurting<'_>", "&pushed")], None,
     "crate::game::tc_effects::knockback_start(pushed);"),
    ("ricochet-end", "RETURN", "horizon_client::game::native_hooks::knockback", [("canceled", "bool", "$value"), ("knock", "&mut horizon_client::health::Knock", "&mut *knock")], "bool",
     "crate::game::tc_effects::knockback_end(canceled, knock)"),
    # Experienced: a mob's experience (onExperienceDrop: the multiplier before `die`, its orbs after) and a broken
    # block's (beforeBlockBreak).
    ("experienced-death", "HEAD", "horizon_client::game::creatures::Game<'_>::drop_death_loot", [GAME, ("m", "&horizon_client::mobs::Mob", "&*m"), ("player_uuid", "Option<u128>", "player_uuid")], None,
     "crate::game::tc_effects::death_experience(game, m, player_uuid);"),
    ("experienced-orbs", "RETURN", "horizon_client_lib::mobs::drops::die", [("value", "(Vec<Drop>, bool)", "$value")], "(Vec<Drop>, bool)",
     "crate::mobs::drops::tc_effects_orbs::apply(value)"),
    ("experienced-block", "RETURN", "horizon_client::game::Game<'_>::block_experience", [("value", "u32", "$value"), GAME], "u32",
     "crate::game::tc_effects::block_experience(value, game)"),
    # The cheese block: where the cheese's states are, at each binding of the movement table, and its row's factors.
    ("cheese-bind", "HEAD", "horizon_world::movement_properties::MovementProperties<'_>::bind", [("properties", "&crate::movement_properties::MovementProperties<'_>", "&*self")], None,
     "crate::movement_properties::tc_cheese::bind(properties.registry);"),
    ("cheese-get", "HEAD-cancel", "horizon_world::movement_properties::BoundMovementProperties::get", [("properties", "&crate::movement_properties::BoundMovementProperties", "&*self"), ("state", "crate::registry::BlockStateId", "state")], "io::Result<MovementBlock>",
     "crate::movement_properties::tc_cheese::get(properties, state)"),
]

# ClientLevel.animateTick for the smeltery's blocks (spec-smeltery.md 12.2): vanilla samples 667 x (a block within 16,
# one within 32) a tick and runs the sampled block's animateTick; Horizon's sampling knows only vanilla's blocks, so
# Tinkers' are sampled here the same way, with the same random, and run as MelterBlock, HeaterBlock,
# SmelteryControllerBlock, FoundryControllerBlock, AlloyerBlock (ControllerBlock.spawnFireParticles) and FaucetBlock do.
PARTICLES_MODULE = """use super::{AnimateContext, ParticleEngine, ParticleOptions, T};
use horizon_core::random::RandomSource;
use horizon_world::nbt::{JavaString, Tag};
use horizon_world::registry::BlockStateId;

pub(super) fn animate(engine: &mut ParticleEngine, ctx: &AnimateContext<'_>, center: [i32; 3]) {
    for _ in 0..667 {
        sample(engine, ctx, center, 16);
        sample(engine, ctx, center, 32);
    }
}

// ClientLevel.doAnimateTick's choice of block.
fn sample(engine: &mut ParticleEngine, ctx: &AnimateContext<'_>, center: [i32; 3], r: i32) {
    let random = engine.random();
    let x = center[0] + super::next_int(random, r) - super::next_int(random, r);
    let y = center[1] + super::next_int(random, r) - super::next_int(random, r);
    let z = center[2] + super::next_int(random, r) - super::next_int(random, r);
    if !ctx.world.loaded(x, z) {
        return;
    }
    let state = ctx.state([x, y, z]);
    let name = ctx.facts.get(state).name.clone();
    if let Some(path) = name.strip_prefix("tconstruct:") {
        block(engine, ctx, state, path, [x, y, z]);
    }
}

fn property(ctx: &AnimateContext<'_>, state: BlockStateId, key: &str) -> Option<String> {
    ctx.registry.state(state).and_then(|s| s.properties.get(key).cloned())
}

// Direction.getStepX / Y / Z of a facing.
fn step(facing: &str) -> [f64; 3] {
    match facing {
        "down" => [0.0, -1.0, 0.0],
        "up" => [0.0, 1.0, 0.0],
        "north" => [0.0, 0.0, -1.0],
        "south" => [0.0, 0.0, 1.0],
        "west" => [-1.0, 0.0, 0.0],
        _ => [1.0, 0.0, 0.0],
    }
}

fn block(engine: &mut ParticleEngine, ctx: &AnimateContext<'_>, state: BlockStateId, path: &str, pos: [i32; 3]) {
    let [fx, fy, fz] = pos.map(f64::from);
    if path.ends_with("_faucet") {
        // FaucetBlock.animateTick: a quarter of the time, a pouring faucet with nothing in its stream shows red dust.
        if engine.random().next_float() >= 0.25 {
            return;
        }
        let Some(crate::containers::BlockEntity::Mod(e)) = ctx.world.block_entities.get(&(pos[0], pos[1], pos[2])) else { return };
        let pouring = matches!(e.nbt.get(&JavaString::from("state")), Some(Tag::Int(s)) if *s != 0);
        let render = match e.nbt.get(&JavaString::from("render_fluid")) {
            Some(Tag::String(s)) => !s.to_string_lossy().is_empty(),
            _ => false,
        };
        if !pouring || render {
            return;
        }
        let d = step(&property(ctx, state, "facing").unwrap_or_default());
        let p = [fx + 0.5 - 0.3 * d[0], fy + 0.5 - 0.3 * d[1], fz + 0.5 - 0.3 * d[2]];
        engine.add(&ParticleOptions::dust([1.0, 0.0, 0.0], 0.5), p, [0.0; 3]);
        return;
    }
    let (height, flame): (fn(f32) -> f32, T) = match path {
        "seared_melter" => (|f| f * 6.0 / 16.0, T::Flame),
        "seared_heater" => (|f| f * 14.0 / 16.0, T::Flame),
        "smeltery_controller" => (|f| (f * 6.0 + 2.0) / 16.0, T::Flame),
        "foundry_controller" => (|f| (f * 6.0 + 2.0) / 16.0, T::SoulFireFlame),
        "scorched_alloyer" => (|f| f * 4.0 / 16.0, T::SoulFireFlame),
        _ => return,
    };
    if property(ctx, state, "active").as_deref() != Some("true") {
        return;
    }
    let random = engine.random();
    let (x, y, z) = (fx + 0.5, fy + f64::from(height(random.next_float())), fz + 0.5);
    let front = 0.52;
    let side = random.next_double() * 0.6 - 0.3;
    // ControllerBlock.spawnFireParticles: smoke, then the flame, at the front.
    let p = match property(ctx, state, "facing").as_deref() {
        Some("west") => [x - front, y, z + side],
        Some("east") => [x + front, y, z + side],
        Some("north") => [x + side, y, z - front],
        Some("south") => [x + side, y, z + front],
        _ => return,
    };
    super::add(engine, T::Smoke, p, [0.0; 3]);
    super::add(engine, flame, p, [0.0; 3]);
}
"""

# The melter's and the heater's slot rules (Slot.mayPlace, getSlotLimit), in the client library: no `crate::game`
# there, so the heater's fuel test reads the burnable items the server put in `tconstruct_fuel` (menu.rs).
SLOT_RULES = """fn tconstruct_slot_rules(menu: &str, slot: usize, stack: &ItemStack, may_place: &mut bool, max_stack: &mut u32) {
    // MeltingModuleInventory: any item, one a slot. HeaterItemHandler (SingleItemHandler(64)): what burns, 64.
    match menu {
        "tconstruct:melter" if slot < 3 => *max_stack = 1,
        // HeatingStructureContainerMenu: the bucket input takes fluid containers, the result nothing, each melting
        // slot one item (the server checks again). DuctItemHandler: one filled container.
        "tconstruct:smeltery" if slot == 0 => *may_place = tconstruct_fuel::is_container(&stack.item),
        "tconstruct:smeltery" if slot == 1 || slot >= 42 => *may_place = false,
        "tconstruct:smeltery" => *max_stack = 1,
        "tconstruct:duct" => {
            *may_place = stack.item.ends_with("_bucket") && !matches!(&*stack.item, "minecraft:milk_bucket" | "minecraft:powder_snow_bucket");
            *max_stack = 1;
        }
        "tconstruct:melter" | "tconstruct:heater" => {
            *may_place = tconstruct_fuel::is_fuel(&stack.item);
            *max_stack = 64;
        }
        // The stations: the part builder's pattern slot takes `#tconstruct:patterns`; the tinker station's slots their
        // layout's filters (TinkerStationSlot.mayPlace, set by the server for each click), its tool slot a modifiable.
        "tconstruct:part_builder" if slot == 1 => *may_place = tconstruct_fuel::is_pattern(&stack.item),
        "tconstruct:tinker_station" | "tconstruct:tinkers_anvil" => {
            if let Some(ok) = tconstruct_fuel::station_rule(menu, slot, &stack.item) {
                *may_place = *may_place && ok;
            }
        }
        _ => {}
    }
}
"""

FUEL_MODULE = """use super::ItemStack;
use std::collections::HashSet;
use std::sync::RwLock;

// The items that burn (a burn time over 3, HeaterItemHandler.isItemValid), from the server's data: None until the
// first world loads, when every item may go in and the server's checks keep the rest out.
static FUELS: RwLock<Option<HashSet<String>>> = RwLock::new(None);

pub(super) fn is_fuel(item: &str) -> bool {
    FUELS.read().ok().and_then(|f| f.as_ref().map(|s| s.contains(item))).unwrap_or(true)
}

// The items that may hold fluid (TankItem.mayHaveFluid: buckets, the copper can, tank items, the data-driven
// transfers' items), from the server's data: None until the first world loads, when buckets go in.
static CONTAINERS: RwLock<Option<HashSet<String>>> = RwLock::new(None);

pub(super) fn is_container(item: &str) -> bool {
    CONTAINERS.read().ok().and_then(|f| f.as_ref().map(|s| s.contains(item))).unwrap_or_else(|| item.ends_with("bucket"))
}

// The stations' tags (`#tconstruct:patterns`, `#tconstruct:modifiable`), and the tinker station's slot rules for the
// click the server handles now (its menu type; per slot None any item, Some(None) none, Some(Some(items)) those).
static PATTERNS: RwLock<Option<HashSet<String>>> = RwLock::new(None);
static MODIFIABLE: RwLock<Option<HashSet<String>>> = RwLock::new(None);
type Rules = Vec<Option<Option<HashSet<String>>>>;
static CLICK_RULES: RwLock<Option<(String, Rules)>> = RwLock::new(None);

pub(super) fn is_pattern(item: &str) -> bool {
    PATTERNS.read().ok().and_then(|f| f.as_ref().map(|s| s.contains(item))).unwrap_or(true)
}

pub(super) fn station_rule(menu: &str, slot: usize, item: &str) -> Option<bool> {
    let rules = CLICK_RULES.read().ok()?;
    let (m, list) = rules.as_ref()?;
    if m != menu {
        return None;
    }
    let rule = list.get(slot)?;
    let modifiable = slot != 0 || MODIFIABLE.read().ok().and_then(|f| f.as_ref().map(|s| s.contains(item))).unwrap_or(true);
    Some(match rule {
        None => modifiable,
        Some(None) => false,
        Some(Some(items)) => modifiable && items.contains(item),
    })
}

impl super::Menu {
    /// Tinkers' Construct's heater: the items that burn, for its slot's rule (`tconstruct_slot_rules`).
    pub fn hz_tconstruct_set_fuels(fuels: HashSet<String>) {
        if let Ok(mut f) = FUELS.write() {
            *f = Some(fuels);
        }
    }

    /// Tinkers' Construct's smeltery: the items that may hold fluid, for its bucket slot's rule.
    pub fn hz_tconstruct_set_containers(items: HashSet<String>) {
        if let Ok(mut f) = CONTAINERS.write() {
            *f = Some(items);
        }
    }

    /// Tinkers' Construct's stations: the patterns and the modifiable items, for their slots' rules.
    pub fn hz_tconstruct_set_station_tags(patterns: HashSet<String>, modifiable: HashSet<String>) {
        if let Ok(mut f) = PATTERNS.write() {
            *f = Some(patterns);
        }
        if let Ok(mut f) = MODIFIABLE.write() {
            *f = Some(modifiable);
        }
    }

    /// Tinkers' Construct's tinker station: its slots' rules for the click about to be handled.
    pub fn hz_tconstruct_set_click_rules(menu: &str, rules: Vec<Option<Option<HashSet<String>>>>) {
        if let Ok(mut f) = CLICK_RULES.write() {
            *f = Some((menu.to_owned(), rules));
        }
    }

    /// Tinkers' Construct's crafting-grid recipes (`crafting_overslime_modifier`, `crafting_modifier_repair`): `craft`
    /// answers a grid no vanilla recipe takes with its result and, per cell, the item a take gives back.
    pub fn hz_tconstruct_set_craft(craft: Craft) {
        if let Ok(mut f) = CRAFT.write() {
            *f = Some(craft);
        }
    }
}

// The crafting grid's Tinkers' recipes (CustomRecipe: assemble, getRemainingItems). The result is set where vanilla's
// recompute finds none; a take (the result's `map_crafted`, then the grid's -1 per cell and the recompute) gives back
// the cells' remainders the recipe named, on the same menu whose grid is exactly the last answered one less 1 a cell.
pub type Craft = fn(&super::Env<'_>, &[Option<ItemStack>], usize) -> Option<(ItemStack, Vec<Option<ItemStack>>)>;

static CRAFT: RwLock<Option<Craft>> = RwLock::new(None);

struct Answered {
    menu: usize,
    grid: Vec<Option<ItemStack>>,
    result: ItemStack,
    back: Vec<Option<ItemStack>>,
}

thread_local! {
    static ANSWERED: std::cell::RefCell<Option<Answered>> = const { std::cell::RefCell::new(None) };
    static TAKEN: std::cell::Cell<bool> = const { std::cell::Cell::new(false) };
}

/// `map_crafted` (ResultSlot.onTake's onCraftedBy, a quick move's too): the Tinkers' result answered last is taken.
pub(super) fn craft_taken(stack: &ItemStack) {
    if ANSWERED.with_borrow(|a| a.as_ref().is_some_and(|a| a.result == *stack)) {
        TAKEN.set(true);
    }
}

/// The grid after vanilla's take: each cell one less than `before` (an emptied cell None), nothing else.
fn took_one(before: &[Option<ItemStack>], now: &[Option<ItemStack>]) -> bool {
    before.len() == now.len()
        && before.iter().zip(now).all(|(b, n)| match (b, n) {
            (None, None) => true,
            (Some(b), None) => b.count == 1,
            (Some(b), Some(n)) => b.count > 1 && n.count == b.count - 1 && n.same_item_same_components(b),
            (None, Some(_)) => false,
        })
}

/// The head of `Menu::recompute`: the take's remainders back, then a Tinkers' result where no vanilla recipe matches.
pub(super) fn craft_recompute(menu: &mut super::Menu, env: &super::Env<'_>) -> core::ops::ControlFlow<()> {
    if menu.grid_size == 0 {
        return core::ops::ControlFlow::Continue(());
    }
    let id = std::ptr::from_ref(menu) as usize;
    let taken = TAKEN.replace(false);
    if let Some(last) = ANSWERED.take().filter(|a| taken && a.menu == id) {
        if took_one(&last.grid, &menu.containers[super::GRID]) {
            for (cell, back) in last.back.into_iter().enumerate() {
                let Some(back) = back else { continue };
                match menu.containers[super::GRID][cell].as_mut() {
                    None => menu.containers[super::GRID][cell] = Some(back),
                    Some(have) => have.count += back.count,
                }
            }
        }
    }
    let Some(craft) = CRAFT.read().ok().and_then(|f| *f) else { return core::ops::ControlFlow::Continue(()) };
    let n = menu.grid_size;
    if env.recipes.find(&menu.containers[super::GRID], n).is_some() {
        return core::ops::ControlFlow::Continue(());
    }
    let grid = menu.containers[super::GRID].clone();
    let Some((result, back)) = craft(env, &grid, n) else { return core::ops::ControlFlow::Continue(()) };
    menu.containers[super::RESULT][0] = Some(result.clone());
    ANSWERED.set(Some(Answered { menu: id, grid, result, back }));
    core::ops::ControlFlow::Break(())
}
"""

# The stations' screens move their slots while open (a tinker station's layout, the side inventory's scroll): a module
# in native_hooks.rs, whose children reach the open mod screen's private fields.
SCREEN_SLOTS = """impl crate::game::Game<'_> {
    /// Tinkers' Construct's stations move their slots as Java's screens do (a tool's layout, the side inventory's
    /// scroll): the open mod screen of `block` takes these places, None hiding a slot. False when another is open.
    pub(in crate::game) fn hz_tconstruct_set_screen_slots(&mut self, block: &str, slots: &[Option<[f32; 2]>]) -> bool {
        let Some(s) = self.mod_screen.as_mut() else { return false };
        if s.block != block {
            return false;
        }
        for (i, p) in slots.iter().enumerate() {
            if let Some(slot) = s.screen.slots.get_mut(i) {
                *slot = *p;
            }
        }
        true
    }
}
"""

SPECIAL_HELPERS = {
    "embedded_content.rs": """// Tinkers' Construct is one file on the registry: its data and textures are the content mod in this bundle's data/
// (made by tools/make_content.py from the jar). It is written out once and loaded as a dev mod is.
fn tconstruct_embedded_content(root: &std::path::Path, enabled: &std::collections::BTreeSet<String>, dev: &[std::path::PathBuf]) -> core::ops::ControlFlow<std::path::PathBuf> {
    static CONTENT: &[u8] = horizon_client::native_data!("tconstruct", "tconstruct-content.hmod");
    let dir = std::env::current_dir().unwrap_or_default().join(".horizon-cache");
    let file = dir.join("tconstruct-embedded-content.hmod");
    if dev.contains(&file) {
        return core::ops::ControlFlow::Continue(());
    }
    let same = std::fs::read(&file).is_ok_and(|on_disk| on_disk == CONTENT);
    if !same && std::fs::create_dir_all(&dir).and_then(|()| std::fs::write(&file, CONTENT)).is_err() {
        log::warn!("Horizon: Tinkers' Construct's content could not be written to {}", file.display());
        return core::ops::ControlFlow::Continue(());
    }
    let mut with = dev.to_vec();
    with.push(file);
    core::ops::ControlFlow::Break(content_root(root, enabled, &with))
}
""",
    "drops.rs": """fn tconstruct_drops(game: &mut crate::game::Game<'_>, pos: [i32; 3], state: BlockStateId, drops: &mut Vec<ItemStack>) {
    let block = game.res.facts().get(state).name.to_string();
    crate::game::tconstruct::block_drops(game, pos, &block, drops);
}
""",
    "fuel_items.rs": FUEL_MODULE,
    "particles.rs": PARTICLES_MODULE,
    "screen_slots.rs": SCREEN_SLOTS,
    "list.rs": """fn tconstruct_list(mods: &mut Vec<crate::game::native_hooks::NativeMod>) {
    mods.push(crate::game::native_hooks::NativeMod {
        id: "tconstruct".into(),
        title: "Tinkers' Construct 3.12.1".into(),
        description: "Tools built from parts, smelteries and casting, as in Tinkers' Construct.".into(),
        // ToolClientEvents' key mappings (Options > Mods): the helmet's and the leggings' interactions.
        keys: vec![
            ["helmet_interact".into(), "Helmet Interaction".into(), "key.keyboard.z".into()],
            ["leggings_interact".into(), "Leggings Interaction".into(), "key.keyboard.i".into()],
        ],
    });
}
""",
}


def binding_lines(bindings):
    return "".join(f'  {{ name = "{n}", ty = "{t}", value = "{v}" }},\n' for n, t, v in bindings)


def main():
    BUNDLE.mkdir(parents=True, exist_ok=True)
    out = [
        "[mod]",
        'id = "tconstruct"',
        f'version = "{VERSION}"',
        "",
        "# The Horizon commit this bundle was built and tested on.",
        "[compatibility]",
        f'horizon_revision = "{HORIZON}"',
        "",
        "[[module]]",
        'id = "tconstruct"',
        'file = "crates/horizon-client/src/game.rs"',
        'name = "tconstruct"',
        'source = "tconstruct.rs"',
        "",
        "[[module]]",
        'id = "tconstruct-fuel-items"',
        'file = "crates/horizon-client/src/menu.rs"',
        'name = "tconstruct_fuel"',
        'source = "fuel_items.rs"',
        "",
        "[[module]]",
        'id = "tconstruct-particles"',
        'file = "crates/horizon-client/src/animate_tick.rs"',
        'name = "tconstruct_particles"',
        'source = "particles.rs"',
        "",
        "[[module]]",
        'id = "tconstruct-screen-slots"',
        'file = "crates/horizon-client/src/game/native_hooks.rs"',
        'name = "tconstruct_screen_slots"',
        'source = "screen_slots.rs"',
        "",
        "[[module]]",
        'id = "tconstruct-tint"',
        'file = "crates/horizon-client-render/src/mesher.rs"',
        'name = "hz_tconstruct_tint"',
        'source = "tinting.rs"',
        "",
    ]
    for hook_id, hook, bindings, body in HOOKS:
        helper = f"h_{hook_id.replace('-', '_')}.rs"
        args = ", ".join(f"{n}: {t}" for n, t, _ in bindings)
        if body is None:
            text = SLOT_RULES
        else:
            text = f"fn tconstruct_{hook_id.replace('-', '_')}({args}) {{\n    {M}::{body};\n}}\n"
        (BUNDLE / helper).write_text(text, encoding="utf8")
        target = [f'target = "{hook[7:]}"'] if hook.startswith("target:") else [f'hook = "{hook}"', "hook_version = 1"]
        out += ["[[injection]]", f'id = "tc-{hook_id}"', 'kind = "HEAD"', *target, f'helper = "{helper}"', "bindings = [", binding_lines(bindings).rstrip("\n"), "]", ""]
    for hook_id, target, bindings, ret, body in WEAPON_HOOKS:
        helper = f"h_{hook_id.replace('-', '_')}.rs"
        args = ", ".join(f"{n}: {t}" for n, t, _ in bindings)
        (BUNDLE / helper).write_text(f"fn tconstruct_{hook_id.replace('-', '_')}({args}) -> core::ops::ControlFlow<{ret}> {{\n    {M}::{body}\n}}\n", encoding="utf8")
        out += ["[[injection]]", f'id = "tc-{hook_id}"', 'kind = "HEAD"', "cancellable = true", f'target = "{target}"', f'helper = "{helper}"', "bindings = [", binding_lines(bindings).rstrip("\n"), "]", ""]
    for hook_id, target, bindings, ret, body in RAW_HOOKS:
        helper = f"h_{hook_id.replace('-', '_')}.rs"
        args = ", ".join(f"{n}: {t}" for n, t, _ in bindings)
        (BUNDLE / helper).write_text(f"fn tconstruct_{hook_id.replace('-', '_')}({args}) -> core::ops::ControlFlow<{ret}> {{\n    {body.format(M=M)}\n}}\n", encoding="utf8")
        out += ["[[injection]]", f'id = "tc-{hook_id}"', 'kind = "HEAD"', "cancellable = true", f'target = "{target}"', f'helper = "{helper}"', "bindings = [", binding_lines(bindings).rstrip("\n"), "]", ""]
    for hook_id, target, bindings, ret, body in LIB_HOOKS:
        helper = f"h_{hook_id.replace('-', '_')}.rs"
        args = ", ".join(f"{n}: {t}" for n, t, _ in bindings)
        returns = f" -> core::ops::ControlFlow<{ret}>" if ret else ""
        call = body if ret else f"{body};"
        (BUNDLE / helper).write_text(f"fn tconstruct_{hook_id.replace('-', '_')}({args}){returns} {{\n    {call}\n}}\n", encoding="utf8")
        cancel = ["cancellable = true"] if ret else []
        out += ["[[injection]]", f'id = "tc-{hook_id}"', 'kind = "HEAD"', *cancel, f'target = "{target}"', f'helper = "{helper}"', "bindings = [", binding_lines(bindings).rstrip("\n"), "]", ""]
    for mod_id, file, name, source, visibility in (EFFECT_MODULES if "effects" not in PAUSED else []):
        out += ["[[module]]", f'id = "{mod_id}"', f'file = "{file}"', f'name = "{name}"', f'source = "{source}"', *([f'visibility = "{visibility}"'] if visibility else []), ""]
    for hook_id, kind, target, bindings, ret, body in (EFFECT_HOOKS if "effects" not in PAUSED else []):
        helper = f"h_{hook_id.replace('-', '_')}.rs"
        args = ", ".join(f"{n}: {t}" for n, t, _ in bindings)
        returns = f" -> core::ops::ControlFlow<{ret}>" if kind == "HEAD-cancel" else f" -> {ret}" if ret else ""
        (BUNDLE / helper).write_text(f"fn tconstruct_{hook_id.replace('-', '_')}({args}){returns} {{\n    {body}\n}}\n", encoding="utf8")
        head = ['kind = "HEAD"', "cancellable = true"] if kind == "HEAD-cancel" else [f'kind = "{kind}"']
        out += ["[[injection]]", f'id = "tc-{hook_id}"', *head, f'target = "{target}"', f'helper = "{helper}"', "bindings = [", binding_lines(bindings).rstrip("\n"), "]", ""]
    for name, text in SPECIAL_HELPERS.items():
        (BUNDLE / name).write_text(text, encoding="utf8")
    out += ["[[injection]]", 'id = "tc-drops"', 'kind = "HEAD"', 'target = "horizon_client::game::native_hooks::Game<\'_>::native_block_drops"', 'helper = "drops.rs"', "bindings = [", binding_lines([GAME_MUT, ("pos", "[i32; 3]", "pos"), ("state", "BlockStateId", "state"), ("drops", "&mut Vec<ItemStack>", "&mut *drops")]).rstrip("\n"), "]", ""]
    out += ["[[injection]]", 'id = "tc-list"', 'kind = "HEAD"', 'hook = "mods"', "hook_version = 1", 'helper = "list.rs"', "bindings = [", binding_lines([("mods", "&mut Vec<crate::game::native_hooks::NativeMod>", "&mut *mods")]).rstrip("\n"), "]", ""]
    out += ["[[injection]]", 'id = "tc-embedded-content"', 'kind = "HEAD"', "cancellable = true", 'target = "horizon_client::game::mods::content_root"', 'helper = "embedded_content.rs"', "bindings = [", binding_lines([("root", "&std::path::Path", "root"), ("enabled", "&std::collections::BTreeSet<String>", "enabled"), ("dev", "&[std::path::PathBuf]", "dev")]).rstrip("\n"), "]", ""]
    # The fancy item frames and armor stands (tools/fancy_hooks.py; fancy_lib.rs, fancy_frames.rs).
    sys.path.insert(0, str(ROOT / "tools"))
    if "fancy" not in PAUSED:
        import fancy_hooks
        out += fancy_hooks.emit(BUNDLE, binding_lines)
    (BUNDLE / "horizon-mixin.toml").write_text("\n".join(out), encoding="utf8")
    subprocess.run([sys.executable, str(ROOT.parent / "jei-kit" / "apply.py"), "tconstruct", str(BUNDLE)], check=True)
    for fixer in ("unused_helper_params.py", "use_helper_params.py"):
        subprocess.run([sys.executable, str(ROOT.parent / "tools" / fixer), str(BUNDLE)], check=True)
    (BUNDLE / "data").mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_content.py"), str(JAR), str(BUNDLE / "data" / "tconstruct-content.hmod"),
                    "--report", str(ROOT / "content-report.json"),
                    "--fluids", str(BUNDLE / "data" / "tconstruct-fluids.json")], check=True)
    target = BUILD / "mixins" / "tconstruct"
    target.mkdir(parents=True, exist_ok=True)
    for old in target.rglob("*"):
        if old.is_file():
            old.unlink()
    for f in BUNDLE.rglob("*"):
        if f.is_file():
            to = target / f.relative_to(BUNDLE)
            to.parent.mkdir(parents=True, exist_ok=True)
            to.write_bytes(f.read_bytes())
    (BUILD / "horizon-native.json").write_text(json.dumps({"game": "26.3", "horizon": HORIZON, "id": "tconstruct", "mixins": MIXINS, "schema": 1, "version": VERSION}, indent=2), encoding="utf8")
    print("bundle written:", len(HOOKS) + len(WEAPON_HOOKS) + len(RAW_HOOKS) + len(LIB_HOOKS) + (len(EFFECT_HOOKS) if "effects" not in PAUSED else 0) + 3, "injections")


if __name__ == "__main__":
    main()
