fn tconstruct_fancy_frame_nbt(f: &ItemFrame, uuid: [i32; 4], raw: Option<&Tag>) -> core::ops::ControlFlow<Tag> {
    crate::entities::ItemFrame::hz_tc_frame_nbt(f, uuid, raw)
}
