fn tconstruct_animate(engine: &mut ParticleEngine, ctx: &AnimateContext<'_>, player: [i32; 3]) {
    tconstruct_particles::animate(engine, ctx, player);
}
