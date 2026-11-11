fn tconstruct_fancy_save_stand(game: &mut crate::game::Game<'_>, i: usize, keys: &HashSet<ChunkKey>) -> core::ops::ControlFlow<Option<(ChunkKey, Tag)>> {
    // FancyArmorStandEntity.addAdditionalSaveData: its id, Variant and LeftHanded on Horizon's stand.
    let Some(id) = crate::game::tconstruct_fancy::saving_stand(game, i) else {
        return core::ops::ControlFlow::Continue(());
    };
    let mut saved = game.save_armor_stand(i, keys);
    crate::game::tconstruct_fancy::saved_stand(id, saved.as_mut().map(|s| &mut s.1));
    core::ops::ControlFlow::Break(saved)
}
