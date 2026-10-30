// ERZEUGT aus vial_layout_291026
// von rmk/werkzeuge/vial-nach-keymap.py -- nicht von Hand aendern.
// Neu erzeugen: Belegung in Vial speichern (.vil), Skript laufen lassen.

use rmk::types::action::KeyAction;
use rmk::types::modifier::ModifierCombination;
use rmk::{a, k, kbctrl, lt, mo, mt, to, user, wm};

pub const ROW: usize = 4;
pub const COL: usize = 12;
pub const NUM_LAYER: usize = 9;

#[rustfmt::skip]
pub fn get_default_keymap() -> [[[KeyAction; COL]; ROW]; NUM_LAYER] {
    [
        // Ebene 0 — vial
        [
            [k!(Escape), k!(Q), lt!(7, W), k!(E), k!(R), k!(T), k!(LeftBracket), k!(P), k!(O), k!(I), k!(U), k!(Y)],
            [k!(Tab), k!(A), mt!(S, ModifierCombination::LALT), mt!(D, ModifierCombination::LSHIFT), mt!(F, ModifierCombination::LCTRL), mt!(G, ModifierCombination::LGUI), k!(Quote), lt!(5, Semicolon), mt!(L, ModifierCombination::RALT), mt!(K, ModifierCombination::RSHIFT), mt!(J, ModifierCombination::RCTRL), mt!(H, ModifierCombination::RGUI)],
            [k!(NonusBackslash), k!(Z), k!(X), k!(C), k!(V), k!(B), k!(F5), k!(Slash), k!(Dot), k!(Comma), k!(M), k!(N)],
            [a!(No), lt!(2, Delete), a!(No), mt!(Kc0, ModifierCombination::LGUI), lt!(1, Space), a!(No), a!(No), lt!(3, Backspace), a!(No), lt!(4, Enter), a!(No), a!(No)],
        ],
        // Ebene 1 — vial
        [
            [k!(Escape), wm!(Kc3, ModifierCombination::LSHIFT), k!(Kc1), k!(Kc2), k!(Kc3), a!(Transparent), k!(Equal), wm!(Kc6, ModifierCombination::LSHIFT), wm!(Kc5, ModifierCombination::LSHIFT), wm!(Kc2, ModifierCombination::LSHIFT), k!(Minus), a!(Transparent)],
            [k!(CapsLock), wm!(Kc2, ModifierCombination::RALT), mt!(Kc4, ModifierCombination::RALT), mt!(Kc5, ModifierCombination::LSHIFT), mt!(Kc6, ModifierCombination::LCTRL), mt!(No, ModifierCombination::LGUI), wm!(Backslash, ModifierCombination::LSHIFT), wm!(RightBracket, ModifierCombination::LSHIFT), wm!(Minus, ModifierCombination::LSHIFT), wm!(Kc7, ModifierCombination::RALT), wm!(Kc7, ModifierCombination::LSHIFT), a!(Transparent)],
            [a!(Transparent), wm!(Grave, ModifierCombination::LSHIFT), k!(Kc7), k!(Kc8), k!(Kc9), k!(Kc0), a!(Transparent), k!(KpEqual), k!(KpAsterisk), k!(KpMinus), k!(KpPlus), a!(Transparent)],
            [a!(No), a!(Transparent), a!(No), a!(Transparent), a!(Transparent), a!(No), a!(No), wm!(RGui, ModifierCombination::RSHIFT), a!(No), k!(RGui), a!(No), a!(No)],
        ],
        // Ebene 2 — vial
        [
            [k!(F1), k!(F2), k!(F3), k!(F4), k!(F5), k!(F6), k!(F12), k!(F11), k!(F10), k!(F9), k!(F8), k!(F7)],
            [k!(SystemSleep), a!(Transparent), k!(AudioMute), k!(AudioVolDown), k!(AudioVolUp), a!(Transparent), a!(Transparent), a!(Transparent), k!(Right), k!(Up), k!(Down), k!(Left)],
            [k!(SystemPower), a!(Transparent), k!(MediaPrevTrack), k!(MediaPlayPause), k!(MediaNextTrack), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(No), a!(Transparent), a!(No), a!(Transparent), a!(Transparent), a!(No), a!(No), a!(Transparent), a!(No), a!(Transparent), a!(No), a!(No)],
        ],
        // Ebene 3 — vial
        [
            [a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(No), a!(Transparent), a!(No), a!(Transparent), a!(Transparent), a!(No), a!(No), a!(Transparent), a!(No), a!(Transparent), a!(No), a!(No)],
        ],
        // Ebene 4 — vial
        [
            [a!(Transparent), a!(Transparent), a!(Transparent), wm!(LeftBracket, ModifierCombination::RALT), wm!(RightBracket, ModifierCombination::RALT), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(Transparent), a!(Transparent), a!(Transparent), wm!(Kc8, ModifierCombination::LSHIFT), wm!(Kc9, ModifierCombination::LSHIFT), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(Transparent), a!(Transparent), a!(Transparent), wm!(Quote, ModifierCombination::RALT), wm!(Backslash, ModifierCombination::RALT), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(No), a!(Transparent), a!(No), a!(Transparent), a!(Transparent), a!(No), a!(No), a!(Transparent), a!(No), a!(Transparent), a!(No), a!(No)],
        ],
        // Ebene 5 — vial
        [
            [a!(Transparent), a!(Transparent), a!(Transparent), wm!(LeftBracket, ModifierCombination::RALT), wm!(RightBracket, ModifierCombination::RALT), a!(Transparent), a!(Transparent), a!(No), mo!(6), k!(MouseBtn3), k!(MouseBtn3), a!(No)],
            [a!(Transparent), a!(Transparent), k!(LAlt), k!(LShift), k!(LCtrl), k!(LGui), a!(Transparent), a!(Transparent), mo!(7), k!(MouseBtn2), k!(MouseBtn1), a!(No)],
            [a!(Transparent), a!(Transparent), a!(Transparent), wm!(Quote, ModifierCombination::RALT), wm!(Backslash, ModifierCombination::RALT), a!(Transparent), a!(Transparent), a!(Transparent), k!(WwwRefresh), k!(WwwForward), k!(WwwBack), a!(Transparent)],
            [a!(No), a!(Transparent), a!(No), a!(Transparent), a!(Transparent), a!(No), a!(No), a!(Transparent), a!(No), a!(Transparent), a!(No), a!(No)],
        ],
        // Ebene 6 — vial
        [
            [a!(Transparent), a!(Transparent), mo!(7), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(Transparent), k!(LGui), k!(LAlt), k!(LShift), k!(LCtrl), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(Transparent), a!(Transparent), a!(Transparent), mo!(3), mo!(2), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(No), k!(MouseBtn1), a!(No), k!(MouseBtn2), k!(MouseBtn3), a!(No), a!(No), k!(MouseBtn1), a!(No), to!(0), a!(No), a!(No)],
        ],
        // Ebene 7 — vial
        [
            [a!(Transparent), a!(Transparent), mo!(7), mo!(6), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(Transparent), k!(LGui), k!(LAlt), k!(LShift), k!(LCtrl), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(Transparent), a!(Transparent), a!(Transparent), mo!(3), mo!(2), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent), a!(Transparent)],
            [a!(No), k!(MouseBtn1), a!(No), k!(MouseBtn2), k!(MouseBtn3), a!(No), a!(No), k!(MouseBtn1), a!(No), to!(0), a!(No), a!(No)],
        ],
        // Ebene 8 — vial
        [
            [user!(8), user!(9), user!(0), user!(1), user!(2), kbctrl!(Bootloader), a!(Transparent), a!(No), a!(No), a!(No), a!(No), a!(No)],
            [a!(Transparent), a!(No), a!(No), a!(No), a!(No), a!(No), a!(Transparent), a!(No), a!(No), a!(No), a!(No), a!(No)],
            [a!(Transparent), a!(No), a!(No), a!(No), a!(No), a!(No), a!(Transparent), a!(No), a!(No), a!(No), a!(No), a!(No)],
            [a!(No), kbctrl!(Bootloader), a!(No), a!(No), a!(No), a!(No), a!(No), kbctrl!(Bootloader), a!(No), a!(No), a!(No), a!(No)],
        ],
    ]
}
