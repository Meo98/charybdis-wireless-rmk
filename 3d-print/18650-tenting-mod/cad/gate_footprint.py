#!/usr/bin/env python3
"""Gate: liegt der Pod-Umriss vollstaendig innerhalb der Bodenplatten-Kontur?

Rechnet den Pod-Umriss (Schnitt bei z=-1, also der Flansch, der die Platte
beruehrt) ins Koordinatensystem der Original-Bodenplatte und prueft Punkt fuer
Punkt. Enthaelt einen Rot-Nachweis: derselbe Umriss 12 mm nach aussen geschoben
MUSS durchfallen, sonst prueft der Test nichts.

Aufruf:  python3 gate_footprint.py            (Platten-STLs werden erzeugt)
Exit 0 = gruen.
"""
import math, struct, sys, zipfile, os, collections
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PODDIR = sys.argv[1] if len(sys.argv) > 1 else HERE   # optional: anderes Pod-Verzeichnis pruefen
PLATES = os.path.join(HERE, "..", "bottom-plates")
NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

# Frames der beiden Platten: Ursprung = Mitte zwischen den zwei inneren
# M4-Loechern, +y = zur ersten Schraube, +x = rechtwinklig davon.
CASES = [
    dict(plate="right-plate.3mf", obj="right_plate", z=-8.3,
         M=(-97.73, 9.67), UX=(0.9937, -0.1121), UY=(0.1121, 0.9937),
         pod="pod_right.stl", span=95.22, out=+1),
    dict(plate="left-plate.3mf", obj="left_plate", z=2.7,
         M=(97.76, 11.16), UX=(0.9883, 0.1525), UY=(-0.1525, 0.9883),
         pod="pod_left.stl", span=93.64, out=-1),
]


def load_3mf(path, name):
    z = zipfile.ZipFile(path)
    root = ET.parse(z.open("3D/3dmodel.model")).getroot()
    for o in root.findall('.//m:object', NS):
        if o.get('name') != name:
            continue
        mesh = o.find('m:mesh', NS)
        vs = [(float(v.get('x')) * 1000, float(v.get('y')) * 1000, float(v.get('z')) * 1000)
              for v in mesh.find('m:vertices', NS)]          # 3MF ist in Metern!
        tr = [(int(t.get('v1')), int(t.get('v2')), int(t.get('v3')))
              for t in mesh.find('m:triangles', NS)]
        return [(vs[a], vs[b], vs[c]) for a, b, c in tr]
    raise SystemExit(f"Objekt {name} nicht in {path}")


def load_stl(path):
    with open(path, 'rb') as f:
        f.seek(80)
        n = struct.unpack('<I', f.read(4))[0]
        return [((d[3], d[4], d[5]), (d[6], d[7], d[8]), (d[9], d[10], d[11]))
                for d in (struct.unpack('<12fH', f.read(50)) for _ in range(n))]


def slice_loops(tris, zc):
    segs = []
    for a, b, c in tris:
        pts = []
        for p, q in ((a, b), (b, c), (c, a)):
            if (p[2] - zc) * (q[2] - zc) < 0:
                t = (zc - p[2]) / (q[2] - p[2])
                pts.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
        if len(pts) == 2:
            segs.append(pts)
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    adj = collections.defaultdict(list)
    for i, (p, q) in enumerate(segs):
        adj[key(p)].append((i, key(q)))
        adj[key(q)].append((i, key(p)))
    used, loops = set(), []
    for i, (p, q) in enumerate(segs):
        if i in used:
            continue
        loop = [key(p), key(q)]
        used.add(i)
        while True:
            nxt = next(((j, o) for j, o in adj[loop[-1]] if j not in used), None)
            if not nxt:
                break
            used.add(nxt[0])
            loop.append(nxt[1])
            if loop[-1] == loop[0]:
                break
        loops.append(loop)
    return loops


def inside(loop, x, y):
    cnt = 0
    for i in range(len(loop) - 1):
        (x1, y1), (x2, y2) = loop[i], loop[i + 1]
        if (y1 > y) != (y2 > y):
            if x1 + (y - y1) / (y2 - y1) * (x2 - x1) > x:
                cnt += 1
    return cnt % 2 == 1


def dist_to_loop(loop, x, y):
    best = 9e9
    for i in range(len(loop) - 1):
        (x1, y1), (x2, y2) = loop[i], loop[i + 1]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2)) if L2 else 0.0
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


def main():
    ok = True
    for c in CASES:
        outer = max(slice_loops(load_3mf(os.path.join(PLATES, c["plate"]), c["obj"]), c["z"]),
                    key=len)
        pod = os.path.join(PODDIR, c["pod"])
        if not os.path.exists(pod):
            print(f"FEHLT: {pod}")
            return 2
        pts = [p for lp in slice_loops(load_stl(pod), -1.0) for p in lp]
        M, UX, UY = c["M"], c["UX"], c["UY"]
        g = lambda lx, ly: (M[0] + UX[0] * lx + UY[0] * ly, M[1] + UX[1] * lx + UY[1] * ly)

        outside = [p for p in pts if not inside(outer, *g(*p))]
        red = [p for p in pts if not inside(outer, *g(p[0] - c["out"] * 12, p[1]))]
        margin = min(dist_to_loop(outer, *g(*p)) for p in pts)

        good = not outside and bool(red)
        ok &= good
        print(f"{c['pod']}: ausserhalb {len(outside)} | Rot-Nachweis {len(red)} | "
              f"min. Randabstand {margin:.2f} mm -> {'GRUEN' if good else 'ROT'}")
        for sy in (+1, -1):
            gx, gy = g(0, sy * c["span"] / 2)
            print(f"    Schraubloch ({gx:.2f}, {gy:.2f})")
    print("GESAMT:", "GRUEN" if ok else "ROT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
