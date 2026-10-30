#!/usr/bin/env python3
"""Legt die DES-Caps in die Schraeglage und setzt ihnen einen Opferfuss an.

    blender -b --factory-startup -noaudio -P keycaps_querlegen.py              # ohne Fuss
    QUER_FUSS=1 blender -b --factory-startup -noaudio -P keycaps_querlegen.py   # mit Opferfuss

Liest `drucken/` und `lagen.json`.
  ohne Fuss  -> `drucken-quer/`           Cap in Schraeglage, tiefster Punkt auf dem Bett.
                                          Stuetzen macht der Slicer (Bambu Studio).
  mit Fuss   -> `drucken-quer-mit-fuss/`  wie bisher: Floss + abknipsbare Rippen im Modell.

Seit 14.10.2026 ist OHNE Fuss der Normalfall: Bambu Studio setzt die Stuetzen
selbst besser (baumfoermig, abloesbar), und 810 Rippen abzuknipsen entfaellt.
Der Fuss bleibt als Betriebsart erhalten, weil seine Gates (Rippen fern der
Fingerkuppe) viel Pruefarbeit enthalten.

Warum ueberhaupt
----------------
Aufrecht wird die Mulde als Deckflaeche gedruckt: 59-84 Prozent der
Fingerflaeche bekommen Infill-Linien, der Rest Treppenstufen von 0.63 mm bei
0.2 mm Schichthoehe. In der von `lage_suchen.py` ermittelten Schraeglage sind
91-99 Prozent der Mulde Wandperimeter -- und kein einziges Quadratmillimeter
braucht Stuetzen.

Warum ein angedruckter Fuss und keine Slicer-Stuetzen
-----------------------------------------------------
In Schraeglage faellt die Bettauflage von 98.7 mm2 auf 0.06-4.1 mm2. Das Cap
steht nicht mehr, es balanciert. Ueberlaesst man das dem Slicer, baut der
unter jedes der 126 Caps einen Turm und entscheidet selbst, wo er anfasst --
jedes Mal anders, und moeglicherweise auf der Mulde. Der Fuss ist Teil des
Modells: gleiche Kontaktpunkte bei jedem Druck, und `gate_quer.py` kann
nachrechnen, dass sie die Fingerflaeche nicht beruehren.

Wo der Fuss anfassen darf
-------------------------
Nur am Bodenring (sitzt spaeter unsichtbar auf dem Switch) und an der
Schuerze. Niemals an der Mulde. Zusaetzlich muss jeder Ankerpunkt der
TIEFSTE Punkt seiner Senkrechten sein -- sonst stiesse die Rippe unterwegs
durch anderes Cap-Material und waere nicht mehr abbrechbar.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

sys.path.append("/home/meo/.claude/skills/blender-headless-build/scripts")
import bl_hygiene as H  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE = os.path.join(HIER, "drucken")
LAGEN = os.path.join(HIER, "lagen.json")
# Betriebsart: Opferfuss nur auf ausdruecklichen Wunsch (QUER_FUSS=1).
MIT_FUSS = os.environ.get("QUER_FUSS", "0") == "1"
ZIEL = os.path.join(HIER, "drucken-quer-mit-fuss" if MIT_FUSS else "drucken-quer")
BERICHT = os.path.join(ZIEL, "fuss-bericht.json" if MIT_FUSS else "lage-bericht.json")

FLOSS_DICKE = 0.80       # Floss auf dem Bett, 4 Lagen bei 0.2 mm
FLOSS_RAND = 1.00        # Ueberstand ueber Grundriss und Rippenfuesse
LUFTSPALT = 0.40         # zwischen Flossoberseite und tiefstem Cap-Punkt
RIPPE_FUSS = 1.40        # Rippenquerschnitt am Floss
RIPPE_SPITZE = 0.70      # am Cap -- das ist die Sollbruchstelle, 0.49 mm2
# Eintauchtiefe SENKRECHT ZUR OBERFLAECHE, nicht senkrecht nach oben. Eine
# senkrecht verlaengerte Rippe dringt in eine schraege Wand nur mit dem
# Kosinus ihrer Neigung ein -- bei nz = -0.45 waeren von 0.4 mm noch 0.18 mm
# uebrig, und der Boolean laesst zwei getrennte Koerper stehen. Die noetige
# senkrechte Verlaengerung wird deshalb aus der Normalen zurueckgerechnet.
RIPPE_EINTAUCH = 0.40
RIPPE_MAX_HOCH = (4.00, 5.00, 6.00)  # ueber dem tiefsten Cap-Punkt, aufsteigend probiert
# Mit der Normalen-Nachrechnung darf die Ankerflaeche flacher sein. -0.40
# statt -0.60: bei 71 Grad Kippung (keycap-r2) lagen sonst alle Anker in
# einem Band auf einer Seite, und das Fussvieleck umschloss den Schwerpunkt
# nur noch mit 0.87 statt der geforderten 1.20 mm.
ANKER_ABWAERTS = -0.40
KORRIDOR = 0.90          # Umkreis, in dem der Anker nicht stark abfallen darf
KORRIDOR_ABFALL = 1.20   # erlaubter Abfall darin -- begrenzt die Bruchnarbe
RIPPE_ABSTAND = 1.50     # Mindestabstand zweier Rippen in XY
# Verteilungspruefung, KEIN Kippkriterium: liegt der Schwerpunkt innerhalb des
# Rippenvielecks, sind die Rippen um ihn herum verteilt statt alle auf einer
# Seite. Mehr sagt die Zahl nicht.
#
# Die erste Fassung forderte hier 1.20 mm und verstand das als Kippsicherung.
# Das ist das falsche Modell: das Cap steht nicht frei auf den Rippen, es
# haengt an Rippen, die auf einem ans Bett geklebten Floss sitzen -- ein
# Kragarm, kein Stapel. 1.5 g Cap an 5 mm Hebel sind 0.07 Nmm gegen fuenf
# PLA-Stege zu je 0.49 mm2. Das echte Kippkriterium ist der Schwerpunkt ueber
# der BETTAUFLAGE, und das prueft `gate_quer.py` als Gate 8 (gemessen +4.8 bis
# +6.5 mm). Hier genuegt ein kleiner positiver Abstand; 0.50 statt 0.0, damit
# ein Grenzfall nicht an Rundung haengt.
RAND_SOLL = 0.50

ZELLE = 0.30
MULDE_AB = 30.0


# ---------------------------------------------------------------- Hilfsmittel

def hull(punkte):
    """Konvexe Huelle (Andrew's monotone chain)."""
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
    """Abstand zum Huellenrand; negativ heisst ausserhalb = kippt."""
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


def volumenschwerpunkt(mesh):
    """Schwerpunkt ueber Tetraeder zum Ursprung -- nicht der Bbox-Mittelpunkt.

    DES-Caps haengen schief ueber ihrer Montageachse; der Bbox-Mittelpunkt
    liegt mehrere Millimeter daneben und wuerde die Kippsicherung verfaelschen.
    """
    vol = 0.0
    summe = Vector((0.0, 0.0, 0.0))
    for poly in mesh.polygons:
        ecken = [mesh.vertices[i].co for i in poly.vertices]
        for i in range(1, len(ecken) - 1):
            a, b, c = ecken[0], ecken[i], ecken[i + 1]
            d = a.dot(b.cross(c)) / 6.0
            vol += d
            summe += (a + b + c) / 4.0 * d
    return summe / vol, abs(vol)


def klassifiziere(mesh):
    """Je Flaeche: mulde / schuerze / boden / innen -- in der AUFRECHTEN Lage.

    Dort ist die Aussenhaut ein Hoehenfeld z = f(x,y). Nach dem Drehen waere
    diese Trennung nicht mehr moeglich, deshalb passiert sie vorher und die
    Flaechenindizes werden mitgefuehrt (Transformieren aendert sie nicht).
    """
    oben = {}
    mitten = []
    for poly in mesh.polygons:
        mitte = poly.center
        mitten.append(mitte)
        schluessel = (int(mitte.x // ZELLE), int(mitte.y // ZELLE))
        if mitte.z > oben.get(schluessel, -1e9):
            oben[schluessel] = mitte.z

    klassen = []
    for poly, mitte in zip(mesh.polygons, mitten):
        schluessel = (int(mitte.x // ZELLE), int(mitte.y // ZELLE))
        if poly.normal.z > 0.02 and mitte.z >= oben[schluessel] - 0.35:
            steil = math.degrees(math.asin(min(1.0, poly.normal.z)))
            klassen.append("mulde" if steil >= MULDE_AB else "schuerze")
        elif poly.normal.z <= -0.02 and mitte.z <= 0.9:
            klassen.append("boden")
        else:
            klassen.append("innen")
    return klassen


# ------------------------------------------------------------------ Fussbau

def waehle_anker(mesh, klassen, schwerpunkt, cap_zmin):
    """Ankerpunkte fuer die Rippen suchen.

    Vier Bedingungen, jede aus einem echten Fehlerbild:

      1. nur Bodenring und Schuerze -- die Mulde ist tabu.

      2. Die Flaeche muss STEIL nach unten zeigen (nz < -0.60). Das war der
         erste Fehlschlag: mit nz < -0.25 waren Bodenringflaechen zugelassen,
         die bei 74 Grad Kippung mit nz = -cos(74 Grad) = -0.28 fast senkrecht
         stehen. Eine senkrechte Rippe, die 0.3 mm nach OBEN verlaengert wird,
         dringt in eine senkrechte Wand nicht ein -- sie kuesst sie. Ergebnis:
         zwei getrennte Koerper statt einem.

      3. Absenkkorridor: der Anker muss der tiefste Cap-Punkt im Umkreis einer
         halben Rippenbreite sein. Eine Ein-Zellen-Pruefung genuegt nicht, weil
         die Rippe unten 1.8 mm breit ist und sonst an Nachbargeometrie
         anstreift -- die Bruchstelle waere dann nicht mehr die Spitze.

      4. Mindestabstand zwischen den Rippen, damit sie nicht verschmelzen.
    """
    unten = {}
    for poly in mesh.polygons:
        mitte = poly.center
        schluessel = (int(mitte.x // ZELLE), int(mitte.y // ZELLE))
        if mitte.z < unten.get(schluessel, 1e9):
            unten[schluessel] = mitte.z

    reichweite = int(math.ceil(KORRIDOR / ZELLE))

    def abfall(mitte):
        """Wie weit faellt das Cap im Umkreis einer Rippenbreite ab?

        Daraus folgt direkt die Groesse der Bruchnarbe: eine senkrechte Rippe
        an einer schraegen Wand beruehrt sie ueber genau diese Hoehe. Punkt-
        kontakt ist auf einer schraegen Schuerze unmoeglich -- gemessen faellt
        sie im Umkreis von 0.9 mm ueberall um 0.4 bis 1.1 mm ab. Also wird die
        Narbe begrenzt, nicht wegdefiniert.
        """
        kx, ky = int(mitte.x // ZELLE), int(mitte.y // ZELLE)
        tiefster = min(
            (
                unten[(kx + dx, ky + dy)]
                for dx in range(-reichweite, reichweite + 1)
                for dy in range(-reichweite, reichweite + 1)
                if (kx + dx, ky + dy) in unten
            ),
            default=mitte.z,
        )
        return mitte.z - tiefster

    roh = []
    for poly, klasse in zip(mesh.polygons, klassen):
        if klasse not in ("boden", "schuerze"):
            continue
        if poly.normal.z >= ANKER_ABWAERTS:
            continue
        roh.append((poly.center.copy(), klasse, poly.normal.z))

    for hoch_grenze in RIPPE_MAX_HOCH:
        kandidaten = [
            (m, k, abfall(m), nz)
            for m, k, nz in roh
            if m.z <= cap_zmin + hoch_grenze and abfall(m) <= KORRIDOR_ABFALL
        ]
        if os.environ.get("QUER_DEBUG"):
            xs = [m.x for m, _, _, _ in kandidaten]
            ys = [m.y for m, _, _, _ in kandidaten]
            print(f"    [debug] hoch<={hoch_grenze}: {len(kandidaten)} Kandidaten"
                  + (f", x {min(xs):.1f}..{max(xs):.1f} y {min(ys):.1f}..{max(ys):.1f}"
                     f", Schwerpunkt ({schwerpunkt.x:.1f},{schwerpunkt.y:.1f})"
                     if kandidaten else ""))
        if len(kandidaten) < 3:
            continue
        for sektoren in (6, 8, 12, 16):
            gewaehlt = []
            for s in range(sektoren):
                a0 = 2 * math.pi * s / sektoren
                a1 = 2 * math.pi * (s + 1) / sektoren
                bester = None
                for mitte, klasse, ab, nz in kandidaten:
                    dx, dy = mitte.x - schwerpunkt.x, mitte.y - schwerpunkt.y
                    winkel = math.atan2(dy, dx) % (2 * math.pi)
                    if not (a0 <= winkel < a1):
                        continue
                    # Bodenring bevorzugen: dort ist eine Bruchnarbe unsichtbar,
                    # weil die Flaeche spaeter auf dem Switch aufsitzt.
                    # weit aussen ist besser (breitere Standflaeche), flach ist
                    # besser (kleinere Narbe), Bodenring ist am besten (unsichtbar)
                    punkte = (
                        math.hypot(dx, dy)
                        - 1.0 * ab
                        + (3.0 if klasse == "boden" else 0.0)
                    )
                    if bester is None or punkte > bester[0]:
                        bester = (punkte, mitte, klasse, ab, nz)
                if bester is None:
                    continue
                if any(
                    math.hypot(bester[1].x - g[0].x, bester[1].y - g[0].y)
                    < RIPPE_ABSTAND
                    for g in gewaehlt
                ):
                    continue
                gewaehlt.append((bester[1], bester[2], bester[3], bester[4]))

            rand = rand_abstand(
                hull([(g[0].x, g[0].y) for g in gewaehlt]),
                (schwerpunkt.x, schwerpunkt.y),
            )
            if os.environ.get("QUER_DEBUG"):
                print(f"    [debug]   {sektoren} Sektoren -> {len(gewaehlt)} Rippen, Rand {rand:+.2f}")
            if rand >= RAND_SOLL and len(gewaehlt) >= 4:
                return gewaehlt, rand, hoch_grenze
    return [], -99.0, 0.0


def baue_fuss(anker, grundriss):
    """Floss und Rippen als EINZELNE, je fuer sich saubere Koerper.

    Nicht als ein Mesh: Floss und Rippen ueberlappen sich, und ein
    selbstdurchdringender Operand ist fuer den Boolean undefiniert. Beim ersten
    Versuch hatte der Fuss deshalb 6 Shells, der MANIFOLD-Solver hat die Rippen
    verschmolzen und das Floss als zweiten Koerper liegen gelassen. Jedes Teil
    wird jetzt in einem eigenen Boolean angesetzt -- langsamer, aber definiert.
    """
    objekte = []

    def neues_mesh(name):
        mesh = bpy.data.meshes.new(name)
        return mesh

    def anlegen(name, bm):
        mesh = neues_mesh(name)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        objekte.append(obj)

    def quader(name, x0, y0, z0, x1, y1, z1):
        bm = bmesh.new()
        ecken = [
            bm.verts.new((x, y, z))
            for z in (z0, z1)
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        ]
        u, o = ecken[:4], ecken[4:]
        bm.faces.new(u[::-1])
        bm.faces.new(o)
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((u[i], u[j], o[j], o[i]))
        anlegen(name, bm)

    def kegelstumpf(name, x, y, zspitze):
        bm = bmesh.new()
        unten_h, oben_h = RIPPE_FUSS / 2.0, RIPPE_SPITZE / 2.0
        u = [
            bm.verts.new((x + sx * unten_h, y + sy * unten_h, 0.0))
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
        o = [
            bm.verts.new((x + sx * oben_h, y + sy * oben_h, zspitze))
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
        bm.faces.new(u[::-1])
        bm.faces.new(o)
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((u[i], u[j], o[j], o[i]))
        anlegen(name, bm)

    # Das Floss deckt den ganzen Grundriss ab, nicht nur die Rippenfuesse.
    # Die erste Fassung war auf die Fuesse beschraenkt -- dann liegt die
    # Auflage als schmales Band neben der Teilachse, und `downfacing_probe.py`
    # meldet zu Recht 69 von 72 Winkelsektoren ohne Plattenkontakt. Ein Floss
    # unter dem ganzen Teil klebt besser und faengt das Cap auch dann, wenn
    # eine Rippe im Druck abreisst.
    xs = [m.x for m, _, _, _ in anker] + [grundriss[0], grundriss[2]]
    ys = [m.y for m, _, _, _ in anker] + [grundriss[1], grundriss[3]]
    halb = RIPPE_FUSS / 2.0 + FLOSS_RAND
    quader("floss", min(xs) - halb, min(ys) - halb, 0.0,
           max(xs) + halb, max(ys) + halb, FLOSS_DICKE)
    for i, (mitte, _, _, nz) in enumerate(anker):
        # senkrechte Verlaengerung so, dass SENKRECHT ZUR FLAECHE
        # RIPPE_EINTAUCH herauskommt
        kegelstumpf(
            f"rippe{i}", mitte.x, mitte.y, mitte.z + RIPPE_EINTAUCH / max(0.35, -nz)
        )
    return objekte


# --------------------------------------------------------------------- Lauf

def leere_szene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.objects):
        for datum in list(block):
            if datum.users == 0:
                block.remove(datum)


def quer(name, polar, azimut):
    leere_szene()
    bpy.ops.wm.stl_import(filepath=os.path.join(QUELLE, name + ".stl"))
    cap = bpy.context.selected_objects[0]
    cap.name = name
    mesh = cap.data

    klassen = klassifiziere(mesh)
    vorher_polys = len(mesh.polygons)

    # Richtung, die nach dem Drehen oben sein soll
    t, p = math.radians(polar), math.radians(azimut)
    hoch = Vector((math.sin(t) * math.cos(p), math.sin(t) * math.sin(p), math.cos(t)))
    drehung = hoch.rotation_difference(Vector((0.0, 0.0, 1.0))).to_matrix().to_4x4()
    mesh.transform(drehung)

    schwerpunkt, volumen = volumenschwerpunkt(mesh)
    zmin = min(v.co.z for v in mesh.vertices)
    xmit = (max(v.co.x for v in mesh.vertices) + min(v.co.x for v in mesh.vertices)) / 2
    ymit = (max(v.co.y for v in mesh.vertices) + min(v.co.y for v in mesh.vertices)) / 2
    # Ohne Fuss steht das Cap direkt auf dem Bett: tiefster Punkt auf z = 0.
    # Mit Fuss bleibt der Luftspalt ueber dem Floss.
    hoehe_ueber_bett = (FLOSS_DICKE + LUFTSPALT) if MIT_FUSS else 0.0
    versatz = Vector((-xmit, -ymit, hoehe_ueber_bett - zmin))
    for v in mesh.vertices:
        v.co += versatz
    schwerpunkt += versatz
    mesh.update()
    cap_zmin = hoehe_ueber_bett

    if not MIT_FUSS:
        # Keine Booleans, also nur: Drehung pruefen, Hygiene, Export. Die
        # Hygiene laeuft trotzdem -- der STL-Export rastert auf float32 und
        # weldet, und das kann aus harmlosen Kanten Vierfachkanten machen.
        vor = H.report(cap)
        if vor["shells"] != 1:
            sys.exit(f"{name}: Quelle hat {vor['shells']} Koerper statt 1.")
        for runde in range(1, 4):
            rep = H.full_hygiene(cap, plate_z=0.0, dissolve_deg=0.0, verbose=(runde == 1))
            if H.is_clean(rep):
                break
            # Bleibt NUR ein entartetes Dreieck uebrig, dreht sich die Kette im
            # Kreis: remove_degenerate LOESCHT es (Loch), holes_fill flickt, der
            # 5-um-Weld am Ende erzeugt an derselben Stelle wieder ein Dreieck
            # mit Flaeche null. Mit Opferfuss hat der Boolean die Stelle
            # umtrianguliert, ohne Fuss bleibt sie, wie die SLS-Quelle sie
            # liefert (300-500 Sliver unter 1e-6 mm2 je Cap). Ausweg: die
            # Nullkanten KOLLABIEREN statt die Flaeche zu loeschen -- das
            # hinterlaesst kein Loch.
            if all(rep[k] == 0 for k in ("non_manifold_edges", "boundary_edges",
                                          "wire_edges", "loose_verts", "duplicate_faces")) \
                    and rep["shells"] == 1 and rep["degenerate_faces"] > 0:
                bm = bmesh.new(); bm.from_mesh(cap.data)
                bmesh.ops.dissolve_degenerate(bm, dist=1e-3, edges=bm.edges)
                bm.to_mesh(cap.data); bm.free(); cap.data.update()
                print(f"  entartete Flaechen kollabiert -> {H.report(cap)}")
                # NICHT abbrechen: der Kollaps kann eine Doppelflaeche oder eine
                # Vierfachkante hinterlassen, die erst die naechste volle Runde
                # (quantisieren, welden, Duplikate) wegraeumt. Bei keycap-daumen-c-L
                # kam sonst eine STL mit 1 non-manifold-Kante durch.
                continue
        else:
            sys.exit(f"{name}: Mesh nach 3 Hygiene-Runden nicht sauber: {rep}")
        _, volumen_nachher = volumenschwerpunkt(cap.data)
        # Die Hygiene darf die Form nicht veraendern: Volumen bleibt (< 0,01 %).
        if abs(volumen_nachher - volumen) / volumen > 1e-4:
            sys.exit(f"{name}: Volumen {volumen:.2f} -> {volumen_nachher:.2f} mm3 durch Hygiene veraendert.")
        pfad = os.path.join(ZIEL, name + ".stl")
        H.export_stl(cap, pfad)
        # Die DATEI pruefen, nicht das Blender-Objekt: der Export rastert auf
        # float32 und weldet, dabei koennen aus harmlosen Kanten Vierfachkanten
        # werden. export_stl warnt nur -- hier ist es ein Abbruch.
        import subprocess
        pruef = subprocess.run(
            [sys.executable if "blender" not in sys.executable else "python3",
             os.path.expanduser("~/.claude/skills/print-mesh-gates/scripts/verify_stl.py"), pfad],
            capture_output=True, text=True)
        zeile = (pruef.stdout + pruef.stderr).strip().splitlines()[-1] if (pruef.stdout + pruef.stderr).strip() else ""
        if "non-manifold 0 / offen 0 / doppelt 0 / degeneriert 0" not in (pruef.stdout + pruef.stderr) \
                or "1 Shell" not in (pruef.stdout + pruef.stderr):
            os.remove(pfad)
            sys.exit(f"{name}: exportierte STL nicht sauber -- geloescht. {zeile}")
        print(f"\n--- {name}  Kippung {polar}deg / Richtung {azimut}deg  (ohne Fuss)")
        print(f"  tiefster Punkt auf z = {min(v.co.z for v in cap.data.vertices):.3f}, "
              f"Volumen {volumen_nachher:.1f} mm3, Polygone {len(cap.data.polygons)}")
        return {
            "kippung": polar, "richtung": azimut, "fuss": False,
            "polygone": len(cap.data.polygons),
            "volumen_cap_mm3": round(volumen_nachher, 1),
            "schwerpunkt_hoehe_mm": round(schwerpunkt.z, 2),
        }

    anker, rand, hoch_grenze = waehle_anker(mesh, klassen, schwerpunkt, cap_zmin)
    if rand < RAND_SOLL:
        sys.exit(
            f"{name}: Fussvieleck umschliesst den Schwerpunkt nur mit {rand:.2f} mm "
            f"(gefordert {RAND_SOLL}). Kein Fuss gebaut."
        )
    auf_mulde = [k for _, k, _, _ in anker if k not in ("boden", "schuerze")]
    if auf_mulde:
        sys.exit(f"{name}: Rippe wuerde auf {auf_mulde} sitzen -- abgebrochen.")

    grundriss = (
        min(v.co.x for v in mesh.vertices),
        min(v.co.y for v in mesh.vertices),
        max(v.co.x for v in mesh.vertices),
        max(v.co.y for v in mesh.vertices),
    )
    teile = baue_fuss(anker, grundriss)
    for teil in teile:
        rep_teil = H.report(teil)
        if rep_teil["shells"] != 1 or not H.is_clean(rep_teil):
            sys.exit(f"{name}: Fussteil {teil.name} ist nicht sauber: {rep_teil}")

    bpy.context.view_layer.objects.active = cap
    for teil in teile:
        vorher_vol = volumenschwerpunkt(cap.data)[1]
        mod = cap.modifiers.new(teil.name, "BOOLEAN")
        mod.operation = "UNION"
        mod.object = teil
        try:
            mod.solver = "MANIFOLD"
        except TypeError:
            mod.solver = "EXACT"
        bpy.ops.object.modifier_apply(modifier=mod.name)
        zuwachs = volumenschwerpunkt(cap.data)[1] - vorher_vol
        if zuwachs <= 0.01:
            sys.exit(
                f"{name}: Boolean mit {teil.name} hat {zuwachs:+.3f} mm3 gebracht -- "
                f"das Teil hat nichts getroffen."
            )
        bpy.data.objects.remove(teil, do_unlink=True)
    nachher_polys = len(cap.data.polygons)
    _, volumen_nachher = volumenschwerpunkt(cap.data)

    print(f"\n--- {name}  Kippung {polar}deg / Richtung {azimut}deg")
    narben = [RIPPE_SPITZE * max(RIPPE_SPITZE, ab) for _, _, ab, _ in anker]
    print(f"  Rippen {len(anker)} ({sum(1 for _, k, _, _ in anker if k == 'boden')} am Bodenring, "
          f"{sum(1 for _, k, _, _ in anker if k == 'schuerze')} an der Schuerze)")
    print(f"  Bruchnarben je {min(narben):.2f}-{max(narben):.2f} mm2, "
          f"zusammen {sum(narben):.2f} mm2")
    print(f"  Schwerpunkt-Rand {rand:+.2f} mm, Rippen bis {hoch_grenze:.0f} mm hoch")
    print(f"  Polygone {vorher_polys} -> {nachher_polys}, "
          f"Volumen {volumen:.1f} -> {volumen_nachher:.1f} mm3 (Fuss {volumen_nachher - volumen:+.1f})")

    # Die Polygonzahl taugt hier NICHT als Treffer-Nachweis: beide Solver
    # verschmelzen koplanare Dreiecke, die Zahl sinkt also auch bei einer
    # geglueckten Union. Der Beweis, dass der Fuss das Cap wirklich beruehrt,
    # ist die Shell-Zahl -- ein nicht treffender Fuss bliebe ein zweiter Koerper.
    vor_hygiene = H.report(cap)
    if vor_hygiene["shells"] != 1:
        sys.exit(
            f"{name}: nach der Union {vor_hygiene['shells']} Koerper statt 1 -- "
            f"mindestens eine Rippe haengt in der Luft."
        )
    if volumen_nachher - volumen < 150.0:
        sys.exit(f"{name}: Fuss bringt nur {volumen_nachher - volumen:.1f} mm3 -- zu wenig.")

    # dissolve_deg=0.0: die Mulde darf NICHT umtrianguliert werden, sonst laesst
    # sich hinterher nicht mehr beweisen, dass sie unberuehrt ist.
    #
    # Mehrere Runden, und am Ende ein harter Abbruch. `export_stl` warnt nur
    # und schreibt die Datei trotzdem -- bei keycap-r1 kam so eine STL mit
    # 2 non-manifold-Kanten durch. Eine Runde genuegt nicht immer: das
    # Lochflicken kann selbst eine Kante hinterlassen, die erst die naechste
    # Runde kollabiert.
    for runde in range(1, 4):
        rep = H.full_hygiene(cap, plate_z=0.0, dissolve_deg=0.0, verbose=(runde == 1))
        if H.is_clean(rep):
            break
        print(f"  Hygiene-Runde {runde} nicht sauber: {rep} -- noch einmal")
    else:
        sys.exit(f"{name}: Mesh nach 3 Hygiene-Runden nicht sauber: {rep}")
    if rep["shells"] != 1:
        sys.exit(f"{name}: {rep['shells']} Koerper nach der Hygiene statt 1.")
    H.export_stl(cap, os.path.join(ZIEL, name + ".stl"))

    return {
        "kippung": polar,
        "richtung": azimut,
        "rippen": [
            {
                "x": round(m.x, 3),
                "y": round(m.y, 3),
                "z": round(m.z, 3),
                "an": k,
                "narbe_mm2": round(RIPPE_SPITZE * max(RIPPE_SPITZE, ab), 3),
            }
            for m, k, ab, _ in anker
        ],
        "narbe_gesamt_mm2": round(sum(narben), 3),
        "schwerpunkt_rand": round(rand, 3),
        "rippe_max_hoch": hoch_grenze,
        "rippe_spitze_mm2": round(RIPPE_SPITZE ** 2, 3),
        "polygone": nachher_polys,
        "volumen_cap_mm3": round(volumen, 1),
        "volumen_fuss_mm3": round(volumen_nachher - volumen, 1),
    }


def main():
    bpy.context.preferences.edit.use_global_undo = False
    os.makedirs(ZIEL, exist_ok=True)
    lagen = json.load(open(LAGEN))
    # QUER_NUR=keycap-r1 baut nur ein Cap -- zum Nachmessen einzelner Faelle.
    nur = os.environ.get("QUER_NUR")
    bericht = {}
    for name in sorted(lagen):
        if nur and name != nur:
            continue
        bericht[name] = quer(name, *lagen[name])
    with open(BERICHT, "w") as f:
        json.dump(bericht, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"\ngeschrieben: {ZIEL}  ({len(bericht)} Dateien)")



if __name__ == "__main__":
    main()
