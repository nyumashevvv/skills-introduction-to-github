"""Beach and sea props: sunbed, beach umbrella, longtail boat, island ferry,
waterfall rock face with a plunge pool.

  blender -b -P tools/blender/make_beach.py -- models/beach.glb [preview.png]

Face +Y in Blender (-Z in Godot). Boat origins sit on the waterline.
The waterfall's falling water is the object WaterfallWater (material "FallingWater"),
animated in the game by a shader.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "beach.glb"
PREVIEW = argv[1] if len(argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))
rnd = random.Random(9)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def mat(name, hexcol, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*srgb(hexcol), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


M = {
    "wood": mat("Wood", "8a5a36", 0.75),
    "wood_dark": mat("WoodDark", "5c3a22", 0.8),
    "cushion": mat("Cushion", "f2efe6", 0.8),
    "cushion2": mat("CushionBlue", "2f6aa8", 0.8),
    "canvas": mat("Umbrella", "f4f1e8", 0.7),
    "thatch": mat("Thatch", "b89462", 0.95),
    "pole": mat("Pole", "c8c3b8", 0.5),
    "hull_blue": mat("HullBlue", "2b5d8a", 0.5),
    "hull_white": mat("HullWhite", "f0f0ec", 0.4),
    "hull_red": mat("HullRed", "a8281f", 0.5),
    "ribbon_y": mat("RibbonYellow", "f2c230", 0.5),
    "ribbon_p": mat("RibbonPink", "e8509a", 0.5),
    "ribbon_g": mat("RibbonGreen", "2fa860", 0.5),
    "engine": mat("Engine", "3a3d40", 0.4, 0.6),
    "steel": mat("Steel", "a9adb0", 0.35, 0.8),
    "glass": mat("Glass", "2a3a46", 0.05, 0.3),
    "rock": mat("Granite", "7d756c", 0.9),
    "rock_wet": mat("GraniteWet", "4d4943", 0.35),
    "moss": mat("Moss", "3f5a2a", 0.9),
    "pool": mat("Pool", "2e6e68", 0.05),
    "falls": mat("FallingWater", "dff1f3", 0.1),
}


def box(name, m, loc, size, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    o.data.materials.append(M[m])
    if bevel:
        bpy.ops.object.transform_apply(scale=True)
        b = o.modifiers.new("b", "BEVEL")
        b.width = bevel
        b.segments = 2
        bpy.ops.object.modifier_apply(modifier="b")
    return o


def cyl(name, m, loc, r, h, rot=(0, 0, 0), verts=12, r2=None):
    bpy.ops.mesh.primitive_cone_add(location=loc, rotation=rot, radius1=r, radius2=r if r2 is None else r2, depth=h, vertices=verts)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(M[m])
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def join(name, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
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


def sunbed():
    p = [box("frame", "wood", (0, 0, 0.3), (0.7, 1.4, 0.06)),
         box("cushion", "cushion", (0, -0.1, 0.36), (0.66, 1.2, 0.07), bevel=0.02),
         box("back", "wood", (0, 0.75, 0.6), (0.7, 0.7, 0.05), rot=(math.radians(-50), 0, 0)),
         box("back_cushion", "cushion", (0, 0.72, 0.64), (0.64, 0.62, 0.06), rot=(math.radians(-50), 0, 0), bevel=0.02)]
    for x in (-0.3, 0.3):
        for y in (-0.6, 0.5):
            p.append(box(f"leg{x}{y}", "wood_dark", (x, y, 0.14), (0.05, 0.05, 0.28)))
    return join("Sunbed", p)


def umbrella(name, m, thatch=False):
    p = [cyl("pole", "pole" if not thatch else "wood", (0, 0, 1.25), 0.03 if not thatch else 0.06, 2.5)]
    if thatch:
        p.append(cyl("roof", m, (0, 0, 2.45), 1.6, 0.9, r2=0.1, verts=10))
        for k in range(10):  # ragged fringe
            a = k / 10 * math.tau
            p.append(box(f"fringe{k}", m, (math.cos(a) * 1.5, math.sin(a) * 1.5, 1.95), (0.5, 0.06, 0.25), rot=(0, 0, a + math.pi / 2)))
    else:
        p.append(cyl("canopy", m, (0, 0, 2.3), 1.35, 0.45, r2=0.04, verts=8))
    return join(name, p)


def longtail():
    """Thai longtail boat: long narrow hull, high curved bow with ribbons, engine on a pole."""
    bm = bmesh.new()
    L, W, D = 9.0, 1.3, 0.75
    rings = []
    n = 14
    for i in range(n + 1):
        t = i / n
        y = -L / 2 + L * t
        w = W / 2 * math.sin(math.pi * min(1.0, 0.12 + t * 0.95)) ** 0.6
        lift = 0.0 if t < 0.65 else (t - 0.65) ** 2 * 7.0   # bow sweeps up
        ring = [bm.verts.new((-w, y, 0.55 + lift)), bm.verts.new((-w * 0.7, y, -0.2 + lift * 0.8)),
                bm.verts.new((0, y, -0.32 + lift * 0.7)), bm.verts.new((w * 0.7, y, -0.2 + lift * 0.8)),
                bm.verts.new((w, y, 0.55 + lift))]
        rings.append(ring)
    for i in range(n):
        for k in range(4):
            bm.faces.new([rings[i][k], rings[i][k + 1], rings[i + 1][k + 1], rings[i + 1][k]])
    me = bpy.data.meshes.new("hull")
    bm.to_mesh(me)
    bm.free()
    hull = bpy.data.objects.new("hull", me)
    scene.collection.objects.link(hull)
    hull.data.materials.append(M["hull_blue"])
    hull.data.materials.append(M["hull_white"])
    for poly in hull.data.polygons:
        poly.use_smooth = True
        if poly.center.z > 0.3:
            poly.material_index = 1
    s = hull.modifiers.new("s", "SOLIDIFY")
    s.thickness = 0.06
    bpy.context.view_layer.objects.active = hull
    bpy.ops.object.modifier_apply(modifier="s")
    p = [hull]
    for k in range(4):
        p.append(box(f"seat{k}", "wood", (0, -2.5 + k * 1.4, 0.35), (1.0, 0.25, 0.05)))
    # ribbons and garland at the bow post
    p.append(cyl("bow_post", "wood_dark", (0, 4.45, 2.0), 0.07, 0.8))
    for k, m in enumerate(("ribbon_y", "ribbon_p", "ribbon_g")):
        p.append(box(f"ribbon{k}", m, (0.05 * (k - 1), 4.4, 1.6 - k * 0.15), (0.08, 0.04, 0.6), rot=(0.2 * k, 0, 0.3 * (k - 1))))
    # engine on a long shaft over the stern
    p.append(box("engine", "engine", (0, -4.6, 1.0), (0.5, 0.7, 0.5), bevel=0.05))
    p.append(cyl("shaft", "steel", (0, -6.6, 0.55), 0.04, 3.8, rot=(math.radians(80), 0, 0)))
    p.append(box("prop", "steel", (0, -8.4, 0.25), (0.35, 0.05, 0.12)))
    p.append(box("canopy", "canvas", (0, -0.5, 1.85), (1.3, 4.5, 0.05)))
    for x in (-0.6, 0.6):
        for y in (-2.6, 1.6):
            p.append(cyl(f"cpost{x}{y}", "steel", (x, y, 1.15), 0.025, 1.4, verts=6))
    return join("Longtail", p)


def ferry():
    p = [box("hull", "hull_white", (0, 0, 0.6), (8.0, 32.0, 2.6), bevel=0.4),
         box("stripe", "hull_red", (0, 0, 0.0), (8.05, 32.05, 0.5)),
         box("bow", "hull_white", (0, 17.0, 0.9), (5.5, 3.0, 2.0), rot=(math.radians(10), 0, 0), bevel=0.3),
         box("deck1", "hull_white", (0, -2, 3.2), (7.4, 22.0, 2.6), bevel=0.15),
         box("windows1", "glass", (0, -2, 3.4), (7.5, 20.0, 1.0)),
         box("deck2", "hull_white", (0, -4, 5.4), (6.6, 12.0, 1.8), bevel=0.15),
         box("windows2", "glass", (0, -4, 5.5), (6.7, 10.0, 0.8)),
         box("bridge", "hull_white", (0, 3.2, 6.9), (5.5, 3.0, 1.4), bevel=0.15),
         box("bridge_glass", "glass", (0, 4.75, 6.9), (5.0, 0.1, 0.8)),
         cyl("funnel", "hull_red", (0, -8.0, 7.2), 0.7, 2.6),
         box("railing", "steel", (0, 0, 4.7), (7.6, 24.0, 0.05))]
    return join("Ferry", p)


def waterfall():
    """Granite rock face ~14 m high with a ledge, a plunge pool at the bottom (towards +Y)."""
    p = []
    spots = []
    for xi in range(-4, 5):                      # a stepped granite wall behind the falls
        x = xi * 2.2
        top = 13.5 - abs(x) * 0.8
        z = 0.0
        while z < top:
            spots.append((x + rnd.uniform(-0.6, 0.6), rnd.uniform(-3.5, -1.2) - abs(x) * 0.15, z))
            z += rnd.uniform(1.8, 2.8)
    for i, (x, y, z) in enumerate(spots):
        r = rnd.uniform(1.4, 2.4)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=(x, y, z))
        o = bpy.context.active_object
        o.scale = (r * rnd.uniform(0.9, 1.4), r * 0.9, r * rnd.uniform(0.7, 1.1))
        o.rotation_euler = (rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 3))
        o.data.materials.append(M["rock_wet" if abs(x) < 2.5 else "rock"])
        seed = rnd.uniform(0, 9)
        for v in o.data.vertices:   # lumpy granite instead of a clean sphere
            n = v.co.normalized()
            v.co *= 1 + 0.18 * math.sin(n.x * 5 + seed) * math.cos(n.y * 4 - seed) + 0.08 * math.sin(n.z * 11 + seed)
            if v.co.z < -0.3:
                v.co.z = -0.3 - (v.co.z + 0.3) * 0.3
        for poly in o.data.polygons:
            poly.use_smooth = True
        p.append(o)
    # ledge the water pours over
    p.append(box("ledge", "rock_wet", (0, -0.8, 13.0), (4.0, 3.0, 1.2), bevel=0.4))
    for k in range(5):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=(rnd.uniform(-5, 5), rnd.uniform(4, 8), 0.2))
        o = bpy.context.active_object
        o.scale = (rnd.uniform(0.6, 1.3), rnd.uniform(0.6, 1.3), rnd.uniform(0.4, 0.8))
        o.data.materials.append(M["rock"])
        p.append(o)
    bpy.ops.mesh.primitive_cylinder_add(location=(0, 4.5, 0.05), radius=6.5, depth=0.1, vertices=32)
    pool = bpy.context.active_object
    pool.data.materials.append(M["pool"])
    p.append(pool)
    rocks = join("WaterfallRocks", p)
    # falling water sheet: curved strip from the ledge to the pool
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    rows = []
    for i in range(9):
        t = i / 8
        z = 13.2 * (1 - t)
        y = 0.9 + 1.6 * t ** 1.5
        w = 1.4 + 1.2 * t
        rows.append((bm.verts.new((-w, y, z)), bm.verts.new((w, y, z)), t))
    for i in range(8):
        a0, b0, t0 = rows[i]
        a1, b1, t1 = rows[i + 1]
        f = bm.faces.new([a0, b0, b1, a1])
        for loop, uvv in zip(f.loops, [(0, t0), (1, t0), (1, t1), (0, t1)]):
            loop[uv].uv = uvv
    me = bpy.data.meshes.new("WaterfallWater")
    bm.to_mesh(me)
    bm.free()
    water = bpy.data.objects.new("WaterfallWater", me)
    scene.collection.objects.link(water)
    water.data.materials.append(M["falls"])
    return [rocks, water]


objs = [sunbed(), umbrella("Umbrella", "canvas"), umbrella("UmbrellaThatch", "thatch", True), longtail(), ferry()] + waterfall()
print({o.name: len(o.data.polygons) for o in objs})

if PREVIEW:
    offs = [(-14, 0), (-11, 0), (-8, 0), (-2, 4), (12, 18), (-30, 6), (-30, 6)]
    for o, (x, y) in zip(objs, offs):
        o.location = (x, y, 0)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.location = (-5, -40, 18)
    cam.rotation_euler = (Vector((-5, 5, 3)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 26
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(50), 0, math.radians(20))
    scene.collection.objects.link(sun)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.7, 0.9, 1)
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=300)
    g = bpy.context.active_object
    g.data.materials.append(mat("Sand", "d9c9a0"))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 800
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    for o in (g, cam, sun):
        bpy.data.objects.remove(o)
    for o in objs:
        o.location = (0, 0, 0)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_yup=True, export_apply=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "beach.blend"))
print("exported", OUT)
