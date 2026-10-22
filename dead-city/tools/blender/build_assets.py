"""Builds the game's 3D models with Blender (run headless):

    blender -b --python tools/blender/build_assets.py -- <sources dir> <project dir> [part ...]

<sources dir> is where tools/fetch_assets.sh unpacked the CC0 source packs.
Parts: characters, viewmodels, previews (default: characters viewmodels).

Coordinates for first-person models: the camera sits at the origin looking down +Y with +Z up,
which the glTF exporter turns into Godot's camera space (-Z forward, +Y up), in metres.
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, PROJECT = argv[0], argv[1]
PARTS = argv[2:] or ["characters", "viewmodels"]
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


def build_characters():
    for out_name, src in CHARACTERS.items():
        reset()
        objs = append_objects(os.path.join(UACP, src + ".blend"), actions=True)
        fix_flat_materials(objs)
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


PISTOL_COLORS = {"Metal": (0.16, 0.16, 0.17), "DarkerMetal": (0.06, 0.06, 0.065), "Muzzle": (0.12, 0.12, 0.13),
                 "Wood": (0.32, 0.16, 0.07), "Magazine": (0.09, 0.09, 0.1), "Material.003": (0.2, 0.2, 0.21)}
SHOTGUN_COLORS = {"Barrels": (0.13, 0.13, 0.14), "Black": (0.035, 0.035, 0.04), "DarkMetal": (0.07, 0.07, 0.075),
                  "Trigger": (0.1, 0.1, 0.1), "BulletRed": (0.5, 0.05, 0.03), "BulletYellow": (0.7, 0.5, 0.15)}
WEAPONS = {
    # source, length (m), grip point (bbox fractions: x, y from the rear, z from the bottom) and where it goes;
    # hands: (grip point as bbox fractions, finger direction, palm direction); material colour overrides
    "pistol": dict(src="guns/FPS Pack/Blends/Pistol.blend", length=0.24, grip=(0.5, 0.17, 0.3), at=(0.09, 0.32, -0.17), yaw=6,
                   right=((0.5, 0.17, 0.3), (0, 1, -0.25), (-1, 0, 0)),
                   left=((0.0, 0.14, 0.15), (0.3, 0.8, -0.3), (1, 0.2, 0.3)), colors=PISTOL_COLORS),
    "rifle": dict(src="guns/GunPack Vol.1/Blends/ak47.blend", length=0.8, grip=(0.5, 0.36, 0.3), at=(0.13, 0.48, -0.28), yaw=12,
                  right=((0.5, 0.36, 0.3), (0, 1, -0.3), (-1, 0, 0)),
                  left=((0.5, 0.68, 0.66), (0.6, 0.8, 0), (0, 0, 1)), colors={}),
    "shotgun": dict(src="guns/FPS Pack/Blends/Shotgun.blend", length=0.98, grip=(0.5, 0.33, 0.5), at=(0.12, 0.38, -0.21), yaw=9,
                    right=((0.5, 0.33, 0.5), (0, 1, -0.35), (-1, 0, 0)),
                    left=((0.5, 0.62, 0.7), (0.6, 0.8, 0), (0, 0, 1)), colors=SHOTGUN_COLORS),
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
        objs = import_any(os.path.join(SRC, w["src"]))
        fix_flat_materials(objs, w["colors"], [os.path.dirname(os.path.join(SRC, w["src"])), os.path.join(SRC, "guns")])
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
    if only and "knife" not in only:
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
