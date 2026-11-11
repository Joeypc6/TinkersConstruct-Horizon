fn tconstruct_list(mods: &mut Vec<crate::game::native_hooks::NativeMod>) {
    mods.push(crate::game::native_hooks::NativeMod {
        id: "tconstruct".into(),
        title: "Tinkers' Construct 3.12.1".into(),
        description: "Tools built from parts, smelteries and casting, as in Tinkers' Construct.".into(),
        // ToolClientEvents' key mappings (Options > Mods): the helmet's and the leggings' interactions.
        keys: vec![
            ["helmet_interact".into(), "Helmet Interaction".into(), "key.keyboard.z".into()],
            ["leggings_interact".into(), "Leggings Interaction".into(), "key.keyboard.i".into()],
        ],
    });
}
