fn tconstruct_sweep_position(game: &mut crate::game::Game<'_>, scale: f32, crit: bool) -> core::ops::ControlFlow<Option<[f64; 3]>> {
    crate::game::tconstruct::sweep_position(game, scale, crit)
}
