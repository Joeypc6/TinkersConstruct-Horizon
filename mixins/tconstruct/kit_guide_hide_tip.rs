// `native_tooltip_render_pre`: while the guide is open, the screen behind it shows no tooltip over its pages (the
// guide draws its own items' tooltips itself).
fn kit_guide_hide_tip_tconstruct(cancel: &mut bool) {
    tconstruct_optional::if_kit!("tconstruct", {
    if crate::game::hz_kit_guide_tconstruct::is_open() {
        *cancel = true;
    }
} else { let _ = cancel; () })
}
