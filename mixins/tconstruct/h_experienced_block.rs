fn tconstruct_experienced_block(value: u32, game: &crate::game::Game<'_>) -> u32 {
    crate::game::tc_effects::block_experience(value, game)
}
