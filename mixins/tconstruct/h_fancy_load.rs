fn tconstruct_fancy_load(game: &mut crate::game::Game<'_>, kind: &str, uuid: Option<[i32; 4]>, tag: &Tag) -> core::ops::ControlFlow<std::result::Result<(), Tag>> {
    crate::game::tconstruct_fancy::load(game, kind, uuid, tag)
}
