fn tconstruct_consume_effect(game: &mut crate::game::Game<'_>, kind: &str, data: &serde_json::Value) {
    crate::game::tconstruct::consume_effect(game, kind, data);
}
