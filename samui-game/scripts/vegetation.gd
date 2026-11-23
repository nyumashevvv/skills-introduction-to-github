class_name Vegetation
extends Node3D
## Streams Koh Samui's vegetation around the player in 150 m cells.
## Three levels: full Blender models near, simple models mid-range,
## canopy blobs far away. Grass tufts in a small ring around the player.
## Which plants grow where comes from the land classes (satellite + OSM).

const CELL := 150.0
const NEAR_R := 330.0       # full models (and shadows)
const MID_R := 1800.0       # simplified models
const FAR_R := 3600.0       # canopy blobs
const GRASS_CELL := 30.0
const GRASS_R := 75.0

var world: World
var density := 1.0          # quality setting
var meshes := {}            # name -> Mesh with wind materials
var _cells := {}            # Vector2i -> {level, nodes}
var _grass := {}            # Vector2i -> MultiMeshInstance3D
var _queue := []
var _focus := Vector3.ZERO
var _scan_t := 1.0

enum { NONE, FAR, MID, NEAR }

# metres to keep from the road edge
const CLEAR := {"TreeJungle": 4.5, "TreeTall": 6.0, "PalmTall": 2.2, "PalmShort": 2.0, "PalmLean": 2.0,
	"Banana": 2.0, "Bush": 1.6, "Bougainvillea": 1.6}

# hi model -> lo model / far model
const LO := {"PalmTall": "PalmLo", "PalmShort": "PalmLo", "PalmLean": "PalmLo", "TreeJungle": "TreeLo", "TreeTall": "TreeLo"}
const FAR_MODEL := {"PalmTall": "FarCanopy", "TreeJungle": "FarCanopy", "TreeTall": "FarCanopy", "PalmShort": "FarCanopy"}

# what grows on each land class: [probability per 7 m spot, [[model, weight], ...]]
var MIX := {
	World.JUNGLE: [0.78, [["TreeJungle", 34], ["TreeTall", 9], ["PalmTall", 26], ["PalmShort", 12], ["Banana", 7], ["Bush", 12]]],
	World.GRASS: [0.42, [["PalmTall", 46], ["PalmShort", 24], ["Banana", 10], ["Bush", 10], ["TreeJungle", 10]]],
	World.URBAN: [0.3, [["PalmTall", 30], ["PalmShort", 18], ["Banana", 18], ["Bougainvillea", 18], ["Bush", 16]]],
	World.SAND: [0.2, [["PalmLean", 70], ["PalmTall", 30]]],
	World.ROCK: [0.06, [["Bush", 100]]],
}


func _ready() -> void:
	var shader: Shader = load("res://shaders/vegetation.gdshader")
	var scene: Node = load("res://models/vegetation.glb").instantiate()
	for mi in scene.find_children("*", "MeshInstance3D", true, false):
		var mesh: ArrayMesh = mi.mesh.duplicate()
		for s in mesh.get_surface_count():
			var src := mesh.surface_get_material(s) as BaseMaterial3D
			var mat := ShaderMaterial.new()
			mat.shader = shader
			if src and src.albedo_texture:
				mat.set_shader_parameter("albedo_tex", src.albedo_texture)
			if src:
				mat.set_shader_parameter("albedo_color", src.albedo_color)
			mat.set_shader_parameter("use_alpha", src != null and src.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED)
			var trunkish := src != null and src.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED
			mat.set_shader_parameter("backlight", 0.0 if trunkish else 0.35)
			mesh.surface_set_material(s, mat)
		meshes[String(mi.name)] = mesh
	scene.free()


func set_focus(p: Vector3) -> void:
	_focus = p


## Builds everything within ~1 km right away (spawn / teleport).
func warm_up(p: Vector3) -> void:
	_focus = p
	_scan()
	var rest := []
	for job in _queue:
		if job[0] == "grass" or _cell_dist(job[1], CELL) < 1000.0:
			if job[0] == "grass":
				_build_grass(job[1])
			else:
				_set_level(job[1], job[2])
		else:
			rest.append(job)
	_queue = rest


func _process(dt: float) -> void:
	_scan_t += dt
	if _scan_t > 0.3:
		_scan_t = 0.0
		_scan()
	var t0 := Time.get_ticks_usec()
	while not _queue.is_empty() and Time.get_ticks_usec() - t0 < 6000:
		var job: Array = _queue.pop_front()
		if job[0] == "grass":
			_build_grass(job[1])
		else:
			_set_level(job[1], job[2])


func _cell_dist(key: Vector2i, size: float) -> float:
	var x0 := key.x * size
	var z0 := key.y * size
	var dx := maxf(0.0, maxf(x0 - _focus.x, _focus.x - x0 - size))
	var dz := maxf(0.0, maxf(z0 - _focus.z, _focus.z - z0 - size))
	return Vector2(dx, dz).length()


func _scan() -> void:
	_queue.clear()
	var jobs := []
	var r := int(ceil(FAR_R / CELL)) + 1
	var c0 := Vector2i(floori(_focus.x / CELL), floori(_focus.z / CELL))
	var wanted := {}
	for dz in range(-r, r + 1):
		for dx in range(-r, r + 1):
			var key := c0 + Vector2i(dx, dz)
			if absf(key.x * CELL) > World.HALF or absf(key.y * CELL) > World.HALF:
				continue
			var d := _cell_dist(key, CELL)
			var lvl := NEAR if d < NEAR_R else (MID if d < MID_R else (FAR if d < FAR_R else NONE))
			if lvl == NONE:
				continue
			wanted[key] = true
			var cur: int = _cells[key]["level"] if _cells.has(key) else NONE
			if cur != lvl:
				jobs.append([d, "cell", key, lvl])
	for key in _cells.keys():
		if not wanted.has(key):
			_free_cell(key)
	# grass
	var gr := int(ceil(GRASS_R / GRASS_CELL)) + 1
	var g0 := Vector2i(floori(_focus.x / GRASS_CELL), floori(_focus.z / GRASS_CELL))
	var gw := {}
	for dz in range(-gr, gr + 1):
		for dx in range(-gr, gr + 1):
			var key := g0 + Vector2i(dx, dz)
			var d := _cell_dist(key, GRASS_CELL)
			if d < GRASS_R:
				gw[key] = true
				if not _grass.has(key):
					jobs.append([d * 0.5, "grass", key])
	for key in _grass.keys():
		if not gw.has(key):
			if _grass[key]:
				_grass[key].queue_free()
			_grass.erase(key)
	jobs.sort_custom(func(a, b): return a[0] < b[0])
	for j in jobs:
		_queue.append(j.slice(1))


func _free_cell(key: Vector2i) -> void:
	if _cells.has(key):
		for n in _cells[key]["nodes"]:
			n.queue_free()
		_cells.erase(key)


# ------------------------------------------------------------ placement
## Deterministic list of plants in a cell: name -> Array of [Transform3D, Color]
func _plants(key: Vector2i) -> Dictionary:
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(key) & 0x7fffffff
	var out := {}
	var step := 7.0 / sqrt(density)
	var n := int(CELL / step)
	var x0 := key.x * CELL
	var z0 := key.y * CELL
	for b in n:
		for a in n:
			var x := x0 + (a + rng.randf()) * step
			var z := z0 + (b + rng.randf()) * step
			var cl := world.class_at(x, z)
			var r1 := rng.randf()
			var r2 := rng.randf()
			var r3 := rng.randf()
			if not MIX.has(cl):
				continue
			var mix: Array = MIX[cl]
			if r1 >= mix[0]:
				continue
			var name := _pick(mix[1], r2)
			# keep clear of roads (trunks off the verge, big crowns further) and houses
			var rd := world.road_dist(x, z)
			if rd < CLEAR.get(name, 2.5):
				continue
			if world.is_blocked(x, z) or world.landmarks.excluded(Vector2(x, z)):
				continue
			var y := world.height_at(x, z)
			if y < 0.5:
				continue
			var s := 0.8 + 0.5 * r3
			if name.begins_with("Tree"):
				s = 0.75 + 0.6 * r3
			var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3(s, s * (0.9 + 0.2 * rng.randf()), s))
			if name == "PalmLean":
				# lean out towards the sea (downhill)
				var gx := world.height_at(x + 6, z) - world.height_at(x - 6, z)
				var gz := world.height_at(x, z + 6) - world.height_at(x, z - 6)
				var down := Vector2(-gx, -gz)
				var yaw := atan2(down.y, down.x) if down.length() > 0.01 else rng.randf() * TAU
				# the model leans along +X; rotate so +X points downhill
				basis = Basis(Vector3.UP, -yaw).scaled(Vector3(s, s, s))
			var tint := Color(1, 1, 1).lerp(Color(1.12, 1.05, 0.72), rng.randf() * 0.5) * (0.85 + 0.25 * rng.randf())
			if not out.has(name):
				out[name] = []
			out[name].append([Transform3D(basis, Vector3(x, y - 0.15, z)), tint])
	return out


func _pick(weights: Array, r: float) -> String:
	var total := 0.0
	for w in weights:
		total += w[1]
	var acc := 0.0
	for w in weights:
		acc += w[1] / total
		if r <= acc:
			return w[0]
	return weights[-1][0]


func _mmi(mesh_name: String, items: Array, vis_begin: float, vis_end: float, shadows: bool, every := 1, scale := 1.0) -> MultiMeshInstance3D:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = meshes[mesh_name]
	var count := int(ceil(items.size() / float(every)))
	mm.instance_count = count
	var buf := PackedFloat32Array()
	buf.resize(count * 16)
	var k := 0
	for i in range(0, items.size(), every):
		var t: Transform3D = items[i][0]
		var c: Color = items[i][1]
		var b := t.basis.scaled(Vector3(scale, scale, scale))
		var o := k * 16
		buf[o] = b.x.x; buf[o + 1] = b.y.x; buf[o + 2] = b.z.x; buf[o + 3] = t.origin.x
		buf[o + 4] = b.x.y; buf[o + 5] = b.y.y; buf[o + 6] = b.z.y; buf[o + 7] = t.origin.y
		buf[o + 8] = b.x.z; buf[o + 9] = b.y.z; buf[o + 10] = b.z.z; buf[o + 11] = t.origin.z
		buf[o + 12] = c.r; buf[o + 13] = c.g; buf[o + 14] = c.b; buf[o + 15] = 1.0
		k += 1
	mm.buffer = buf
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.visibility_range_begin = vis_begin
	mmi.visibility_range_end = vis_end
	mmi.visibility_range_end_margin = 30.0
	mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)
	return mmi


func _set_level(key: Vector2i, lvl: int) -> void:
	_free_cell(key)
	var plants := _plants(key)
	var nodes := []
	for name in plants:
		var items: Array = plants[name]
		match lvl:
			NEAR:
				nodes.append(_mmi(name, items, 0.0, NEAR_R + 120.0, true))
				if LO.has(name):
					nodes.append(_mmi(LO[name], items, NEAR_R + 120.0, MID_R + 200.0, false))
			MID:
				if LO.has(name):
					nodes.append(_mmi(LO[name], items, 0.0, MID_R + 200.0, false))
				elif name == "Banana":
					nodes.append(_mmi("Bush", items, 0.0, 700.0, false, 2))
			FAR:
				if FAR_MODEL.has(name):
					nodes.append(_mmi(FAR_MODEL[name], items, 0.0, FAR_R + 300.0, false, 2, 1.15))
	_cells[key] = {"level": lvl, "nodes": nodes}


func _build_grass(key: Vector2i) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = (hash(key) ^ 0x5bd1e995) & 0x7fffffff
	var items := []
	var step := 1.6
	var n := int(GRASS_CELL / step)
	for b in n:
		for a in n:
			var x := key.x * GRASS_CELL + (a + rng.randf()) * step
			var z := key.y * GRASS_CELL + (b + rng.randf()) * step
			var cl := world.class_at(x, z)
			if cl != World.GRASS and cl != World.JUNGLE and cl != World.URBAN and cl != World.ROAD:
				continue
			if world.road_dist(x, z) < 2.6:
				continue
			if rng.randf() > (0.75 if cl != World.URBAN else 0.3):
				continue
			var s := 0.7 + 0.7 * rng.randf()
			var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3(s, s, s))
			var tint := Color(1, 1, 1) * (0.8 + 0.35 * rng.randf())
			items.append([Transform3D(basis, Vector3(x, world.height_at(x, z) - 0.05, z)), tint])
	if items.is_empty():
		_grass[key] = null
		return
	_grass[key] = _mmi("Grass", items, 0.0, GRASS_R + 20.0, false)
