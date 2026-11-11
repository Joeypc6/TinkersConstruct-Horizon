fn tconstruct_rod_use(game: &mut crate::game::Game<'_>, stack: &horizon_client::items::ItemStack) -> core::ops::ControlFlow<bool> {
    crate::game::tconstruct::rod_use(game, stack)
}
