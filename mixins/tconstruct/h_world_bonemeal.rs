fn tconstruct_world_bonemeal(level: &mut crate::game::GameLevel<'_>, ticks: &mut horizon_world::level::Ticks, pos: horizon_core::position::BlockPos, state: horizon_world::registry::BlockStateId) {
    crate::game::tconstruct::world_bonemeal(level, ticks, pos, state);
}
