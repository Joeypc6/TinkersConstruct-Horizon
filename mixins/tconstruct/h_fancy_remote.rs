fn tconstruct_fancy_remote(game: &mut crate::game::Game<'_>, id: i32, values: &[(u8, i32, Value)]) -> core::ops::ControlFlow<()> {
    crate::game::tconstruct_fancy::remote_data(game, id, values)
}
