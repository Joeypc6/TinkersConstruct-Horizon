fn tconstruct_gadget_shape(level: &crate::game::GameLevel<'_>, ticks: &mut horizon_world::level::Ticks, pos: horizon_core::position::BlockPos, state: horizon_world::registry::BlockStateId, direction: horizon_core::geometry::Direction, neighbour_pos: horizon_core::position::BlockPos, neighbour: horizon_world::registry::BlockStateId, new: &mut Option<horizon_world::registry::BlockStateId>) {
    crate::game::tconstruct::gadget_update_shape(level, ticks, pos, state, direction, neighbour_pos, neighbour, new);
}
