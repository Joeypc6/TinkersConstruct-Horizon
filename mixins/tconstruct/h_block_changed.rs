fn tconstruct_block_changed(level: &crate::game::GameLevel<'_>, dimension: horizon_world::level::Dimension, pos: horizon_core::position::BlockPos, old: horizon_world::registry::BlockStateId, new: horizon_world::registry::BlockStateId) {
    crate::game::tconstruct::block_changed(level, dimension, pos, old, new);
}
