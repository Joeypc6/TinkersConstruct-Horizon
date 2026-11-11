fn tconstruct_reload_apply(listener: &crate::game::native_reload_listeners::NativeReloadListener, files: &[(String, serde_json::Value)]) {
    crate::game::tconstruct::reload_apply(listener, files);
}
