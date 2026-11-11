fn tconstruct_left_click(game: &mut crate::game::Game<'_>, pos: [i32; 3], face: [i32; 3], state: horizon_world::registry::BlockStateId, canceled: &mut bool) {
    let _ = state;
    crate::game::tconstruct::left_click(game, pos, face, canceled);
}
