fn kit_guide_dragged_tconstruct(delta: [f32; 2], canceled: &mut bool) {
    tconstruct_optional::if_kit!("tconstruct", {
    crate::game::hz_kit_guide_tconstruct::drag(delta, canceled);
} else { let _ = (delta, canceled); () })
}
