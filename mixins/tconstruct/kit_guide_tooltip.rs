fn kit_guide_tooltip_tconstruct(stack: &horizon_client::items::ItemStack, lines: &mut Vec<(horizon_client::text::Text, u32)>) {
    tconstruct_optional::if_kit!("tconstruct", {
    crate::game::hz_kit_guide_tconstruct::tooltip(stack, lines);
} else { let _ = (stack, lines); () })
}
