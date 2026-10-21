extends Node
## Checks weapons and zombie behaviour in a real chapter.
##   godot --headless --path . res://tests/test_combat.tscn

const WALKER := preload("res://scenes/zombies/walker.tscn")
const BRUTE := preload("res://scenes/zombies/brute.tscn")

var failures := 0
var level: Level
var player: Player


func check(cond: bool, what: String) -> void:
	print(("PASS  " if cond else "FAIL  ") + what)
	if not cond:
		failures += 1


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _ready() -> void:
	_run.call_deferred()


## A frozen walker standing [param distance] m straight ahead of the player.
func dummy(scene: PackedScene, offset: Vector3, frozen := true) -> Zombie:
	var zombie := scene.instantiate() as Zombie
	zombie.position = player.global_position + offset
	zombie.rotation.y = PI
	level.add_child(zombie)
	if frozen:
		zombie.set_physics_process(false)
	return zombie


func aim_at(point: Vector3) -> void:
	player.rotation = Vector3.ZERO
	var to := point - player.camera.global_position
	player.head.rotation.x = atan2(to.y, -to.z)
	player.rotation.y = atan2(-to.x, -to.z)
	await frames(2)


func equip(id: String) -> Weapon:
	player.holder.give_weapon(id, false)
	player.holder.switch_to(player.holder.get_weapon(id))
	var weapon := player.holder.current
	await get_tree().create_timer(weapon.equip_time + 0.1).timeout
	return weapon


func _run() -> void:
	level = (load("res://scenes/levels/level_1_outskirts.tscn") as PackedScene).instantiate() as Level
	get_tree().root.add_child(level)
	get_tree().current_scene = level
	await frames(3)
	level.start_playing()
	while level.nav_region.is_baking():
		await frames(1)
	# Clear the street so only test dummies are around.
	for z in get_tree().get_nodes_in_group("zombies"):
		z.queue_free()
	player = level.player
	player.global_position = Vector3(0, 0, 6)
	await frames(20)

	# Knife: silent, two body hits kill a walker.
	var knife := await equip("knife")
	var w := dummy(WALKER, Vector3(0, 0, -1.4))
	var far := dummy(WALKER, Vector3(6, 0, -14), false)
	far.sight_range = 3.0  # can only be alerted by noise
	await aim_at(w.global_position + Vector3.UP * 0.8)
	knife._handle_input(true, true)
	await get_tree().create_timer(0.5).timeout
	check(w.health == 70 - 45, "knife hit for 45 (health %d)" % w.health)
	knife._handle_input(true, true)
	await get_tree().create_timer(0.5).timeout
	check(w.state == Zombie.State.DEAD, "second stab kills the walker")
	check(far.state == Zombie.State.IDLE, "knife is silent: walker 15 m away still idle")

	# Pistol headshot.
	var pistol := await equip("pistol")
	var target := dummy(WALKER, Vector3(0, 0, -7))
	await aim_at(target.global_position + Vector3.UP * 1.5)
	var ammo := pistol.ammo
	pistol._handle_input(true, true)
	await frames(2)
	check(pistol.ammo == ammo - 1, "pistol used one round")
	check(target.state == Zombie.State.DEAD and target._pose.head_hidden, "pistol headshot kills and removes the head")
	await frames(10)
	check(far.state == Zombie.State.CHASE, "gunshot alerted the distant walker")
	far.queue_free()

	# Rifle body shots.
	var rifle := await equip("rifle")
	target = dummy(WALKER, Vector3(0, 0, -8))
	await aim_at(target.global_position + Vector3.UP * 0.8)
	(rifle as Gun)._cooldown = 0.0
	rifle._handle_input(true, true)
	await frames(2)
	check(target.health == 70 - 26, "rifle body shot for 26 (health %d)" % target.health)
	target.queue_free()

	# Reload.
	player.holder.add_ammo("rifle", 60)
	rifle.ammo = 0
	var reserve := rifle.reserve
	rifle.start_reload()
	await get_tree().create_timer(rifle.reload_time + 0.2).timeout
	check(rifle.ammo == 30 and rifle.reserve == reserve - 30, "rifle reload: %d / %d" % [rifle.ammo, rifle.reserve])

	# Bazooka splash damage.
	var bazooka := await equip("bazooka")
	player.holder.add_ammo("rocket", 2)
	var group: Array[Zombie] = []
	for offset: Vector3 in [Vector3(0, 0, -14), Vector3(1.5, 0, -15), Vector3(-1.5, 0, -15.5)]:
		group.append(dummy(WALKER, offset))
	await aim_at(group[0].global_position + Vector3.UP * 0.8)
	var hp := player.health
	bazooka._handle_input(true, true)
	await get_tree().create_timer(1.0).timeout
	check(group.all(func(z: Zombie) -> bool: return not is_instance_valid(z) or z.state == Zombie.State.DEAD),
		"one rocket killed a group of three")
	check(player.health == hp, "rocket at 14 m did not hurt the player")
	check(bazooka.is_reloading or bazooka.ammo == 1, "bazooka reloads automatically")

	# Zombie attacks.
	player.health = 100
	var attacker := dummy(WALKER, Vector3(0, 0, -3), false)
	attacker.alert(false)
	await get_tree().create_timer(3.0).timeout
	check(player.health < 100, "walker attacked the player (health %d)" % player.health)
	attacker.take_damage(999, Vector3.FORWARD, attacker.global_position)

	player.health = 100
	player.global_position = Vector3(0, 0, 6)
	await frames(5)
	var brute := dummy(BRUTE, Vector3(0, 0, -4), false)
	brute.alert(false)
	var start := player.global_position
	await get_tree().create_timer(3.5).timeout
	check(player.health <= 100 - 34, "brute hits hard (health %d)" % player.health)
	check(player.global_position.distance_to(start) > 1.0, "brute knocks the player back")
	brute.take_damage(300, Vector3.FORWARD, brute.global_position + Vector3.UP)
	check(brute.state != Zombie.State.DEAD and brute.health == 700, "brute survives 300 damage")

	# Pickups and inventory.
	var pistol_weapon := player.holder.get_weapon("pistol")
	var before := pistol_weapon.reserve
	check(player.holder.add_ammo("pistol", 24) and pistol_weapon.reserve == mini(before + 24, pistol_weapon.max_reserve),
		"pistol ammo pickup")
	var state := player.get_state()
	check(state["weapons"]["owned"].size() == 4, "state lists four weapons")

	print("FAILURES: %d" % failures)
	get_tree().quit(failures)
