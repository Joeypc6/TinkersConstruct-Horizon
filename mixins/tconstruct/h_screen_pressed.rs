fn tconstruct_screen_pressed(game: &crate::game::Game<'_>, screen: &crate::game::native_hooks::NativeScreenView<'_>, canceled: &mut bool) {
    crate::game::tconstruct::screen_pressed(game, screen, canceled);
}
