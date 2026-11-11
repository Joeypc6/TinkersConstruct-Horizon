fn tconstruct_fancy_place_stand(game: &mut crate::game::Game<'_>, hit: &crate::game::Hit, stack: &ItemStack) -> core::ops::ControlFlow<bool> {
    crate::game::tconstruct_fancy::place_stand(game, hit, stack)
}
