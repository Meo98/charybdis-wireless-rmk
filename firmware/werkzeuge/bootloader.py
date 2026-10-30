#!/usr/bin/env python3
# Die Tastatur in den Bootloader schicken, ohne sie anzufassen
#
#   sudo ./bootloader.py            (oder als Benutzer, wenn hidraw erlaubt)
#
# Sonst müsste man zweimal schnell auf den Reset-Knopf drücken, und der
# sitzt bei dieser Tastatur unter dem Gehäuse.
#
# RMK versteht das Vial-Protokoll; dessen Befehl 0x0B heisst
# "BootloaderJump". Geschickt wird er über die rohe HID-Schnittstelle,
# dieselbe, über die auch Vial die Belegung ändert.
#
# Danach meldet sich die Hälfte als Laufwerk NICENANO. Der Bootloader
# selbst wird dabei nie überschrieben -- der Weg zurück bleibt offen,
# auch zu CircuitPython.

import glob
import os
import sys
import time

BEFEHL_BOOTLOADER = 0x0B
HERSTELLER = "4c4b"      # BastardKB, wie in keyboard.toml
PRODUKT = "4643"


def passende_geraete():
    """Alle rohen HID-Schnittstellen dieser Tastatur finden."""
    gefunden = []
    for pfad in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            with open(os.path.join(pfad, "device/uevent")) as f:
                text = f.read()
        except OSError:
            continue
        if ("HID_ID" in text
                and HERSTELLER.upper() in text.upper()
                and PRODUKT.upper() in text.upper()):
            gefunden.append("/dev/" + os.path.basename(pfad))
    return gefunden


def schicke(geraet):
    """Den Befehl auf eine Schnittstelle schreiben.

    Welche der drei die richtige ist, steht nicht im System; die
    falschen antworten einfach nicht. Darum der Reihe nach alle
    versuchen -- ein unbekannter Befehl richtet keinen Schaden an.
    """
    # Erst die Bericht-Nummer 0 -- die verlangt hidraw, wenn das Gerät
    # keine Nummern vergibt, und sie zählt NICHT zur Nutzlast. Danach
    # die vollen 32 Byte, die das Vial-Protokoll erwartet: Befehl,
    # Rest leer. Ein Byte zu wenig, und der Bericht wird stillschweigend
    # verworfen.
    daten = bytes([0x00, BEFEHL_BOOTLOADER]) + bytes(31)
    try:
        fd = os.open(geraet, os.O_RDWR | os.O_NONBLOCK)
    except OSError as f:
        return "nicht zu öffnen (%s)" % f.strerror
    try:
        os.write(fd, daten)
        return "Befehl geschickt"
    except OSError as f:
        return "abgelehnt (%s)" % f.strerror
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def main():
    geraete = passende_geraete()
    if not geraete:
        print("Keine Tastatur gefunden (HID %s:%s)." % (HERSTELLER, PRODUKT),
              file=sys.stderr)
        print("Laeuft die RMK-Firmware? `lsusb | grep -i charybdis`",
              file=sys.stderr)
        sys.exit(1)

    print("Gefunden:", ", ".join(geraete))
    for g in geraete:
        print("  %-16s %s" % (g, schicke(g)))

    print()
    print("Warte auf das Laufwerk NICENANO ...")
    for _ in range(20):
        time.sleep(1)
        laufwerke = glob.glob("/run/media/meo/NICENANO*")
        if laufwerke:
            print("  da:", ", ".join(laufwerke))
            return
    print("  kein Laufwerk erschienen.", file=sys.stderr)
    print("  Dann hilft nur zweimal schnell auf Reset druecken.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
