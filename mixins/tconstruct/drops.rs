fn tconstruct_drops(game: &mut crate::game::Game<'_>, pos: [i32; 3], state: BlockStateId, drops: &mut Vec<ItemStack>) {
    let block = game.res.facts().get(state).name.to_string();
    crate::game::tconstruct::block_drops(game, pos, &block, drops);
}
