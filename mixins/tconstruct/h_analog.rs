fn tconstruct_analog(level: &crate::game::GameLevel<'_>, pos: horizon_core::position::BlockPos, output: &mut i32) {
    crate::game::tconstruct::analog_output(level, [pos.x, pos.y, pos.z], output);
}
