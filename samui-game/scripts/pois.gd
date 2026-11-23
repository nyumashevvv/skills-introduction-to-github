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


func setup() -> void:
	var scene: Node = load("res://models/pois.glb").instantiate()
	for mi in scene.find_children("*", "MeshInstance3D", true, false):
		meshes[String(mi.name)] = mi.mesh
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
