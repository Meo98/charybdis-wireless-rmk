#!/usr/bin/env python3
"""DES-Keycaps von der JLC3DP-Steg-Leiste trennen und fuer FDM aufbereiten.

Die Originaldateien in `jlc3dp-original/` haengen je 10 (Daumen: 6) Caps ueber
einen Steg an einer Leiste -- eine JLC3DP-Bestellanforderung, damit die Gruppe
als EIN Teil zaehlt. Fuer den eigenen Drucker braucht es Einzelteile.

Zwei Schnitte:
  1. z = -0.60  trennt die Caps voneinander (dort endet der Steg)
  2. z = +0.05  entfernt den Steg-Stummel unter dem Cap-Boden

Schnitt 2 laeuft als BOOLEAN, nicht als bisect+holes_fill. Der Cap-Boden ist ein
RING: sein Rand besteht aus zwei getrennten Schleifen (aussen und innen).
`holes_fill` deckelt jede Schleife einzeln ab und macht daraus zwei
ineinandersteckende Huellen statt eines Koerpers -- 0 non-manifold, aber Muell.

Aufruf:
    blender -b --factory-startup -noaudio -P keycaps_trennen.py
"""
import bpy, bmesh, math, os, sys, collections
from mathutils import Matrix

HIER      = os.path.dirname(os.path.abspath(bpy.data.filepath or __file__))
SRC       = os.path.join(HIER, "jlc3dp-original")
ZIEL      = os.path.join(HIER, "drucken")
Z_TRENN   = -0.60      # unterhalb: Leiste + Steg
Z_BODEN   =  0.05      # Cap-Unterkante liegt bei z=0.00

# Position in der Leiste (von -x nach +x) -> Dateiname. None = Dublette.
LEISTEN = {
    "r1":    {tuple(range(10)): "keycap-r1"},
    "r2":    {(0, 1, 2, 4, 5, 7, 8, 9): "keycap-r2", (3, 6): "keycap-r2-homing"},
    "r3":    {tuple(range(10)): "keycap-r3"},
    "thumb": {(0,): "keycap-daumen-a-L", (1,): "keycap-daumen-b",
              (2,): "keycap-daumen-c-L", (3,): "keycap-daumen-c-R",
              (4,): None,                (5,): "keycap-daumen-a-R"},
}
# erwartete Caps je Leiste -- faengt einen veraenderten Z_TRENN ab
ERWARTET = {"r1": 10, "r2": 10, "r3": 10, "thumb": 6}


def leeren():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.objects):
        for x in list(c):
            if getattr(x, "users", 0) == 0:
                c.remove(x)


def pruefen(ob, wo):
    """Harte Zusicherung: ein Koerper, geschlossen, positives Volumen."""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    vol = bm.calc_volume(signed=True)
    nm  = len([e for e in bm.edges if len(e.link_faces) != 2])
    rest = set(bm.faces); shells = 0
    while rest:
        st = [rest.pop()]; shells += 1
        while st:
            for e in st.pop().edges:
                for nb in e.link_faces:
                    if nb in rest:
                        rest.discard(nb); st.append(nb)
    bm.free()
    assert shells == 1, f"{wo}: {shells} Shells -- Ringflaeche falsch gefuellt?"
    assert nm == 0,     f"{wo}: {nm} offene/non-manifold Kanten"
    assert vol > 0,     f"{wo}: Volumen {vol:.1f} mm3 (Normalen invertiert?)"
    return vol


def trennschnitt(ob, zc):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                           plane_co=(0, 0, zc), plane_no=(0, 0, 1), clear_inner=True)
    offen = [e for e in bm.edges if len(e.link_faces) == 1]
    if offen:
        bmesh.ops.holes_fill(bm, edges=offen)   # hier ein einfacher Steg-Querschnitt
    bm.to_mesh(ob.data); bm.free(); ob.data.update()


def boden_kappen(ob, zc):
    bpy.ops.mesh.primitive_cube_add(size=1)
    box = bpy.context.object
    box.scale = (400, 400, 200); box.location = (0, 0, zc - 100)
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new("kappen", 'BOOLEAN')
    m.operation = 'DIFFERENCE'; m.solver = 'EXACT'; m.object = box
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(box, do_unlink=True)


def in_drucklage(ob):
    """Cap steht wie auf dem Switch: offener Bodenring auf dem Bett, z=0."""
    vs = [v.co for v in ob.data.vertices]
    cx = (min(p.x for p in vs) + max(p.x for p in vs)) / 2
    cy = (min(p.y for p in vs) + max(p.y for p in vs)) / 2
    ob.data.transform(Matrix.Translation((-cx, -cy, -min(p.z for p in vs))))
    ob.data.update()


os.makedirs(ZIEL, exist_ok=True)
zusammen = []
for leiste, karte in LEISTEN.items():
    leeren()
    bpy.ops.wm.stl_import(filepath=os.path.join(SRC, f"{leiste}.stl"))
    strip = bpy.context.selected_objects[0]
    trennschnitt(strip, Z_TRENN)
    bpy.ops.object.select_all(action='DESELECT'); strip.select_set(True)
    bpy.context.view_layer.objects.active = strip
    bpy.ops.mesh.separate(type='LOOSE')
    caps = sorted([o for o in bpy.context.scene.objects if o.type == 'MESH'],
                  key=lambda o: min(v.co.x for v in o.data.vertices))
    assert len(caps) == ERWARTET[leiste], \
        f"{leiste}: {len(caps)} Teile statt {ERWARTET[leiste]} -- Z_TRENN pruefen"

    fertig = set()
    for idx, name in karte.items():
        if name is None or name in fertig:
            continue
        cap = caps[idx[0]]
        boden_kappen(cap, Z_BODEN)
        vol = pruefen(cap, f"{leiste}[{idx[0]}]")
        in_drucklage(cap)
        bpy.ops.object.select_all(action='DESELECT'); cap.select_set(True)
        bpy.context.view_layer.objects.active = cap
        bpy.ops.wm.stl_export(filepath=os.path.join(ZIEL, name + ".stl"),
                              export_selected_objects=True)
        vs = [v.co for v in cap.data.vertices]
        zusammen.append((name, vol, max(p.z for p in vs),
                         max(p.x for p in vs) - min(p.x for p in vs),
                         max(p.y for p in vs) - min(p.y for p in vs),
                         len(cap.data.polygons)))
        fertig.add(name)

print("\n  Datei                        Volumen      Hoehe    Grundriss        Dreiecke")
for n, v, h, dx, dy, t in zusammen:
    print(f"  {n:26s} {v:8.1f} mm3  {h:6.2f}  {dx:6.2f} x {dy:6.2f}  {t:8d}")
print(f"\n  {len(zusammen)} Dateien in {ZIEL}")
