extends Node
## Plays through all three chapters by teleporting the player and checks every story beat.
##   godot --headless --path . res://tests/test_story.tscn

var failures := 0


func check(cond: bool, what: String) -> void:
	print(("PASS  " if cond else "FAIL  ") + what)
	if not cond:
		failures += 1


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func wait_scene(scene_name: String) -> Level:
	for i in 600:
		await get_tree().process_frame
		if get_tree().current_scene != null and get_tree().current_scene.name == scene_name and get_tree().current_scene.is_node_ready():
			break
	await frames(5)
	return get_tree().current_scene as Level


func start(level: Level) -> void:
	level.start_playing()
	for i in 600:
		if not level.nav_region.is_baking():
			break
		await get_tree().physics_frame
	await frames(10)
	var player := level.player
	player.max_health = 100000
	player.health = 100000


func check_paths(level: Level, targets: Dictionary) -> void:
	var map := level.get_world_3d().navigation_map
	var from := NavigationServer3D.map_get_closest_point(map, level.player.global_position)
	for label: String in targets:
		var target: Vector3 = targets[label]
		var path := NavigationServer3D.map_get_path(map, from, target, true)
		var end: Vector3 = path[path.size() - 1] if path.size() > 0 else from
		var ok := Vector2(end.x - target.x, end.z - target.z).length() < 1.5
		check(ok, "%s: reachable %s (path ends %s)" % [level.name, label, end])


func teleport(level: Level, pos: Vector3) -> void:
	level.player.global_position = pos
	level.player.velocity = Vector3.ZERO
	await frames(15)


func node_pos(level: Level, path: String) -> Vector3:
	return (level.get_node(path) as Node3D).global_position


func kill_all(level: Level) -> void:
	for z in get_tree().get_nodes_in_group("zombies"):
		var zombie := z as Zombie
		if zombie.state != Zombie.State.DEAD:
			zombie.take_damage(99999, Vector3.FORWARD, zombie.global_position)
	await frames(3)


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_run.call_deferred()


func _run() -> void:
	# Keep this node alive across scene changes: hand "current scene" to a placeholder.
	var placeholder := Node.new()
	get_tree().root.add_child(placeholder)
	get_tree().current_scene = placeholder
	Game.new_game()
	# ---------------------------------------------------------------- chapter 1
	var level := await wait_scene("Outskirts")
	check(level != null, "chapter 1 loaded")
	check(get_tree().paused and level.hud.intro_screen.visible, "chapter 1 intro card")
	await start(level)
	var p := level.player
	check(p.holder.current != null and p.holder.current.id == "pistol", "starts with pistol")
	check(p.holder.get_weapon("knife").owned and not p.holder.get_weapon("rifle").owned, "knife owned, rifle not yet")
	check_paths(level, {
		"rifle": node_pos(level, "Pickups/WeaponRifle1"),
		"alley ammo": node_pos(level, "Pickups/AmmoRifle1"),
		"station door": Vector3(0, 0, -128.5),
	})
	await frames(30)
	check(level.hud.subtitle_label.text.contains("стадион"), "intro radio: " + level.hud.subtitle_label.text.left(60))
	await teleport(level, node_pos(level, "Pickups/WeaponRifle1"))
	check(p.holder.get_weapon("rifle").owned and p.holder.current.id == "rifle", "rifle picked up and equipped")
	var left := level.get_node("Story/AlleyLeft") as ZombieSpawner
	check(left.active, "alley horde started")
	await get_tree().create_timer(8.0).timeout
	var spawned := get_tree().get_nodes_in_group("zombies").filter(func(z: Zombie) -> bool: return z.state == Zombie.State.CHASE)
	check(spawned.size() >= 8, "alley zombies are hunting (%d chasing)" % spawned.size())
	for i in 6:
		await kill_all(level)
		await get_tree().create_timer(1.0).timeout
	check(level.hud.objective_label.text == "Доберись до полицейского участка", "alley cleared -> objective: " + level.hud.objective_label.text)
	await teleport(level, Vector3(0, 0, -104))
	check((level.get_node("Story/Horde") as ZombieSpawner).active, "ambush horde started")
	check(level.hud.objective_label.text == "Войди в полицейский участок", "objective: enter the station")
	await teleport(level, Vector3(0, 0, -127.6))
	p.rotation = Vector3.ZERO
	p.head.rotation = Vector3.ZERO
	await frames(3)
	check(level.hud.prompt_label.text.contains("Войти"), "door prompt: " + level.hud.prompt_label.text)
	(level.get_node("Doors/StationDoor") as Door).interact(p)

	# ---------------------------------------------------------------- chapter 2
	level = await wait_scene("Station")
	check(level != null and Game.current_level == 1, "chapter 2 loaded")
	check(Game.checkpoint.get("weapons", {}).get("owned", []).has("rifle"), "rifle carried over in checkpoint")
	await start(level)
	p = level.player
	check(p.holder.get_weapon("rifle").owned, "chapter 2 player still has the rifle")
	check_paths(level, {
		"keycard": node_pos(level, "Pickups/Keycard1"),
		"armory": Vector3(0, 0, -55),
		"garage": Vector3(12, 0, -46),
		"yard exit": Vector3(30, 0, -48),
	})
	var armory := level.get_node("Doors/ArmoryDoor") as Door
	armory.interact(p)
	await frames(5)
	check(not armory.is_open, "armory stays locked without the card")
	await teleport(level, node_pos(level, "Pickups/Keycard1"))
	check(p.has_key("armory"), "picked up the armory keycard")
	check(level.hud.objective_label.text.contains("оружейную"), "objective: open the armory")
	armory.interact(p)
	await frames(5)
	check(armory.is_open, "armory opened with the card")
	await teleport(level, Vector3(0, 0, -55))
	await teleport(level, node_pos(level, "Pickups/WeaponBazooka1"))
	check(p.holder.get_weapon("bazooka").owned, "bazooka picked up")
	await frames(90)
	check((level.get_node("Doors/Cell2") as Door).is_open, "alarm opened the cells")
	check((level.get_node("Doors/GarageDoor") as Door).is_open, "alarm opened the garage door")
	check((level.get_node("Zombies/Prisoner1") as Zombie).state != Zombie.State.IDLE, "prisoners are awake")
	await kill_all(level)
	var shutter := level.get_node("Doors/Shutter") as Door
	shutter.interact(p)
	await frames(10)
	check(shutter.is_open, "garage shutter raised")
	await get_tree().create_timer(3.0).timeout
	await teleport(level, Vector3(30, 0.1, -48))

	# ---------------------------------------------------------------- chapter 3
	level = await wait_scene("Stadium")
	check(level != null and Game.current_level == 2, "chapter 3 loaded")
	await start(level)
	p = level.player
	check(p.holder.get_weapon("bazooka").owned, "bazooka carried into chapter 3")
	check_paths(level, {"helipad": Vector3(0, 0, 0), "north tunnel": Vector3(0, 0, -50),
		"east tunnel": Vector3(50, 0, 0), "rocket crate": node_pos(level, "Pickups/AmmoRocket1")})
	await teleport(level, Vector3(0, 0.1, 2))
	var holdout := level.get_node("Story/Holdout") as Holdout
	check(holdout.running, "siege started on the helipad")
	await get_tree().create_timer(6.0).timeout
	check(level.hud.timer_label.text.begins_with("Вертолёт через"), "timer: " + level.hud.timer_label.text)
	var siege_zombies := get_tree().get_nodes_in_group("zombies").filter(func(z: Zombie) -> bool: return z.state != Zombie.State.DEAD).size()
	check(siege_zombies >= 10, "siege spawns zombies (%d alive)" % siege_zombies)
	holdout.time_left = holdout.duration - holdout.boss_time - 0.1
	await frames(5)
	var brutes := get_tree().get_nodes_in_group("zombies").filter(func(z: Zombie) -> bool: return z.name.begins_with("Brute"))
	check(brutes.size() == 1, "boss spawned at the halfway mark")
	holdout.time_left = 0.05
	await frames(5)
	check(not holdout.running and level.get_node("Helicopter").visible, "time up: helicopter is flying in")
	await kill_all(level)
	await teleport(level, Vector3(0, 0.1, 20))
	await get_tree().create_timer(11.0).timeout
	check(level.hud.objective_label.text == "Садись в вертолёт!", "objective: board the helicopter")
	await teleport(level, Vector3(0, 0.1, 1))
	for i in 600:
		await get_tree().process_frame
		if get_tree().current_scene != null and get_tree().current_scene.name == "Ending":
			break
	check(get_tree().current_scene != null and get_tree().current_scene.name == "Ending", "reached the ending")
	await frames(10)
	print("  ending stats: " + str(get_tree().current_scene.get_node("Center/VBox/Stats").text).replace("\n", " | "))
	print("FAILURES: %d" % failures)
	get_tree().quit(failures)
