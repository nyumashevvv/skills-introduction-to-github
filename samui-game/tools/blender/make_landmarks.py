"""Koh Samui landmarks, modelled in Blender, exported as models/landmarks.glb.

  blender -b -P tools/blender/make_landmarks.py -- models/landmarks.glb [preview.png]

BigBuddha   Wat Phra Yai: 12 m golden Buddha in the earth-touching posture on a
            stepped white terrace; front stairs flanked by two emerald nagas.
Guanyin     Wat Plai Laem: white 18-armed Guan Yin on a lotus, platform in a pond.
Maitreya    Wat Plai Laem: the laughing Buddha.
Rocks       Hin Ta & Hin Yai granite boulders on the shore south of Lamai.
All face +Y in Blender (-Z in Godot); origin at ground level, centre of the base.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "landmarks.glb"
PREVIEW = argv[1] if len(argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))
rnd = random.Random(5)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, rgb, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


M = {
    "gold": mat("Gold", srgb("e8b33a"), 0.28, 1.0),
    "gold_dark": mat("GoldDark", srgb("b07d1e"), 0.35, 1.0),
    "white": mat("Plaster", srgb("f3f0e8"), 0.7),
    "red": mat("TempleRed", srgb("a81c12"), 0.5),
    "naga": mat("Naga", srgb("1d8a4a"), 0.35, 0.3),
    "naga_belly": mat("NagaBelly", srgb("d9b23a"), 0.4, 0.6),
    "stone": mat("Stone", srgb("9a958c"), 0.85),
    "granite": mat("Granite", srgb("8a8078"), 0.9),
    "statue_white": mat("StatueWhite", srgb("f5f3ee"), 0.45),
    "tile": mat("Tile", srgb("d96a1e"), 0.5),
    "water": mat("Pond", srgb("2f7f7a"), 0.05),
    "skin_gold": mat("Maitreya", srgb("f0c060"), 0.35, 0.8),
    "robe_red": mat("Robe", srgb("c0392b"), 0.5),
}


def link(o):
    scene.collection.objects.link(o)
    return o


def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for s in bpy.context.view_layer.objects:
        s.select_set(s == o)
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def shade_smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


def skin_figure(name, joints, edges, material, root, levels=2):
    names = list(joints)
    me = bpy.data.meshes.new(name)
    me.from_pydata([joints[n][0] for n in names], [(names.index(a), names.index(b)) for a, b in edges], [])
    o = link(bpy.data.objects.new(name, me))
    o.modifiers.new("skin", "SKIN")
    for i, n in enumerate(names):
        sv = o.data.skin_vertices[0].data[i]
        r = joints[n][1]
        sv.radius = (r, joints[n][2] if len(joints[n]) > 2 else r)
        sv.use_root = n == root
    s = o.modifiers.new("sub", "SUBSURF")
    s.levels = levels
    apply_mods(o)
    shade_smooth(o)
    o.data.materials.append(material)
    return o


def prim(kind, name, material, loc, scale=(1, 1, 1), rot=(0, 0, 0), **kw):
    getattr(bpy.ops.mesh, "primitive_" + kind + "_add")(location=loc, rotation=rot, **kw)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    if kind in ("uv_sphere", "ico_sphere", "torus", "cylinder", "cone"):
        shade_smooth(o)
    return o


def box(name, material, loc, size, bevel=0.0):
    o = prim("cube", name, material, loc, scale=(size[0] / 2, size[1] / 2, size[2] / 2))
    if bevel:
        b = o.modifiers.new("b", "BEVEL")
        b.width = bevel
        b.segments = 2
        bpy.ops.object.transform_apply(scale=True)
        apply_mods(o)
    return o


def tube(name, pts, radii, material, sides=10):
    bm = bmesh.new()
    rings = []
    for i, (p, r) in enumerate(zip(pts, radii)):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = t.orthogonal().normalized()
        b = t.cross(a).normalized()
        rings.append([bm.verts.new(p + (a * math.cos(k / sides * math.tau) + b * math.sin(k / sides * math.tau)) * r) for k in range(sides)])
    for i in range(len(rings) - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            bm.faces.new([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]])
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = link(bpy.data.objects.new(name, me))
    o.data.materials.append(material)
    shade_smooth(o)
    return o


def join(name, objs):
    for o in objs:
        bpy.context.view_layer.objects.active = o
        for s in bpy.context.view_layer.objects:
            s.select_set(s == o)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    o.data.name = name
    scene.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    return o


def lotus(name, z, r, h, material, petals=16):
    parts = [prim("cylinder", name + "_core", material, (0, 0, z + h / 2), vertices=32, radius=r * 0.9, depth=h)]
    for k in range(petals):
        a = k / petals * math.tau
        o = prim("uv_sphere", f"{name}_petal{k}", material, (math.cos(a) * r * 0.92, math.sin(a) * r * 0.92, z + h * 0.55),
                 scale=(r * 0.22, r * 0.12, h * 0.6), rot=(0, 0, a), segments=12, ring_count=8)
        parts.append(o)
    return parts


def seated_buddha(prefix, s, material, hands="earth"):
    """Seated Buddha, ~10 * s tall, sitting at z=0, facing +Y."""
    J = {
        "pelvis": ((0, 0, 1.9 * s), 2.1 * s, 1.6 * s),
        "waist": ((0, 0.1 * s, 3.2 * s), 1.75 * s, 1.35 * s),
        "chest": ((0, 0.05 * s, 4.7 * s), 2.0 * s, 1.35 * s),
        "neck": ((0, 0, 6.05 * s), 0.62 * s),
    }
    for side, sx in (("L", -1), ("R", 1)):
        J.update({
            f"sh{side}": ((sx * 1.85 * s, -0.05 * s, 5.55 * s), 0.72 * s),
            f"el{side}": ((sx * 2.35 * s, 0.45 * s, 3.55 * s), 0.58 * s),
            f"hip{side}": ((sx * 1.15 * s, 0.3 * s, 1.35 * s), 0.95 * s),
            f"knee{side}": ((sx * 2.75 * s, 1.9 * s, 0.95 * s), 0.85 * s),
            f"foot{side}": ((-sx * 0.7 * s, 2.35 * s, 1.35 * s), 0.5 * s, 0.35 * s),
        })
    if hands == "earth":
        J.update({"wrR": ((2.15 * s, 1.75 * s, 2.0 * s), 0.42 * s), "haR": ((2.2 * s, 2.25 * s, 1.15 * s), 0.42 * s, 0.25 * s),
                  "wrL": ((-0.9 * s, 1.6 * s, 2.25 * s), 0.42 * s), "haL": ((-0.1 * s, 1.75 * s, 2.15 * s), 0.45 * s, 0.25 * s)})
    else:  # both hands in the lap (meditation)
        J.update({"wrR": ((0.9 * s, 1.6 * s, 2.25 * s), 0.42 * s), "haR": ((0.15 * s, 1.75 * s, 2.2 * s), 0.45 * s, 0.25 * s),
                  "wrL": ((-0.9 * s, 1.6 * s, 2.25 * s), 0.42 * s), "haL": ((-0.15 * s, 1.75 * s, 2.15 * s), 0.45 * s, 0.25 * s)})
    E = [("pelvis", "waist"), ("waist", "chest"), ("chest", "neck")]
    for side in "LR":
        E += [("chest", f"sh{side}"), (f"sh{side}", f"el{side}"), (f"el{side}", f"wr{side}"), (f"wr{side}", f"ha{side}"),
              ("pelvis", f"hip{side}"), (f"hip{side}", f"knee{side}"), (f"knee{side}", f"foot{side}")]
    body = skin_figure(prefix + "_body", J, E, material, "pelvis")
    parts = [body]
    hc = Vector((0, 0.15 * s, 7.15 * s))
    parts.append(prim("uv_sphere", prefix + "_head", material, hc, scale=(1.0 * s, 1.08 * s, 1.22 * s), segments=24, ring_count=16))
    for sx in (-1, 1):  # long ears
        parts.append(prim("uv_sphere", f"{prefix}_ear{sx}", material, hc + Vector((sx * 1.0 * s, -0.1 * s, -0.45 * s)),
                          scale=(0.18 * s, 0.35 * s, 0.75 * s), segments=12, ring_count=8))
    parts.append(prim("uv_sphere", prefix + "_ushnisha", material, hc + Vector((0, -0.05 * s, 1.1 * s)),
                      scale=(0.62 * s, 0.62 * s, 0.55 * s), segments=16, ring_count=10))
    parts.append(prim("cone", prefix + "_flame", material, hc + Vector((0, -0.05 * s, 2.3 * s)), vertices=12,
                      radius1=0.32 * s, radius2=0.0, depth=1.7 * s))
    # robe edge over the left shoulder
    parts.append(tube(prefix + "_sash", [Vector((-1.6 * s, 0.9 * s, 5.4 * s)), Vector((-0.3 * s, 1.35 * s, 4.4 * s)),
                                         Vector((0.9 * s, 1.25 * s, 3.2 * s))], [0.16 * s] * 3, material, 8))
    return parts


def naga(prefix, start, end, side):
    """Serpent balustrade from the bottom (start) to the top (end) of the stairs, multi-headed hood at the bottom."""
    pts, radii = [], []
    n = 24
    for i in range(n + 1):
        t = i / n
        p = start.lerp(end, t) + Vector((0, 0, 0.55 + 0.25 * math.sin(t * math.pi * 6)))
        pts.append(p)
        radii.append(0.42 - 0.12 * t)
    parts = [tube(prefix + "_body", pts, radii, M["naga"], 12)]
    # belly ridge
    parts.append(tube(prefix + "_belly", [p - Vector((0, 0, 0.3)) for p in pts], [r * 0.55 for r in radii], M["naga_belly"], 8))
    head = start + Vector((0, -0.6, 1.4))
    for k in range(5):  # five-headed hood
        a = (k - 2) * 0.35
        hp = head + Vector((math.sin(a) * 1.0, -0.2, math.cos(a) * 1.1))
        parts.append(tube(f"{prefix}_neck{k}", [start + Vector((0, 0, 0.6)), head, hp], [0.42, 0.34, 0.26], M["naga"], 10))
        parts.append(prim("uv_sphere", f"{prefix}_head{k}", M["naga"], hp + Vector((0, -0.25, 0.05)),
                          scale=(0.3, 0.5, 0.28), segments=12, ring_count=8))
        parts.append(prim("cone", f"{prefix}_crest{k}", M["gold"], hp + Vector((0, -0.1, 0.42)), vertices=8,
                          radius1=0.12, radius2=0.0, depth=0.5))
    parts.append(prim("uv_sphere", prefix + "_hood", M["naga_belly"], head + Vector((0, -0.05, 0.9)), scale=(1.4, 0.25, 1.2),
                      segments=16, ring_count=10))
    return parts


# ------------------------------------------------------------------ Big Buddha (Wat Phra Yai)
def big_buddha():
    parts = []
    # terraces: lower 30 x 30 m (4 m), upper 18 x 18 m (2.5 m), white with red and gold trim
    t1, t2 = 4.0, 2.5
    parts.append(box("terrace1", M["white"], (0, -2, t1 / 2), (30, 30, t1), 0.05))
    parts.append(box("terrace1_band", M["red"], (0, -2, t1 - 0.35), (30.2, 30.2, 0.5)))
    parts.append(box("terrace1_gold", M["gold_dark"], (0, -2, t1 - 0.05), (30.4, 30.4, 0.12)))
    parts.append(box("terrace2", M["white"], (0, 0, t1 + t2 / 2), (18, 18, t2), 0.05))
    parts.append(box("terrace2_band", M["red"], (0, 0, t1 + t2 - 0.3), (18.2, 18.2, 0.45)))
    # balustrade posts around the upper terrace edge
    for k in range(40):
        a = k / 40
        side = int(a * 4)
        f = a * 4 - side
        p = [(-14.8 + 29.6 * f, -16.8), (14.8, -16.8 + 29.6 * f), (14.8 - 29.6 * f, 12.8), (-14.8, 12.8 - 29.6 * f)][side]
        if abs(p[0]) < 3.6 and p[1] > 12:
            continue
        parts.append(box(f"post{k}", M["gold_dark"], (p[0], p[1], t1 + 0.5), (0.25, 0.25, 1.0)))
    # plinth and lotus throne
    z0 = t1 + t2
    parts.append(prim("cylinder", "plinth", M["white"], (0, 0, z0 + 1.0), vertices=8, radius=6.2, depth=2.0))
    parts.append(prim("cylinder", "plinth_band", M["red"], (0, 0, z0 + 1.6), vertices=8, radius=6.3, depth=0.5))
    parts += lotus("lotus", z0 + 2.0, 5.6, 1.3, M["gold"])
    # the Buddha: about 12 m
    for o in seated_buddha("buddha", 1.12, M["gold"], "earth"):
        o.location.z += z0 + 3.1
        parts.append(o)
    # front staircase (towards +Y) from the ground to the upper terrace
    steps = 26
    for i in range(steps):
        h = (t1 + t2) * (i + 1) / steps
        y = 30.0 - i * 0.62
        parts.append(box(f"step{i}", M["white"], (0, y, h / 2), (6.0, 0.62, h)))
    for sx in (-1, 1):
        parts += naga(f"naga{sx}", Vector((sx * 3.5, 30.6, 0.0)), Vector((sx * 3.5, 13.8, t1 + t2)), sx)
    return join("BigBuddha", parts)


# ------------------------------------------------------------------ Wat Plai Laem: Guanyin
def guanyin():
    parts = []
    # round pond with a tiered white platform in the middle and a short bridge
    parts.append(prim("cylinder", "pond", M["water"], (0, 0, 0.05), vertices=48, radius=26, depth=0.1))
    parts.append(prim("torus", "pond_rim", M["white"], (0, 0, 0.15), major_radius=26.3, minor_radius=0.45,
                      major_segments=64, minor_segments=8))
    parts.append(prim("cylinder", "platform1", M["white"], (0, 0, 1.0), vertices=24, radius=9, depth=2.0))
    parts.append(prim("cylinder", "platform1_band", M["red"], (0, 0, 1.85), vertices=24, radius=9.1, depth=0.3))
    parts.append(prim("cylinder", "platform2", M["white"], (0, 0, 2.8), vertices=24, radius=6, depth=1.6))
    parts += lotus("lotus", 3.6, 4.2, 1.4, M["statue_white"], 20)
    parts.append(box("bridge", M["white"], (0, 17.5, 0.9), (3.0, 17, 0.3)))
    for sx in (-1, 1):
        parts.append(box(f"bridge_rail{sx}", M["red"], (sx * 1.45, 17.5, 1.5), (0.15, 17, 0.9)))
    # seated figure in white, crowned
    for o in seated_buddha("guanyin", 0.95, M["statue_white"], "lap"):
        o.location.z += 5.0
        parts.append(o)
    crown = prim("cone", "crown", M["gold"], (0, 0.1, 5.0 + 0.95 * 8.4), vertices=12, radius1=0.95, radius2=0.35, depth=1.4)
    parts.append(crown)
    # 18 arms fanned out behind the shoulders, each holding something
    sh = Vector((0, -0.4, 5.0 + 0.95 * 5.5))
    for side in (-1, 1):
        for k in range(9):
            a = math.radians(-50 + k * 17)
            d = Vector((side * math.cos(a), -0.25, math.sin(a)))
            base = sh + Vector((side * 1.4, 0, 0))
            elbow = base + d * 2.6 + Vector((0, 0.2, 0))
            hand = elbow + (d + Vector((0, 0.6, 0.2))).normalized() * 2.2
            parts.append(tube(f"arm{side}_{k}", [base, elbow, hand], [0.42, 0.34, 0.26], M["statue_white"], 8))
            item = prim("uv_sphere", f"item{side}_{k}", M["gold"], hand + Vector((0, 0.15, 0.25)), scale=(0.28, 0.28, 0.4),
                        segments=10, ring_count=6)
            parts.append(item)
    # two small Chinese pagodas on the platform rim
    for sx in (-1, 1):
        for lvl in range(5):
            r = 1.2 - lvl * 0.18
            parts.append(prim("cylinder", f"pagoda{sx}_{lvl}", M["red"] if lvl % 2 else M["white"],
                              (sx * 12, -8, 0.6 + lvl * 1.3), vertices=8, radius=r, depth=1.0))
            parts.append(prim("cylinder", f"pagoda_roof{sx}_{lvl}", M["tile"], (sx * 12, -8, 1.2 + lvl * 1.3), vertices=8,
                              radius=r + 0.5, depth=0.25))
    return join("Guanyin", parts)


def maitreya():
    parts = [prim("cylinder", "base", M["white"], (0, 0, 0.8), vertices=16, radius=4.0, depth=1.6)]
    z = 1.6
    parts.append(prim("uv_sphere", "legs", M["robe_red"], (0, 0.4, z + 0.9), scale=(3.0, 2.2, 1.1), segments=24, ring_count=12))
    parts.append(prim("uv_sphere", "belly", M["skin_gold"], (0, 0.5, z + 2.6), scale=(2.4, 2.2, 2.2), segments=24, ring_count=16))
    parts.append(prim("uv_sphere", "chest", M["robe_red"], (0, -0.3, z + 3.9), scale=(2.3, 1.6, 1.4), segments=24, ring_count=12))
    parts.append(prim("uv_sphere", "head", M["skin_gold"], (0, 0.1, z + 5.8), scale=(1.25, 1.25, 1.3), segments=24, ring_count=16))
    for sx in (-1, 1):
        parts.append(prim("uv_sphere", f"ear{sx}", M["skin_gold"], (sx * 1.2, 0, z + 5.6), scale=(0.2, 0.4, 0.7), segments=10, ring_count=6))
        parts.append(tube(f"arm{sx}", [Vector((sx * 2.0, -0.3, z + 4.1)), Vector((sx * 2.8, 0.4, z + 2.6)), Vector((sx * 2.0, 1.6, z + 1.9))],
                          [0.6, 0.5, 0.45], M["skin_gold"], 10))
    # smile and closed eyes, carved in darker gold
    parts.append(tube("smile", [Vector((-0.55, 1.3, z + 5.35)), Vector((0, 1.38, z + 5.15)), Vector((0.55, 1.3, z + 5.35))], [0.06] * 3, M["gold_dark"], 6))
    for sx in (-1, 1):
        parts.append(tube(f"eye{sx}", [Vector((sx * 0.25, 1.23, z + 6.0)), Vector((sx * 0.45, 1.25, z + 5.92)), Vector((sx * 0.65, 1.18, z + 6.0))], [0.04] * 3, M["gold_dark"], 6))
    return join("Maitreya", parts)


def rocks():
    parts = []
    spots = [((0, 0, 0), (2.2, 2.0, 4.8), 0.0), ((4.5, 1.5, 0), (3.2, 2.6, 2.4), 0.6), ((-4, 2, 0), (3.8, 3.0, 2.0), 1.2),
             ((2, -4, 0), (4.5, 3.5, 2.6), 2.0), ((-3, -5, 0), (3.0, 2.6, 1.8), 2.8), ((7, -3, 0), (2.4, 2.0, 1.4), 3.5),
             ((-7, -1, 0), (2.6, 2.4, 1.6), 4.2), ((5, 6, 0), (2.8, 2.2, 1.2), 5.0)]
    for i, (c, sc, rot) in enumerate(spots):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=(c[0], c[1], sc[2] * 0.75), rotation=(0, 0, rot))
        o = bpy.context.active_object
        o.name = f"rock{i}"
        o.scale = sc
        for v in o.data.vertices:
            n = v.co.normalized()
            v.co *= 1 + 0.12 * math.sin(n.x * 4 + i) * math.cos(n.y * 3 + i) + 0.05 * math.sin(n.z * 9)
        o.data.materials.append(M["granite"])
        shade_smooth(o)
        parts.append(o)
    return join("Rocks", parts)


objs = [big_buddha(), guanyin(), maitreya(), rocks()]
print({o.name: len(o.data.polygons) for o in objs})

if PREVIEW:
    for i, o in enumerate(objs):
        o.location = (i * 45.0, 0, 0)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    link(cam)
    cam.location = (60, 120, 45)
    cam.rotation_euler = (Vector((60, 0, 8)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 30
    scene.camera = cam
    sun = link(bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")))
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(50), 0, math.radians(200))
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.7, 0.9, 1)
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=400)
    ground = bpy.context.active_object
    ground.data.materials.append(mat("Ground", srgb("7d8a5a")))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 800
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    for o in (ground, cam, sun):
        bpy.data.objects.remove(o)
    for o in objs:
        o.location = (0, 0, 0)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_yup=True, export_apply=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "landmarks.blend"))
print("exported", OUT)
