#!/usr/bin/env python3
"""Sucht fuer jedes Cap die Drucklage, in der die Fingerflaeche glatt wird.

    python3 lage_suchen.py            # Tabelle + schreibt lagen.json
    python3 lage_suchen.py --fein     # feineres Raster (langsamer)

Hintergrund
-----------
Beim FDM ist eine Flaeche genau dann glatt, wenn sie als Wandperimeter
gedruckt wird. Liegt sie flacher als etwa 25 Grad, behandelt der Slicer sie
als Deckflaeche und fuellt sie mit Infill-Linien; dazwischen bleibt die
Treppe mit der Stufenbreite h/tan(alpha). In der aufrechten Lage ist die
DES-Mulde zu 59-84 Prozent Deckflaeche -- deshalb fuehlt sie sich rauh an.

Gesucht wird die Richtung, die nach dem Drehen "oben" sein soll, so dass
moeglichst viel Muldenflaeche in das Wandfenster faellt. Harte Nebenbedingung:
die Mulde darf KEINE Stuetzen brauchen. Stuetzmarken auf der Fingerkuppe
waeren schlimmer als die Treppe, die wir loswerden wollen.

Laufzeit
--------
Die rund 13000 Muldennormalen werden einmal in ein Richtungs-Histogramm
einsortiert. Danach kostet jede Probelage nur noch so viele Rechenschritte,
wie das Histogramm Faecher hat -- aus 13000 werden ~500.
"""
import json
import math
import os
import struct
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE = os.path.join(HIER, "drucken")
LAGEN = os.path.join(HIER, "lagen.json")

# Fenster, mit denen der Slicer eine Flaeche einordnet (Grad gegen die Waagerechte
# der Normalen, +90 = zeigt senkrecht nach oben).
WAND_OBEN = 25.0     # darueber: Deckflaeche oder Treppe
WAND_UNTEN = -45.0   # darunter: Ueberhang, braucht Stuetze

# Harte Grenze fuer die Fingerzone. Strenger als WAND_UNTEN, und zwar aus
# einem praktischen Grund: -45 Grad Normalenneigung heisst 45 Grad Flaechen-
# neigung gegen die Waagerechte, und dort setzen gaengige Slicer schon
# Stuetzen (PrusaSlicer stuetzt per Default alles unter 55 Grad Neigung).
# Eine Datei, die nur mit umgestellter Slicer-Einstellung haelt, ist fragil.
# -30 Grad Normalenneigung = mindestens 60 Grad Flaechenneigung -- das bleibt
# unter jedem gaengigen Default stuetzenfrei. Gemessen kostet es 1 bis 2
# Prozentpunkte Wandflaeche, bei den Daumencaps gar nichts.
STUETZ_GRENZE = -30.0
MULDE_AB = 30.0      # Aussenhaut steiler als das zaehlt als Mulde, nicht Schuerze

ZELLE = 0.30         # XY-Raster fuer die Hoehenfeld-Trennung
HISTO_SCHRITT = 3.0  # Winkelaufloesung des Richtungs-Histogramms
FINGERZONE_RAND = 1.50  # Abstand von der Schuerzenkante -- siehe unten
FEINPROBEN = 40      # so viele Histogramm-Treffer werden exakt nachgerechnet


def lade(pfad):
    with open(pfad, "rb") as f:
        rohdaten = f.read()
    anzahl = struct.unpack("<I", rohdaten[80:84])[0]
    if 84 + anzahl * 50 != len(rohdaten):
        sys.exit(f"{pfad}: keine binaere STL")
    return [
        struct.unpack("<12f", rohdaten[84 + i * 50 : 84 + i * 50 + 48])[3:12]
        for i in range(anzahl)
    ]


def facetten(pfad):
    """(Normale, Flaeche, Schwerpunkt) je Dreieck."""
    raus = []
    for v in lade(pfad):
        a, b, c = v[0:3], v[3:6], v[6:9]
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        laenge = math.sqrt(nx * nx + ny * ny + nz * nz)
        if laenge == 0.0:
            continue
        raus.append(
            (
                (nx / laenge, ny / laenge, nz / laenge),
                laenge / 2.0,
                tuple((a[k] + b[k] + c[k]) / 3.0 for k in range(3)),
            )
        )
    return raus


def aussenhaut(pfad):
    """Die Fingerflaeche allein -- Schuerze, Hohlraum und Stamm bleiben draussen.

    In der aufrechten Lage ist die Aussenhaut ein Hoehenfeld z = f(x,y): an
    jeder XY-Stelle ist sie das Oberste. Damit laesst sie sich ohne Raytracing
    vom Rest trennen. Die Schuerze wird danach per Neigung abgetrennt -- sie
    zeigt leicht nach oben, weil sie sich nach oben verjuengt.
    """
    alle = facetten(pfad)
    oben = {}
    for _, _, schwer in alle:
        schluessel = (int(schwer[0] // ZELLE), int(schwer[1] // ZELLE))
        if schwer[2] > oben.get(schluessel, -1e9):
            oben[schluessel] = schwer[2]
    mulde, schuerze = [], []
    for normale, flaeche, schwer in alle:
        if normale[2] <= 0.02:
            continue
        schluessel = (int(schwer[0] // ZELLE), int(schwer[1] // ZELLE))
        if schwer[2] < oben[schluessel] - 0.35:
            continue
        if math.degrees(math.asin(min(1.0, normale[2]))) >= MULDE_AB:
            mulde.append((normale, flaeche, schwer))
        else:
            schuerze.append((normale, flaeche, schwer))
    return mulde, schuerze


def fingerzone(mulde, schuerze):
    """Die Mulde ohne ihren aeussersten Rand.

    Die Klassengrenze zwischen Mulde und Schuerze liegt bei 30 Grad Neigung,
    also mitten in der Kantenrundung. Die Facette direkt daneben gehoert schon
    zur Schuerze -- ein Unterschied von einer Facettenbreite. Fuer die Frage
    "fuehlt sich das gut an" ist dieser Saum uninteressant: die Fingerkuppe
    liegt im Inneren der Mulde, nicht auf ihrer Abrisskante.

    Ohne diese Unterscheidung messen beide Gates die falsche Flaeche. Gemessen:
    auf der Kante weicht die Flaeche nach dem Rippen-Boolean bis 272 um ab, in
    der Fingerzone unter 1 um.
    """
    raster = {}
    for _, _, schwer in schuerze:
        k = tuple(int(schwer[i] // 1.0) for i in range(3))
        raster.setdefault(k, []).append(schwer)

    def kantenabstand(punkt):
        best = 1e9
        kx, ky, kz = (int(punkt[i] // 1.0) for i in range(3))
        for ring in range(0, 5):
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    for dz in range(-ring, ring + 1):
                        if max(abs(dx), abs(dy), abs(dz)) != ring:
                            continue
                        for s in raster.get((kx + dx, ky + dy, kz + dz), ()):
                            d = math.dist(punkt, s)
                            if d < best:
                                best = d
            if best <= ring:
                break
        return best

    return [
        (normale, flaeche)
        for normale, flaeche, schwer in mulde
        if kantenabstand(schwer) >= FINGERZONE_RAND
    ]


def histogramm(flaechen):
    """Normalen nach Richtung buendeln, Flaechen aufsummieren."""
    faecher = {}
    for normale, flaeche in flaechen:
        polar = math.degrees(math.acos(max(-1.0, min(1.0, normale[2]))))
        azimut = math.degrees(math.atan2(normale[1], normale[0])) % 360.0
        schluessel = (int(polar / HISTO_SCHRITT), int(azimut / HISTO_SCHRITT))
        if schluessel not in faecher:
            t = math.radians((schluessel[0] + 0.5) * HISTO_SCHRITT)
            p = math.radians((schluessel[1] + 0.5) * HISTO_SCHRITT)
            faecher[schluessel] = [
                (math.sin(t) * math.cos(p), math.sin(t) * math.sin(p), math.cos(t)),
                0.0,
            ]
        faecher[schluessel][1] += flaeche
    return list(faecher.values())


def bewerte(faecher, oben_richtung, gesamt):
    """Flaechenanteile: Wand (glatt) / Deckflaeche+Treppe (rauh) / Stuetze."""
    wand = rauh = stuetze = 0.0
    for normale, flaeche in faecher:
        punkt = (
            normale[0] * oben_richtung[0]
            + normale[1] * oben_richtung[1]
            + normale[2] * oben_richtung[2]
        )
        winkel = math.degrees(math.asin(max(-1.0, min(1.0, punkt))))
        if winkel >= WAND_OBEN:
            rauh += flaeche
        elif winkel >= WAND_UNTEN:
            wand += flaeche
        else:
            stuetze += flaeche
    return (
        100.0 * wand / gesamt,
        100.0 * rauh / gesamt,
        100.0 * stuetze / gesamt,
    )


def suche(pfad, fein=False):
    """Zwei Stufen: grob ueber das Histogramm, dann exakt ueber die Facetten.

    Die erste Fassung hat die harte Nebenbedingung AUF DEM HISTOGRAMM
    geprueft -- also auf gebuendelten Normalen, vertreten durch die
    Faechermitte. Die echten Facetten streuen innerhalb eines 3-Grad-Fachs,
    und ein paar davon kippen ueber die 45-Grad-Grenze. Die Suche meldete
    "0.00 Prozent stuetzenfrei", das Gate hinterher 0.05 bis 0.49 mm2. Das
    Histogramm darf deshalb nur noch vorsortieren; entschieden wird exakt.
    """
    mulde_flaechen, schuerze = aussenhaut(pfad)
    finger = fingerzone(mulde_flaechen, schuerze)
    mulde_paare = [(n, f) for n, f, _ in mulde_flaechen]
    gesamt = sum(f for _, f in mulde_paare)
    gesamt_finger = sum(f for _, f in finger)
    faecher = histogramm(mulde_paare)
    d_polar, d_azimut = (1, 2) if fein else (2, 5)

    grob = []
    for polar in range(0, 181, d_polar):
        t = math.radians(polar)
        for azimut in range(0, 360, d_azimut):
            p = math.radians(azimut)
            richtung = (
                math.sin(t) * math.cos(p),
                math.sin(t) * math.sin(p),
                math.cos(t),
            )
            wand, _, stuetze = bewerte(faecher, richtung, gesamt)
            if stuetze < 0.05:
                grob.append((wand, polar, azimut))
    if not grob:
        sys.exit(f"{pfad}: nicht einmal grob eine stuetzenfreie Lage gefunden")
    grob.sort(reverse=True)

    # Feinsuche: die besten Grobtreffer plus ein Grad-Umfeld, exakt gerechnet
    kandidaten = set()
    for _, polar, azimut in grob[:FEINPROBEN]:
        for dp in (-2, -1, 0, 1, 2):
            for da in (-4, -2, 0, 2, 4):
                kandidaten.add((max(0, min(180, polar + dp)), (azimut + da) % 360))

    beste = None
    for polar, azimut in sorted(kandidaten):
        t, p = math.radians(polar), math.radians(azimut)
        richtung = (
            math.sin(t) * math.cos(p),
            math.sin(t) * math.sin(p),
            math.cos(t),
        )
        wand, rauh, stuetze = bewerte(mulde_paare, richtung, gesamt)
        stuetze_finger = 0.0
        for normale, flaeche in finger:
            punkt = sum(normale[i] * richtung[i] for i in range(3))
            if math.degrees(math.asin(max(-1.0, min(1.0, punkt)))) < STUETZ_GRENZE:
                stuetze_finger += flaeche
        stuetze_finger = 100.0 * stuetze_finger / gesamt_finger
        if stuetze_finger > 0.0:         # harte Nebenbedingung, exakt
            continue
        if beste is None or wand > beste[0]:
            beste = (wand, rauh, stuetze, polar, azimut, stuetze_finger)
    if beste is None:
        sys.exit(f"{pfad}: keine exakt stuetzenfreie Fingerzone gefunden")
    return gesamt, gesamt_finger, beste


def main():
    fein = "--fein" in sys.argv
    dateien = sorted(
        f for f in os.listdir(QUELLE) if f.endswith(".stl")
    )
    lagen = {}
    print(f"{'Datei':<22} {'Mulde':>8} {'Finger':>8} {'Kippung':>8} {'Richtung':>9} "
          f"{'Wand':>7} {'rauh':>7} {'Stuetze':>8} {'Finger<60':>11}")
    for datei in dateien:
        name = datei[:-4]
        gesamt, gesamt_finger, (wand, rauh, stuetze, polar, azimut, st_finger) = suche(
            os.path.join(QUELLE, datei), fein
        )
        lagen[name] = [polar, azimut]
        print(f"{name:<22} {gesamt:7.1f}mm2 {gesamt_finger:7.1f}mm2 "
              f"{polar:7d}deg {azimut:8d}deg {wand:6.1f}% {rauh:6.1f}% "
              f"{stuetze:7.2f}% {st_finger:10.2f}%")
    with open(LAGEN, "w") as f:
        json.dump(lagen, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"\ngeschrieben: {LAGEN}")
    print("Zum Vergleich -- aufrecht ist die Mulde 0% Wand und 59-84% Deckflaeche.")


if __name__ == "__main__":
    main()
