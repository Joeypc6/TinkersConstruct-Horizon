fn jei_panel_tint(game: &Game<'_>, batch: &mut HudBatch) {
    tconstruct_optional::if_kit_jei!("tconstruct", {
    crate::game::hz_kit_window_tconstruct::tint(game, batch);
} else { let _ = (game, batch); () })
}
