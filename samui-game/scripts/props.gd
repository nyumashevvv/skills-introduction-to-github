class_name Props
## Procedural models: palm tree, scooter with rider, Big Buddha statue.


static func make_palm() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	# trunk: slightly curved tapered prism
	var sides := 6
	var segs := 5
	var height := 9.0
	var ring := []
	for s in segs + 1:
		var t := float(s) / segs
		var cpos := Vector3(0.6 * t * t, height * t, 0)
		var r := lerpf(0.24, 0.14, t)
		var pts := []
		for k in sides:
			var a := TAU * k / sides
			pts.append(cpos + Vector3(cos(a) * r, 0, sin(a) * r))
		ring.append(pts)
	for s in segs:
		for k in sides:
			var k2 := (k + 1) % sides
			var a: Vector3 = ring[s][k]
			var b: Vector3 = ring[s][k2]
			var c: Vector3 = ring[s + 1][k]
			var d: Vector3 = ring[s + 1][k2]
			var shade := 0.8 + 0.2 * float(s % 2)
			st.set_color(Color(0.45, 0.36, 0.26) * shade)
			st.set_normal(Vector3(a.x + b.x, 0, a.z + b.z).normalized())
			for v in [a, b, d, a, d, c]:
				st.add_vertex(v)
	# fronds
	var top := Vector3(0.6, height, 0)
	var fronds := 9
	for f in fronds:
		var ang := TAU * f / fronds + 0.3 * sin(f * 2.1)
		var dir := Vector3(cos(ang), 0, sin(ang))
		var side := Vector3(-dir.z, 0, dir.x)
		var length := 4.6 + 0.8 * sin(f * 1.7)
		var lift := 0.9 + 0.3 * cos(f * 2.3)
		var n := 5
		var prev_l := top
		var prev_r := top
		var prev_c := top
		for s in range(1, n + 1):
			var t := float(s) / n
			var c := top + dir * length * t + Vector3.UP * (lift * t * 2.0 - 2.4 * t * t)
			var w := 0.85 * sin(PI * minf(t * 1.1, 1.0))
			var l := c + side * w - Vector3.UP * w * 0.25
			var r := c - side * w - Vector3.UP * w * 0.25
			var g := Color(0.16, 0.36, 0.10).lerp(Color(0.32, 0.42, 0.12), t * 0.6)
			st.set_color(g)
			st.set_normal((Vector3.UP + dir * 0.2).normalized())
			for v in [prev_c, prev_l, l, prev_c, l, c, prev_c, c, r, prev_c, r, prev_r]:
				st.add_vertex(v)
			prev_l = l
			prev_r = r
			prev_c = c
	# coconuts
	st.set_color(Color(0.35, 0.30, 0.12))
	for k in 3:
		var p := top + Vector3(cos(k * 2.1) * 0.3, -0.35, sin(k * 2.1) * 0.3)
		_box(st, p, Vector3(0.18, 0.18, 0.18))
	var m := st.commit()
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.vertex_color_is_srgb = true
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.roughness = 0.9
	m.surface_set_material(0, mat)
	return m


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


## Scooter facing -Z, origin between the wheels on the ground.
static func make_scooter(body_col := Color(0.85, 0.15, 0.2)) -> Node3D:
	var root := Node3D.new()
	var paint := _mat(body_col, 0.3, 0.35)
	var black := _mat(Color(0.05, 0.05, 0.05), 0.0, 0.8)
	var chrome := _mat(Color(0.8, 0.8, 0.82), 0.9, 0.2)
	var skin := _mat(Color(0.85, 0.65, 0.5))
	var shirt := _mat(Color(0.95, 0.95, 0.9))
	var shorts := _mat(Color(0.2, 0.35, 0.6))
	var helmet := _mat(Color(0.95, 0.8, 0.1), 0.2, 0.3)
	var wheel := _cyl(0.27, 0.12)
	_part(root, wheel, black, Vector3(0, 0.27, -0.62), Vector3(0, 0, PI / 2))
	_part(root, wheel, black, Vector3(0, 0.27, 0.6), Vector3(0, 0, PI / 2))
	_part(root, _box_mesh(Vector3(0.36, 0.22, 0.9)), paint, Vector3(0, 0.42, 0.25))            # rear body
	_part(root, _box_mesh(Vector3(0.30, 0.08, 0.55)), black, Vector3(0, 0.36, -0.2))          # floorboard
	_part(root, _box_mesh(Vector3(0.34, 0.70, 0.16)), paint, Vector3(0, 0.72, -0.52), Vector3(-0.25, 0, 0))  # leg shield
	_part(root, _box_mesh(Vector3(0.32, 0.10, 0.62)), black, Vector3(0, 0.6, 0.28))           # seat
	_part(root, _cyl(0.025, 0.95), chrome, Vector3(0, 0.75, -0.6), Vector3(-0.3, 0, 0))       # steering column
	_part(root, _cyl(0.02, 0.62), chrome, Vector3(0, 1.17, -0.48), Vector3(0, 0, PI / 2))     # handlebar
	_part(root, _box_mesh(Vector3(0.18, 0.12, 0.1)), chrome, Vector3(0, 1.08, -0.66))         # headlight
	_part(root, _box_mesh(Vector3(0.22, 0.24, 0.3)), paint, Vector3(0, 0.3, -0.62))           # front fender
	# rider
	var r := Node3D.new()
	r.name = "Rider"
	root.add_child(r)
	_part(r, _box_mesh(Vector3(0.4, 0.55, 0.24)), shirt, Vector3(0, 1.05, 0.18), Vector3(-0.15, 0, 0))   # torso
	_part(r, _sph(0.14), skin, Vector3(0, 1.45, 0.1))                                                     # head
	_part(r, _sph(0.165), helmet, Vector3(0, 1.49, 0.11), Vector3.ZERO, Vector3(1, 0.85, 1.05))           # helmet
	for sx in [-1.0, 1.0]:
		_part(r, _box_mesh(Vector3(0.15, 0.14, 0.45)), shorts, Vector3(0.11 * sx, 0.72, 0.05))            # thigh
		_part(r, _box_mesh(Vector3(0.11, 0.38, 0.12)), skin, Vector3(0.12 * sx, 0.5, -0.17))              # shin
		_part(r, _box_mesh(Vector3(0.09, 0.09, 0.46)), skin, Vector3(0.22 * sx, 1.12, -0.18), Vector3(0.3, 0.15 * sx, 0))  # arm
	return root


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
