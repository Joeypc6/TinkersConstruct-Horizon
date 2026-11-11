fn tconstruct_screen_char(game: &crate::game::Game<'_>, screen: &crate::game::native_hooks::NativeScreenView<'_>, c: char, canceled: &mut bool) {
    crate::game::tconstruct::screen_char(game, screen, c, canceled);
}
