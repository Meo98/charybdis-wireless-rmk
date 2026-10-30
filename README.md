# Charybdis Mini (3x6) Wireless — RMK firmware + printable parts

My working setup for the wireless **Charybdis Mini 3x6** (nice!nano v2 + PMW3610
trackball, split over BLE): a tuned [RMK](https://github.com/rmk-rs/rmk)
(Rust) firmware and two printable mods. Built and used daily on Linux.

| Folder | What | License |
|---|---|---|
| [`firmware/`](firmware/) | RMK firmware, build/flash scripts, tools, ready UF2 | MIT OR Apache-2.0 |
| [`3d-print/18650-tenting-mod/`](3d-print/18650-tenting-mod/) | bottom plate with built-in 18650 cell + tenting | CC BY-NC-SA 4.0 |
| [`3d-print/des-key-caps/`](3d-print/des-key-caps/) | DES keycaps split for FDM printing (no sprue) | GPL-3.0 |

The READMEs inside the folders are in German.

## Firmware

Based on [jools333/rmk](https://github.com/jools333/rmk), a complete RMK port for
this exact keyboard. Changes on top of it:

- **Direct Bluetooth to the computer**, no dongle needed (`dongle_profiles = 0`;
  with a dongle profile RMK only advertises to dongles). USB and BLE work at the
  same time; they show up as `Charybdis BT` and `Charybdis USB`
  (new `DeviceConfig::usb_product_name`).
- **Lower latency:** FastDebouncer with 5 ms, split sleep disabled (subrating
  cost 100–230 ms), trackball at 133 Hz.
- **Hi-res scrolling** via HID resolution multiplier 120 (USB + BLE).
- **QMK-style tap-hold** (`rmk/src/keyboard.rs`): keys after a home-row mod are
  buffered until the mod is decided; a second mod on the same hand is a chord
  (chordal hold). Tests: `rmk-upstream/rmk/tests/scenarios/charybdis_reihenfolge.toml`.
- **My keymap** baked into `src/keymap.rs` (from Vial, backup in
  [`firmware/vial/`](firmware/vial/)). Trackball modes per layer: layer 7 =
  scroll, layer 6 = sniper.

Known issue: 6 of the 13 combos don't fire next to mod-/layer-tap keys.

### Build

```sh
cd firmware
./bauen.sh            # both halves -> fertig/rechts-zentrale.uf2, fertig/links-gegenstelle.uf2
./bauen.sh reset      # additionally a settings-reset image
```

Needs Rust stable ≥ 1.93 via rustup, `arm-none-eabi` binutils, a C compiler and
libclang. On NixOS `shell.nix` provides everything except rustup:
`nix shell nixpkgs#rustup -c ./bauen.sh`.

### Flash

1. Bootloader: double-tap reset, or without touching the board
   `python3 werkzeuge/bootloader.py` (Vial command over hidraw, USB only).
2. Copy the UF2 onto the `NICENANO` drive. (`./flashen.sh rechts|links|beide` does
   this, but tells the halves apart by USB port — adjust the ports at its top.)
   Right half = central (connects to the computer), left = peripheral.
3. Pair over Bluetooth as `Charybdis BT`.

Prebuilt UF2 are in [`firmware/fertig/`](firmware/fertig/).

### Things worth knowing

- **Storage wipe trap.** RMK erases its whole flash storage (BLE bonds *and* the
  Vial keymap) when its `SCHEMA_HASH` changes. Upstream mixes the current git
  commit into that hash, so in a git repo every commit would wipe the keyboard on
  the next flash. This repo pins it (`rmk-upstream/rmk/build.rs`). After a wipe:
  remove the device from the computer's Bluetooth list and pair again.
- **Vial over Bluetooth does not work on Linux** (bluez passes the report-ID
  byte through). Plug in USB for Vial. Changes made in Vial live in flash and
  take priority over the firmware defaults.
- **kanata / keyd users:** exclude the keyboard (`Charybdis BT`, `Charybdis USB`)
  or every home-row mod gets a second tap-hold layer and typing lags.
- `werkzeuge/lies-keymap.py` reads the keymap back from the keyboard and compares
  it key by key with `src/keymap.rs`; `werkzeuge/messe-takt.py` measures report
  rate and checks that hi-res scrolling negotiated correctly.

## Credits

- Keyboard: [Bastard Keyboards — Charybdis](https://github.com/Bastardkb/Charybdis)
- Wireless build guide: [280Zo](https://github.com/280Zo/charybdis-wireless-mini-3x6-build-guide)
- RMK port this is based on: [jools333/rmk](https://github.com/jools333/rmk)
- Firmware framework: [RMK](https://github.com/rmk-rs/rmk) by Haobo Gu
- Keycaps: [pseudoku/PseudoMakeMeKeyCapProfiles](https://github.com/pseudoku/PseudoMakeMeKeyCapProfiles)
