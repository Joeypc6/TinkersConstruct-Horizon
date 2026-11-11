fn tconstruct_interact_entity(game: &mut crate::game::Game<'_>, entity: i32, kind: &str, stack: Option<&horizon_client::items::ItemStack>, claimed: &mut bool) {
    let _ = kind;
    crate::game::tconstruct::interact_entity(game, entity, stack, claimed);
}
