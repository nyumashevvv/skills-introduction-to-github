"""Traffic vehicles: sedan, pickup, songthaew (pickup taxi with a roof and
benches), scooter with rider. Generic shapes, no real makes or logos.

  blender -b -P tools/blender/make_vehicles.py -- models/vehicles.glb [preview.png]

Face +Y in Blender (-Z in Godot); origin on the ground between the axles.
Body paint uses the material named "Paint" so the game can recolour it.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "vehicles.glb"
PREVIEW = argv[1] if len(argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def mat(name, hexcol, rough=0.5, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*srgb(hexcol), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*srgb(hexcol), 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


M = {
    "paint": mat("Paint", "ffffff", 0.25, 0.4),
    "glass": mat("Glass", "1c2730", 0.05, 0.3),
    "tyre": mat("Tyre", "121212", 0.9),
    "rim": mat("Rim", "b0b3b5", 0.3, 0.9),
    "black": mat("Trim", "1d1e20", 0.6),
    "chrome": mat("Chrome", "d9d9d9", 0.15, 1.0),
    "head": mat("Headlight", "f4f6ff", 0.1, 0.0, 1.0),
    "tail": mat("Taillight", "b5120c", 0.2, 0.0, 1.0),
    "seat": mat("Bench", "5a3b26", 0.7),
    "skin": mat("Skin", "c99a74", 0.6),
    "shirt": mat("Shirt", "e8e2d4", 0.8),
    "helmet": mat("Helmet", "2b4c8c", 0.3),
}


def box(name, m, loc, size, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    o.data.materials.append(M[m])
    if bevel:
        bpy.ops.object.transform_apply(scale=True)
        b = o.modifiers.new("b", "BEVEL")
        b.width = bevel
        b.segments = 3
        bpy.ops.object.modifier_apply(modifier="b")
        for p in o.data.polygons:
            p.use_smooth = True
    return o


def wheel(name, x, y, r=0.32, w=0.22):
    parts = []
    bpy.ops.mesh.primitive_cylinder_add(location=(x, y, r), rotation=(0, math.pi / 2, 0), radius=r, depth=w, vertices=20)
    t = bpy.context.active_object
    t.data.materials.append(M["tyre"])
    parts.append(t)
    bpy.ops.mesh.primitive_cylinder_add(location=(x + math.copysign(w / 2 + 0.005, x), y, r), rotation=(0, math.pi / 2, 0),
                                        radius=r * 0.62, depth=0.02, vertices=20)
    h = bpy.context.active_object
    h.data.materials.append(M["rim"])
    parts.append(h)
    return parts


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


def lights(p, half_w, front_y, rear_y, z):
    for sx in (-1, 1):
        p.append(box(f"hl{sx}", "head", (sx * (half_w - 0.25), front_y, z), (0.32, 0.04, 0.12)))
        p.append(box(f"tl{sx}", "tail", (sx * (half_w - 0.18), rear_y, z), (0.22, 0.04, 0.14)))


def sedan():
    p = [box("body", "paint", (0, 0, 0.62), (1.74, 4.4, 0.62), 0.12),
         box("cabin", "paint", (0, -0.25, 1.12), (1.56, 2.2, 0.55), 0.14),
         box("glass", "glass", (0, -0.25, 1.13), (1.58, 2.0, 0.42), 0.1),
         box("bumper_f", "black", (0, 2.2, 0.45), (1.76, 0.12, 0.22)),
         box("bumper_r", "black", (0, -2.2, 0.45), (1.76, 0.12, 0.22)),
         box("grille", "black", (0, 2.21, 0.66), (0.9, 0.04, 0.16))]
    lights(p, 0.87, 2.21, -2.21, 0.72)
    for x in (-0.82, 0.82):
        for y in (1.35, -1.35):
            p += wheel("w", x, y, 0.31, 0.2)
    return join("Sedan", p)


def pickup(name="Pickup", songthaew=False):
    p = [box("hood", "paint", (0, 1.45, 0.78), (1.8, 1.7, 0.7), 0.1),
         box("cab", "paint", (0, 0.15, 1.15), (1.8, 1.2, 1.25), 0.12),
         box("glass", "glass", (0, 0.2, 1.42), (1.82, 1.0, 0.55), 0.06),
         box("bed_floor", "black", (0, -1.55, 0.72), (1.76, 2.2, 0.12)),
         box("bumper_f", "chrome", (0, 2.32, 0.5), (1.82, 0.12, 0.2)),
         box("grille", "black", (0, 2.31, 0.85), (1.2, 0.04, 0.3))]
    for sx in (-1, 1):
        p.append(box(f"bed_side{sx}", "paint", (sx * 0.86, -1.55, 0.98), (0.08, 2.2, 0.45)))
    p.append(box("tailgate", "paint", (0, -2.62, 0.98), (1.76, 0.08, 0.45)))
    if songthaew:
        # roof on posts, two long benches facing each other, step at the back
        p.append(box("roof", "paint", (0, -1.35, 2.25), (1.95, 2.9, 0.1), 0.03))
        p.append(box("roof_rack", "chrome", (0, -1.35, 2.34), (1.7, 2.6, 0.05)))
        for sx in (-1, 1):
            for y in (-0.2, -1.4, -2.55):
                p.append(box(f"post{sx}{y}", "chrome", (sx * 0.9, y, 1.68), (0.05, 0.05, 1.1)))
            p.append(box(f"bench{sx}", "seat", (sx * 0.6, -1.5, 1.05), (0.42, 2.0, 0.08)))
            p.append(box(f"back{sx}", "seat", (sx * 0.84, -1.5, 1.32), (0.06, 2.0, 0.42)))
        p.append(box("step", "chrome", (0, -2.85, 0.4), (1.2, 0.35, 0.05)))
    lights(p, 0.9, 2.31, -2.67, 0.92)
    for x in (-0.84, 0.84):
        for y in (1.5, -1.6):
            p += wheel("w", x, y, 0.36, 0.24)
    return join(name, p)


def scooter_npc():
    p = [box("body", "paint", (0, -0.25, 0.5), (0.34, 0.9, 0.3), 0.06),
         box("floor", "black", (0, 0.15, 0.33), (0.3, 0.5, 0.07)),
         box("shield", "paint", (0, 0.45, 0.7), (0.38, 0.12, 0.7), 0.04),
         box("seat", "black", (0, -0.27, 0.72), (0.3, 0.68, 0.1), 0.03),
         box("bars", "black", (0, 0.5, 1.1), (0.55, 0.1, 0.08)),
         box("hl", "head", (0, 0.58, 0.98), (0.18, 0.04, 0.08)),
         box("tl", "tail", (0, -0.72, 0.62), (0.16, 0.04, 0.06)),
         # rider
         box("torso", "shirt", (0, -0.2, 1.08), (0.38, 0.22, 0.52), 0.06),
         box("legs", "black", (0, 0.0, 0.72), (0.34, 0.5, 0.16), 0.04),
         box("arms", "shirt", (0, 0.2, 1.1), (0.52, 0.45, 0.1), 0.03),
         box("head", "skin", (0, -0.17, 1.47), (0.2, 0.22, 0.24), 0.08),
         box("helmet", "helmet", (0, -0.18, 1.55), (0.26, 0.3, 0.2), 0.09)]
    for y in (0.62, -0.6):
        p += wheel("w", 0.0001, y, 0.25, 0.1)
    return join("ScooterNPC", p)


objs = [sedan(), pickup(), pickup("Songthaew", True), scooter_npc()]
print({o.name: len(o.data.polygons) for o in objs})

if PREVIEW:
    cols = ["d8d8d8", "3b5fa8", "c8261d", "1f8a4a"]
    for i, o in enumerate(objs):
        o.location = (i * 4.0 - 6, 0, 0)
    M["paint"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*srgb("c8261d"), 1)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.location = (8, 11, 5)
    cam.rotation_euler = (Vector((0, 0, 0.8)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 30
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(50), 0, math.radians(160))
    scene.collection.objects.link(sun)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.7, 0.9, 1)
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=100)
    g = bpy.context.active_object
    g.data.materials.append(mat("Ground", "6b6b66"))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 700
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    M["paint"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 1, 1, 1)
    for o in (g, cam, sun):
        bpy.data.objects.remove(o)
    for o in objs:
        o.location = (0, 0, 0)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_yup=True, export_apply=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "vehicles.blend"))
print("exported", OUT)
