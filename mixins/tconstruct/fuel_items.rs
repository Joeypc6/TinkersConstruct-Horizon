use super::ItemStack;
use std::collections::HashSet;
use std::sync::RwLock;

// The items that burn (a burn time over 3, HeaterItemHandler.isItemValid), from the server's data: None until the
// first world loads, when every item may go in and the server's checks keep the rest out.
static FUELS: RwLock<Option<HashSet<String>>> = RwLock::new(None);

pub(super) fn is_fuel(item: &str) -> bool {
    FUELS.read().ok().and_then(|f| f.as_ref().map(|s| s.contains(item))).unwrap_or(true)
}

// The items that may hold fluid (TankItem.mayHaveFluid: buckets, the copper can, tank items, the data-driven
// transfers' items), from the server's data: None until the first world loads, when buckets go in.
static CONTAINERS: RwLock<Option<HashSet<String>>> = RwLock::new(None);

pub(super) fn is_container(item: &str) -> bool {
    CONTAINERS.read().ok().and_then(|f| f.as_ref().map(|s| s.contains(item))).unwrap_or_else(|| item.ends_with("bucket"))
}

// The stations' tags (`#tconstruct:patterns`, `#tconstruct:modifiable`), and the tinker station's slot rules for the
// click the server handles now (its menu type; per slot None any item, Some(None) none, Some(Some(items)) those).
static PATTERNS: RwLock<Option<HashSet<String>>> = RwLock::new(None);
static MODIFIABLE: RwLock<Option<HashSet<String>>> = RwLock::new(None);
type Rules = Vec<Option<Option<HashSet<String>>>>;
static CLICK_RULES: RwLock<Option<(String, Rules)>> = RwLock::new(None);

pub(super) fn is_pattern(item: &str) -> bool {
    PATTERNS.read().ok().and_then(|f| f.as_ref().map(|s| s.contains(item))).unwrap_or(true)
}

pub(super) fn station_rule(menu: &str, slot: usize, item: &str) -> Option<bool> {
    let rules = CLICK_RULES.read().ok()?;
    let (m, list) = rules.as_ref()?;
    if m != menu {
        return None;
    }
    let rule = list.get(slot)?;
    let modifiable = slot != 0 || MODIFIABLE.read().ok().and_then(|f| f.as_ref().map(|s| s.contains(item))).unwrap_or(true);
    Some(match rule {
        None => modifiable,
        Some(None) => false,
        Some(Some(items)) => modifiable && items.contains(item),
    })
}

impl super::Menu {
    /// Tinkers' Construct's heater: the items that burn, for its slot's rule (`tconstruct_slot_rules`).
    pub fn hz_tconstruct_set_fuels(fuels: HashSet<String>) {
        if let Ok(mut f) = FUELS.write() {
            *f = Some(fuels);
        }
    }

    /// Tinkers' Construct's smeltery: the items that may hold fluid, for its bucket slot's rule.
    pub fn hz_tconstruct_set_containers(items: HashSet<String>) {
        if let Ok(mut f) = CONTAINERS.write() {
            *f = Some(items);
        }
    }

    /// Tinkers' Construct's stations: the patterns and the modifiable items, for their slots' rules.
    pub fn hz_tconstruct_set_station_tags(patterns: HashSet<String>, modifiable: HashSet<String>) {
        if let Ok(mut f) = PATTERNS.write() {
            *f = Some(patterns);
        }
        if let Ok(mut f) = MODIFIABLE.write() {
            *f = Some(modifiable);
        }
    }

    /// Tinkers' Construct's tinker station: its slots' rules for the click about to be handled.
    pub fn hz_tconstruct_set_click_rules(menu: &str, rules: Vec<Option<Option<HashSet<String>>>>) {
        if let Ok(mut f) = CLICK_RULES.write() {
            *f = Some((menu.to_owned(), rules));
        }
    }

    /// Tinkers' Construct's crafting-grid recipes (`crafting_overslime_modifier`, `crafting_modifier_repair`): `craft`
    /// answers a grid no vanilla recipe takes with its result and, per cell, the item a take gives back.
    pub fn hz_tconstruct_set_craft(craft: Craft) {
        if let Ok(mut f) = CRAFT.write() {
            *f = Some(craft);
        }
    }
}

// The crafting grid's Tinkers' recipes (CustomRecipe: assemble, getRemainingItems). The result is set where vanilla's
// recompute finds none; a take (the result's `map_crafted`, then the grid's -1 per cell and the recompute) gives back
// the cells' remainders the recipe named, on the same menu whose grid is exactly the last answered one less 1 a cell.
pub type Craft = fn(&super::Env<'_>, &[Option<ItemStack>], usize) -> Option<(ItemStack, Vec<Option<ItemStack>>)>;

static CRAFT: RwLock<Option<Craft>> = RwLock::new(None);

struct Answered {
    menu: usize,
    grid: Vec<Option<ItemStack>>,
    result: ItemStack,
    back: Vec<Option<ItemStack>>,
}

thread_local! {
    static ANSWERED: std::cell::RefCell<Option<Answered>> = const { std::cell::RefCell::new(None) };
    static TAKEN: std::cell::Cell<bool> = const { std::cell::Cell::new(false) };
}

/// `map_crafted` (ResultSlot.onTake's onCraftedBy, a quick move's too): the Tinkers' result answered last is taken.
pub(super) fn craft_taken(stack: &ItemStack) {
    if ANSWERED.with_borrow(|a| a.as_ref().is_some_and(|a| a.result == *stack)) {
        TAKEN.set(true);
    }
}

/// The grid after vanilla's take: each cell one less than `before` (an emptied cell None), nothing else.
fn took_one(before: &[Option<ItemStack>], now: &[Option<ItemStack>]) -> bool {
    before.len() == now.len()
        && before.iter().zip(now).all(|(b, n)| match (b, n) {
            (None, None) => true,
            (Some(b), None) => b.count == 1,
            (Some(b), Some(n)) => b.count > 1 && n.count == b.count - 1 && n.same_item_same_components(b),
            (None, Some(_)) => false,
        })
}

/// The head of `Menu::recompute`: the take's remainders back, then a Tinkers' result where no vanilla recipe matches.
pub(super) fn craft_recompute(menu: &mut super::Menu, env: &super::Env<'_>) -> core::ops::ControlFlow<()> {
    if menu.grid_size == 0 {
        return core::ops::ControlFlow::Continue(());
    }
    let id = std::ptr::from_ref(menu) as usize;
    let taken = TAKEN.replace(false);
    if let Some(last) = ANSWERED.take().filter(|a| taken && a.menu == id) {
        if took_one(&last.grid, &menu.containers[super::GRID]) {
            for (cell, back) in last.back.into_iter().enumerate() {
                let Some(back) = back else { continue };
                match menu.containers[super::GRID][cell].as_mut() {
                    None => menu.containers[super::GRID][cell] = Some(back),
                    Some(have) => have.count += back.count,
                }
            }
        }
    }
    let Some(craft) = CRAFT.read().ok().and_then(|f| *f) else { return core::ops::ControlFlow::Continue(()) };
    let n = menu.grid_size;
    if env.recipes.find(&menu.containers[super::GRID], n).is_some() {
        return core::ops::ControlFlow::Continue(());
    }
    let grid = menu.containers[super::GRID].clone();
    let Some((result, back)) = craft(env, &grid, n) else { return core::ops::ControlFlow::Continue(()) };
    menu.containers[super::RESULT][0] = Some(result.clone());
    ANSWERED.set(Some(Answered { menu: id, grid, result, back }));
    core::ops::ControlFlow::Break(())
}
