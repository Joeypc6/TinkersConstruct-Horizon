fn ae2_jei_event(
    game: &mut crate::game::Game<'_>,
    mod_id: &str,
    event: &crate::game::native_hooks::NativePanelEvent,
) {
    tconstruct_optional::if_kit_jei!("tconstruct", {
    crate::game::hz_kit_layer_tconstruct::event(game, mod_id, event);
} else { let _ = (game, mod_id, event); () })
}
