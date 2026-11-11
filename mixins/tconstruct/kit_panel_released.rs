fn jei_window_released(screen: &crate::game::native_hooks::NativeScreenView<'_>) {
    tconstruct_optional::if_kit_jei!("tconstruct", {
    crate::game::hz_kit_window_tconstruct::release(screen.mouse);
} else { let _ = screen; () })
}
