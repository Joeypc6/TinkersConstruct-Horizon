fn tconstruct_fancy_dispense(game: &mut crate::game::Game<'_>, pos: Pos, facing: Direction, stack: &ItemStack) -> core::ops::ControlFlow<Result<Option<ItemStack>>> {
    crate::game::tconstruct_fancy::dispense(game, pos, facing, stack)
}
