// The cheese block's movement factors (TinkerCommons.cheeseBlock: `speedFactor(0.4F)`, `jumpFactor(0.5F)`). Content
// blocks take their template's movement row; the cheese's template (a plain block) has 1.0 and 1.0. Every movement query
// (the player's, mobs', items', boats', minecarts', TNT's speed factor and the jump factors) reads a state's row through
// `BoundMovementProperties::get`, which answers the cheese's states here.
use super::{BoundMovementProperties, MovementBlock};
use crate::registry::{BlockRegistry, BlockStateId};
use std::{
    io,
    ops::ControlFlow,
    sync::atomic::{AtomicU32, Ordering},
};

const CHEESE: &str = "tconstruct:cheese_block";
/// The cheese block's first state and its number of states in the bound registry (0: none).
static FIRST: AtomicU32 = AtomicU32::new(0);
static COUNT: AtomicU32 = AtomicU32::new(0);

/// `MovementProperties::bind`'s start: where the cheese block's states are in this registry.
pub(super) fn bind(registry: &BlockRegistry) {
    let (first, count) = match registry.default_state(CHEESE) {
        None => (0, 0),
        Some(d) => {
            let is_cheese = |id: u32| registry.state(BlockStateId(id)).is_some_and(|s| s.name == CHEESE);
            let mut first = d.0;
            while first > 0 && is_cheese(first - 1) {
                first -= 1;
            }
            let mut end = d.0 + 1;
            while is_cheese(end) {
                end += 1;
            }
            (first, end - first)
        }
    };
    FIRST.store(first, Ordering::Relaxed);
    COUNT.store(count, Ordering::Relaxed);
}

/// `BoundMovementProperties::get`: a cheese state's row with Java's speed and jump factors; any other state goes on at
/// once.
pub(super) fn get(properties: &BoundMovementProperties, state: BlockStateId) -> ControlFlow<io::Result<MovementBlock>> {
    if state.0.wrapping_sub(FIRST.load(Ordering::Relaxed)) >= COUNT.load(Ordering::Relaxed) {
        return ControlFlow::Continue(());
    }
    match properties.states.get(state.0 as usize) {
        Some(block) => {
            let mut block = *block;
            block.coefficients.speed_factor = 0.4;
            block.coefficients.jump_factor = 0.5;
            ControlFlow::Break(Ok(block))
        }
        None => ControlFlow::Continue(()),
    }
}
