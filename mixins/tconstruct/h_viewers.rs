fn tconstruct_viewers(game: &mut crate::game::Game<'_>, dimension: &str, pos: [i32; 3], viewers: u32) {
    crate::game::tconstruct::container_viewers(game, dimension, pos, viewers);
}
