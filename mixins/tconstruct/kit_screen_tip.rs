fn jei_screen_tip(game: &crate::game::Game<'_>) -> core::ops::ControlFlow<()> {
    tconstruct_optional::if_kit_jei!("tconstruct", {
    if crate::game::hz_kit_window_tconstruct::defer_tooltip(game) {
        return core::ops::ControlFlow::Break(());
    }
} else { let _ = game; () });
    core::ops::ControlFlow::Continue(())
}
