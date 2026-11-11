fn tconstruct_shield_blocked(game: &mut crate::game::Game<'_>, outcome: horizon_client::health::BlockOutcome) {
    crate::game::tconstruct::shield_blocked(game, outcome);
}
