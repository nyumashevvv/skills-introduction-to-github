class_name Beach
extends Node3D
## Sea and beach life (models/beach.glb, spots from data/beach.json):
## sunbeds with umbrellas in front of beach resorts, longtail boats bobbing
## off the beaches, ferries moored at the long piers, and waterfalls with
## falling water at every OSM waterfall.

const CELL := 300.0

var world: World
var meshes := {}
var _boats := []                # [MeshInstance3D, base y, phase]
var stats := {}


func setup() -> void:
	var scene: Node = load("res://models/beach.glb").instantiate()
	for mi in scene.find_children("*", "MeshInstance3D", true, false):
		meshes[String(mi.name)] = mi.mesh
	scene.free()
	var d = JSON.parse_string(FileAccess.get_file_as_string("res://data/beach.json"))
	_place_sunbeds(d["rows"])
	_place_boats(d["boats"])
	_place_ferries()
	_place_waterfalls()
	print("beach placed: ", stats)


func _count(k: String, n := 1) -> void:
	stats[k] = stats.get(k, 0) + n


func _ok_sand(p: Vector2) -> bool:
	var cl := world.class_at(p.x, p.y)
	return (cl == World.SAND or cl == World.GRASS) and world.height_at(p.x, p.y) > 0.45 \
		and world.road_dist(p.x, p.y) > 1.5 and not world.is_blocked(p.x, p.y)


func _place_sunbeds(rows: Array) -> void:
	var groups := {}    # cell -> {mesh name -> Array of Transform3D}
	for r in rows:
		var c := Vector2(r[0], r[1])
		var sea := Vector2(r[2], r[3]).normalized()
		var along := Vector2(-sea.y, sea.x)
		var pairs: int = r[4]
		var thatch: bool = r[5] == 1
		var yaw := atan2(sea.x, sea.y)          # model +Z (foot end) towards the water
		var key := Vector2i(floori(c.x / CELL), floori(c.y / CELL))
		if not groups.has(key):
			groups[key] = {}
		var g: Dictionary = groups[key]
		for k in pairs:
			var base := c + along * (k - (pairs - 1) * 0.5) * 3.4
			for side in [-0.55, 0.55]:
				var p: Vector2 = base + along * side
				if not _ok_sand(p):
					continue
				_add(g, "Sunbed", Transform3D(Basis(Vector3.UP, yaw), Vector3(p.x, world.height_at(p.x, p.y), p.y)))
				_count("sunbed")
			var up := base + sea * 0.9
			if _ok_sand(up):
				_add(g, "UmbrellaThatch" if thatch else "Umbrella", Transform3D(Basis(Vector3.UP, yaw), Vector3(up.x, world.height_at(up.x, up.y) - 0.1, up.y)))
				_count("umbrella")
	for key in groups:
		for name in groups[key]:
			_mm(name, groups[key][name], 600.0)


func _add(g: Dictionary, name: String, t: Transform3D) -> void:
	if not g.has(name):
		g[name] = []
	g[name].append(t)


func _mm(name: String, xf: Array, vis: float) -> void:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = meshes[name]
	mm.instance_count = xf.size()
	for i in xf.size():
		mm.set_instance_transform(i, xf[i])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.visibility_range_end = vis
	add_child(mmi)


func _place_boats(spots: Array) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 77
	for b in spots:
		var p := Vector2(b[0], b[1])
		var out := Vector2(b[2], b[3])
		if world.height_at(p.x, p.y) > -0.4:
			continue
		var yaw := atan2(out.x, out.y) + rng.randf_range(-0.4, 0.4)   # bow points at the beach
		var mi := MeshInstance3D.new()
		mi.mesh = meshes["Longtail"]
		mi.position = Vector3(p.x, 0.0, p.y)
		mi.rotation.y = yaw
		mi.visibility_range_end = 1600.0
		add_child(mi)
		_boats.append([mi, 0.0, rng.randf() * TAU])
		_count("longtail boat")


func _place_ferries() -> void:
	for pr in world.landmarks.piers:
		var poly: PackedVector2Array = pr[1]
		if poly.size() != 4:
			continue
		var a := (poly[0] + poly[3]) * 0.5
		var b := (poly[1] + poly[2]) * 0.5
		if a.distance_to(b) < 60.0:
			continue
		# the seaward end is the deeper one
		var end := b if world.height_at(b.x, b.y) < world.height_at(a.x, a.y) else a
		var other := a if end == b else b
		if world.height_at(end.x, end.y) > -1.5:
			continue
		var dir := (end - other).normalized()
		var side := Vector2(-dir.y, dir.x)
		for s in [1.0, -1.0]:
			var c: Vector2 = end - dir * 14.0 + side * s * 7.5
			if world.height_at(c.x, c.y) < -1.5 and world.height_at((c + dir * 16.0).x, (c + dir * 16.0).y) < -1.0:
				var mi := MeshInstance3D.new()
				mi.mesh = meshes["Ferry"]
				mi.position = Vector3(c.x, -0.4, c.y)
				mi.rotation.y = atan2(-dir.x, -dir.y)
				mi.visibility_range_end = 5000.0
				add_child(mi)
				world.landmarks.blockers.append([c, 4.0])
				world.landmarks.blockers.append([c + dir * 10.0, 4.0])
				world.landmarks.blockers.append([c - dir * 10.0, 4.0])
				_count("ferry")
				break


func _place_waterfalls() -> void:
	var wmat := ShaderMaterial.new()
	wmat.shader = load("res://shaders/waterfall.gdshader")
	var nt := NoiseTexture2D.new()
	nt.seamless = true
	var fn := FastNoiseLite.new()
	fn.frequency = 0.04
	nt.noise = fn
	wmat.set_shader_parameter("noise", nt)
	for p in world.pois.all:
		if p["t"] != "waterfall":
			continue
		var at := Vector2(p["x"], p["z"])
		var gx := world.height_at(at.x + 10, at.y) - world.height_at(at.x - 10, at.y)
		var gz := world.height_at(at.x, at.y + 10) - world.height_at(at.x, at.y - 10)
		var down := Vector2(-gx, -gz)
		if down.length() < 0.05:
			down = Vector2(0, 1)
		down = down.normalized()
		var yaw := atan2(-down.x, -down.y)          # model -Z (pool side) faces downhill
		var y := world.height_at(at.x, at.y) - 0.5
		for name in ["WaterfallRocks", "WaterfallWater"]:
			var mi := MeshInstance3D.new()
			mi.mesh = meshes[name]
			mi.position = Vector3(at.x, y, at.y)
			mi.rotation.y = yaw
			mi.visibility_range_end = 1500.0
			if name == "WaterfallWater":
				mi.material_override = wmat
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			add_child(mi)
		world.landmarks.exclusions.append([at - down * 6.0, 22.0])
		world.landmarks.blockers.append([at - down * 2.0, 7.0])
		_count("waterfall")


func _process(_dt: float) -> void:
	var t := Time.get_ticks_msec() / 1000.0
	for b in _boats:
		var mi: MeshInstance3D = b[0]
		mi.position.y = sin(t * 0.9 + b[2]) * 0.08
		mi.rotation.z = sin(t * 0.7 + b[2] * 1.3) * 0.04
