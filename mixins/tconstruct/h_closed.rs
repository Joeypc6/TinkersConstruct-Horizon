fn tconstruct_closed(game: &mut crate::game::Game<'_>, player: u128, dimension: &str, pos: Option<[i32; 3]>) {
    crate::game::tconstruct::container_closed(game, dimension, player, pos);
}
