extends Node
## Plays through all five chapters by teleporting the player and checks every story beat.
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
	# The navmesh bakes on a thread; with lots of props it can take a while right after an import.
	var map := level.get_world_3d().navigation_map
	for i in 3000:
		if not level.nav_region.is_baking() and NavigationServer3D.map_get_iteration_id(map) > 0:
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


func kill_all(level: Level, bosses := false) -> void:
	for z in get_tree().get_nodes_in_group("zombies"):
		var zombie := z as Zombie
		if zombie.state != Zombie.State.DEAD and (bosses or not zombie is Boss):
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
	# ---------------------------------------------------------------- menu, difficulty, intro cutscene
	get_tree().change_scene_to_file(Game.MAIN_MENU)
	for i in 60:
		await get_tree().process_frame
	var menu := get_tree().current_scene
	check(menu != null and menu.name == "MainMenu" and menu.get_tree().get_nodes_in_group("zombies").size() >= 5,
		"main menu with the burning street behind it")
	(menu.get_node("Menu/Buttons/SettingsButton") as Button).pressed.emit()
	await frames(2)
	check((menu.get_node("Menu/Settings") as Control).visible, "settings open from the menu")
	var old_master: float = Settings.get_value("master")
	Settings.set_value("master", 0.5)
	check(is_equal_approx(db_to_linear(AudioServer.get_bus_volume_db(0)), 0.5), "master volume applied to the bus")
	Settings.set_value("master", old_master)
	Settings.set_value("quality", 0)
	check(get_tree().root.msaa_3d == Viewport.MSAA_DISABLED, "low quality turns MSAA off")
	Settings.set_value("quality", 2)
	(menu.get_node("Menu/Settings") as Control).call("close")
	await frames(2)
	check((menu.get_node("Menu/Buttons") as Control).visible, "back from settings to the menu")
	(menu.get_node("Menu/Buttons/NewGameButton") as Button).pressed.emit()
	check((menu.get_node("Menu/Difficulty") as Control).visible, "new game asks for the difficulty")
	(menu.get_node("Menu/Difficulty/Level2") as Button).pressed.emit()
	var cutscene: Node = null
	for i in 300:
		await get_tree().process_frame
		if get_tree().current_scene != null and get_tree().current_scene.name == "IntroCutscene":
			cutscene = get_tree().current_scene
			break
	check(cutscene != null and Game.difficulty == Game.Difficulty.HARD, "hard game starts with the intro cutscene")
	await get_tree().create_timer(2.5).timeout
	check((cutscene.get_node("Voice") as AudioStreamPlayer).playing, "the intro is voiced")
	var key := InputEventKey.new()
	key.keycode = KEY_SPACE
	key.pressed = true
	Input.parse_input_event(key)
	var level := await wait_scene("Outskirts")
	check(level != null, "a key skips the intro to chapter 1")
	var walker := level.get_tree().get_nodes_in_group("zombies").filter(func(z: Zombie) -> bool: return z.name.begins_with("Walker"))[0] as Zombie
	check(walker.max_health == roundi(120 * 1.35), "hard: walkers are tougher (%d HP)" % walker.max_health)

	Game.new_game(Game.Difficulty.NORMAL, false)
	# ---------------------------------------------------------------- chapter 1
	level = await wait_scene("Outskirts")
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
	check(level.hud.objective_label.text == "Беги к полицейскому участку", "objective: run to the station")
	var butcher := level.get_node("Zombies/Butcher") as Boss
	check(butcher.state == Zombie.State.IDLE and not level.hud.boss_box.visible, "the Butcher waits at the station")
	await teleport(level, Vector3(0, 0, -112))
	check(butcher.state != Zombie.State.IDLE and level.hud.boss_box.visible and level.hud.boss_label.text == "Мясник",
		"the Butcher attacks, boss bar: " + level.hud.boss_label.text)
	check(level.hud.objective_label.text == "Убей Мясника", "objective: " + level.hud.objective_label.text)
	var station_door := level.get_node("Doors/StationDoor") as Door
	station_door.interact(p)
	await frames(3)
	check(not station_door.is_open, "station door stays shut while the Butcher lives")
	butcher.take_damage(99999, Vector3.FORWARD, butcher.global_position)
	await frames(5)
	check(not level.hud.boss_box.visible and level.hud.objective_label.text == "Войди в полицейский участок",
		"Butcher dead -> objective: " + level.hud.objective_label.text)
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
	var warden := level.get_node("Zombies/Warden") as Boss
	check(warden.state != Zombie.State.IDLE and level.hud.objective_label.text == "Убей Надзирателя",
		"the Warden comes for you: " + level.hud.objective_label.text)
	await teleport(level, Vector3(30, 0.1, -48))
	check(get_tree().current_scene == level, "no escape while the Warden lives")
	await kill_all(level, true)
	check(level.hud.objective_label.text.contains("машину"), "Warden dead -> objective: " + level.hud.objective_label.text)
	await teleport(level, Vector3(26, 0.1, -48))
	await teleport(level, Vector3(30, 0.1, -48))

	# ---------------------------------------------------------------- chapter 3: hospital
	level = await wait_scene("Hospital")
	check(level != null and Game.current_level == 2, "chapter 3 (hospital) loaded")
	await start(level)
	p = level.player
	check(p.holder.get_weapon("bazooka").owned, "bazooka carried into the hospital")
	check_paths(level, {"shotgun": node_pos(level, "Pickups/WeaponShotgun1"), "generator": Vector3(17.5, 0, -28),
		"fire door": Vector3(-23, 0, -16.5), "yard": Vector3(-31, 0, -17), "metro entrance": Vector3(-34.5, 0, -17)})
	await teleport(level, node_pos(level, "Pickups/WeaponShotgun1"))
	check(p.holder.get_weapon("shotgun").owned and p.holder.current.id == "shotgun", "shotgun picked up and equipped")
	var fire_door := level.get_node("Doors/FireDoor") as Door
	fire_door.interact(p)
	await frames(3)
	check(not fire_door.is_open, "fire door stays shut without power")
	var lamp := level.get_node("Lights/Ceiling3") as Light3D
	check(lamp.light_energy == 0.0, "ceiling lights are dark")
	await teleport(level, Vector3(17.3, 0, -28.2))
	(level.get_node("Doors/GeneratorSwitch") as Door).interact(p)
	await get_tree().create_timer(2.0).timeout
	check(lamp.light_energy > 0.5, "power on: lights came back (%.2f)" % lamp.light_energy)
	check(fire_door.is_open, "power on: fire door opened")
	check((level.get_node("Story/WardHorde") as ZombieSpawner).active, "power on: the wards wake up")
	check(level.hud.objective_label.text.contains("пожарному выходу"), "objective: " + level.hud.objective_label.text)
	await kill_all(level)
	await teleport(level, Vector3(-26.5, 0.1, -17))
	var patient := level.get_node("Zombies/PatientZero") as Boss
	check(patient.state != Zombie.State.IDLE and level.hud.objective_label.text == "Убей Пациента Ноль",
		"Patient Zero in the yard: " + level.hud.objective_label.text)
	await teleport(level, Vector3(-34.5, 0.1, -17))
	check(get_tree().current_scene == level, "metro entrance closed while Patient Zero lives")
	await kill_all(level, true)
	check(level.hud.objective_label.text == "Спускайся в метро", "Patient Zero dead -> " + level.hud.objective_label.text)
	await teleport(level, Vector3(-30, 0.1, -17))
	await teleport(level, Vector3(-34.5, 0.1, -17))

	# ---------------------------------------------------------------- chapter 4: subway
	level = await wait_scene("Subway")
	check(level != null and Game.current_level == 3, "chapter 4 (subway) loaded")
	await start(level)
	p = level.player
	check(p.holder.get_weapon("shotgun").owned, "shotgun carried into the subway")
	check_paths(level, {"blockage": Vector3(-7, 0, -86), "service corridor": Vector3(-13, 0, -96),
		"after blockage": Vector3(-7, 0, -110), "dinamo": Vector3(0, 0, -150), "gate": Vector3(0, 0, -170)})
	await teleport(level, Vector3(-7, 0.1, -83))
	check(level.hud.objective_label.text == "Найди обход завала", "blockage: " + level.hud.objective_label.text)
	(level.get_node("Doors/ServiceDoor") as Door).interact(p)
	await frames(5)
	check((level.get_node("Doors/ServiceDoor") as Door).is_open, "service door opened")
	await teleport(level, Vector3(-7, 0.1, -108))
	check((level.get_node("Story/Runners") as ZombieSpawner).active, "runners chase through the tunnel")
	await kill_all(level)
	await teleport(level, Vector3(0, 0.1, -142))
	var gate_holdout := level.get_node("Story/Holdout") as Holdout
	check(gate_holdout.running, "gate siege started")
	await get_tree().create_timer(4.0).timeout
	check(level.hud.timer_label.text.begins_with("Решётка откроется"), "timer: " + level.hud.timer_label.text)
	gate_holdout.time_left = gate_holdout.duration - gate_holdout.boss_time - 0.1
	await frames(5)
	var linemen := get_tree().get_nodes_in_group("bosses").filter(func(z: Zombie) -> bool: return z.name.begins_with("Lineman"))
	check(linemen.size() == 1, "the Lineman comes out of the side passage")
	gate_holdout.time_left = 0.05
	await frames(5)
	check(not (level.get_node("Doors/Gate") as Door).is_open and level.hud.timer_label.text == "Убей Обходчика!",
		"gate waits for the Lineman: " + level.hud.timer_label.text)
	await kill_all(level, true)
	await get_tree().create_timer(2.5).timeout
	check((level.get_node("Doors/Gate") as Door).is_open, "Lineman dead -> gate opened")
	await kill_all(level, true)
	await teleport(level, Vector3(0, 0.1, -179))

	# ---------------------------------------------------------------- chapter 5: stadium
	level = await wait_scene("Stadium")
	check(level != null and Game.current_level == 4, "chapter 5 (stadium) loaded")
	await start(level)
	p = level.player
	check(p.holder.get_weapon("bazooka").owned and p.holder.get_weapon("shotgun").owned, "full arsenal carried into the stadium")
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
	var colossi := get_tree().get_nodes_in_group("bosses").filter(func(z: Zombie) -> bool: return z.name.begins_with("Colossus"))
	check(colossi.size() == 1, "the Colossus arrives at the halfway mark")
	check(level.hud.boss_box.visible and level.hud.boss_label.text == "Колосс", "boss bar: " + level.hud.boss_label.text)
	holdout.time_left = 0.05
	await frames(5)
	check(holdout.running and not level.get_node("Helicopter").visible and level.hud.timer_label.text.begins_with("Убей Колосса"),
		"helicopter waits for the Colossus: " + level.hud.timer_label.text)
	await kill_all(level, true)
	await frames(5)
	check(not holdout.running and level.get_node("Helicopter").visible, "Colossus dead: helicopter is flying in")
	await kill_all(level, true)
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
