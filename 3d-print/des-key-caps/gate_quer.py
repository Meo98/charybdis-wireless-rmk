#!/usr/bin/env python3
"""Gate: taugt die Schraeglage in `drucken-quer/` wirklich?

    python3 gate_quer.py
    python3 gate_quer.py --rotnachweis

Geprueft wird die EXPORTIERTE Datei, ohne Blender und ohne Zutun von
`keycaps_querlegen.py`. Die Fingerzone wird hier eigenstaendig bestimmt, nicht
aus dem Build uebernommen -- eine Pruefung, die sich auf die Buchfuehrung des
Erzeugers verlaesst, prueft nichts.

Die Fingerzone
--------------
Die Klassengrenze zwischen Mulde und Schuerze liegt bei 30 Grad Neigung, also
mitten in der Kantenrundung; die Nachbarfacette gehoert schon zur Schuerze.
Gemessen an den fertigen Dateien weicht die Flaeche auf dieser Kante nach dem
Rippen-Boolean bis 272 um ab, 1.5 mm weiter innen unter 1 um. Die Fingerkuppe
liegt im Inneren der Mulde, nicht auf ihrer Abrisskante -- die Gates messen
deshalb die um 1.5 mm eingezogene Mulde, und die Kante bekommt ihr eigenes,
begrenztes Gate.

Die neun Gates
--------------
1. Manifold: 1 Shell, keine offenen oder 4-Flaechen-Kanten, Volumen positiv.
2. Fingerzone unverformt: die Flaeche darf sich nirgends messbar verschoben
   haben. Beweis, dass keine Rippe die Fingerkuppe angefasst hat.
3. Fingerzone stuetzenfrei: nichts steht flacher als 60 Grad zur Waagerechten,
   also stuetzt auch kein Slicer mit Default-Einstellung dort hinein.
   Stuetzmarken auf der Fingerkuppe waeren schlimmer als die Treppe, gegen die
   die ganze Uebung gerichtet ist.
4. Fingerzone ist Wand: sonst koennte die Datei stuetzenfrei und manifold sein
   und trotzdem die alte, rauhe Lage haben.
5. Muldenkante begrenzt: auf der Abrisskante DARF der Boolean wirken, aber nur
   so weit, wie eine Rippenspitze breit ist.
6. Kreuzschlitz unangetastet: die Passung zum Switch darf sich nicht bewegen.
7. Bettauflage: das Floss braucht Flaeche auf dem Bett.
8. Kippsicherheit: Schwerpunkt ueber der Auflage, Fussvolumen im Fenster.
9. Rippen fern der Fingerzone: prueft die eigentliche Zusage. Alle anderen
   Gates koennen gruen sein, waehrend eine Rippe mitten auf der Kuppe sitzt.
"""
import json
import math
import os
import struct
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
AUFRECHT = os.path.join(HIER, "drucken")
LAGEN = os.path.join(HIER, "lagen.json")
ROT = "--rotnachweis" in sys.argv
# Welcher Ordner: `--mit-fuss` prueft die Fassung mit Opferfuss (alle neun
# Gates), sonst die fusslose in `drucken-quer/` (Gates 1-6 unveraendert,
# 7-9 ersetzt -- ohne Fuss gibt es keine Rippen und keine Auflage zu messen,
# dafuer muss das Cap exakt auf dem Bett stehen und sein Volumen darf sich
# durch die Hygiene nicht geaendert haben).
MIT_FUSS = "--mit-fuss" in sys.argv
QUER = os.path.join(HIER, "drucken-quer-mit-fuss" if MIT_FUSS else "drucken-quer")

WAND_OBEN, WAND_UNTEN = 25.0, -45.0   # Fenster wie in lage_suchen.py
# Harte Grenze der Fingerzone, strenger als WAND_UNTEN: -30 Grad Normalen-
# neigung = mindestens 60 Grad Flaechenneigung gegen die Waagerechte. Darunter
# setzen gaengige Slicer per Default Stuetzen -- PrusaSlicer stuetzt alles
# flacher als 55 Grad. Die Zusage soll ohne Sondereinstellung gelten.
STUETZ_GRENZE = -30.0
MULDE_AB = 30.0
ZELLE = 0.30
FINGERZONE_RAND = 1.50
SUCHE = 0.50                          # Rasterweite der Nachbarschaftssuche

# Aus dem Build; hier bewusst wiederholt statt importiert.
FLOSS_DICKE, LUFTSPALT = 0.80, 0.40
RIPPE_SPITZE = 0.70

SHELLS_SOLL = 1                 # genau ein Koerper
FINGER_ABWEICHUNG_MAX = 0.005   # mm -- gemessen 0.000 bis 0.001
KANTE_ABWEICHUNG_MAX = 0.350    # mm -- halbe Rippenspitze plus Reserve
STAMM_ABWEICHUNG_MAX = 0.005
FINGER_STUETZE_MAX = 0.0        # mm2, hart
FINGER_WAND_MIN = 90.0          # Prozent
AUFLAGE_MIN = 60.0              # mm2
KIPPRAND_MIN = 2.00             # mm
FUSS_VOLUMEN = (200.0, 560.0)   # mm3 -- gemessen 247 bis 499
RIPPE_FINGER_MIN = 1.20         # mm
BETT_MAX = 0.002                # mm -- tiefster Punkt auf z = 0 (ohne Fuss)
VOLUMEN_ABW_MAX = 0.0001        # Anteil -- Hygiene darf die Form nicht aendern

if ROT:                         # absichtlich unerfuellbare Fenster
    # Negative Schwellen, nicht 0.0: bei 0.0 haengt das Rotwerden daran, ob der
    # Messwert exakt 0 trifft -- dann waere der Nachweis ein Zufall.
    SHELLS_SOLL = 2
    FINGER_ABWEICHUNG_MAX = -1.0
    KANTE_ABWEICHUNG_MAX = -1.0
    STAMM_ABWEICHUNG_MAX = -1.0
    FINGER_STUETZE_MAX = -1.0
    FINGER_WAND_MIN = 100.001
    AUFLAGE_MIN = 10_000.0
    KIPPRAND_MIN = 50.0
    FUSS_VOLUMEN = (10_000.0, 20_000.0)
    RIPPE_FINGER_MIN = 50.0
    BETT_MAX = -1.0
    VOLUMEN_ABW_MAX = -1.0


# --------------------------------------------------------------------- STL

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


def geometrie(rohdreiecke):
    """(Normale, Flaeche, Schwerpunkt, Ecken) je Dreieck, entartete weg."""
    raus = []
    for v in rohdreiecke:
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
                (a, b, c),
            )
        )
    return raus


def volumen_und_schwerpunkt(geo):
    """Divergenzsatz -- nicht der Bbox-Mittelpunkt. DES-Caps haengen schief."""
    vol = sx = sy = sz = 0.0
    for _, _, _, (a, b, c) in geo:
        d = (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0
        vol += d
        sx += (a[0] + b[0] + c[0]) / 4.0 * d
        sy += (a[1] + b[1] + c[1]) / 4.0 * d
        sz += (a[2] + b[2] + c[2]) / 4.0 * d
    return vol, (sx / vol, sy / vol, sz / vol)


# ------------------------------------------------------- Lage nachvollziehen

def drehmatrix(polar, azimut):
    """Dieselbe Drehung wie im Build: die gewaehlte Richtung wandert auf +Z.

    Der Build benutzt `Vector.rotation_difference` -- die kuerzeste Drehung.
    Hier als Achse-Winkel-Matrix nachgebaut, damit das Gate ohne Blender laeuft.
    """
    t, p = math.radians(polar), math.radians(azimut)
    u = (math.sin(t) * math.cos(p), math.sin(t) * math.sin(p), math.cos(t))
    achse = (u[1], -u[0], 0.0)          # u x (0,0,1)
    laenge = math.hypot(achse[0], achse[1])
    kosinus = max(-1.0, min(1.0, u[2]))
    if laenge < 1e-12:
        return ((1, 0, 0), (0, 1, 0), (0, 0, 1)) if kosinus > 0 else \
               ((1, 0, 0), (0, -1, 0), (0, 0, -1))
    x, y, z = achse[0] / laenge, achse[1] / laenge, 0.0
    winkel = math.acos(kosinus)
    s, c = math.sin(winkel), math.cos(winkel)
    return (
        (c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s),
        (y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s),
        (z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)),
    )


def dreh(M, v):
    return tuple(sum(M[r][k] * v[k] for k in range(3)) for r in range(3))


def in_drucklage(auf_geo, polar, azimut):
    """Die aufrechte Geometrie in die Drucklage bringen -- wie im Build."""
    M = drehmatrix(polar, azimut)
    gedreht = [
        (dreh(M, n), f, dreh(M, s), tuple(dreh(M, p) for p in e))
        for n, f, s, e in auf_geo
    ]
    xs = [p[0] for _, _, _, e in gedreht for p in e]
    ys = [p[1] for _, _, _, e in gedreht for p in e]
    zs = [p[2] for _, _, _, e in gedreht for p in e]
    versatz = (
        -(max(xs) + min(xs)) / 2.0,
        -(max(ys) + min(ys)) / 2.0,
        ((FLOSS_DICKE + LUFTSPALT) if MIT_FUSS else 0.0) - min(zs),
    )
    return [
        (
            n,
            f,
            tuple(s[i] + versatz[i] for i in range(3)),
            tuple(tuple(p[i] + versatz[i] for i in range(3)) for p in e),
        )
        for n, f, s, e in gedreht
    ]


def klassen(geo):
    """mulde / schuerze / boden / innen -- in der aufrechten Lage.

    Dort ist die Aussenhaut ein Hoehenfeld z = f(x,y): an jeder XY-Stelle ist
    sie das Oberste. Nach dem Drehen waere die Trennung nicht mehr moeglich.
    """
    oben = {}
    for _, _, s, _ in geo:
        k = (int(s[0] // ZELLE), int(s[1] // ZELLE))
        if s[2] > oben.get(k, -1e9):
            oben[k] = s[2]
    raus = []
    for n, _, s, _ in geo:
        k = (int(s[0] // ZELLE), int(s[1] // ZELLE))
        if n[2] > 0.02 and s[2] >= oben[k] - 0.35:
            raus.append(
                "mulde"
                if math.degrees(math.asin(min(1.0, n[2]))) >= MULDE_AB
                else "schuerze"
            )
        elif n[2] <= -0.02 and s[2] <= 0.9:
            raus.append("boden")
        else:
            raus.append("innen")
    return raus


def nachbarsuche(punkte, weite=1.0):
    """Abstandsfunktion zur naechsten Stelle einer Punktwolke."""
    raster = {}
    for p in punkte:
        raster.setdefault(tuple(int(p[i] // weite) for i in range(3)), []).append(p)

    def abstand(q):
        best = 1e9
        kq = tuple(int(q[i] // weite) for i in range(3))
        for ring in range(0, 6):
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    for dz in range(-ring, ring + 1):
                        if max(abs(dx), abs(dy), abs(dz)) != ring:
                            continue
                        for p in raster.get(
                            (kq[0] + dx, kq[1] + dy, kq[2] + dz), ()
                        ):
                            d = math.dist(q, p)
                            if d < best:
                                best = d
            if best <= ring * weite:
                break
        return best

    return abstand


# ------------------------------------------------------- Abstandsrechnungen

def punkt_dreieck_abstand(punkt, ecken):
    """Kuerzester Abstand Punkt zu Dreieck im Raum.

    Der Ebenenabstand genuegt nicht: am Rand einer Facette liegt der naechste
    Punkt auf einer Kante, nicht in der Ebene.
    """
    a, b, c = ecken
    e0 = tuple(b[i] - a[i] for i in range(3))
    e1 = tuple(c[i] - a[i] for i in range(3))
    d = tuple(a[i] - punkt[i] for i in range(3))
    aa = sum(e0[i] * e0[i] for i in range(3))
    ab = sum(e0[i] * e1[i] for i in range(3))
    bb = sum(e1[i] * e1[i] for i in range(3))
    ad = sum(e0[i] * d[i] for i in range(3))
    bd = sum(e1[i] * d[i] for i in range(3))
    dd = sum(d[i] * d[i] for i in range(3))
    det = aa * bb - ab * ab
    s_, t_ = ab * bd - bb * ad, ab * ad - aa * bd
    if det <= 1e-20:
        return math.sqrt(max(0.0, dd))
    if s_ + t_ <= det:
        if s_ < 0.0:
            s_, t_ = (
                (min(max(-ad / aa, 0.0), 1.0), 0.0)
                if t_ < 0.0 and ad < 0.0
                else (0.0, min(max(-bd / bb, 0.0), 1.0))
            )
        elif t_ < 0.0:
            s_, t_ = min(max(-ad / aa, 0.0), 1.0), 0.0
        else:
            s_, t_ = s_ / det, t_ / det
    else:
        if s_ < 0.0:
            s_, t_ = 0.0, min(max(-bd / bb, 0.0), 1.0)
        elif t_ < 0.0:
            s_, t_ = min(max(-ad / aa, 0.0), 1.0), 0.0
        else:
            nenner = aa - 2.0 * ab + bb
            s_ = min(max((bb + bd - ab - ad) / nenner, 0.0), 1.0) if nenner > 1e-20 else 0.0
            t_ = 1.0 - s_
    quadrat = (
        dd + s_ * (aa * s_ + 2.0 * ad) + t_ * (bb * t_ + 2.0 * bd) + 2.0 * s_ * t_ * ab
    )
    return math.sqrt(max(0.0, quadrat))


def raster_bauen(ziel_geo):
    """Zielfacetten in jede Rasterzelle eintragen, die ihre Bbox beruehrt.

    Nicht nach Schwerpunkt einsortieren: der Boolean verschmilzt koplanare
    Dreiecke, der Schwerpunkt der verschmolzenen Facette liegt dann weit weg
    von dem der urspruenglichen -- eine Schwerpunktsuche verfehlt sie.
    """
    raster = {}
    for _, _, _, ecken in ziel_geo:
        for kx in range(
            int(min(p[0] for p in ecken) // SUCHE),
            int(max(p[0] for p in ecken) // SUCHE) + 1,
        ):
            for ky in range(
                int(min(p[1] for p in ecken) // SUCHE),
                int(max(p[1] for p in ecken) // SUCHE) + 1,
            ):
                for kz in range(
                    int(min(p[2] for p in ecken) // SUCHE),
                    int(max(p[2] for p in ecken) // SUCHE) + 1,
                ):
                    raster.setdefault((kx, ky, kz), []).append(ecken)
    return raster


def abweichung(proben, raster):
    """Wie weit wandert die Zielflaeche an den Probenpunkten?

    Erst die eigene Rasterzelle, Abbruch sobald ein Treffer unter 1 um liegt --
    der Normalfall ist eine unveraenderte Facette. Der wachsende Suchring
    greift nur dort, wo die Hygiene-Kette umtrianguliert hat.
    """
    schlimmster = 0.0
    for _, _, s, _ in proben:
        k = tuple(int(s[i] // SUCHE) for i in range(3))
        best = None
        for ecken in raster.get(k, ()):
            dist = punkt_dreieck_abstand(s, ecken)
            if best is None or dist < best:
                best = dist
                if best < 1e-6:
                    break
        ring = 1
        while (best is None or best > 1e-6) and ring <= 5:
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    for dz in range(-ring, ring + 1):
                        if max(abs(dx), abs(dy), abs(dz)) != ring:
                            continue
                        for ecken in raster.get(
                            (k[0] + dx, k[1] + dy, k[2] + dz), ()
                        ):
                            dist = punkt_dreieck_abstand(s, ecken)
                            if best is None or dist < best:
                                best = dist
            if best is not None and best <= ring * SUCHE:
                break
            ring += 1
        if best is None:
            return 99.0
        schlimmster = max(schlimmster, best)
    return schlimmster


def abstand_rippen(rippen, flaechen):
    """Abstand der naechsten Rippenspitze zu einer Flaechengruppe.

    Vorauswahl ueber den Schwerpunktabstand; eine Facette ist deutlich kleiner
    als 1 mm, die Vorauswahl kann das Ergebnis nicht verfehlen.
    """
    if not rippen or not flaechen:
        return -1.0
    best = 1e9
    for rippe in rippen:
        nah = sorted(
            flaechen,
            key=lambda g: sum((g[2][i] - rippe[i]) ** 2 for i in range(3)),
        )[:120]
        for _, _, _, ecken in nah:
            best = min(best, punkt_dreieck_abstand(rippe, ecken))
    return best


# ------------------------------------------------------------- Kleinwerkzeug

def hull(punkte):
    punkte = sorted(set(punkte))
    if len(punkte) < 3:
        return punkte

    def haelfte(folge):
        h = []
        for p in folge:
            while len(h) >= 2:
                (x1, y1), (x2, y2) = h[-2], h[-1]
                if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) > 0:
                    break
                h.pop()
            h.append(p)
        return h

    return haelfte(punkte)[:-1] + haelfte(punkte[::-1])[:-1]


def rand_abstand(huelle, punkt):
    if len(huelle) < 3:
        return -99.0
    best = 1e9
    for i in range(len(huelle)):
        a, b = huelle[i], huelle[(i + 1) % len(huelle)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        laenge = math.hypot(ex, ey)
        if laenge < 1e-9:
            continue
        best = min(best, (ex * (punkt[1] - a[1]) - ey * (punkt[0] - a[0])) / laenge)
    return best


def kanten_bericht(rohdreiecke):
    """Shells, offene und 4-Flaechen-Kanten direkt aus der Datei."""
    index, kanten = {}, {}
    for nr, v in enumerate(rohdreiecke):
        ecken = []
        for p in (v[0:3], v[3:6], v[6:9]):
            ecken.append(
                index.setdefault((round(p[0], 4), round(p[1], 4), round(p[2], 4)),
                                 len(index))
            )
        for i in range(3):
            kanten.setdefault(
                tuple(sorted((ecken[i], ecken[(i + 1) % 3]))), []
            ).append(nr)
    eltern = list(range(len(index)))

    def finde(x):
        while eltern[x] != x:
            eltern[x] = eltern[eltern[x]]
            x = eltern[x]
        return x

    for u, v in kanten:
        ru, rv = finde(u), finde(v)
        if ru != rv:
            eltern[ru] = rv
    return (
        len({finde(i) for i in range(len(index))}),
        sum(1 for v in kanten.values() if len(v) == 1),
        sum(1 for v in kanten.values() if len(v) > 2),
    )


def neigung(normale):
    """Winkel der Normalen gegen die Waagerechte. +90 = zeigt nach oben."""
    return math.degrees(math.asin(max(-1.0, min(1.0, normale[2]))))


# -------------------------------------------------------------------- Gates

def pruefe(name, polar, azimut):
    auf_geo = geometrie(lade(os.path.join(AUFRECHT, name + ".stl")))
    kl = klassen(auf_geo)
    roh_quer = lade(os.path.join(QUER, name + ".stl"))
    quer_geo = geometrie(roh_quer)
    gedreht = in_drucklage(auf_geo, polar, azimut)

    mulde = [g for g, k in zip(gedreht, kl) if k == "mulde"]
    schuerze = [g for g, k in zip(gedreht, kl) if k == "schuerze"]
    stamm = [
        g
        for g, (_, _, s, _) in zip(gedreht, auf_geo)
        if abs(s[0]) < 3.4 and abs(s[1]) < 3.4 and s[2] < 6.5
    ]
    kantenabstand = nachbarsuche([s for _, _, s, _ in schuerze])
    finger = [g for g in mulde if kantenabstand(g[2]) >= FINGERZONE_RAND]
    kante = [g for g in mulde if kantenabstand(g[2]) < FINGERZONE_RAND]
    finger_flaeche = sum(f for _, f, _, _ in finger)

    raster = raster_bauen(quer_geo)
    quer_vol, schwerpunkt = volumen_und_schwerpunkt(quer_geo)
    rippen = [
        (r["x"], r["y"], r["z"])
        for r in json.load(open(os.path.join(QUER, "fuss-bericht.json")))[name]["rippen"]
    ] if MIT_FUSS else []

    zmin = min(p[2] for _, _, _, e in quer_geo for p in e)
    auflage, fusspunkte = 0.0, []
    for n, f, _, e in quer_geo:
        if max(p[2] for p in e) - zmin < 0.15 and n[2] < -0.9:
            auflage += f
            fusspunkte += [(round(p[0], 2), round(p[1], 2)) for p in e]

    shells, offen, viel = kanten_bericht(roh_quer)
    finger_stuetze = sum(f for n, f, _, _ in finger if neigung(n) < STUETZ_GRENZE)
    finger_wand = sum(
        f for n, f, _, _ in finger if WAND_UNTEN <= neigung(n) < WAND_OBEN
    )
    auf_vol = volumen_und_schwerpunkt(auf_geo)[0]
    fuss_vol = quer_vol - auf_vol
    kipprand = rand_abstand(hull(fusspunkte), schwerpunkt[:2])
    vol_abw = abs(quer_vol - auf_vol) / auf_vol

    gemeinsam = [
        ("1 Manifold",
         f"{shells} Shell, {offen} offen, {viel} vierfach, Vol {quer_vol:.1f} mm3",
         shells == SHELLS_SOLL and offen == 0 and viel == 0 and quer_vol > 0),
        ("2 Fingerzone unverformt",
         f"max {abweichung(finger, raster) * 1000:.1f} um ({len(finger)} Proben, "
         f"{finger_flaeche:.0f} mm2)",
         abweichung(finger, raster) <= FINGER_ABWEICHUNG_MAX),
        ("3 Fingerzone stuetzenfrei",
         f"{finger_stuetze:.4f} mm2 flacher als 60 Grad zur Waagerechten",
         finger_stuetze <= FINGER_STUETZE_MAX),
        ("4 Fingerzone ist Wand",
         f"{100.0 * finger_wand / finger_flaeche:.1f}%",
         100.0 * finger_wand / finger_flaeche >= FINGER_WAND_MIN),
        ("5 Muldenkante begrenzt",
         f"max {abweichung(kante, raster) * 1000:.0f} um ({len(kante)} Proben)",
         abweichung(kante, raster) <= KANTE_ABWEICHUNG_MAX),
        ("6 Kreuzschlitz heil",
         f"max {abweichung(stamm, raster) * 1000:.1f} um ({len(stamm)} Proben)",
         abweichung(stamm, raster) <= STAMM_ABWEICHUNG_MAX),
    ]
    if not MIT_FUSS:
        return gemeinsam + [
            ("7 steht auf dem Bett", f"tiefster Punkt z = {zmin:+.4f} mm", abs(zmin) <= BETT_MAX),
            ("8 Volumen unveraendert",
             f"{quer_vol:.2f} mm3 quer, {auf_vol:.2f} aufrecht ({vol_abw * 100:.4f} %)",
             vol_abw <= VOLUMEN_ABW_MAX),
            ("9 Auflage (nur Info)",
             f"{auflage:.2f} mm2 -- Stuetzen setzt der Slicer, kein Fenster", True if not ROT else False),
        ]
    return gemeinsam + [
        ("7 Bettauflage", f"{auflage:.1f} mm2", auflage >= AUFLAGE_MIN),
        ("8 Kippsicherheit",
         f"Schwerpunkt {kipprand:+.2f} mm innen, Fuss {fuss_vol:.1f} mm3",
         kipprand >= KIPPRAND_MIN and FUSS_VOLUMEN[0] <= fuss_vol <= FUSS_VOLUMEN[1]),
        ("9 Rippen fern der Kuppe",
         f"naechste Rippe {abstand_rippen(rippen, finger):.2f} mm von der Fingerzone",
         abstand_rippen(rippen, finger) >= RIPPE_FINGER_MIN),
    ]


def main():
    lagen = json.load(open(LAGEN))
    if ROT:
        print("ROT-NACHWEIS: alle Fenster sind absichtlich unerfuellbar.")
        print("Wird hier irgendetwas gruen, prueft dieses Gate nichts.\n")
    alles_gut = True
    for name in sorted(lagen):
        print(f"=== {name} ===")
        for gate, text, gut in pruefe(name, *lagen[name]):
            print(f"  {'OK ' if gut else 'ROT'}  {gate:<26} {text}")
            alles_gut = alles_gut and gut
        print()
    if ROT:
        if alles_gut:
            print("ROT-NACHWEIS GESCHEITERT: ein Gate kann nicht rot werden.")
            sys.exit(1)
        print("Rot-Nachweis bestanden.")
        sys.exit(0)
    print("Alle Gates gruen." if alles_gut else "MINDESTENS EIN GATE IST ROT.")
    sys.exit(0 if alles_gut else 1)


if __name__ == "__main__":
    main()
