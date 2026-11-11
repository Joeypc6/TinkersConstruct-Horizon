fn tconstruct_update_tag(entity: &horizon_client::containers::ModBlockEntity, tag: &mut Option<horizon_world::nbt::Compound>) {
    crate::game::tconstruct::update_tag(entity, tag);
}
