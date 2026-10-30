#!/usr/bin/env python3
"""Misst, was von der Charybdis wirklich beim Rechner ankommt.

    python3 werkzeuge/messe-takt.py            # 15 s lang messen
    python3 werkzeuge/messe-takt.py 30         # 30 s

Waehrend der Messung: Kugel bewegen, mit gehaltenem W scrollen, ein paar
Tasten tippen. Liest die Linux-Eingabegeraete direkt (Gruppe `input` reicht,
kein root) und beantwortet drei Fragen:

1. Hi-Res-Scrollen aktiv? Seit 16.10.2026 meldet die Firmware das Rad in
   1/120-Rastungen (Resolution Multiplier, rmk hid.rs). Erwartet werden
   REL_WHEEL_HI_RES-Werte, die meist KLEINER als 120 sind.
2. 120-fach-Falle? Hat Linux das Feature-Report nicht setzen koennen, rechnet
   es jede Einheit als ganze Rastung: dann kommen Hi-Res-Werte von 600 und
   mehr pro Ereignis und das Scrollen rast. Das Werkzeug meldet das laut.
3. Funk-Takt: Abstand der Mausberichte. Der kleinste haeufige Abstand ist das
   Verbindungsintervall (Ziel 7,5 ms). Liegt er bei 15 ms oder mehr, hat der
   Rechner das schnelle Intervall abgelehnt.
"""

import os
import select
import struct
import sys
import time

EV_KEY, EV_REL = 0x01, 0x02
REL_X, REL_Y, REL_WHEEL, REL_WHEEL_HI_RES = 0x00, 0x01, 0x08, 0x0B
EREIGNIS = struct.Struct("llHHi")  # struct input_event auf 64 Bit


def geraete():
    """(Name, Pfad) aller Eingabegeraete der Charybdis."""
    funde, name = [], None
    with open("/proc/bus/input/devices") as f:
        for zeile in f:
            if zeile.startswith("N: Name="):
                name = zeile.split("=", 1)[1].strip().strip('"')
            elif zeile.startswith("H: Handlers=") and name and "charybdis" in name.lower():
                for h in zeile.split("=", 1)[1].split():
                    if h.startswith("event"):
                        funde.append((name, "/dev/input/" + h))
    return funde


def main():
    dauer = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    liste = geraete()
    if not liste:
        sys.exit("Keine Charybdis gefunden (weder USB noch Bluetooth verbunden?).")
    offen = {}
    for name, pfad in liste:
        try:
            offen[os.open(pfad, os.O_RDONLY | os.O_NONBLOCK)] = (name, pfad)
        except PermissionError:
            sys.exit(f"Kein Lesezugriff auf {pfad} (Gruppe 'input' fehlt?).")
    print("Lese:", ", ".join(f"{n} ({p})" for n, p in offen.values()))
    print(f"{dauer:.0f} s messen: Kugel bewegen, mit W scrollen, tippen ...")

    bewegung, hires, grob, tasten = [], [], 0, 0
    ende = time.monotonic() + dauer
    while (rest := ende - time.monotonic()) > 0:
        if not offen:
            print("Alle Geraete getrennt, Messung endet frueher.")
            break
        bereit, _, _ = select.select(list(offen), [], [], rest)
        for fd in bereit:
            try:
                daten = os.read(fd, EREIGNIS.size * 64)
            except OSError:  # Verbindung weg (Funk abgerissen, Kabel gezogen)
                print("Getrennt:", offen.pop(fd)[0])
                os.close(fd)
                continue
            for i in range(0, len(daten) - EREIGNIS.size + 1, EREIGNIS.size):
                sek, usek, typ, code, wert = EREIGNIS.unpack_from(daten, i)
                t = sek + usek / 1e6
                if typ == EV_REL and code in (REL_X, REL_Y):
                    if not bewegung or t - bewegung[-1] > 1e-4:  # X und Y eines Berichts zusammen
                        bewegung.append(t)
                elif typ == EV_REL and code == REL_WHEEL_HI_RES:
                    hires.append(wert)
                elif typ == EV_REL and code == REL_WHEEL:
                    grob += abs(wert)
                elif typ == EV_KEY and wert == 1:
                    tasten += 1

    print()
    print(f"Tastenanschlaege: {tasten}")

    # 1 + 2: Scrollen
    if not hires:
        print("Scrollen: keine REL_WHEEL_HI_RES-Ereignisse (nicht gescrollt?).")
    else:
        betraege = sorted(abs(w) for w in hires)
        median = betraege[len(betraege) // 2]
        print(f"Scrollen: {len(hires)} Hi-Res-Ereignisse, Median {median}, "
              f"Maximum {betraege[-1]}, {grob} ganze Rastungen")
        if median >= 600:
            print("  FEHLER: 120-fach-Falle. Linux hat den Multiplikator nicht setzen koennen,")
            print("  jede Einheit zaehlt als ganze Rastung. Bluetooth entkoppeln und neu koppeln;")
            print("  hilft das nicht, Feature-Report-Charakteristik pruefen (rmk ble_server.rs).")
        elif median % 120 == 0:
            print("  Nur ganze Rastungen: Hi-Res ist NICHT aktiv (alte Firmware oder alter")
            print("  Deskriptor im Bluetooth-Zwischenspeicher -> entkoppeln, neu koppeln).")
        else:
            print("  Hi-Res aktiv: Bruchteile einer Rastung kommen an.")

    # 3: Funk-Takt
    abst = [(b - a) * 1000 for a, b in zip(bewegung, bewegung[1:]) if b - a < 0.1]
    if len(abst) < 20:
        print("Takt: zu wenig Mausbewegung gemessen.")
    else:
        abst.sort()
        p10, p50, p90 = (abst[int(len(abst) * q)] for q in (0.1, 0.5, 0.9))
        print(f"Takt der Mausberichte: 10 % {p10:.1f} ms | Median {p50:.1f} ms | 90 % {p90:.1f} ms "
              f"({len(abst)} Abstaende)")
        print("  Ziel: Median um 7,5 ms. Um 15 ms oder mehr: Rechner hat 7,5 ms abgelehnt.")
        print("  (Ueber USB sind kleinere Werte normal; dort gibt es kein Funk-Intervall.)")


if __name__ == "__main__":
    main()
