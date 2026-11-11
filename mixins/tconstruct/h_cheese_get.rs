fn tconstruct_cheese_get(properties: &crate::movement_properties::BoundMovementProperties, state: crate::registry::BlockStateId) -> core::ops::ControlFlow<io::Result<MovementBlock>> {
    crate::movement_properties::tc_cheese::get(properties, state)
}
