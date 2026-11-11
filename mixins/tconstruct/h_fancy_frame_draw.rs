fn tconstruct_fancy_frame_draw(game: &mut crate::game::Game<'_>, camera: glam::DVec3, out: &mut Vec<horizon_client::mesher::Vertex>) -> core::ops::ControlFlow<()> {
    crate::game::tconstruct_fancy::frame_geometry(game, camera, out)
}
