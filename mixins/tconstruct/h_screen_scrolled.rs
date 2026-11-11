fn tconstruct_screen_scrolled(game: &crate::game::Game<'_>, screen: &crate::game::native_hooks::NativeScreenView<'_>, scroll: [f64; 2], modifiers: u32, canceled: &mut bool) {
    let _ = modifiers;
    crate::game::tconstruct::screen_scrolled(game, screen, scroll, canceled);
}
