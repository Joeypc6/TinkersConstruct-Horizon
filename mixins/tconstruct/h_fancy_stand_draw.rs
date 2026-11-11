fn tconstruct_fancy_stand_draw(game: &crate::game::Game<'_>, a: &ArmorStand, base: glam::Mat4, packed: u32, skin: &mut Option<&mut horizon_client::mobs::skin::Skin>, out: &mut Vec<Vertex>) -> core::ops::ControlFlow<()> {
    // FancyArmorStandRenderer: the stand's own texture (full bright for necrotic bone), its body hidden while a clear
    // stand wears or holds anything, a left-handed stand's hands swapped; then Horizon's items, armour and wings.
    let Some((texture, full_bright, hidden, left)) = crate::game::tconstruct_fancy::stand_look(a) else {
        return core::ops::ControlFlow::Continue(());
    };
    if !crate::game::tconstruct_fancy::stand_draw_guard(true) {
        return core::ops::ControlFlow::Continue(());
    }
    let packed = if full_bright { horizon_client::mobs::render::FULL_BRIGHT } else { packed };
    let model = if a.small { &game.armor_stand_assets.small } else { &game.armor_stand_assets.main };
    let uv = game.gui.atlas.sprites.get(texture).map(|r| [r.u0, r.v0, r.u1, r.v1]);
    if !a.invisible && !hidden && let (Some(model), Some(uv)) = (model, uv) {
        let mut poses = Poses::new(model);
        apply_pose(&mut poses, &a.pose);
        for (name, shown) in [("left_arm", a.show_arms), ("right_arm", a.show_arms), ("base_plate", !a.no_base_plate)] {
            if !shown && poses.has(name) {
                let pose = poses.get(name);
                pose[6] = 0.0;
                pose[7] = 0.0;
                pose[8] = 0.0;
            }
        }
        horizon_client::mobs::render::put(&mut *skin, model, base, &poses, uv, 0.0, 0xFFFF_FFFF, packed, 0, out);
    }
    let mut plain = a.clone();
    plain.invisible = true;
    if left {
        plain.equipment.swap(0, 1);
    }
    game.armor_stand_vertices(&plain, base, packed, skin.as_deref_mut(), out);
    crate::game::tconstruct_fancy::stand_draw_guard(false);
    core::ops::ControlFlow::Break(())
}
