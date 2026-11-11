"""The fancy item frames and fancy armor stands (spec-gadgets.md G.9): their modules and injections, for make_bundle.py.

Horizon's item frames and armor stands with a variant: fancy_lib.rs (a module of the client library's entities.rs)
keeps each fancy frame's FrameType and RotationTimer and each fancy stand's StandType and LeftHanded by entity id;
fancy_frames.rs (a module of game.rs) is FancyItemFrameItem / FancyArmorStandItem, the entities' ticks, clicks, drops,
saves, LAN data and FancyItemFrameRenderer / FancyArmorStandRenderer. `emit(bundle)` writes the helpers and returns the
toml lines.
"""

F = "crate::game::tconstruct_fancy"
GAME_MUT = ("game", "&mut crate::game::Game<'_>", "&mut *self")
GAME = ("game", "&crate::game::Game<'_>", "&*self")

MODULES = [
    ("tconstruct-fancy-lib", "crates/horizon-client/src/entities.rs", "tconstruct_fancy", "fancy_lib.rs"),
    ("tconstruct-fancy", "crates/horizon-client/src/game.rs", "tconstruct_fancy", "fancy_frames.rs"),
]

CF = "core::ops::ControlFlow"

# (id, target, bindings, return type (None: a plain head), helper body)
HOOKS = [
    # The client library: a fancy frame's kind and dropped item, a fancy stand's fire immunity, a frame's save, a pick.
    ("kind", "horizon_client_lib::entities::ItemFrame::kind", [("f", "&ItemFrame", "&*self")], "&'static str",
     "tconstruct_fancy::frame_kind(f)"),
    ("frame-stack", "horizon_client_lib::entities::ItemFrame::item_stack_with_data", [("f", "&ItemFrame", "&*self")],
     "ItemStack", "tconstruct_fancy::frame_stack(f)"),
    ("stand-fire", "horizon_client_lib::entities::ArmorStand::environment_tick",
     [("a", "&mut ArmorStand", "&mut *self"), ("world", "&World", "world"), ("facts", "&BlockFacts", "facts"),
      ("registry", "&horizon_world::registry::BlockRegistry", "registry")],
     "bool", "tconstruct_fancy::stand_environment(a, world, facts, registry)"),
    ("frame-nbt", "horizon_client_lib::entity_nbt::item_frame_to_nbt",
     [("f", "&ItemFrame", "f"), ("uuid", "[i32; 4]", "uuid"), ("raw", "Option<&Tag>", "raw")],
     "Tag", "crate::entities::ItemFrame::hz_tc_frame_nbt(f, uuid, raw)"),
    ("pick", "horizon_client_lib::pick_item::pick",
     [("items", "&mut [Option<ItemStack>]", "&mut *items"), ("selected", "&mut usize", "&mut *selected"),
      ("stack", "&ItemStack", "stack"), ("infinite_materials", "bool", "infinite_materials")],
     "bool", "crate::entities::ItemFrame::hz_tc_pick(items, selected, stack, infinite_materials)"),
    # The game: placing, using, hitting, ticking, blasts, comparators.
    ("place-frame", "horizon_client::game::frames::Game<'_>::place_item_frame",
     [GAME_MUT, ("hit", "&crate::game::Hit", "hit"), ("stack", "&horizon_client::items::ItemStack", "stack")],
     "bool", f"{F}::place_frame(game, hit, stack)"),
    ("interact-frame", "horizon_client::game::frames::Game<'_>::interact_frame",
     [GAME_MUT, ("target", "Option<crate::game::InteractTarget>", "target")], "bool", f"{F}::interact_frame(game, target)"),
    ("attack-frame", "horizon_client::game::frames::Game<'_>::attack_frame", [GAME_MUT], "bool", f"{F}::attack_frame(game)"),
    ("tick-frames", "horizon_client::game::frames::Game<'_>::tick_item_frames", [GAME_MUT], None, f"{F}::tick_frames(game)"),
    ("frame-draw", "horizon_client::game::frames::Game<'_>::frame_geometry",
     [GAME_MUT, ("camera", "glam::DVec3", "camera"), ("out", "&mut Vec<horizon_client::mesher::Vertex>", "&mut *out")],
     "()", f"{F}::frame_geometry(game, camera, out)"),
    ("blast", "horizon_client::game::frames::Game<'_>::explosion_breaks_frames",
     [GAME_MUT, ("blast", "[f64; 3]", "blast"), ("diameter", "f64", "diameter"),
      ("interaction", "crate::game::explosion::BlockInteraction", "interaction")],
     "()", f"{F}::explosion(game, blast, diameter, interaction)"),
    ("analog", "horizon_client::game::<GameLevel<'_> as LevelAccess>::item_frame_analog_output",
     [("level", "&crate::game::GameLevel<'_>", "&*self"), ("pos", "BlockPos", "pos"), ("facing", "Direction", "facing")],
     "Option<i32>", f"{F}::analog(level, pos, facing)"),
    ("place-stand", "horizon_client::game::armor_stands::Game<'_>::place_armor_stand",
     [GAME_MUT, ("hit", "&crate::game::Hit", "hit"), ("stack", "&ItemStack", "stack")],
     "bool", f"{F}::place_stand(game, hit, stack)"),
    ("punch-stand", "horizon_client::game::armor_stands::Game<'_>::punch_armor_stand", [GAME_MUT, ("i", "usize", "i")],
     "bool", f"{F}::punch_stand(game, i)"),
    ("dispense", "horizon_client::game::dispenser::Game<'_>::dispense_item",
     [GAME_MUT, ("pos", "Pos", "pos"), ("facing", "Direction", "facing"), ("stack", "&ItemStack", "&stack")],
     "Result<Option<ItemStack>>", f"{F}::dispense(game, pos, facing, stack)"),
    # Saving, loading, the level's end, picks.
    ("load", "horizon_client::game::persist::Game<'_>::load_unlisted",
     [GAME_MUT, ("kind", "&str", "kind"), ("uuid", "Option<[i32; 4]>", "uuid"), ("tag", "&Tag", "&tag")],
     "std::result::Result<(), Tag>", f"{F}::load(game, kind, uuid, tag)"),
    ("save-stand", "horizon_client::game::persist::Game<'_>::save_armor_stand",
     [GAME_MUT, ("i", "usize", "i"), ("keys", "&HashSet<ChunkKey>", "keys")], "Option<(ChunkKey, Tag)>",
     None),
    ("clear", "horizon_client::game::Game<'_>::clear_entities", [], None, f"{F}::clear()"),
    ("main-hand", "horizon_client::game::native_hooks::Game<'_>::native_player_change_main_hand",
     [("player", "u128", "player"), ("left", "bool", "left")], None, f"{F}::main_hand(player, left)"),
    ("pick-hit", "horizon_client::game::pick_entity::Game<'_>::pick_entity_hit", [GAME], "Option<Option<i32>>",
     f"{F}::pick_hit(game)"),
    ("pick-guest", "horizon_client::game::pick_entity::Game<'_>::within_entity_range", [("id", "i32", "id")], None,
     f"{F}::pick_guest(id)"),
    # LAN: what guests get, and a guest's reading of it.
    ("lan", "horizon_client::game::lan_entities::Game<'_>::lan_object_states",
     [GAME_MUT, ("hub", "&mut Hub", "&mut *hub"), ("out", "&mut States", "&mut *out"),
      ("drain_minecart_steps", "bool", "drain_minecart_steps"), ("after", "u32", "after")],
     "()", f"{F}::lan_states(game, hub, out, drain_minecart_steps, after)"),
    ("remote", "horizon_client::game::remote_objects::Game<'_>::remote_object_data",
     [GAME_MUT, ("id", "i32", "id"), ("values", "&[(u8, i32, Value)]", "values")], "()", f"{F}::remote_data(game, id, values)"),
    # The stand's drawing, in armor_stands.rs for its private Poses and apply_pose.
    ("stand-draw", "horizon_client::game::armor_stands::Game<'_>::armor_stand_vertices",
     [GAME, ("a", "&ArmorStand", "a"), ("base", "glam::Mat4", "base"), ("packed", "u32", "packed"),
      ("skin", "&mut Option<&mut horizon_client::mobs::skin::Skin>", "&mut skin"), ("out", "&mut Vec<Vertex>", "&mut *out")],
     "()", None),
]

# Helper bodies written out (the hooks above with None).
RAW = {
    "save-stand": f"""    // FancyArmorStandEntity.addAdditionalSaveData: its id, Variant and LeftHanded on Horizon's stand.
    let Some(id) = {F}::saving_stand(game, i) else {{
        return {CF}::Continue(());
    }};
    let mut saved = game.save_armor_stand(i, keys);
    {F}::saved_stand(id, saved.as_mut().map(|s| &mut s.1));
    {CF}::Break(saved)
""",
    "stand-draw": f"""    // FancyArmorStandRenderer: the stand's own texture (full bright for necrotic bone), its body hidden while a clear
    // stand wears or holds anything, a left-handed stand's hands swapped; then Horizon's items, armour and wings.
    let Some((texture, full_bright, hidden, left)) = {F}::stand_look(a) else {{
        return {CF}::Continue(());
    }};
    if !{F}::stand_draw_guard(true) {{
        return {CF}::Continue(());
    }}
    let packed = if full_bright {{ horizon_client::mobs::render::FULL_BRIGHT }} else {{ packed }};
    let model = if a.small {{ &game.armor_stand_assets.small }} else {{ &game.armor_stand_assets.main }};
    let uv = game.gui.atlas.sprites.get(texture).map(|r| [r.u0, r.v0, r.u1, r.v1]);
    if !a.invisible && !hidden && let (Some(model), Some(uv)) = (model, uv) {{
        let mut poses = Poses::new(model);
        apply_pose(&mut poses, &a.pose);
        for (name, shown) in [("left_arm", a.show_arms), ("right_arm", a.show_arms), ("base_plate", !a.no_base_plate)] {{
            if !shown && poses.has(name) {{
                let pose = poses.get(name);
                pose[6] = 0.0;
                pose[7] = 0.0;
                pose[8] = 0.0;
            }}
        }}
        horizon_client::mobs::render::put(&mut *skin, model, base, &poses, uv, 0.0, 0xFFFF_FFFF, packed, 0, out);
    }}
    let mut plain = a.clone();
    plain.invisible = true;
    if left {{
        plain.equipment.swap(0, 1);
    }}
    game.armor_stand_vertices(&plain, base, packed, skin.as_deref_mut(), out);
    {F}::stand_draw_guard(false);
    {CF}::Break(())
""",
}


def emit(bundle, binding_lines):
    out = []
    for module_id, file, name, source in MODULES:
        out += ["[[module]]", f'id = "{module_id}"', f'file = "{file}"', f'name = "{name}"', f'source = "{source}"', ""]
    for hook_id, target, bindings, ret, body in HOOKS:
        name = f"tconstruct_fancy_{hook_id.replace('-', '_')}"
        helper = f"h_fancy_{hook_id.replace('-', '_')}.rs"
        args = ", ".join(f"{n}: {t}" for n, t, _ in bindings)
        returns = f" -> {CF}<{ret}>" if ret else ""
        if body is None:
            text = RAW[hook_id]
        elif ret:
            text = f"    {body}\n"
        else:
            text = f"    {body};\n"
        (bundle / helper).write_text(f"fn {name}({args}){returns} {{\n{text}}}\n", encoding="utf8")
        cancel = ["cancellable = true"] if ret else []
        out += ["[[injection]]", f'id = "tc-fancy-{hook_id}"', 'kind = "HEAD"', *cancel, f'target = "{target}"',
                f'helper = "{helper}"', "bindings = [", binding_lines(bindings).rstrip("\n"), "]", ""]
    return out
