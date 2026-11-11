use super::{Game, GameLevel, Hit, InteractTarget};
use horizon_client::entities::{ArmorStand, ItemFrame};
use horizon_client::items::ItemStack;
use horizon_client::mesher::Vertex;
use horizon_core::geometry::{Aabb, Direction, Vec3};
use horizon_core::position::BlockPos;
use horizon_core::random::RandomSource;
use horizon_protocol::entity_data::{Value, serializer};
use horizon_world::nbt::Tag;
use std::ops::ControlFlow;
use std::sync::Arc;

// Tinkers' Construct's fancy item frames and fancy armor stands (spec-gadgets.md G.9), as Horizon's item frames and
// armor stands with a variant (fancy_lib.rs keeps it by entity id): FancyItemFrameEntity and its FancyItemFrameItem,
// FancyItemFrameRenderer; FancyArmorStandEntity, FancyArmorStandItem, DispenseFancyArmorStand, FancyArmorStandRenderer.

const FRAME_KIND: &str = "tconstruct:fancy_item_frame";
const STAND_KIND: &str = "tconstruct:armor_stand";

// FrameType ids.
const REVERSED_GOLD: u8 = 0;
const DIAMOND: u8 = 1;
const MANYULLYN: u8 = 2;
const GOLD: u8 = 3;
const CLEAR: u8 = 4;
const NETHERITE: u8 = 5;
// StandType ids.
const BAMBOO: u8 = 0;
const BONE: u8 = 1;
const NECROTIC_BONE: u8 = 2;
const CLEAR_STAND: u8 = 3;

// The hooks that call their own target again (fancy_lib.rs's guard bits 1, 2 and 4 are the client library's).
const IN_INTERACT: u32 = 8;
const IN_ATTACK: u32 = 16;
const IN_DRAW: u32 = 32;
const IN_BLAST: u32 = 64;
const IN_LAN: u32 = 128;
const IN_STAND_DRAW: u32 = 256;
const IN_PUNCH: u32 = 512;
const IN_DISPENSE: u32 = 1024;
const IN_SAVE: u32 = 2048;

// FancyItemFrameEntity.doesRotate.
fn does_rotate(v: u8) -> bool {
    matches!(v, GOLD | REVERSED_GOLD | DIAMOND)
}

// FrameType.hasMoreRotations: 16 steps of 22.5 degrees.
fn more_rotations(v: u8) -> bool {
    matches!(v, DIAMOND | MANYULLYN | NETHERITE)
}

// FrameType.byId: an unknown id is the first type.
fn frame_type(id: i64) -> u8 {
    if (0..6).contains(&id) { id as u8 } else { 0 }
}

// StandType.byId.
fn stand_type(id: i64) -> u8 {
    if (0..4).contains(&id) { id as u8 } else { 0 }
}

fn frame_center(f: &ItemFrame) -> [f64; 3] {
    let (lo, hi) = f.bounds();
    std::array::from_fn(|i| (lo[i] + hi[i]) / 2.0)
}

fn int(tag: &Tag, key: &str) -> i64 {
    horizon_client::save::number(tag.get(key)).unwrap_or(0)
}

// ---- Placing

/// The cancellable head of `frames::Game::place_item_frame`: FancyItemFrameItem.useOn.
pub(super) fn place_frame(game: &mut Game<'_>, hit: &Hit, stack: &ItemStack) -> ControlFlow<bool> {
    let Some(variant) = ItemFrame::hz_tc_frame_variant_of(&stack.item) else {
        return ControlFlow::Continue(());
    };
    let pos: [i32; 3] = std::array::from_fn(|i| hit.pos[i] + hit.face[i]);
    // canPlace: `isOutsideBuildHeight` is FAIL.
    if !(horizon_client::chunk::MIN_Y..horizon_client::chunk::MIN_Y + horizon_client::chunk::HEIGHT).contains(&pos[1]) {
        game.use_failed = true;
        return ControlFlow::Break(true);
    }
    let mut frame = ItemFrame {
        id: game.next_entity + 1,
        pos,
        facing: match hit.face {
            [0, -1, 0] => 0,
            [0, 1, 0] => 1,
            [0, 0, -1] => 2,
            [0, 0, 1] => 3,
            [-1, 0, 0] => 4,
            _ => 5,
        },
        glow: false,
        item: None,
        rotation: 0,
        drop_chance: 1.0,
        fixed: false,
        invisible: false,
        check_interval: 0,
        custom_name: stack.data().and_then(|d| d.custom_name.clone()),
    };
    // The frame's own tag with its Variant, the item's entity data over it (EntityType.updateCustomEntityTag).
    let mut own = horizon_client::entity_nbt::item_frame_to_nbt(&frame, [0; 4], None);
    if let Tag::Compound(map) = &mut own {
        map.insert("id".into(), Tag::String(FRAME_KIND.into()));
        map.insert("Variant".into(), Tag::Int(i32::from(variant)));
    }
    let configured = horizon_client::block_entity_item::stack_configured_entity(stack, FRAME_KIND, &own);
    if let Some(loaded) = horizon_client::entity_nbt::item_frame_from_nbt(&configured, frame.id) {
        frame = ItemFrame { glow: false, ..loaded };
    }
    let variant = frame_type(int(&configured, "Variant"));
    // HangingEntity.survives false: CONSUME, which ItemStack.useOn still counts as a use.
    if !frame_survives(game, &frame) {
        game.award_stat("used", &stack.item, 1);
        return ControlFlow::Break(true);
    }
    if game.hanging_place_cancelled(FRAME_KIND, pos) {
        return ControlFlow::Break(true);
    }
    game.next_entity += 1;
    ItemFrame::hz_tc_set_frame(frame.id, Some((variant, 0)));
    // playPlacementSound, then the frame joins (FancyItemFrameItem posts no game event).
    game.audio.play("minecraft:entity.item_frame.place", Some(frame_center(&frame)), 1.0, 1.0);
    game.world.modified.insert((pos[0] >> 4, pos[2] >> 4));
    let mut raw = configured;
    if let Tag::Compound(map) = &mut raw {
        map.remove(&"UUID".into());
    }
    game.persist.raw.insert(frame.id, raw);
    game.item_frames.push(frame);
    if !game.creative {
        game.consume_held();
    }
    game.award_stat("used", &stack.item, 1);
    ControlFlow::Break(true)
}

/// `ItemFrame.survives` (frames.rs's own is private): nothing in the way, a solid block behind (or a diode for a wall
/// frame), no hanging entity facing the same way overlapping it.
fn frame_survives(game: &Game<'_>, f: &ItemFrame) -> bool {
    if f.fixed {
        return true;
    }
    let (lo, hi) = f.bounds();
    let bounds = Aabb::new(Vec3::new(lo[0], lo[1], lo[2]), Vec3::new(hi[0], hi[1], hi[2]));
    let mut scene = horizon_client::collisions::SceneCollisions { world: &game.world, binding: game.collision, subject: None };
    if !scene.unobstructed(bounds).unwrap_or(false) {
        return false;
    }
    let s = f.step();
    let behind = game.res.facts().get(game.world.block(f.pos[0] - s[0], f.pos[1] - s[1], f.pos[2] - s[2]));
    let supported = behind.legacy_solid || (s[1] == 0 && behind.has_class("DiodeBlock"));
    supported && super::paintings::frame_coexists(f, &game.item_frames, &game.paintings)
}

/// The cancellable head of `armor_stands::Game::place_armor_stand`: FancyArmorStandItem.useOn, then its
/// StandType.onPlace (bamboo is small, the bones show their arms) and LeftHanded by the hand that placed it.
pub(super) fn place_stand(game: &mut Game<'_>, hit: &Hit, stack: &ItemStack) -> ControlFlow<bool> {
    let Some(variant) = ItemFrame::hz_tc_stand_variant_of(&stack.item) else {
        return ControlFlow::Continue(());
    };
    // Not on a bottom face, nothing in the vanilla stand's box: FAIL, as Horizon answers a vanilla stand's.
    let Some((pos, mut stand)) = game.armor_stand_spawn(hit, stack) else {
        return ControlFlow::Break(false);
    };
    let drop = game.drop_offset_from(0.5, 1.975, (pos[0], pos[1], pos[2]), true);
    stand.position.y = f64::from(pos[1]) + drop;
    stand.previous = stand.position;
    let own = horizon_client::entity_nbt::armor_stand_to_nbt(&stand, [0; 4], None);
    let mut raw = horizon_client::block_entity_item::stack_configured_entity(stack, STAND_KIND, &own);
    if let Some(loaded) = horizon_client::entity_nbt::armor_stand_from_nbt(&raw, stand.id) {
        let mut loaded = loaded;
        loaded.first_tick = stand.first_tick;
        loaded.yaw = stand.yaw;
        loaded.previous_yaw = stand.previous_yaw;
        loaded.pitch = 0.0;
        loaded.previous = loaded.position;
        stand = loaded;
    }
    match variant {
        BAMBOO => stand.small = true,
        BONE | NECROTIC_BONE => stand.show_arms = true,
        _ => {}
    }
    // setLeft(hand == MAIN_HAND == (player.getMainArm() == LEFT)).
    let left_handed = match game.lan_acting_uuid {
        Some(uuid) => ItemFrame::hz_tc_guest_left(uuid),
        None => game.settings.main_hand_left,
    };
    let left = (game.hand == horizon_client::first_person::Hand::Main) == left_handed;
    if let Tag::Compound(map) = &mut raw {
        map.remove(&"UUID".into());
    }
    game.persist.raw.insert(stand.id, raw);
    let foot = stand.position;
    game.world.random.next_float();
    game.next_entity += 1;
    ArmorStand::hz_tc_set_stand(stand.id, Some((variant, left)));
    game.audio.play("minecraft:entity.armor_stand.place", Some([foot.x, foot.y, foot.z]), 0.75, 0.8);
    let ctx = game.player_context(None);
    game.post_game_event("minecraft:entity_place", [foot.x, foot.y, foot.z], ctx);
    game.world.modified.insert((pos[0] >> 4, pos[2] >> 4));
    game.armor_stands.push(stand);
    if !game.creative {
        game.consume_held();
    }
    game.award_stat("used", &stack.item, 1);
    game.swing_arm();
    ControlFlow::Break(true)
}

/// The cancellable head of `dispenser::Game::dispense_item`: DispenseFancyArmorStand, the vanilla stand's dispense
/// with the stand's StandType.onPlace.
pub(super) fn dispense(
    game: &mut Game<'_>,
    pos: (i32, i32, i32),
    facing: Direction,
    stack: &ItemStack,
) -> ControlFlow<horizon_client::Result<Option<ItemStack>>> {
    let Some(variant) = ItemFrame::hz_tc_stand_variant_of(&stack.item) else {
        return ControlFlow::Continue(());
    };
    if !ItemFrame::hz_tc_enter(IN_DISPENSE) {
        return ControlFlow::Continue(());
    }
    let before = game.armor_stands.len();
    let vanilla = ItemStack { item: Arc::from("minecraft:armor_stand"), ..stack.clone() };
    let left = game.dispense_item(pos, facing, vanilla);
    ItemFrame::hz_tc_leave(IN_DISPENSE);
    if game.armor_stands.len() > before
        && let Some(stand) = game.armor_stands.last_mut()
    {
        match variant {
            BAMBOO => stand.small = true,
            BONE | NECROTIC_BONE => stand.show_arms = true,
            _ => {}
        }
        ArmorStand::hz_tc_set_stand(stand.id, Some((variant, false)));
    }
    let left = match left {
        Ok(Some(mut rest)) if &*rest.item == "minecraft:armor_stand" => {
            rest.item = stack.item.clone();
            Ok(Some(rest))
        }
        other => other,
    };
    ControlFlow::Break(left)
}

// ---- Using and hitting a frame

/// The cancellable head of `frames::Game::interact_frame`: a clear frame holding an item hands a click (not sneaking)
/// to the block behind it, then the frame's own (vanilla's): putting an item in resets a turning frame, and a turn
/// goes by the frame's steps (FancyItemFrameEntity.setRotation: the diamond one clicks and stops at 16).
pub(super) fn interact_frame(game: &mut Game<'_>, target: Option<InteractTarget>) -> ControlFlow<bool> {
    if !ItemFrame::hz_tc_any() || game.remote.is_some() {
        return ControlFlow::Continue(());
    }
    let found = match target {
        Some(t) => Game::named_entity(&game.item_frames, t.id, |f| f.id).map(|i| (i, 0.0)),
        None => game.frame_hit(),
    };
    let Some((i, d)) = found else { return ControlFlow::Continue(()) };
    let Some((variant, _)) = ItemFrame::hz_tc_frame(game.item_frames[i].id) else {
        return ControlFlow::Continue(());
    };
    if target.is_none() && !game.before_block(d) {
        return ControlFlow::Continue(());
    }
    let (id, had, before) = (game.item_frames[i].id, game.item_frames[i].item.is_some(), game.item_frames[i].rotation);
    if variant == CLEAR && had && !game.native_sneaking() && use_block_behind(game, i) {
        return ControlFlow::Break(true);
    }
    if !ItemFrame::hz_tc_enter(IN_INTERACT) {
        return ControlFlow::Continue(());
    }
    let done = game.interact_frame(target);
    ItemFrame::hz_tc_leave(IN_INTERACT);
    let Some(j) = game.item_frames.iter().position(|f| f.id == id) else {
        return ControlFlow::Break(done);
    };
    let now = game.item_frames[j].item.is_some();
    if !had && now {
        // setItem(stack, true): a turning frame starts again at 0 (setRotation(0, false): no comparator update).
        if does_rotate(variant) {
            game.item_frames[j].rotation = 0;
            ItemFrame::hz_tc_set_frame(id, Some((variant, 0)));
        }
    } else if had && done && game.item_frames[j].rotation != before {
        // setRotation(getRotation() + 1).
        set_rotation(game, j, variant, i32::from(before) + 1, true);
    }
    ControlFlow::Break(done)
}

/// `BlockState.use` of the block behind a clear frame (FancyItemFrameEntity.interact), with the hand emptied so only the
/// block acts (Horizon's click would go on to use the item on it). Whether the block took the click.
fn use_block_behind(game: &mut Game<'_>, i: usize) -> bool {
    let f = &game.item_frames[i];
    let s = f.step();
    let behind = [f.pos[0] - s[0], f.pos[1] - s[1], f.pos[2] - s[2]];
    let state = game.world.block(behind[0], behind[1], behind[2]);
    if game.res.facts().is_air(state) {
        return false;
    }
    // Util.createTraceResult(behind, direction, false): the face the frame hangs on, at its centre.
    let point = std::array::from_fn(|k| f64::from(behind[k]) + 0.5 + f64::from(s[k]) * 0.5);
    let hit = Hit { pos: behind, face: s, point };
    let held = game.held_mut().take();
    let used = game.use_hand(Some(&hit)).unwrap_or(false);
    if let Some(stack) = held {
        if game.held().is_none() {
            *game.held_mut() = Some(stack);
        } else {
            game.give_or_drop(stack);
        }
    }
    used
}

/// FancyItemFrameEntity.setRotation(rotation, updateComparator): the timer starts again, the diamond frame clicks (on a
/// comparator update) and stops at 16, the other 16-step frames wrap at 16, the rest at 8.
fn set_rotation(game: &mut Game<'_>, i: usize, variant: u8, rotation: i32, update: bool) {
    let rotation = if more_rotations(variant) {
        if variant == DIAMOND {
            if update {
                let at = frame_center(&game.item_frames[i]);
                game.audio.play("tconstruct:item_frame_click", Some(at), 1.0, 1.0);
            }
            rotation.min(16)
        } else {
            rotation.rem_euclid(16)
        }
    } else {
        rotation.rem_euclid(8)
    };
    let f = &mut game.item_frames[i];
    f.rotation = rotation.clamp(0, 16) as u8;
    let (id, pos) = (f.id, f.pos);
    ItemFrame::hz_tc_set_frame(id, Some((variant, 0)));
    game.world.modified.insert((pos[0] >> 4, pos[2] >> 4));
    if update {
        let at = BlockPos::new(pos[0], pos[1], pos[2]);
        game.with_level(|b, level, ticks| b.update_neighbour_for_output_signal(level, ticks, at));
    }
}

/// The cancellable head of `frames::Game::attack_frame`: taking the item out of a turning frame resets it
/// (FancyItemFrameEntity.setItem(EMPTY, true)); the frame drops its own item (fancy_lib.rs).
pub(super) fn attack_frame(game: &mut Game<'_>) -> ControlFlow<bool> {
    if !ItemFrame::hz_tc_any() || game.remote.is_some() {
        return ControlFlow::Continue(());
    }
    let Some((i, _)) = game.frame_hit() else { return ControlFlow::Continue(()) };
    let id = game.item_frames[i].id;
    let Some((variant, _)) = ItemFrame::hz_tc_frame(id) else { return ControlFlow::Continue(()) };
    let had = game.item_frames[i].item.is_some();
    if !does_rotate(variant) || !had || !ItemFrame::hz_tc_enter(IN_ATTACK) {
        return ControlFlow::Continue(());
    }
    let done = game.attack_frame();
    ItemFrame::hz_tc_leave(IN_ATTACK);
    if let Some(f) = game.item_frames.iter_mut().find(|f| f.id == id)
        && f.item.is_none()
    {
        f.rotation = 0;
        ItemFrame::hz_tc_set_frame(id, Some((variant, 0)));
    }
    ControlFlow::Break(done)
}

/// The cancellable head of `frames::Game::explosion_breaks_frames`: a netherite frame ignores explosions
/// (FancyItemFrameEntity.ignoreExplosion); it is kept as a fixed frame is while the blast is worked out.
pub(super) fn explosion(
    game: &mut Game<'_>,
    blast: [f64; 3],
    diameter: f64,
    interaction: super::explosion::BlockInteraction,
) -> ControlFlow<()> {
    if !ItemFrame::hz_tc_any() {
        return ControlFlow::Continue(());
    }
    let spared: Vec<u32> = game
        .item_frames
        .iter()
        .filter(|f| !f.fixed && ItemFrame::hz_tc_frame(f.id).is_some_and(|(v, _)| v == NETHERITE))
        .map(|f| f.id)
        .collect();
    if spared.is_empty() || !ItemFrame::hz_tc_enter(IN_BLAST) {
        return ControlFlow::Continue(());
    }
    for f in game.item_frames.iter_mut().filter(|f| spared.contains(&f.id)) {
        f.fixed = true;
    }
    game.explosion_breaks_frames(blast, diameter, interaction);
    ItemFrame::hz_tc_leave(IN_BLAST);
    for f in game.item_frames.iter_mut().filter(|f| spared.contains(&f.id)) {
        f.fixed = false;
    }
    ControlFlow::Break(())
}

/// The head of `frames::Game::tick_item_frames`: FancyItemFrameEntity.tick on the server. A golden frame turns a step
/// every 20 ticks (the inverted one back), the diamond one turns back a step every 300 ticks until it is at 0.
pub(super) fn tick_frames(game: &mut Game<'_>) {
    if !ItemFrame::hz_tc_any() || game.remote.is_some() {
        return;
    }
    let ticking = game.entity_ticking_area();
    for i in 0..game.item_frames.len() {
        let f = &game.item_frames[i];
        let Some((variant, timer)) = ItemFrame::hz_tc_frame(f.id) else { continue };
        if !does_rotate(variant) {
            continue;
        }
        let at = frame_center(f);
        if !ticking(at[0].floor() as i32, at[2].floor() as i32) {
            continue;
        }
        let (id, rotation) = (f.id, i32::from(f.rotation));
        let timer = timer + 1;
        if variant == DIAMOND {
            if timer >= 300 {
                ItemFrame::hz_tc_set_frame(id, Some((variant, 0)));
                if rotation > 0 {
                    set_rotation(game, i, variant, rotation - 1, true);
                }
            } else {
                ItemFrame::hz_tc_set_frame(id, Some((variant, timer)));
            }
        } else if timer >= 20 {
            let next = if variant == REVERSED_GOLD {
                if rotation - 1 == -1 { 7 } else { rotation - 1 }
            } else {
                rotation + 1
            };
            set_rotation(game, i, variant, next, true);
        } else {
            ItemFrame::hz_tc_set_frame(id, Some((variant, timer)));
        }
    }
}

/// The cancellable head of `<GameLevel as LevelAccess>::item_frame_analog_output`: a 16-step frame's signal is its
/// rotation (FancyItemFrameEntity.getAnalogOutput), any other frame's vanilla's.
pub(super) fn analog(level: &GameLevel<'_>, pos: BlockPos, facing: Direction) -> ControlFlow<Option<i32>> {
    if !ItemFrame::hz_tc_any() {
        return ControlFlow::Continue(());
    }
    let mut frames = level.item_frames.iter().filter(|f| f.pos == [pos.x, pos.y, pos.z] && f.facing == facing as u8);
    let (Some(frame), None) = (frames.next(), frames.next()) else {
        return ControlFlow::Break(None);
    };
    let more = ItemFrame::hz_tc_frame(frame.id).is_some_and(|(v, _)| more_rotations(v));
    let signal = match (&frame.item, more) {
        (None, _) => 0,
        (Some(_), true) => i32::from(frame.rotation),
        (Some(_), false) => i32::from(frame.rotation % 8) + 1,
    };
    ControlFlow::Break(Some(signal))
}

// ---- Saving, loading, the level's end

/// The cancellable head of `persist::Game::load_unlisted`: a saved fancy frame or stand loads as Horizon's own with
/// its Variant (and RotationTimer, LeftHanded).
pub(super) fn load(
    game: &mut Game<'_>,
    kind: &str,
    uuid: Option<[i32; 4]>,
    tag: &Tag,
) -> ControlFlow<std::result::Result<(), Tag>> {
    match kind {
        FRAME_KIND => {
            let before = game.item_frames.len();
            game.load_item_frame(tag.clone(), uuid);
            if game.item_frames.len() > before
                && let Some(f) = game.item_frames.last()
            {
                let variant = frame_type(int(tag, "Variant"));
                let timer = if does_rotate(variant) { int(tag, "RotationTimer") as i32 } else { 0 };
                ItemFrame::hz_tc_set_frame(f.id, Some((variant, timer)));
            }
            ControlFlow::Break(Ok(()))
        }
        STAND_KIND => {
            let before = game.armor_stands.len();
            game.load_armor_stand(tag.clone(), uuid);
            if game.armor_stands.len() > before
                && let Some(a) = game.armor_stands.last()
            {
                let left = int(tag, "LeftHanded") != 0;
                ArmorStand::hz_tc_set_stand(a.id, Some((stand_type(int(tag, "Variant")), left)));
            }
            ControlFlow::Break(Ok(()))
        }
        _ => ControlFlow::Continue(()),
    }
}

/// `persist::Game::save_armor_stand`'s fancy stand: whether stand `i` is one (and the save enters it); `saved_stand`
/// then writes its id, Variant and LeftHanded (FancyArmorStandEntity.addAdditionalSaveData).
pub(super) fn saving_stand(game: &Game<'_>, i: usize) -> Option<u32> {
    let id = game.armor_stands.get(i)?.id;
    ArmorStand::hz_tc_stand(id)?;
    ItemFrame::hz_tc_enter(IN_SAVE).then_some(id)
}

pub(super) fn saved_stand(id: u32, tag: Option<&mut Tag>) {
    ItemFrame::hz_tc_leave(IN_SAVE);
    let Some((variant, left)) = ArmorStand::hz_tc_stand(id) else { return };
    if let Some(Tag::Compound(map)) = tag {
        map.insert("id".into(), Tag::String(STAND_KIND.into()));
        map.insert("Variant".into(), Tag::Int(i32::from(variant)));
        map.insert("LeftHanded".into(), Tag::Byte(i8::from(left)));
    }
}

/// The head of `Game::clear_entities`: the next world's entities are not these.
pub(super) fn clear() {
    ItemFrame::hz_tc_clear();
}

/// The head of `native_hooks::Game::native_player_change_main_hand`: a guest's main arm, for a stand they place.
pub(super) fn main_hand(player: u128, left: bool) {
    ItemFrame::hz_tc_set_guest_arm(player, left);
}

/// The cancellable head of `pick_entity::Game::pick_entity_hit`: its answer, remembered for the pick's item.
pub(super) fn pick_hit(game: &Game<'_>) -> ControlFlow<Option<Option<i32>>> {
    let hit = game.pick_entity_hit_at().map(|b| b.1);
    ItemFrame::hz_tc_set_picked(hit.flatten());
    ControlFlow::Break(hit)
}

/// The head of `pick_entity::Game::within_entity_range`: a guest's pick names the entity first.
pub(super) fn pick_guest(id: i32) {
    ItemFrame::hz_tc_set_picked(Some(id));
}

// ---- What LAN guests get

/// The cancellable head of `lan_entities::Game::lan_object_states`: a fancy frame goes out as an item frame with its
/// VARIANT (entity data 11), a fancy stand as an armor stand with VARIANT and LEFT_HANDED (22 and 23).
pub(super) fn lan_states(
    game: &mut Game<'_>,
    hub: &mut horizon_client::lan::hub::Hub,
    out: &mut horizon_client::lan::entity::States,
    drain_minecart_steps: bool,
    after: u32,
) -> ControlFlow<()> {
    if !ItemFrame::hz_tc_any() || !ItemFrame::hz_tc_enter(IN_LAN) {
        return ControlFlow::Continue(());
    }
    let start = out.as_slice().len();
    game.lan_object_states(hub, out, drain_minecart_steps, after);
    ItemFrame::hz_tc_leave(IN_LAN);
    for e in &mut out.as_mut_slice()[start..] {
        let Ok(id) = u32::try_from(e.id) else { continue };
        if e.kind == FRAME_KIND {
            let Some((variant, _)) = ItemFrame::hz_tc_frame(id) else { continue };
            e.kind = "minecraft:item_frame".into();
            e.meta.push((11, serializer::INT, Value::Int(i32::from(variant))));
        } else if e.kind == "minecraft:armor_stand" {
            let Some((variant, left)) = ArmorStand::hz_tc_stand(id) else { continue };
            e.meta.push((22, serializer::INT, Value::Int(i32::from(variant))));
            if left {
                e.meta.push((23, serializer::BOOLEAN, Value::Bool(true)));
            }
            e.defaults.push((23, serializer::BOOLEAN, Value::Bool(false)));
        }
    }
    ControlFlow::Break(())
}

/// The cancellable head of `remote_objects::Game::remote_object_data` on a guest: a frame's VARIANT makes it fancy, and
/// a fancy frame takes its rotation whole (up to 16); a stand's VARIANT and LEFT_HANDED make it fancy.
pub(super) fn remote_data(game: &mut Game<'_>, id: i32, values: &[(u8, i32, Value)]) -> ControlFlow<()> {
    let Ok(uid) = u32::try_from(id) else { return ControlFlow::Continue(()) };
    if let Some(i) = game.item_frames.iter().position(|f| f.id == uid) {
        let mut variant = ItemFrame::hz_tc_frame(uid).map(|(v, _)| v);
        for (index, _, value) in values {
            if let (11, Value::Int(v)) = (index, value) {
                variant = Some(frame_type(i64::from(*v)));
            }
        }
        let Some(variant) = variant else { return ControlFlow::Continue(()) };
        ItemFrame::hz_tc_set_frame(uid, Some((variant, 0)));
        for (index, _, value) in values {
            match (index, value) {
                (0, Value::Byte(flags)) => game.item_frames[i].invisible = (*flags as u8 & 0x20) != 0,
                (8, Value::Id(d)) => game.item_frames[i].facing = (*d).clamp(0, 5) as u8,
                (9, Value::Item(stack)) => {
                    let item = game.to_stack(stack);
                    game.item_frames[i].item = item;
                }
                (10, Value::Int(r)) => {
                    game.item_frames[i].rotation = if more_rotations(variant) { (*r).clamp(0, 16) as u8 } else { r.rem_euclid(8) as u8 };
                }
                _ => {}
            }
        }
        return ControlFlow::Break(());
    }
    if let Some(a) = game.armor_stands.iter().find(|a| a.id == uid) {
        let mut info = ArmorStand::hz_tc_stand(a.id);
        for (index, _, value) in values {
            match (index, value) {
                (22, Value::Int(v)) => info = Some((stand_type(i64::from(*v)), info.is_some_and(|i| i.1))),
                (23, Value::Bool(left)) => info = info.map(|i| (i.0, *left)),
                _ => {}
            }
        }
        if info.is_some() {
            ArmorStand::hz_tc_set_stand(uid, info);
        }
    }
    ControlFlow::Continue(())
}

// ---- Drawing

/// The cancellable head of `frames::Game::frame_geometry`: Horizon draws the plain frames, then the fancy ones are
/// drawn here (FancyItemFrameRenderer).
pub(super) fn frame_geometry(game: &mut Game<'_>, camera: glam::DVec3, out: &mut Vec<Vertex>) -> ControlFlow<()> {
    if !ItemFrame::hz_tc_any() || !game.item_frames.iter().any(|f| ItemFrame::hz_tc_frame(f.id).is_some()) {
        return ControlFlow::Continue(());
    }
    if !ItemFrame::hz_tc_enter(IN_DRAW) {
        return ControlFlow::Continue(());
    }
    let all = std::mem::take(&mut game.item_frames);
    let mut fancy = Vec::new();
    let mut plain = Vec::with_capacity(all.len());
    for (i, f) in all.into_iter().enumerate() {
        if ItemFrame::hz_tc_frame(f.id).is_some() {
            fancy.push((i, f));
        } else {
            plain.push(f);
        }
    }
    game.item_frames = plain;
    game.frame_geometry(camera, out);
    ItemFrame::hz_tc_leave(IN_DRAW);
    for (i, f) in fancy {
        game.item_frames.insert(i.min(game.item_frames.len()), f);
    }
    draw_fancy_frames(game, camera, out);
    ControlFlow::Break(())
}

// FancyItemFrameRenderer's models (`tconstruct:block/frame/<type>[_map]`): vanilla's item frame with its `wood` and
// `back` textures replaced; the reversed golden frame is the golden one.
fn frame_sprite(variant: u8, sprite: &str) -> &str {
    let (wood, back) = match variant {
        DIAMOND => ("block/diamond_block", "tconstruct:block/item_frame_background"),
        MANYULLYN => ("tconstruct:block/storage/manyullyn", "tconstruct:block/item_frame_background"),
        CLEAR => ("block/white_stained_glass", "block/glass"),
        NETHERITE => ("block/netherite_block", "tconstruct:block/item_frame_background"),
        _ => ("block/gold_block", "tconstruct:block/item_frame_background"),
    };
    match sprite {
        "block/birch_planks" => wood,
        "block/item_frame" => back,
        other => other,
    }
}

/// FancyItemFrameRenderer.render for the fancy frames, in Horizon's frame drawing (frames.rs): the frame model unless
/// invisible (a clear frame holding something is), the manyullyn frame at least 7 bright with its item full bright, the
/// item 7/16 out from the wall at a 22.5 degree step for the 16-step frames, a clear frame's item at 3/4.
fn draw_fancy_frames(game: &mut Game<'_>, camera: glam::DVec3, out: &mut Vec<Vertex>) {
    let sprites = &game.gui.atlas.sprites;
    let mut maps: Vec<(i32, glam::Mat4, u32, bool)> = Vec::new();
    let mut items: Vec<(ItemStack, u32, glam::Mat4, u8, bool)> = Vec::new();
    let range = 16.0 * 64.0 * game.view_scale();
    for f in &game.item_frames {
        let Some((variant, _)) = ItemFrame::hz_tc_frame(f.id) else { continue };
        let entity_start = out.len();
        game.mark_entity(entity_start, FRAME_KIND);
        let map = f.item.as_ref().and_then(super::maps::map_id);
        let (lo, hi) = f.bounds();
        let (mut lo, mut hi) = (glam::DVec3::from(lo), glam::DVec3::from(hi));
        if map.is_some() {
            let s = f.step();
            for i in 0..3 {
                if s[i] == 0 {
                    let c = (lo[i] + hi[i]) / 2.0;
                    (lo[i], hi[i]) = (c - 0.5, c + 0.5);
                }
            }
        }
        if !game.entity_in_view(camera, (lo + hi) / 2.0, range, lo, hi) {
            continue;
        }
        let culling = game.entity_cull_decision(f, 1.0);
        if culling.hides_entity() {
            continue;
        }
        let entity_start = out.len();
        let s = f.step();
        let (x_rot, y_rot) = if s[1] == 0 {
            let to_y = match f.facing {
                3 => 0.0,
                4 => 90.0,
                2 => 180.0,
                _ => 270.0,
            };
            (0.0f64, 180.0f64 - to_y)
        } else {
            (-90.0 * f64::from(s[1]), 180.0)
        };
        let pose = glam::DMat4::from_translation(
            glam::DVec3::new(f64::from(f.pos[0]) + 0.5, f64::from(f.pos[1]) + 0.5, f64::from(f.pos[2]) + 0.5) - camera,
        ) * glam::DMat4::from_rotation_x(x_rot.to_radians())
            * glam::DMat4::from_rotation_y(y_rot.to_radians());
        let light = game.world.light(f.pos[0], f.pos[1], f.pos[2]);
        // getBlockLightLevel: the manyullyn frame is at least 7 bright.
        let light = if variant == MANYULLYN { (light & 0xF0) | (light & 15).max(7) } else { light };
        let packed = (u32::from(light >> 4) * 16) | ((u32::from(light & 15) * 16) << 8);
        let visible = !f.invisible && (variant != CLEAR || f.item.is_none());
        if visible {
            let model = if map.is_some() { &game.map_frame_model } else { &game.frame_model };
            for (corners, uv, sprite) in model {
                let Some(r) = sprites.get(frame_sprite(variant, sprite)) else { continue };
                let at = corners.map(|c| {
                    pose.transform_point3(glam::DVec3::new(
                        f64::from(c[0]) - 0.5,
                        f64::from(c[1]) - 0.5,
                        f64::from(c[2]) - 0.5,
                    ))
                });
                let n = (at[1] - at[0]).cross(at[2] - at[0]).normalize_or_zero();
                let normal = [0, 1, 2].map(|k| (n[k].clamp(-1.0, 1.0) * 127.0) as i8);
                for (p, uv) in at.into_iter().zip(*uv) {
                    out.push(Vertex {
                        normal: [normal[0], normal[1], normal[2], -127],
                        pos: p.as_vec3().to_array(),
                        uv: [r.u0 + uv[0] * (r.u1 - r.u0), r.v0 + uv[1] * (r.v1 - r.v0)],
                        layer: 0,
                        color: 0xFFFF_FFFF,
                        light: packed,
                        glint_uv: [0.0, 0.0],
                    });
                }
            }
        }
        game.finish_entity_occlusion(culling, f, out, entity_start);
        let cull_contents = culling.checks_vertices();
        let Some(stack) = &f.item else { continue };
        let mut canceled = false;
        game.native_render_item_in_frame(f.id, f.pos, stack, &mut canceled);
        if canceled {
            continue;
        }
        let depth = glam::DMat4::from_translation(glam::DVec3::new(0.0, 0.0, 0.4375));
        if let Some(id) = map {
            // (rotation + 2) % 4 quarter turns: Horizon's map pose with its half turn.
            let light = if variant == MANYULLYN { 240 | 240 << 8 } else { packed };
            let m = pose
                * depth
                * glam::DMat4::from_rotation_z((f64::from(f.rotation % 4 * 2) * 45.0).to_radians())
                * glam::DMat4::from_rotation_z(std::f64::consts::PI)
                * glam::DMat4::from_scale(glam::DVec3::splat(0.0078125))
                * glam::DMat4::from_translation(glam::DVec3::new(-64.0, -64.0, -1.0));
            maps.push((id, m.as_mat4(), light, cull_contents));
            continue;
        }
        let step = if more_rotations(variant) { 22.5 } else { 45.0 };
        let scale = if variant == CLEAR { 0.75 } else { 0.5 };
        let item_light = if variant == MANYULLYN { 0xFF } else { light };
        let m = pose
            * depth
            * glam::DMat4::from_rotation_z((f64::from(f.rotation) * step).to_radians())
            * glam::DMat4::from_scale(glam::DVec3::splat(scale));
        items.push((stack.clone(), f.id, m.as_mat4(), item_light, cull_contents));
    }
    let skinning = game.skinning();
    let lights = horizon_client::block_entity_render::diffuse_lights(game.dim == super::Dim::Nether);
    for (stack, id, m, light, cull) in items {
        let entity_start = out.len();
        game.mark_entity(entity_start, FRAME_KIND);
        let owner = super::item_draw::owner_at([0.0; 3], 0.0, "minecraft:item_frame");
        let state = game.resolve_item(&stack, horizon_assets::item_model::DisplayContext::Fixed, Some(&owner), id as i32);
        let light = horizon_client::block_entity_render::vertex_light(light);
        let skinned = if skinning { game.submit_item_skinned(&state, &[m], light, lights) } else { None };
        if skinned.is_none() {
            game.submit_item_world(&state, m, light, out);
        }
        if cull {
            game.cull_skinned(out, entity_start, skinned);
        }
    }
    for (id, m, light, cull) in maps {
        let entity_start = out.len();
        game.mark_entity(entity_start, FRAME_KIND);
        game.map_vertices(id, true, m, light, out);
        if cull {
            game.cull_entity_vertices(out, entity_start);
        }
    }
}

/// FancyArmorStandRenderer for `armor_stands::Game::armor_stand_vertices`: the stand's texture, full bright
/// (necrotic bone), its body hidden (a clear stand wearing or holding anything) and its main arm the left.
pub(super) fn stand_look(a: &ArmorStand) -> Option<(&'static str, bool, bool, bool)> {
    let (variant, left) = ArmorStand::hz_tc_stand(a.id)?;
    let texture = match variant {
        BAMBOO => "tconstruct:entity/armorstand/bamboo",
        BONE => "tconstruct:entity/armorstand/bone",
        NECROTIC_BONE => "tconstruct:entity/armorstand/necrotic_bone",
        _ => "tconstruct:entity/armorstand/clear",
    };
    let hidden = variant == CLEAR_STAND && a.equipment.iter().any(Option::is_some);
    Some((texture, variant == NECROTIC_BONE, hidden, left))
}

/// Enters (true) or leaves the fancy stand's second, plain drawing.
pub(super) fn stand_draw_guard(enter: bool) -> bool {
    if enter {
        ItemFrame::hz_tc_enter(IN_STAND_DRAW)
    } else {
        ItemFrame::hz_tc_leave(IN_STAND_DRAW);
        true
    }
}

/// The cancellable head of `armor_stands::Game::punch_armor_stand`: a broken fancy stand drops its own item, named as
/// the stand is (FancyArmorStandEntity.brokenByPlayer).
pub(super) fn punch_stand(game: &mut Game<'_>, i: usize) -> ControlFlow<bool> {
    let Some(a) = game.armor_stands.get(i) else { return ControlFlow::Continue(()) };
    let Some((variant, _)) = ArmorStand::hz_tc_stand(a.id) else { return ControlFlow::Continue(()) };
    if !ItemFrame::hz_tc_enter(IN_PUNCH) {
        return ControlFlow::Continue(());
    }
    let id = a.id;
    let name = a
        .custom_name
        .as_ref()
        .and_then(|_| horizon_client::entity_nbt::armor_stand_to_nbt(a, [0; 4], None).get("CustomName").cloned());
    let before = game.dropped.len();
    let hurt = game.punch_armor_stand(i);
    ItemFrame::hz_tc_leave(IN_PUNCH);
    if !game.armor_stands.iter().any(|a| a.id == id)
        && let Some(e) = game
            .dropped
            .iter_mut()
            .skip(before)
            .find(|e| &*e.stack.item == "minecraft:armor_stand" && e.stack.extra.is_none())
    {
        let mut stack = ItemStack::new(ItemFrame::hz_tc_stand_item(variant), 1);
        if let Some(name) = name {
            stack.data_mut().custom_name = Some(name);
        }
        e.stack = stack;
    }
    ControlFlow::Break(hurt)
}
