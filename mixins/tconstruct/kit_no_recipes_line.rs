// `native_chat`: holds back JEI's "No recipes for" while the window shows more than JEI's own recipes.
fn jei_no_recipes_line(text: &str) -> core::ops::ControlFlow<()> {
    tconstruct_optional::if_kit_jei!("tconstruct", {
    if crate::game::hz_kit_layer_tconstruct::chat_allowed(text) {
        core::ops::ControlFlow::Continue(())
    } else {
        core::ops::ControlFlow::Break(())
    }
} else { let _ = text; core::ops::ControlFlow::Continue(()) })
}
