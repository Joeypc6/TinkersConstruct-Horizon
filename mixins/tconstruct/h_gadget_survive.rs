fn tconstruct_gadget_survive(level: &crate::game::GameLevel<'_>, pos: horizon_core::position::BlockPos, state: horizon_world::registry::BlockStateId, survives: &mut Option<bool>) {
    crate::game::tconstruct::gadget_can_survive(level, pos, state, survives);
}
