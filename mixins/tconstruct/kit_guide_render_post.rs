fn kit_guide_render_post_tconstruct(game: &crate::game::Game<'_>, batch: &mut horizon_client::hud::HudBatch, screen: &crate::game::native_hooks::NativeScreenView<'_>) {
    tconstruct_optional::if_kit!("tconstruct", {
    if game.player.is_none() {
        return;
    }
    crate::game::hz_kit_guide_tconstruct::screen_frame(screen.id, screen.menu);
    crate::game::hz_kit_guide_tconstruct::draw(game, batch, screen.mouse);
} else { let _ = (game, batch, screen); () })
}
