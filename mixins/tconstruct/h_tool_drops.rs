fn tconstruct_tool_drops(game: &mut crate::game::Game<'_>, pos: [i32; 3], state: horizon_world::registry::BlockStateId, player: Option<u128>, tool: Option<&horizon_client::items::ItemStack>, drops: &mut Vec<horizon_client::items::ItemStack>) {
    crate::game::tconstruct::tool_drops(game, pos, state, player, tool, drops);
}
