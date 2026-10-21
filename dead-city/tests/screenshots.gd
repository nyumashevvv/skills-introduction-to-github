extends Node
## Renders reference screenshots (needs a display, e.g. xvfb-run):
##   godot --path . res://tests/screenshots.tscn -- <output dir>

var out := "user://"
## Optional second argument: comma-separated sections to render (menu, street, station, stadium).
var sections := PackedStringArray(["menu", "gallery", "street", "station", "stadium"])


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
	if "street" in sections:
		await _street()
	if "station" in sections:
		await _station()
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
	var level := await load_level("res://scenes/levels/level_3_stadium.tscn")
	var player := await play(level)
	var brute := (load("res://scenes/zombies/brute.tscn") as PackedScene).instantiate() as Zombie
	brute.position = Vector3(3, 0, -14)
	level.add_child(brute)
	brute.alert(false)
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
