fn tconstruct_efln_positions(game: &mut crate::game::Game<'_>, center: [f64; 3], radius: f32) -> core::ops::ControlFlow<Vec<[i32; 3]>> {
    crate::game::tconstruct::efln_positions(game, center, radius)
}
