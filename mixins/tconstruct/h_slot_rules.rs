fn tconstruct_slot_rules(menu: &str, slot: usize, stack: &ItemStack, may_place: &mut bool, max_stack: &mut u32) {
    // MeltingModuleInventory: any item, one a slot. HeaterItemHandler (SingleItemHandler(64)): what burns, 64.
    match menu {
        "tconstruct:melter" if slot < 3 => *max_stack = 1,
        // HeatingStructureContainerMenu: the bucket input takes fluid containers, the result nothing, each melting
        // slot one item (the server checks again). DuctItemHandler: one filled container.
        "tconstruct:smeltery" if slot == 0 => *may_place = tconstruct_fuel::is_container(&stack.item),
        "tconstruct:smeltery" if slot == 1 || slot >= 42 => *may_place = false,
        "tconstruct:smeltery" => *max_stack = 1,
        "tconstruct:duct" => {
            *may_place = stack.item.ends_with("_bucket") && !matches!(&*stack.item, "minecraft:milk_bucket" | "minecraft:powder_snow_bucket");
            *max_stack = 1;
        }
        "tconstruct:melter" | "tconstruct:heater" => {
            *may_place = tconstruct_fuel::is_fuel(&stack.item);
            *max_stack = 64;
        }
        // The stations: the part builder's pattern slot takes `#tconstruct:patterns`; the tinker station's slots their
        // layout's filters (TinkerStationSlot.mayPlace, set by the server for each click), its tool slot a modifiable.
        "tconstruct:part_builder" if slot == 1 => *may_place = tconstruct_fuel::is_pattern(&stack.item),
        "tconstruct:tinker_station" | "tconstruct:tinkers_anvil" => {
            if let Some(ok) = tconstruct_fuel::station_rule(menu, slot, &stack.item) {
                *may_place = *may_place && ok;
            }
        }
        _ => {}
    }
}
