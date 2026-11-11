fn tconstruct_reflect(game: &mut crate::game::Game<'_>, p: &horizon_client::projectiles::Projectile, hit: &horizon_client::projectiles::Hit) -> core::ops::ControlFlow<Result<()>> {
    if crate::game::tconstruct::reflect_hit(game, p, hit) { core::ops::ControlFlow::Break(Ok(())) } else { core::ops::ControlFlow::Continue(()) }
}
