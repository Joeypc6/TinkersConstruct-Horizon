fn tconstruct_accepts(game: &crate::game::Game<'_>, pos: [i32; 3], entity: &horizon_client::containers::ModBlockEntity, slot: usize, stack: &horizon_client::items::ItemStack, cancel: &mut bool) {
    crate::game::tconstruct::container_accepts(game, pos, entity, slot, stack, cancel);
}
