class_name Landmarks
extends Node3D
## Koh Samui landmarks (Blender models from models/landmarks.glb) placed at
## their OpenStreetMap positions, plus every pier mapped in OSM as a deck you
## can ride onto.

const PIER_Y := 1.7

var world: World
var meshes := {}
var exclusions := []        # [Vector2 centre, radius]: no generated houses or plants here
var blockers := []          # [Vector2 centre, radius]: solid for the scooter
var piers := []             # [Rect2, PackedVector2Array]


func setup() -> void:
	var scene: Node = load("res://models/landmarks.glb").instantiate()
	for mi in scene.find_children("*", "MeshInstance3D", true, false):
		meshes[String(mi.name)] = mi.mesh
	scene.free()
	_place_big_buddha()
	_place_plai_laem()
	_place_rocks()
	_build_piers()


func _place(name: String, pos: Vector3, yaw: float) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = meshes[name]
	mi.position = pos
	mi.rotation.y = yaw
	add_child(mi)


func _place_by_name(en: String) -> Vector2:
	for p in world.places:
		if p["en"] == en:
			return Vector2(p["x"], p["z"])
	return Vector2.INF


## Yaw that turns the model's front (local -Z) towards the nearest road.
func _face_road(at: Vector2) -> float:
	var r := world.nearest_road(at.x, at.y, true)
	if not r.has("pos"):
		r = world.nearest_road(at.x, at.y)
	if not r.has("pos"):
		return 0.0
	var d: Vector2 = r["pos"] - at
	return atan2(-d.x, -d.y)


func _place_big_buddha() -> void:
	var c := _place_by_name("Big Buddha")
	if c == Vector2.INF:
		return
	# the statue sits on the top of Ko Fan islet: highest ground nearby
	var best := c
	var best_h := -INF
	for dz in range(-80, 81, 8):
		for dx in range(-80, 81, 8):
			var hh := world.height_at(c.x + dx, c.y + dz)
			if hh > best_h:
				best_h = hh
				best = c + Vector2(dx, dz)
	var low := INF
	for d in [Vector2(-15, -17), Vector2(15, -17), Vector2(15, 13), Vector2(-15, 13), Vector2.ZERO]:
		low = minf(low, world.height_at(best.x + d.x, best.y + d.y))
	_place("BigBuddha", Vector3(best.x, maxf(low, 0.4) - 0.2, best.y), _face_road(best))
	exclusions.append([best, 26.0])
	blockers.append([best, 10.0])


func _place_plai_laem() -> void:
	var c := _place_by_name("Wat Plai Laem")
	if c == Vector2.INF:
		return
	_place("Guanyin", Vector3(c.x, world.height_at(c.x, c.y) + 0.05, c.y), _face_road(c))
	exclusions.append([c, 30.0])
	blockers.append([c, 9.5])
	var m := c + Vector2(0, -48)
	_place("Maitreya", Vector3(m.x, world.height_at(m.x, m.y), m.y), _face_road(m))
	exclusions.append([m, 8.0])
	blockers.append([m, 4.0])


func _place_rocks() -> void:
	var c := _place_by_name("Hin Ta & Hin Yai (Grandma and Grandpa Rocks)")
	if c == Vector2.INF:
		return
	_place("Rocks", Vector3(c.x, world.height_at(c.x, c.y) - 0.6, c.y), randf() * TAU)
	exclusions.append([c, 12.0])
	blockers.append([c, 7.0])


func excluded(p: Vector2) -> bool:
	for e in exclusions:
		if p.distance_to(e[0]) < e[1]:
			return true
	return false


func blocked(p: Vector2) -> bool:
	for e in blockers:
		if p.distance_to(e[0]) < e[1]:
			return true
	return false


# ------------------------------------------------------------ piers
func _build_piers() -> void:
	var data = JSON.parse_string(FileAccess.get_file_as_string("res://data/piers.json"))
	if data == null:
		return
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var deck_col := Color(0.72, 0.71, 0.68)
	for pr in data:
		var polys := []
		if pr.has("poly"):
			var poly := PackedVector2Array()
			var a: Array = pr["poly"]
			for k in range(0, a.size() - 1, 2):
				poly.append(Vector2(a[k], a[k + 1]))
			polys.append(poly)
		else:
			var a: Array = pr["line"]
			var hw: float = maxf(float(pr.get("w", 4.0)), 3.0) * 0.5
			for k in range(0, a.size() - 3, 2):
				var p0 := Vector2(a[k], a[k + 1])
				var p1 := Vector2(a[k + 2], a[k + 3])
				var d := (p1 - p0).normalized()
				var n := Vector2(-d.y, d.x) * hw
				polys.append(PackedVector2Array([p0 - n - d * hw, p1 - n + d * hw, p1 + n + d * hw, p0 + n - d * hw]))
		for poly in polys:
			if poly.size() < 3:
				continue
			piers.append([_rect(poly), poly])
			var tri := Geometry2D.triangulate_polygon(poly)
			st.set_color(deck_col)
			st.set_normal(Vector3.UP)
			for t in tri:
				st.add_vertex(Vector3(poly[t].x, PIER_Y, poly[t].y))
			# deck edge and piles along the outline
			for k in poly.size():
				var q0: Vector2 = poly[k]
				var q1: Vector2 = poly[(k + 1) % poly.size()]
				var nn := Vector3(q1.y - q0.y, 0, q0.x - q1.x).normalized()
				st.set_color(deck_col * 0.8)
				st.set_normal(nn)
				for v in [Vector3(q0.x, PIER_Y - 0.5, q0.y), Vector3(q1.x, PIER_Y - 0.5, q1.y), Vector3(q1.x, PIER_Y, q1.y),
						Vector3(q0.x, PIER_Y - 0.5, q0.y), Vector3(q1.x, PIER_Y, q1.y), Vector3(q0.x, PIER_Y, q0.y)]:
					st.add_vertex(v)
				var seg := q0.distance_to(q1)
				var steps := int(seg / 6.0)
				for s in steps + 1:
					var pp := q0.lerp(q1, float(s) / maxf(steps, 1)) - Vector2(nn.x, nn.z) * 0.4
					var gy := minf(world.height_at(pp.x, pp.y), 0.0) - 1.0
					_pile(st, Vector3(pp.x, gy, pp.y), PIER_Y - 0.5 - gy)
	var mi := MeshInstance3D.new()
	var m := st.commit()
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.vertex_color_is_srgb = true
	mat.roughness = 0.9
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.surface_set_material(0, mat)
	mi.mesh = m
	add_child(mi)


func _pile(st: SurfaceTool, base: Vector3, h: float) -> void:
	var r := 0.18
	st.set_color(Color(0.55, 0.54, 0.5))
	for k in 4:
		var a0 := Vector3(cos(k * PI / 2) * r, 0, sin(k * PI / 2) * r)
		var a1 := Vector3(cos((k + 1) * PI / 2) * r, 0, sin((k + 1) * PI / 2) * r)
		st.set_normal((a0 + a1).normalized())
		for v in [base + a0, base + a1, base + a1 + Vector3(0, h, 0), base + a0, base + a1 + Vector3(0, h, 0), base + a0 + Vector3(0, h, 0)]:
			st.add_vertex(v)


func _rect(poly: PackedVector2Array) -> Rect2:
	var r := Rect2(poly[0], Vector2.ZERO)
	for q in poly:
		r = r.expand(q)
	return r.grow(0.3)


## Deck height if (x, z) is on a pier, else -INF.
func pier_height(x: float, z: float) -> float:
	var p := Vector2(x, z)
	for pr in piers:
		if pr[0].has_point(p) and Geometry2D.is_point_in_polygon(p, pr[1]):
			return PIER_Y
	return -INF
