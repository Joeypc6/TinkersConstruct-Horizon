fn tconstruct_use_item(game: &mut crate::game::Game<'_>, stack: &horizon_client::items::ItemStack, claimed: &mut bool) {
    crate::game::tconstruct::ranged_use_item(game, stack, claimed);
}
