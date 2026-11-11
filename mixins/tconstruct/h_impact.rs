fn tconstruct_impact(game: &mut crate::game::Game<'_>, projectile: u32, entity: Option<u32>, canceled: &mut bool) {
    crate::game::tconstruct::ranged_impact(game, projectile, entity, canceled);
}
