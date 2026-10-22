extends Node
## Renders reference screenshots (needs a display, e.g. xvfb-run):
##   godot --path . res://tests/screenshots.tscn -- <output dir>

var out := "user://"
## Optional second argument: comma-separated sections to render (menu, street, station, stadium).
var sections := PackedStringArray(["menu", "gallery", "bosses", "street", "station", "hospital", "subway", "stadium"])


func frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func snap(name: String) -> void:
	await frames(4)
	get_viewport().get_texture().get_image().save_png(out.path_join(name + ".png"))
	print("saved ", name)


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if not args.is_empty():
		out = args[0]
	if args.size() > 1:
		sections = args[1].split(",")
	_run.call_deferred()


func load_level(path: String) -> Level:
	var old := get_tree().current_scene
	if old != null and old != self:
		old.queue_free()
	var placeholder := Node.new()
	get_tree().root.add_child(placeholder)
	get_tree().current_scene = placeholder
	get_tree().change_scene_to_file(path)
	for i in 300:
		await frames(1)
		if get_tree().current_scene is Level:
			break
	var level := get_tree().current_scene as Level
	await frames(10)
	return level


func play(level: Level) -> Player:
	level.start_playing()
	while level.nav_region.is_baking():
		await frames(1)
	level.player.max_health = 100000
	level.player.health = 100000
	await frames(5)
	return level.player


func pose(player: Player, pos: Vector3, yaw_deg: float, pitch_deg := 0.0) -> void:
	player.global_position = pos
	player.rotation = Vector3(0, deg_to_rad(yaw_deg), 0)
	player.head.rotation = Vector3(deg_to_rad(pitch_deg), 0, 0)
	await frames(30)


func freeze_zombies() -> void:
	for z in get_tree().get_nodes_in_group("zombies"):
		(z as Zombie).set_physics_process(false)


func equip(player: Player, id: String) -> void:
	player.holder.give_weapon(id, false)
	player.holder.switch_to(player.holder.get_weapon(id))
	await get_tree().create_timer(0.7).timeout


func _run() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var placeholder := Node.new()
	get_tree().root.add_child(placeholder)
	get_tree().current_scene = placeholder
	if "menu" in sections:
		get_tree().change_scene_to_file("res://scenes/ui/main_menu.tscn")
		await frames(30)
		await snap("01_menu")
	if "gallery" in sections:
		await _gallery()
	if "bosses" in sections:
		await _bosses()
	if "street" in sections:
		await _street()
	if "doors" in sections:
		await _doors()
	if "station" in sections:
		await _station()
	if "hospital" in sections:
		await _hospital()
	if "subway" in sections:
		await _subway()
	if "stadium" in sections:
		await _stadium()
	get_tree().quit()


func _street() -> void:
	var level := await load_level("res://scenes/levels/level_1_outskirts.tscn")
	await snap("02_intro")
	var player := await play(level)
	await pose(player, Vector3(0, 0, 8), 0)
	await snap("03_street")
	# zombies close up
	for z in get_tree().get_nodes_in_group("zombies"):
		z.queue_free()
	await frames(2)
	for spec: Array in [["walker", Vector3(-1.2, 0, -27)], ["runner", Vector3(1.4, 0, -28.5)]]:
		var zombie := (load("res://scenes/zombies/%s.tscn" % spec[0]) as PackedScene).instantiate() as Zombie
		zombie.position = spec[1]
		zombie.rotation.y = PI
		level.add_child(zombie)
		zombie.alert(false)
	await frames(10)
	freeze_zombies()
	await equip(player, "rifle")
	await pose(player, Vector3(0, 0, -20), 0)
	await snap("04_zombies_rifle")


## The doors the story sends you through: the station entrance at night and the armory.
func _doors() -> void:
	var level := await load_level("res://scenes/levels/level_1_outskirts.tscn")
	var player := await play(level)
	freeze_zombies()
	player.holder.visible = false
	await pose(player, Vector3(0, 0, -114), 0, 4)
	await snap("15_station_entrance")
	level = await load_level("res://scenes/levels/level_2_station.tscn")
	player = await play(level)
	freeze_zombies()
	player.holder.visible = false
	await pose(player, Vector3(0, 0, -41), 0, 2)
	await snap("16_armory_door")
	await pose(player, Vector3(-1.2, 0, -41.25), -90, 0)
	await snap("17_garage_door")
	(level.get_node("Doors/GarageDoor") as Door).open()
	await get_tree().create_timer(1.5).timeout
	await pose(player, Vector3(9, 0, -47), -90, 6)
	await snap("18_garage_shutter")


func _station() -> void:
	var level := await load_level("res://scenes/levels/level_2_station.tscn")
	var player := await play(level)
	freeze_zombies()
	player.flashlight.visible = true
	await equip(player, "knife")
	await pose(player, Vector3(0, 0, -15), 0)
	await snap("05_corridor_knife")
	(level.get_node("Doors/ArmoryDoor") as Door).open()
	await get_tree().create_timer(1.5).timeout
	player.flashlight.visible = false
	for id: String in ["knife", "pistol", "rifle", "bazooka"]:
		await equip(player, id)
		await pose(player, Vector3(0, 0, -51), 0, -6)
		await snap("06_armory_" + id)


func _stadium() -> void:
	var level := await load_level("res://scenes/levels/level_5_stadium.tscn")
	var player := await play(level)
	var colossus := (load("res://scenes/zombies/colossus.tscn") as PackedScene).instantiate() as Zombie
	colossus.position = Vector3(-6.5, 0, -12)
	level.add_child(colossus)
	colossus.alert(false)
	await get_tree().create_timer(0.4).timeout
	freeze_zombies()
	level.get_node("Helicopter").activate()
	await equip(player, "bazooka")
	await pose(player, Vector3(-2, 0, 8), 0, 4)
	await get_tree().create_timer(8.5).timeout
	await snap("07_stadium_bazooka")
	await pose(player, Vector3(0, 0, 68), 0, 2)
	await snap("08_stadium_tunnel")


## Every zombie body in the lit lobby of the station: walking at the camera, one dying.
func _gallery() -> void:
	var level := await load_level("res://scenes/levels/level_2_station.tscn")
	var player := await play(level)
	for z in get_tree().get_nodes_in_group("zombies"):
		z.queue_free()
	await frames(2)
	var specs := [["walker", Vector3(-3.2, 0, -8.5)], ["walker", Vector3(-1.2, 0, -7.2)], ["runner", Vector3(1.0, 0, -7.8)],
		["walker", Vector3(3.0, 0, -8.8)], ["brute", Vector3(0.5, 0, -11.5)], ["walker", Vector3(-4.0, 0, -6.0)]]
	var spawned: Array[Zombie] = []
	for spec: Array in specs:
		var zombie := (load("res://scenes/zombies/%s.tscn" % spec[0]) as PackedScene).instantiate() as Zombie
		zombie.position = spec[1]
		level.add_child(zombie)
		zombie.set_physics_process(false)
		zombie.rotation.y = PI  # face the camera
		spawned.append(zombie)
	await frames(5)
	for i in spawned.size():
		var zombie := spawned[i]
		if i == 5:
			zombie.take_damage(9999, Vector3.BACK, zombie.global_position + Vector3.UP * 0.6)
		elif i == 2:
			zombie._play("Run", 1.0)
		else:
			zombie._play("Walk", 1.0)
			zombie._pose.reach = 1.0
	await pose(player, Vector3(0, 0, -2), 0, -4)
	await get_tree().create_timer(0.8).timeout
	await snap("00_gallery")
	await pose(player, Vector3(-5.5, 0, -7.0), -60, -8)
	await snap("00_gallery_side")


## The five chapter bosses side by side in the hospital lobby (power on, no HUD).
func _bosses() -> void:
	var level := await load_level("res://scenes/levels/level_3_hospital.tscn")
	var player := await play(level)
	level.get_node("Story/PowerOn").call("fire")
	(level.get_node("Decor/Alarm") as AudioStreamPlayer3D).stop()
	await get_tree().create_timer(2.0).timeout
	for z in get_tree().get_nodes_in_group("zombies"):
		z.queue_free()
	for spawner: String in ["Story/WardHorde", "Story/LobbyHorde"]:
		(level.get_node(spawner) as ZombieSpawner).deactivate()
	await frames(2)
	var specs := [["butcher", Vector3(-4.4, 0, -12.2)], ["warden", Vector3(-2.2, 0, -12.0)], ["patient_zero", Vector3(-0.1, 0, -11.8)],
		["lineman", Vector3(2.1, 0, -12.0)], ["colossus", Vector3(5.2, 0, -12.6)]]
	for spec: Array in specs:
		var boss := (load("res://scenes/zombies/%s.tscn" % spec[0]) as PackedScene).instantiate() as Boss
		boss.position = spec[1]
		level.add_child(boss)
		boss.set_physics_process(false)
		boss.rotation.y = PI - 0.2
	await frames(5)
	for boss in get_tree().get_nodes_in_group("bosses"):
		(boss as Boss)._play("Walk", 1.0)
	level.hud.gameplay.visible = false
	player.holder.visible = false
	await pose(player, Vector3(0.3, 0, -6.2), 0, 12)
	await get_tree().create_timer(0.6).timeout
	await snap("00_bosses")
	level.hud.gameplay.visible = true
	player.holder.visible = true


func _hospital() -> void:
	var level := await load_level("res://scenes/levels/level_3_hospital.tscn")
	var player := await play(level)
	freeze_zombies()
	await pose(player, Vector3(0, 0, 9), 0, 2)
	await snap("09_hospital_entrance")
	await equip(player, "shotgun")
	player.flashlight.visible = true
	await pose(player, Vector3(-6, 0, -16.5), 0, -4)
	await pose(player, Vector3(-6, 0, -16.5), 0, -4)
	player.rotation.y = deg_to_rad(10)
	await frames(10)
	await snap("10_hospital_ward_shotgun")
	player.flashlight.visible = false
	level.get_node("Story/PowerOn").call("fire")
	await get_tree().create_timer(2.0).timeout
	freeze_zombies()
	await pose(player, Vector3(16, 0, -16.5), 90, -2)
	await snap("11_hospital_power_on")


func _subway() -> void:
	var level := await load_level("res://scenes/levels/level_4_subway.tscn")
	var player := await play(level)
	freeze_zombies()
	await equip(player, "shotgun")
	await pose(player, Vector3(0, 0, -14), 0, -2)
	await snap("12_subway_platform")
	player.flashlight.visible = true
	await pose(player, Vector3(-7, 0, -66), 0, 0)
	await snap("13_subway_tunnel")
	player.flashlight.visible = false
	await pose(player, Vector3(0, 0, -134), 0, 0)
	await snap("14_subway_dinamo")
