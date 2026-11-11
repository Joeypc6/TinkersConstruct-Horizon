fn tconstruct_screen_released(game: &crate::game::Game<'_>, screen: &crate::game::native_hooks::NativeScreenView<'_>, canceled: &mut bool) {
    crate::game::tconstruct::screen_released(game, screen, canceled);
}
