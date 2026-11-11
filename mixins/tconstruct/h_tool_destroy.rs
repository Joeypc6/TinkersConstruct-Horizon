fn tconstruct_tool_destroy(game: &mut crate::game::Game<'_>, pos: [i32; 3], state: horizon_world::registry::BlockStateId) {
    crate::game::tconstruct::tool_destroy(game, pos, state);
}
