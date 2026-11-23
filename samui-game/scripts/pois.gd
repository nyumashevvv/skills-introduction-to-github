class_name Pois
extends Node3D
## Gameplay places from OpenStreetMap (data/pois.json): fuel stations and
## 24-hour mini-marts at their real positions, plus roadside bottle-fuel stands
## in villages. Models are unbranded (models/pois.glb).
## Every site is checked before it is placed: next to a road, on land, on the
## side of the road with room, and the generated houses/plants are cleared there.

const STATION_PRICE := 38.0     # THB per litre
const BOTTLE_PRICE := 45.0

var world: World
var meshes := {}
var all := []                   # raw POIs from the data file (all kinds)
var fuel_spots := []            # [Vector2 position, radius, price, name]
var shops := []                 # [Vector2 position, name] for the map
var shop_grid := {}             # Vector2i(40 m cell) -> Array of Vector2: shops inside mapped buildings
var stats := {}
var _signs := []                # sign materials that light up at night


func setup() -> void:
	var scene: Node = load("res://models/pois.glb").instantiate()
	for mi in scene.find_children("*", "MeshInstance3D", true, false):
		var mesh: Mesh = mi.mesh.duplicate()
		for k in mesh.get_surface_count():
			var mat := mesh.surface_get_material(k)
			if mat and mat.resource_name in ["Light", "Bulb"]:
				mesh.surface_set_material(k, Props.night_light_mat(Color(1, 0.95, 0.85) if mat.resource_name == "Light" else Color(1.0, 0.75, 0.35), 8.0))
			elif mat and mat.resource_name in ["BandTeal", "BandOrange", "Text"] and mat is BaseMaterial3D:
				var m2: BaseMaterial3D = mat.duplicate()
				m2.emission_enabled = true
				m2.emission = m2.albedo_color
				m2.emission_energy_multiplier = 0.0
				mesh.surface_set_material(k, m2)
				_signs.append(m2)
		meshes[String(mi.name)] = mesh
	scene.free()
	all = JSON.parse_string(FileAccess.get_file_as_string("res://data/pois.json"))
	for p in all:
		var at := Vector2(p["x"], p["z"])
		match p["t"]:
			"fuel":
				_place_station(at, p.get("n", ""))
			"shop":
				if p.get("b", 0) == 1:
					var key := Vector2i(floori(at.x / 40.0), floori(at.y / 40.0))
					if not shop_grid.has(key):
						shop_grid[key] = []
					shop_grid[key].append(at)
					shops.append([at, p.get("n", "")])
					_count("shop in a mapped building")
				else:
					_place_minimart(at, p.get("n", ""))
	_place_bottle_stands()
	for p in all:
		if p["t"] == "market":
			_place_market(Vector2(p["x"], p["z"]), float(p.get("r", 15.0)))
	print("pois placed: ", stats)


func _count(k: String) -> void:
	stats[k] = stats.get(k, 0) + 1


## Finds where a roadside site goes: [front point at the road edge, outward normal] or [] if no room.
## Faces the nearest main road when there is one within 60 m (side lanes and the
## site's own driveway may run under it); the site centre must be off the road and
## the whole site on land. Tries shifting along the road when the first spot is taken.
func _site(at: Vector2, depth: float, half_w: float, prefer_main := true) -> Array:
	var r := world.nearest_road(at.x, at.y, true) if prefer_main else {}
	if not r.has("pos") or Vector2(r["pos"]).distance_to(at) > 60.0:
		r = world.nearest_road(at.x, at.y)
	if not r.has("pos") or Vector2(r["pos"]).distance_to(at) > 90.0:
		return []
	var rp0: Vector2 = r["pos"]
	var dir: Vector2 = r["dir"]
	var n := Vector2(-dir.y, dir.x)
	var sides := [n, -n]
	if (at - rp0).dot(n) < 0.0:
		sides = [-n, n]
	for shift in [0.0, 6.0, -6.0, 12.0, -12.0]:
		var rp: Vector2 = rp0 + dir * shift
		for side in sides:
			var edge: Vector2 = rp
			for i in 40:
				if world.road_dist(edge.x, edge.y) > 1.2:
					break
				edge += side * 0.5
			var front: Vector2 = edge + side * 0.8
			var centre: Vector2 = front + side * depth * 0.5
			var ok := world.road_dist(centre.x, centre.y) > 1.0
			for probe in [centre, front + side * depth, centre + dir * half_w, centre - dir * half_w, front]:
				if world.height_at(probe.x, probe.y) < 0.4:
					ok = false
			if ok:
				return [front, side]
	return []


func _put(mesh_name: String, front: Vector2, side: Vector2, vis := 900.0) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = meshes[mesh_name]
	var y := INF
	for d in [0.0, 4.0, 8.0]:
		y = minf(y, world.height_at(front.x + side.x * d, front.y + side.y * d))
	mi.position = Vector3(front.x, y, front.y)
	mi.rotation.y = atan2(side.x, side.y)   # model front (-Z) faces the road
	mi.visibility_range_end = vis
	add_child(mi)


func _place_station(at: Vector2, name: String) -> void:
	var s := _site(at, 18.0, 13.0)
	if s.is_empty():
		_count("fuel skipped (no roadside room)")
		return
	var front: Vector2 = s[0]
	var side: Vector2 = s[1]
	_put("FuelStation", front, side, 1500.0)
	var centre := front + side * 9.0
	world.landmarks.exclusions.append([centre, 15.0])
	var gy := world.height_at(centre.x, centre.y)
	world.extra_lights.append([Vector3(centre.x, gy + 4.6, centre.y), Color(0.95, 0.97, 1.0), 22.0])
	fuel_spots.append([front + side * 8.5, 9.0, STATION_PRICE, name if name != "" else "Заправка"])
	_count("fuel station")
	var moved := at.distance_to(centre)
	if moved > 35.0:
		_count("fuel moved > 35 m from OSM point")
	if OS.get_cmdline_user_args().has("--poi-report"):
		print("station %s osm %s placed %s moved %.0f m" % [name, at, centre, moved])


func _place_minimart(at: Vector2, name: String) -> void:
	var s := _site(at, 10.0, 5.5)
	if s.is_empty():
		_count("shop skipped (no roadside room)")
		return
	var front: Vector2 = s[0]
	var side: Vector2 = s[1]
	_put("MiniMart", front, side)
	var centre := front + side * 5.5
	world.landmarks.exclusions.append([centre, 7.5])
	world.extra_lights.append([Vector3(front.x, world.height_at(front.x, front.y) + 2.8, front.y), Color(0.92, 0.97, 1.0), 12.0])
	world.landmarks.blockers.append([centre + side * 0.5, 4.2])
	shops.append([centre, name])
	_count("mini-mart model")
	if OS.get_cmdline_user_args().has("--poi-report") and stats["mini-mart model"] <= 3:
		print("minimart at ", centre)


## One bottle-fuel stand on some longer village roads, at least 600 m apart.
func _place_bottle_stands() -> void:
	var placed := []
	for c in world.roads_data.size():
		for r in world.roads_data[c]:
			if r["k"] != 1 or r.get("m", 0) == 2:
				continue
			var p: Array = r["p"]
			var cnt := p.size() / 2
			if cnt < 12:
				continue
			var mid := cnt / 2
			var at := Vector2(p[mid * 2], p[mid * 2 + 1])
			if hash(at) % 7 != 0:
				continue
			var cl := world.class_at(at.x, at.y)
			if cl != World.URBAN and cl != World.GRASS and cl != World.ROAD:
				continue
			var near := false
			for q in placed:
				if q.distance_to(at) < 600.0:
					near = true
					break
			if near:
				continue
			var s := _site(at + Vector2(0.01, 0.01), 2.0, 1.5, false)
			if s.is_empty() or world.is_blocked(s[0].x + s[1].x, s[0].y + s[1].y):
				continue
			_put("BottleStand", s[0], s[1], 300.0)
			fuel_spots.append([s[0] + s[1] * 0.6, 3.5, BOTTLE_PRICE, "Бензин в бутылках"])
			placed.append(at)
			_count("bottle stand")
			if OS.get_cmdline_user_args().has("--poi-report") and stats["bottle stand"] <= 3:
				print("bottle stand at ", s[0])


## Shop facade flag for a building footprint: true if an OSM shop lies inside.
func shop_inside(poly: PackedVector2Array, rect: Rect2) -> bool:
	for gx in range(floori(rect.position.x / 40.0), floori(rect.end.x / 40.0) + 1):
		for gz in range(floori(rect.position.y / 40.0), floori(rect.end.y / 40.0) + 1):
			for q in shop_grid.get(Vector2i(gx, gz), []):
				if rect.has_point(q) and Geometry2D.is_point_in_polygon(q, poly):
					return true
	return false


## [spot, distance] of the nearest place to buy fuel.
func nearest_fuel(p: Vector2) -> Array:
	var best := []
	var bd := INF
	for f in fuel_spots:
		var d: float = p.distance_to(f[0])
		if d < bd:
			bd = d
			best = f
	return [best, bd]



func _process(_dt: float) -> void:
	var night: float = DayNight.night_now
	for m in _signs:
		m.emission_energy_multiplier = 1.6 * night



## Night market at an OSM marketplace: rows of stalls with coloured awnings
## and strings of bulbs. Stalls go only where there is free ground.
func _place_market(at: Vector2, radius: float) -> void:
	var stall_mesh := _stall_mesh()
	var xf := []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(at)
	var r := clampf(radius, 10.0, 35.0)
	var tries := 0
	while xf.size() < int(r * 0.9) and tries < 400:
		tries += 1
		var q := at + Vector2(rng.randf_range(-r, r), rng.randf_range(-r, r))
		if q.distance_to(at) > r or world.road_dist(q.x, q.y) < 1.0 or world.is_blocked(q.x, q.y) or world.height_at(q.x, q.y) < 0.4:
			continue
		var clash := false
		for t in xf:
			if Vector2(t.origin.x, t.origin.z).distance_to(q) < 3.4:
				clash = true
				break
		if clash:
			continue
		var yaw: float = round(rng.randf() * 4.0) * PI * 0.5
		xf.append(Transform3D(Basis(Vector3.UP, yaw), Vector3(q.x, world.height_at(q.x, q.y), q.y)))
	if xf.size() < 3:
		_count("market skipped (no free ground)")
		return
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.mesh = stall_mesh
	mm.instance_count = xf.size()
	var awn := [Color(0.85, 0.2, 0.15), Color(0.15, 0.4, 0.75), Color(0.95, 0.75, 0.15), Color(0.2, 0.6, 0.3), Color(0.9, 0.9, 0.88)]
	for i in xf.size():
		mm.set_instance_transform(i, xf[i])
		mm.set_instance_color(i, awn[rng.randi() % awn.size()])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.visibility_range_end = 700.0
	add_child(mmi)
	var c3 := Vector3(at.x, world.height_at(at.x, at.y) + 3.0, at.y)
	world.extra_lights.append([c3, Color(1.0, 0.7, 0.4), r + 10.0])
	_count("night market")


var _stall: ArrayMesh
func _stall_mesh() -> ArrayMesh:
	if _stall:
		return _stall
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	st.set_color(Color(0.55, 0.42, 0.3))
	Props._box(st, Vector3(0, 0.45, 0), Vector3(1.2, 0.45, 0.6))          # counter
	st.set_color(Color(0.85, 0.85, 0.85))
	for x in [-1.15, 1.15]:
		for z in [-0.55, 0.55]:
			Props._box(st, Vector3(x, 1.2, z), Vector3(0.03, 1.2, 0.03))    # poles
	st.set_color(Color(0.9, 0.5, 0.2))
	for i in 6:                                                          # goods
		Props._box(st, Vector3(-0.9 + i * 0.36, 0.98, 0.1), Vector3(0.13, 0.08, 0.2))
	var m := st.commit()
	var mat := Props._vc_mat()
	m.surface_set_material(0, mat)
	var aw := SurfaceTool.new()   # awning tinted per stall (instance colour)
	aw.begin(Mesh.PRIMITIVE_TRIANGLES)
	aw.set_color(Color(1, 1, 1))
	Props._box(aw, Vector3(0, 2.45, 0), Vector3(1.35, 0.05, 0.85))
	aw.commit(m)
	var am := StandardMaterial3D.new()
	am.vertex_color_use_as_albedo = true
	am.roughness = 0.7
	m.surface_set_material(1, am)
	var bulbs := SurfaceTool.new()
	bulbs.begin(Mesh.PRIMITIVE_TRIANGLES)
	bulbs.set_color(Color(1, 1, 1))
	for i in 7:
		Props._box(bulbs, Vector3(-1.2 + i * 0.4, 2.3 - 0.08 * sin(i * 0.45), 0.85), Vector3(0.05, 0.05, 0.05))
	bulbs.commit(m)
	m.surface_set_material(2, Props.night_light_mat(Color(1.0, 0.75, 0.35), 10.0))
	_stall = m
	return m
