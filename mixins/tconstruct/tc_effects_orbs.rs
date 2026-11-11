// Tinkers' Experienced effect on a mob's experience orbs (ModifierEvents.onExperienceDrop, LivingExperienceDropEvent):
// the game works the multiplier out (crate::game::tc_effects::death_experience) just before `die`, which takes it.
use std::cell::Cell;

thread_local! {
    /// The multiplier for the next `die` on this thread (1.0: none).
    static MULTIPLIER: Cell<f64> = const { Cell::new(1.0) };
}

/// Sets the experience multiplier the next `die` takes.
pub fn set_multiplier(k: f64) {
    MULTIPLIER.with(|c| c.set(k));
}

/// `die`'s drops with the multiplier taken: `(int)(experience * multiplier)` of the orbs' total, split again as
/// `ExperienceOrb.award` splits it, where the orbs were.
pub(super) fn apply(value: (Vec<super::Drop>, bool)) -> (Vec<super::Drop>, bool) {
    let k = MULTIPLIER.with(|c| c.replace(1.0));
    let (mut drops, skulls) = value;
    if k == 1.0 {
        return (drops, skulls);
    }
    let Some(at) = drops.iter().position(|d| matches!(d, super::Drop::Orb(_))) else {
        return (drops, skulls);
    };
    let total: i64 = drops.iter().map(|d| if let super::Drop::Orb(v) = d { i64::from(*v) } else { 0 }).sum();
    drops.retain(|d| !matches!(d, super::Drop::Orb(_)));
    let mut amount = (total as f64 * k) as i32;
    let mut orbs = Vec::new();
    while amount > 0 {
        let v = super::orb_value(amount);
        amount -= v;
        orbs.push(super::Drop::Orb(v));
    }
    drops.splice(at..at, orbs);
    (drops, skulls)
}
