"""Tiny helper for writing Godot 4 .tscn / .tres files from Python."""
import math

def fmt(v):
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, float): return repr(round(v, 4))
    return str(v)

def V3(x, y, z): return f'Vector3({fmt(float(x))}, {fmt(float(y))}, {fmt(float(z))})'
def V2(x, y): return f'Vector2({fmt(float(x))}, {fmt(float(y))})'
def C(r, g, b, a=1.0): return f'Color({fmt(float(r))}, {fmt(float(g))}, {fmt(float(b))}, {fmt(float(a))})'
def S(s): return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
def NP(p): return f'NodePath("{p}")'
def NPS(paths): return 'Array[NodePath]([' + ', '.join(NP(p) for p in paths) + '])'
def PSA(items): return 'PackedStringArray(' + ', '.join(S(i) for i in items) + ')'
RX = 1.5708  # 90 degrees: turns a Y-axis cylinder to lie along Z

M = 'res://materials/'
SND = 'res://sounds/'


class Scene:
    def __init__(self):
        self.ext, self.sub, self.nodes = [], [], []
        self.ext_ids, self.n_sub = {}, 0
        self.mesh_cache = {}

    def ext_res(self, typ, path):
        if path not in self.ext_ids:
            rid = f'{len(self.ext) + 1}_{path.split("/")[-1].split(".")[0]}'
            self.ext_ids[path] = rid
            self.ext.append(f'[ext_resource type="{typ}" path="{path}" id="{rid}"]')
        return f'ExtResource("{self.ext_ids[path]}")'

    def mat(self, name):
        return self.ext_res('Material', f'{M}{name}.tres')

    def sound(self, name):
        return self.ext_res('AudioStream', f'{SND}{name}.wav')

    def sub_res(self, typ, **props):
        self.n_sub += 1
        rid = f'{typ}_{self.n_sub}'
        lines = [f'[sub_resource type="{typ}" id="{rid}"]'] + [f'{k} = {fmt(v)}' for k, v in props.items()]
        self.sub.append('\n'.join(lines))
        return f'SubResource("{rid}")'

    def cached_mesh(self, typ, **props):
        key = (typ, tuple(sorted(props.items())))
        if key not in self.mesh_cache:
            self.mesh_cache[key] = self.sub_res(typ, **props)
        return self.mesh_cache[key]

    def node(self, name, typ=None, parent=None, instance=None, groups=None, node_paths=None, **props):
        head = f'[node name="{name}"'
        if typ: head += f' type="{typ}"'
        if parent is not None: head += f' parent="{parent}"'
        if instance: head += f' instance={instance}'
        if node_paths: head += ' node_paths=' + PSA(node_paths)
        if groups: head += ' groups=[' + ', '.join(S(g) for g in groups) + ']'
        head += ']'
        self.nodes.append('\n'.join([head] + [f'{k} = {fmt(v)}' for k, v in props.items()]))

    def _mesh_node(self, name, parent, mesh, pos, rot, extra):
        props = dict(mesh=mesh, position=V3(*pos))
        if rot: props['rotation'] = V3(*rot)
        props.update(extra)
        self.node(name, 'MeshInstance3D', parent, **props)

    def box(self, name, parent, size, pos, mat, rot=None, **extra):
        mesh = self.cached_mesh('BoxMesh', size=V3(*size), material=self.mat(mat))
        self._mesh_node(name, parent, mesh, pos, rot, extra)

    def cyl(self, name, parent, radius, height, pos, mat, rot=None, top=None, segments=16, **extra):
        mesh = self.cached_mesh('CylinderMesh', top_radius=float(radius if top is None else top),
                                bottom_radius=float(radius), height=float(height), radial_segments=segments,
                                rings=1, material=self.mat(mat))
        self._mesh_node(name, parent, mesh, pos, rot, extra)

    def sphere(self, name, parent, radius, pos, mat, **extra):
        mesh = self.cached_mesh('SphereMesh', radius=float(radius), height=float(radius * 2),
                                radial_segments=12, rings=6, material=self.mat(mat))
        self._mesh_node(name, parent, mesh, pos, None, extra)

    def save(self, path):
        parts = ['[gd_scene format=3]'] + self.ext + self.sub + self.nodes
        open(path, 'w').write('\n\n'.join(parts) + '\n')


def material(path, color=(0.5, 0.5, 0.5), metallic=0.0, roughness=0.8, texture=None, uv_scale=0.5,
             emission=None, energy=1.0, extra=None, pbr=None, normal_scale=1.0, rough_map=True):
    """pbr: an ambientCG set in textures/pbr (<id>_color/_normal/_rough.jpg), mapped world-triplanar."""
    lines = []
    ext = ''
    if pbr:
        ext = ''.join(f'[ext_resource type="Texture2D" path="res://textures/pbr/{pbr}_{m}.jpg" id="{i}_{m}"]\n\n'
                      for i, m in enumerate(('color', 'normal', 'rough'), 1))
        lines += [f'albedo_color = {C(*color)}', 'albedo_texture = ExtResource("1_color")',
                  f'metallic = {fmt(float(metallic))}', f'roughness = {fmt(1.0 if rough_map else float(roughness))}',
                  *(['roughness_texture = ExtResource("3_rough")'] if rough_map else []),
                  'normal_enabled = true', f'normal_scale = {fmt(float(normal_scale))}', 'normal_texture = ExtResource("2_normal")',
                  f'uv1_scale = {V3(uv_scale, uv_scale, uv_scale)}', 'uv1_triplanar = true', 'uv1_world_triplanar = true']
        for k, v in (extra or {}).items():
            lines.append(f'{k} = {fmt(v)}')
        open(path, 'w').write('[gd_resource type="StandardMaterial3D" load_steps=4 format=3]\n\n' + ext + '[resource]\n'
                              + '\n'.join(lines) + '\n')
        return
    if texture:
        ext = f'[ext_resource type="Texture2D" path="res://textures/{texture}.png" id="1_tex"]\n\n'
    lines.append(f'albedo_color = {C(*color)}')
    if texture:
        lines += ['albedo_texture = ExtResource("1_tex")', f'uv1_scale = {V3(uv_scale, uv_scale, uv_scale)}',
                  'uv1_triplanar = true', 'uv1_world_triplanar = true']
    if metallic: lines.append(f'metallic = {fmt(float(metallic))}')
    lines.append(f'roughness = {fmt(float(roughness))}')
    if emission:
        lines += ['emission_enabled = true', f'emission = {C(*emission)}',
                  f'emission_energy_multiplier = {fmt(float(energy))}']
    for k, v in (extra or {}).items():
        lines.append(f'{k} = {fmt(v)}')
    head = '[gd_resource type="StandardMaterial3D" format=3]\n\n' if not texture else \
        '[gd_resource type="StandardMaterial3D" load_steps=2 format=3]\n\n'
    open(path, 'w').write(head + ext + '[resource]\n' + '\n'.join(lines) + '\n')
