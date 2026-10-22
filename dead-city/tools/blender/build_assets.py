"""Builds the game's 3D models with Blender (run headless):

    blender -b --python tools/blender/build_assets.py -- <sources dir> <project dir> [part ...]

<sources dir> is where tools/fetch_assets.sh unpacked the CC0 source packs.
Parts: characters, bosses, kenney (vehicles, the bus, Kenney props), viewmodels, previews, lineup
(default: characters bosses kenney viewmodels);
`boss:<name>` or `vm:<name>` rebuild a single model.

Coordinates for first-person models: the camera sits at the origin looking down +Y with +Z up,
which the glTF exporter turns into Godot's camera space (-Z forward, +Y up), in metres.
"""
import bpy
import bmesh
import math
import os
import random
import sys
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, PROJECT = argv[0], argv[1]
PARTS = argv[2:] or ["characters", "bosses", "kenney", "viewmodels"]
UACP = os.path.join(SRC, "uacp", "Ultimate Animated Character Pack - Nov 2019", "Blends")
CHAR_SCALE = 0.58  # Quaternius characters are ~3.06 units tall -> ~1.78 m
FOV_DEG = 78.0     # Godot camera fov (vertical)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def append_objects(path, names=None, actions=False):
    with bpy.data.libraries.load(path) as (src, dst):
        dst.objects = [n for n in src.objects if names is None or n in names]
        if actions:
            dst.actions = list(src.actions)
    objs = [o for o in dst.objects if o is not None and o.type not in ('CAMERA', 'LIGHT')]
    for o in objs:
        bpy.context.scene.collection.objects.link(o)
    return objs


def import_any(path):
    before = set(bpy.data.objects)
    if path.endswith(".blend"):
        append_objects(path)
    elif path.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=path)
    elif path.endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in [o for o in new if o.type in ('CAMERA', 'LIGHT')]:
        bpy.data.objects.remove(o)
    return [o for o in bpy.data.objects if o not in before]


def world_verts(objs):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        if o.type != 'MESH':
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        pts += [ev.matrix_world @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    return pts


def bounds(pts):
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def export_glb(path, objs, animations=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=False, export_animations=bool(animations),
                              export_animation_mode='NLA_TRACKS' if animations == 'nla' else 'ACTIONS', export_skins=True, export_materials='EXPORT')
    print("EXPORTED", path)


def material(name, color, metallic=0.0, roughness=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    m.diffuse_color = (*color, 1.0)
    return m


def fix_flat_materials(objs, colors=None, search_dirs=()):
    """Rebuild every material as a Principled BSDF the glTF exporter understands: keeps image textures
    (re-finding lost files by name in `search_dirs`), legacy Diffuse colours or the viewport colour.
    `colors` overrides the colour of materials by name."""
    colors = colors or {}
    done = set()
    for o in objs:
        if o.type != 'MESH':
            continue
        for slot in o.material_slots:
            m = slot.material
            if m is None or m.name in done:
                continue
            done.add(m.name)
            color, image = tuple(m.diffuse_color), None
            if m.use_nodes:
                nodes = m.node_tree.nodes
                if nodes.get("Principled BSDF") and m.name not in colors:
                    continue
                for n in nodes:
                    if n.type == 'TEX_IMAGE' and n.image is not None:
                        image = n.image
                    elif n.type == 'BSDF_DIFFUSE':
                        color = tuple(n.inputs["Color"].default_value)
            if image is not None and not os.path.exists(bpy.path.abspath(image.filepath, library=image.library)):
                name = os.path.basename(image.filepath.replace("\\", "/"))
                found = [os.path.join(r, name) for d in search_dirs for r, _, files in os.walk(d) if name in files]
                if found:
                    image.filepath = found[0]
                    image.reload()
                else:
                    image = None
            if m.name in colors:
                color, image = (*colors[m.name], 1.0), None
            m.use_nodes = True
            nodes = m.node_tree.nodes
            nodes.clear()
            out = nodes.new("ShaderNodeOutputMaterial")
            bsdf = nodes.new("ShaderNodeBsdfPrincipled")
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Roughness"].default_value = 0.7
            m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
            if image is not None:
                tex = nodes.new("ShaderNodeTexImage")
                tex.image = image
                tex.interpolation = 'Closest'
                m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])


def bake_skinned(objs):
    """Apply armature deformation and drop the armatures: first-person guns are static meshes."""
    bpy.context.view_layer.update()
    for o in objs:
        if o.type == 'MESH':
            for md in list(o.modifiers):
                if md.type == 'ARMATURE':
                    bpy.context.view_layer.objects.active = o
                    mw = o.matrix_world.copy()
                    bpy.ops.object.modifier_apply(modifier=md.name)
                    o.parent = None
                    o.matrix_world = mw
    for o in [o for o in objs if o.type == 'ARMATURE']:
        bpy.data.objects.remove(o)
    return [o for o in bpy.data.objects if o.type == 'MESH' and o in objs or (o.type == 'EMPTY' and o in objs)]


# ---------------------------------------------------------------- characters
CHARACTERS = {
    "zombie_male": "Zombie_Male", "zombie_female": "Zombie_Female", "worker": "Worker_Male",
    "doctor": "Doctor_Male_Young", "chef": "Chef_Female", "soldier": "Soldier_Male",
}



def scary_face(objs, seed=0):
    """Replaces the cartoon eyes and brows with a dead face drawn onto the head: dark sunken sockets, milky eyes
    with glowing pinprick pupils, brows knitted into a scowl, a torn-open mouth with crooked teeth and blood running
    from it. Every piece is projected onto the head surface and skinned to the Head bone (so a headshot takes it too)."""
    rnd = random.Random(seed)
    mesh = next(o for o in objs if o.type == 'MESH' and o.vertex_groups.get("Head") is not None)
    arm = next(o for o in objs if o.type == 'ARMATURE')
    old_pose = arm.data.pose_position
    arm.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    me = mesh.data
    names = [m.name for m in me.materials]
    face_slot = names.index("Face") if "Face" in names else -1
    # The head surface without the old face decals, for projecting onto.
    tree = BVHTree.FromPolygons([v.co.copy() for v in me.vertices],
                                [list(p.vertices) for p in me.polygons if p.material_index != face_slot])

    def slot(mat):
        if mat.name not in [m.name for m in me.materials]:
            me.materials.append(mat)
        return [m.name for m in me.materials].index(mat.name)
    socket = slot(material("FaceSocket", (0.03, 0.006, 0.006), roughness=0.85))
    eye = slot(emissive("FaceEye", (0.62, 0.6, 0.4), 0.06))
    pupil = slot(emissive("FacePupil", (1.0, 0.08, 0.02), 3.0))
    brow = slot(material("FaceBrow", (0.02, 0.012, 0.01), roughness=0.9))
    mouth = slot(material("FaceMouth", (0.045, 0.0, 0.0), roughness=0.4))
    teeth = slot(material("FaceTeeth", (0.48, 0.42, 0.26), roughness=0.55))
    blood = slot(material("FaceBlood", (0.2, 0.0, 0.0), roughness=0.15))

    bm = bmesh.new()
    bm.from_mesh(me)
    if face_slot >= 0:
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == face_slot], context='FACES')
    deform = bm.verts.layers.deform.verify()
    head = mesh.vertex_groups["Head"].index

    def on_head(x, z, lift):
        loc, nor, _, _ = tree.ray_cast(Vector((x, -3.0, z)), Vector((0.0, 1.0, 0.0)))
        if loc is None:
            loc, nor = Vector((x, -0.48, z)), Vector((0.0, -1.0, 0.0))
        v = bm.verts.new(loc + nor * lift)
        v[deform][head] = 1.0
        return v

    def shape(points, lift, mat):
        """A flat polygon (x, z points, drawn as seen from the front) laid on the face, fanned from its centre."""
        area = sum(points[i][0] * points[(i + 1) % len(points)][1] - points[(i + 1) % len(points)][0] * points[i][1]
                   for i in range(len(points)))
        if area < 0:  # counter-clockwise as seen from the front makes the faces point out of the head
            points = list(reversed(points))
        ring = [on_head(x, z, lift) for x, z in points]
        centre = on_head(sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points), lift)
        for i in range(len(ring)):
            bm.faces.new((centre, ring[i], ring[(i + 1) % len(ring)])).material_index = mat

    def blob(cx, cz, rx, rz, lift, mat, jag=0.0, n=14, tilt=0.0):
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            r = 1.0 + rnd.uniform(-jag, jag)
            x, z = math.cos(a) * rx * r, math.sin(a) * rz * r
            pts.append((cx + x * math.cos(tilt) - z * math.sin(tilt), cz + x * math.sin(tilt) + z * math.cos(tilt)))
        shape(pts, lift, mat)

    def strip(x, z0, z1, w, lift, mat):
        """A drip running down from z0 to z1, thinning out, with a drop at the end."""
        wob = rnd.uniform(-0.015, 0.015)
        shape([(x - w / 2, z0), (x + w / 2, z0), (x + w * 0.3 + wob, z1), (x - w * 0.3 + wob, z1)], lift, mat)
        blob(x + wob, z1, w * 0.45, w * 0.5, lift, mat, n=8)

    look = rnd.uniform(-0.012, 0.012)
    for s in (-1, 1):
        ex, ez = s * 0.245, 2.53
        blob(ex, ez - 0.01, 0.14, 0.125, 0.004, socket, jag=0.12)        # bruised, sunken socket
        blob(ex, ez, 0.08, 0.06, 0.008, eye, jag=0.08, tilt=s * 0.25)     # milky, slit-like eye
        blob(ex - s * 0.01 + look, ez + 0.004, 0.027, 0.03, 0.012, pupil, n=8)
        # brows pulled down to the nose: a scowl
        shape([(s * 0.09, 2.645), (s * 0.4, 2.76), (s * 0.41, 2.715), (s * 0.1, 2.6)], 0.006, brow)
    # bloody tear under one eye
    side = rnd.choice((-1, 1))
    strip(side * 0.27, 2.43, 2.33, 0.03, 0.006, blood)
    # a lopsided gaping mouth with broken teeth
    mx, mz, tilt = rnd.uniform(-0.03, 0.03), 2.315, rnd.uniform(-0.12, 0.12)
    blob(mx, mz, 0.21, 0.075, 0.005, mouth, jag=0.18, n=18, tilt=tilt)
    for row, sign in ((7, 1), (6, -1)):
        for i in range(row):
            t = (i + 0.5) / row
            x = mx + (t - 0.5) * 0.32
            edge = mz + sign * 0.06 * math.sqrt(max(0.0, 1 - ((t - 0.5) * 1.9) ** 2)) + (x - mx) * math.tan(tilt)
            if rnd.random() < 0.2:
                continue  # a missing tooth
            w, h = rnd.uniform(0.028, 0.04), rnd.uniform(0.03, 0.06)
            shape([(x - w / 2, edge), (x + w / 2, edge), (x + rnd.uniform(-0.008, 0.008), edge - sign * h)], 0.009, teeth)
    for x in (mx - 0.15, mx + rnd.uniform(-0.05, 0.05), mx + 0.13):
        strip(x, mz - 0.03, mz - rnd.uniform(0.09, 0.15), rnd.uniform(0.025, 0.04), 0.007, blood)
    bm.to_mesh(me)
    bm.free()
    arm.data.pose_position = old_pose


def build_characters():
    for out_name, src in CHARACTERS.items():
        reset()
        objs = append_objects(os.path.join(UACP, src + ".blend"), actions=True)
        fix_flat_materials(objs)
        scary_face(objs, seed=len(out_name))
        arm = next(o for o in objs if o.type == 'ARMATURE')
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = None
        # Every action as its own NLA track so the exporter writes them all.
        for act in bpy.data.actions:
            act.use_fake_user = True
            track = arm.animation_data.nla_tracks.new()
            track.name = act.name
            track.strips.new(act.name, int(act.frame_range[0]), act)
        print("ACTIONS", src, [a.name for a in bpy.data.actions])
        export_glb(os.path.join(PROJECT, "models", "characters", out_name + ".glb"), objs, animations='nla')


# ---------------------------------------------------------------- bosses
# Character units: the rig is ~3.2 units tall and imported at 0.58, so 1 m = 1.72 units.
# Rest pose is a T-pose facing -Y. In the idle/walk animations the fists turn so that the rest
# pose's outward arm axis (-X right, +X left) points down-forward and rest +Z points forward,
# so hand-held props run along the arm axis and face +Z.
M = 1.0 / CHAR_SCALE
FIST_R = Vector((-1.41, 0.02, 1.86))
FIST_L = Vector((1.41, 0.02, 1.86))
ALONG_X = (0, math.pi / 2, 0)


def prim(kind, size, loc, mat, rot=(0, 0, 0)):
    """A primitive in character units: box size (x, y, z), cyl/cone (radius, depth[, radius2]), sphere (radius,)."""
    if kind == 'box':
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
        bpy.context.object.scale = size
    elif kind == 'cyl':
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=size[0], depth=size[1], location=loc, rotation=rot)
    elif kind == 'cone':
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=size[0], radius2=size[2] if len(size) > 2 else 0.0,
                                        depth=size[1], location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=size[0], location=loc, rotation=rot)
    o = bpy.context.object
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    return o


def attach(parts, arm, bone, name, pivot=None, tilt=0.0):
    """Join `parts` into one mesh and parent it to `bone`, keeping its rest-pose placement.
    `tilt` turns the prop about the Y axis through `pivot` first (tips the tip of a held weapon forward)."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    if tilt:
        o.matrix_world = Matrix.Translation(pivot) @ Matrix.Rotation(tilt, 4, 'Y') @ Matrix.Translation(-pivot) @ o.matrix_world
    mw = o.matrix_world.copy()
    o.parent, o.parent_type, o.parent_bone = arm, 'BONE', bone
    bpy.context.view_layer.update()
    o.matrix_world = mw
    return o


def emissive(name, color, strength):
    m = material(name, color)
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Emission Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = strength
    return m


def props_butcher(arm):
    steel, wood = material("Steel", (0.55, 0.56, 0.58), 0.9, 0.35), material("Wood", (0.25, 0.14, 0.07))
    blood = material("Blood", (0.3, 0.02, 0.02), 0.0, 0.3)
    g = FIST_R
    handle = prim('cyl', (0.03 * M, 0.2 * M), g + Vector((-0.06 * M, 0, 0)), wood, rot=ALONG_X)
    blade = prim('box', (0.42 * M, 0.02 * M, 0.24 * M), g + Vector((-0.37 * M, 0, 0.09 * M)), steel)
    smear = prim('box', (0.16 * M, 0.024 * M, 0.08 * M), g + Vector((-0.4 * M, 0, 0.12 * M)), blood)
    return [attach([handle, blade, smear], arm, "Fist.R", "Cleaver", g, 0.5)]


def props_warden(arm):
    pane = material("ShieldPane", (0.08, 0.09, 0.11), 0.2, 0.15)
    frame, white = material("ShieldFrame", (0.03, 0.03, 0.03)), material("ShieldStripe", (0.85, 0.85, 0.8))
    rubber = material("Baton", (0.04, 0.04, 0.04), 0.0, 0.5)
    # Riot shield: long side along the arm, spreading inward (+Y) and held in front (+Z).
    c = FIST_L + Vector((-0.2 * M, 0.18 * M, 0.16 * M))
    parts = [prim('box', (1.25 * M, 0.72 * M, 0.03 * M), c, pane),
             prim('box', (1.29 * M, 0.76 * M, 0.025 * M), c + Vector((0, 0, -0.01 * M)), frame),
             prim('box', (1.2 * M, 0.1 * M, 0.035 * M), c, white)]
    shield = attach(parts, arm, "Fist.L", "Shield")
    baton = attach([prim('cyl', (0.025 * M, 0.55 * M), FIST_R + Vector((-0.2 * M, 0, 0)), rubber, rot=ALONG_X)],
                   arm, "Fist.R", "Baton", FIST_R, 0.6)
    return [shield, baton]


def props_patient(arm):
    glow = emissive("Acid", (0.45, 0.9, 0.15), 2.0)
    rnd = __import__("random").Random(7)
    torso, head = [], []
    for i in range(14):  # pustules around the chest and back
        a = rnd.uniform(0, math.tau)
        torso.append(prim('sphere', (rnd.uniform(0.05, 0.1) * M,),
                          Vector((math.cos(a) * 0.36, math.sin(a) * 0.36, rnd.uniform(1.25, 2.0))), glow))
    for i in range(7):  # and on the skull, away from the face
        a, up = rnd.uniform(0.3, math.pi - 0.3), rnd.uniform(0.2, 1.0)
        d = Vector((math.cos(a) * math.sqrt(1 - up * up), math.sin(a) * math.sqrt(1 - up * up), up))
        head.append(prim('sphere', (rnd.uniform(0.04, 0.08) * M,), Vector((0, 0, 2.7)) + d * 0.62, glow))
    return [attach(torso, arm, "Torso", "BackGrowths"), attach(head, arm, "Head", "HeadGrowths")]


def props_lineman(arm):
    steel, wood = material("HammerHead", (0.3, 0.3, 0.32), 0.9, 0.4), material("Wood", (0.35, 0.22, 0.1))
    lamp = emissive("HeadLamp", (1.0, 0.95, 0.7), 4.0)
    f = FIST_R
    handle = prim('cyl', (0.025 * M, 0.7 * M), f + Vector((-0.15 * M, 0, 0)), wood, rot=ALONG_X)
    head = prim('box', (0.13 * M, 0.13 * M, 0.34 * M), f + Vector((-0.48 * M, 0, 0)), steel)
    hammer = attach([handle, head], arm, "Fist.R", "Sledgehammer", f, 0.6)
    light = attach([prim('cyl', (0.05 * M, 0.04 * M), Vector((0, -0.62, 2.95)), lamp, rot=(math.pi / 2, 0, 0))],
                   arm, "Head", "HeadLamp")
    return [hammer, light]


def props_colossus(arm):
    bone = material("BoneSpike", (0.85, 0.8, 0.68), 0.0, 0.5)
    spikes = []
    for x, z, tilt in [(-0.35, 1.95, -0.5), (0.0, 2.05, 0.0), (0.35, 1.95, 0.5), (-0.2, 1.6, -0.3), (0.2, 1.6, 0.3)]:
        spikes.append(prim('cone', (0.09 * M, 0.45 * M), Vector((x, 0.75, z)), bone, rot=(-math.pi / 2 - 0.4, tilt, 0)))
    for sx in (-1, 1):
        spikes.append(prim('cone', (0.08 * M, 0.35 * M), Vector((sx * 0.62, 0.1, 2.15)), bone, rot=(0, sx * 0.5, 0)))
    return [attach(spikes, arm, "Torso", "Spikes")]


BOSSES = {
    # out name: (source blend, material colour overrides, props)
    "boss_butcher": ("Chef_Male", {"Clothes": (0.62, 0.55, 0.5), "Shirt": (0.5, 0.2, 0.18)}, props_butcher),
    "boss_warden": ("BlueSoldier_Male", {}, props_warden),
    "boss_patient": ("Goblin_Male", {"Pants": (0.55, 0.62, 0.66)}, props_patient),
    "boss_lineman": ("Worker_Male", {"Vest": (0.95, 0.4, 0.05)}, props_lineman),
    "boss_colossus": ("Viking_Male", {"Main": (0.22, 0.16, 0.12), "Light": (0.35, 0.3, 0.25)}, props_colossus),
}


def build_bosses(only=()):
    for out_name, (src, colors, props) in BOSSES.items():
        if only and out_name not in only:
            continue
        reset()
        objs = append_objects(os.path.join(UACP, src + ".blend"), actions=True)
        fix_flat_materials(objs, colors)
        scary_face(objs, seed=len(out_name) + 7)
        arm = next(o for o in objs if o.type == 'ARMATURE')
        arm.data.pose_position = 'REST'
        bpy.context.view_layer.update()
        objs += props(arm)
        arm.data.pose_position = 'POSE'
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = None
        for act in bpy.data.actions:
            act.use_fake_user = True
            track = arm.animation_data.nla_tracks.new()
            track.name = act.name
            track.strips.new(act.name, int(act.frame_range[0]), act)
        path = os.path.join(PROJECT, "models", "characters", out_name + ".glb")
        export_glb(path, objs, animations='nla')
        render_character(arm, os.path.join(SRC, "previews", out_name + "_%s.png"))


def render_character(arm, out_pattern, poses=(("Idle", 10), ("Walk", 8), ("SwordSlash", 14), ("Punch", 10))):
    """Renders the character in a few animation frames (front three-quarter view)."""
    scene = bpy.context.scene
    for track in arm.animation_data.nla_tracks:
        track.mute = True
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.location = (-4.5, -7.5, 2.6)
    direction = Vector((0, 0, 1.6)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 3.5
    sun.rotation_euler = (0.7, 0.2, -0.6)
    scene.collection.objects.link(sun)
    scene.world = bpy.data.worlds.new("W")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.32, 0.36, 1)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 8
    scene.render.resolution_x, scene.render.resolution_y = 300, 360
    for action, frame in poses:
        if action not in bpy.data.actions:
            continue
        arm.animation_data.action = bpy.data.actions[action]
        scene.frame_set(frame)
        scene.render.filepath = out_pattern % action
        bpy.ops.render.render(write_still=True)
    arm.animation_data.action = None


# ---------------------------------------------------------------- Kenney kits (vehicles, furniture, street, camp)
KENNEY = os.path.join(SRC, "kenney")
KITS = {  # kit folder, model subfolder, scale to metres
    "car": ("car-kit", "Models/GLB format", 1.76),
    "furniture": ("furniture-kit", "Models/GLTF format", 2.1),
    "roads": ("city-kit-roads", "Models/GLB format", 8.0),
    "survival": ("survival-kit", "Models/GLB format", 2.65),
}
# width, length, height factors for vehicles (on top of the kit scale)
VEHICLE_STRETCH = (0.72, 1.0, 0.68)
# out name: (kit, source, look) — look is 'dirty', 'burnt' (no wheels, charred), 'worn' (furniture) or 'plain'
VEHICLES = {n: ("car", n.replace("_", "-"), "dirty") for n in
            ("sedan", "suv", "suv_luxury", "hatchback_sports", "taxi", "police", "ambulance", "van", "delivery",
             "truck", "garbage_truck", "firetruck")}
VEHICLES.update({n + "_burnt": ("car", n.replace("_", "-"), "burnt") for n in ("sedan", "suv", "van", "hatchback_sports", "taxi")})
KENNEY_PROPS = {
    **{n: ("car", s, "dirty") for n, s in [("debris_door", "debris-door"), ("debris_door_window", "debris-door-window"),
                                           ("debris_bumper", "debris-bumper"), ("debris_tire", "debris-tire"),
                                           ("debris_plate", "debris-plate-a"), ("debris_spoiler", "debris-spoiler-a"),
                                           ("debris_axle", "debris-drivetrain-axle")]},
    **{n: ("furniture", s, "worn") for n, s in [
        ("bookcase_open", "bookcaseOpen"), ("bookcase_wide", "bookcaseClosedWide"), ("bookcase_doors", "bookcaseClosedDoors"),
        ("desk_corner", "deskCorner"), ("desk_chair", "chairDesk"), ("computer_screen", "computerScreen"),
        ("computer_keyboard", "computerKeyboard"), ("laptop", "laptop"), ("fridge", "kitchenFridgeLarge"),
        ("kitchen_cabinet", "kitchenCabinet"), ("kitchen_cabinet_drawer", "kitchenCabinetDrawer"), ("kitchen_sink", "kitchenSink"),
        ("kitchen_stove", "kitchenStove"), ("microwave", "kitchenMicrowave"), ("coffee_machine", "kitchenCoffeeMachine"),
        ("kitchen_upper", "kitchenCabinetUpperDouble"), ("lounge_sofa", "loungeSofa"), ("lounge_chair", "loungeChair"),
        ("table_round", "tableRound"), ("table", "table"), ("chair_cushion", "chairCushion"), ("coat_rack", "coatRackStanding"),
        ("floor_lamp", "lampRoundFloor"), ("table_lamp", "lampSquareTable"), ("tv_old", "televisionVintage"), ("radio", "radio"),
        ("trashcan_small", "trashcan"), ("sink", "bathroomSink"), ("bed_single", "bedSingle"), ("box_closed", "cardboardBoxClosed"),
        ("box_open", "cardboardBoxOpen"), ("rug", "rugRectangle"), ("rug_round", "rugRound"), ("plant_tall", "pottedPlant"),
        ("plant_small", "plantSmall2"), ("books", "books"), ("washer", "washer"), ("side_table", "sideTableDrawers"),
        ("tv_cabinet", "cabinetTelevision"), ("speaker", "speaker"), ("toaster", "toaster"), ("stool_bar", "stoolBar"),
        ("kitchen_bar", "kitchenBar"), ("shower", "shower"), ("bathtub", "bathtub")]},
    **{n: ("roads", s, "dirty") for n, s in [
        ("traffic_light", "traffic-light"), ("sign_stop", "road-sign-stop"), ("sign_warning", "road-sign-warning"),
        ("sign_street", "road-sign-street"), ("construction_barrier", "construction-barrier"),
        ("construction_fence", "construction-fence"), ("construction_light", "construction-light"),
        ("electricity_pole", "electricity-pole"), ("bridge_pillar", "bridge-pillar")]},
    **{n: ("survival", s, "dirty") for n, s in [
        ("barrel_open", "barrel-open"), ("crate_large", "box-large"), ("crate_large_open", "box-large-open"), ("bucket", "bucket"),
        ("fence_wood", "fence"), ("fence_fortified", "fence-fortified"), ("metal_panel", "metal-panel-screws"),
        ("tent_small", "tent"), ("tent_canvas", "tent-canvas"), ("bedroll", "bedroll"), ("bedroll_packed", "bedroll-packed"),
        ("campfire_pit", "campfire-pit"), ("chest", "chest"), ("bottle", "bottle-large"), ("shovel", "tool-shovel"),
        ("pickaxe", "tool-pickaxe"), ("axe", "tool-axe"), ("camp_workbench", "workbench"), ("signpost", "signpost"),
        ("canvas_shelter", "structure-canvas"), ("planks", "resource-planks"), ("rock", "rock-a"), ("rock_flat", "rock-flat")]},
}


def grime(objs, look):
    """Make bright toy colours fit a dead city: images and plain colours are desaturated and darkened;
    'burnt' chars everything."""
    import numpy as np
    done = set()

    def tone(rgb):
        gray = rgb @ np.array([0.3, 0.59, 0.11])
        if look == "burnt":
            return gray[..., None] * 0.14 + np.array([0.045, 0.035, 0.03])
        amount, dark = (0.45, 0.72) if look == "dirty" else (0.25, 0.85)
        return (rgb * (1 - amount) + gray[..., None] * amount) * dark + np.array([0.03, 0.025, 0.015])

    for o in objs:
        if o.type != 'MESH':
            continue
        for slot in o.material_slots:
            m = slot.material
            if m is None or m.name in done or not m.use_nodes:
                continue
            done.add(m.name)
            bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is None:
                continue
            bsdf.inputs["Roughness"].default_value = 0.8
            if "Metallic" in bsdf.inputs and look == "burnt":
                bsdf.inputs["Metallic"].default_value = 0.0
            link = bsdf.inputs["Base Color"].links
            if link and link[0].from_node.type == 'TEX_IMAGE':
                tex = link[0].from_node
                src = tex.image
                img = src.copy()
                img.name = f"{src.name}_{look}"
                px = np.empty(len(img.pixels), dtype=np.float32)
                img.pixels.foreach_get(px)
                px = px.reshape(-1, 4)
                px[:, :3] = np.clip(tone(px[:, :3]), 0, 1)
                img.pixels.foreach_set(px.ravel())
                img.update()
                img.pack()
                tex.image = img
            else:
                c = np.array(bsdf.inputs["Base Color"].default_value[:3])
                bsdf.inputs["Base Color"].default_value = (*np.clip(tone(c), 0, 1), 1.0)


def kenney_model(kit, source, look, out_path):
    """Imports a Kenney model, scales it to metres, centres it on the floor, gives it a grimy look and exports it.
    Vehicles are turned to face Blender +Y (Godot -Z). Returns its size (x, y, z in Godot axes)."""
    folder, sub, scale = KITS[kit]
    reset()
    bpy.ops.import_scene.gltf(filepath=os.path.join(KENNEY, folder, sub, source + ".glb"))
    objs = [o for o in bpy.data.objects]
    if look == "burnt":
        for o in [o for o in objs if "wheel" in o.name]:
            bpy.data.objects.remove(o)
        objs = list(bpy.data.objects)
    root = bpy.data.objects.new("Root", None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs:
        if o.parent is None:
            o.parent = root
    turn = Matrix.Identity(4)
    front = [o for o in objs if "wheel-front" in o.name]
    if (front and front[0].matrix_world.translation.y < 0) or kit == "furniture":
        turn = Matrix.Rotation(math.pi, 4, 'Z')  # fronts face +Y like every other model here (Godot -Z)
    if out_path.endswith(".glb") and os.sep + "vehicles" + os.sep in out_path:
        # Kenney cars are stubby toys: stretch them to real proportions, but keep the wheels round.
        stretch = Vector(VEHICLE_STRETCH) * scale
        root.matrix_world = turn @ Matrix.Diagonal((*stretch, 1.0))
        bpy.context.view_layer.update()
        for o in objs:
            if "wheel" in o.name:
                loc, rot, sca = o.matrix_world.decompose()
                round_scale = Vector((sca.x, sca.z, sca.z))
                o.matrix_world = Matrix.LocRotScale(loc, rot, round_scale)
    else:
        if kit == "car":  # loose car parts match the (squashed) height of the vehicles
            scale *= VEHICLE_STRETCH[2]
        root.matrix_world = turn @ Matrix.Scale(scale, 4)
    lo, hi = bounds(world_verts(objs))
    drop = 0.22 if look == "burnt" else 0.0  # wheel-less wrecks sit on their belly
    root.matrix_world = Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z - drop))) @ root.matrix_world
    grime(objs, look)
    export_glb(out_path, objs + [root])
    lo, hi = bounds(world_verts(objs))
    return [round(hi.x - lo.x, 3), round(hi.z - lo.z, 3), round(hi.y - lo.y, 3)]


def build_bus(out_path):
    """A city bus modelled from scratch: rounded body, window band with pillars, doors, Kenney truck wheels."""
    reset()
    paint, trim = material("BusPaint", (0.62, 0.5, 0.22), 0.2, 0.6), material("BusTrim", (0.08, 0.08, 0.09))
    glass, lights = material("BusGlass", (0.05, 0.07, 0.09), 0.3, 0.1), material("BusLights", (0.85, 0.8, 0.6))
    rust = material("BusRust", (0.32, 0.17, 0.08))
    L, W, H = 11.0, 2.5, 2.9
    parts = []

    def box(size, loc, mat, bevel=0.0):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        o = bpy.context.object
        o.scale = size
        bpy.ops.object.transform_apply(scale=True)
        if bevel:
            md = o.modifiers.new("Bevel", 'BEVEL')
            md.width, md.segments = bevel, 3
            bpy.ops.object.modifier_apply(modifier=md.name)
        o.data.materials.append(mat)
        parts.append(o)
        return o
    box((W, L, H - 0.45), (0, 0, 0.45 + (H - 0.45) / 2), paint, 0.18)               # body (front = +Y)
    for sx in (-1, 1):
        box((0.04, L - 1.4, 0.95), (sx * W / 2, -0.2, 1.95), glass)                   # window band
        for i in range(9):
            box((0.06, 0.1, 0.95), (sx * (W / 2 + 0.005), -L / 2 + 1.0 + i * 1.12, 1.95), paint)
        box((0.05, L - 0.3, 0.32), (sx * W / 2, 0, 0.62), trim)                        # skirt
        for y in (-3.6, 3.4):                                                           # wheel arches
            box((0.06, 1.3, 0.75), (sx * (W / 2 + 0.01), y, 0.75), trim)
        for i in range(4):
            box((0.05, rnd_u(i, 0.3, 0.7), rnd_u(i + 7, 0.1, 0.3)), (sx * (W / 2 + 0.01), -4 + i * 2.6, 0.95), rust)
    box((0.05, 1.1, 1.85), (W / 2 + 0.02, 3.6, 1.42), glass); box((0.05, 1.1, 1.85), (W / 2 + 0.02, -0.4, 1.42), glass)  # doors
    box((W - 0.3, 0.05, 1.2), (0, L / 2, 1.85), glass)                                 # windscreen
    box((W - 0.5, 0.05, 0.7), (0, -L / 2, 2.0), glass)                                 # rear window
    box((W - 0.6, 0.06, 0.28), (0, L / 2 + 0.01, 2.62), trim)                         # route sign
    for sx in (-1, 1):
        box((0.35, 0.05, 0.18), (sx * 0.85, L / 2 + 0.02, 0.85), lights)
        box((0.25, 0.05, 0.25), (sx * 0.95, -L / 2 - 0.02, 0.9), material("BusTail", (0.5, 0.05, 0.03)))
    box((W + 0.05, 0.2, 0.3), (0, L / 2 + 0.05, 0.5), trim); box((W + 0.05, 0.2, 0.3), (0, -L / 2 - 0.05, 0.5), trim)
    box((1.4, 2.0, 0.25), (0, -2.5, H + 0.1), paint, 0.05)                            # roof hatch / AC unit
    # wheels from the Kenney car kit
    wheel_path = os.path.join(KENNEY, "car-kit", "Models/GLB format", "wheel-truck.glb")
    for sx in (-1, 1):
        for y in (-3.6, 3.4):
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=wheel_path)
            new = [o for o in bpy.data.objects if o not in before]
            lo, hi = bounds(world_verts(new))
            k = 1.0 / max(hi.z - lo.z, 1e-3)
            for o in new:
                if o.parent is None:
                    o.matrix_world = Matrix.Translation(Vector((sx * (W / 2 - 0.15), y, 0.5))) @ \
                        Matrix.Rotation(0 if sx > 0 else math.pi, 4, 'Z') @ Matrix.Scale(k, 4) @ \
                        Matrix.Translation(-(lo + hi) / 2) @ o.matrix_world
            parts += new
    grime(parts, "dirty")
    export_glb(out_path, parts)
    lo, hi = bounds(world_verts(parts))
    return [round(hi.x - lo.x, 3), round(hi.z - lo.z, 3), round(hi.y - lo.y, 3)]


def rnd_u(seed, a, b):
    return a + (b - a) * ((seed * 9301 + 49297) % 233280) / 233280.0


def build_kenney(only=()):
    import json
    sizes_path = os.path.join(PROJECT, "models", "kenney_sizes.json")
    sizes = json.load(open(sizes_path)) if os.path.exists(sizes_path) else {}
    for out_dir, table in (("vehicles", VEHICLES), ("props", KENNEY_PROPS)):
        for name, (kit, source, look) in table.items():
            if only and name not in only:
                continue
            sizes[name] = kenney_model(kit, source, look, os.path.join(PROJECT, "models", out_dir, name + ".glb"))
    if not only or "bus" in only:
        sizes["bus"] = build_bus(os.path.join(PROJECT, "models", "vehicles", "bus.glb"))
    json.dump(sizes, open(sizes_path, "w"), indent=1, sort_keys=True)


def render_lineup(paths, out_png, spacing=6.0, cam=(0, -22, 9)):
    """Imports models side by side and renders them (quick look at the Kenney conversions)."""
    reset()
    for i, p in enumerate(paths):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=p)
        for o in bpy.data.objects:
            if o not in before and o.parent is None:
                o.location.x += (i % 6 - 2.5) * spacing
                o.location.y += (i // 6) * spacing
    scene = bpy.context.scene
    c = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    c.location = cam
    c.rotation_euler = (Vector((0, spacing * 0.5, 0.5)) - Vector(cam)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(c)
    scene.camera = c
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 3.0
    sun.rotation_euler = (0.7, 0.2, -0.6)
    scene.collection.objects.link(sun)
    scene.world = bpy.data.worlds.new("W")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.37, 0.4, 1)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 8
    scene.render.resolution_x, scene.render.resolution_y = 1200, 600
    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- weapons
def normalize_weapon(objs, length, grip, grip_at):
    """Turn the weapon so its muzzle points +Y, scale it to `length` metres and move it so that the
    point `grip` (fractions of its bounding box: x, y from the rear, z from the bottom) lands on `grip_at`."""
    root = bpy.data.objects.new("WeaponRoot", None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs:
        if o.parent is None:
            o.parent = root
    pts = world_verts(objs)
    lo, hi = bounds(pts)
    axis = max(range(3), key=lambda i: hi[i] - lo[i])
    span = hi[axis] - lo[axis]

    def slice_area(near_lo):
        sl = [p for p in pts if (p[axis] - lo[axis] if near_lo else hi[axis] - p[axis]) < span * 0.06]
        others = [i for i in range(3) if i != axis]
        return (max(p[others[0]] for p in sl) - min(p[others[0]] for p in sl)) * \
               (max(p[others[1]] for p in sl) - min(p[others[1]] for p in sl))
    muzzle_high = slice_area(False) < slice_area(True)
    # Rotate the long axis onto +Y (muzzle forward).
    if axis == 0:
        rot = Matrix.Rotation(math.radians(90 if muzzle_high else -90), 4, 'Z')
    elif axis == 1:
        rot = Matrix.Identity(4) if muzzle_high else Matrix.Rotation(math.pi, 4, 'Z')
    else:
        raise RuntimeError("weapon long axis is vertical")
    root.matrix_world = rot @ Matrix.Scale(length / span, 4)
    pts = world_verts(objs)
    lo, hi = bounds(pts)
    g = Vector((lo.x + (hi.x - lo.x) * grip[0], lo.y + (hi.y - lo.y) * grip[1], lo.z + (hi.z - lo.z) * grip[2]))
    root.matrix_world = Matrix.Translation(Vector(grip_at) - g) @ root.matrix_world
    pts = world_verts(objs)
    lo, hi = bounds(pts)
    front = [p for p in pts if hi.y - p.y < (hi.y - lo.y) * 0.03]
    muzzle = sum(front, Vector()) / len(front)
    muzzle.y = hi.y
    print("WEAPON bounds", tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi), "muzzle", tuple(round(v, 3) for v in muzzle))
    return root, lo, hi, muzzle


def build_arms(right_target, left_target, keep_left=True, right_pole=(0.7, -0.2, -0.9), left_pole=(-0.7, -0.2, -0.9)):
    """Soldier arms posed with IK so the fists reach the given points; returns a static mesh object."""
    objs = append_objects(os.path.join(UACP, "Soldier_Male.blend"))
    fix_flat_materials(objs)
    arm = next(o for o in objs if o.type == 'ARMATURE')
    body = next(o for o in objs if o.type == 'MESH')
    if arm.animation_data:
        arm.animation_data.action = None
    # Face +Y like the camera, scale to metres, shoulders just below and behind the eyes.
    shoulder_mid = Vector((0.0, 0.012, 1.87))
    arm.matrix_world = Matrix.Translation(Vector((0.0, -0.08, -0.5))) @ Matrix.Rotation(math.pi, 4, 'Z') @ \
        Matrix.Scale(CHAR_SCALE, 4) @ Matrix.Translation(-shoulder_mid)
    for side, target, pole in (("R", right_target, right_pole), ("L", left_target, left_pole)):
        t = bpy.data.objects.new(f"IK_{side}", None)
        t.location = target
        p = bpy.data.objects.new(f"Pole_{side}", None)
        p.location = pole
        bpy.context.scene.collection.objects.link(t)
        bpy.context.scene.collection.objects.link(p)
        c = arm.pose.bones[f"LowerArm.{side}"].constraints.new('IK')
        c.target, c.pole_target, c.chain_count = t, p, 2
        c.pole_angle = math.radians(-90)
    # Keep only the arm geometry.
    bpy.context.view_layer.update()
    names = ["UpperArm", "LowerArm", "Fist"]
    sides = ["R", "L"] if keep_left else ["R"]
    keep_groups = {body.vertex_groups[f"{n}.{s}"].index for n in names for s in sides}
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    posed = bpy.data.objects.new("Arms", me)
    bpy.context.scene.collection.objects.link(posed)
    posed.matrix_world = body.matrix_world.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    src_me = body.data
    bm.verts.ensure_lookup_table()
    drop = []
    for v in bm.verts:
        groups = src_me.vertices[v.index].groups
        total = sum(g.weight for g in groups) or 1.0
        armw = sum(g.weight for g in groups if g.group in keep_groups)
        if armw / total < 0.5:
            drop.append(v)
    bmesh.ops.delete(bm, geom=drop, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    for o in objs:
        bpy.data.objects.remove(o)
    return posed


FPS_ARMS = os.path.join("guns", "fpsarms", "FPS ARMS RIG 1.blend")
ARMS_SCALE = 0.1          # rig units -> metres (upper arm ~0.26 m)
SHOULDERS_AT = (0.0, -0.06, -0.24)
HAND_BONES = ("hand", "palm", "f_", "thumb")


def hand_basis(fwd, palm):
    """Rotation whose bone axis (Y) points along `fwd` (wrist -> knuckles) and whose palm faces `palm`."""
    y = Vector(fwd).normalized()
    z = (Vector(palm) - y * Vector(palm).dot(y)).normalized()  # palm normal, made orthogonal to y
    x = y.cross(z)
    return Matrix((x, y, z)).transposed().to_4x4()


def build_real_arms(right, left=None, curl=75.0, left_curl=60.0):
    """CC0 FPS arms (gloves + sleeves) posed with IK. `right`/`left` are (grip point, finger direction, palm
    direction) in camera space: the palm is placed against the grip point. Without `left` the left arm is removed."""
    objs = append_objects(os.path.join(SRC, FPS_ARMS))
    arm = next(o for o in objs if o.type == 'ARMATURE')
    body = next(o for o in objs if o.type == 'MESH')
    if arm.animation_data:
        arm.animation_data.action = None
    bpy.context.view_layer.update()
    mid = (arm.matrix_world @ arm.data.bones["clavicle.R"].head_local + arm.matrix_world @ arm.data.bones["clavicle.L"].head_local) / 2
    arm.matrix_world = Matrix.Translation(Vector(SHOULDERS_AT)) @ Matrix.Scale(ARMS_SCALE, 4) @ Matrix.Translation(-mid) @ arm.matrix_world
    bpy.context.view_layer.update()
    inv = arm.matrix_world.inverted()
    for side, spec, amount in (("R", right, curl), ("L", left, left_curl)):
        if spec is None:
            continue
        grip, fwd, palm = (Vector(v) for v in spec)
        mw = arm.matrix_world
        bones = arm.data.bones
        wrist_rest = mw @ bones[f"hand.{side}"].head_local
        knuckle = mw @ bones[f"f_middle.01.{side}"].head_local
        index_k = mw @ bones[f"f_index.01.{side}"].head_local
        pinky_k = mw @ bones[f"f_pinky.01.{side}"].head_local
        f_rest = (knuckle - wrist_rest).normalized()
        sign = 1.0 if side == "R" else -1.0
        p_rest = ((index_k - pinky_k).cross(f_rest) * sign).normalized()
        delta = hand_basis(fwd, palm) @ hand_basis(f_rest, p_rest).inverted()
        reach = (knuckle - wrist_rest).length
        wrist = grip - palm.normalized() * 0.022 - fwd.normalized() * reach * 0.55
        ctrl = arm.pose.bones[f"hand.{side}.control"]
        rest = mw @ ctrl.bone.matrix_local
        loc, rot, scl = rest.decompose()
        offset = wrist_rest - loc  # control bone head vs wrist
        new = Matrix.Translation(wrist - delta.to_3x3() @ offset) @ delta @ rot.to_matrix().to_4x4() @ Matrix.Diagonal(scl).to_4x4()
        ctrl.matrix = inv @ new
        for f in ("index", "middle", "ring", "pinky"):
            pb = arm.pose.bones[f"f_{f}.01.{side}"]
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler.x = math.radians(amount)
        th = arm.pose.bones[f"thumb.02.{side}"]
        th.rotation_mode = 'XYZ'
        th.rotation_euler.x = math.radians(amount * 0.4)
    bpy.context.view_layer.update()
    # Bake the pose into a static mesh.
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg))
    posed = bpy.data.objects.new("Arms", me)
    bpy.context.scene.collection.objects.link(posed)
    posed.matrix_world = body.matrix_world.copy()
    glove = material("Glove", (0.035, 0.035, 0.038), roughness=0.75)
    sleeve = material("Sleeve", (0.045, 0.055, 0.032), roughness=0.95)
    me.materials.clear()
    me.materials.append(sleeve)
    me.materials.append(glove)
    groups = {g.index: g.name for g in body.vertex_groups}
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    hand_vert, left_vert = [], []
    for v in bm.verts:
        gs = body.data.vertices[v.index].groups
        total = sum(g.weight for g in gs) or 1.0
        handw = sum(g.weight for g in gs if groups[g.group].startswith(HAND_BONES))
        hand_vert.append(handw / total > 0.5)
        left_vert.append(any(groups[g.group].endswith(".L") and g.weight > 0.5 for g in gs))
    for f in bm.faces:
        f.material_index = 1 if sum(hand_vert[v.index] for v in f.verts) * 2 > len(f.verts) else 0
        f.smooth = True
    if left is None:
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if left_vert[v.index]], context='VERTS')
    bm.to_mesh(me)
    bm.free()
    for o in objs:
        bpy.data.objects.remove(o)
    return posed


def arms_test():
    reset()
    arms = build_real_arms(((0.15, 0.4, -0.2), (0, 1, 0.15), (-1, 0, 0)), ((0.1, 0.4, -0.22), (0, 0.8, 0.6), (1, 0, 0)))
    export_glb(os.path.join(SRC, "previews", "arms_test.glb"), [arms])


def add_muzzle(pos):
    e = bpy.data.objects.new("Muzzle", None)
    e.location = pos
    bpy.context.scene.collection.objects.link(e)
    return e


def model_knife():
    """A combat knife modelled from scratch: tapered blade with a clipped point, guard, ribbed grip."""
    steel = material("Steel", (0.62, 0.64, 0.68), metallic=0.8, roughness=0.25)
    edge = material("Edge", (0.85, 0.87, 0.9), metallic=0.9, roughness=0.15)
    black = material("Rubber", (0.03, 0.03, 0.035), roughness=0.85)
    parts = []
    # Blade profile in the YZ plane (y forward), extruded along x.
    prof = [(0.0, -0.012), (0.12, -0.014), (0.165, -0.004), (0.185, 0.008), (0.15, 0.012), (0.11, 0.016), (0.0, 0.016)]
    bm = bmesh.new()
    t = 0.0022
    front = [bm.verts.new((t, y, z)) for y, z in prof]
    back = [bm.verts.new((-t, y, z)) for y, z in prof]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], front[j], back[j], back[i]))
    # Sharpen the cutting edge (lower side) by pulling it to the centre plane.
    for k in (1, 2, 3):
        front[k].co.x = back[k].co.x = 0.0
    me = bpy.data.meshes.new("Blade")
    bm.to_mesh(me)
    bm.free()
    blade = bpy.data.objects.new("Blade", me)
    blade.data.materials.append(steel)
    blade.data.materials.append(edge)
    bpy.context.scene.collection.objects.link(blade)
    parts.append(blade)

    def prim(op, name, mat, **kw):
        op(**kw)
        o = bpy.context.active_object
        o.name = name
        o.data.materials.append(mat)
        parts.append(o)
        return o
    prim(bpy.ops.mesh.primitive_cube_add, "Guard", steel, size=1, location=(0, -0.004, 0.002)).scale = (0.012, 0.008, 0.05)
    grip = prim(bpy.ops.mesh.primitive_cylinder_add, "Grip", black, vertices=12, radius=0.013, depth=0.11,
                location=(0, -0.062, 0.002), rotation=(math.pi / 2, 0, 0))
    grip.scale = (0.75, 1, 1)
    for i in range(5):
        prim(bpy.ops.mesh.primitive_torus_add, f"Rib{i}", black, major_radius=0.0125, minor_radius=0.0025,
             location=(0, -0.022 - i * 0.02, 0.002), rotation=(math.pi / 2, 0, 0)).scale = (0.8, 1, 1)
    prim(bpy.ops.mesh.primitive_cylinder_add, "Pommel", steel, vertices=12, radius=0.015, depth=0.012,
         location=(0, -0.121, 0.002), rotation=(math.pi / 2, 0, 0))
    for o in parts:
        o.data.polygons.foreach_set("use_smooth", [o.name.startswith(("Grip", "Rib", "Pommel"))] * len(o.data.polygons))
    return parts


def model_grenade():
    """A frag grenade: ribbed olive body, fuse, spoon and pin ring (centred on the origin, ~10 cm tall)."""
    olive = material("GrenadeBody", (0.09, 0.11, 0.05), roughness=0.75)
    metal = material("GrenadeFuse", (0.45, 0.45, 0.47), metallic=0.8, roughness=0.35)
    parts = []
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.03, location=(0, 0, 0))
    body = bpy.context.object
    body.scale = (1, 1, 1.25)
    body.data.materials.append(olive)
    body.data.polygons.foreach_set("use_smooth", [True] * len(body.data.polygons))
    parts.append(body)
    for i in range(3):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.0305, minor_radius=0.0025, location=(0, 0, -0.018 + i * 0.018))
        ring = bpy.context.object
        ring.data.materials.append(olive)
        parts.append(ring)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.011, depth=0.025, location=(0, 0, 0.045))
    bpy.context.object.data.materials.append(metal)
    parts.append(bpy.context.object)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.012, 0, 0.02))
    spoon = bpy.context.object
    spoon.scale = (0.006, 0.012, 0.06)
    spoon.rotation_euler = (0, 0.25, 0)
    spoon.data.materials.append(metal)
    parts.append(spoon)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.012, minor_radius=0.0018, location=(-0.016, 0, 0.055),
                                     rotation=(math.pi / 2, 0, 0))
    bpy.context.object.data.materials.append(metal)
    parts.append(bpy.context.object)
    return parts


class GunKit:
    """Parts for guns modelled from scratch: y forward (butt to muzzle), z up, x across, in metres."""

    def __init__(self):
        self.parts = []

    def prism(self, name, profile, width, mat, x=0.0):
        """A polygon in the YZ plane extruded along x."""
        bm = bmesh.new()
        a = [bm.verts.new((x + width / 2, y, z)) for y, z in profile]
        b = [bm.verts.new((x - width / 2, y, z)) for y, z in profile]
        bm.faces.new(a)
        bm.faces.new(list(reversed(b)))
        for i in range(len(profile)):
            j = (i + 1) % len(profile)
            bm.faces.new((a[i], b[i], b[j], a[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        o.data.materials.append(mat)
        bpy.context.scene.collection.objects.link(o)
        self.parts.append(o)
        return o

    def box(self, name, size, loc, mat, rot=(0, 0, 0), bevel=0.0):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
        o = bpy.context.object
        o.name = name
        o.scale = size
        bpy.ops.object.transform_apply(scale=True)
        if bevel:
            md = o.modifiers.new("Bevel", 'BEVEL')
            md.width, md.segments = bevel, 2
            bpy.ops.object.modifier_apply(modifier=md.name)
        o.data.materials.append(mat)
        self.parts.append(o)
        return o

    def tube(self, name, radius, y0, y1, z, mat, x=0.0):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=y1 - y0,
                                            location=(x, (y0 + y1) / 2, z), rotation=(math.pi / 2, 0, 0))
        o = bpy.context.object
        o.name = name
        o.data.materials.append(mat)
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
        self.parts.append(o)
        return o


def model_smg():
    """A compact submachine gun (MP5-like): boxy receiver, straight magazine, folding wire stock, suppressor."""
    metal = material("SmgMetal", (0.06, 0.06, 0.065), metallic=0.6, roughness=0.45)
    poly = material("SmgPolymer", (0.03, 0.03, 0.033), roughness=0.7)
    k = GunKit()
    k.box("Receiver", (0.042, 0.26, 0.06), (0, 0.27, 0.0), metal, bevel=0.006)
    k.box("TopRail", (0.02, 0.2, 0.012), (0, 0.27, 0.037), metal)
    k.prism("Grip", [(0.2, -0.03), (0.24, -0.03), (0.225, -0.13), (0.19, -0.125)], 0.03, poly)
    k.box("Mag", (0.026, 0.035, 0.17), (0, 0.29, -0.11), metal, rot=(0.12, 0, 0))
    k.box("Handguard", (0.05, 0.11, 0.05), (0, 0.44, -0.008), poly, bevel=0.012)
    k.tube("Barrel", 0.009, 0.48, 0.52, 0.005, metal)
    k.tube("Suppressor", 0.019, 0.52, 0.68, 0.005, poly)
    k.box("FrontSight", (0.02, 0.015, 0.03), (0, 0.49, 0.04), metal)
    k.box("RearSight", (0.024, 0.02, 0.025), (0, 0.16, 0.042), metal)
    for sx in (-1, 1):
        k.box(f"StockArm{sx}", (0.006, 0.17, 0.008), (sx * 0.018, 0.06, 0.012), metal)
    k.box("ButtPad", (0.045, 0.012, 0.09), (0, -0.025, -0.01), poly)
    k.box("TriggerGuard", (0.01, 0.05, 0.006), (0, 0.24, -0.055), metal)
    return k.parts



def model_revolver():
    """A six-shot double-action revolver: blued frame, fluted cylinder with chambers, 6" barrel with an underlug,
    hammer and a wooden grip (y forward, z up, real-life size)."""
    blued = material("RevolverBlued", (0.1, 0.1, 0.11), metallic=0.85, roughness=0.3)
    dark = material("RevolverDark", (0.025, 0.025, 0.028), metallic=0.5, roughness=0.5)
    wood = material("RevolverWood", (0.24, 0.1, 0.035), roughness=0.45)
    brass = material("RevolverBrass", (0.75, 0.55, 0.2), metallic=0.9, roughness=0.3)
    k = GunKit()
    k.prism("Frame", [(0.035, -0.012), (0.1, -0.024), (0.158, -0.02), (0.158, 0.038), (0.098, 0.044),
                      (0.06, 0.044), (0.038, 0.03)], 0.026, blued)
    k.prism("Grip", [(0.034, -0.006), (0.078, -0.016), (0.072, -0.118), (0.032, -0.122), (0.018, -0.07),
                     (0.02, -0.02)], 0.034, wood)
    k.box("GripCap", (0.03, 0.04, 0.008), (0, 0.053, -0.122), blued, rot=(-0.1, 0, 0))
    # cylinder: a fat drum with six flutes and the chambers showing at the front
    cyl = k.tube("Cylinder", 0.021, 0.1, 0.152, 0.013, blued)
    for i in range(6):
        a = math.radians(30 + i * 60)
        k.box(f"Flute{i}", (0.006, 0.03, 0.006), (math.cos(a) * 0.021, 0.126, 0.013 + math.sin(a) * 0.021), dark,
              rot=(0, -a, 0))
        k.tube(f"Chamber{i}", 0.0048, 0.1515, 0.1535, 0.013 + math.sin(a + math.radians(30)) * 0.013, dark,
               x=math.cos(a + math.radians(30)) * 0.013)
        k.tube(f"Round{i}", 0.0042, 0.0985, 0.1005, 0.013 + math.sin(a + math.radians(30)) * 0.013, brass,
               x=math.cos(a + math.radians(30)) * 0.013)
    k.tube("Pin", 0.004, 0.152, 0.158, 0.013, dark)
    k.tube("Barrel", 0.0085, 0.155, 0.31, 0.024, blued)
    k.box("Underlug", (0.015, 0.15, 0.016), (0, 0.233, 0.01), blued, bevel=0.004)
    k.box("Rib", (0.012, 0.155, 0.007), (0, 0.233, 0.034), blued, bevel=0.002)
    k.box("FrontSight", (0.004, 0.012, 0.012), (0, 0.302, 0.041), dark)
    k.box("RearSight", (0.012, 0.01, 0.006), (0, 0.095, 0.047), dark)
    k.box("Hammer", (0.008, 0.022, 0.026), (0, 0.045, 0.045), dark, rot=(-0.5, 0, 0), bevel=0.002)
    k.box("TriggerGuard", (0.008, 0.05, 0.005), (0, 0.098, -0.052), blued)
    k.box("GuardFront", (0.008, 0.005, 0.03), (0, 0.122, -0.037), blued)
    k.box("Trigger", (0.006, 0.006, 0.024), (0, 0.098, -0.036), dark, rot=(0.25, 0, 0))
    k.box("Latch", (0.004, 0.012, 0.008), (-0.015, 0.088, 0.02), dark)
    return k.parts


def model_shotgun():
    """A pump-action shotgun (870-like): walnut stock and forend, blued receiver, barrel over the magazine tube."""
    blued = material("ShotgunBlued", (0.09, 0.09, 0.1), metallic=0.85, roughness=0.32)
    dark = material("ShotgunDark", (0.025, 0.025, 0.028), metallic=0.4, roughness=0.6)
    wood = material("ShotgunWood", (0.26, 0.11, 0.04), roughness=0.42)
    rubber = material("ShotgunPad", (0.04, 0.035, 0.035), roughness=0.9)
    red = material("ShotgunShell", (0.55, 0.06, 0.04), roughness=0.5)
    k = GunKit()
    k.prism("Stock", [(0.012, -0.135), (0.012, 0.012), (0.04, 0.02), (0.27, 0.004), (0.3, -0.018), (0.3, -0.05),
                      (0.27, -0.065), (0.1, -0.135)], 0.042, wood)
    k.box("RecoilPad", (0.044, 0.022, 0.15), (0, 0.0, -0.062), rubber, bevel=0.006)
    k.box("Receiver", (0.046, 0.23, 0.07), (0, 0.41, -0.006), blued, bevel=0.006)
    k.box("EjectionPort", (0.003, 0.07, 0.024), (0.0235, 0.43, 0.008), dark)
    k.box("ShellInPort", (0.004, 0.03, 0.014), (0.022, 0.425, 0.008), red)
    k.box("TriggerGuard", (0.014, 0.08, 0.008), (0, 0.36, -0.052), dark, bevel=0.002)
    k.box("Trigger", (0.006, 0.008, 0.025), (0, 0.36, -0.038), dark, rot=(0.25, 0, 0))
    k.box("Safety", (0.034, 0.008, 0.008), (0, 0.33, -0.044), dark)
    k.tube("Barrel", 0.0125, 0.52, 1.0, 0.012, blued)
    k.box("Rib", (0.008, 0.48, 0.005), (0, 0.76, 0.026), dark)
    k.box("Bead", (0.004, 0.004, 0.006), (0, 0.995, 0.031), material("ShotgunBead", (0.9, 0.85, 0.7), metallic=1.0))
    k.tube("MagTube", 0.012, 0.52, 0.9, -0.018, blued)
    k.tube("MagCap", 0.0135, 0.9, 0.925, -0.018, dark)
    k.box("BarrelBand", (0.03, 0.02, 0.048), (0, 0.885, -0.002), blued)
    # pump forend with grip grooves
    k.box("Forend", (0.052, 0.2, 0.05), (0, 0.64, -0.02), wood, bevel=0.014)
    for i in range(7):
        for sx in (-1, 1):
            k.box(f"Groove{i}{sx}", (0.003, 0.006, 0.03), (sx * 0.026, 0.57 + i * 0.023, -0.02), dark)
    k.box("ActionBar", (0.004, 0.13, 0.008), (0.02, 0.55, -0.02), blued)
    return k.parts


def model_ak():
    """An AK-style rifle modelled from scratch (y forward from the butt to the muzzle, z up), real-life size."""
    metal = material("AkMetal", (0.07, 0.07, 0.075), metallic=0.7, roughness=0.4)
    dark = material("AkDark", (0.03, 0.03, 0.033), metallic=0.4, roughness=0.6)
    wood = material("AkWood", (0.33, 0.14, 0.05), roughness=0.5)
    mag_mat = material("AkMag", (0.24, 0.09, 0.03), roughness=0.45)
    k = GunKit()
    prism, box, tube, parts = k.prism, k.box, k.tube, k.parts

    prism("Stock", [(0.0, -0.115), (0.0, 0.025), (0.03, 0.03), (0.25, 0.022), (0.25, -0.03), (0.07, -0.115)], 0.038, wood)
    box("ButtPlate", (0.04, 0.012, 0.14), (0, 0.004, -0.045), dark)
    box("Receiver", (0.046, 0.3, 0.066), (0, 0.4, -0.002), metal, bevel=0.004)
    box("DustCover", (0.04, 0.27, 0.022), (0, 0.41, 0.04), metal, bevel=0.008)
    prism("Grip", [(0.29, -0.034), (0.335, -0.034), (0.315, -0.135), (0.275, -0.13)], 0.032, mag_mat)
    box("TriggerGuard", (0.012, 0.075, 0.006), (0, 0.355, -0.07), dark)
    box("Trigger", (0.008, 0.008, 0.025), (0, 0.35, -0.05), dark, rot=(0.3, 0, 0))
    # curved magazine: segments bending forward
    y, z, angle = 0.4, -0.035, 0.0
    for i in range(5):
        angle += math.radians(7)
        seg = box(f"Mag{i}", (0.03, 0.068, 0.046), (0, y + math.sin(angle) * 0.023, z - math.cos(angle) * 0.023),
                  mag_mat, rot=(angle, 0, 0))
        y += math.sin(angle) * 0.044
        z -= math.cos(angle) * 0.044
    box("HandguardLow", (0.05, 0.19, 0.045), (0, 0.645, -0.018), wood, bevel=0.01)
    box("HandguardUp", (0.04, 0.15, 0.03), (0, 0.63, 0.035), wood, bevel=0.01)
    box("RearSight", (0.03, 0.04, 0.02), (0, 0.555, 0.055), metal)
    tube("Barrel", 0.011, 0.55, 0.89, -0.002, metal)
    tube("GasTube", 0.009, 0.7, 0.77, 0.03, metal)
    box("GasBlock", (0.03, 0.03, 0.055), (0, 0.77, 0.012), metal)
    box("FrontSight", (0.024, 0.02, 0.05), (0, 0.85, 0.022), metal)
    tube("MuzzleBrake", 0.015, 0.88, 0.925, -0.002, dark)
    tube("ChargingHandle", 0.006, 0.47, 0.5, 0.015, metal, x=0.03)
    box("Selector", (0.004, 0.11, 0.012), (-0.026, 0.42, 0.02), metal)
    return parts


PISTOL_COLORS = {"Metal": (0.16, 0.16, 0.17), "DarkerMetal": (0.06, 0.06, 0.065), "Muzzle": (0.12, 0.12, 0.13),
                 "Wood": (0.32, 0.16, 0.07), "Magazine": (0.09, 0.09, 0.1), "Material.003": (0.2, 0.2, 0.21)}
SNIPER_COLORS = {"LightWood": (0.32, 0.17, 0.07), "DarkWood": (0.2, 0.1, 0.04), "Black": (0.03, 0.03, 0.035),
                 "Metal": (0.14, 0.14, 0.15), "Barrels": (0.08, 0.08, 0.09), "Barrel": (0.08, 0.08, 0.09),
                 "Green": (0.12, 0.16, 0.1), "Trigger": (0.1, 0.1, 0.1), "Magazine": (0.06, 0.06, 0.065),
                 "BulletYellow": (0.7, 0.5, 0.15), "BulletOrange": (0.6, 0.3, 0.1)}
WEAPONS = {
    # source, length (m), grip point (bbox fractions: x, y from the rear, z from the bottom) and where it goes;
    # hands: (grip point as bbox fractions, finger direction, palm direction); material colour overrides
    "pistol": dict(src="guns/FPS Pack/Blends/Pistol.blend", length=0.24, grip=(0.5, 0.17, 0.3), at=(0.09, 0.32, -0.17), yaw=6,
                   right=((0.5, 0.17, 0.3), (0, 1, -0.25), (-1, 0, 0)),
                   left=((0.0, 0.14, 0.15), (0.3, 0.8, -0.3), (1, 0.2, 0.3)), colors=PISTOL_COLORS),
    "rifle": dict(src="model:ak", length=0.72, grip=(0.5, 0.33, 0.45), at=(0.165, 0.4, -0.265), yaw=8,
                  right=((0.5, 0.33, 0.45), (0, 1, -0.3), (-1, 0, 0)),
                  left=((0.5, 0.7, 0.66), (0.6, 0.8, 0), (0, 0, 1)), colors={}),
    "revolver": dict(src="model:revolver", length=0.3, grip=(0.5, 0.12, 0.36), at=(0.1, 0.32, -0.17),
                     yaw=6, right=((0.5, 0.12, 0.36), (0, 1, -0.25), (-1, 0, 0)),
                     left=((0.0, 0.1, 0.2), (0.3, 0.8, -0.3), (1, 0.2, 0.3)), colors={}),
    "smg": dict(src="model:smg", length=0.6, grip=(0.5, 0.37, 0.55), at=(0.14, 0.38, -0.22), yaw=7,
                right=((0.5, 0.37, 0.55), (0, 1, -0.3), (-1, 0, 0)),
                left=((0.5, 0.68, 0.72), (0.6, 0.8, 0), (0, 0, 1)), colors={}),
    "sniper": dict(src="guns/FPS Pack/Blends/SniperRifle.blend", length=1.05, grip=(0.5, 0.3, 0.4), at=(0.13, 0.38, -0.23),
                   yaw=8, right=((0.5, 0.3, 0.4), (0, 1, -0.3), (-1, 0, 0)),
                   left=((0.5, 0.6, 0.62), (0.6, 0.8, 0), (0, 0, 1)), colors=SNIPER_COLORS),
    "shotgun": dict(src="model:shotgun", length=1.0, grip=(0.5, 0.31, 0.56), at=(0.12, 0.38, -0.21), yaw=9,
                    right=((0.5, 0.31, 0.56), (0, 1, -0.35), (-1, 0, 0)),
                    left=((0.5, 0.64, 0.5), (0.6, 0.8, 0), (0, 0, 1)), colors={}),
    "rpg": dict(src="guns/rpg/RPG7.fbx", length=1.0, grip=(0.5, 0.4, 0.1), at=(0.19, 0.36, -0.36), yaw=4,
                right=((0.5, 0.4, 0.12), (0, 1, -0.2), (-1, 0, 0)),
                left=((0.5, 0.56, 0.12), (0, 1, -0.2), (1, 0, 0)), colors={}),
}


def build_viewmodels(only=()):
    out = os.path.join(PROJECT, "models", "weapons")
    for name, w in WEAPONS.items():
        if only and name not in only:
            continue
        reset()
        if w["src"].startswith("model:"):
            objs = {"model:ak": model_ak, "model:smg": model_smg, "model:revolver": model_revolver,
                    "model:shotgun": model_shotgun}[w["src"]]()
        else:
            objs = import_any(os.path.join(SRC, w["src"]))
            fix_flat_materials(objs, w["colors"], [os.path.dirname(os.path.join(SRC, w["src"])), os.path.join(SRC, "guns")])
            if w.get("rest_pose"):  # the file is saved mid-animation
                for o in objs:
                    if o.type == 'ARMATURE':
                        o.data.pose_position = 'REST'
            objs = bake_skinned(objs)
        for o in objs:
            if o.name.startswith("Muzzle"):
                o.name = "Gun"  # the marker below owns the name
        root, lo, hi, muzzle = normalize_weapon(objs, w["length"], w["grip"], w["at"])
        # Turn the gun a little towards the screen centre so its side shows, not just its back.
        at = Vector(w["at"])
        yaw = Matrix.Translation(at) @ Matrix.Rotation(math.radians(w.get("yaw", 0.0)), 4, 'Z') @ Matrix.Translation(-at)
        root.matrix_world = yaw @ root.matrix_world
        muzzle = yaw @ muzzle
        turn = yaw.to_3x3()

        def frac(f):
            return yaw @ Vector((lo.x + (hi.x - lo.x) * f[0], lo.y + (hi.y - lo.y) * f[1], lo.z + (hi.z - lo.z) * f[2]))

        def hand(spec):
            return frac(spec[0]), turn @ Vector(spec[1]), turn @ Vector(spec[2])
        arms = build_real_arms(hand(w["right"]), hand(w["left"]))
        m = add_muzzle(muzzle)
        rocket = next((o for o in objs if "Rocket" in o.name), None)
        if rocket is not None:
            rocket.name = "LoadedRocket"
        export_glb(os.path.join(out, f"{name}_fp.glb"), objs + [root, arms, m])
        if rocket is not None:
            export_rocket(rocket, out)
        export_world_model(objs, root, os.path.join(out, f"{name}_world.glb"))
    if only and "knife" not in only and "grenade" not in only:
        return
    # knife: modelled here, held in the right hand
    reset()
    parts = model_knife()
    root = bpy.data.objects.new("WeaponRoot", None)
    bpy.context.scene.collection.objects.link(root)
    for o in parts:
        o.parent = root
    # Hammer grip: the handle runs up through the fist, the blade points up and forward.
    grip = Vector((0.13, 0.32, -0.2))
    root.matrix_world = Matrix.Translation(grip) @ Matrix.Rotation(math.radians(-15), 4, 'Y') \
        @ Matrix.Rotation(math.radians(60), 4, 'X') @ Matrix.Rotation(math.radians(-65), 4, 'Y') \
        @ Matrix.Translation(Vector((0, 0.062, 0)))
    arms = build_real_arms((grip, (0, 1, -0.2), (-1, 0, 0)), None)
    export_glb(os.path.join(out, "knife_fp.glb"), parts + [root, arms])
    root.matrix_world = Matrix.Identity(4)
    export_glb(os.path.join(out, "knife_world.glb"), parts + [root])
    # grenade: modelled here, held in the right hand
    reset()
    parts = model_grenade()
    root = bpy.data.objects.new("WeaponRoot", None)
    bpy.context.scene.collection.objects.link(root)
    for o in parts:
        o.parent = root
    # Held up in the open fingers, fuse and ring on top, ready to be thrown overarm.
    grip = Vector((0.15, 0.36, -0.13))
    root.matrix_world = Matrix.Translation(grip + Vector((-0.012, 0.0, 0.012))) @ Matrix.Rotation(math.radians(-15), 4, 'Y')
    arms = build_real_arms((grip, (0, 0.9, 0.3), (-1, 0, 0.15)), None, curl=50.0)
    export_glb(os.path.join(out, "grenade_fp.glb"), parts + [root, arms])
    root.matrix_world = Matrix.Identity(4)
    export_glb(os.path.join(out, "grenade_world.glb"), parts + [root])


def split_warhead(meshes, lo, hi):
    """Separates the grenade at the front of the RPG so the game can hide it after firing."""
    cut = hi.y - (hi.y - lo.y) * 0.3
    pieces = []
    for o in meshes:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        mw = o.matrix_world
        front = [f for f in bm.faces if (mw @ f.calc_center_median()).y > cut]
        if front:
            new_bm = bmesh.new()
            # Copy front faces into a new mesh.
            vmap = {}
            for f in front:
                vs = []
                for v in f.verts:
                    if v not in vmap:
                        vmap[v] = new_bm.verts.new(v.co)
                    vs.append(vmap[v])
                nf = new_bm.faces.new(vs)
                nf.material_index = f.material_index
            uv_src = bm.loops.layers.uv.active
            if uv_src is not None:
                uv_dst = new_bm.loops.layers.uv.new()
                for f, nf in zip(front, new_bm.faces):
                    for l_src, l_dst in zip(f.loops, nf.loops):
                        l_dst[uv_dst].uv = l_src[uv_src].uv
            me = bpy.data.meshes.new("LoadedRocket")
            new_bm.to_mesh(me)
            new_bm.free()
            for mat in o.data.materials:
                me.materials.append(mat)
            piece = bpy.data.objects.new("LoadedRocket", me)
            bpy.context.scene.collection.objects.link(piece)
            piece.matrix_world = mw.copy()
            pieces.append(piece)
            bmesh.ops.delete(bm, geom=front, context='FACES')
            bm.to_mesh(o.data)
        bm.free()
    return pieces[0]


def export_rocket(warhead, out):
    """The flying rocket: the warhead re-centred with its tip pointing +Y."""
    copy = warhead.copy()
    copy.data = warhead.data.copy()
    copy.name = "Rocket"
    bpy.context.scene.collection.objects.link(copy)
    pts = world_verts([copy])
    lo, hi = bounds(pts)
    copy.matrix_world = Matrix.Translation(-(lo + hi) / 2) @ copy.matrix_world
    export_glb(os.path.join(out, "rocket.glb"), [copy])
    bpy.data.objects.remove(copy)


def export_world_model(objs, root, path):
    saved = root.matrix_world.copy()
    pts = world_verts(objs)
    lo, hi = bounds(pts)
    root.matrix_world = Matrix.Translation(-(lo + hi) / 2) @ saved
    export_glb(path, objs + [root])
    root.matrix_world = saved


# ---------------------------------------------------------------- previews
def render_first_person(glb, out_png):
    reset()
    bpy.ops.import_scene.gltf(filepath=glb)
    scene = bpy.context.scene
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.angle = math.radians(FOV_DEG)
    cam.data.clip_start = 0.02
    cam.rotation_euler = (math.pi / 2, 0, 0)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 3.5
    sun.rotation_euler = (0.6, 0.4, 0.3)
    scene.collection.objects.link(sun)
    scene.world = bpy.data.worlds.new("W")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.32, 0.36, 1)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.render.resolution_x, scene.render.resolution_y = 640, 360
    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)


if "characters" in PARTS:
    build_characters()
if "viewmodels" in PARTS:
    build_viewmodels()
if "bosses" in PARTS:
    build_bosses()
if "kenney" in PARTS:
    build_kenney()
KENNEY_ONLY = [p[7:] for p in PARTS if p.startswith("kenney:")]
if KENNEY_ONLY:
    build_kenney(KENNEY_ONLY)
if "lineup" in PARTS:
    vdir = os.path.join(PROJECT, "models", "vehicles")
    render_lineup([os.path.join(vdir, n + ".glb") for n in list(VEHICLES) + ["bus"]], os.path.join(SRC, "previews", "vehicles.png"),
                  spacing=7.0, cam=(0, -30, 14))
BOSS_ONLY = [p[5:] for p in PARTS if p.startswith("boss:")]
if BOSS_ONLY:
    build_bosses(BOSS_ONLY)
ONLY = [p[3:] for p in PARTS if p.startswith("vm:")]
if ONLY:
    build_viewmodels(ONLY)
    for n in ONLY:
        render_first_person(os.path.join(PROJECT, "models", "weapons", f"{n}_fp.glb"), os.path.join(SRC, "previews", f"{n}_fp.png"))
if "armstest" in PARTS:
    arms_test()
    render_first_person(os.path.join(SRC, "previews", "arms_test.glb"), os.path.join(SRC, "previews", "arms_test.png"))
if "previews" in PARTS:
    out = os.path.join(PROJECT, "models", "weapons")
    for n in ("knife", "pistol", "shotgun", "rifle", "rpg"):
        render_first_person(os.path.join(out, f"{n}_fp.glb"), os.path.join(SRC, "previews", f"{n}_fp.png"))
