"""Roadside places: fuel station, 24-hour mini-mart, bottle fuel stand.
Unbranded on purpose (no real logos or trade dress).

  blender -b -P tools/blender/make_pois.py -- models/pois.glb [preview.png]

All face +Y in Blender (= -Z in Godot, towards the road); origin on the ground
at the front edge centre of the site.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "pois.glb"
PREVIEW = argv[1] if len(argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def mat(name, hexcol, rough=0.6, metal=0.0, emit=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*srgb(hexcol), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*srgb(hexcol), 1)
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
    return m


M = {
    "white": mat("White", "f2f2ee", 0.5),
    "canopy": mat("CanopyWhite", "f4f4f0", 0.4, 0.2),
    "band": mat("BandOrange", "e8761e", 0.45),
    "band2": mat("BandTeal", "1f8a8a", 0.45),
    "steel": mat("Steel", "a9adb0", 0.35, 0.8),
    "dark": mat("Dark", "2a2c2e", 0.6),
    "concrete": mat("Concrete", "b9b6ae", 0.85),
    "glass": mat("Glass", "3d5866", 0.05, 0.3),
    "light": mat("Light", "fff6e0", 0.2, 0.0, emit=3.0),
    "pump": mat("Pump", "e9e9e4", 0.4),
    "hose": mat("Hose", "111111", 0.7),
    "sign": mat("SignBlue", "1b4f9c", 0.4),
    "red": mat("Red", "c8261d", 0.45),
    "yellow": mat("Yellow", "f2c230", 0.45),
    "wood": mat("Wood", "7a5233", 0.8),
    "fuel_red": mat("FuelRed", "d8401f", 0.05, 0.0, alpha=0.85),
    "fuel_yel": mat("FuelYellow", "e6b422", 0.05, 0.0, alpha=0.85),
    "bottle": mat("BottleGlass", "cfe3e0", 0.05, 0.0, alpha=0.35),
    "ice": mat("IceBox", "e6eef5", 0.3),
    "text": mat("Text", "ffffff", 0.4),
}


def box(name, m, loc, size, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    o.data.materials.append(M[m])
    return o


def cyl(name, m, loc, r, h, rot=(0, 0, 0), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(location=loc, rotation=rot, radius=r, depth=h, vertices=verts)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(M[m])
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def text(name, body, m, loc, size, rot=(math.pi / 2, 0, math.pi), extrude=0.02):
    """Text standing upright, readable from the front (+Y)."""
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.body = body
    o.data.size = size
    o.data.extrude = extrude
    o.data.align_x = "CENTER"
    o.data.align_y = "CENTER"
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    o.data.materials.clear()
    o.data.materials.append(M[m])
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


def fuel_station():
    p = []
    # forecourt slab, set back from the road edge (y = 0)
    p.append(box("slab", "concrete", (0, -9, 0.05), (26, 18, 0.1)))
    # canopy on four columns, 5.2 m clearance, orange/teal fascia
    for x in (-5.5, 5.5):
        for y in (-5.0, -12.0):
            p.append(box(f"col{x}{y}", "white", (x, y, 2.6), (0.5, 0.5, 5.2)))
    p.append(box("canopy", "canopy", (0, -8.5, 5.45), (16, 11, 0.5)))
    for nm, loc, size in (("f_front", (0, -2.95, 5.55), (16.2, 0.12, 0.42)), ("f_back", (0, -14.05, 5.55), (16.2, 0.12, 0.42)),
                          ("f_left", (-8.05, -8.5, 5.55), (0.12, 11.2, 0.42)), ("f_right", (8.05, -8.5, 5.55), (0.12, 11.2, 0.42))):
        p.append(box(nm, "band", loc, size))
        p.append(box(nm + "_line", "band2", (loc[0], loc[1], 5.27), (size[0] + 0.02, size[1] + 0.02, 0.12)))
    for x in (-4, 0, 4):
        for y in (-6.5, -10.5):
            p.append(box(f"lamp{x}{y}", "light", (x, y, 5.18), (1.2, 0.5, 0.05)))
    # two pump islands with two dispensers each
    for x in (-3.2, 3.2):
        p.append(box(f"island{x}", "concrete", (x, -8.5, 0.15), (1.4, 7.0, 0.2)))
        for y in (-6.5, -10.5):
            p.append(box(f"pump{x}{y}", "pump", (x, y, 1.05), (0.9, 0.6, 1.7)))
            p.append(box(f"pump_band{x}{y}", "band", (x, y, 1.75), (0.92, 0.62, 0.25)))
            for sy in (-1, 1):
                p.append(box(f"screen{x}{y}{sy}", "dark", (x, y + sy * 0.31, 1.3), (0.6, 0.02, 0.35)))
            p.append(cyl(f"hose{x}{y}", "hose", (x + 0.48, y, 0.9), 0.03, 1.1))
    # kiosk shop at the back
    p.append(box("shop", "white", (0, -16, 1.7), (9, 4.5, 3.4)))
    p.append(box("shop_glass", "glass", (0, -13.74, 1.3), (6, 0.05, 2.2)))
    p.append(box("shop_band", "band2", (0, -13.7, 3.0), (9.1, 0.1, 0.6)))
    p.append(text("shop_text", "SHOP 24", "text", (0, -13.62, 3.0), 0.42))
    p.append(box("air", "red", (8.5, -6, 0.6), (0.5, 0.4, 1.2)))
    # price pylon by the road
    p.append(box("pylon", "white", (-11.5, -1.0, 3.2), (1.6, 0.5, 6.4)))
    p.append(box("pylon_top", "band", (-11.5, -1.0, 5.7), (1.7, 0.55, 1.4)))
    p.append(text("pylon_text", "FUEL", "text", (-11.5, -0.7, 5.7), 0.55))
    for i, y in enumerate((4.4, 3.6, 2.8)):
        p.append(box(f"price{i}", "dark", (-11.5, -0.73, y), (1.3, 0.05, 0.6)))
        p.append(box(f"price_d{i}", "light", (-11.2, -0.71, y), (0.55, 0.03, 0.35)))
    return join("FuelStation", p)


def minimart():
    p = []
    w, d, h = 10.0, 9.0, 4.2
    p.append(box("body", "white", (0, -d / 2 - 1.0, h / 2), (w, d, h)))
    p.append(box("step", "concrete", (0, -0.5, 0.08), (w + 0.4, 1.4, 0.16)))
    # glass front with white mullions and door
    p.append(box("glass", "glass", (0, -1.0 + 0.02, 1.45), (w - 1.0, 0.05, 2.5)))
    for k in range(6):
        p.append(box(f"mull{k}", "white", (-(w - 1.0) / 2 + k * (w - 1.0) / 5, -0.95, 1.45), (0.1, 0.08, 2.5)))
    p.append(box("door_frame", "steel", (0, -0.93, 1.2), (1.9, 0.08, 2.4)))
    # sign band (neutral colours, our own name)
    p.append(box("sign", "band2", (0, -0.85, 3.4), (w + 0.2, 0.15, 1.1)))
    p.append(box("sign_line", "band", (0, -0.8, 2.92), (w + 0.2, 0.1, 0.16)))
    p.append(text("sign_text", "MINI MART 24", "text", (0, -0.76, 3.42), 0.62))
    p.append(box("canopy", "band2", (0, -0.2, 3.05), (w, 1.8, 0.12), rot=(math.radians(-8), 0, 0)))
    # ice freezer, AC units, bench
    p.append(box("freezer", "ice", (3.6, 0.1, 0.55), (1.6, 0.8, 1.1)))
    p.append(box("ac", "white", (-4.2, -1.0 - d + 0.0, 2.8), (0.9, 0.4, 0.6)))
    p.append(box("bench", "red", (-3.4, 0.15, 0.45), (1.8, 0.5, 0.1)))
    for x in (-4.1, -2.7):
        p.append(box(f"bench_leg{x}", "dark", (x, 0.15, 0.22), (0.08, 0.4, 0.44)))
    return join("MiniMart", p)


def bottle_stand():
    """Wooden shelf of glass bottles with petrol, a classic Thai roadside sight."""
    p = []
    for x in (-0.55, 0.55):
        for y in (-0.15, -0.55):
            p.append(box(f"leg{x}{y}", "wood", (x, y, 0.65), (0.06, 0.06, 1.3)))
    for z in (0.45, 0.85, 1.25):
        p.append(box(f"shelf{z}", "wood", (0, -0.35, z), (1.25, 0.5, 0.04)))
        for i in range(6):
            x = -0.5 + i * 0.2
            m = "fuel_red" if (i + int(z * 10)) % 3 else "fuel_yel"
            p.append(cyl(f"fuel{z}{i}", m, (x, -0.3, z + 0.15), 0.045, 0.24, verts=10))
            p.append(cyl(f"neck{z}{i}", "bottle", (x, -0.3, z + 0.31), 0.018, 0.1, verts=8))
    p.append(box("sign", "yellow", (0, -0.1, 1.6), (0.8, 0.03, 0.35)))
    p.append(text("sign_text", "FUEL", "dark", (0, -0.08, 1.6), 0.22))
    p.append(cyl("funnel", "steel", (0.75, -0.3, 0.9), 0.08, 0.2, verts=10))
    # umbrella
    p.append(cyl("pole", "steel", (-0.8, -0.8, 1.2), 0.025, 2.4, verts=8))
    bpy.ops.mesh.primitive_cone_add(location=(-0.8, -0.8, 2.35), radius1=1.3, radius2=0.05, depth=0.5, vertices=12)
    u = bpy.context.active_object
    u.data.materials.append(M["red"])
    p.append(u)
    return join("BottleStand", p)


objs = [fuel_station(), minimart(), bottle_stand()]
print({o.name: len(o.data.polygons) for o in objs})

if PREVIEW:
    for i, o in enumerate(objs):
        o.location = (i * 22.0 - 22, 0, 0)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.location = (0, 34, 14)
    cam.rotation_euler = (Vector((0, -6, 2)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 28
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(50), 0, math.radians(160))
    scene.collection.objects.link(sun)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.7, 0.9, 1)
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=200)
    g = bpy.context.active_object
    g.data.materials.append(mat("Ground", "6d7356"))
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
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "pois.blend"))
print("exported", OUT)
