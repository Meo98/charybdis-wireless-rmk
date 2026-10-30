#!/usr/bin/env python3
"""Eine in Vial gespeicherte Belegung (.vil) als Standardbelegung einbauen.

    ./vial-nach-keymap.py DATEI.vil > ../charybdis/src/keymap.rs

Vial speichert die Belegung im Flash der Tastatur. Solange der Speicher
heil bleibt, reicht das. Loescht RMK ihn aber (SCHEMA_HASH-Falle,
`clear_storage`), faellt die Tastatur auf die Belegung zurueck, die in
der Firmware steht. Dieses Skript sorgt dafuer, dass das DEINE ist.

Die .vil-Datei ist nach Matrix geordnet: [Ebene][Reihe][Spalte], genau
wie keymap.rs. Es wird also nichts umsortiert. -1 heisst "an dieser
Matrixstelle sitzt keine Taste".

Jeder Name wird gegen RMKs eigene Liste geprueft (aus rmk-types). Was
das Skript nicht sicher uebersetzen kann, laesst es scheitern, statt
eine tote Taste zu bauen.
"""

import json
import pathlib
import re
import sys

HIER = pathlib.Path(__file__).resolve().parent
KEYCODES = HIER.parent / "charybdis" / "rmk-upstream" / "rmk-types" / "src" / "keycode"

ZEILEN, SPALTEN = 4, 12

# QMK/Vial-Kurzname -> RMK-Name, nur wo sie sich unterscheiden.
NAMEN = {
    "ESCAPE": "Escape", "TAB": "Tab", "SPACE": "Space", "ENTER": "Enter",
    "BSPACE": "Backspace", "DELETE": "Delete", "CAPSLOCK": "CapsLock",
    "LBRACKET": "LeftBracket", "RBRACKET": "RightBracket", "QUOTE": "Quote",
    "SCOLON": "Semicolon", "SLASH": "Slash", "BSLASH": "Backslash",
    "NONUS_BSLASH": "NonusBackslash", "GRAVE": "Grave", "MINUS": "Minus",
    "EQUAL": "Equal", "COMMA": "Comma", "DOT": "Dot",
    "LEFT": "Left", "RIGHT": "Right", "UP": "Up", "DOWN": "Down",
    "LCTRL": "LCtrl", "RCTRL": "RCtrl", "LSHIFT": "LShift", "RSHIFT": "RShift",
    "LALT": "LAlt", "RALT": "RAlt", "LGUI": "LGui", "RGUI": "RGui",
    "KP_ASTERISK": "KpAsterisk", "KP_EQUAL": "KpEqual",
    "KP_MINUS": "KpMinus", "KP_PLUS": "KpPlus",
    "BTN1": "MouseBtn1", "BTN2": "MouseBtn2", "BTN3": "MouseBtn3",
    "MUTE": "AudioMute", "VOLU": "AudioVolUp", "VOLD": "AudioVolDown",
    "MPLY": "MediaPlayPause", "MNXT": "MediaNextTrack", "MPRV": "MediaPrevTrack",
    "WBAK": "WwwBack", "WFWD": "WwwForward", "WREF": "WwwRefresh",
    "PWR": "SystemPower", "SLEP": "SystemSleep",
}
for z in range(10):
    NAMEN[str(z)] = "Kc%d" % z
for n in range(1, 25):
    NAMEN["F%d" % n] = "F%d" % n

# Vial-Modifierkuerzel -> ModifierCombination. LSFT(x) = x mit Shift,
# LSFT_T(x) = tippen x, halten Shift. SGUI = Shift+Gui.
MODS = {"LCTL": "LCTRL", "RCTL": "RCTRL", "LSFT": "LSHIFT", "RSFT": "RSHIFT",
        "LALT": "LALT", "RALT": "RALT", "LGUI": "LGUI", "RGUI": "RGUI",
        "SGUI": "LSHIFT | ModifierCombination::LGUI"}
# Modifier allein als Taste (fuer XXX_T(KC_NO): Tippen tut nichts)
MOD_TASTE = {"LCTL": "LCtrl", "RCTL": "RCtrl", "LSFT": "LShift", "RSFT": "RShift",
             "LALT": "LAlt", "RALT": "RAlt", "LGUI": "LGui", "RGUI": "RGui"}

fehler = []


def rmk_namen():
    """Gueltige Namen aus `pub enum HidKeyCode` in rmk-types."""
    namen = set()
    for f in KEYCODES.rglob("*.rs"):
        s = f.read_text()
        for m in re.finditer(r"pub enum HidKeyCode\b", s):
            start = s.index("{", m.end())
            tiefe, j = 0, start
            while True:
                tiefe += {"{": 1, "}": -1}.get(s[j], 0)
                if tiefe == 0:
                    break
                j += 1
            namen |= set(re.findall(r"^\s+([A-Z][A-Za-z0-9_]*)\s*(?:=\s*[^,]+)?,",
                                    s[start:j], re.M))
    return namen


def grundtaste(kc, gueltig, wo):
    """'KC_A' -> 'A' (RMK-Name), geprueft. None bei Fehler."""
    if not kc.startswith("KC_"):
        fehler.append("%s: '%s' ist keine einfache Taste" % (wo, kc))
        return None
    roh = kc[3:]
    name = NAMEN.get(roh, roh if len(roh) == 1 else roh.capitalize())
    if name not in gueltig:
        fehler.append("%s: '%s' -> '%s' kennt RMK nicht" % (wo, kc, name))
        return None
    return name


def taste(kc, gueltig, wo):
    if kc == -1 or kc == "KC_NO":
        return "a!(No)"
    if kc == "KC_TRNS":
        return "a!(Transparent)"
    if kc == "QK_BOOT":
        return "kbctrl!(Bootloader)"
    if m := re.fullmatch(r"USER(\d\d)", kc):
        return "user!(%d)" % int(m[1])
    if m := re.fullmatch(r"M(\d+)", kc):
        return "macros!(%d)" % int(m[1])
    if m := re.fullmatch(r"(MO|TG|TO)\((\d+)\)", kc):
        return "%s!(%s)" % (m[1].lower(), m[2])
    if m := re.fullmatch(r"LT(\d+)\((\w+)\)", kc):
        g = grundtaste(m[2], gueltig, wo)
        return "lt!(%s, %s)" % (m[1], g) if g else "a!(No)"
    if m := re.fullmatch(r"(\w{4})_T\((\w+)\)", kc):
        if m[1] not in MOD_TASTE:
            fehler.append("%s: Mod-Tap '%s' unbekannt" % (wo, kc))
            return "a!(No)"
        if m[2] == "KC_NO":
            # Halten = Modifier, Tippen = nichts. NICHT k!(LGui): das schickt
            # beim Antippen ein Gui (oeffnet den Launcher).
            return "mt!(No, ModifierCombination::%s)" % MODS[m[1]]
        g = grundtaste(m[2], gueltig, wo)
        return "mt!(%s, ModifierCombination::%s)" % (g, MODS[m[1]]) if g else "a!(No)"
    if m := re.fullmatch(r"(\w{4})\((\w+)\)", kc):
        if m[1] not in MODS:
            fehler.append("%s: Modifier '%s' unbekannt" % (wo, kc))
            return "a!(No)"
        g = grundtaste(m[2], gueltig, wo)
        return "wm!(%s, ModifierCombination::%s)" % (g, MODS[m[1]]) if g else "a!(No)"
    g = grundtaste(kc, gueltig, wo)
    return "k!(%s)" % g if g else "a!(No)"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    quelle = pathlib.Path(sys.argv[1])
    daten = json.loads(quelle.read_text())
    gueltig = rmk_namen()

    # Alle Ebenen behalten, auch leere: MO()/LT() zeigen auf feste Nummern.
    ebenen = daten["layout"]
    aus = [
        "// ERZEUGT aus %s" % quelle.name,
        "// von rmk/werkzeuge/vial-nach-keymap.py -- nicht von Hand aendern.",
        "// Neu erzeugen: Belegung in Vial speichern (.vil), Skript laufen lassen.",
        "",
        "use rmk::types::action::KeyAction;",
        "use rmk::types::modifier::ModifierCombination;",
        "use rmk::{%s};",  # nur, was unten vorkommt (sonst Warnung)
        "",
        "pub const ROW: usize = %d;" % ZEILEN,
        "pub const COL: usize = %d;" % SPALTEN,
        "pub const NUM_LAYER: usize = %d;" % len(ebenen),
        "",
        "#[rustfmt::skip]",
        "pub fn get_default_keymap() -> [[[KeyAction; COL]; ROW]; NUM_LAYER] {",
        "    [",
    ]
    for nr, ebene in enumerate(ebenen):
        if len(ebene) != ZEILEN or any(len(r) != SPALTEN for r in ebene):
            sys.exit("Ebene %d hat nicht %dx%d Plaetze" % (nr, ZEILEN, SPALTEN))
        aus.append("        // Ebene %d — vial" % nr)
        aus.append("        [")
        for z, reihe in enumerate(ebene):
            felder = [taste(kc, gueltig, "Ebene %d (%d,%d)" % (nr, z, s))
                      for s, kc in enumerate(reihe)]
            aus.append("            [" + ", ".join(felder) + "],")
        aus.append("        ],")
    aus += ["    ]", "}", ""]
    rumpf = "\n".join(aus)
    benutzt = sorted({m for m in re.findall(r"\b([a-z]+)!\(", rumpf)})
    aus = [z % ", ".join(benutzt) if z.startswith("use rmk::{%s}") else z for z in aus]

    if fehler:
        print("Uebersetzung fehlgeschlagen:", file=sys.stderr)
        for f in fehler:
            print("   ", f, file=sys.stderr)
        sys.exit(1)
    print("%d Ebenen uebersetzt, alle Namen von RMK bestaetigt" % len(ebenen),
          file=sys.stderr)
    sys.stdout.write("\n".join(aus))


if __name__ == "__main__":
    main()
