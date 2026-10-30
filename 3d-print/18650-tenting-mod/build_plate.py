"""Neue Bodenplatte mit integriertem 18650-Fach und angeformter Tenting-Neigung.

Ersetzt die flache Originalplatte UND den angeschraubten Pod: ein Teil statt zwei.
Oben plan (liegt am Case an), unten eine schiefe Ebene -> die Neigung entsteht
aus dem Teil selbst. Im dicken Bereich an der Daumen-/Innenseite sitzt der
18650-Halter in einer Tasche, die von unten mit einem verschraubten Deckel
geschlossen wird.

Aufruf:  b3d build_plate.py            (baut beide Haelften)
"""
import json, math, os
from build123d import *
import b3d_gate as G

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "cad")            # STEP + Konstruktionslage
PRINT = os.path.join(HERE, "drucken")      # fertig gedreht fuer den Slicer
for d in (CAD, PRINT):
    os.makedirs(d, exist_ok=True)

NAMEN = {"plate_right": "bodenplatte-rechts", "plate_left": "bodenplatte-links",
         "lid_right": "akkudeckel-rechts",    "lid_left": "akkudeckel-links"}


def export_beides(shape, stem, nrm=None):
    """STEP + Konstruktions-STL nach cad/, gedrehte Drucklage nach drucken/."""
    import struct
    G.export(shape, os.path.join(CAD, stem))
    src = os.path.join(CAD, stem + ".stl")
    with open(src, "rb") as f:
        f.read(80); n = struct.unpack("<I", f.read(4))[0]
        tris = [struct.unpack("<12fH", f.read(50)) for _ in range(n)]
    if nrm is None:
        # 180 Grad um X -> Planflaeche nach unten; echte Rotation, Wicklung bleibt
        rot = lambda x, y, z: (x, -y, -z)
    else:
        # Teil auf seine eigene schraege Flaeche legen: nrm -> +Z
        import math as _m
        ln = _m.sqrt(sum(a * a for a in nrm)); u = [a / ln for a in nrm]
        ax = (u[1] * 1 - 0, 0 - u[0] * 1, 0.0)          # u x Z
        la = _m.sqrt(ax[0] ** 2 + ax[1] ** 2)
        if la < 1e-9:
            rot = lambda x, y, z: (x, y, z)
        else:
            k = (ax[0] / la, ax[1] / la, 0.0)
            th = _m.acos(max(-1.0, min(1.0, u[2])))
            c, si = _m.cos(th), _m.sin(th)
            def rot(x, y, z, k=k, c=c, si=si):           # Rodrigues
                kv = k[0] * x + k[1] * y + k[2] * z
                return (x * c + (k[1] * z - k[2] * y) * si + k[0] * kv * (1 - c),
                        y * c + (k[2] * x - k[0] * z) * si + k[1] * kv * (1 - c),
                        z * c + (k[0] * y - k[1] * x) * si + k[2] * kv * (1 - c))
    out = []
    for t in tris:
        v = []
        for i in range(0, 12, 3):
            v += list(rot(t[i], t[i + 1], t[i + 2]))
        out.append(v)
    zmin = min(v[i] for v in out for i in (5, 8, 11))
    dst = os.path.join(PRINT, NAMEN.get(stem, stem) + ".stl")
    with open(dst, "wb") as f:
        f.write(b"\0" * 80); f.write(struct.pack("<I", len(out)))
        for v in out:
            f.write(struct.pack("<12fH", *v[0:3],
                                v[3], v[4], v[5] - zmin,
                                v[6], v[7], v[8] - zmin,
                                v[9], v[10], v[11] - zmin, 0))
    print(f"  -> drucken/{NAMEN.get(stem, stem)}.stl")

# ---- Halter (MPD BH-18650-W, Datenblatt Rev. G) + Luft -------------------
HOLDER_L, HOLDER_W, HOLDER_H = 77.7, 20.9, 21.31
CLR = 0.7
BAY_L, BAY_W, BAY_D = HOLDER_L + 2 * CLR, HOLDER_W + 2 * CLR, HOLDER_H + CLR

# ---- Plattenprofil ------------------------------------------------------
T_IN = 40.0          # Dicke an der Innenkante (Daumenseite) -> traegt das Akkufach
BAY_U = 12.0         # Fachmitte, gemessen von der Schraubenachse nach innen
T_OUT = 4.0          # Dicke an der Aussenkante
TOP_SKIN = 2.0       # Material ueber dem Akkufach (zum Case hin)
LID_T = 2.5          # Deckelstaerke
LID_REBATE = 6.0     # Flanschbreite des Deckels (nimmt die Schrauben auf)
LID_SCREW_R = 1.6    # M3 durch den Deckel
LID_PILOT_R = 1.25   # Kernloch in der Platte (selbstschneidend)
WALL = 3.0           # Wandstaerke um das Fach

# ---- Schrauben: M4 Senkkopf (DIN 7991 / ISO 10642, 90 Grad) ---------------
# Nachgemessen an den Originalplatten (bottom-plates/*.3mf): Durchgang Ø4,0,
# 90-Grad-Kegel bis Ø8,0 an der Unterseite. Hier etwas Luft: Ø4,5 durch,
# Kegel bis Ø9,2 -- ein Kopf mit Ø8,4 (ISO-Hoechstmass) sitzt damit
# 0,4 mm unter dem Kegelrand und steht nirgends vor.
SCREW_R = 2.25       # Durchgang Ø4,5
HEAD_R = 4.60        # Kegel oben Ø9,2 = Bohrung fuer den Kopf
CONE_H = HEAD_R - SCREW_R   # 90 Grad -> Hoehe = Radiusdifferenz = 2,35 mm
# Im dicken Bereich sitzt der Kopf tief, damit ueberall M4x12 passt:
# Kopfoberkante 7 mm unter dem Case -> 12 - 7 = 5 mm Gewinde im Einsatz (L5).
HEAD_FLOOR = 7.0
# Im duennen Bereich entscheidet die Schraege: Die Unterseite steigt innerhalb
# des Kopfradius um HEAD_R*tan(Neigung) an. Der Kopf muss auch an der hohen
# Seite noch unter der Flaeche liegen -- sonst steht er dort vor.
SLOPE_CLEAR = 0.3
MIN_LEAVE = 2.0      # so viel Material bleibt ueber dem Kegel mindestens stehen

# ---- Gummifuesse ----------------------------------------------------------
# Original: Mulde Ø10,4..10,8, 1 mm tief, KEIN Loch darunter. Die Mulde wird
# senkrecht zur schraegen Unterseite geschnitten, damit der Fuss plan aufliegt.
FOOT_R = 5.3         # Ø10,6
FOOT_D = 1.0
FOOT_LID_CLEAR = 1.0 # Mindestabstand Mulde -> Deckelrand
FOOT_EDGE_CLEAR = 1.5  # Mindestabstand Mulde -> Plattenkante

CABLE_R = 4.0        # Kabeldurchlass Fach -> Case
CHAMFER = 0.8        # Fase an der Oberkante, setzt die Platte optisch vom Case ab

# ---- Haelften -----------------------------------------------------------
HALVES = {
    "right": dict(
        outline="outline_right.json",
        M=(-97.73, 9.67), UX=(0.9937, -0.1121), UY=(0.1121, 0.9937), sign=+1,
        # aus right-plate.3mf gemessen: Mulden Ø10,4-11,6 x 1 mm ohne Loch
        fuesse=[(-103.07, -37.64), (23.91, 46.85), (-92.40, 56.98), (24.53, -5.01), (-67.08, -4.69)],
        # aus right-plate.3mf gemessen: Ø4,0 durch, 90-Grad-Kegel bis Ø8,0
        schrauben=[(-8.99, 53.00), (-93.99, 8.02), (-65.99, -46.00), (24.03, -15.81)],
    ),
    "left": dict(
        outline="outline_left.json",
        M=(97.76, 11.16), UX=(0.9883, 0.1525), UY=(-0.1525, 0.9883), sign=-1,
        fuesse=[(59.55, -22.12), (-23.83, 45.51), (90.62, 57.43), (104.90, -35.11), (-25.15, -4.98)],
        schrauben=[(51.59, -13.98), (93.99, 8.00), (8.99, 53.00), (-24.02, -16.01)],
    ),
}


def build(name, cfg):
    pts = json.load(open(os.path.join(CAD, cfg["outline"])))
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    # Splitter entfernen: zu kurze Abschnitte lassen keine Fase zu
    MIN_SEG = 1.5
    keep = [pts[0]]
    for q in pts[1:]:
        if math.dist(q, keep[-1]) >= MIN_SEG:
            keep.append(q)
    while len(keep) > 3 and math.dist(keep[-1], keep[0]) < MIN_SEG:
        keep.pop()
    if len(keep) < len(pts):
        print(f"  [{name}] Kontur {len(pts)} -> {len(keep)} Pkt "
              f"(Abschnitte unter {MIN_SEG} mm zusammengefasst)")
    pts = keep
    M, UX, UY, sign = cfg["M"], cfg["UX"], cfg["UY"], cfg["sign"]

    def u_of(p):                       # Abstand von der Schraubenachse, positiv in die Platte
        return sign * ((p[0] - M[0]) * UX[0] + (p[1] - M[1]) * UX[1])

    us = [u_of(p) for p in pts]
    u_in, u_out = min(us), max(us)
    theta = math.degrees(math.atan2(T_IN - T_OUT, u_out - u_in))

    # --- Grundkoerper: Prisma, dann schiefe Ebene abschneiden -------------
    with BuildPart() as p:
        with BuildSketch(Plane.XY) as sk:
            with BuildLine():
                Polyline(*[(x, y) for x, y in pts], close=True)
            make_face()
        area = sk.sketch.area
        extrude(amount=-T_IN)
        assert abs(p.part.volume - area * T_IN) / (area * T_IN) < 1e-6

    # Schnittebene: bei u_in auf -T_IN, bei u_out auf -T_OUT.
    # WICHTIG: ausserhalb des BuildPart-Kontexts bauen — dort wuerde Box()
    # sofort zum Koerper addiert statt nur erzeugt.
    px = M[0] + sign * UX[0] * u_in
    py = M[1] + sign * UX[1] * u_in

    # Flaechenschwerpunkt exakt aus dem Polygon (nicht BBox-Mitte!)
    A2 = cxs = cys = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        cr = x0 * y1 - x1 * y0
        A2 += cr
        cxs += (x0 + x1) * cr
        cys += (y0 + y1) * cr
    A2 *= 0.5
    cx, cy = cxs / (6 * A2), cys / (6 * A2)
    t_c = T_IN + (T_OUT - T_IN) * (u_of((cx, cy)) - u_in) / (u_out - u_in)
    want = area * t_c
    print(f"  [{name}] u {u_in:.1f}..{u_out:.1f}  Schwerpunkt u={u_of((cx,cy)):.1f}  "
          f"t_c={t_c:.1f} mm  Sollvolumen {want/1000:.1f} cm3  Neigung {theta:.1f} deg")

    # Schnittebene analytisch: enthaelt UY und die Steigungsrichtung
    tan = (T_IN - T_OUT) / (u_out - u_in)
    uy3 = (UY[0], UY[1], 0.0)
    d3 = (sign * UX[0], sign * UX[1], tan)
    n = (uy3[1] * d3[2] - uy3[2] * d3[1],
         uy3[2] * d3[0] - uy3[0] * d3[2],
         uy3[0] * d3[1] - uy3[1] * d3[0])
    # Normale so drehen, dass sie zur Materialseite zeigt (Deckflaeche bei z=-0.5)
    probe = (cx - px, cy - py, -0.5 - (-T_IN))
    if sum(a * b for a, b in zip(n, probe)) < 0:
        n = tuple(-a for a in n)
    pl = Plane(origin=(px, py, -T_IN), z_dir=n)
    cutter = Box(800, 800, 400, align=(Align.CENTER, Align.CENTER, Align.MAX))
    body = p.part - cutter.locate(pl.location)
    G.assert_volume(body, want, tol_pct=1.5)

    # --- Akkufach + Deckel ------------------------------------------------
    bay_u = BAY_U                            # Fachmitte (die Platte laeuft zur Kante hin schmaler zu)
    bx = M[0] + sign * UX[0] * bay_u
    by = M[1] + sign * UX[1] * bay_u
    ang = math.degrees(math.atan2(UY[1], UY[0])) - 90.0

    def local_box(l, w, h, ztop):
        b = Box(w, l, h, align=(Align.CENTER, Align.CENTER, Align.MAX))
        b = b.rotate(Axis.Z, ang)
        return b.translate((bx, by, ztop))

    # Schacht: vom Fachboden durch die Keilflaeche nach aussen -> einlegbar
    bay = local_box(BAY_L, BAY_W, 250, -TOP_SKIN)
    v0 = body.volume
    body = body - bay
    assert (v0 - body.volume) > BAY_L * BAY_W * BAY_D * 0.99, \
        "Akkufach trifft nicht genug Material"

    # Deckelsitz: Stufe parallel zur Keilflaeche, LID_T tief
    nh = math.sqrt(sum(a * a for a in n))
    nu = tuple(a / nh for a in n)
    pl_seat = Plane(origin=(px + nu[0] * LID_T, py + nu[1] * LID_T, -T_IN + nu[2] * LID_T),
                    z_dir=n)
    cut_bottom = Box(800, 800, 400, align=(Align.CENTER, Align.CENTER, Align.MAX)).locate(pl.location)
    cut_seat = Box(800, 800, 400, align=(Align.CENTER, Align.CENTER, Align.MAX)).locate(pl_seat.location)
    rec = local_box(BAY_L + 2 * LID_REBATE, BAY_W + 2 * LID_REBATE, 250, -(TOP_SKIN + BAY_D))
    v0 = body.volume
    body = body - (rec & cut_seat)
    assert (v0 - body.volume) > 100, "Deckelsitz schneidet kein Material — Keilflaeche zu flach?"

    # Deckel = Scheibe zwischen Sitz- und Keilflaeche
    lid = (local_box(BAY_L + 2 * LID_REBATE - 0.4, BAY_W + 2 * LID_REBATE - 0.4, 250,
                     -(TOP_SKIN + BAY_D)) & cut_seat) - cut_bottom

    # Deckelschrauben: 2x M3 in den Flansch, Kernloch in die Platte
    for sy in (+1, -1):
        sxp = bx + UY[0] * sy * (BAY_L / 2 + LID_REBATE / 2)
        syp = by + UY[1] * sy * (BAY_L / 2 + LID_REBATE / 2)
        lid = lid - Cylinder(LID_SCREW_R, 60, align=(Align.CENTER, Align.CENTER, Align.CENTER)
                             ).translate((sxp, syp, -(TOP_SKIN + BAY_D)))
        body = body - Cylinder(LID_PILOT_R, 14, align=(Align.CENTER, Align.CENTER, Align.MAX)
                               ).translate((sxp, syp, -(TOP_SKIN + BAY_D) + 0.01))

    # Kabeldurchlass nach oben ins Case
    ch = Cylinder(CABLE_R, 3 * TOP_SKIN, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    cu = BAY_U
    body = body - ch.translate((M[0] + sign * UX[0] * cu + UY[0] * (BAY_L / 2 - 8),
                                M[1] + sign * UX[1] * cu + UY[1] * (BAY_L / 2 - 8),
                                -TOP_SKIN / 2))

    # --- Hilfen: Lage relativ zu Deckel und Kante ---------------------------
    def v_of(p):                       # Laengsrichtung des Fachs
        return (p[0] - M[0]) * UY[0] + (p[1] - M[1]) * UY[1]

    LID_HU = (BAY_W + 2 * LID_REBATE) / 2     # halbe Deckelbreite  (quer, u)
    LID_HV = (BAY_L + 2 * LID_REBATE) / 2     # halbe Deckellaenge  (laengs, v)

    def im_deckel(p, rand=0.0):
        return abs(u_of(p) - BAY_U) < LID_HU + rand and abs(v_of(p)) < LID_HV + rand

    def kantenabstand(p):
        """Abstand eines Punkts zur Aussenkontur (Polygon)."""
        best = 1e9
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            tt = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.dist(p, (a[0] + tt * dx, a[1] + tt * dy)))
        return best

    def t_at(p):
        return T_IN + (T_OUT - T_IN) * (u_of(p) - u_in) / (u_out - u_in)

    nh = math.sqrt(sum(a * a for a in n))
    nu = tuple(a / nh for a in n)                 # Einheitsnormale der Keilflaeche, zeigt ins Material

    # --- Schrauben: Durchgang + 90-Grad-Senkung, Kopf nie vorstehend --------
    # Eine Schraube, die im Akkufach laege, wird AUSGELASSEN und gemeldet:
    # ihr Loch fuehrte in den Hohlraum, der Deckel hat dort keine Oeffnung,
    # und das Fach so weit nach aussen zu ruecken, dass sie durch den
    # Deckelflansch passt, liesse am aeusseren Deckelrand kaum 1 mm stehen.
    rise = HEAD_R * tan                            # Anstieg der Unterseite ueber den Kopfradius
    schrauben_gebaut = []
    for (hx, hy) in cfg["schrauben"]:
        if im_deckel((hx, hy), rand=HEAD_R):
            print(f"  [{name}] Schraube ({hx:.2f},{hy:.2f}) liegt im Akkufach "
                  f"(u={u_of((hx,hy)):.1f}) -> AUSGELASSEN")
            continue
        t_h = t_at((hx, hy))
        z_c = -t_h                                 # Unterseite an der Schraubenachse
        # Boden der Kopfbohrung: tief, wenn die Platte es hergibt, sonst so
        # hoch wie noetig, damit der Kopf an der hohen Seite der Schraege
        # noch SLOPE_CLEAR unter der Flaeche liegt.
        z_floor_tief = -HEAD_FLOOR
        z_floor_min = z_c + rise + SLOPE_CLEAR
        z_floor = z_floor_tief if z_floor_tief >= z_floor_min else z_floor_min
        leave = -(z_floor + CONE_H)                # Material ueber dem Kegel bis zum Case
        assert leave >= MIN_LEAVE, f"Schraube ({hx},{hy}): nur {leave:.2f} mm ueber dem Kegel"
        schraube = "M4x12" if z_floor <= -HEAD_FLOOR + 1e-6 else f"M4x{int(round(-z_floor + 5))}"

        v0 = body.volume
        # 1) Durchgang Ø4,5 ueber die ganze Hoehe
        body = body - Cylinder(SCREW_R, T_IN + 10, align=(Align.CENTER, Align.CENTER, Align.CENTER)
                               ).translate((hx, hy, -T_IN / 2))
        # 2) 90-Grad-Kegel: unten HEAD_R am Bohrungsboden, oben SCREW_R
        body = body - Cone(HEAD_R, SCREW_R, CONE_H, align=(Align.CENTER, Align.CENTER, Align.MIN)
                           ).translate((hx, hy, z_floor))
        # 3) Kopfbohrung Ø9,2 von unten bis zum Boden; beginnt 3 mm unter der
        #    Flaeche, damit auch die tiefe Seite der Schraege erfasst wird.
        body = body - Cylinder(HEAD_R, z_floor - (z_c - 3.0), align=(Align.CENTER, Align.CENTER, Align.MIN)
                               ).translate((hx, hy, z_c - 3.0))
        # Handrechnung: Bohrung mit schraegem Deckel (mittlere Tiefe = Tiefe an
        # der Achse) + Kegelstumpf + Durchgang oberhalb des Kegels.
        want = (math.pi * HEAD_R**2 * (z_floor - z_c)
                + math.pi * CONE_H / 3 * (HEAD_R**2 + HEAD_R * SCREW_R + SCREW_R**2)
                + math.pi * SCREW_R**2 * leave)
        got = v0 - body.volume
        assert abs(got - want) / want < 0.01, \
            f"Schraube ({hx},{hy}): {got:.1f} statt {want:.1f} mm3 entfernt -- trifft etwas anderes"
        schrauben_gebaut.append((hx, hy, t_h, -z_floor, leave, schraube))
        print(f"  [{name}] Schraube ({hx:7.2f},{hy:7.2f})  Dicke {t_h:5.1f}  Kopf {-z_floor:4.1f} tief  "
              f"{leave:4.1f} mm bleiben  -> {schraube}   Volumen ok ({got:.0f} mm3)")

    # --- Gummifuesse: 1-mm-Mulde senkrecht zur Keilflaeche ------------------
    # Ein Fuss, der den Deckel ueberlappt, rueckt auf der kuerzeren Achse weg.
    # Reicht dafuer die Platte nicht (innere Ecke: Deckelecke und Plattenrand
    # klemmen ihn ein), kommt er AUF den Deckel, 1 mm von dessen Rand: die
    # Mulde sitzt dann im Deckel. Der Fuss drueckt den Deckel von unten in
    # seinen Sitz, die Last geht in den Flansch, nicht in die M3-Schrauben --
    # und beim Akkuwechsel nimmt der Deckel seinen Fuss mit, statt dass ein
    # Fuss ueber die Fuge klebt.
    lid_schrauben = []
    for sy in (+1, -1):
        lid_schrauben.append((bx + UY[0] * sy * (BAY_L / 2 + LID_REBATE / 2),
                              by + UY[1] * sy * (BAY_L / 2 + LID_REBATE / 2)))
    M3_HEAD_R = 2.75                               # M3 Linsen-/Zylinderkopf Ø5,5
    ux_, uy_ = sign * UX[0], sign * UX[1]          # Richtung wachsendes u

    def xy_von_uv(u, v):
        return (M[0] + ux_ * u + UY[0] * v, M[1] + uy_ * u + UY[1] * v)

    fuesse_gebaut = []
    for (fx, fy) in cfg["fuesse"]:
        du, dv = u_of((fx, fy)) - BAY_U, v_of((fx, fy))
        px_, py_, traeger, wie = fx, fy, "Platte", ""
        if im_deckel((fx, fy), rand=FOOT_R + FOOT_LID_CLEAR):
            ueber_u = (LID_HU + FOOT_R + FOOT_LID_CLEAR) - abs(du)
            ueber_v = (LID_HV + FOOT_R + FOOT_LID_CLEAR) - abs(dv)
            if ueber_u <= ueber_v:
                sgn = 1 if du >= 0 else -1
                kand = (fx + sgn * ueber_u * ux_, fy + sgn * ueber_u * uy_); wie = f"quer {ueber_u:.1f} mm"
            else:
                sgn = 1 if dv >= 0 else -1
                kand = (fx + sgn * ueber_v * UY[0], fy + sgn * ueber_v * UY[1]); wie = f"laengs {ueber_v:.1f} mm"
            if kantenabstand(kand) >= FOOT_R + FOOT_EDGE_CLEAR:
                px_, py_ = kand
                print(f"  [{name}] Fuss ({fx:.2f},{fy:.2f}) ueberlappt den Deckel -> verschoben {wie} "
                      f"nach ({px_:.2f},{py_:.2f})")
            else:
                # auf den Deckel, 1 mm innerhalb seines Rands, so nah wie moeglich am Original
                hu = LID_HU - FOOT_R - FOOT_LID_CLEAR
                hv = LID_HV - FOOT_R - FOOT_LID_CLEAR
                u_l = BAY_U + max(-hu, min(hu, du))
                v_l = max(-hv, min(hv, dv))
                px_, py_ = xy_von_uv(u_l, v_l); traeger = "Deckel"
                print(f"  [{name}] Fuss ({fx:.2f},{fy:.2f}) ueberlappt den Deckel, Ausweichen traefe die Kante "
                      f"({kantenabstand(kand) - FOOT_R:.1f} mm Wand) -> AUF DEN DECKEL nach ({px_:.2f},{py_:.2f}), "
                      f"Versatz {math.dist((fx, fy), (px_, py_)):.1f} mm")
        if traeger == "Platte":
            assert not im_deckel((px_, py_), rand=FOOT_R + FOOT_LID_CLEAR - 1e-6)
            ka = kantenabstand((px_, py_))
            assert ka >= FOOT_R + FOOT_EDGE_CLEAR, \
                f"Fuss ({px_:.1f},{py_:.1f}) zu nah an der Kante: {ka - FOOT_R:.1f} mm Wand"
            for (sx, sy_, *_r) in schrauben_gebaut:
                d = math.dist((px_, py_), (sx, sy_))
                assert d >= FOOT_R + HEAD_R + 0.5, \
                    f"Fuss ({px_:.1f},{py_:.1f}) kollidiert mit Schraube ({sx:.1f},{sy_:.1f}): {d:.1f} mm"
        else:
            for (sx, sy_) in lid_schrauben:
                d = math.dist((px_, py_), (sx, sy_))
                assert d >= FOOT_R + M3_HEAD_R + 0.5, \
                    f"Fuss auf dem Deckel ({px_:.1f},{py_:.1f}) trifft die Deckelschraube ({sx:.1f},{sy_:.1f}): {d:.1f} mm"
        t_h = t_at((px_, py_))
        pl_f = Plane(origin=(px_, py_, -t_h), z_dir=nu)
        cutter = Cylinder(FOOT_R, 2 * FOOT_D, align=(Align.CENTER, Align.CENTER, Align.CENTER)
                          ).locate(pl_f.location)
        want = math.pi * FOOT_R**2 * FOOT_D
        if traeger == "Platte":
            v0 = body.volume; body = body - cutter; got = v0 - body.volume
        else:
            v0 = lid.volume; lid = lid - cutter; got = v0 - lid.volume
        assert abs(got - want) / want < 0.01, \
            f"Fuss ({px_:.1f},{py_:.1f}) im {traeger}: {got:.1f} statt {want:.1f} mm3 -- Mulde trifft etwas"
        fuesse_gebaut.append((px_, py_, traeger))
    n_deckel = sum(1 for f in fuesse_gebaut if f[2] == "Deckel")
    print(f"  [{name}] {len(fuesse_gebaut)} Fussmulden Ø{2*FOOT_R:.1f} x {FOOT_D} mm "
          f"({len(fuesse_gebaut) - n_deckel} in der Platte, {n_deckel} im Deckel), "
          f"{len(schrauben_gebaut)} Schrauben mit 90-Grad-Senkung")

    # Fase an der Oberkante: sauberer Uebergang zum Case, verdeckt den
    # Toleranzsprung zwischen Plattenkontur und Gehaeusekante.
    try:
        top = body.edges().filter_by(GeomType.LINE).group_by(Axis.Z)[-1]
        body = chamfer(top, length=CHAMFER)
        print(f"  Fase {CHAMFER} mm an {len(top)} Oberkanten gesetzt")
    except Exception as e:
        print(f"  KEINE Fase moeglich: {e}")

    G.stats(body)
    export_beides(body, f"plate_{name}")

    G.stats(lid)
    export_beides(lid, f"lid_{name}", nrm=n)

    print(f"  {name}: Flaeche {area/100:.1f} cm2, Keil {T_IN}->{T_OUT} mm, "
          f"Neigung {theta:.1f} deg, Fach bei u={bay_u:.1f} mm")
    return theta


for nm, cf in HALVES.items():
    build(nm, cf)
