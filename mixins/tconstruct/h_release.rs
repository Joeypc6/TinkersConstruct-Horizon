fn tconstruct_release(game: &mut crate::game::Game<'_>, stack: &horizon_client::items::ItemStack, entity: Option<i32>, time_left: i32) {
    crate::game::tconstruct::ranged_release(game, stack, entity, time_left);
}
