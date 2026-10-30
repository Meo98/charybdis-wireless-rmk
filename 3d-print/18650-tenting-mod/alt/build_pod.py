# 18650-Akku-Pod + Klick-Tenting-Fuesse fuer Charybdis Wireless Mini 3x6
# Pod haengt unter der Bodenplatte an 2 vorhandenen M4-Positionen (M4x12 statt M4x8).
# Huelse (oben offen zur Platte) nimmt einen generischen 1x18650-Drahthalter auf.
# Schwalbenschwanz-Schiene unten: Fuesse in Stufenhoehen aufklickbar (Rastkerben).
import math, os
from build123d import *
import b3d_gate as G

OUT = "/home/meo/Dokumente/Private/charybdis-wireless-mini-3x6-build-guide-main/3d-print/18650-tenting-mod"
os.makedirs(OUT, exist_ok=True)
# veraltete, defekte _print-Varianten aus dem ersten Lauf aufraeumen
import glob as _glob
for _f in _glob.glob(f"{OUT}/*_print.*"):
    os.remove(_f)

# ---------------- Parameter (alle mm) ----------------
# MPD BH-18650-W, Masse aus dem Datenblatt (Rev. G, 08/21/24) verifiziert:
# 77.7 x 20.9 x 21.31 mm, 24AWG-Draehte 150 mm, "designed for use with
# protected 18650 batteries (PCB)" - steht wortwoertlich auf der Zeichnung.
HOLDER_L, HOLDER_W, HOLDER_H = 77.7, 20.9, 21.31
CLR = 0.7
CAV_L = HOLDER_L + 2 * CLR          # 79.1
CAV_W = HOLDER_W + 2 * CLR          # 22.3
CAV_D = HOLDER_H + CLR              # 22.01 - Halter darf NICHT ueberstehen, sonst
                                    # bockt er die Bodenplatte auf (21.31 > 21.0!)
WALL = 2.65
FLOOR = 3.0
FLAN_T = 4.0
PAD_R = 6.5
SCREW_R = 2.3                       # M4 Durchgang
CSK_R = 5.4                         # M4 Senkkopf
SLV_W = CAV_W + 2 * WALL            # 27.7
SLV_L = CAV_L + 2 * WALL            # 84.7
SLV_X0 = 0.5                        # Huelsen-Westkante oestlich der Schraubenachse
BONE_W = 14.0                       # Stegbreite ausserhalb der Huelse (ab Schraubenachse)
SLV_Y0 = 2.0                        # Huelse/Schiene nach Norden versetzt (Platte laeuft im Sueden schraeg zu)
RAIL_ROOT, RAIL_CREST, RAIL_H = 8.0, 11.0, 3.5
RAIL_L = 76.0
NOTCH_R, NOTCH_STEP, NOTCH_DEPTH = 1.2, 12.0, 0.5
CHAMF = 4.0
FOOT_L, FOOT_WALL = 25.0, 3.0
FOOT_W = RAIL_CREST + 0.5 + 2 * FOOT_WALL       # 17.5
GROOVE_ROOT, GROOVE_CREST, GROOVE_D = 8.5, 11.5, 3.7
FOOT_BASE = 5.0
FOOT_HEIGHTS = [8.0, 16.0]
BUMP_R = 1.2
SPAN_R = 95.22                      # rechte Platte (-92.40,56.98)-(-103.07,-37.64)
SPAN_L = 93.64                      # linke Platte  (90.62,57.43)-(104.90,-35.11)
M_R = (-97.73, 9.67); UX_R = (0.9937, -0.1121)
BUMPER = (28.0, 20.0); PAD_H = 4.0

POD_DEPTH = CAV_D + FLOOR           # 24
CREST_Z = POD_DEPTH + RAIL_H        # 27.5

def tent_angle(extra):
    cx = M_R[0] + UX_R[0] * (SLV_X0 + SLV_W / 2)
    cy = M_R[1] + UX_R[1] * (SLV_X0 + SLV_W / 2)
    lever = abs((BUMPER[0] - cx) * UX_R[0] + (BUMPER[1] - cy) * UX_R[1])
    return math.degrees(math.atan2(CREST_Z + extra - PAD_H, lever)), lever

TH0, LEVER = tent_angle(0)
angles = {h: tent_angle(h + FOOT_BASE + FOOT_WALL - GROOVE_D)[0] for h in FOOT_HEIGHTS}
print(f"Hebelarm {LEVER:.1f} mm | Grundwinkel {TH0:.1f} deg | " +
      ", ".join(f"h{h:g}->{a:.1f} deg" for h, a in angles.items()))

VP = Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))  # vertikale Ebene, v -> global z

def build_pod(span):
    xc = SLV_X0 + SLV_W / 2
    with BuildPart() as p:
        with Locations((xc, SLV_Y0, -POD_DEPTH / 2)):
            Box(SLV_W, SLV_L, POD_DEPTH)
        assert abs(p.part.volume - SLV_W * SLV_L * POD_DEPTH) < 1e-6
        # Flansch: volle Breite NUR ueber der Huelse, danach schmaler Steg zu den Pads.
        # (Die linke Platte laeuft im Sueden schraeg zu; ein durchgehend breiter
        #  Flansch ragte dort ueber die Plattenkante hinaus.)
        with BuildSketch(Plane.XY) as sk:
            with Locations((xc, SLV_Y0)):
                RectangleRounded(SLV_W, SLV_L, 3.0)
            Rectangle(BONE_W, span, align=(Align.MIN, Align.CENTER))
            with Locations((0, span / 2), (0, -span / 2)):
                Circle(PAD_R)
        extrude(amount=-FLAN_T)
        # Kavitaet, oben offen zur Platte (Kabel gehen durchs Voronoi-Gitter)
        vpre = p.part.volume
        with Locations((xc, SLV_Y0, -CAV_D / 2)):
            Box(CAV_W, CAV_L, CAV_D, mode=Mode.SUBTRACT)
        assert abs((vpre - p.part.volume) - CAV_W * CAV_L * CAV_D) < 1e-3, "Kavitaet daneben"
        # Bruecken-Fasen: 45-Grad-Keile unten an beiden Kavitaeten-Laengskanten (additiv)
        vpre = p.part.volume
        for sx in (+1, -1):
            wp = Plane(origin=(xc + sx * CAV_W / 2, SLV_Y0, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
            with BuildSketch(wp):
                Polygon((0, -CAV_D + CHAMF), (0, -CAV_D), (-sx * CHAMF, -CAV_D), align=None)
            extrude(amount=CAV_L / 2, both=True)
        assert abs((p.part.volume - vpre) - CHAMF * CHAMF * CAV_L) < 1e-3, "Fasen daneben"
        # Schwalbenschwanz-Schiene (Krone unten breiter -> Hinterschnitt)
        rp = Plane(origin=(xc, SLV_Y0, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
        with BuildSketch(rp):
            Polygon((-RAIL_ROOT / 2, -POD_DEPTH), (RAIL_ROOT / 2, -POD_DEPTH),
                    (RAIL_CREST / 2, -CREST_Z), (-RAIL_CREST / 2, -CREST_Z), align=None)
        extrude(amount=RAIL_L / 2, both=True)
        # Rastkerben quer ueber die Krone
        n = int(RAIL_L // NOTCH_STEP)
        for i in range(n):
            y = SLV_Y0 + (-(n - 1) / 2 + i) * NOTCH_STEP
            with Locations((xc, y, -CREST_Z - NOTCH_R + NOTCH_DEPTH)):
                Cylinder(NOTCH_R, 40, rotation=(0, 90, 0), mode=Mode.SUBTRACT)
        # M4: Durchgang + Senkung von der Flansch-Unterseite
        for sy in (+1, -1):
            with Locations((0, sy * span / 2, -FLAN_T / 2)):
                Cylinder(SCREW_R, FLAN_T + 2, mode=Mode.SUBTRACT)
            with Locations((0, sy * span / 2, -FLAN_T)):
                Cone(CSK_R, SCREW_R, CSK_R - SCREW_R,
                     align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
    return p.part

def build_foot(h, angle_deg):
    tot = GROOVE_D + FOOT_WALL + h + FOOT_BASE
    with BuildPart() as f:
        with Locations((0, 0, -tot / 2)):
            Box(FOOT_W, FOOT_L, tot)
        with BuildSketch(VP):
            Polygon((-GROOVE_ROOT / 2, 0), (GROOVE_ROOT / 2, 0),
                    (GROOVE_CREST / 2, -GROOVE_D), (-GROOVE_CREST / 2, -GROOVE_D), align=None)
        extrude(amount=FOOT_L / 2, both=True, mode=Mode.SUBTRACT)
        # Rastnase im Nutgrund
        with Locations((0, 0, -GROOVE_D - BUMP_R + (NOTCH_DEPTH - 0.05))):
            Cylinder(BUMP_R, FOOT_W - 2, rotation=(0, 90, 0))
    # Bodenschraege = Tentwinkel; tiefster Punkt bleibt an der Westkante (-x)
    # (Cut ausserhalb des Builders: im Builder wuerde der Box-Konstruktor sofort ADDen)
    a = math.radians(angle_deg)
    c = -tot + math.tan(a) * FOOT_W / 2
    cut = Box(80, 80, 40, align=(Align.CENTER, Align.CENTER, Align.MAX))
    cut = cut.rotate(Axis.Y, -angle_deg).translate((0, 0, c))
    foot = f.part - cut
    assert 3000 < foot.volume < 12000, f"Fussvolumen unplausibel: {foot.volume}"
    return foot

# ---------------- Bauen + Export ----------------
pod_r = build_pod(SPAN_R)
pod_l = mirror(build_pod(SPAN_L), about=Plane.YZ)
G.stats(pod_r); G.stats(pod_l)
G.export(pod_r, f"{OUT}/pod_right")
G.export(pod_l, f"{OUT}/pod_left")

for h in FOOT_HEIGHTS:
    foot_r = build_foot(h, angles[h])
    foot_l = mirror(foot_r, about=Plane.YZ)
    for part, name in [(foot_r, f"foot_h{h:g}_right"), (foot_l, f"foot_h{h:g}_left")]:
        G.export(part, f"{OUT}/{name}")

# Fit-Coupon: 45-mm-Schienenstueck mit 3 Kerben auf Sockel
with BuildPart() as c:
    with Locations((0, 0, 1.5)):
        Box(RAIL_CREST + 8, 45, 3)
    with BuildSketch(VP):
        Polygon((-RAIL_ROOT / 2, 3), (RAIL_ROOT / 2, 3),
                (RAIL_CREST / 2, 3 + RAIL_H), (-RAIL_CREST / 2, 3 + RAIL_H), align=None)
    extrude(amount=45 / 2, both=True)
    for y in (-NOTCH_STEP, 0, NOTCH_STEP):
        with Locations((0, y, 3 + RAIL_H + NOTCH_R - NOTCH_DEPTH)):
            Cylinder(NOTCH_R, 40, rotation=(0, 90, 0), mode=Mode.SUBTRACT)
G.stats(c.part)
G.export(c.part, f"{OUT}/rail_fit_coupon")
print("FERTIG. Winkel:", {f"h{h:g}": round(a, 1) for h, a in angles.items()}, f"| Grund {TH0:.1f} deg")
