#!/usr/bin/env python3
# Die Belegung AUS der Tastatur lesen und gegen die erwartete prüfen
#
#   ./lies-keymap.py
#
# Dass eine Firmware gebaut und aufgespielt wurde, heisst nicht, dass
# die richtige Belegung darauf liegt. Dieses Skript fragt die Tastatur
# selbst -- über dieselbe Schnittstelle, die auch Vial benutzt -- und
# vergleicht Taste für Taste mit dem, was aus der Konfiguration
# erzeugt wurde.
#
# Ohne das bliebe nur: tippen und hoffen.

import glob
import json
import os
import pathlib
import re
import struct
import sys
import time

HIER = pathlib.Path(__file__).resolve().parent
KEYMAP_RS = HIER.parent / "charybdis" / "src" / "keymap.rs"

HERSTELLER, PRODUKT = "4C4B", "4643"
CMD_GET_KEYCODE = 0x04
ZEILEN, SPALTEN = 4, 12


def finde_geraet():
    """Die HID-Schnittstelle finden, die auf Vial-Anfragen antwortet."""
    for pfad in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            text = open(os.path.join(pfad, "device/uevent")).read()
        except OSError:
            continue
        if HERSTELLER not in text.upper() or PRODUKT not in text.upper():
            continue
        yield "/dev/" + os.path.basename(pfad)


def frage(fd, ebene, zeile, spalte):
    """Einen Tastencode abfragen. Gibt None, wenn nichts zurückkommt.

    Die Tastatur meldet drei rohe HID-Schnittstellen; nur eine davon
    nimmt Vial-Anfragen an. Die anderen lassen sich zwar oeffnen,
    laufen beim Schreiben aber in eine Zeitueberschreitung -- das ist
    kein Fehler, sondern das Erkennungsmerkmal.
    """
    try:
        os.write(fd, bytes([0x00, CMD_GET_KEYCODE, ebene, zeile, spalte])
                 + bytes(28))
    except OSError:
        return None
    ende = time.time() + 0.5
    while time.time() < ende:
        try:
            antwort = os.read(fd, 32)
        except BlockingIOError:
            time.sleep(0.005)
            continue
        except OSError:
            return None
        if len(antwort) >= 5 and antwort[0] == CMD_GET_KEYCODE:
            return struct.unpack(">H", antwort[4:6])[0] if len(antwort) >= 6 else None
    return None


def hid_codes():
    """Name -> Zahlenwert, aus RMKs eigenem Quelltext.

    Nicht abgeschrieben: eine Tabelle, die neben der Firmware gepflegt
    wird, geht irgendwann auseinander, und dann prueft dieses Skript
    gegen seine eigene Erinnerung statt gegen die Tastatur.
    """
    datei = (HIER.parent / "charybdis" / "rmk-upstream" / "rmk-types"
             / "src" / "keycode" / "hid.rs")
    s = datei.read_text()
    start = s.index("{", s.index("pub enum HidKeyCode"))
    tiefe, j = 0, start
    while True:
        if s[j] == "{":
            tiefe += 1
        elif s[j] == "}":
            tiefe -= 1
            if tiefe == 0:
                break
        j += 1
    codes, letzter = {}, -1
    for m in re.finditer(
            r"^\s+([A-Z][A-Za-z0-9_]*)\s*(?:=\s*(0x[0-9A-Fa-f]+|\d+))?\s*,",
            s[start:j], re.M):
        name, wert = m.group(1), m.group(2)
        letzter = int(wert, 0) if wert else letzter + 1
        codes[name] = letzter
    return codes


# Wie Vial zusammengesetzte Tasten verschluesselt. Die oberen Bits
# sagen, um welche Art es sich handelt.
def erwarteter_code(ausdruck, codes):
    """Was die Tastatur fuer diesen keymap.rs-Ausdruck melden muss.

    Gibt None, wenn sich der Wert nicht vorhersagen laesst -- dann
    wird dieser Platz uebersprungen statt falsch beanstandet.
    """
    m = re.fullmatch(r"k!\((\w+)\)", ausdruck)
    if m:
        return codes.get(m.group(1))
    if ausdruck == "a!(No)":
        return 0
    if ausdruck == "a!(Transparent)":
        return 1
    # Zusammengesetzte Tasten, Kodierung wie in rmk host/via/keycode_convert.rs
    # (QMK-Schema: 5 Modifier-Bits Ctrl/Shift/Alt/Gui + Rechts-Bit 0x10).
    m = re.fullmatch(r"(mo|tg|to)!\((\d+)\)", ausdruck)
    if m:
        return {"mo": 0x5220, "tg": 0x5260, "to": 0x5200}[m.group(1)] | int(m.group(2))
    m = re.fullmatch(r"lt!\((\d+), (\w+)\)", ausdruck)
    if m and m.group(2) in codes:
        return 0x4000 | (int(m.group(1)) << 8) | codes[m.group(2)]
    m = re.fullmatch(r"(mt|wm)!\((\w+), (.+)\)", ausdruck)
    if m and m.group(2) in codes:
        bits = modifier_bits(m.group(3))
        if bits is not None:
            basis = 0x2000 if m.group(1) == "mt" else 0
            return basis | (bits << 8) | codes[m.group(2)]
    m = re.fullmatch(r"user!\((\d+)\)", ausdruck)
    if m:
        return 0x7E00 | int(m.group(1))
    m = re.fullmatch(r"macros!\((\d+)\)", ausdruck)
    if m:
        return 0x7700 + int(m.group(1))
    if ausdruck == "kbctrl!(Bootloader)":
        return 0x7C00
    return None


def modifier_bits(text):
    """'ModifierCombination::LSHIFT | ModifierCombination::LGUI' -> 5-Bit-Wert.

    QMK kann links und rechts nicht mischen; gemischt -> None (nicht pruefbar).
    """
    wert = {"CTRL": 1, "SHIFT": 2, "ALT": 4, "GUI": 8}
    bits, seiten = 0, set()
    for teil in text.split("|"):
        name = teil.strip().removeprefix("ModifierCombination::")
        if name[:1] not in "LR" or name[1:] not in wert:
            return None
        seiten.add(name[0])
        bits |= wert[name[1:]]
    if len(seiten) != 1:
        return None
    return bits | (0x10 if "R" in seiten else 0)


def erwartete_belegung():
    """Aus der erzeugten keymap.rs lesen, was draufliegen soll."""
    s = KEYMAP_RS.read_text()
    ebenen = []
    for block in re.findall(r"// Ebene \d+ — \w+\n        \[\n((?:.*\n){4})        \],", s):
        reihen = []
        for zeile in block.strip().split("\n"):
            inhalt = zeile.strip().lstrip("[").rstrip("],")
            # An den Kommas trennen, die nicht in Klammern stehen
            teile, tiefe, start = [], 0, 0
            for i, z in enumerate(inhalt):
                if z == "(":
                    tiefe += 1
                elif z == ")":
                    tiefe -= 1
                elif z == "," and tiefe == 0:
                    teile.append(inhalt[start:i].strip())
                    start = i + 1
            teile.append(inhalt[start:].strip())
            reihen.append([t for t in teile if t])
        ebenen.append(reihen)
    return ebenen


def main():
    erwartet = erwartete_belegung()
    if not erwartet:
        print("keymap.rs liess sich nicht lesen", file=sys.stderr)
        sys.exit(1)
    print("erwartet: %d Ebenen" % len(erwartet))

    for geraet in finde_geraet():
        try:
            fd = os.open(geraet, os.O_RDWR | os.O_NONBLOCK)
        except OSError:
            continue
        probe = frage(fd, 0, 0, 0)
        if probe is None:
            os.close(fd)
            continue

        print("Vial antwortet auf %s" % geraet)
        codes = hid_codes()

        geprueft = uebersprungen = 0
        abweichungen = []
        for nr, ebene in enumerate(erwartet):
            for z in range(ZEILEN):
                for sp in range(SPALTEN):
                    ausdruck = ebene[z][sp]
                    soll = erwarteter_code(ausdruck, codes)
                    if soll is None:
                        uebersprungen += 1
                        continue
                    ist = frage(fd, nr, z, sp)
                    geprueft += 1
                    if ist != soll:
                        abweichungen.append(
                            "Ebene %d (%d,%2d): %-22s erwartet %04X, Tastatur meldet %s"
                            % (nr, z, sp, ausdruck, soll,
                               "nichts" if ist is None else "%04X" % ist))
        os.close(fd)

        print()
        print("%d Plaetze geprueft, %d uebersprungen (zusammengesetzte Tasten)"
              % (geprueft, uebersprungen))
        if abweichungen:
            print()
            print("ROT -- %d Abweichung(en):" % len(abweichungen))
            for a in abweichungen[:25]:
                print("   ", a)
            if len(abweichungen) > 25:
                print("    ... und %d weitere" % (len(abweichungen) - 25))
            sys.exit(1)
        print("GRUEN -- die Tastatur traegt genau die erzeugte Belegung.")
        return

    print("Keine Vial-Schnittstelle gefunden.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
