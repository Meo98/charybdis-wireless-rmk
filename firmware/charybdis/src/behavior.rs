use rmk::config::{BehaviorConfig, CombosConfig, KeyboardMacrosConfig};
use rmk::keyboard::combo::Combo;
use rmk::types::constants::COMBO_MAX_NUM;
use rmk::types::morse::{MorseMode, MorseProfile};

pub fn get_default_behavior_config() -> BehaviorConfig {
    let mut behavior_config = BehaviorConfig::default();

    // 1. Tap-Hold-Zeiten: so, wie sie in Vial eingestellt waren
    //    (vial_layout_291026, Feld "settings", Nummern = SettingKey in
    //    rmk-types/src/protocol/vial.rs). Vial speichert sie im Flash; hier
    //    stehen sie, damit sie auch nach einem geloeschten Speicher gelten.
    //    2  Combo-Fenster            60 ms   (unten bei den Combos)
    //    6  One-Shot                 1000 ms
    //    7  Halte-Schwelle           150 ms  (vorher 200)
    //    18 Tipp-Intervall           30 ms   (vorher 20)
    //    19 Caps-Tipp-Intervall      20 ms
    //    22 Permissive Hold          aus     (vorher an)
    //    23 Hold on other press      aus     -> 22+23 aus = MorseMode::Normal
    //    25 Quick-Tap                130 ms  (vorher 180)
    //    26 Unilateral Tap           an
    //    27 Prior idle (Flow Tap)    150 ms  (Vial hatte 50; 29.10. erhoeht: Home-Row-Mods
    //       mitten im Wort werden so beim Druecken sofort Buchstaben -- sonst
    //       ueberholte eine spaeter gedrueckte Taste sie, Test
    //       rmk-upstream/rmk/tests/scenarios/charybdis_reihenfolge.toml)
    behavior_config.morse.enable_flow_tap = true;
    behavior_config.morse.prior_idle_time = embassy_time::Duration::from_millis(150);
    behavior_config.morse.default_profile = MorseProfile::new(
        Some(true),               // unilateral_tap (26)
        Some(MorseMode::Normal),  // permissive (22) und hold-on-other (23) aus
        Some(150u16),             // Halte-Schwelle (7)
        Some(180u16),             // Pause zwischen Mehrfach-Taps (keine Vial-Einstellung)
    )
    .with_quick_tap_timeout_ms(Some(130))
    .with_enable_flow_tap(Some(true));

    behavior_config.one_shot.timeout = embassy_time::Duration::from_millis(1000);
    behavior_config.tap.tap_interval = 30;
    behavior_config.tap.tap_capslock_interval = 20;

    // 2. Keine Combos (29.10.2026). Die 13 aus der Vorlage feuerten beim
    //    schnellen Tippen: "ei" -> Gui+3, "ru"/"ur" -> Gui+4 sprangen auf
    //    andere Arbeitsflaechen. Ausserdem hielt jede Combo-Taste bis zu 60 ms
    //    zurueck. Die alten stehen in sicherung-vor-layout-2026-10-29/behavior.rs.
    //    ACHTUNG: Combos liegen auch im Flash (Vial). Dort ebenfalls leeren,
    //    sonst gelten die gespeicherten weiter.
    let combos: [Option<Combo>; COMBO_MAX_NUM] = core::array::from_fn(|_| None);

    behavior_config.combo = CombosConfig {
        combos,
        timeout: embassy_time::Duration::from_millis(60),
        prior_idle_time: None,
        switch_to_default_layer: true,
    };

    // 3. Макросы:
    // Macro 0: "->" (тонкая стрелка)
    // Macro 1: "=>" (толстая стрелка)
    // Macro 2: "gt" (Vim переключение вкладки вперед)
    // Macro 3: "gT" (Vim переключение вкладки назад)
    let macro0 = rmk::keyboard_macros::to_macro_sequence("->");
    let macro1 = rmk::keyboard_macros::to_macro_sequence("=>");
    let macro2 = rmk::keyboard_macros::to_macro_sequence("gt");
    let macro3 = rmk::keyboard_macros::to_macro_sequence("gT");
    behavior_config.keyboard_macros = KeyboardMacrosConfig::new(
        rmk::keyboard_macros::define_macro_sequences(&[macro0, macro1, macro2, macro3]),
    );

    behavior_config
}
