#!/usr/bin/env python3
"""Gate: sitzt der MX-Kreuzschlitz nach dem Trennen noch im Toleranzfenster?

Der Boolean-Schnitt am Cap-Boden liegt 0.05 mm ueber der Stamm-Unterkante und
darf den Schlitz nicht anschneiden. Gemessen wird per Strahlenschnitt im
fertigen STL, nicht im Blender-Zustand.

Der Stamm sitzt NICHT in der Bbox-Mitte (DES ist sculpted, das Cap haengt
schief ueber seiner Montageachse). Er wird deshalb erst lokalisiert und die
Strahlen dann durch seine Achse gelegt.

    blender -b --factory-startup -noaudio -P gate_mx_stamm.py
    blender -b --factory-startup -noaudio -P gate_mx_stamm.py -- --rotnachweis
"""
import bpy, bmesh, os, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.path.join(HIER, "drucken")
ROT  = "--rotnachweis" in sys.argv

# Cherry-MX-Zapfen: Kreuz 4.10 x 1.17 mm. Der Cap-Schlitz muss darueber passen.
ARM_MIN,   ARM_MAX   = 3.90, 4.30
SPALT_MIN, SPALT_MAX = 1.05, 1.60
if ROT:                              # absichtlich unerfuellbares Fenster
    ARM_MIN, ARM_MAX = 5.00, 5.50

Z_MESS   = 2.00                      # Hoehe im Schlitz, weit weg von beiden Enden
ARM_WEG  = 1.50                      # Querversatz fuer die Spaltmessung


def strahl(bvh, start, richtung, weite=40.0):
    """Alternierende Eintritts-/Austrittsabstaende entlang des Strahls."""
    treffer, t = [], 0.0
    while t < weite:
        r = bvh.ray_cast(start + richtung * (t + 1e-4), richtung, weite - t)
        if r[0] is None:
            break
        t += 1e-4 + r[3]; treffer.append(t)
    return treffer


def schlitz(bvh, start, richtung, achse):
    """Aus 8 Treffern (Schuerze, Stamm, SCHLITZ, Stamm, Schuerze) die Luft in der
    Mitte herausziehen. Andere Trefferzahl = Strahl liegt falsch."""
    h = strahl(bvh, start, richtung)
    if len(h) != 8:
        return None, len(h)
    p = [start + richtung * d for d in h]
    return (p[4] - p[3]).length, 8


fehler, zeilen = [], []
for datei in sorted(os.listdir(ZIEL)):
    if not datei.endswith(".stl"):
        continue
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    bpy.ops.wm.stl_import(filepath=os.path.join(ZIEL, datei))
    ob = bpy.context.selected_objects[0]

    bm = bmesh.new(); bm.from_mesh(ob.data); bvh = BVHTree.FromBMesh(bm)

    # --- Stammachse lokalisieren --------------------------------------------
    # Nicht ueber Vertices: die senkrechten Stammwaende bestehen aus langen
    # Dreiecken, die von der Unterkante bis zur Decke durchlaufen und im
    # Messband gar keine Eckpunkte haben. Stattdessen von unten anleuchten --
    # der Stamm ist die Flaeche, deren erster Treffer knapp ueber dem Bett liegt
    # (Schuerze trifft bei z=0, Hohlraum erst an der Decke bei z>4).
    treffer_xy = []
    r = 6.0
    n = int(2 * r / 0.1) + 1
    for i in range(n):
        for j in range(n):
            x, y = -r + i * 0.1, -r + j * 0.1
            h = bvh.ray_cast(Vector((x, y, -5.0)), Vector((0, 0, 1)), 40.0)
            if h[0] is not None and 0.10 < h[0].z < 0.45:
                treffer_xy.append((x, y))
    assert len(treffer_xy) > 100, \
        f"{datei}: Stamm nicht gefunden ({len(treffer_xy)} Rasterpunkte)"
    sx = (min(p[0] for p in treffer_xy) + max(p[0] for p in treffer_xy)) / 2
    sy = (min(p[1] for p in treffer_xy) + max(p[1] for p in treffer_xy)) / 2
    arm_x, nx = schlitz(bvh, Vector((sx - 20, sy, Z_MESS)), Vector((1, 0, 0)), "x")
    arm_y, ny = schlitz(bvh, Vector((sx, sy - 20, Z_MESS)), Vector((0, 1, 0)), "y")
    sp_x,  mx = schlitz(bvh, Vector((sx + ARM_WEG, sy - 20, Z_MESS)), Vector((0, 1, 0)), "y")
    sp_y,  my = schlitz(bvh, Vector((sx - 20, sy + ARM_WEG, Z_MESS)), Vector((1, 0, 0)), "x")
    hz = strahl(bvh, Vector((sx + 2.4, sy, -5)), Vector((0, 0, 1)))
    stamm_z = (hz[0] - 5) if hz else float('nan')
    bm.free()

    schlecht = []
    for nm, wert, lo, hi, trf in [("ArmX", arm_x, ARM_MIN, ARM_MAX, nx),
                                  ("ArmY", arm_y, ARM_MIN, ARM_MAX, ny),
                                  ("SpaltX", sp_x, SPALT_MIN, SPALT_MAX, mx),
                                  ("SpaltY", sp_y, SPALT_MIN, SPALT_MAX, my)]:
        if wert is None:
            schlecht.append(f"{nm}:{trf}Treffer")
        elif not (lo <= wert <= hi):
            schlecht.append(f"{nm}={wert:.2f}")
    f = lambda v: f"{v:7.2f}" if v is not None else "      -"
    zeilen.append(f"  {datei[:-4]:26s} {sx:+6.2f} {sy:+6.2f} {f(arm_x)} {f(arm_y)}"
                  f" {f(sp_x)} {f(sp_y)} {stamm_z:7.2f}"
                  + ("   <-- " + ", ".join(schlecht) if schlecht else ""))
    if schlecht:
        fehler.append(datei)

print(f"  Fenster: Arm {ARM_MIN}-{ARM_MAX} mm, Spalt {SPALT_MIN}-{SPALT_MAX} mm"
      + ("   [ROT-NACHWEIS]" if ROT else ""))
print(f"  {'Datei':26s} {'Achse x':>6s} {'y':>6s} {'Arm X':>7s} {'Arm Y':>7s}"
      f" {'Spalt X':>7s} {'Spalt Y':>7s} {'Stamm z':>7s}")
print("\n".join(zeilen))
if ROT:
    assert fehler, "ROT-NACHWEIS FEHLGESCHLAGEN: unerfuellbares Fenster wurde bestanden"
    print(f"\n  ROT-NACHWEIS OK -- {len(fehler)} Datei(en) fallen durch, wie erwartet")
else:
    assert not fehler, f"Schlitzmass ausserhalb Toleranz: {fehler}"
    print("\n  GATE GRUEN -- alle Schlitze im Fenster")
