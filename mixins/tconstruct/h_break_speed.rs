fn tconstruct_break_speed(game: &crate::game::Game<'_>, pos: [i32; 3], state: horizon_world::registry::BlockStateId, speed: &mut f32) {
    crate::game::tconstruct::break_speed(game, pos, state, speed);
}
