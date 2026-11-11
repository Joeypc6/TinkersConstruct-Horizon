fn tconstruct_fancy_analog(level: &crate::game::GameLevel<'_>, pos: BlockPos, facing: Direction) -> core::ops::ControlFlow<Option<i32>> {
    crate::game::tconstruct_fancy::analog(level, pos, facing)
}
