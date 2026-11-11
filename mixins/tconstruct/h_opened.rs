fn tconstruct_opened(player: u128, dimension: &str, pos: Option<[i32; 3]>) {
    crate::game::tconstruct::container_opened(dimension, player, pos, true);
}
