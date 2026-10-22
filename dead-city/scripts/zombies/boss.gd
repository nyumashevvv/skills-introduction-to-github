class_name Boss
extends Zombie
## The enemy at the end of a chapter: a zombie with a health bar on the HUD and special abilities.
## Each ability is switched on by its exports (charge_speed, projectile, slam_radius, minion,
## front_armor) and used when it is off cooldown and the player is at the right distance.

enum Ability { NONE, CHARGE, THROW, SLAM, SUMMON }

const SPARKS_SCENE := preload("res://scenes/effects/impact.tscn")
const SLAM_SCENE := preload("res://scenes/effects/slam.tscn")
const ROARS: Array[AudioStream] = [
	preload("res://sounds/zombie/roar1.ogg"), preload("res://sounds/zombie/roar2.ogg"),
	preload("res://sounds/zombie/roar3.ogg"),
]
const CHARGE_WINDUP := 0.8
const CHARGE_TIME := 1.6
const STUN_TIME := 1.8
const THROW_TIME := 1.1
const SLAM_LAND := 0.75
const SLAM_TIME := 1.4
const SUMMON_TIME := 1.6
## Abilities run faster and recover sooner once enraged.
const RAGE_SPEED := 1.35
const RAGE_COOLDOWN := 0.65

@export var boss_name := ""
## StoryEvent fired when it first notices the player (or gets shot), so its introduction
## always comes before its death even if the player opens fire from afar.
@export var alert_event: NodePath
## StoryEvent fired when the boss dies.
@export var death_event: NodePath
## Played (looping) from the moment it notices the player until it dies.
@export var music: AudioStream
## Pickups left where it falls.
@export var drops: Array[PackedScene] = []
@export_group("Armour")
## Bosses shrug off bullets but explosions tear into them: the RPG is the boss weapon.
@export var bullet_multiplier := 0.6
@export var explosive_multiplier := 2.0
## Damage multiplier for hits from the front, except headshots and explosions. 1 = no shield.
@export_range(0.0, 1.0) var front_armor := 1.0
@export_group("Charge")
## Running speed of the charge; 0 = no charge.
@export var charge_speed := 0.0
@export var charge_cooldown := 7.0
@export var charge_damage := 30
@export var charge_distance := Vector2(5.0, 18.0)
@export_group("Throw")
@export var projectile: PackedScene
@export var projectile_count := 1
@export var throw_cooldown := 4.0
@export var throw_distance := Vector2(5.0, 30.0)
@export var throw_animation := "SwordSlash"
@export_group("Slam")
## Shockwave radius of a ground slam; 0 = no slam.
@export var slam_radius := 0.0
@export var slam_damage := 30
@export var slam_cooldown := 8.0
@export_group("Summon")
@export var minion: PackedScene
@export var summon_count := 3
@export var summon_cooldown := 18.0
@export var max_minions := 6
@export_group("Rage")
## Health fraction below which it gets faster and uses abilities more often; 0 = never.
@export_range(0.0, 1.0) var enrage_at := 0.0

var enraged := false
var ability := Ability.NONE

var _ability_time := 0.0
var _done := false
var _charge_direction := Vector3.ZERO
var _stunned := false
var _cooldowns := {Ability.CHARGE: 1.5, Ability.THROW: 2.0, Ability.SLAM: 2.0, Ability.SUMMON: 6.0}
var _minions: Array[Zombie] = []

@onready var roar_sound: AudioStreamPlayer3D = $RoarSound
@onready var shield_sound: AudioStreamPlayer3D = get_node_or_null("ShieldSound")


func _ready() -> void:
	add_to_group("bosses")
	super._ready()


func _physics_process(delta: float) -> void:
	for key: Ability in _cooldowns:
		_cooldowns[key] = maxf(_cooldowns[key] - delta, 0.0)
	super._physics_process(delta)


func alert(spread := true) -> void:
	var was_idle := state == State.IDLE
	super.alert(spread)
	if was_idle and state != State.IDLE:
		roar()
		_update_bar()
		var level := get_tree().current_scene as Level
		if level != null and music != null:
			level.play_music(music)
		if not alert_event.is_empty():
			get_node(alert_event).call("fire")


func roar() -> void:
	roar_sound.stream = ROARS.pick_random()
	roar_sound.pitch_scale = voice_pitch * randf_range(0.95, 1.05)
	roar_sound.play()


func take_damage(amount: int, direction: Vector3, hit_point: Vector3, explosive := false) -> bool:
	var killed := super.take_damage(amount, direction, hit_point, explosive)
	if not killed and not enraged and enrage_at > 0.0 and health <= max_health * enrage_at:
		enraged = true
		chase_speed *= RAGE_SPEED
		roar()
	_update_bar()
	return killed


func _damage_scale(direction: Vector3, hit_point: Vector3, explosive: bool) -> float:
	if explosive:
		return explosive_multiplier
	if front_armor >= 1.0 or is_headshot(hit_point) or _stunned:
		return bullet_multiplier
	# A hit travelling against the way it faces lands on the shield.
	if direction.dot(-global_basis.z) > -0.35:
		return bullet_multiplier
	Effects.spawn(SPARKS_SCENE, self, hit_point, -direction)
	if shield_sound != null:
		shield_sound.pitch_scale = randf_range(0.9, 1.1)
		shield_sound.play()
	return bullet_multiplier * front_armor


func _update_bar() -> void:
	var level := get_tree().current_scene as Level
	if level == null:
		return
	if state == State.DEAD:
		level.hud.hide_boss()
	elif state != State.IDLE:
		level.hud.show_boss(boss_name + (" — в ярости" if enraged else ""), health, max_health)


# --------------------------------------------------------------------------- abilities
func _try_special(distance: float) -> bool:
	var alive: Array[Zombie] = []
	for zombie in _minions:
		if is_instance_valid(zombie) and zombie.state != State.DEAD:
			alive.append(zombie)
	_minions = alive
	if minion != null and _ready_to(Ability.SUMMON) and _minions.size() < max_minions:
		return _start(Ability.SUMMON)
	if slam_radius > 0.0 and _ready_to(Ability.SLAM) and distance < slam_radius * 0.6:
		return _start(Ability.SLAM)
	var in_sight := _has_line_of_sight()
	if charge_speed > 0.0 and _ready_to(Ability.CHARGE) and in_sight \
			and distance > charge_distance.x and distance < charge_distance.y:
		return _start(Ability.CHARGE)
	if projectile != null and _ready_to(Ability.THROW) and in_sight \
			and distance > throw_distance.x and distance < throw_distance.y:
		return _start(Ability.THROW)
	return false


func _ready_to(which: Ability) -> bool:
	return _cooldowns[which] <= 0.0


func _start(which: Ability) -> bool:
	var cooldown: float = {Ability.CHARGE: charge_cooldown, Ability.THROW: throw_cooldown,
		Ability.SLAM: slam_cooldown, Ability.SUMMON: summon_cooldown}[which]
	_cooldowns[which] = cooldown * (RAGE_COOLDOWN if enraged else 1.0) * randf_range(0.85, 1.15)
	state = State.SPECIAL
	ability = which
	_ability_time = 0.0
	_done = false
	_stunned = false
	var anim_speed := RAGE_SPEED if enraged else 1.0
	match which:
		Ability.CHARGE:
			roar()
			_play_once("Idle", 1.0)
		Ability.THROW:
			_play_once(throw_animation, anim_speed)
		Ability.SLAM:
			_play_once("Jump", 1.0)
		Ability.SUMMON:
			roar()
			_play_once("Victory", 1.2)
	return true


func _process_special(delta: float) -> void:
	_ability_time += delta
	var to_player := player.global_position - global_position
	to_player.y = 0.0
	match ability:
		Ability.CHARGE:
			_process_charge(delta, to_player)
		Ability.THROW:
			_move(Vector3.ZERO, 0.0, delta)
			_face(to_player, delta)
			if not _done and _ability_time >= THROW_TIME * 0.45:
				_done = true
				_throw()
			if _ability_time >= THROW_TIME:
				_end_ability()
		Ability.SLAM:
			_move(Vector3.ZERO, 0.0, delta)
			if not _done and _ability_time >= SLAM_LAND:
				_done = true
				_slam()
			if _ability_time >= SLAM_TIME:
				_end_ability()
		Ability.SUMMON:
			_move(Vector3.ZERO, 0.0, delta)
			if not _done and _ability_time >= 0.6:
				_done = true
				_summon()
			if _ability_time >= SUMMON_TIME:
				_end_ability()


func _end_ability() -> void:
	ability = Ability.NONE
	_stunned = false
	state = State.CHASE
	_repath_timer = 0.0


func _process_charge(delta: float, to_player: Vector3) -> void:
	if _stunned:
		_move(Vector3.ZERO, 0.0, delta)
		if _ability_time >= STUN_TIME:
			_end_ability()
		return
	if _ability_time < CHARGE_WINDUP:
		# Lock on, then go.
		_move(Vector3.ZERO, 0.0, delta)
		_face(to_player, delta * 2.0)
		_charge_direction = to_player.normalized()
		return
	if _anim.current_animation != "Run":
		_play_once("Run", 1.8)
	velocity.x = _charge_direction.x * charge_speed
	velocity.z = _charge_direction.z * charge_speed
	_face(_charge_direction, delta)
	if not _done and to_player.length() < attack_range + 0.4 and absf(player.global_position.y - global_position.y) < 1.5:
		_done = true
		player.take_damage(charge_damage)
		player.apply_knockback(_charge_direction * 11.0 + Vector3.UP * 4.0)
		player.shake(0.6)
		attack_sound.stream = ATTACKS.pick_random()
		attack_sound.play()
		_end_ability()
	elif is_on_wall() and _ability_time > CHARGE_WINDUP + 0.15:
		# Ran into something: dazed for a moment, and its guard is down.
		_stunned = true
		_ability_time = 0.0
		velocity = -_charge_direction * 2.0
		player.shake(0.3)
		_play_once("RecieveHit", 0.5)
	elif _ability_time >= CHARGE_WINDUP + CHARGE_TIME:
		_end_ability()


func _throw() -> void:
	var hand := _bone_position("Fist.R")
	var target := player.global_position + Vector3.UP * 0.9
	var side := global_basis.x
	for i in projectile_count:
		var shot := projectile.instantiate() as BossProjectile
		get_tree().current_scene.add_child(shot)
		var offset := 0.0 if projectile_count == 1 else (float(i) / (projectile_count - 1) - 0.5) * 3.0
		shot.launch(hand, target + side * offset + player.velocity * 0.35, self)


func _slam() -> void:
	var at := global_position
	var effect := Effects.spawn(SLAM_SCENE, self, at + Vector3.UP * 0.1)
	effect.scale = Vector3.ONE * slam_radius / 7.0
	var to_player := player.global_position - at
	var distance := Vector2(to_player.x, to_player.z).length()
	player.shake(clampf(1.2 - distance / (slam_radius * 2.0), 0.2, 1.0))
	# A jump dodges the shockwave.
	if distance < slam_radius and player.is_on_floor() and absf(to_player.y) < 1.5:
		player.take_damage(roundi(slam_damage * (1.0 - 0.6 * distance / slam_radius)))
		var away := Vector3(to_player.x, 0.0, to_player.z).normalized()
		player.apply_knockback(away * 8.0 + Vector3.UP * 5.0)


func _summon() -> void:
	var nav_map := get_world_3d().navigation_map
	for i in summon_count:
		if _minions.size() >= max_minions:
			break
		var angle := TAU * i / summon_count + randf() * 0.5
		var spot := global_position + Vector3(cos(angle), 0.0, sin(angle)) * 3.0
		spot = NavigationServer3D.map_get_closest_point(nav_map, spot)
		var zombie := minion.instantiate() as Zombie
		zombie.start_alerted = true
		zombie.position = spot
		get_tree().current_scene.add_child(zombie)
		_minions.append(zombie)


func _play_once(animation: String, speed: float) -> void:
	if _anim == null or not _anim.has_animation(animation):
		return
	_anim.play(animation, 0.15)
	_anim.speed_scale = speed


func _bone_position(bone: String) -> Vector3:
	var index := _skeleton.find_bone(bone)
	if index < 0:
		return global_position + Vector3.UP * 1.5
	return (_skeleton.global_transform * _skeleton.get_bone_global_pose(index)).origin


func _has_line_of_sight() -> bool:
	var from := global_position + Vector3.UP * 1.5
	var query := PhysicsRayQueryParameters3D.create(from, player.global_position + Vector3.UP * 1.3, SIGHT_MASK, [get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	return not hit.is_empty() and hit.collider == player


func _die(headshot: bool) -> void:
	super._die(headshot)
	ability = Ability.NONE
	_update_bar()
	var level := get_tree().current_scene as Level
	if level != null:
		level.stop_music()
	for i in drops.size():
		var pickup := drops[i].instantiate() as Node3D
		var angle := TAU * i / drops.size()
		pickup.position = global_position + Vector3(cos(angle), 0.0, sin(angle)) * 1.2
		get_tree().current_scene.add_child.call_deferred(pickup)
	if not death_event.is_empty():
		get_node(death_event).call("fire")
