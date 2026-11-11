fn tconstruct_armor_net(game: &mut crate::game::Game<'_>, player: u128, channel: &str, data: &[u8]) {
    crate::game::tconstruct::armor_net(game, player, channel, data);
}
