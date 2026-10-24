extends Node
## Looks for holes in every chapter: from each walkable spot that the start can reach, steps 1.3 m out in 12
## directions; where there is no walkable ground and no wall in the way, casts a ray down. Nothing below = a hole
## to fall out of the map (a failure); a drop over 6 m is reported too.
##   godot --headless --path . res://tests/test_holes.tscn

const STEP := 1.5
const FLOORS := {"Mall": [0.0, 5.0, 10.0, 15.0]}

var failures := 0


func _ready() -> void:
	_run.call_deferred()


func walkable(map: RID, p: Vector3) -> bool:
	var c := NavigationServer3D.map_get_closest_point(map, p)
	return Vector2(c.x - p.x, c.z - p.z).length() < 0.35 and absf(c.y - p.y) < 0.8


func _run() -> void:
	for path: String in Game.LEVELS:
		await _check(path)
	print("FAILURES: %d" % failures)
	get_tree().quit(failures)


func _check(path: String) -> void:
	var level := (load(path) as PackedScene).instantiate() as Level
	get_tree().root.add_child(level)
	get_tree().current_scene = level
	await get_tree().physics_frame
	level.start_playing()
	var map := level.get_world_3d().navigation_map
	for i in 3000:
		if not level.nav_region.is_baking() and NavigationServer3D.map_get_iteration_id(map) > 0:
			break
		await get_tree().physics_frame
	for i in 10:
		await get_tree().physics_frame
	var space := level.get_world_3d().direct_space_state
	var start := NavigationServer3D.map_get_closest_point(map, level.player.global_position)
	var bounds := AABB()
	for node in level.nav_region.get_children():
		if node is Node3D:
			bounds = bounds.merge(AABB((node as Node3D).global_position, Vector3.ONE))
	var holes := 0
	var drops := {}
	for y: float in FLOORS.get(level.name, [0.0]):
		var x := bounds.position.x
		while x <= bounds.end.x:
			var z := bounds.position.z
			while z <= bounds.end.z:
				var s := Vector3(x, y, z)
				z += STEP
				if not walkable(map, s):
					continue
				var c := NavigationServer3D.map_get_closest_point(map, s)
				var reached := false
				for k in 12:
					var q := c + Vector3(cos(k * TAU / 12), 0, sin(k * TAU / 12)) * 1.3
					if walkable(map, q):
						continue
					if not space.intersect_ray(PhysicsRayQueryParameters3D.create(c + Vector3.UP * 0.05, q + Vector3.UP * 0.05, 1)).is_empty():
						continue
					if not reached:
						var route := NavigationServer3D.map_get_path(map, start, c, true)
						if route.size() == 0 or (route[route.size() - 1] as Vector3).distance_to(c) > 1.0:
							break  # cannot get there (the top of a wall and such)
						reached = true
					var down := _down(space, q)
					if down.is_empty():
						holes += 1
						if holes <= 10:
							print("  hole at ", q.snapped(Vector3(0.1, 0.1, 0.1)))
					elif c.y - (down.position as Vector3).y > 6.0:
						drops["%.0f m at (%.0f, %.0f, %.0f)" % [c.y - (down.position as Vector3).y, snappedf(q.x, 5), c.y, snappedf(q.z, 5)]] = true
			x += STEP
	print(("PASS  " if holes == 0 else "FAIL  ") + "%s: %d holes" % [level.name, holes])
	if holes > 0:
		failures += 1
	for d: String in drops:
		print("  drop " + d)
	level.queue_free()
	await get_tree().process_frame


## The first floor below `q`, probed at four points round it: a ray exactly on the seam between two boxes can slip
## through where no player capsule could.
func _down(space: PhysicsDirectSpaceState3D, q: Vector3) -> Dictionary:
	var best := {}
	for o: Vector3 in [Vector3(0.1, 0, 0.1), Vector3(-0.1, 0, 0.1), Vector3(0.1, 0, -0.1), Vector3(-0.1, 0, -0.1)]:
		var hit := space.intersect_ray(PhysicsRayQueryParameters3D.create(q + o + Vector3.UP * 0.05, q + o + Vector3.DOWN * 100, 1))
		if not hit.is_empty() and (best.is_empty() or (hit.position as Vector3).y > (best.position as Vector3).y):
			best = hit
	return best
