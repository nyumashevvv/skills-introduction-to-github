class_name World
extends Node3D
## Koh Samui at 1:1 scale: heightfield terrain streamed in chunks with LOD,
## plus roads, buildings and palms built around the player.

const N := 2400            # heightfield samples per side
const CELL := 10.0         # metres between samples
const HALF := 12000.0      # map half size in metres
const CHUNK := 1200.0      # chunk size in metres
const NC := 20             # chunks per side
const CPC := 120           # cells per chunk
const LODS := [1, 3, 8]    # sample step per LOD level
const LOD_DIST := [650.0, 2600.0]
const CONTENT_DIST := 1300.0
const CONTENT_FREE := 1900.0

enum { WATER, SAND, GRASS, JUNGLE, URBAN, ROAD, BUILDING, ROCK }

var heights: PackedFloat32Array
var classes: PackedByteArray
var roads_data: Array
var buildings_data: Array
var places: Array = []
var colormap: Texture2D

var terrain_mat: ShaderMaterial
var road_mat: ShaderMaterial
var building_mat: StandardMaterial3D
var palm_mesh: ArrayMesh

var _indices := {}          # step -> PackedInt32Array
var _chunks := []           # per chunk: {node, lod, meshes, content}
var _queue := []            # pending jobs [priority, kind, chunk, arg]
var _queued := {}
var _focus := Vector3.ZERO
var _since_scan := 1.0
var building_polys := {}    # chunk -> Array of [Rect2, PackedVector2Array]


func _ready() -> void:
	_load_data()
	_make_materials()
	palm_mesh = Props.make_palm()
	for c in NC * NC:
		var n := Node3D.new()
		n.name = "C%d" % c
		n.position = Vector3(-HALF + (c % NC) * CHUNK, 0, -HALF + (c / NC) * CHUNK)
		add_child(n)
		var mi := MeshInstance3D.new()
		mi.material_override = terrain_mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		n.add_child(mi)
		_chunks.append({"node": n, "mi": mi, "lod": -1, "meshes": {}, "content": null})
		_set_lod(c, LODS.size() - 1)
	if not OS.get_cmdline_user_args().has("--nowater"):
		_add_water()
	_add_places()


func _load_data() -> void:
	var f := FileAccess.open("res://data/heights.bin", FileAccess.READ)
	heights = f.get_buffer(f.get_length()).decompress(N * N * 4, FileAccess.COMPRESSION_DEFLATE).to_float32_array()
	f = FileAccess.open("res://data/landclass.bin", FileAccess.READ)
	classes = f.get_buffer(f.get_length()).decompress(N * N, FileAccess.COMPRESSION_DEFLATE)
	roads_data = JSON.parse_string(FileAccess.get_file_as_string("res://data/roads.json"))
	buildings_data = JSON.parse_string(FileAccess.get_file_as_string("res://data/buildings.json"))
	places = JSON.parse_string(FileAccess.get_file_as_string("res://data/places.json"))
	colormap = load("res://data/colormap.png")


func _make_materials() -> void:
	var noise := FastNoiseLite.new()
	noise.frequency = 0.05
	noise.fractal_octaves = 4
	var nt := NoiseTexture2D.new()
	nt.width = 256
	nt.height = 256
	nt.seamless = true
	nt.noise = noise
	nt.generate_mipmaps = true
	terrain_mat = ShaderMaterial.new()
	terrain_mat.shader = load("res://shaders/terrain.gdshader")
	terrain_mat.set_shader_parameter("colormap", colormap)
	terrain_mat.set_shader_parameter("detail", nt)
	road_mat = ShaderMaterial.new()
	road_mat.shader = load("res://shaders/road.gdshader")
	building_mat = StandardMaterial3D.new()
	building_mat.vertex_color_use_as_albedo = true
	building_mat.vertex_color_is_srgb = true
	building_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	building_mat.roughness = 0.9


# ------------------------------------------------------------ height queries
func _h(i: int, j: int) -> float:
	return heights[clampi(j, 0, N - 1) * N + clampi(i, 0, N - 1)]


## Exact height of the fine terrain mesh at world x,z (matches triangulation).
func height_at(x: float, z: float) -> float:
	var gx := clampf((x + HALF) / CELL, 0.0, N - 1.001)
	var gz := clampf((z + HALF) / CELL, 0.0, N - 1.001)
	var i := int(gx)
	var j := int(gz)
	var fx := gx - i
	var fz := gz - j
	var a := heights[j * N + i]
	var b := heights[j * N + i + 1]
	var c := heights[(j + 1) * N + i]
	if fx + fz <= 1.0:
		return a + (b - a) * fx + (c - a) * fz
	var d := heights[(j + 1) * N + i + 1]
	return d + (c - d) * (1.0 - fx) + (b - d) * (1.0 - fz)


func class_at(x: float, z: float) -> int:
	var i := clampi(int(round((x + HALF) / CELL)), 0, N - 1)
	var j := clampi(int(round((z + HALF) / CELL)), 0, N - 1)
	return classes[j * N + i]


func chunk_of(x: float, z: float) -> int:
	var cx := clampi(int((x + HALF) / CHUNK), 0, NC - 1)
	var cz := clampi(int((z + HALF) / CHUNK), 0, NC - 1)
	return cz * NC + cx


func is_blocked(x: float, z: float) -> bool:
	var c := chunk_of(x, z)
	var p := Vector2(x, z)
	for cc in [c, c - 1, c + 1, c - NC, c + NC]:
		if not building_polys.has(cc):
			continue
		for b in building_polys[cc]:
			if b[0].has_point(p) and Geometry2D.is_point_in_polygon(p, b[1]):
				return true
	return false


## Nearest road point (and direction) to x,z, searching nearby chunks' data.
func nearest_road(x: float, z: float, main_only := false) -> Dictionary:
	var best := {"d": INF}
	var c0 := chunk_of(x, z)
	for dz in range(-1, 2):
		for dx in range(-1, 2):
			var c: int = c0 + dz * NC + dx
			if c < 0 or c >= NC * NC:
				continue
			for r in roads_data[c]:
				if main_only and r["k"] > 1:
					continue
				var p: Array = r["p"]
				for k in range(0, p.size() - 2, 2):
					var d := Vector2(p[k] - x, p[k + 1] - z).length_squared()
					if d < best["d"]:
						best = {"d": d, "pos": Vector2(p[k], p[k + 1]), "dir": Vector2(p[k + 2] - p[k], p[k + 3] - p[k + 1]).normalized()}
	return best


# ------------------------------------------------------------ streaming
func set_focus(p: Vector3) -> void:
	_focus = p


func _process(delta: float) -> void:
	_since_scan += delta
	if _since_scan > 0.2:
		_since_scan = 0.0
		_scan()
	var t0 := Time.get_ticks_usec()
	while not _queue.is_empty() and Time.get_ticks_usec() - t0 < 7000:
		var job: Array = _queue.pop_front()
		_queued.erase(str(job[1], job[2]))
		_run_job(job)


func _chunk_dist(c: int) -> float:
	var x0 := -HALF + (c % NC) * CHUNK
	var z0 := -HALF + (c / NC) * CHUNK
	var dx := maxf(0.0, maxf(x0 - _focus.x, _focus.x - x0 - CHUNK))
	var dz := maxf(0.0, maxf(z0 - _focus.z, _focus.z - z0 - CHUNK))
	return Vector2(dx, dz).length()


func _scan() -> void:
	_queue.clear()
	_queued.clear()
	for c in NC * NC:
		var d := _chunk_dist(c)
		var want := LODS.size() - 1
		for l in LOD_DIST.size():
			if d < LOD_DIST[l]:
				want = l
				break
		var ch: Dictionary = _chunks[c]
		if want != ch["lod"]:
			_enqueue(d, "lod", c, want)
		if d < CONTENT_DIST and ch["content"] == null:
			_enqueue(d + 50.0, "content", c, 0)
		elif d > CONTENT_FREE and ch["content"] != null:
			ch["content"].queue_free()
			ch["content"] = null
			building_polys.erase(c)
	_queue.sort_custom(func(a, b): return a[0] < b[0])


func _enqueue(prio: float, kind: String, c: int, arg: int) -> void:
	var key := str(kind, c)
	if _queued.has(key):
		return
	_queued[key] = true
	_queue.append([prio, kind, c, arg])


func _run_job(job: Array) -> void:
	var c: int = job[2]
	if job[1] == "lod":
		_set_lod(c, job[3])
	else:
		_build_content(c)


## Builds everything near a point immediately (used at spawn / teleport).
func warm_up(p: Vector3) -> void:
	_focus = p
	_scan()
	for job in _queue:
		if job[0] < 900.0:
			_run_job(job)
	_scan()


func _set_lod(c: int, lod: int) -> void:
	var ch: Dictionary = _chunks[c]
	var step: int = LODS[lod]
	if not ch["meshes"].has(step):
		ch["meshes"][step] = _build_terrain_mesh(c, step)
	ch["mi"].mesh = ch["meshes"][step]
	ch["lod"] = lod
	# drop the finest mesh when not in use to save memory
	if lod != 0:
		ch["meshes"].erase(LODS[0])


func _indices_for(step: int) -> PackedInt32Array:
	if _indices.has(step):
		return _indices[step]
	var n := CPC / step + 1
	var idx := PackedInt32Array()
	for j in n - 1:
		for i in n - 1:
			var a := j * n + i
			idx.append_array([a, a + 1, a + n, a + 1, a + n + 1, a + n])
	# skirt: ring of vertices stored after the grid, same order as _skirt_edge
	var edge := _skirt_edge(n)
	var base := n * n
	for k in edge.size():
		var k2 := (k + 1) % edge.size()
		idx.append_array([edge[k], edge[k2], base + k, edge[k2], base + k2, base + k])
	_indices[step] = idx
	return idx


func _skirt_edge(n: int) -> PackedInt32Array:
	var e := PackedInt32Array()
	for i in n: e.append(i)
	for j in range(1, n): e.append(j * n + n - 1)
	for i in range(n - 2, -1, -1): e.append((n - 1) * n + i)
	for j in range(n - 2, 0, -1): e.append(j * n)
	return e


func _build_terrain_mesh(c: int, step: int) -> ArrayMesh:
	var n := CPC / step + 1
	var gi0 := (c % NC) * CPC
	var gj0 := (c / NC) * CPC
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	verts.resize(n * n)
	norms.resize(n * n)
	var s := float(step) * CELL
	for b in n:
		var gj := gj0 + b * step
		for a in n:
			var gi := gi0 + a * step
			var k := b * n + a
			verts[k] = Vector3(a * s, _h(gi, gj), b * s)
			norms[k] = Vector3(_h(gi - step, gj) - _h(gi + step, gj), 2.0 * s, _h(gi, gj - step) - _h(gi, gj + step)).normalized()
	var edge := _skirt_edge(n)
	for k in edge:
		verts.append(verts[k] - Vector3(0, 4.0 + step * 2.0, 0))
		norms.append(norms[k])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	arr[Mesh.ARRAY_INDEX] = _indices_for(step)
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


# ------------------------------------------------------------ chunk content
func _build_content(c: int) -> void:
	var ch: Dictionary = _chunks[c]
	if ch["content"] != null:
		return
	var root := Node3D.new()
	ch["node"].add_child(root)
	ch["content"] = root
	var origin: Vector3 = ch["node"].position
	var rm := _build_roads(c, origin)
	if rm:
		var mi := MeshInstance3D.new()
		mi.mesh = rm
		mi.material_override = road_mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(mi)
	var bm := _build_buildings(c, origin)
	if bm:
		var mi2 := MeshInstance3D.new()
		mi2.mesh = bm
		mi2.material_override = building_mat
		root.add_child(mi2)
	var palms := _build_palms(c, origin)
	if palms:
		root.add_child(palms)


const ROAD_COL := [Color(0.30, 0.30, 0.31, 1), Color(0.36, 0.36, 0.35, 0), Color(0.58, 0.45, 0.32, 0), Color(0.34, 0.34, 0.35, 1)]
const ROAD_LIFT := [0.24, 0.20, 0.16, 0.14]


func _build_roads(c: int, o: Vector3) -> ArrayMesh:
	var list: Array = roads_data[c]
	if list.is_empty():
		return null
	var v := PackedVector3Array()
	var nrm := PackedVector3Array()
	var col := PackedColorArray()
	var uv := PackedVector2Array()
	var idx := PackedInt32Array()
	for r in list:
		var p: Array = r["p"]
		var cnt := p.size() / 2
		if cnt < 2:
			continue
		var hw: float = r["w"] * 0.5
		var kind: int = r["k"]
		var lift: float = ROAD_LIFT[kind]
		var cc: Color = ROAD_COL[kind]
		if kind == 0 and hw < 3.4:
			cc.a = 0.0
		var dist := 0.0
		var base := v.size()
		for k in cnt:
			var pt := Vector2(p[k * 2], p[k * 2 + 1])
			var prev := Vector2(p[maxi(k - 1, 0) * 2], p[maxi(k - 1, 0) * 2 + 1])
			var nxt := Vector2(p[mini(k + 1, cnt - 1) * 2], p[mini(k + 1, cnt - 1) * 2 + 1])
			var t := (nxt - prev).normalized()
			var side := Vector2(-t.y, t.x) * hw
			if k > 0:
				dist += pt.distance_to(prev)
			for sgn in [-1.0, 1.0]:
				var q: Vector2 = pt + side * sgn
				v.append(Vector3(q.x - o.x, height_at(q.x, q.y) + lift, q.y - o.z))
				nrm.append(Vector3.UP)
				col.append(cc)
				uv.append(Vector2(0.0 if sgn < 0 else 1.0, dist))
			if k > 0:
				var a := base + (k - 1) * 2
				idx.append_array([a, a + 2, a + 1, a + 1, a + 2, a + 3])
	if idx.is_empty():
		return null
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_NORMAL] = nrm
	arr[Mesh.ARRAY_COLOR] = col
	arr[Mesh.ARRAY_TEX_UV] = uv
	arr[Mesh.ARRAY_INDEX] = idx
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


const WALLS := [Color(0.93, 0.92, 0.88), Color(0.95, 0.89, 0.76), Color(0.88, 0.85, 0.80), Color(0.96, 0.86, 0.80), Color(0.80, 0.84, 0.86), Color(0.92, 0.80, 0.62)]
const ROOFS := [Color(0.72, 0.32, 0.18), Color(0.62, 0.22, 0.16), Color(0.80, 0.45, 0.22), Color(0.25, 0.42, 0.45), Color(0.45, 0.30, 0.22)]


func _build_buildings(c: int, o: Vector3) -> ArrayMesh:
	var list: Array = buildings_data[c]
	if list.is_empty():
		return null
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = c * 7919 + 13
	var polys := []
	for b in list:
		var p: Array = b["p"]
		var cnt := p.size() / 2
		if cnt < 3:
			continue
		var poly := PackedVector2Array()
		for k in cnt:
			poly.append(Vector2(p[k * 2], p[k * 2 + 1]))
		if Geometry2D.is_polygon_clockwise(poly):
			poly.reverse()
		var gmin := INF
		var gmax := -INF
		for q in poly:
			var hh := height_at(q.x, q.y)
			gmin = minf(gmin, hh)
			gmax = maxf(gmax, hh)
		var bottom := gmin - 1.0
		var top: float = gmax + float(b["h"])
		var wall: Color = WALLS[rng.randi() % WALLS.size()]
		var roof: Color = ROOFS[rng.randi() % ROOFS.size()]
		polys.append([_rect_of(poly), poly])
		# walls
		for k in cnt:
			var a2: Vector2 = poly[k]
			var b2: Vector2 = poly[(k + 1) % cnt]
			var e := (b2 - a2)
			if e.length() < 0.01:
				continue
			var nn := Vector3(e.y, 0, -e.x).normalized()
			var shade := 0.82 + 0.18 * absf(nn.x)
			st.set_color(wall * shade)
			st.set_normal(nn)
			var A := Vector3(a2.x - o.x, bottom, a2.y - o.z)
			var B := Vector3(b2.x - o.x, bottom, b2.y - o.z)
			var At := Vector3(A.x, top, A.z)
			var Bt := Vector3(B.x, top, B.z)
			for vv in [A, B, Bt, A, Bt, At]:
				st.add_vertex(vv)
		# roof
		if cnt == 4 and float(b["h"]) < 8.0:
			_gable_roof(st, poly, top, o, roof)
		else:
			var tri := Geometry2D.triangulate_polygon(poly)
			st.set_color(Color(0.62, 0.61, 0.58) if rng.randf() < 0.6 else roof)
			st.set_normal(Vector3.UP)
			for t in tri:
				st.add_vertex(Vector3(poly[t].x - o.x, top, poly[t].y - o.z))
	building_polys[c] = polys
	return st.commit()


func _rect_of(poly: PackedVector2Array) -> Rect2:
	var r := Rect2(poly[0], Vector2.ZERO)
	for q in poly:
		r = r.expand(q)
	return r.grow(0.5)


func _gable_roof(st: SurfaceTool, poly: PackedVector2Array, top: float, o: Vector3, col: Color) -> void:
	# ridge runs along the longer side
	var p := poly
	if p[0].distance_to(p[1]) > p[1].distance_to(p[2]):
		p = PackedVector2Array([poly[1], poly[2], poly[3], poly[0]])
	# now p0-p1 and p2-p3 are the short sides
	var m1 := (p[0] + p[1]) * 0.5
	var m2 := (p[2] + p[3]) * 0.5
	var rh := p[0].distance_to(p[1]) * 0.32
	var o2 := Vector2(o.x, o.z)
	var V := func(q: Vector2, y: float) -> Vector3: return Vector3(q.x - o2.x, y, q.y - o2.y)
	var R1: Vector3 = V.call(m1, top + rh)
	var R2: Vector3 = V.call(m2, top + rh)
	var P := []
	for q in p:
		P.append(V.call(q, top))
	var faces := [[P[1], P[2], R2, R1], [P[3], P[0], R1, R2]]
	for f in faces:
		var nn: Vector3 = (f[1] - f[0]).cross(f[3] - f[0]).normalized()
		if nn.y < 0: nn = -nn
		st.set_color(col * (0.8 + 0.2 * nn.y))
		st.set_normal(nn)
		for vv in [f[0], f[1], f[2], f[0], f[2], f[3]]:
			st.add_vertex(vv)
	st.set_color(Color(0.9, 0.88, 0.84))
	for tr in [[P[0], P[1], R1], [P[2], P[3], R2]]:
		st.set_normal((tr[1] - tr[0]).cross(tr[2] - tr[0]).normalized())
		for vv in tr:
			st.add_vertex(vv)


const PALM_P := [0.0, 0.05, 0.10, 0.45, 0.04, 0.0, 0.0, 0.0]


func _build_palms(c: int, o: Vector3) -> MultiMeshInstance3D:
	var rng := RandomNumberGenerator.new()
	rng.seed = c * 104729 + 7
	var xf := []
	var step := 13.0
	var cells := int(CHUNK / step)
	for b in cells:
		for a in cells:
			var x := o.x + (a + rng.randf()) * step
			var z := o.z + (b + rng.randf()) * step
			var cl := class_at(x, z)
			if rng.randf() >= PALM_P[cl]:
				continue
			var y := height_at(x, z)
			if y < 0.6:
				continue
			# keep palms off roads and buildings nearby
			if class_at(x + 6, z) == ROAD or class_at(x - 6, z) == ROAD or class_at(x, z + 6) == ROAD or class_at(x, z - 6) == ROAD:
				continue
			var s := rng.randf_range(0.75, 1.3)
			var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3(s, s, s))
			basis = Basis(Vector3(rng.randf() - 0.5, 0, rng.randf() - 0.5).normalized(), rng.randf() * 0.12) * basis
			xf.append(Transform3D(basis, Vector3(x - o.x, y - 0.2, z - o.z)))
	if xf.is_empty():
		return null
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = palm_mesh
	mm.instance_count = xf.size()
	for k in xf.size():
		mm.set_instance_transform(k, xf[k])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mmi


# ------------------------------------------------------------ static scenery
func _add_water() -> void:
	var pm := PlaneMesh.new()
	pm.size = Vector2(80000, 80000)
	pm.subdivide_width = 0
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/water.gdshader")
	var noise := FastNoiseLite.new()
	noise.frequency = 0.03
	var nt := NoiseTexture2D.new()
	nt.seamless = true
	nt.noise = noise
	nt.generate_mipmaps = true
	mat.set_shader_parameter("waves", nt)
	var mi := MeshInstance3D.new()
	mi.mesh = pm
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)


func _add_places() -> void:
	for p in places:
		var k: String = p["k"]
		var x: float = p["x"]
		var z: float = p["z"]
		var l := Label3D.new()
		l.text = p["n"]
		l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		l.fixed_size = true
		l.pixel_size = 0.0012 if k == "town" else 0.0008
		l.font_size = 48
		l.outline_size = 12
		l.modulate = {"town": Color(1, 1, 1), "beach": Color(1, 0.95, 0.6), "waterfall": Color(0.6, 0.9, 1),
			"temple": Color(1, 0.8, 0.4), "sight": Color(1, 0.75, 0.9), "airport": Color(0.8, 0.9, 1)}.get(k, Color.WHITE)
		l.position = Vector3(x, height_at(x, z) + (45.0 if k == "town" else 18.0), z)
		l.visibility_range_end = 3500.0 if k == "town" else 1200.0
		add_child(l)
	# a golden landmark at the Big Buddha temple
	for p in places:
		if p["en"] == "Big Buddha":
			var bb := Props.make_buddha()
			bb.position = Vector3(p["x"], height_at(p["x"], p["z"]), p["z"])
			add_child(bb)
			break
