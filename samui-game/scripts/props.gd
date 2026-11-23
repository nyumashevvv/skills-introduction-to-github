class_name Props
## Procedural models: Big Buddha statue, electricity poles.
## Plants come from Blender: models/vegetation.glb.
## The scooter and rider come from Blender: models/scooter_rider.glb.


static func _box(st: SurfaceTool, c: Vector3, h: Vector3) -> void:
	var faces := [
		[Vector3.UP, [Vector3(-1, 1, -1), Vector3(1, 1, -1), Vector3(1, 1, 1), Vector3(-1, 1, 1)]],
		[Vector3.DOWN, [Vector3(-1, -1, 1), Vector3(1, -1, 1), Vector3(1, -1, -1), Vector3(-1, -1, -1)]],
		[Vector3.RIGHT, [Vector3(1, -1, -1), Vector3(1, -1, 1), Vector3(1, 1, 1), Vector3(1, 1, -1)]],
		[Vector3.LEFT, [Vector3(-1, -1, 1), Vector3(-1, -1, -1), Vector3(-1, 1, -1), Vector3(-1, 1, 1)]],
		[Vector3.BACK, [Vector3(1, -1, 1), Vector3(-1, -1, 1), Vector3(-1, 1, 1), Vector3(1, 1, 1)]],
		[Vector3.FORWARD, [Vector3(-1, -1, -1), Vector3(1, -1, -1), Vector3(1, 1, -1), Vector3(-1, 1, -1)]],
	]
	for f in faces:
		st.set_normal(f[0])
		var q: Array = f[1]
		for i in [0, 1, 2, 0, 2, 3]:
			st.add_vertex(c + q[i] * h)


static func _mat(col: Color, metal := 0.0, rough := 0.7) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = col
	m.metallic = metal
	m.roughness = rough
	return m


static func _part(parent: Node3D, mesh: Mesh, mat: Material, pos: Vector3, rot := Vector3.ZERO, scl := Vector3.ONE) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.rotation = rot
	mi.scale = scl
	parent.add_child(mi)
	return mi


static func _box_mesh(size: Vector3) -> BoxMesh:
	var b := BoxMesh.new()
	b.size = size
	return b


static func _cyl(r: float, h: float, r2 := -1.0) -> CylinderMesh:
	var c := CylinderMesh.new()
	c.top_radius = r if r2 < 0 else r2
	c.bottom_radius = r
	c.height = h
	c.radial_segments = 14
	return c


static func _sph(r: float) -> SphereMesh:
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2
	s.radial_segments = 16
	s.rings = 8
	return s


## Seated golden Buddha on a white pedestal, about 15 m tall.
static func make_buddha() -> Node3D:
	var root := Node3D.new()
	var gold := _mat(Color(0.95, 0.72, 0.25), 0.85, 0.3)
	var white := _mat(Color(0.95, 0.93, 0.9))
	var red := _mat(Color(0.7, 0.15, 0.1))
	_part(root, _box_mesh(Vector3(14, 3, 14)), white, Vector3(0, 1.5, 0))
	_part(root, _box_mesh(Vector3(11, 2, 11)), red, Vector3(0, 4, 0))
	_part(root, _cyl(4.5, 1.2, 4.0), gold, Vector3(0, 5.6, 0))                       # lotus base
	_part(root, _sph(3.6), gold, Vector3(0, 7.2, 0), Vector3.ZERO, Vector3(1.25, 0.55, 1))   # crossed legs
	_part(root, _cyl(2.0, 5.0, 1.4), gold, Vector3(0, 10.0, 0))                      # torso
	_part(root, _sph(1.35), gold, Vector3(0, 13.4, 0), Vector3.ZERO, Vector3(1, 1.15, 1))    # head
	_part(root, _cyl(0.5, 1.6, 0.05), gold, Vector3(0, 15.2, 0))                     # ushnisha
	for sx in [-1.0, 1.0]:
		_part(root, _cyl(0.55, 3.6, 0.45), gold, Vector3(2.2 * sx, 10.0, 0.4), Vector3(0.3, 0, 0.35 * sx))
	return root


static func _vc_mat() -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.vertex_color_is_srgb = true
	mat.roughness = 0.85
	return mat


static func _prism(st: SurfaceTool, base: Vector3, h: float, r0: float, r1: float, sides: int, col: Color) -> void:
	for k in sides:
		var a0 := TAU * k / sides
		var a1 := TAU * (k + 1) / sides
		var p0 := base + Vector3(cos(a0) * r0, 0, sin(a0) * r0)
		var p1 := base + Vector3(cos(a1) * r0, 0, sin(a1) * r0)
		var q0 := base + Vector3(cos(a0) * r1, h, sin(a0) * r1)
		var q1 := base + Vector3(cos(a1) * r1, h, sin(a1) * r1)
		st.set_color(col * (0.85 + 0.15 * cos(a0 - 0.8)))
		st.set_normal(Vector3(cos((a0 + a1) / 2), 0, sin((a0 + a1) / 2)))
		for v in [p0, p1, q1, p0, q1, q0]:
			st.add_vertex(v)


## Concrete electricity pole, 9 m, crossarm across the road (local Z).
static func make_pole() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var concrete := Color(0.72, 0.71, 0.68)
	_prism(st, Vector3.ZERO, 9.0, 0.15, 0.1, 6, concrete)
	st.set_color(Color(0.3, 0.3, 0.3))
	_box(st, Vector3(0, 8.1, 0), Vector3(0.06, 0.06, 0.8))          # crossarm
	st.set_color(Color(0.85, 0.85, 0.8))
	for z in [-0.6, 0.0, 0.6]:
		_box(st, Vector3(0, 8.22, z), Vector3(0.04, 0.07, 0.04))     # insulators
	st.set_color(Color(0.25, 0.25, 0.25))
	_box(st, Vector3(0.12, 6.4, 0.18), Vector3(0.05, 0.35, 0.05))    # telecom clamp
	st.set_color(Color(0.95, 0.85, 0.1))
	_box(st, Vector3(0, 1.6, 0), Vector3(0.155, 0.25, 0.155))       # yellow-black band
	st.set_color(Color(0.1, 0.1, 0.1))
	_box(st, Vector3(0, 1.2, 0), Vector3(0.157, 0.15, 0.157))
	var m := st.commit()
	m.surface_set_material(0, _vc_mat())
	return m


static func make_transformer() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	st.set_color(Color(0.55, 0.58, 0.55))
	_box(st, Vector3(0.38, 7.0, 0), Vector3(0.22, 0.42, 0.22))
	st.set_color(Color(0.3, 0.3, 0.3))
	_box(st, Vector3(0.2, 7.0, 0), Vector3(0.05, 0.05, 0.25))
	var m := st.commit()
	m.surface_set_material(0, _vc_mat())
	return m
