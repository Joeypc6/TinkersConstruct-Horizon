// Tinkers' Experienced and Ricochet effects, server side. In Java they are attribute modifiers (TinkerEffects:
// `tconstruct:player.experience_multiplier` MULTIPLY_BASE 0.25 a level, `tconstruct:generic.knockback_multiplier`
// MULTIPLY_BASE 0.5 a level) and ModifierEvents reads those attributes: onExperienceDrop (a dying entity's experience),
// beforeBlockBreak (a broken block's experience) and onKnockback (LivingKnockBackEvent). Horizon has no mod attributes:
// the values are worked out here from the effect and its amplifier, as AttributeInstance.calculateValue does.
use super::Game;
use horizon_client::health::{Hurting, Knock};
use horizon_client::mobs::Mob;
use std::cell::Cell;

const EXPERIENCED: &str = "tconstruct:experienced";
const RICOCHET: &str = "tconstruct:ricochet";

thread_local! {
    /// The Ricochet multiplier of the knockback being run, from its start to its end (1.0: none).
    static KNOCKBACK: Cell<f64> = const { Cell::new(1.0) };
    /// The player `knock_back_player` is about to push (entity id) and that player's Ricochet multiplier.
    static PLAYER: Cell<(i32, f64)> = const { Cell::new((0, 1.0)) };
}

/// A Tinkers' multiplier attribute (AttributeDeferredRegister.registerMultiplier: base 1.0, 0 to 100) with one effect's
/// MULTIPLY_BASE modifier: `amount * (amplifier + 1)` (MobEffect.getAttributeModifierValue), `base + base * that`
/// (AttributeInstance.calculateValue), clamped (RangedAttribute.sanitizeValue). No effect: the base.
fn attribute(amount: f64, amplifier: Option<i32>) -> f64 {
    match amplifier {
        None => 1.0,
        Some(a) => (1.0 + 1.0 * (amount * (f64::from(a) + 1.0))).clamp(0.0, 100.0),
    }
}

/// A mob's amplifier of the effect `id`, if it has it.
fn mob_amplifier(m: &Mob, id: &str) -> Option<i32> {
    m.extra.effects.iter().find(|e| e.0 == id).map(|e| e.2)
}

/// The acting player's amplifier of the effect `id`, if they have it.
fn player_amplifier(game: &Game<'_>, id: &str) -> Option<i32> {
    game.potions.effects.list.iter().find(|e| e.id == id).map(|e| e.amplifier)
}

/// `Game::knock_back_player`'s start: the player about to be pushed and their Ricochet multiplier, for the knockback
/// hook (which names the player by entity id only).
pub(crate) fn knocked_player(game: &Game<'_>) {
    let Some(p) = game.player.as_ref() else { return };
    let k = attribute(0.5, player_amplifier(game, RICOCHET));
    PLAYER.with(|c| c.set((p.entity_id, k)));
}

/// LivingEntity.knockback's start (LivingKnockBackEvent): the pushed entity's knockback multiplier attribute. Armor
/// stands take no effects (ArmorStand.isAffectedByPotions); the dragon keeps none here.
pub(crate) fn knockback_start(pushed: &Hurting<'_>) {
    let player = PLAYER.with(|c| c.replace((0, 1.0)));
    let k = match pushed {
        Hurting::Mob(m, _) => attribute(0.5, mob_amplifier(m, RICOCHET)),
        Hurting::Player(id, _) if *id == player.0 => player.1,
        _ => 1.0,
    };
    KNOCKBACK.with(|c| c.set(k));
}

/// ModifierEvents.onKnockback, after every other change to the push (a Tinkers' tool's knockback is part of the
/// strength Java passes to `knockback`): `event.setStrength((float)(event.getStrength() * knockback))` when the
/// multiplier isn't 1. The event's strength is a float.
pub(crate) fn knockback_end(canceled: bool, knock: &mut Knock) -> bool {
    let k = KNOCKBACK.with(|c| c.replace(1.0));
    if !canceled && k != 1.0 {
        knock.strength = f64::from((f64::from(knock.strength as f32) * k) as f32);
    }
    canceled
}

/// ModifierEvents.onExperienceDrop's multiplier for the mob `m` about to drop its loot: `1 + ` the dying entity's own
/// Experienced amplifier, then with an attacking player `+` their experience multiplier attribute (1.0 without the
/// effect: Java gives every player's kill this base too). The armor's experience stat and a Tinkers' tool's or
/// projectile's experience bonus have no port yet (0).
pub(crate) fn death_experience(game: &Game<'_>, m: &Mob, player: Option<u128>) {
    let mut k = f64::from(1i32.wrapping_add(mob_amplifier(m, EXPERIENCED).unwrap_or(0)));
    if let Some(uuid) = player {
        let amplifier = game
            .native_effects(uuid)
            .and_then(|list| list.into_iter().find(|e| e.id == EXPERIENCED))
            .map(|e| i32::from(e.amplifier));
        k += attribute(0.25, amplifier);
    }
    horizon_client::mobs::drops::tc_effects_orbs::set_multiplier(k);
}

/// ModifierEvents.beforeBlockBreak: `(int)(exp * bonus)`, the bonus being the breaking player's experience multiplier
/// attribute (1.0 without the effect; a Tinkers' tool's Experienced levels and the armor's stat have no port yet).
pub(crate) fn block_experience(value: u32, game: &Game<'_>) -> u32 {
    if value == 0 {
        return 0;
    }
    match player_amplifier(game, EXPERIENCED) {
        None => value,
        amplifier => (f64::from(value) * attribute(0.25, amplifier)) as u32,
    }
}
