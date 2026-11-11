fn tconstruct_be(block: &str, entity: &mut Option<(String, horizon_world::nbt::Compound)>) {
    crate::game::tconstruct::block_entity(block, entity);
}
