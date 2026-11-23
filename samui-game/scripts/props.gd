class_name Props
## Procedural street furniture: electricity poles, lamps, signs.
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


## Town street lamp: 7.5 m steel pole, arm reaching over the road (local -Z).
static func make_streetlamp() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var steel := Color(0.42, 0.46, 0.45)
	_prism(st, Vector3.ZERO, 7.4, 0.09, 0.05, 8, steel)
	st.set_color(steel)
	_box(st, Vector3(0, 7.35, -0.7), Vector3(0.03, 0.03, 0.75))
	st.set_color(Color(0.25, 0.27, 0.27))
	_box(st, Vector3(0, 7.32, -1.45), Vector3(0.14, 0.06, 0.3))
	st.set_color(Color(1.0, 0.97, 0.85))
	_box(st, Vector3(0, 7.25, -1.45), Vector3(0.1, 0.012, 0.24))
	st.set_color(Color(0.3, 0.32, 0.32))
	_box(st, Vector3(0, 0.25, 0), Vector3(0.14, 0.25, 0.14))
	var m := st.commit()
	m.surface_set_material(0, _vc_mat())
	return m


## Blue Thai highway direction board on two posts, facing along local +Z.
static func make_sign() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var post := Color(0.75, 0.76, 0.76)
	for x in [-1.0, 1.0]:
		_prism(st, Vector3(x, 0, 0), 3.4, 0.05, 0.05, 6, post)
	st.set_color(Color(0.95, 0.95, 0.95))
	_box(st, Vector3(0, 2.6, 0.06), Vector3(1.55, 0.8, 0.03))
	st.set_color(Color(0.05, 0.25, 0.62))
	_box(st, Vector3(0, 2.6, 0.075), Vector3(1.47, 0.72, 0.03))
	# white text lines and arrows
	st.set_color(Color(0.95, 0.95, 0.95))
	for y in [2.95, 2.7, 2.45, 2.2]:
		_box(st, Vector3(-0.25, y, 0.11), Vector3(0.9, 0.05, 0.01))
	_box(st, Vector3(1.05, 2.75, 0.11), Vector3(0.22, 0.05, 0.01))
	_box(st, Vector3(1.05, 2.35, 0.11), Vector3(0.22, 0.05, 0.01))
	var m := st.commit()
	var mat := _vc_mat()
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.surface_set_material(0, mat)
	return m
