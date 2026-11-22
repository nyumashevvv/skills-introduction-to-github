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
var building_wall_mat: ShaderMaterial
var wire_mat: StandardMaterial3D
var pole_mesh: Mesh
var transformer_mesh: Mesh
var palm_mesh: ArrayMesh

var _indices := {}          # step -> PackedInt32Array
var _chunks := []           # per chunk: {node, lod, meshes, content}
var _queue := []            # pending jobs [priority, kind, chunk, arg]
var _queued := {}
var _focus := Vector3.ZERO
var _since_scan := 1.0


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
	road_mat.set_shader_parameter("noise", nt)
	wire_mat = StandardMaterial3D.new()
	wire_mat.albedo_color = Color(0.04, 0.04, 0.04)
	wire_mat.roughness = 0.6
	wire_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	pole_mesh = Props.make_pole()
	transformer_mesh = Props.make_transformer()
	building_mat = StandardMaterial3D.new()
	building_mat.vertex_color_use_as_albedo = true
	building_mat.vertex_color_is_srgb = true
	building_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	building_mat.roughness = 0.9
	building_wall_mat = ShaderMaterial.new()
	building_wall_mat.shader = load("res://shaders/building.gdshader")


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
	var p := Vector2(x, z)
	var key := Vector2i(floori(x / GRID), floori(z / GRID))
	var c0 := chunk_of(x, z)
	for dz in range(-1, 2):
		for dx in range(-1, 2):
			var grid: Dictionary = building_grid.get(c0 + dz * NC + dx, {})
			for b in grid.get(key, []):
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
			_free_buildings(c)
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
	var bm := _build_buildings(c, origin)
	if bm:
		var mi2 := MeshInstance3D.new()
		mi2.mesh = bm
		root.add_child(mi2)
	var pole_runs := []
	var rm := _build_roads(c, origin, pole_runs)
	if rm:
		var mi := MeshInstance3D.new()
		mi.mesh = rm
		mi.material_override = road_mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(mi)
	if not pole_runs.is_empty():
		root.add_child(_build_poles(pole_runs))
	var palms := _build_palms(c, origin)
	if palms:
		root.add_child(palms)


# ------------------------------------------------------------ roads
const ROAD_LIFT := [0.10, 0.08, 0.06, 0.05]
const CURB_H := 0.15
const WALK_W := 1.8
const POLE_SPACING := 36.0


class RoadBuf:
	var v := PackedVector3Array()
	var n := PackedVector3Array()
	var c := PackedColorArray()
	var uv := PackedVector2Array()
	var uv2 := PackedVector2Array()
	var idx := PackedInt32Array()

	## Adds one strip: a[i] and b[i] are the two long edges, across_a/b their UV.x.
	func strip(a: PackedVector3Array, b: PackedVector3Array, along: PackedFloat32Array, across_a: float, across_b: float,
			nrm: Array, col: Color, kind: float, seed: float) -> void:
		var base := v.size()
		for i in a.size():
			v.append(a[i]); v.append(b[i])
			n.append(nrm[i]); n.append(nrm[i])
			c.append(col); c.append(col)
			uv.append(Vector2(across_a, along[i])); uv.append(Vector2(across_b, along[i]))
			uv2.append(Vector2(kind, seed)); uv2.append(Vector2(kind, seed))
			if i > 0:
				var k := base + (i - 1) * 2
				idx.append_array([k, k + 2, k + 1, k + 1, k + 2, k + 3])

	func set_junction(from: int, flags: PackedFloat32Array) -> void:
		# junction flag lives in COLOR.r, one value per cross-section (two vertices)
		for i in flags.size():
			c[from + i * 2].r = flags[i]
			c[from + i * 2 + 1].r = flags[i]

	func commit() -> ArrayMesh:
		if idx.is_empty():
			return null
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = v
		arr[Mesh.ARRAY_NORMAL] = n
		arr[Mesh.ARRAY_COLOR] = c
		arr[Mesh.ARRAY_TEX_UV] = uv
		arr[Mesh.ARRAY_TEX_UV2] = uv2
		arr[Mesh.ARRAY_INDEX] = idx
		var m := ArrayMesh.new()
		m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
		return m


func _build_roads(c: int, o: Vector3, poles: Array) -> ArrayMesh:
	var list: Array = roads_data[c]
	if list.is_empty():
		return null
	var rb := RoadBuf.new()
	var ri := 0
	for r in list:
		ri += 1
		var p: Array = r["p"]
		var cnt := p.size() / 2
		if cnt < 2:
			continue
		var w: float = r["w"]
		var hw := w * 0.5
		var kind: int = r["k"]
		var mat: int = r.get("m", 0)
		var jstr: String = r.get("j", "")
		var lift: float = ROAD_LIFT[kind]
		var seed := fmod(float(c * 131 + ri) * 0.618034, 1.0)
		var markings := 0.0
		if kind == 3:
			markings = 0.6
		elif kind == 0 and w >= 6.0 and mat == 0:
			markings = 1.0
		var col := Color(0.0, w / 50.0, mat * 0.5, markings)
		# town roads get raised sidewalks with painted curbs
		var mid := Vector2(p[(cnt / 2) * 2], p[(cnt / 2) * 2 + 1])
		var urban := kind <= 1 and w >= 6.0 and mat != 2 and _is_town(mid)
		var verge := 0.6 if mat == 2 else 1.1
		# centre line, sides and distance along
		var C := PackedVector2Array()
		var S := PackedVector2Array()
		var along := PackedFloat32Array()
		var dist := 0.0
		for k in cnt:
			var pt := Vector2(p[k * 2], p[k * 2 + 1])
			var prev := Vector2(p[maxi(k - 1, 0) * 2], p[maxi(k - 1, 0) * 2 + 1])
			var nxt := Vector2(p[mini(k + 1, cnt - 1) * 2], p[mini(k + 1, cnt - 1) * 2 + 1])
			var t := (nxt - prev).normalized()
			if k > 0:
				dist += pt.distance_to(prev)
			C.append(pt)
			S.append(Vector2(-t.y, t.x))
			along.append(dist)
		var ups := []
		ups.resize(cnt)
		ups.fill(Vector3.UP)
		# road surface
		var L := PackedVector3Array()
		var R := PackedVector3Array()
		for k in cnt:
			var a := C[k] - S[k] * hw
			var b := C[k] + S[k] * hw
			L.append(Vector3(a.x - o.x, height_at(a.x, a.y) + lift, a.y - o.z))
			R.append(Vector3(b.x - o.x, height_at(b.x, b.y) + lift, b.y - o.z))
		var first := rb.v.size()
		rb.strip(L, R, along, 0.0, w, ups, col, 0.0, seed)
		if jstr.length() == cnt:
			var fl := PackedFloat32Array()
			for k in cnt:
				fl.append(1.0 if jstr[k] == "1" else 0.0)
			rb.set_junction(first, fl)
		# both sides: curb + sidewalk, or a gravel verge
		for side in [-1.0, 1.0]:
			var edge := L if side < 0 else R
			if urban:
				var top := PackedVector3Array()
				var outer := PackedVector3Array()
				var ground := PackedVector3Array()
				var curb_n := []
				for k in cnt:
					var e := edge[k]
					top.append(e + Vector3(0, CURB_H, 0))
					var q: Vector2 = C[k] + S[k] * side * (hw + WALK_W)
					var gq: Vector2 = C[k] + S[k] * side * (hw + WALK_W + 0.5)
					var yt := maxf(e.y + CURB_H, height_at(q.x, q.y) + 0.05)
					outer.append(Vector3(q.x - o.x, yt, q.y - o.z))
					ground.append(Vector3(gq.x - o.x, height_at(gq.x, gq.y) - 0.05, gq.y - o.z))
					curb_n.append(Vector3(-S[k].x * side, 0, -S[k].y * side))
				rb.strip(edge, top, along, 0.0, CURB_H, curb_n, col, 1.0, seed)
				rb.strip(top, outer, along, 0.0, WALK_W, ups, col, 2.0, seed)
				rb.strip(outer, ground, along, 0.0, 0.5, ups, col, 3.0, seed)
			else:
				var ground2 := PackedVector3Array()
				for k in cnt:
					var gq: Vector2 = C[k] + S[k] * side * (hw + verge)
					ground2.append(Vector3(gq.x - o.x, height_at(gq.x, gq.y) - 0.04, gq.y - o.z))
				rb.strip(edge, ground2, along, 0.0, verge, ups, col, 3.0, seed)
		# electricity poles along bigger roads, Thai style
		if (kind == 0 or (kind == 1 and w >= 5.0)) and dist > 20.0:
			var side_p := -1.0 if seed < 0.5 else 1.0
			var off := hw + (WALK_W - 0.4 if urban else verge + 0.4)
			var run := []
			var next_d := fmod(seed * 97.0, POLE_SPACING)
			var k2 := 0
			while next_d < dist:
				while k2 < cnt - 2 and along[k2 + 1] < next_d:
					k2 += 1
				var f := (next_d - along[k2]) / maxf(along[k2 + 1] - along[k2], 0.01)
				var cp := C[k2].lerp(C[k2 + 1], f)
				var sd := S[k2].lerp(S[k2 + 1], f).normalized()
				var pp := cp + sd * side_p * off
				var pos := Vector3(pp.x - o.x, height_at(pp.x, pp.y), pp.y - o.z)
				if class_at(pp.x, pp.y) != BUILDING and pos.y > 0.3 and not is_blocked(pp.x, pp.y):
					run.append([pos, Vector3(sd.x, 0, sd.y)])
				else:
					if run.size() > 0:
						poles.append(run)
					run = []
				next_d += POLE_SPACING
			if run.size() > 0:
				poles.append(run)
	return rb.commit()


func _is_town(pt: Vector2) -> bool:
	var n := 0
	for d in [Vector2(12, 0), Vector2(-12, 0), Vector2(0, 12), Vector2(0, -12), Vector2(20, 20), Vector2(-20, -20)]:
		var cl := class_at(pt.x + d.x, pt.y + d.y)
		if cl == BUILDING or cl == URBAN:
			n += 1
	return n >= 3


## Poles (MultiMesh) and the sagging cable bundles between them.
func _build_poles(runs: Array) -> Node3D:
	var xf := []
	var tf := []
	var wires := MeshBuf.new()
	var rng := RandomNumberGenerator.new()
	rng.seed = runs.size() * 31 + 5
	for run in runs:
		for i in run.size():
			var pos: Vector3 = run[i][0]
			var sd: Vector3 = run[i][1]
			var basis := Basis(Vector3.UP, atan2(sd.x, sd.z))
			xf.append(Transform3D(basis, pos))
			if rng.randf() < 0.12:
				tf.append(Transform3D(basis, pos))
			if i == 0:
				continue
			var a: Vector3 = run[i - 1][0]
			var asd: Vector3 = run[i - 1][1]
			# three power lines on the crossarm + a telecom bundle lower down
			for line in [[-0.6, 8.15, 0.55], [0.0, 8.15, 0.6], [0.6, 8.15, 0.55], [0.18, 6.6, 0.9], [0.22, 6.35, 1.1], [0.15, 6.1, 1.3]]:
				var p0: Vector3 = a + asd * line[0] + Vector3(0, line[1], 0)
				var p1: Vector3 = pos + sd * line[0] + Vector3(0, line[1], 0)
				_cable(wires, p0, p1, line[2] + rng.randf() * 0.3)
	var root := Node3D.new()
	if xf.size() > 0:
		root.add_child(_multimesh(pole_mesh, xf))
	if tf.size() > 0:
		root.add_child(_multimesh(transformer_mesh, tf))
	var m := ArrayMesh.new()
	wires.add_to(m, wire_mat)
	if m.get_surface_count() > 0:
		var mi := MeshInstance3D.new()
		mi.mesh = m
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.visibility_range_end = 450.0
		root.add_child(mi)
	return root


func _cable(mb: MeshBuf, a: Vector3, b: Vector3, sag: float) -> void:
	var segs := 7
	var prev := a
	var th := Vector3(0, 0.02, 0)
	for s in range(1, segs + 1):
		var t := float(s) / segs
		var q := a.lerp(b, t) - Vector3(0, sag * 4.0 * t * (1.0 - t), 0)
		var nn := (q - prev).cross(Vector3.UP).normalized()
		mb.quad(prev - th, q - th, q + th, prev + th, nn, Color(0.05, 0.05, 0.05))
		prev = q


func _multimesh(mesh: Mesh, xf: Array) -> MultiMeshInstance3D:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh
	mm.instance_count = xf.size()
	for k in xf.size():
		mm.set_instance_transform(k, xf[k])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.visibility_range_end = 700.0
	return mmi


class MeshBuf:
	var v := PackedVector3Array()
	var n := PackedVector3Array()
	var c := PackedColorArray()
	var uv := PackedVector2Array()
	var uv2 := PackedVector2Array()
	var with_uv := false

	func tri(a: Vector3, b: Vector3, d: Vector3, nn: Vector3, col: Color) -> void:
		v.append(a); v.append(b); v.append(d)
		n.append(nn); n.append(nn); n.append(nn)
		c.append(col); c.append(col); c.append(col)

	func quad(a: Vector3, b: Vector3, d: Vector3, e: Vector3, nn: Vector3, col: Color) -> void:
		tri(a, b, d, nn, col)
		tri(a, d, e, nn, col)

	## Wall quad with facade coordinates: u along the wall, v above ground.
	func wall(a: Vector3, b: Vector3, top: float, ground: float, nn: Vector3, col: Color, info: Vector2) -> void:
		var L := Vector2(b.x - a.x, b.z - a.z).length()
		var A2 := Vector3(a.x, top, a.z)
		var B2 := Vector3(b.x, top, b.z)
		for q in [[a, 0.0], [b, L], [B2, L], [a, 0.0], [B2, L], [A2, 0.0]]:
			var p: Vector3 = q[0]
			v.append(p)
			n.append(nn)
			c.append(col)
			uv.append(Vector2(q[1], p.y - ground))
			uv2.append(info)

	func add_to(m: ArrayMesh, mat: Material) -> void:
		if v.is_empty():
			return
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = v
		arr[Mesh.ARRAY_NORMAL] = n
		arr[Mesh.ARRAY_COLOR] = c
		if with_uv:
			arr[Mesh.ARRAY_TEX_UV] = uv
			arr[Mesh.ARRAY_TEX_UV2] = uv2
		m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
		m.surface_set_material(m.get_surface_count() - 1, mat)


const GRID := 40.0                  # collision grid cell, metres
var building_grid := {}             # chunk -> {Vector2i cell -> Array of [Rect2, PackedVector2Array]}

# Thai street palette: whitewash, cream, pastel and a few bold colours
const WALLS := [Color(0.95, 0.94, 0.90), Color(0.96, 0.91, 0.78), Color(0.93, 0.86, 0.70), Color(0.97, 0.84, 0.72),
	Color(0.80, 0.88, 0.90), Color(0.78, 0.90, 0.80), Color(0.96, 0.80, 0.80), Color(0.88, 0.88, 0.86),
	Color(0.98, 0.93, 0.60), Color(0.85, 0.62, 0.45), Color(0.70, 0.82, 0.92), Color(0.92, 0.92, 0.92)]
const ROOFS := [Color(0.72, 0.28, 0.16), Color(0.62, 0.18, 0.14), Color(0.84, 0.45, 0.20), Color(0.20, 0.42, 0.50),
	Color(0.24, 0.48, 0.30), Color(0.45, 0.28, 0.20), Color(0.55, 0.57, 0.60), Color(0.22, 0.32, 0.52)]


func _build_buildings(c: int, o: Vector3) -> ArrayMesh:
	var list: Array = buildings_data[c]
	if list.is_empty():
		return null
	var walls := MeshBuf.new()
	walls.with_uv = true
	var roofs := MeshBuf.new()
	var rng := RandomNumberGenerator.new()
	rng.seed = c * 7919 + 13
	var grid := {}
	for b in list:
		var p: Array = b["p"]
		var cnt := p.size() / 2
		if cnt < 3:
			continue
		var poly := PackedVector2Array()
		poly.resize(cnt)
		for k in cnt:
			poly[k] = Vector2(p[k * 2], p[k * 2 + 1])
		if Geometry2D.is_polygon_clockwise(poly):
			poly.reverse()
		var gmin := INF
		var gmax := -INF
		for q in poly:
			var hh := height_at(q.x, q.y)
			gmin = minf(gmin, hh)
			gmax = maxf(gmax, hh)
		var bh: float = b["h"]
		var bottom := gmin - 1.0
		var ground := gmax                       # facade starts at the highest ground point
		var top: float = gmax + bh
		var wall_col: Color = WALLS[rng.randi() % WALLS.size()]
		wall_col.a = rng.randf()                 # seed for the facade shader
		var roof_col: Color = ROOFS[rng.randi() % ROOFS.size()]
		var rect := _rect_of(poly)
		for gx in range(floori(rect.position.x / GRID), floori(rect.end.x / GRID) + 1):
			for gz in range(floori(rect.position.y / GRID), floori(rect.end.y / GRID) + 1):
				var key := Vector2i(gx, gz)
				if not grid.has(key):
					grid[key] = []
				grid[key].append([rect, poly])
		var area := absf(_area(poly))
		var pitched := cnt == 4 and bh < 8.0 and area < 600.0
		var wall_top := top if pitched else top + 0.8   # flat roofs get a parapet
		for k in cnt:
			var a2: Vector2 = poly[k]
			var b2: Vector2 = poly[(k + 1) % cnt]
			var e := b2 - a2
			if e.length_squared() < 0.0001:
				continue
			var nn := Vector3(e.y, 0, -e.x).normalized()
			var shade := 0.86 + 0.14 * absf(nn.x)
			var wc := Color(wall_col.r * shade, wall_col.g * shade, wall_col.b * shade, wall_col.a)
			walls.wall(Vector3(a2.x - o.x, bottom, a2.y - o.z), Vector3(b2.x - o.x, bottom, b2.y - o.z),
				wall_top, ground, nn, wc, Vector2(e.length(), bh))
		if pitched:
			var sides := [poly[0].distance_to(poly[1]), poly[1].distance_to(poly[2])]
			if maxf(sides[0], sides[1]) / maxf(minf(sides[0], sides[1]), 0.1) < 1.35 and rng.randf() < 0.6:
				_hip_roof(roofs, poly, top, o, roof_col)
			else:
				_gable_roof(roofs, poly, top, o, roof_col)
		else:
			var tri := Geometry2D.triangulate_polygon(poly)
			var rc := Color(0.58, 0.57, 0.54).lerp(Color(0.7, 0.68, 0.64), rng.randf())
			for t in range(0, tri.size() - 2, 3):
				roofs.tri(Vector3(poly[tri[t]].x - o.x, top, poly[tri[t]].y - o.z),
					Vector3(poly[tri[t + 1]].x - o.x, top, poly[tri[t + 1]].y - o.z),
					Vector3(poly[tri[t + 2]].x - o.x, top, poly[tri[t + 2]].y - o.z), Vector3.UP, rc)
			# rooftop water tank or AC unit
			if area > 40.0 and rng.randf() < 0.45:
				var cpos := _centroid(poly) + Vector2(rng.randf_range(-1.5, 1.5), rng.randf_range(-1.5, 1.5))
				if Geometry2D.is_point_in_polygon(cpos, poly):
					var tank := Color(0.15, 0.3, 0.6) if rng.randf() < 0.5 else Color(0.85, 0.85, 0.82)
					_box(roofs, Vector3(cpos.x - o.x, top + 0.75, cpos.y - o.z), Vector3(0.6, 0.75, 0.6), tank)
	building_grid[c] = grid
	var m := ArrayMesh.new()
	walls.add_to(m, building_wall_mat)
	roofs.add_to(m, building_mat)
	return m if m.get_surface_count() > 0 else null


func _free_buildings(c: int) -> void:
	building_grid.erase(c)


func _area(poly: PackedVector2Array) -> float:
	var s := 0.0
	for i in poly.size():
		var a := poly[i]
		var b := poly[(i + 1) % poly.size()]
		s += a.x * b.y - b.x * a.y
	return s * 0.5


func _centroid(poly: PackedVector2Array) -> Vector2:
	var c := Vector2.ZERO
	for q in poly:
		c += q
	return c / poly.size()


func _rect_of(poly: PackedVector2Array) -> Rect2:
	var r := Rect2(poly[0], Vector2.ZERO)
	for q in poly:
		r = r.expand(q)
	return r.grow(0.5)


func _box(mb: MeshBuf, c: Vector3, h: Vector3, col: Color) -> void:
	var x := Vector3(h.x, 0, 0)
	var y := Vector3(0, h.y, 0)
	var z := Vector3(0, 0, h.z)
	mb.quad(c + y - x - z, c + y + x - z, c + y + x + z, c + y - x + z, Vector3.UP, col)
	for f in [[x, z, y], [-x, -z, y], [z, -x, y], [-z, x, y]]:
		var nrm: Vector3 = f[0]
		var side: Vector3 = f[1]
		mb.quad(c + nrm - side - y, c + nrm + side - y, c + nrm + side + y, c + nrm - side + y, nrm.normalized(), col * 0.85)


## Gable roof with eaves: ridge along the longer side, overhang all round.
func _gable_roof(mb: MeshBuf, poly: PackedVector2Array, top: float, o: Vector3, col: Color) -> void:
	var p := poly
	if p[0].distance_to(p[1]) > p[1].distance_to(p[2]):
		p = PackedVector2Array([poly[1], poly[2], poly[3], poly[0]])
	# p0-p1 and p2-p3 are the short (gable) sides
	var ov := 0.6
	var ctr := _centroid(p)
	var along := ((p[2] + p[3]) * 0.5 - (p[0] + p[1]) * 0.5).normalized()
	var q := PackedVector2Array()
	for pt in p:
		var d := pt - ctr
		var across := d - along * d.dot(along)
		q.append(pt + along * signf(d.dot(along)) * ov + across.normalized() * ov)
	var span := p[0].distance_to(p[1])
	var rh := clampf(span * 0.38, 1.0, 4.5)            # steep Thai-style pitch
	var drop := ov * rh / (span * 0.5)
	var m1 := (q[0] + q[1]) * 0.5
	var m2 := (q[2] + q[3]) * 0.5
	var R1 := Vector3(m1.x - o.x, top + rh, m1.y - o.z)
	var R2 := Vector3(m2.x - o.x, top + rh, m2.y - o.z)
	var P: Array[Vector3] = []
	for pt in q:
		P.append(Vector3(pt.x - o.x, top - drop, pt.y - o.z))
	for f in [[P[1], P[2], R2, R1], [P[3], P[0], R1, R2]]:
		var nn: Vector3 = (f[1] - f[0]).cross(f[3] - f[0]).normalized()
		if nn.y < 0: nn = -nn
		mb.quad(f[0], f[1], f[2], f[3], nn, col * (0.78 + 0.22 * nn.y))
	# gable triangles (wall colour is unknown here, keep them light)
	var g1 := [Vector3(p[0].x - o.x, top, p[0].y - o.z), Vector3(p[1].x - o.x, top, p[1].y - o.z), Vector3(((p[0] + p[1]) * 0.5).x - o.x, top + rh - drop, ((p[0] + p[1]) * 0.5).y - o.z)]
	var g2 := [Vector3(p[2].x - o.x, top, p[2].y - o.z), Vector3(p[3].x - o.x, top, p[3].y - o.z), Vector3(((p[2] + p[3]) * 0.5).x - o.x, top + rh - drop, ((p[2] + p[3]) * 0.5).y - o.z)]
	for tr in [g1, g2]:
		mb.tri(tr[0], tr[1], tr[2], (tr[1] - tr[0]).cross(tr[2] - tr[0]).normalized(), Color(0.93, 0.91, 0.86))
	# ridge cap
	mb.quad(R1 + Vector3(0, 0.08, 0), R2 + Vector3(0, 0.08, 0), R2 - Vector3(0, 0.05, 0), R1 - Vector3(0, 0.05, 0), Vector3.UP, col * 0.6)


## Hip roof (pyramid-like) for squarish houses.
func _hip_roof(mb: MeshBuf, poly: PackedVector2Array, top: float, o: Vector3, col: Color) -> void:
	var ctr := _centroid(poly)
	var span := minf(poly[0].distance_to(poly[1]), poly[1].distance_to(poly[2]))
	var rh := clampf(span * 0.35, 1.0, 4.0)
	var apex := Vector3(ctr.x - o.x, top + rh, ctr.y - o.z)
	var ov := 0.6
	var P: Array[Vector3] = []
	for pt in poly:
		var d := (pt - ctr)
		var q := pt + d.normalized() * ov * 1.4
		P.append(Vector3(q.x - o.x, top - 0.25, q.y - o.z))
	for k in P.size():
		var a: Vector3 = P[k]
		var b: Vector3 = P[(k + 1) % P.size()]
		var nn := (b - a).cross(apex - a).normalized()
		if nn.y < 0: nn = -nn
		mb.tri(a, b, apex, nn, col * (0.78 + 0.22 * nn.y))


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
