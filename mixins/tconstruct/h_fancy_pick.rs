fn tconstruct_fancy_pick(items: &mut [Option<ItemStack>], selected: &mut usize, stack: &ItemStack, infinite_materials: bool) -> core::ops::ControlFlow<bool> {
    crate::entities::ItemFrame::hz_tc_pick(items, selected, stack, infinite_materials)
}
