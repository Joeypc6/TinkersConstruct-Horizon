fn tconstruct_gadget_impact(game: &mut crate::game::Game<'_>, dimension: &str, projectile: u32, kind: &str, entity: Option<u32>, block: [i32; 3], face: [i32; 3], at: [f64; 3], canceled: &mut bool) {
    crate::game::tconstruct::gadget_impact(game, dimension, projectile, kind, entity, block, face, at, canceled);
}
