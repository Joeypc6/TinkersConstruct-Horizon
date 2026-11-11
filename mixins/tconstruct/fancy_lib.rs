use super::{ArmorStand, ItemFrame};
use crate::items::ItemStack;
use horizon_world::nbt::Tag;
use std::cell::Cell;
use std::collections::HashMap;
use std::sync::RwLock;
use std::sync::atomic::{AtomicBool, Ordering};

// Tinkers' Construct's fancy item frames (FancyItemFrameEntity, `tconstruct:fancy_item_frame`) and fancy armor stands
// (FancyArmorStandEntity, `tconstruct:armor_stand`) are Horizon's item frames and armor stands with a variant kept here
// by entity id: the frame's FrameType and its RotationTimer, the stand's StandType and LeftHanded. The game's side is
// game.rs's `tconstruct_fancy` module (fancy_frames.rs).

// FrameType's order (its ids) and the items TinkerGadgets.itemFrame registers for them.
const FRAME_ITEMS: [&str; 6] = [
    "tconstruct:reversed_gold_item_frame",
    "tconstruct:diamond_item_frame",
    "tconstruct:manyullyn_item_frame",
    "tconstruct:gold_item_frame",
    "tconstruct:clear_item_frame",
    "tconstruct:netherite_item_frame",
];
// FancyArmorStandEntity.StandType's order and TinkerGadgets.armorStand's items.
const STAND_ITEMS: [&str; 4] = [
    "tconstruct:bamboo_armor_stand",
    "tconstruct:bone_armor_stand",
    "tconstruct:necrotic_bone_armor_stand",
    "tconstruct:clear_armor_stand",
];
const FRAME_KIND: &str = "tconstruct:fancy_item_frame";

static FRAMES: RwLock<Option<HashMap<u32, (u8, i32)>>> = RwLock::new(None);
static ANY_FRAMES: AtomicBool = AtomicBool::new(false);
static STANDS: RwLock<Option<HashMap<u32, (u8, bool)>>> = RwLock::new(None);
static ANY_STANDS: AtomicBool = AtomicBool::new(false);
// The LAN guests' main arms (ClientInformation.mainHand), for a stand a guest places.
static GUEST_ARMS: RwLock<Option<HashMap<u128, bool>>> = RwLock::new(None);

thread_local! {
    // The hooks that call their own target again, so the inner call runs Horizon's code.
    static GUARD: Cell<u32> = const { Cell::new(0) };
    // The entity a pick (middle click) found last, for the item it gives.
    static PICKED: Cell<Option<u32>> = const { Cell::new(None) };
}

// FancyItemFrameEntity.doesRotate: the golden frames and the diamond one turn by themselves.
fn does_rotate(variant: u8) -> bool {
    matches!(variant, 0 | 1 | 3)
}

impl ItemFrame {
    /// Tinkers' Construct: the fancy frame `id`'s FrameType id and RotationTimer, None for any other frame.
    pub fn hz_tc_frame(id: u32) -> Option<(u8, i32)> {
        if !ANY_FRAMES.load(Ordering::Relaxed) {
            return None;
        }
        FRAMES.read().ok()?.as_ref()?.get(&id).copied()
    }

    /// Tinkers' Construct: makes frame `id` a fancy frame (FrameType id, RotationTimer), or a plain one again.
    pub fn hz_tc_set_frame(id: u32, info: Option<(u8, i32)>) {
        if let Ok(mut frames) = FRAMES.write() {
            let map = frames.get_or_insert_with(HashMap::new);
            match info {
                Some(info) => {
                    map.insert(id, info);
                }
                None => {
                    map.remove(&id);
                }
            }
            ANY_FRAMES.store(!map.is_empty(), Ordering::Relaxed);
        }
    }

    /// Tinkers' Construct: whether any fancy frame or stand is known (the hooks' fast way out).
    pub fn hz_tc_any() -> bool {
        ANY_FRAMES.load(Ordering::Relaxed) || ANY_STANDS.load(Ordering::Relaxed)
    }

    /// Tinkers' Construct: forgets every fancy frame and stand (the level's entities were let go).
    pub fn hz_tc_clear() {
        if let Ok(mut frames) = FRAMES.write() {
            *frames = None;
        }
        if let Ok(mut stands) = STANDS.write() {
            *stands = None;
        }
        ANY_FRAMES.store(false, Ordering::Relaxed);
        ANY_STANDS.store(false, Ordering::Relaxed);
    }

    /// Tinkers' Construct: the item of FrameType `variant` (FancyItemFrameEntity.getFrameItem).
    pub fn hz_tc_frame_item(variant: u8) -> &'static str {
        FRAME_ITEMS[usize::from(variant).min(5)]
    }

    /// Tinkers' Construct: the FrameType of a frame item, None for any other item.
    pub fn hz_tc_frame_variant_of(item: &str) -> Option<u8> {
        FRAME_ITEMS.iter().position(|i| *i == item).map(|v| v as u8)
    }

    /// Tinkers' Construct: the item of StandType `variant` (FancyArmorStandEntity.getStandItem).
    pub fn hz_tc_stand_item(variant: u8) -> &'static str {
        STAND_ITEMS[usize::from(variant).min(3)]
    }

    /// Tinkers' Construct: the StandType of a stand item, None for any other item.
    pub fn hz_tc_stand_variant_of(item: &str) -> Option<u8> {
        STAND_ITEMS.iter().position(|i| *i == item).map(|v| v as u8)
    }

    /// Tinkers' Construct: enters the hook `bit` stands for; false when it is already running on this thread.
    pub fn hz_tc_enter(bit: u32) -> bool {
        GUARD.with(|g| {
            let v = g.get();
            if v & bit != 0 {
                false
            } else {
                g.set(v | bit);
                true
            }
        })
    }

    /// Tinkers' Construct: leaves the hook `bit` stands for.
    pub fn hz_tc_leave(bit: u32) {
        GUARD.with(|g| g.set(g.get() & !bit));
    }

    /// Tinkers' Construct: the entity a pick found (or None).
    pub fn hz_tc_set_picked(id: Option<i32>) {
        PICKED.set(id.and_then(|id| u32::try_from(id).ok()));
    }

    /// Tinkers' Construct: a LAN guest's main arm (true: left), as their client last said.
    pub fn hz_tc_set_guest_arm(uuid: u128, left: bool) {
        if let Ok(mut arms) = GUEST_ARMS.write() {
            arms.get_or_insert_with(HashMap::new).insert(uuid, left);
        }
    }

    /// Tinkers' Construct: whether the LAN guest `uuid` is left-handed (false until their client said).
    pub fn hz_tc_guest_left(uuid: u128) -> bool {
        GUEST_ARMS
            .read()
            .ok()
            .and_then(|arms| arms.as_ref().and_then(|a| a.get(&uuid).copied()))
            .unwrap_or(false)
    }

    /// The cancellable head of `entity_nbt::item_frame_to_nbt`: a fancy frame saves its `Variant` and, for the
    /// turning ones, its `RotationTimer` (FancyItemFrameEntity.addAdditionalSaveData); its id is the frame's kind.
    pub fn hz_tc_frame_nbt(f: &ItemFrame, uuid: [i32; 4], raw: Option<&Tag>) -> core::ops::ControlFlow<Tag> {
        let Some((variant, timer)) = Self::hz_tc_frame(f.id) else {
            return core::ops::ControlFlow::Continue(());
        };
        if !Self::hz_tc_enter(1) {
            return core::ops::ControlFlow::Continue(());
        }
        let mut tag = crate::entity_nbt::item_frame_to_nbt(f, uuid, raw);
        Self::hz_tc_leave(1);
        if let Tag::Compound(map) = &mut tag {
            map.insert("Variant".into(), Tag::Int(i32::from(variant)));
            if does_rotate(variant) {
                map.insert("RotationTimer".into(), Tag::Int(timer));
            } else {
                map.remove(&"RotationTimer".into());
            }
        }
        core::ops::ControlFlow::Break(tag)
    }

    /// The cancellable head of `pick_item::pick`: an entity pick of a fancy frame or stand gives its own item
    /// (FancyItemFrameEntity / FancyArmorStandEntity.getPickedResult), the frame's held item unchanged.
    pub fn hz_tc_pick(
        items: &mut [Option<ItemStack>],
        selected: &mut usize,
        stack: &ItemStack,
        infinite: bool,
    ) -> core::ops::ControlFlow<bool> {
        let frame_kind = &*stack.item == FRAME_KIND;
        if !frame_kind && &*stack.item != "minecraft:armor_stand" {
            return core::ops::ControlFlow::Continue(());
        }
        let picked = PICKED.get();
        let item = match picked {
            Some(id) if frame_kind => Self::hz_tc_frame(id).map(|(v, _)| Self::hz_tc_frame_item(v)),
            Some(id) => ArmorStand::hz_tc_stand(id).map(|(v, _)| Self::hz_tc_stand_item(v)),
            None => None,
        };
        let Some(item) = item else {
            // A frame's own kind is no item: nothing to pick.
            return if frame_kind {
                core::ops::ControlFlow::Break(false)
            } else {
                core::ops::ControlFlow::Continue(())
            };
        };
        if !Self::hz_tc_enter(2) {
            return core::ops::ControlFlow::Continue(());
        }
        let own = ItemStack::new(item, 1);
        let done = crate::pick_item::pick(items, selected, &own, infinite);
        Self::hz_tc_leave(2);
        core::ops::ControlFlow::Break(done)
    }
}

impl ArmorStand {
    /// Tinkers' Construct: the fancy stand `id`'s StandType id and LeftHanded, None for any other stand.
    pub fn hz_tc_stand(id: u32) -> Option<(u8, bool)> {
        if !ANY_STANDS.load(Ordering::Relaxed) {
            return None;
        }
        STANDS.read().ok()?.as_ref()?.get(&id).copied()
    }

    /// Tinkers' Construct: makes stand `id` a fancy stand (StandType id, LeftHanded), or a plain one again.
    pub fn hz_tc_set_stand(id: u32, info: Option<(u8, bool)>) {
        if let Ok(mut stands) = STANDS.write() {
            let map = stands.get_or_insert_with(HashMap::new);
            match info {
                Some(info) => {
                    map.insert(id, info);
                }
                None => {
                    map.remove(&id);
                }
            }
            ANY_STANDS.store(!map.is_empty(), Ordering::Relaxed);
        }
    }
}

/// The cancellable head of `ItemFrame::kind`: a fancy frame is a `tconstruct:fancy_item_frame`.
pub(super) fn frame_kind(f: &ItemFrame) -> core::ops::ControlFlow<&'static str> {
    if ItemFrame::hz_tc_frame(f.id).is_some() {
        core::ops::ControlFlow::Break(FRAME_KIND)
    } else {
        core::ops::ControlFlow::Continue(())
    }
}

/// The cancellable head of `ItemFrame::item_stack_with_data`: a fancy frame drops its own item
/// (FancyItemFrameEntity.getFrameItemStack), named as the frame is.
pub(super) fn frame_stack(f: &ItemFrame) -> core::ops::ControlFlow<ItemStack> {
    let Some((variant, _)) = ItemFrame::hz_tc_frame(f.id) else {
        return core::ops::ControlFlow::Continue(());
    };
    let mut stack = ItemStack::new(ItemFrame::hz_tc_frame_item(variant), 1);
    if let Some(name) = &f.custom_name {
        stack.data_mut().custom_name = Some(name.clone());
    }
    core::ops::ControlFlow::Break(stack)
}

/// The cancellable head of `ArmorStand::environment_tick`: a fancy stand is fire immune
/// (FancyArmorStandEntity.fireImmune): fire, lava and burning take no health and it shows no fire.
pub(super) fn stand_environment(
    a: &mut ArmorStand,
    world: &crate::world::World,
    facts: &crate::blocks::BlockFacts,
    registry: &horizon_world::registry::BlockRegistry,
) -> core::ops::ControlFlow<bool> {
    if ArmorStand::hz_tc_stand(a.id).is_none() || !ItemFrame::hz_tc_enter(4) {
        return core::ops::ControlFlow::Continue(());
    }
    let health = a.health;
    let _burnt = a.environment_tick(world, facts, registry);
    ItemFrame::hz_tc_leave(4);
    a.health = health;
    a.fire_ticks = 0;
    core::ops::ControlFlow::Break(a.health > 0.5)
}
