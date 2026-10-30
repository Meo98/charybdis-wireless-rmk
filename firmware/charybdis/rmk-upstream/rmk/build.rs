#[path = "./build_common.rs"]
mod common;

fn main() {
    let mut cfgs = common::CfgSet::new();
    common::set_target_cfgs(&mut cfgs);

    // `RMK_COMMIT` and `RMK_FEATURES` go into the storage schema hash.
    // When either changes, the storage is erased.
    //
    // charybdis-wireless-rmk: pinned to "" instead of `git log`. This vendored
    // copy lives inside a git repo, so every commit touching it would change
    // the hash and wipe BLE bonds + the Vial keymap on the next flash. "" is
    // what the firmware already on the keyboard was built with (no .git).
    // Bump this string by hand only if the storage layout really changes.
    let commit = "";
    println!("cargo:rustc-env=RMK_COMMIT={commit}");

    let mut features: Vec<String> = std::env::vars()
        .filter_map(|(key, _)| key.strip_prefix("CARGO_FEATURE_").map(str::to_lowercase))
        .collect();
    features.sort();
    println!("cargo:rustc-env=RMK_FEATURES={}", features.join(","));
}
