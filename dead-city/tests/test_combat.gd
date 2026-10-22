extends Node
## Checks weapons and zombie behaviour in a real chapter.
##   godot --headless --path . res://tests/test_combat.tscn

const WALKER := preload("res://scenes/zombies/walker.tscn")
const BRUTE := preload("res://scenes/zombies/brute.tscn")
const BUTCHER := preload("res://scenes/zombies/butcher.tscn")
const WARDEN := preload("res://scenes/zombies/warden.tscn")
const PATIENT_ZERO := preload("res://scenes/zombies/patient_zero.tscn")
const LINEMAN := preload("res://scenes/zombies/lineman.tscn")
const COLOSSUS := preload("res://scenes/zombies/colossus.tscn")
const SOLDIER := preload("res://scenes/zombies/soldier.tscn")
const BLOATER := preload("res://scenes/zombies/bloater.tscn")
const SPITTER := preload("res://scenes/zombies/spitter.tscn")

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

	# Knife: an unaware zombie dies silently in one stab; an alerted one takes three and staggers.
	var knife := await equip("knife")
	var far := dummy(WALKER, Vector3(6, 0, -14), false)
	far.sight_range = 3.0  # can only be alerted by noise
	var neighbour := dummy(WALKER, Vector3(2.5, 0, -3), false)
	neighbour.sight_range = 0.5
	var unaware := dummy(WALKER, Vector3(0, 0, -1.4))
	await aim_at(unaware.global_position + Vector3.UP * 0.8)
	await get_tree().create_timer(0.2).timeout
	check(level.hud.prompt_label.text == MeleeWeapon.STEALTH_HINT, "takedown hint: " + level.hud.prompt_label.text)
	knife._handle_input(true, true)
	await get_tree().create_timer(0.5).timeout
	check(unaware.state == Zombie.State.DEAD, "stealth kill: an unaware walker dies from one stab")
	check(neighbour.state == Zombie.State.IDLE, "stealth kill is silent: the walker 3 m away did not notice")
	neighbour.queue_free()
	var w := dummy(WALKER, Vector3(0, 0, -1.4))
	w.alert(false)
	await aim_at(w.global_position + Vector3.UP * 0.8)
	knife._handle_input(true, true)
	await get_tree().create_timer(0.5).timeout
	check(w.health == 120 - 50, "knife hit for 50 on an alerted walker (health %d)" % w.health)
	check(w._stagger > 0.3, "the knife knocks it off balance")
	knife._handle_input(true, true)
	await get_tree().create_timer(0.5).timeout
	check(w.state != Zombie.State.DEAD, "a walker survives two stabs")
	knife._handle_input(true, true)
	await get_tree().create_timer(0.5).timeout
	check(w.state == Zombie.State.DEAD, "third stab kills the walker")
	check(far.state == Zombie.State.IDLE, "knife is silent: walker 15 m away still idle")

	# Pistol: a walker takes two headshots.
	var pistol := await equip("pistol")
	var target := dummy(WALKER, Vector3(0, 0, -7))
	await aim_at(target.global_position + Vector3.UP * 1.5)
	var ammo := pistol.ammo
	pistol._handle_input(true, true)
	await frames(2)
	check(pistol.ammo == ammo - 1, "pistol used one round")
	check(target.state != Zombie.State.DEAD and target.health == 120 - 85, "one headshot is not enough (health %d)" % target.health)
	(pistol as Gun)._cooldown = 0.0
	pistol._handle_input(true, true)
	await frames(2)
	check(target.state == Zombie.State.DEAD and target._pose.head_hidden, "second headshot kills and removes the head")
	await frames(10)
	check(far.state == Zombie.State.CHASE, "gunshot alerted the distant walker")
	far.queue_free()

	# Shotgun: devastating up close, weak far away, loads shell by shell.
	var shotgun := await equip("shotgun") as Gun
	player.holder.add_ammo("shells", 16)
	var close := dummy(WALKER, Vector3(0, 0, -3))
	await aim_at(close.global_position + Vector3.UP * 0.8)
	shotgun._handle_input(true, true)
	await frames(2)
	check(close.state == Zombie.State.DEAD, "shotgun kills a walker at 3 m in one shot")
	await get_tree().create_timer(1.0).timeout
	var far_target := dummy(WALKER, Vector3(0, 0, -25))
	await aim_at(far_target.global_position + Vector3.UP * 0.8)
	shotgun._cooldown = 0.0
	shotgun._handle_input(true, true)
	await frames(2)
	check(far_target.state != Zombie.State.DEAD and far_target.health > 80,
		"shotgun is weak at 25 m (health %d)" % far_target.health)
	far_target.queue_free()
	await get_tree().create_timer(1.0).timeout
	var loaded := shotgun.ammo
	shotgun.start_reload()
	await get_tree().create_timer(shotgun.reload_time + 0.1).timeout
	check(shotgun.ammo == loaded + 1 and shotgun.is_reloading, "one shell per reload step (%d -> %d)" % [loaded, shotgun.ammo])
	await get_tree().create_timer(shotgun.reload_time * 3).timeout
	check(shotgun.ammo == shotgun.magazine_size and not shotgun.is_reloading, "reload continues until the tube is full")

	# Rifle body shots.
	var rifle := await equip("rifle")
	target = dummy(WALKER, Vector3(0, 0, -8))
	await aim_at(target.global_position + Vector3.UP * 0.8)
	(rifle as Gun)._cooldown = 0.0
	rifle._handle_input(true, true)
	await frames(2)
	check(target.health == 120 - 30, "rifle body shot for 30 (health %d)" % target.health)
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
	check(brute.state != Zombie.State.DEAD and brute.health == 900, "brute survives 300 damage")
	brute.queue_free()

	await test_new_arsenal()
	await test_bosses()

	# Pickups and inventory.
	var pistol_weapon := player.holder.get_weapon("pistol")
	var before := pistol_weapon.reserve
	check(player.holder.add_ammo("pistol", 30) and pistol_weapon.reserve == mini(before + 30, pistol_weapon.max_reserve),
		"pistol ammo pickup")
	var state := player.get_state()
	var owned_count := player.holder.weapons.filter(func(w: Weapon) -> bool: return w.owned).size()
	check(state["weapons"]["owned"].size() == owned_count and owned_count >= 8, "state lists all %d owned weapons" % owned_count)

	print("FAILURES: %d" % failures)
	get_tree().quit(failures)


func reset_player() -> void:
	player.health = 100
	player.velocity = Vector3.ZERO
	player.global_position = Vector3(0, 0, 6)
	player.rotation = Vector3.ZERO
	player.head.rotation = Vector3.ZERO
	await frames(5)


func test_bosses() -> void:
	# The Warden's shield: bullets from the front barely scratch it, its head and back are open.
	await reset_player()
	var rifle := await equip("rifle") as Gun
	player.holder.add_ammo("rifle", 60)
	var warden := dummy(WARDEN, Vector3(0, 0, -8)) as Boss
	await aim_at(warden.global_position + Vector3.UP * 1.0)
	rifle._cooldown = 0.0
	rifle._handle_input(true, true)
	await frames(2)
	check(warden.health == warden.max_health - 2, "shield blocks a body shot (%d damage)" % (warden.max_health - warden.health))
	check(level.hud.boss_box.visible and level.hud.boss_label.text == "Надзиратель", "shooting the Warden shows its health bar")
	check(level.is_music_playing() and level._music.stream == warden.music, "boss music starts")
	var before := warden.health
	await aim_at(warden.global_position + Vector3.UP * 2.1)
	rifle._cooldown = 0.0
	rifle._handle_input(true, true)
	await frames(2)
	check(before - warden.health == 45, "headshot goes over the shield, bullets do 60%% to bosses (%d damage)" % (before - warden.health))
	warden.rotation.y = 0.0  # back to the player
	await frames(2)
	before = warden.health
	await aim_at(warden.global_position + Vector3.UP * 1.0)
	rifle._cooldown = 0.0
	rifle._handle_input(true, true)
	await frames(2)
	check(before - warden.health == 18, "no shield from behind (%d)" % (before - warden.health))
	before = warden.health
	warden.take_damage(220, Vector3.FORWARD, warden.global_position + Vector3.UP, true)
	check(before - warden.health == 440, "explosions do double damage to bosses (%d)" % (before - warden.health))
	warden.take_damage(99999, Vector3.FORWARD, warden.global_position)
	await frames(3)
	check(not level.hud.boss_box.visible, "boss bar hidden when the boss dies")
	await get_tree().create_timer(3.3).timeout
	check(not level.is_music_playing(), "boss music fades out after its death")
	var drops := level.get_children().filter(func(n: Node) -> bool: return n is Pickup)
	check(drops.size() == warden.drops.size(), "the Warden dropped %d pickups" % drops.size())
	for drop: Node in drops:
		drop.queue_free()
	warden.queue_free()

	# The Butcher charges from a distance.
	await reset_player()
	var butcher := dummy(BUTCHER, Vector3(0, 0, -12), false) as Boss
	butcher.alert(false)
	var top_speed := 0.0
	for i in 300:
		await frames(1)
		top_speed = maxf(top_speed, Vector2(butcher.velocity.x, butcher.velocity.z).length())
		if player.health < 100:
			break
	check(top_speed > 8.0, "the Butcher charges (top speed %.1f m/s)" % top_speed)
	check(player.health <= 100 - butcher.charge_damage, "the charge hits hard (health %d)" % player.health)
	butcher.queue_free()

	# The Lineman's ground slam: hurts on the ground, a jump dodges it.
	await reset_player()
	var lineman := dummy(LINEMAN, Vector3(0, 0, -3.5), false) as Boss
	lineman.summon_cooldown = 999.0
	lineman._cooldowns[Boss.Ability.SUMMON] = 999.0
	lineman.alert(false)
	for i in 240:
		await frames(1)
		if lineman.ability == Boss.Ability.SLAM:
			break
	check(lineman.ability == Boss.Ability.SLAM, "the Lineman slams when the player is close")
	await get_tree().create_timer(Boss.SLAM_LAND + 0.1).timeout
	check(player.health < 100, "the shockwave hurts (health %d)" % player.health)
	lineman.queue_free()

	# Patient Zero spits acid from afar and calls the sick.
	await reset_player()
	var patient := dummy(PATIENT_ZERO, Vector3(0, 0, -12), false) as Boss
	patient._cooldowns[Boss.Ability.SUMMON] = 0.0
	patient.alert(false)
	await get_tree().create_timer(1.5).timeout
	check(patient._minions.size() == patient.summon_count, "Patient Zero summoned %d walkers" % patient._minions.size())
	for minion: Zombie in patient._minions:
		minion.queue_free()
	await reset_player()
	patient._cooldowns[Boss.Ability.SUMMON] = 999.0
	patient._cooldowns[Boss.Ability.THROW] = 0.0
	patient.global_position = player.global_position + Vector3(0, 0, -12)
	await get_tree().create_timer(2.5).timeout
	check(player.health < 100, "acid spit hits a standing target (health %d)" % player.health)
	patient.queue_free()

	# The Colossus goes berserk at half health.
	await reset_player()
	var colossus := dummy(COLOSSUS, Vector3(0, 0, -20)) as Boss
	var speed := colossus.chase_speed
	colossus.take_damage(colossus.max_health / 4 + 10, Vector3.FORWARD, colossus.global_position + Vector3.UP, true)
	check(colossus.enraged and colossus.chase_speed > speed, "the Colossus is enraged below half health")
	check(level.hud.boss_label.text.contains("ярости"), "boss bar says it: " + level.hud.boss_label.text)
	colossus.take_damage(99999, Vector3.FORWARD, colossus.global_position + Vector3.UP)
	await frames(3)
	colossus.queue_free()
	for z in get_tree().get_nodes_in_group("zombies"):
		z.queue_free()
	await reset_player()


func test_new_arsenal() -> void:
	await reset_player()
	# Revolver: one heavy round.
	var revolver := await equip("revolver") as Gun
	var target := dummy(WALKER, Vector3(0, 0, -8))
	target.alert(false)
	target.set_physics_process(false)
	await aim_at(target.global_position + Vector3.UP * 0.8)
	revolver._handle_input(true, true)
	await frames(2)
	check(target.health == 120 - 80, "revolver body shot for 80 (health %d)" % target.health)
	target.queue_free()
	# SMG: holding the trigger empties the magazine fast.
	var smg := await equip("smg") as Gun
	var before := smg.ammo
	for i in 30:
		smg._handle_input(true, false)
		await frames(1)
	check(before - smg.ammo >= 5, "SMG fires automatically (%d rounds in half a second)" % (before - smg.ammo))
	# Sniper: the scope narrows the view and the gun is deadly accurate.
	var sniper := await equip("sniper") as Gun
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	Input.action_press("aim")
	await get_tree().create_timer(0.6).timeout
	check(sniper.aiming and player.camera.fov < 30.0 and level.hud.get_node("Gameplay/Scope").visible,
		"sniper scope zooms in (fov %.0f)" % player.camera.fov)
	Input.action_release("aim")
	await get_tree().create_timer(0.6).timeout
	check(not sniper.aiming and player.camera.fov > 60.0, "scope released")
	# Soldier: body armour, bare head.
	var soldier := dummy(SOLDIER, Vector3(0, 0, -8))
	await aim_at(soldier.global_position + Vector3.UP * 0.8)
	var pistol := await equip("pistol") as Gun
	pistol._handle_input(true, true)
	await frames(2)
	check(soldier.health == 150 - roundi(34 * 0.45), "body armour stops most of a pistol round (health %d)" % soldier.health)
	soldier.queue_free()
	# Grenade: thrown in an arc, blows up a group.
	await reset_player()
	var grenade := await equip("grenade") as Thrower
	var group: Array[Zombie] = []
	for offset: Vector3 in [Vector3(0, 0, -9), Vector3(1.5, 0, -10), Vector3(-1.5, 0, -10)]:
		group.append(dummy(WALKER, offset))
	await aim_at(player.global_position + Vector3(0, 0, -6))
	grenade._handle_input(true, true)
	await get_tree().create_timer(3.2).timeout
	check(group.all(func(z: Zombie) -> bool: return not is_instance_valid(z) or z.state == Zombie.State.DEAD),
		"a grenade kills a group of walkers")
	# Bloater: bursts next to the player, hurting the player and other zombies.
	await reset_player()
	var bloater := dummy(BLOATER, Vector3(0, 0, -4), false)
	var bystander := dummy(WALKER, Vector3(1.5, 0, -4.5))
	bloater.alert(false)
	await get_tree().create_timer(3.0).timeout
	check(bloater.state == Zombie.State.DEAD and player.health < 100, "the bloater bursts in your face (health %d)" % player.health)
	check(not is_instance_valid(bystander) or bystander.health < bystander.max_health, "the burst hurts other zombies too")
	# Spitter: acid from a distance, no boss bar.
	await reset_player()
	var spitter := dummy(SPITTER, Vector3(0, 0, -12), false) as Boss
	spitter.alert(false)
	await get_tree().create_timer(4.0).timeout
	check(player.health < 100 and not level.hud.boss_box.visible, "the spitter spits acid (health %d), no boss bar" % player.health)
	spitter.queue_free()
	for z in get_tree().get_nodes_in_group("zombies"):
		z.queue_free()
	await reset_player()
