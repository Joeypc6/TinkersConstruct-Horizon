fn kit_guide_char_tconstruct(game: &crate::game::Game<'_>, c: char, canceled: &mut bool) {
    tconstruct_optional::if_kit!("tconstruct", {
    let _ = c;
    if game.player.is_some() && crate::game::hz_kit_guide_tconstruct::is_open() {
        *canceled = true;
    }
} else { let _ = (game, c, canceled); () })
}
