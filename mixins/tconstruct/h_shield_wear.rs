fn tconstruct_shield_wear(game: &mut crate::game::Game<'_>, stack: &horizon_client::items::ItemStack, amount: u32) -> core::ops::ControlFlow<u32> {
    crate::game::tconstruct::shield_wear(game, stack, amount)
}
