fn tconstruct_use_tick(game: &mut crate::game::Game<'_>, stack: &horizon_client::items::ItemStack, entity: Option<i32>, remaining: i32) {
    crate::game::tconstruct::ranged_use_tick(game, stack, entity, remaining);
}
