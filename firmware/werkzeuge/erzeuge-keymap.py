#!/usr/bin/env python3
# Die Belegung aus kmk/konfiguration/tastatur.json nach RMK übersetzen
#
#   ./erzeuge-keymap.py [> ../charybdis/src/keymap.rs]
#
# Die Belegung ist über Monate in der KMK-Fassung entstanden und wird
# weiter in der Oberfläche bearbeitet. Sie von Hand nach Rust
# abzuschreiben hiesse, sie zweimal zu pflegen -- und beim ersten
# Tippfehler tippt die Tastatur still das Falsche.
#
# KMK und RMK benennen dieselben Tasten verschieden (KC.BSPC gegen
# Backspace, KC.N1 gegen Kc1). Jeder übersetzte Name wird deshalb gegen
# RMKs eigene Liste geprüft, die aus rmk-types/src/keycode/ stammt.
# Was dort nicht steht, lässt das Skript scheitern, statt eine tote
# Taste zu erzeugen.

import json
import pathlib
import re
import sys

HIER = pathlib.Path(__file__).resolve().parent
WURZEL = HIER.parent.parent
KONFIG = WURZEL / "kmk" / "konfiguration" / "tastatur.json"
KEYCODES = HIER.parent / "charybdis" / "rmk-upstream" / "rmk-types" / "src" / "keycode"

ZEILEN, SPALTEN = 4, 12


def rmk_namen():
    """Die gültigen Tastennamen aus RMKs Quelltext holen.

    NUR aus `HidKeyCode`. RMK kennt daneben `ConsumerKey` und
    `SystemControlKey`, aber das Makro `k!()` nimmt ausschliesslich
    HID-Namen; die Medien- und Systemtasten werden intern aus
    HID-Codes abgeleitet (`HidKeyCode::AudioVolUp` wird zu
    `ConsumerKey::VolumeIncrement`). Wer den Consumer-Namen einsetzt,
    bekommt einen Übersetzungsfehler -- genau das ist hier beim ersten
    Versuch passiert.
    """
    namen = set()
    for f in KEYCODES.rglob("*.rs"):
        s = f.read_text()
        for m in re.finditer(r"pub enum (HidKeyCode)\b", s):
            start = s.index("{", m.end())
            tiefe, j = 0, start
            while True:
                if s[j] == "{":
                    tiefe += 1
                elif s[j] == "}":
                    tiefe -= 1
                    if tiefe == 0:
                        break
                j += 1
            namen |= set(re.findall(r"^\s+([A-Z][A-Za-z0-9_]*)\s*(?:=\s*[^,]+)?,",
                                    s[start:j], re.M))
    return namen


# KMK-Name -> RMK-Name. Nur was sich unterscheidet; alles andere wird
# unverändert durchgereicht und dann geprüft.
UEBERSETZUNG = {
    "NO": None, "TRNS": None,                 # Sonderfälle, siehe unten
    "ESC": "Escape", "BSPC": "Backspace", "ENT": "Enter", "SPC": "Space",
    "TAB": "Tab", "DEL": "Delete", "INS": "Insert",
    "MINS": "Minus", "EQL": "Equal", "LBRC": "LeftBracket",
    "RBRC": "RightBracket", "BSLS": "Backslash", "SCLN": "Semicolon",
    "QUOT": "Quote", "GRV": "Grave", "COMMA": "Comma", "DOT": "Dot",
    "SLSH": "Slash",
    "LEFT": "Left", "RIGHT": "Right", "UP": "Up", "DOWN": "Down",
    "HOME": "Home", "END": "End", "PGUP": "PageUp", "PGDN": "PageDown",
    "PSCR": "PrintScreen", "CAPS": "CapsLock",
    "LCTL": "LCtrl", "RCTL": "RCtrl", "LSFT": "LShift", "RSFT": "RShift",
    "LALT": "LAlt", "RALT": "RAlt", "LGUI": "LGui", "RGUI": "RGui",
    "MB_LMB": "MouseBtn1", "MB_RMB": "MouseBtn2", "MB_MMB": "MouseBtn3",
    "MB_BTN4": "MouseBtn4", "MB_BTN5": "MouseBtn5",
    "MW_UP": "MouseWheelUp", "MW_DOWN": "MouseWheelDown",
    "MW_LEFT": "MouseWheelLeft", "MW_RIGHT": "MouseWheelRight",
    "MS_UP": "MouseUp", "MS_DOWN": "MouseDown",
    "MS_LEFT": "MouseLeft", "MS_RIGHT": "MouseRight",
    # Die HID-Namen, nicht die Consumer-Namen -- siehe rmk_namen().
    "AUDIO_MUTE": "AudioMute", "AUDIO_VOL_UP": "AudioVolUp",
    "AUDIO_VOL_DOWN": "AudioVolDown",
    "MEDIA_PLAY_PAUSE": "MediaPlayPause", "MEDIA_STOP": "MediaStop",
    "MEDIA_NEXT_TRACK": "MediaNextTrack", "MEDIA_PREV_TRACK": "MediaPrevTrack",
    "BRIGHTNESS_UP": "BrightnessUp", "BRIGHTNESS_DOWN": "BrightnessDown",
    # Zeichen, die KMK als Shift-Kombination führt. RMK kennt sie als
    # eigene Namen; wo nicht, wird unten mit wm! geschiftet.
    "TILD": ("Grave", "LSHIFT"), "EXLM": ("Kc1", "LSHIFT"),
    "AT": ("Kc2", "LSHIFT"), "HASH": ("Kc3", "LSHIFT"),
    "DLR": ("Kc4", "LSHIFT"), "PERC": ("Kc5", "LSHIFT"),
    "CIRC": ("Kc6", "LSHIFT"), "AMPR": ("Kc7", "LSHIFT"),
    "ASTR": ("Kc8", "LSHIFT"), "LPRN": ("Kc9", "LSHIFT"),
    "RPRN": ("Kc0", "LSHIFT"), "UNDS": ("Minus", "LSHIFT"),
    "PLUS": ("Equal", "LSHIFT"), "LCBR": ("LeftBracket", "LSHIFT"),
    "RCBR": ("RightBracket", "LSHIFT"), "PIPE": ("Backslash", "LSHIFT"),
    "COLN": ("Semicolon", "LSHIFT"), "DQUO": ("Quote", "LSHIFT"),
    "LABK": ("Comma", "LSHIFT"), "RABK": ("Dot", "LSHIFT"),
    "QUES": ("Slash", "LSHIFT"),
}
for z in range(10):
    UEBERSETZUNG["N%d" % z] = "Kc%d" % z
for n in range(1, 25):
    UEBERSETZUNG["F%d" % n] = "F%d" % n

MODIFIER = {"LCTL": "LCTRL", "RCTL": "RCTRL", "LSFT": "LSHIFT",
            "RSFT": "RSHIFT", "LALT": "LALT", "RALT": "RALT",
            "LGUI": "LGUI", "RGUI": "RGUI"}

fehler = []


def taste(name, gueltig, wo):
    """Einen einfachen KMK-Namen in einen RMK-Ausdruck übersetzen."""
    if name == "NO":
        return "a!(No)"
    if name == "TRNS":
        return "a!(Transparent)"

    ziel = UEBERSETZUNG.get(name, name)
    if isinstance(ziel, tuple):
        grund, mod = ziel
        if grund not in gueltig:
            fehler.append("%s: '%s' -> '%s' kennt RMK nicht" % (wo, name, grund))
        return "wm!(%s, ModifierCombination::%s)" % (grund, mod)

    if ziel not in gueltig:
        fehler.append("%s: '%s' -> '%s' kennt RMK nicht" % (wo, name, ziel))
        return "a!(No)"
    return "k!(%s)" % ziel


def eintrag(t, gueltig, wo):
    if isinstance(t, str):
        return taste(t, gueltig, wo)

    art = t["art"]
    args = t["args"]
    if art == "HT":
        tippen, halten = args
        if halten not in MODIFIER:
            fehler.append("%s: HT hält '%s', das ist kein Modifier" % (wo, halten))
            return "a!(No)"
        ziel = UEBERSETZUNG.get(tippen, tippen)
        if isinstance(ziel, tuple) or ziel not in gueltig:
            fehler.append("%s: HT tippt '%s', das geht so nicht" % (wo, tippen))
            return "a!(No)"
        return "mt!(%s, ModifierCombination::%s)" % (ziel, MODIFIER[halten])
    if art == "LT":
        ebene, tippen = args
        ziel = UEBERSETZUNG.get(tippen, tippen)
        if isinstance(ziel, tuple) or ziel not in gueltig:
            fehler.append("%s: LT tippt '%s', das geht so nicht" % (wo, tippen))
            return "a!(No)"
        return "lt!(%d, %s)" % (ebene, ziel)
    if art in ("MO", "TG", "TO", "TT", "DF"):
        kurz = {"MO": "mo", "TG": "tg", "TO": "to", "TT": "tt", "DF": "df"}[art]
        return "%s!(%d)" % (kurz, args[0])

    fehler.append("%s: Verhalten '%s' kennt der Übersetzer nicht" % (wo, art))
    return "a!(No)"


def raster(ebene, gueltig):
    """Die 41 Plätze auf das 4x12-Raster verteilen.

    Die Reihenfolge entspricht der Anzeige: drei Reihen zu zwölf, dann
    die Daumen. Die rechte Hälfte ist spaltenverkehrt verdrahtet -- das
    steckt schon in der Reihenfolge der Plätze, nicht in dieser Tabelle.
    """
    tasten = ebene["tasten"]
    feld = [["a!(No)"] * SPALTEN for _ in range(ZEILEN)]
    for i in range(36):
        feld[i // SPALTEN][i % SPALTEN] = eintrag(
            tasten[i], gueltig, "Ebene %d Platz %d" % (ebene["nummer"], i))
    # Daumen: links Spalte 3, 4, 1 -- rechts 7, 9. Dieselbe Zuordnung
    # benutzt keyboard.toml in der Zeile "[3] (3,3) (3,4) (3,1) [1] ...".
    for platz, spalte in zip(range(36, 41), (3, 4, 1, 7, 9)):
        feld[3][spalte] = eintrag(
            tasten[platz], gueltig, "Ebene %d Daumen %d" % (ebene["nummer"], platz))
    return feld


def main():
    gueltig = rmk_namen()
    daten = json.loads(KONFIG.read_text())
    ebenen = daten["ebenen"]

    zeilen = [
        "// ERZEUGT aus kmk/konfiguration/tastatur.json",
        "// von rmk/werkzeuge/erzeuge-keymap.py -- nicht von Hand ändern.",
        "//",
        "// Die Belegung wird weiterhin in der Oberfläche gepflegt",
        "// (kmk/werkzeuge/oberflaeche/starten.sh); dieses Skript bringt sie",
        "// nach Rust. Jeder Name ist gegen RMKs eigene Liste geprüft.",
        "",
        "use rmk::types::action::KeyAction;",
        "use rmk::types::modifier::ModifierCombination;",
        "use rmk::{a, k, lt, mo, mt, tg, to, wm};",
        "",
        "pub const ROW: usize = %d;" % ZEILEN,
        "pub const COL: usize = %d;" % SPALTEN,
        "pub const NUM_LAYER: usize = %d;" % len(ebenen),
        "",
        "#[rustfmt::skip]",
        "pub fn get_default_keymap() -> [[[KeyAction; COL]; ROW]; NUM_LAYER] {",
        "    [",
    ]

    for e in ebenen:
        feld = raster(e, gueltig)
        zeilen.append("        // Ebene %d — %s" % (e["nummer"], e["name"]))
        zeilen.append("        [")
        for reihe in feld:
            zeilen.append("            [" + ", ".join(reihe) + "],")
        zeilen.append("        ],")

    zeilen += ["    ]", "}", ""]

    if fehler:
        print("Übersetzung fehlgeschlagen:", file=sys.stderr)
        for f in fehler:
            print("   ", f, file=sys.stderr)
        sys.exit(1)

    print("%d Ebenen übersetzt, alle Namen von RMK bestätigt"
          % len(ebenen), file=sys.stderr)
    sys.stdout.write("\n".join(zeilen))


if __name__ == "__main__":
    main()
