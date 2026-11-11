fn tconstruct_experienced_death(game: &crate::game::Game<'_>, m: &horizon_client::mobs::Mob, player_uuid: Option<u128>) {
    crate::game::tc_effects::death_experience(game, m, player_uuid);
}
