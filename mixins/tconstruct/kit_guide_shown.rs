fn kit_guide_shown_tconstruct(stack: &ItemStack) {
    tconstruct_optional::if_kit!("tconstruct", {
    crate::game::hz_kit_guide_tconstruct::hovered(&stack.item);
} else { let _ = stack; () })
}
