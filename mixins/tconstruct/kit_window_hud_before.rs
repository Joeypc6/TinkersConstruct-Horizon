fn jei_hud_before(game: &mut crate::game::Game<'_>) {
    tconstruct_optional::if_kit_jei!("tconstruct", {
    crate::game::hz_kit_window_tconstruct::hud_before(game);
} else { let _ = game; () })
}
