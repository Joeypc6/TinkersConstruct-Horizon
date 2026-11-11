fn tconstruct_knockback(attacker_main: Option<&horizon_client::items::ItemStack>, strength: &mut f64) {
    crate::game::tconstruct::living_knockback(attacker_main, strength);
}
