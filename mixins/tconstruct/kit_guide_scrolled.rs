fn kit_guide_scrolled_tconstruct(game: &crate::game::Game<'_>, scroll: [f64; 2], canceled: &mut bool) {
    tconstruct_optional::if_kit!("tconstruct", {
    if game.player.is_some() {
        crate::game::hz_kit_guide_tconstruct::scroll(scroll[1], canceled);
    }
} else { let _ = (game, scroll, canceled); () })
}
