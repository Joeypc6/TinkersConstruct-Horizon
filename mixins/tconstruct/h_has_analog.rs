fn tconstruct_has_analog(level: &crate::game::GameLevel<'_>, state: horizon_world::registry::BlockStateId, output: &mut bool) {
    crate::game::tconstruct::has_analog_output(level, state, output);
}
