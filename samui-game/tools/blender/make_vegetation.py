"""Builds Koh Samui vegetation in Blender and exports models/vegetation.glb.

  python3 tools/blender/make_leaf_textures.py tools/blender/tex
  blender -b -P tools/blender/make_vegetation.py -- models/vegetation.glb [preview.png]

Objects (origin on the ground at the base, Z up in Blender):
  PalmTall, PalmShort, PalmLean, PalmLo      coconut palms (+ low-detail version)
  TreeJungle, TreeTall, TreeLo               broadleaf rainforest trees
  Banana, Bush, Bougainvillea, Grass         undergrowth
  FarCanopy                                  cheap blob for distant forest
Leaves are alpha-cut textured cards (painted by make_leaf_textures.py).
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "vegetation.glb"
PREVIEW = argv[1] if len(argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")
rnd = random.Random(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def tex_mat(name, image, rough=0.8, cutout=True):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(os.path.join(TEX, image))
    nt.links.new(img.outputs["Color"], b.inputs["Base Color"])
    if cutout:
        nt.links.new(img.outputs["Alpha"], b.inputs["Alpha"])
        m.blend_method = "CLIP"
        m.alpha_threshold = 0.5
    b.inputs["Roughness"].default_value = rough
    m.use_backface_culling = False
    return m


def col_mat(name, rgb, rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = rough
    return m


M = {
    "frond": tex_mat("PalmFrond", "palm_frond.png"),
    "frond_dry": tex_mat("PalmFrondDry", "palm_frond_dry.png"),
    "trunk": tex_mat("PalmTrunk", "palm_trunk.png", 0.95, cutout=False),
    "bark": tex_mat("Bark", "bark.png", 0.95, cutout=False),
    "jungle": tex_mat("LeavesJungle", "leaves_jungle.png"),
    "light": tex_mat("LeavesLight", "leaves_light.png"),
    "bougain": tex_mat("Bougainvillea", "leaves_bougainvillea.png"),
    "banana": tex_mat("BananaLeaf", "banana_leaf.png", 0.6),
    "grass": tex_mat("Grass", "grass.png"),
    "coconut": col_mat("Coconut", (0.16, 0.22, 0.04), 0.6),
    "canopy": tex_mat("Canopy", "canopy.png", 0.9, cutout=False),
    "stem": col_mat("BananaStem", (0.18, 0.3, 0.08), 0.7),
}


class Builder:
    """Collects faces with UVs and materials, then makes one object."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new()
        self.mats = []

    def mat_index(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def face(self, pts, uvs, m, smooth=True):
        vs = [self.bm.verts.new(p) for p in pts]
        f = self.bm.faces.new(vs)
        f.material_index = self.mat_index(m)
        f.smooth = smooth
        for loop, uv in zip(f.loops, uvs):
            loop[self.uv].uv = uv
        return f

    def strip(self, left, mid, right, m):
        """Two-sided V-folded strip: rows of (left, mid, right) points, v along."""
        n = len(mid)
        for i in range(n - 1):
            v0, v1 = i / (n - 1), (i + 1) / (n - 1)
            self.face([left[i], mid[i], mid[i + 1], left[i + 1]], [(0, v0), (0.5, v0), (0.5, v1), (0, v1)], m)
            self.face([mid[i], right[i], right[i + 1], mid[i + 1]], [(0.5, v0), (1, v0), (1, v1), (0.5, v1)], m)

    def card(self, center, size, yaw, m, tilt=0.0, up=0.0):
        """Vertical (or tilted) textured quad."""
        d = Vector((math.cos(yaw), math.sin(yaw), 0))
        n = Vector((-d.y, d.x, 0))
        w, h = size
        up_v = Vector((0, 0, 1)) * math.cos(tilt) + n * math.sin(tilt)
        c = Vector(center) + Vector((0, 0, up))
        p = [c - d * w / 2 - up_v * h / 2, c + d * w / 2 - up_v * h / 2, c + d * w / 2 + up_v * h / 2, c - d * w / 2 + up_v * h / 2]
        self.face(p, [(0, 0), (1, 0), (1, 1), (0, 1)], m)

    def hcard(self, center, size, yaw, m, sag=0.0):
        """Near-horizontal card (canopy layer), randomly tilted so layers don't line up."""
        tilt = rnd.uniform(-0.45, 0.45)
        d = Vector((math.cos(yaw), math.sin(yaw), math.sin(tilt)))
        n = Vector((-math.sin(yaw), math.cos(yaw), math.sin(rnd.uniform(-0.45, 0.45))))
        c = Vector(center)
        s = size / 2
        p = [c - d * s - n * s - Vector((0, 0, sag)), c + d * s - n * s - Vector((0, 0, sag)),
             c + d * s + n * s - Vector((0, 0, sag)), c - d * s + n * s - Vector((0, 0, sag))]
        self.face(p, [(0, 0), (1, 0), (1, 1), (0, 1)], m)

    def tube(self, path, radii, m, sides=8, v_scale=1.0):
        rings = []
        for i, (p, r) in enumerate(zip(path, radii)):
            t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
            a = t.orthogonal().normalized()
            b = t.cross(a).normalized()
            rings.append([p + (a * math.cos(k / sides * math.tau) + b * math.sin(k / sides * math.tau)) * r for k in range(sides)])
        vlen = 0.0
        for i in range(len(rings) - 1):
            seg = (path[i + 1] - path[i]).length
            for k in range(sides):
                k2 = (k + 1) % sides
                u0, u1 = k / sides, (k + 1) / sides
                self.face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]],
                          [(u0, vlen), (u1, vlen), (u1, vlen + seg * v_scale), (u0, vlen + seg * v_scale)], m)
            vlen += seg * v_scale

    def sphere(self, c, r, m, segs=8):
        tmp = bmesh.new()
        bmesh.ops.create_uvsphere(tmp, u_segments=segs, v_segments=segs // 2, radius=r)
        for f in tmp.faces:
            self.face([Vector(c) + v.co for v in f.verts], [(0, 0)] * len(f.verts), m)
        tmp.free()

    def blob(self, c, scale, m, subdiv=2, noise=0.18, lumps=0.0):
        """Lumpy canopy volume with a wrapped leaf texture."""
        tmp = bmesh.new()
        bmesh.ops.create_icosphere(tmp, subdivisions=subdiv, radius=1.0)
        seed = rnd.uniform(0, 10)
        for f in tmp.faces:
            pts, uvs = [], []
            for v in f.verts:
                n = v.co.normalized()
                k = 1 + noise * math.sin(n.x * 5.1 + n.y * 3.7 + seed) * math.cos(n.z * 4.3 + seed)
                k += lumps * max(0.0, math.sin(n.x * 9 + seed) * math.sin(n.y * 8) * math.sin(n.z * 7 + seed))
                if n.z < -0.3:
                    k *= 0.75 + 0.25 * (1 + n.z)   # flatter underside
                pts.append(Vector(c) + Vector((n.x * scale[0], n.y * scale[1], n.z * scale[2])) * k)
                uvs.append(((math.atan2(n.y, n.x) / math.tau + 0.5) * 3, (n.z * 0.5 + 0.5) * 1.5))
            # fix the seam
            us = [u for u, _ in uvs]
            if max(us) - min(us) > 1.5:
                uvs = [(u + 3 if u < 1.5 else u, v) for u, v in uvs]
            self.face(pts, uvs, m)
        tmp.free()

    def finish(self):
        me = bpy.data.meshes.new(self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        scene.collection.objects.link(o)
        return o


# ------------------------------------------------------------------ coconut palm
def frond(b, base, yaw, pitch, length, droop, m=None, width=None):
    m = m or M["frond"]
    d0 = Vector((math.cos(yaw) * math.cos(pitch), math.sin(yaw) * math.cos(pitch), math.sin(pitch)))
    side = Vector((-math.sin(yaw), math.cos(yaw), 0))
    w = width or length * 0.36
    L, Mi, R = [], [], []
    n = 9
    for i in range(n):
        t = i / (n - 1)
        p = Vector(base) + d0 * length * t + Vector((0, 0, -droop * length * t * t))
        ww = w * (0.15 + 0.85 * math.sin(math.pi * min(1.0, 0.1 + t)))
        fold = ww * 0.35
        Mi.append(p)
        L.append(p + side * ww / 2 - Vector((0, 0, fold)))
        R.append(p - side * ww / 2 - Vector((0, 0, fold)))
    b.strip(L, Mi, R, m)


def palm(name, height, lean, curve, fronds=16, dry=2, nuts=6):
    b = Builder(name)
    lean_dir = Vector((1, 0, 0))
    path, radii = [], []
    n = 12
    for i in range(n + 1):
        t = i / n
        off = lean_dir * (lean * t + curve * math.sin(t * math.pi * 0.9)) * height
        path.append(Vector((0, 0, height * t)) + off)
        radii.append(0.27 * (1 - t) ** 3 * 0.6 + 0.16 - 0.04 * t)
    b.tube(path, radii, M["trunk"], sides=8, v_scale=1.0 / 1.6)
    top = path[-1]
    tan = (path[-1] - path[-2]).normalized()
    b.blob(top + Vector((0, 0, 0.15)), (0.28, 0.28, 0.35), M["trunk"], 1, 0.05)
    for k in range(fronds):
        yaw = k / fronds * math.tau + rnd.uniform(-0.15, 0.15)
        young = k % 4 == 0
        pitch = math.radians(rnd.uniform(48, 70) if young else rnd.uniform(5, 30))
        L = rnd.uniform(3.6, 4.8) * (0.8 if young else 1.0)
        frond(b, top + tan * 0.1, yaw, pitch, L, 0.25 if young else rnd.uniform(0.45, 0.7))
    for k in range(dry):  # dead fronds hanging down the trunk
        yaw = rnd.uniform(0, math.tau)
        frond(b, top - Vector((0, 0, 0.2)), yaw, math.radians(-62), 3.2, 0.1, M["frond_dry"])
    for k in range(nuts):
        a = k / nuts * math.tau
        b.sphere(top + Vector((math.cos(a) * 0.28, math.sin(a) * 0.28, -0.3 - 0.1 * (k % 2))), 0.13, M["coconut"])
    return b.finish()


def palm_lo(name):
    b = Builder(name)
    path = [Vector((0, 0, 0)), Vector((0.3, 0, 5)), Vector((0.7, 0, 10))]
    b.tube(path, [0.2, 0.16, 0.14], M["trunk"], sides=4, v_scale=1 / 1.6)
    for k in range(6):
        yaw = k / 6 * math.tau
        d = Vector((math.cos(yaw), math.sin(yaw), 0))
        n = Vector((-d.y, d.x, 0))
        top = path[-1]
        tip = top + d * 4.2 - Vector((0, 0, 1.4))
        mid = top + d * 2.0 + Vector((0, 0, 0.3))
        w = 0.8
        b.face([top + n * 0.1, top - n * 0.1, mid - n * w, mid + n * w], [(0.6, 0), (0.4, 0), (0, 0.5), (1, 0.5)], M["frond"])
        b.face([mid + n * w, mid - n * w, tip - n * 0.2, tip + n * 0.2], [(1, 0.5), (0, 0.5), (0.4, 1), (0.6, 1)], M["frond"])
    return b.finish()


# ------------------------------------------------------------------ broadleaf trees
def broadleaf(name, height, crown_r, crown_h, cards, leaves, flat=False):
    b = Builder(name)
    trunk_top = Vector((0, 0, height - crown_h * 0.6))
    path = [Vector((0, 0, 0)), Vector((0.1, 0.05, height * 0.35)), trunk_top]
    b.tube(path, [0.38 if flat else 0.26, 0.22, 0.16], M["bark"], sides=7, v_scale=0.5)
    # a few branches
    for k in range(5):
        a = k / 5 * math.tau + 0.4
        end = trunk_top + Vector((math.cos(a) * crown_r * 0.6, math.sin(a) * crown_r * 0.6, crown_h * 0.35))
        b.tube([trunk_top, (trunk_top + end) / 2 + Vector((0, 0, 0.3)), end], [0.1, 0.07, 0.04], M["bark"], sides=5, v_scale=0.5)
    cz = height - crown_h * 0.45
    # dark inner volume so the crown never looks hollow
    b.blob((0, 0, cz), (crown_r * 0.85, crown_r * 0.85, crown_h * 0.45), M["canopy"], 2, 0.2, 0.25)
    for k in range(cards):
        a = rnd.uniform(0, math.tau)
        r = crown_r * math.sqrt(rnd.uniform(0.15, 1.0)) * 0.85
        z = cz + rnd.uniform(-0.35, 0.45) * crown_h * (0.5 if flat else 1.0)
        c = Vector((math.cos(a) * r, math.sin(a) * r, z))
        s = rnd.uniform(2.2, 3.2) * crown_r / 3.0
        if rnd.random() < 0.55:
            b.hcard(c + Vector((0, 0, 0.2)), s * 1.2, rnd.uniform(0, math.pi), leaves, sag=0.15)
        else:
            b.card(c, (s, s), a + math.pi / 2 + rnd.uniform(-0.4, 0.4), leaves, tilt=rnd.uniform(-0.4, 0.4))
    return b.finish()


def tree_lo(name):
    b = Builder(name)
    b.tube([Vector((0, 0, 0)), Vector((0, 0, 5))], [0.22, 0.15], M["bark"], sides=4, v_scale=0.5)
    b.blob((0, 0, 7.5), (3.6, 3.6, 2.9), M["canopy"], 2, 0.22, 0.3)
    return b.finish()


def far_canopy(name):
    b = Builder(name)
    b.blob((0, 0, 7.0), (4.2, 4.2, 3.2), M["canopy"], 1, 0.25, 0.2)
    return b.finish()


# ------------------------------------------------------------------ undergrowth
def banana(name):
    b = Builder(name)
    b.tube([Vector((0, 0, 0)), Vector((0, 0, 2.6))], [0.16, 0.12], M["stem"], sides=6, v_scale=1)
    for k in range(9):
        yaw = k / 9 * math.tau + rnd.uniform(-0.2, 0.2)
        frond(b, (0, 0, 2.5 + 0.1 * (k % 3)), yaw, math.radians(rnd.uniform(35, 70)), rnd.uniform(2.2, 2.9),
              rnd.uniform(0.25, 0.45), M["banana"], width=0.75)
    return b.finish()


def bush(name, leaves, r=1.0, h=1.2, cards=7):
    b = Builder(name)
    b.blob((0, 0, h * 0.45), (r * 0.75, r * 0.75, h * 0.42), M["canopy"], 1, 0.2, 0.2)
    for k in range(cards):
        a = k / cards * math.pi + rnd.uniform(-0.2, 0.2)
        b.card((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), h * 0.5), (r * 2.0, h), a, leaves)
    b.hcard((0, 0, h * 0.95), r * 1.9, 0.3, leaves, sag=0.1)
    return b.finish()


def grass(name):
    b = Builder(name)
    for k in range(3):
        b.card((0, 0, 0.32), (1.2, 0.64), k * math.pi / 3, M["grass"])
    return b.finish()


objs = [
    palm("PalmTall", 12.0, 0.04, 0.05),
    palm("PalmShort", 8.0, 0.02, 0.02, fronds=14, dry=3),
    palm("PalmLean", 11.0, 0.32, 0.08, fronds=15),
    palm_lo("PalmLo"),
    broadleaf("TreeJungle", 11.0, 3.6, 5.5, 44, M["jungle"]),
    broadleaf("TreeTall", 19.0, 5.5, 5.0, 56, M["light"], flat=True),
    tree_lo("TreeLo"),
    far_canopy("FarCanopy"),
    banana("Banana"),
    bush("Bush", M["jungle"]),
    bush("Bougainvillea", M["bougain"], r=1.2, h=1.8, cards=8),
    grass("Grass"),
]
for i, o in enumerate(objs):
    o.location = (i * 9.0, 0, 0)  # spread out for the preview only; reset before export
print({o.name: len(o.data.polygons) for o in objs})

if PREVIEW:
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.location = (50, -75, 14)
    cam.rotation_euler = (Vector((50, 0, 6)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 26
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(45), 0, math.radians(30))
    scene.collection.objects.link(sun)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.65, 0.85, 1)
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=300)
    ground = bpy.context.active_object
    ground.data.materials.append(col_mat("Ground", (0.25, 0.3, 0.12)))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 700
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(ground)
    bpy.data.objects.remove(cam)
    bpy.data.objects.remove(sun)

for o in objs:
    o.location = (0, 0, 0)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_yup=True,
                          export_apply=True, export_materials="EXPORT", export_image_format="AUTO")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "vegetation.blend"))
print("exported", OUT)
