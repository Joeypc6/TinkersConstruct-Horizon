fn tconstruct_click_pre(game: &mut crate::game::Game<'_>, host: &mut crate::game::lan::LanHost, conn: u32, p: &horizon_protocol::packets::play::ContainerClick) {
    crate::game::tconstruct::station_click(game, host, conn, p);
}
