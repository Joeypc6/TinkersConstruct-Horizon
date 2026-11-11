fn tconstruct_custom_tanks(game: &crate::game::Game<'_>, pos: [i32; 3], side: Option<horizon_core::geometry::Direction>, out: &mut Option<Vec<horizon_client::mod_api::NativeFluidTankView>>) {
    crate::game::tconstruct::custom_fluid_tanks(game, pos, side, out);
}
