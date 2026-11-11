fn tconstruct_be_removed(level: &mut crate::game::GameLevel<'_>, pos: horizon_core::position::BlockPos) {
    crate::game::tconstruct::block_entity_removed(level, [pos.x, pos.y, pos.z]);
}
