fn tconstruct_fancy_lan(game: &mut crate::game::Game<'_>, hub: &mut Hub, out: &mut States, drain_minecart_steps: bool, after: u32) -> core::ops::ControlFlow<()> {
    crate::game::tconstruct_fancy::lan_states(game, hub, out, drain_minecart_steps, after)
}
