fn kit_guide_frame_tconstruct(game: &mut crate::game::Game<'_>) {
    tconstruct_optional::if_kit!("tconstruct", {
    if game.player.is_some() {
        crate::game::hz_kit_guide_tconstruct::frame_hook(game);
    }
} else { let _ = game; () })
}
