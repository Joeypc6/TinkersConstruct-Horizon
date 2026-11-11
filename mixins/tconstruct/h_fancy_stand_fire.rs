fn tconstruct_fancy_stand_fire(a: &mut ArmorStand, world: &World, facts: &BlockFacts, registry: &horizon_world::registry::BlockRegistry) -> core::ops::ControlFlow<bool> {
    tconstruct_fancy::stand_environment(a, world, facts, registry)
}
