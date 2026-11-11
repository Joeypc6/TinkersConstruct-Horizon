fn jei_window_scrolled(game: &crate::game::Game<'_>, scroll: [f64; 2], canceled: &mut bool) {
    tconstruct_optional::if_kit_jei!("tconstruct", {
    if game.player.is_none() || *canceled {
        return;
    }
    crate::game::hz_kit_window_tconstruct::scroll(scroll[1], canceled);
} else { let _ = (game, scroll, canceled); () })
}
