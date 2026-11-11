fn tconstruct_fancy_blast(game: &mut crate::game::Game<'_>, blast: [f64; 3], diameter: f64, interaction: crate::game::explosion::BlockInteraction) -> core::ops::ControlFlow<()> {
    crate::game::tconstruct_fancy::explosion(game, blast, diameter, interaction)
}
