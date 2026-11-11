fn tconstruct_fancy_place_frame(game: &mut crate::game::Game<'_>, hit: &crate::game::Hit, stack: &horizon_client::items::ItemStack) -> core::ops::ControlFlow<bool> {
    crate::game::tconstruct_fancy::place_frame(game, hit, stack)
}
