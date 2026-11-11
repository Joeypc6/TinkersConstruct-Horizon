fn tconstruct_render_bounds(game: &crate::game::Game<'_>, pos: [i32; 3], block: &str, state: horizon_world::registry::BlockStateId, entity: &horizon_client::containers::ModBlockEntity, bounds: &mut [f32; 6]) {
    let _ = (game, block, state);
    crate::game::tconstruct::render_bounds(pos, entity, bounds);
}
