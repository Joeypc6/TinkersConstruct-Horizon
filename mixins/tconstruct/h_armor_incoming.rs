fn tconstruct_armor_incoming(entity: i32, kind: &str, damage_type: &str, causing: i32, direct: i32, amount: &mut f32, canceled: &mut bool) {
    crate::game::tconstruct::armor_incoming_damage(entity, kind, damage_type, causing, direct, amount, canceled);
}
