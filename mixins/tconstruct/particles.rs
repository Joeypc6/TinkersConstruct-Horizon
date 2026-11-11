use super::{AnimateContext, ParticleEngine, ParticleOptions, T};
use horizon_core::random::RandomSource;
use horizon_world::nbt::{JavaString, Tag};
use horizon_world::registry::BlockStateId;

pub(super) fn animate(engine: &mut ParticleEngine, ctx: &AnimateContext<'_>, center: [i32; 3]) {
    for _ in 0..667 {
        sample(engine, ctx, center, 16);
        sample(engine, ctx, center, 32);
    }
}

// ClientLevel.doAnimateTick's choice of block.
fn sample(engine: &mut ParticleEngine, ctx: &AnimateContext<'_>, center: [i32; 3], r: i32) {
    let random = engine.random();
    let x = center[0] + super::next_int(random, r) - super::next_int(random, r);
    let y = center[1] + super::next_int(random, r) - super::next_int(random, r);
    let z = center[2] + super::next_int(random, r) - super::next_int(random, r);
    if !ctx.world.loaded(x, z) {
        return;
    }
    let state = ctx.state([x, y, z]);
    let name = ctx.facts.get(state).name.clone();
    if let Some(path) = name.strip_prefix("tconstruct:") {
        block(engine, ctx, state, path, [x, y, z]);
    }
}

fn property(ctx: &AnimateContext<'_>, state: BlockStateId, key: &str) -> Option<String> {
    ctx.registry.state(state).and_then(|s| s.properties.get(key).cloned())
}

// Direction.getStepX / Y / Z of a facing.
fn step(facing: &str) -> [f64; 3] {
    match facing {
        "down" => [0.0, -1.0, 0.0],
        "up" => [0.0, 1.0, 0.0],
        "north" => [0.0, 0.0, -1.0],
        "south" => [0.0, 0.0, 1.0],
        "west" => [-1.0, 0.0, 0.0],
        _ => [1.0, 0.0, 0.0],
    }
}

fn block(engine: &mut ParticleEngine, ctx: &AnimateContext<'_>, state: BlockStateId, path: &str, pos: [i32; 3]) {
    let [fx, fy, fz] = pos.map(f64::from);
    if path.ends_with("_faucet") {
        // FaucetBlock.animateTick: a quarter of the time, a pouring faucet with nothing in its stream shows red dust.
        if engine.random().next_float() >= 0.25 {
            return;
        }
        let Some(crate::containers::BlockEntity::Mod(e)) = ctx.world.block_entities.get(&(pos[0], pos[1], pos[2])) else { return };
        let pouring = matches!(e.nbt.get(&JavaString::from("state")), Some(Tag::Int(s)) if *s != 0);
        let render = match e.nbt.get(&JavaString::from("render_fluid")) {
            Some(Tag::String(s)) => !s.to_string_lossy().is_empty(),
            _ => false,
        };
        if !pouring || render {
            return;
        }
        let d = step(&property(ctx, state, "facing").unwrap_or_default());
        let p = [fx + 0.5 - 0.3 * d[0], fy + 0.5 - 0.3 * d[1], fz + 0.5 - 0.3 * d[2]];
        engine.add(&ParticleOptions::dust([1.0, 0.0, 0.0], 0.5), p, [0.0; 3]);
        return;
    }
    let (height, flame): (fn(f32) -> f32, T) = match path {
        "seared_melter" => (|f| f * 6.0 / 16.0, T::Flame),
        "seared_heater" => (|f| f * 14.0 / 16.0, T::Flame),
        "smeltery_controller" => (|f| (f * 6.0 + 2.0) / 16.0, T::Flame),
        "foundry_controller" => (|f| (f * 6.0 + 2.0) / 16.0, T::SoulFireFlame),
        "scorched_alloyer" => (|f| f * 4.0 / 16.0, T::SoulFireFlame),
        _ => return,
    };
    if property(ctx, state, "active").as_deref() != Some("true") {
        return;
    }
    let random = engine.random();
    let (x, y, z) = (fx + 0.5, fy + f64::from(height(random.next_float())), fz + 0.5);
    let front = 0.52;
    let side = random.next_double() * 0.6 - 0.3;
    // ControllerBlock.spawnFireParticles: smoke, then the flame, at the front.
    let p = match property(ctx, state, "facing").as_deref() {
        Some("west") => [x - front, y, z + side],
        Some("east") => [x + front, y, z + side],
        Some("north") => [x + side, y, z - front],
        Some("south") => [x + side, y, z + front],
        _ => return,
    };
    super::add(engine, T::Smoke, p, [0.0; 3]);
    super::add(engine, flame, p, [0.0; 3]);
}
