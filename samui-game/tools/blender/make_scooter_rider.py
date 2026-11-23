"""Builds the scooter and its rider in Blender and exports them as glTF.

  blender -b -P tools/blender/make_scooter_rider.py -- models/scooter_rider.glb [preview.png]

Also saves tools/blender/scooter_rider.blend for editing by hand.

Blender axes: X right, Y forward, Z up. The exporter turns this into glTF Y-up
with the scooter facing -Z, which is "forward" in Godot. Origin: on the ground
between the wheels. Objects: ScooterBody, WheelFront, WheelRear, Rider.
Rider outfit: black and green (jacket, joggers, sneakers, helmet, sunglasses).
"""
import math
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "scooter_rider.glb"
PREVIEW = argv[1] if len(argv) > 1 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


# ------------------------------------------------------------------ materials
def mat(name, rgb, rough=0.5, metal=0.0, emit=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = 2.0
    return m


def srgb(h):
    """hex -> linear rgb"""
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


M = {
    "paint": mat("Paint_Black", srgb("111413"), 0.22, 0.35),
    "paint_green": mat("Paint_Green", srgb("1fbf5b"), 0.3, 0.3),
    "plastic": mat("Plastic_Black", srgb("1a1a1a"), 0.65),
    "rubber": mat("Rubber", srgb("0d0d0d"), 0.9),
    "seat": mat("Seat_Leather", srgb("141414"), 0.55),
    "chrome": mat("Chrome", srgb("d9d9d9"), 0.15, 1.0),
    "alu": mat("Aluminium", srgb("8c9094"), 0.35, 1.0),
    "rim": mat("Rim_Black", srgb("202020"), 0.35, 0.6),
    "headlight": mat("Headlight", srgb("f5f5ff"), 0.05, 0.0, emit=srgb("fff6e0")),
    "taillight": mat("Taillight", srgb("b0100c"), 0.15, 0.0, emit=srgb("ff1a10")),
    "indicator": mat("Indicator", srgb("ff8c10"), 0.2),
    "plate": mat("Plate", srgb("f2f2ea"), 0.6),
    "glass": mat("Mirror", srgb("9fb0bf"), 0.05, 1.0),
    # rider
    "skin": mat("Skin", srgb("c99a74"), 0.6),
    "jacket": mat("Jacket_Black", srgb("16181a"), 0.7),
    "jacket_green": mat("Jacket_Green", srgb("1ecf62"), 0.6),
    "pants": mat("Joggers_Black", srgb("1c1d1f"), 0.85),
    "shoe": mat("Sneaker_Black", srgb("121212"), 0.6),
    "sole": mat("Sole_Green", srgb("2be070"), 0.5),
    "helmet": mat("Helmet_Black", srgb("0e0f10"), 0.18, 0.2),
    "lens": mat("Lens_Green", srgb("0b3d22"), 0.05, 0.8),
    "hair": mat("Hair", srgb("1a120c"), 0.8),
}


# ------------------------------------------------------------------ helpers
def link(obj):
    scene.collection.objects.link(obj)
    return obj


def new_obj(name, bm, material=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = link(bpy.data.objects.new(name, me))
    if material:
        o.data.materials.append(material)
    return o


def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for s in bpy.context.view_layer.objects:
        s.select_set(s == o)
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def smooth(o, levels=2, bevel=0.0, segments=2):
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = segments
    if levels:
        s = o.modifiers.new("subsurf", "SUBSURF")
        s.levels = levels
        s.render_levels = levels
    apply_mods(o)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def box(name, size, loc, material, rot=(0, 0, 0), taper=None, levels=2, bevel=0.0):
    """Box with optional taper {'top': (sx, sy), 'front': (sx, sz)} then subdivided."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        x, y, z = v.co
        if taper:
            if "top" in taper and z > 0:
                x *= taper["top"][0]
                y *= taper["top"][1]
            if "front" in taper and y > 0:
                x *= taper["front"][0]
                z *= taper["front"][1]
            if "shift_top" in taper and z > 0:
                y += taper["shift_top"]
        v.co = Vector((x * size[0], y * size[1], z * size[2]))
    o = new_obj(name, bm, material)
    o.location = loc
    o.rotation_euler = rot
    smooth(o, levels, bevel)
    return o


def cyl(name, r, depth, loc, material, rot=(0, 0, 0), verts=24, r2=None, levels=0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=depth)
    o = new_obj(name, bm, material)
    o.location = loc
    o.rotation_euler = rot
    if levels:
        smooth(o, levels)
    else:
        for p in o.data.polygons:
            p.use_smooth = True
    return o


def sphere(name, r, loc, material, scale=(1, 1, 1), segs=24):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=r)
    o = new_obj(name, bm, material)
    o.location = loc
    o.scale = scale
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def torus(name, R, r, loc, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=40, minor_segments=14,
                                     location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def join(name, objs, origin=None):
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
    if origin is not None:
        scene.cursor.location = origin
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    return o


# ------------------------------------------------------------------ scooter
R_WHEEL = 0.28
FRONT_Y, REAR_Y = 0.66, -0.62


def wheel(name, y):
    parts = []
    c = Vector((0, y, R_WHEEL))
    rot = (0, math.pi / 2, 0)
    parts.append(torus(name + "_tire", R_WHEEL - 0.07, 0.07, c, M["rubber"], rot))
    parts.append(cyl(name + "_rim", R_WHEEL - 0.115, 0.09, c, M["rim"], rot, verts=32))
    parts.append(cyl(name + "_lip", R_WHEEL - 0.105, 0.1, c, M["alu"], rot, verts=32, r2=R_WHEEL - 0.105))
    parts.append(cyl(name + "_hub", 0.05, 0.14, c, M["alu"], rot))
    parts.append(cyl(name + "_disc", 0.11, 0.012, c + Vector((-0.055, 0, 0)), M["chrome"], rot, verts=32))
    for k in range(5):  # spokes
        a = k * 2 * math.pi / 5
        d = Vector((0, math.cos(a), math.sin(a)))
        parts.append(box(f"{name}_spoke{k}", (0.03, 0.15, 0.025), c + d * 0.1, M["rim"],
                         rot=(a, 0, 0), levels=1))
    w = join(name, parts, origin=c)
    return w


body = []
# rear cowl: long, tapered, raised at the back
body.append(box("rear_cowl", (0.36, 0.95, 0.34), (0, -0.33, 0.56), M["paint"],
                taper={"top": (0.85, 0.9), "front": (0.8, 0.75)}, bevel=0.04))
# green side stripes on the cowl
for sx in (-1, 1):
    body.append(box(f"stripe{sx}", (0.01, 0.7, 0.035), (sx * 0.172, -0.33, 0.6), M["paint_green"],
                    rot=(math.radians(6), 0, 0), levels=1))
    body.append(box(f"stripe_low{sx}", (0.01, 0.45, 0.02), (sx * 0.165, -0.42, 0.5), M["paint_green"],
                    rot=(math.radians(6), 0, 0), levels=1))
# floorboard and tunnel
body.append(box("floor", (0.34, 0.5, 0.07), (0, 0.13, 0.33), M["plastic"], bevel=0.02, levels=1))
for i in range(5):
    body.append(box(f"floor_rib{i}", (0.28, 0.02, 0.012), (0, -0.05 + i * 0.09, 0.37), M["rubber"], levels=0))
body.append(box("underbody", (0.26, 0.6, 0.12), (0, 0.05, 0.26), M["plastic"], bevel=0.02))
# leg shield / front apron, tilted back
body.append(box("apron", (0.44, 0.14, 0.78), (0, 0.45, 0.68), M["paint"], rot=(math.radians(-14), 0, 0),
                taper={"top": (0.72, 1.0), "front": (0.95, 1.0)}, bevel=0.03))
body.append(box("apron_inner", (0.34, 0.05, 0.6), (0, 0.36, 0.66), M["plastic"], rot=(math.radians(-14), 0, 0), bevel=0.02))
body.append(box("apron_stripe", (0.06, 0.02, 0.55), (0, 0.53, 0.68), M["paint_green"], rot=(math.radians(-14), 0, 0), levels=1))
# headlight nose and handlebar cover
body.append(box("nose", (0.3, 0.2, 0.18), (0, 0.6, 1.0), M["paint"], rot=(math.radians(-14), 0, 0), bevel=0.03))
body.append(box("headlight", (0.22, 0.04, 0.08), (0, 0.7, 1.0), M["headlight"], rot=(math.radians(-14), 0, 0), levels=1))
body.append(box("bar_cover", (0.52, 0.2, 0.12), (0, 0.5, 1.13), M["paint"], taper={"top": (0.9, 0.8)}, bevel=0.03))
body.append(box("dash", (0.2, 0.1, 0.02), (0, 0.46, 1.19), M["glass"], rot=(math.radians(-20), 0, 0), levels=0))
for sx in (-1, 1):
    body.append(cyl(f"bar{sx}", 0.012, 0.16, (sx * 0.3, 0.5, 1.12), M["chrome"], rot=(0, math.pi / 2, 0)))
    body.append(cyl(f"grip{sx}", 0.02, 0.12, (sx * 0.4, 0.5, 1.12), M["rubber"], rot=(0, math.pi / 2, 0), verts=16))
    body.append(box(f"lever{sx}", (0.16, 0.015, 0.01), (sx * 0.38, 0.56, 1.13), M["alu"], levels=0))
    body.append(cyl(f"mirror_stalk{sx}", 0.007, 0.16, (sx * 0.27, 0.49, 1.24), M["chrome"], rot=(0, sx * 0.45, 0), verts=8))
    body.append(box(f"mirror{sx}", (0.12, 0.03, 0.07), (sx * 0.31, 0.49, 1.32), M["plastic"], levels=2, bevel=0.01))
    body.append(box(f"indicator_f{sx}", (0.06, 0.03, 0.03), (sx * 0.2, 0.67, 1.06), M["indicator"], levels=1))
    body.append(box(f"indicator_r{sx}", (0.05, 0.03, 0.03), (sx * 0.12, -0.82, 0.62), M["indicator"], levels=1))
# front fender + fork
# curved front mudguard hugging the tyre
bpy.ops.mesh.primitive_torus_add(major_radius=R_WHEEL + 0.035, minor_radius=0.05, major_segments=48, minor_segments=10,
                                 location=(0, FRONT_Y, R_WHEEL), rotation=(0, math.pi / 2, 0))
fender = bpy.context.active_object
fender.name = "fender_f"
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
bm = bmesh.new()
bm.from_mesh(fender.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < 0.06 or v.co.y < -0.12], context="VERTS")
bm.to_mesh(fender.data)
bm.free()
fender.scale = (2.4, 1.0, 1.0)
fender.data.materials.append(M["paint"])
for p in fender.data.polygons:
    p.use_smooth = True
body.append(fender)
for sx in (-1, 1):
    body.append(cyl(f"fork{sx}", 0.025, 0.62, (sx * 0.075, FRONT_Y - 0.04, 0.6), M["chrome"],
                    rot=(math.radians(-14), 0, 0), verts=12))
# seat: black leather with green piping
body.append(box("seat", (0.32, 0.74, 0.11), (0, -0.27, 0.79), M["seat"], taper={"top": (0.92, 0.95)}, bevel=0.04))
body.append(box("seat_piping", (0.33, 0.75, 0.012), (0, -0.27, 0.745), M["paint_green"], levels=1))
body.append(box("grab_rail", (0.3, 0.08, 0.03), (0, -0.72, 0.8), M["alu"], bevel=0.01, levels=1))
# rear light, plate, fender
body.append(box("taillight", (0.18, 0.04, 0.06), (0, -0.82, 0.68), M["taillight"], levels=1))
body.append(box("rear_fender", (0.14, 0.2, 0.18), (0, -0.82, 0.5), M["plastic"], rot=(math.radians(25), 0, 0), bevel=0.02))
body.append(box("plate", (0.17, 0.01, 0.1), (0, -0.92, 0.47), M["plate"], rot=(math.radians(15), 0, 0), levels=0))
# engine, swingarm, exhaust
body.append(box("engine", (0.2, 0.5, 0.18), (-0.1, -0.45, 0.3), M["alu"], bevel=0.03))
body.append(box("belt_cover", (0.05, 0.6, 0.16), (-0.17, -0.5, 0.3), M["plastic"], bevel=0.02))
body.append(cyl("shock", 0.025, 0.3, (0.12, -0.62, 0.45), M["paint_green"], rot=(math.radians(20), 0, 0), verts=10))
body.append(cyl("exhaust", 0.045, 0.45, (0.16, -0.62, 0.3), M["chrome"], rot=(math.radians(80), 0, 0), verts=16))
body.append(box("heat_shield", (0.03, 0.3, 0.07), (0.205, -0.6, 0.31), M["plastic"], rot=(math.radians(-10), 0, 0), levels=1))
body.append(cyl("kickstand", 0.012, 0.3, (-0.12, -0.1, 0.18), M["alu"], rot=(math.radians(-60), math.radians(20), 0), verts=8))

scooter = join("ScooterBody", body, origin=(0, 0, 0))
wf = wheel("WheelFront", FRONT_Y)
wr = wheel("WheelRear", REAR_Y)


# ------------------------------------------------------------------ rider
# skeleton for the skin modifier: (name, position, skin radius x, radius y)
J = {
    "pelvis": ((0, -0.24, 0.9), 0.15, 0.11),
    "spine": ((0, -0.25, 1.05), 0.14, 0.1),
    "chest": ((0, -0.21, 1.22), 0.17, 0.11),
    "neck": ((0, -0.16, 1.42), 0.055, 0.055),
    "head_base": ((0, -0.14, 1.47), 0.06, 0.06),
}
for s, sx in (("L", -1), ("R", 1)):
    J.update({
        f"shoulder{s}": ((sx * 0.2, -0.18, 1.36), 0.065, 0.065),
        f"elbow{s}": ((sx * 0.29, 0.1, 1.17), 0.05, 0.05),
        f"wrist{s}": ((sx * 0.37, 0.43, 1.13), 0.035, 0.03),
        f"hand{s}": ((sx * 0.39, 0.5, 1.12), 0.045, 0.03),
        f"hip{s}": ((sx * 0.1, -0.2, 0.86), 0.09, 0.09),
        f"knee{s}": ((sx * 0.17, 0.25, 0.9), 0.062, 0.062),
        f"ankle{s}": ((sx * 0.15, 0.2, 0.46), 0.045, 0.045),
        f"toe{s}": ((sx * 0.15, 0.34, 0.41), 0.045, 0.035),
    })
E = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck"), ("neck", "head_base")]
for s in "LR":
    E += [("chest", f"shoulder{s}"), (f"shoulder{s}", f"elbow{s}"), (f"elbow{s}", f"wrist{s}"), (f"wrist{s}", f"hand{s}"),
          ("pelvis", f"hip{s}"), (f"hip{s}", f"knee{s}"), (f"knee{s}", f"ankle{s}"), (f"ankle{s}", f"toe{s}")]
names = list(J)
me = bpy.data.meshes.new("body")
me.from_pydata([J[n][0] for n in names], [(names.index(a), names.index(b)) for a, b in E], [])
bodyo = link(bpy.data.objects.new("body", me))
skin = bodyo.modifiers.new("skin", "SKIN")
for i, n in enumerate(names):
    sv = bodyo.data.skin_vertices[0].data[i]
    sv.radius = (J[n][1], J[n][2])
    sv.use_root = n == "pelvis"
sub = bodyo.modifiers.new("sub", "SUBSURF")
sub.levels = 2
apply_mods(bodyo)
for p in bodyo.data.polygons:
    p.use_smooth = True
for k in ("skin", "jacket", "jacket_green", "pants", "shoe", "sole"):
    bodyo.data.materials.append(M[k])
slot = {k: i for i, k in enumerate(("skin", "jacket", "jacket_green", "pants", "shoe", "sole"))}


def near(p, name, r):
    return (Vector(p) - Vector(J[name][0])).length < r


for poly in bodyo.data.polygons:
    c = poly.center
    nrm = poly.normal
    on_leg = c.z < 0.93 and abs(c.x) > 0.03 and c.y > -0.15 or c.z < 0.8
    if c.z > 1.4:
        m = "skin"                                          # neck
    elif near(c, "handL", 0.07) or near(c, "handR", 0.07):
        m = "jacket"                                        # black gloves
    elif near(c, "wristL", 0.045) or near(c, "wristR", 0.045):
        m = "jacket_green"                                  # green cuffs
    elif c.z < 0.5 and (c.y > 0.12):
        m = "sole" if c.z < 0.385 else "shoe"
    elif on_leg:
        m = "pants"
        if abs(nrm.x) > 0.95 and nrm.x * c.x > 0:
            m = "jacket_green"                              # stripe down the outside of the leg
    else:
        m = "jacket"
        if c.z > 1.35 and abs(c.x) < 0.09:
            m = "jacket_green"                              # collar
        elif nrm.z > 0.93 and abs(c.x) > 0.2 and c.y > -0.12:
            m = "jacket_green"                              # thin stripe along the top of the forearms
        elif abs(c.x) > 0.15 and 1.0 < c.z < 1.3 and abs(nrm.x) > 0.93:
            m = "jacket_green"                              # side stripes
    poly.material_index = slot[m]

# zipper down the front
rider = [bodyo]
rider.append(box("zip", (0.012, 0.01, 0.4), (0, -0.095, 1.16), M["jacket_green"], rot=(math.radians(-8), 0, 0), levels=0))
# head, face, helmet, sunglasses
HC = Vector((0, -0.12, 1.57))
rider.append(sphere("head", 0.105, HC, M["skin"], scale=(0.9, 1.0, 1.1)))
rider.append(sphere("nose", 0.022, HC + Vector((0, 0.1, -0.02)), M["skin"], scale=(0.8, 1.0, 1.2), segs=12))
for sx in (-1, 1):
    rider.append(sphere(f"ear{sx}", 0.025, HC + Vector((sx * 0.095, -0.01, 0.0)), M["skin"], scale=(0.5, 1, 1.3), segs=12))
rider.append(box("glasses", (0.2, 0.025, 0.045), HC + Vector((0, 0.093, 0.018)), M["lens"], levels=1))
rider.append(box("glasses_frame", (0.21, 0.02, 0.01), HC + Vector((0, 0.094, 0.037)), M["helmet"], levels=0))
# open-face helmet: upper part of a sphere
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.135)
cut = [v for v in bm.verts if v.co.z < -0.01 + (0.06 if v.co.y > 0.03 else -0.035)]
bmesh.ops.delete(bm, geom=cut, context="VERTS")
helmet = new_obj("helmet", bm, M["helmet"])
helmet.data.materials.append(M["jacket_green"])
for p in helmet.data.polygons:
    p.use_smooth = True
    if abs(p.center.x) < 0.022 and p.center.z > 0.02:
        p.material_index = 1                                # green stripe over the top
sol = helmet.modifiers.new("solid", "SOLIDIFY")
sol.thickness = 0.012
helmet.location = HC + Vector((0, -0.01, 0.035))
helmet.scale = (0.92, 1.05, 1.0)
apply_mods(helmet)
rider.append(helmet)
rider.append(box("visor", (0.19, 0.07, 0.012), HC + Vector((0, 0.13, 0.085)), M["helmet"], rot=(math.radians(18), 0, 0), levels=1))
rider.append(box("hair", (0.17, 0.06, 0.05), HC + Vector((0, -0.09, -0.05)), M["hair"], levels=1))
rider_obj = join("Rider", rider, origin=(0, 0, 0))

# ------------------------------------------------------------------ export
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_yup=True,
                          export_apply=True, export_materials="EXPORT")
import os
BLEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scooter_rider.blend")
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("exported", OUT, {o.name: len(o.data.polygons) for o in scene.objects if o.type == "MESH"})

# ------------------------------------------------------------------ preview render
if PREVIEW:
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    link(cam)
    cam.location = (2.6, 2.3, 1.75)
    direction = Vector((0, 0, 0.8)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 45
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(140))
    link(sun)
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "AREA"))
    fill.data.energy = 120
    fill.data.size = 3
    fill.location = (-2, -1.5, 2.5)
    fill.rotation_euler = (Vector((0, 0, 0.7)) - fill.location).to_track_quat("-Z", "Y").to_euler()
    link(fill)
    bpy.ops.mesh.primitive_plane_add(size=20)
    bpy.context.active_object.data.materials.append(mat("Ground", srgb("9a9a94"), 0.9))
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (*srgb("b9d4ea"), 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    scene.world = world
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 900
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    print("preview", PREVIEW)
