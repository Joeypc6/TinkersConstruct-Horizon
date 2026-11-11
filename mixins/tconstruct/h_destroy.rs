fn tconstruct_destroy(game: &mut crate::game::Game<'_>, pos: [i32; 3]) {
    crate::game::tconstruct::destroyed(game, pos);
}
