fn tconstruct_gadget_dispense(game: &mut crate::game::Game<'_>, pos: [i32; 3], facing: horizon_core::geometry::Direction, stack: &horizon_client::items::ItemStack, answer: &mut Option<horizon_client::mod_api::NativeDispensed>) {
    crate::game::tconstruct::gadget_dispense(game, pos, facing, stack, answer);
}
