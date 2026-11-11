fn tconstruct_ricochet_end(canceled: bool, knock: &mut horizon_client::health::Knock) -> bool {
    crate::game::tc_effects::knockback_end(canceled, knock)
}
