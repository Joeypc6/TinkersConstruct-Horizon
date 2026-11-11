fn tconstruct_sweep_damage(game: &mut crate::game::Game<'_>, target: horizon_core::geometry::Aabb, spared: &crate::game::mace::Spared, scale: f32) -> core::ops::ControlFlow<()> {
    let _ = scale;
    crate::game::tconstruct::sweep_damage(game, target, spared)
}
