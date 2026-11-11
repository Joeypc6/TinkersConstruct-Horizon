impl crate::game::Game<'_> {
    /// Tinkers' Construct's stations move their slots as Java's screens do (a tool's layout, the side inventory's
    /// scroll): the open mod screen of `block` takes these places, None hiding a slot. False when another is open.
    pub(in crate::game) fn hz_tconstruct_set_screen_slots(&mut self, block: &str, slots: &[Option<[f32; 2]>]) -> bool {
        let Some(s) = self.mod_screen.as_mut() else { return false };
        if s.block != block {
            return false;
        }
        for (i, p) in slots.iter().enumerate() {
            if let Some(slot) = s.screen.slots.get_mut(i) {
                *slot = *p;
            }
        }
        true
    }
}
