fn kit_guide_released_tconstruct(game: &crate::game::Game<'_>, canceled: &mut bool) {
    tconstruct_optional::if_kit!("tconstruct", {
    crate::game::hz_kit_guide_tconstruct::release(game, canceled);
} else { let _ = (game, canceled); () })
}
