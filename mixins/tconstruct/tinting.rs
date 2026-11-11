// Tinkers' Construct's slime foliage colours (WorldClientEvents.registerBlockColorHandlers, SlimeColorizer), a child
// module of the section mesher. Java registers a block colour handler on the slime grass and nylium, leaves, ferns,
// tall grass, potted ferns and the two vines; Horizon gives a tint source only to vanilla's block names.
// - In the world: the foliage type's 256x256 colormap (`assets/tconstruct/textures/colormap/<type>_grass_color.png`,
//   read from the pack on each resource load, so a resource pack may replace it as in Java) at the block's x and z,
//   leaves and vines offset by LOOP_OFFSET (128, 0, 128). The tables' per-state tint sources are fixed when they are
//   built, so each resource load makes a copy of the mesh tables in which these states take a position-reading
//   source (the dry foliage resolver, which only leaf litter has otherwise), and the section mesher meshes with the
//   copy. When that source asks the biome blend for the block's colour, the answer is the colormap's: the block is
//   the one the mesher placed last on this thread (`offset`, asked for each block before its faces).
// - Terrain particles (`terrain_particle_tint`): the same colour at the block.
// - With no position (`MeshTables::default_tint`: block models drawn as items, in minecarts and the guide's scenes;
//   `tint_source`: native passes drawing blocks as voxels): FoliageType's own colour.
// The tint index is not read, as in Java's handlers: every tinted face of these blocks takes the colour.
use super::{Info, MeshTables, Resolver, Tint, TintSource, Tints};
use horizon_world::registry::{BlockRegistry, BlockStateId};
use std::cell::{Cell, RefCell};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, RwLock};

// FoliageType in order, with its constructor colour (getColor: the item colour, and a block's with no position).
const TYPES: [&str; 5] = ["earth", "sky", "ichor", "ender", "blood"];
const COLORS: [u32; 5] = [0x8C_D782, 0x00_F4DA, 0xD0_9800, 0xA9_2DFF, 0xB8_0000];
// A state's kind: 0 for none, else 1 + its FoliageType, with OFFSET for the leaves and vines.
const OFFSET: u8 = 8;
const DIRTS: [&str; 5] = ["earth", "sky", "ichor", "ender", "vanilla"];

// What one resource load gives: the mesh tables it built (by address) and their copy with these states' sources,
// each state's kind, and the five colormaps (empty when the pack has none: the type's colour then).
struct Table {
    original: usize,
    copy: &'static MeshTables,
    kinds: Vec<u8>,
    maps: [Vec<u32>; 5],
}

impl Table {
    // WorldClientEvents.getSlimeColorByPos with a position.
    fn at(&self, kind: u8, x: i32, z: i32) -> u32 {
        let t = usize::from((kind & !OFFSET) - 1);
        let (x, z) = if kind & OFFSET != 0 { (x.wrapping_add(128), z.wrapping_add(128)) } else { (x, z) };
        colormap(&self.maps[t], x, z).unwrap_or(COLORS[t])
    }

    fn kind(&self, state: BlockStateId) -> u8 {
        self.kinds.get(state.0 as usize).copied().unwrap_or(0)
    }

    // The kind of the copy's state whose `Info` is at `at`.
    fn kind_at(&self, at: usize) -> u8 {
        let base = self.copy.info.as_ptr() as usize;
        let offset = at.wrapping_sub(base);
        if offset >= std::mem::size_of_val(self.copy.info.as_slice()) {
            return 0;
        }
        self.kinds.get(offset / std::mem::size_of::<Info>()).copied().unwrap_or(0)
    }
}

// SlimeColorizer.getColor: x and z each fold into |256 - |pos| % 512| / 256 (float arithmetic, as Java's), the larger
// is the colormap's row and the smaller its column, so the colours loop every 512 blocks.
fn colormap(map: &[u32], x: i32, z: i32) -> Option<u32> {
    let fold = |p: i32| ((256.0f32 - (p.wrapping_abs() as f32) % 512.0) / 256.0).abs();
    let (mut a, mut b) = (fold(x), fold(z));
    if a < b {
        std::mem::swap(&mut a, &mut b);
    }
    let index = ((a * 255.0) as i32) << 8 | (b * 255.0) as i32;
    map.get(index as usize).copied()
}

// The table, replaced on each resource load. Mesh workers keep their own handle and look at the shared one again only
// when the generation moved, so a lookup takes no lock and allocates nothing.
static TABLE: RwLock<Option<Arc<Table>>> = RwLock::new(None);
static GENERATION: AtomicUsize = AtomicUsize::new(0);

thread_local! {
    static CACHED: RefCell<(usize, Option<Arc<Table>>)> = const { RefCell::new((0, None)) };
    // The block the section mesher meshes on this thread: its state's `Info` (by address) and its x and z.
    static PLACE: Cell<(usize, i32, i32)> = const { Cell::new((0, 0, 0)) };
}

fn with_table<R>(f: impl FnOnce(&Table) -> Option<R>) -> Option<R> {
    let generation = GENERATION.load(Ordering::Acquire);
    CACHED.with(|cached| {
        let mut cached = cached.borrow_mut();
        if cached.0 != generation {
            *cached = (generation, TABLE.read().ok().and_then(|t| t.clone()));
        }
        cached.1.as_deref().and_then(f)
    })
}

// The state names Java's handlers are registered on, with their kind.
fn kind_of(name: &str) -> u8 {
    let Some(path) = name.strip_prefix("tconstruct:") else { return 0 };
    let typed = |t: &str| TYPES.iter().position(|x| *x == t).map_or(0, |i| i as u8 + 1);
    match path {
        "sky_slime_vine" => return typed("sky") | OFFSET,
        "ender_slime_vine" => return typed("ender") | OFFSET,
        _ => {}
    }
    if let Some(rest) = path.strip_suffix("_slime_grass") {
        // <foliage>_<dirt>_slime_grass (the slime grass and, on ichor and blood, the nylium).
        return rest.split_once('_').filter(|(_, d)| DIRTS.contains(d)).map_or(0, |(t, _)| typed(t));
    }
    if let Some(t) = path.strip_prefix("potted_").and_then(|p| p.strip_suffix("_slime_fern")) {
        return typed(t);
    }
    if let Some(t) = path.strip_suffix("_slime_leaves") {
        let k = typed(t);
        return if k == 0 { 0 } else { k | OFFSET };
    }
    path.strip_suffix("_slime_fern").or_else(|| path.strip_suffix("_slime_tall_grass")).map_or(0, typed)
}

// SlimeColorReloadListener.prepare: the colormap's pixels, row by row, as 0xRRGGBB.
fn read_colormap(root: &std::path::Path, t: &str) -> Vec<u32> {
    let path = root.join("assets/tconstruct/textures/colormap").join(t.to_owned() + "_grass_color.png");
    let decode = || -> Option<Vec<u32>> {
        let bytes = horizon_core::prepared_files::read(&path).ok()?;
        let mut decoder = png::Decoder::new(std::io::Cursor::new(bytes));
        decoder.ignore_checksums(true);
        decoder.set_transformations(png::Transformations::EXPAND | png::Transformations::STRIP_16);
        let mut reader = decoder.read_info().ok()?;
        let mut buf = vec![0; reader.output_buffer_size()?];
        let info = reader.next_frame(&mut buf).ok()?;
        let channels = info.color_type.samples();
        let rgb = |p: &[u8]| match p.len() {
            1 | 2 => u32::from(p[0]) * 0x01_0101,
            _ => u32::from(p[0]) << 16 | u32::from(p[1]) << 8 | u32::from(p[2]),
        };
        Some(buf[..info.buffer_size()].chunks_exact(channels).map(rgb).collect())
    };
    decode().unwrap_or_else(|| {
        log::warn!("Horizon: Tinkers' Construct's colormap {} could not be read", path.display());
        Vec::new()
    })
}

impl MeshTables {
    /// Tinkers' Construct's slime foliage: these tables' states with Java's colour handlers, the copy of the tables
    /// the section mesher uses in their place (those states reading their colour by position), and the colormaps of
    /// the pack at `root`. Called once per resource load, with the new tables; the copy stays for the game's life.
    pub fn hz_tconstruct_foliage(&self, root: &std::path::Path, registry: &BlockRegistry) {
        let kinds: Vec<u8> = (0..self.info.len())
            .map(|id| registry.state(BlockStateId(id as u32)).map_or(0, |s| kind_of(&s.name)))
            .collect();
        let table = kinds.iter().any(|k| *k != 0).then(|| {
            let mut info = self.info.clone();
            for (i, k) in info.iter_mut().zip(&kinds) {
                if *k != 0 {
                    // Every tint index (Java's handlers ignore it) reads the position's colour.
                    i.tints = [Tint::DryFoliage; 2];
                    i.tint_count = u8::MAX;
                }
            }
            let copy: &'static MeshTables = Box::leak(Box::new(MeshTables {
                info,
                solid: self.solid.clone(),
                full_faces: self.full_faces.clone(),
                visibility: self.visibility.clone(),
                water_still: self.water_still,
                water_flow: self.water_flow,
                water_overlay: self.water_overlay,
                lava_still: self.lava_still,
                lava_flow: self.lava_flow,
                animated_layers: self.animated_layers.clone(),
            }));
            Arc::new(Table {
                original: std::ptr::from_ref(self) as usize,
                copy,
                kinds,
                maps: TYPES.map(|t| read_colormap(root, t)),
            })
        });
        if let Ok(mut shared) = TABLE.write() {
            *shared = table;
        }
        GENERATION.fetch_add(1, Ordering::Release);
    }
}

// The head of `Mesher::mesh_reusing` (every section mesh): the tables of this resource load are meshed as their copy.
pub(super) fn mesh_with_copy(me: &mut super::Mesher<'_>) {
    let at = std::ptr::from_ref(me.tables) as usize;
    if let Some(copy) = with_table(|t| (t.original == at).then_some(t.copy)) {
        me.tables = copy;
    }
}

// The head of `offset`: the block the section mesher meshes now.
pub(super) fn place(info: &Info, x: i32, z: i32) {
    PLACE.set((std::ptr::from_ref(info) as usize, x, z));
}

// The head of `Tints::get`: the copy's position source of a slime foliage state answers with the colormap at its
// block. `x`, `z` are section-local, the section's chunk is in `tints`.
pub(super) fn blend(tints: &Tints<'_>, resolver: Resolver, x: i32, z: i32) -> core::ops::ControlFlow<u32> {
    if !matches!(resolver, Resolver::Dry) {
        return core::ops::ControlFlow::Continue(());
    }
    let (placed, px, pz) = PLACE.get();
    let [cx, cz, _] = tints.origin;
    if px != cx.wrapping_mul(16).wrapping_add(x) || pz != cz.wrapping_mul(16).wrapping_add(z) {
        return core::ops::ControlFlow::Continue(());
    }
    let color = with_table(|t| match t.kind_at(placed) {
        0 => None,
        k => Some(t.at(k, px, pz)),
    });
    match color {
        Some(c) => core::ops::ControlFlow::Break(c),
        None => core::ops::ControlFlow::Continue(()),
    }
}

// The head of `MeshTables::terrain_particle_tint`: TerrainParticle's colour, the block's at its position.
pub(super) fn particle(state: BlockStateId, pos: [i32; 3]) -> core::ops::ControlFlow<Option<u32>> {
    match with_table(|t| match t.kind(state) {
        0 => None,
        k => Some(t.at(k, pos[0], pos[2])),
    }) {
        Some(c) => core::ops::ControlFlow::Break(Some(c)),
        None => core::ops::ControlFlow::Continue(()),
    }
}

// FoliageType.getColor of a slime foliage state, for a tinted face drawn with no position.
fn fixed(state: BlockStateId, index: i32) -> Option<u32> {
    if index < 0 {
        return None;
    }
    with_table(|t| match t.kind(state) {
        0 => None,
        k => Some(COLORS[usize::from((k & !OFFSET) - 1)]),
    })
}

// The head of `MeshTables::default_tint`.
pub(super) fn default(state: BlockStateId, index: i32) -> core::ops::ControlFlow<Option<u32>> {
    match fixed(state, index) {
        Some(c) => core::ops::ControlFlow::Break(Some(c)),
        None => core::ops::ControlFlow::Continue(()),
    }
}

// The head of `MeshTables::tint_source`.
pub(super) fn source(state: BlockStateId, index: i32) -> core::ops::ControlFlow<Option<TintSource>> {
    match fixed(state, index) {
        Some(c) => core::ops::ControlFlow::Break(Some(TintSource::Fixed(c))),
        None => core::ops::ControlFlow::Continue(()),
    }
}
