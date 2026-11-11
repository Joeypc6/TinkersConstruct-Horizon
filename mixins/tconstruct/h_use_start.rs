fn tconstruct_use_start(game: &mut crate::game::Game<'_>, stack: &horizon_client::items::ItemStack, entity: Option<i32>, canceled: &mut bool) {
    crate::game::tconstruct::ranged_use_start(game, stack, entity, canceled);
}
