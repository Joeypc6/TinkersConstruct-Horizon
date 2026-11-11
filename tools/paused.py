"""Features whose native mixins aren't finished, left out of the bundle until they are (their Rust stays in
mixins/tconstruct). The content generator reads this too, so the content matches what the bundle carries.

  effects: Experienced / Ricochet and the cheese block's speed and jump factors (tc_effects*.rs, tc_cheese.rs)
  fancy:   the fancy item frames and armor stands (fancy_*.rs, tools/fancy_hooks.py)
"""
PAUSED = {"effects", "fancy"}
