class_name Traffic
extends Node3D
## Traffic on the real road network (data/roadgraph.json: OSM ways split at
## junctions). Vehicles keep LEFT as in Thailand, follow one-way streets,
## pick a new road at every junction, slow down behind each other and for the
## player, and are spawned/removed in a ring around the player.

const SPAWN_MIN := 90.0
const SPAWN_MAX := 420.0
const DESPAWN := 520.0
const GRID := 200.0

var world: World
var target_count := 45
var nodes := PackedVector2Array()
var node_edges := []            # node -> Array of edge indices
var edges := []                 # {a, b, k, w, o, pts: PackedVector2Array, cum: PackedFloat32Array, len}
var grid := {}                  # Vector2i -> edge indices (main component only)
var meshes := {}
var cars := []                  # Array of Dictionary
var _spawn_t := 0.0
var _rng := RandomNumberGenerator.new()

const PAINT := [Color(0.92, 0.92, 0.92), Color(0.12, 0.12, 0.13), Color(0.6, 0.62, 0.64), Color(0.75, 0.1, 0.08),
	Color(0.15, 0.3, 0.6), Color(0.85, 0.85, 0.8), Color(0.3, 0.32, 0.3), Color(0.55, 0.05, 0.05)]
const SONGTHAEW := [Color(0.85, 0.15, 0.1), Color(0.1, 0.45, 0.75), Color(0.95, 0.75, 0.1), Color(0.15, 0.55, 0.3), Color(0.95, 0.5, 0.1)]


func setup() -> void:
	_rng.seed = 12345
	var scene: Node = load("res://models/vehicles.glb").instantiate()
	for mi in scene.find_children("*", "MeshInstance3D", true, false):
		meshes[String(mi.name)] = mi.mesh
	scene.free()
	var g = JSON.parse_string(FileAccess.get_file_as_string("res://data/roadgraph.json"))
	for n in g["n"]:
		nodes.append(Vector2(n[0], n[1]))
	node_edges.resize(nodes.size())
	for i in nodes.size():
		node_edges[i] = []
	for e in g["e"]:
		var pts := PackedVector2Array()
		var a: Array = e["p"]
		for k in range(0, a.size() - 1, 2):
			pts.append(Vector2(a[k], a[k + 1]))
		var cum := PackedFloat32Array([0.0])
		for k in range(1, pts.size()):
			cum.append(cum[k - 1] + pts[k].distance_to(pts[k - 1]))
		var idx := edges.size()
		edges.append({"a": int(e["a"]), "b": int(e["b"]), "k": int(e["k"]), "w": float(e["w"]), "o": e.get("o", 0) == 1,
			"pts": pts, "cum": cum, "len": cum[cum.size() - 1]})
		node_edges[int(e["a"])].append(idx)
		node_edges[int(e["b"])].append(idx)
	# spawn only on the largest connected part of the network
	var comp := _largest_component()
	for i in edges.size():
		var e: Dictionary = edges[i]
		if not comp.has(e["a"]) or e["len"] < 15.0:
			continue
		var cells := {}
		for p in e["pts"]:
			cells[Vector2i(floori(p.x / GRID), floori(p.y / GRID))] = true
		for key in cells:
			if not grid.has(key):
				grid[key] = []
			grid[key].append(i)
	print("traffic: %d nodes, %d edges, %d in the main network" % [nodes.size(), edges.size(), comp.size()])


func _largest_component() -> Dictionary:
	var seen := {}
	var best := {}
	for start in nodes.size():
		if seen.has(start) or node_edges[start].is_empty():
			continue
		var comp := {start: true}
		var stack := [start]
		seen[start] = true
		while not stack.is_empty():
			var n: int = stack.pop_back()
			for ei in node_edges[n]:
				for m in [edges[ei]["a"], edges[ei]["b"]]:
					if not seen.has(m):
						seen[m] = true
						comp[m] = true
						stack.append(m)
		if comp.size() > best.size():
			best = comp
	return best


# ------------------------------------------------------------ geometry along an edge
func _at(e: Dictionary, s: float) -> Array:
	var cum: PackedFloat32Array = e["cum"]
	var pts: PackedVector2Array = e["pts"]
	s = clampf(s, 0.0, e["len"])
	var i := cum.bsearch(s)
	i = clampi(i, 1, pts.size() - 1)
	var seg := cum[i] - cum[i - 1]
	var f := (s - cum[i - 1]) / maxf(seg, 0.001)
	return [pts[i - 1].lerp(pts[i], f), (pts[i] - pts[i - 1]).normalized()]


# ------------------------------------------------------------ spawning
func _kind_pick(k: int) -> String:
	var r := _rng.randf()
	if k == 0:
		return "ScooterNPC" if r < 0.45 else ("Sedan" if r < 0.7 else ("Pickup" if r < 0.85 else "Songthaew"))
	return "ScooterNPC" if r < 0.72 else ("Sedan" if r < 0.9 else "Pickup")


func _spawn(focus: Vector3) -> void:
	var c0 := Vector2i(floori(focus.x / GRID), floori(focus.z / GRID))
	var cand := []
	var demo := OS.get_cmdline_user_args().has("--traffic-demo") and cars.size() < 6
	for dz in range(-2, 3):
		for dx in range(-2, 3):
			if demo and (dx != 0 or dz != 0):
				continue
			cand.append_array(grid.get(c0 + Vector2i(dx, dz), []))
	if cand.is_empty():
		return
	for attempt in (200 if demo else 6):
		var ei: int = cand[_rng.randi() % cand.size()]
		var e: Dictionary = edges[ei]
		var s: float = _rng.randf() * e["len"]
		var p: Vector2 = _at(e, s)[0]
		var d := p.distance_to(Vector2(focus.x, focus.z))
		# fill the streets near the player when traffic is thin (start, teleport), else spawn out of sight
		var dmin := 30.0 if cars.size() < target_count / 2 else SPAWN_MIN
		if demo:
			dmin = 12.0
		if d < dmin or d > (60.0 if demo else SPAWN_MAX):
			continue
		var dir := 1 if (e["o"] or _rng.randf() < 0.5) else -1
		var type := _kind_pick(e["k"])
		var mi := MeshInstance3D.new()
		mi.mesh = meshes[type]
		var paint: Color = SONGTHAEW[_rng.randi() % SONGTHAEW.size()] if type == "Songthaew" else PAINT[_rng.randi() % PAINT.size()]
		for si in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(si)
			if m and m.resource_name == "Paint":
				var pm: BaseMaterial3D = m.duplicate()
				pm.albedo_color = paint
				mi.set_surface_override_material(si, pm)
		add_child(mi)
		var cruise := (_rng.randf_range(12.0, 16.0) if e["k"] == 0 else _rng.randf_range(6.5, 9.5))
		if type == "ScooterNPC":
			cruise *= 0.9
		cars.append({"mi": mi, "e": ei, "dir": dir, "s": s, "v": cruise * 0.6, "cruise": cruise,
			"type": type, "len": 2.0 if type == "ScooterNPC" else 4.8, "pos": Vector3(p.x, 0, p.y), "fwd": Vector3.FORWARD})
		return


# ------------------------------------------------------------ per frame
func update(dt: float, player: Scooter) -> void:
	var focus := player.position
	_spawn_t -= dt
	if _spawn_t <= 0.0:
		_spawn_t = 0.15
		for k in (8 if cars.size() < target_count / 2 else 1):
			if cars.size() < target_count:
				_spawn(focus)
	var pp := Vector2(focus.x, focus.z)
	var pfwd := Vector2(player.forward().x, player.forward().z)
	for i in range(cars.size() - 1, -1, -1):
		var c: Dictionary = cars[i]
		if Vector2(c["pos"].x, c["pos"].z).distance_to(pp) > DESPAWN:
			c["mi"].queue_free()
			cars.remove_at(i)
			continue
		_drive(c, dt, player, pp)


func _drive(c: Dictionary, dt: float, player: Scooter, pp: Vector2) -> void:
	var e: Dictionary = edges[c["e"]]
	var dir: int = c["dir"]
	var me := Vector2(c["pos"].x, c["pos"].z)
	var fwd2 := Vector2(c["fwd"].x, c["fwd"].z)
	# obstacles ahead: other vehicles in the same direction, and the player
	var gap := INF
	for o in cars:
		if o == c:
			continue
		var d: Vector2 = Vector2(o["pos"].x, o["pos"].z) - me
		var ahead := d.dot(fwd2)
		if ahead > 0.0 and ahead < 25.0 and absf(d.cross(fwd2)) < 2.0 and Vector2(o["fwd"].x, o["fwd"].z).dot(fwd2) > 0.3:
			gap = minf(gap, ahead - (o["len"] + c["len"]) * 0.5)
	var dp := pp - me
	var pa := dp.dot(fwd2)
	if pa > 0.0 and pa < 25.0 and absf(dp.cross(fwd2)) < 2.2:
		gap = minf(gap, pa - 2.5)
	var want: float = c["cruise"]
	if gap < 20.0:
		want = minf(want, maxf(0.0, (gap - 3.0) * 0.8))
	# slow down for sharp bends near the end of the edge
	c["v"] = move_toward(c["v"], want, (6.0 if want < c["v"] else 2.5) * dt)
	c["s"] += c["v"] * dt * dir
	if (dir > 0 and c["s"] > e["len"]) or (dir < 0 and c["s"] < 0.0):
		var over: float = (c["s"] - e["len"]) if dir > 0 else -c["s"]
		var node: int = e["b"] if dir > 0 else e["a"]
		_next_edge(c, node, over)
		e = edges[c["e"]]
		dir = c["dir"]
	var at := _at(e, c["s"])
	var p: Vector2 = at[0]
	var t: Vector2 = at[1] * dir
	var lane: float = 0.0 if e["o"] else e["w"] * 0.25
	if c["type"] == "ScooterNPC":
		lane = e["w"] * 0.32       # scooters ride near the left edge of their lane
	var left := Vector2(t.y, -t.x)      # keep left (Thailand)
	p += left * lane
	var y := world.height_at(p.x, p.y) + 0.08
	var pos := Vector3(p.x, y, p.y)
	var newf := Vector3(t.x, 0, t.y)
	c["fwd"] = c["fwd"].lerp(newf, clampf(dt * 8.0, 0.0, 1.0)).normalized()
	c["pos"] = pos
	var mi: MeshInstance3D = c["mi"]
	mi.position = pos
	mi.rotation = Vector3(0, atan2(-c["fwd"].x, -c["fwd"].z), 0)
	# collision with the player
	var dd := Vector2(pos.x, pos.z).distance_to(pp)
	if dd < (1.0 if c["type"] == "ScooterNPC" else 2.0):
		player.hit_by(newf * c["v"])
		c["v"] = 0.0


func _next_edge(c: Dictionary, node: int, over: float) -> void:
	var options := []
	var weights := []
	var cur: int = c["e"]
	for ei in node_edges[node]:
		var e: Dictionary = edges[ei]
		if ei == cur and node_edges[node].size() > 1:
			continue
		var forward: bool = e["a"] == node
		if e["o"] and not forward:
			continue                         # wrong way down a one-way street
		options.append([ei, 1 if forward else -1])
		weights.append(3.0 if e["k"] == 0 else 1.0)
	if options.is_empty():                   # dead end: turn around
		var e0: Dictionary = edges[cur]
		if e0["o"]:
			c["s"] = 0.0 if c["dir"] > 0 else e0["len"]
			return
		c["dir"] = -c["dir"]
		c["s"] = e0["len"] - over if c["dir"] < 0 else over
		c["v"] *= 0.3
		return
	var total := 0.0
	for w in weights:
		total += w
	var r := _rng.randf() * total
	var pick: Array = options[0]
	for k in options.size():
		r -= weights[k]
		if r <= 0.0:
			pick = options[k]
			break
	var ne: Dictionary = edges[pick[0]]
	c["e"] = pick[0]
	c["dir"] = pick[1]
	c["s"] = over if pick[1] > 0 else ne["len"] - over
	c["v"] *= 0.8                            # ease off through the junction


func clear() -> void:
	for c in cars:
		c["mi"].queue_free()
	cars.clear()
