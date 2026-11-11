fn tconstruct_be_fluids(block: &str, fluids: &mut Option<horizon_client::containers::ModFluidTanks>) {
    crate::game::tconstruct::block_entity_fluids(block, fluids);
}
