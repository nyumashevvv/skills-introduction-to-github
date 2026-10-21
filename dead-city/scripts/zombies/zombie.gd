class_name Zombie
extends CharacterBody3D
## Zombie AI driving a rigged, animated body. One script for every zombie type;
## the scenes differ in stats and in which bodies they pick from.

signal died(zombie: Zombie)

enum State { IDLE, CHASE, ATTACK, DEAD }

const BLOOD_SCENE := preload("res://scenes/effects/blood_burst.tscn")
const BLOOD_DECAL_SCENE := preload("res://scenes/effects/blood_decal.tscn")
const FLASH_MATERIAL := preload("res://materials/hit_flash.tres")
const GROANS: Array[AudioStream] = [
	preload("res://sounds/zombie/groan1.ogg"), preload("res://sounds/zombie/groan2.ogg"),
	preload("res://sounds/zombie/groan3.ogg"), preload("res://sounds/zombie/groan4.ogg"),
	preload("res://sounds/zombie/groan5.ogg"), preload("res://sounds/zombie/groan6.ogg"),
	preload("res://sounds/zombie/groan7.ogg"), preload("res://sounds/zombie/groan8.ogg"),
]
const ATTACKS: Array[AudioStream] = [
	preload("res://sounds/zombie/attack1.ogg"), preload("res://sounds/zombie/attack2.ogg"),
	preload("res://sounds/zombie/attack3.ogg"), preload("res://sounds/zombie/attack4.ogg"),
	preload("res://sounds/zombie/attack5.ogg"),
]
const DEATHS: Array[AudioStream] = [
	preload("res://sounds/zombie/death1.ogg"), preload("res://sounds/zombie/death2.ogg"),
	preload("res://sounds/zombie/death3.ogg"), preload("res://sounds/zombie/death4.ogg"),
]
const LOOPING_ANIMATIONS: Array[String] = ["Idle", "Walk", "Run"]
## Line of sight is blocked by the world and ends on the player.
const SIGHT_MASK := 1 | 2
const CORPSE_TIME := 15.0
## Ground speed (m/s) of the Walk and Run animations at speed_scale 1 and normal body size.
const WALK_ANIM_SPEED := 1.4
const RUN_ANIM_SPEED := 4.0
## Seconds between any two groans across all zombies, so a horde never moans in chorus.
const GROAN_GAP := 1.2

static var _next_groan_time := 0.0

@export var max_health := 60
@export var chase_speed := 2.2
@export var wander_speed := 0.5
@export var turn_speed := 6.0
@export_group("Attack")
@export var attack_damage := 15
@export var attack_range := 1.6
@export var attack_windup := 0.5
@export var attack_recovery := 0.6
## Pushes the player away on a hit (the brute).
@export var knockback := 0.0
@export_group("Senses")
@export var sight_range := 20.0
@export var start_alerted := false
@export_group("Body")
## Rigged character models to pick from at random.
@export var bodies: Array[PackedScene] = []
@export var body_scale := 0.58
## Tints the "Skin" material so every body looks dead. Empty keeps the model's own skin.
@export var skin_colors: Array[Color] = []
## Animation used while chasing: "Walk" (shambling, arms out) or "Run".
@export var chase_animation := "Walk"
@export_range(0.0, 1.0) var stagger_resistance := 0.0
@export var voice_pitch := 1.0

var state := State.IDLE
var health := 0
var player: Player
var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

var _home := Vector3.ZERO
var _wander_target := Vector3.ZERO
var _wander_timer := 0.0
var _sight_timer := 0.0
var _repath_timer := 0.0
var _attack_timer := 0.0
var _attack_hit_done := false
var _groan_timer := 0.0
var _stagger := 0.0
var _flash_timer := 0.0
var _hit_anim_time := 0.0
var _meshes: Array[MeshInstance3D] = []
var _anim: AnimationPlayer
var _skeleton: Skeleton3D
var _pose: ZombiePose
var _neck := -1

@onready var agent: NavigationAgent3D = $NavigationAgent3D
@onready var model: Node3D = $Model
@onready var collision: CollisionShape3D = $CollisionShape3D
@onready var groan_sound: AudioStreamPlayer3D = $GroanSound
@onready var attack_sound: AudioStreamPlayer3D = $AttackSound
@onready var death_sound: AudioStreamPlayer3D = $DeathSound


func _ready() -> void:
	health = max_health
	player = get_tree().get_first_node_in_group("player") as Player
	_home = global_position
	_wander_target = global_position
	_groan_timer = randf_range(3.0, 15.0)
	_build_body()
	if start_alerted:
		alert(false)


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	_update_flash(delta)
	_stagger = maxf(_stagger - delta, 0.0)
	_hit_anim_time = maxf(_hit_anim_time - delta, 0.0)
	_update_groan(delta)
	match state:
		State.IDLE:
			_process_idle(delta)
		State.CHASE:
			_process_chase(delta)
		State.ATTACK:
			_process_attack(delta)
	move_and_slide()
	_animate(delta)


func is_headshot(point: Vector3) -> bool:
	if _skeleton == null or _neck < 0:
		return false
	return point.y >= (_skeleton.global_transform * _skeleton.get_bone_global_pose(_neck)).origin.y


## Returns true when this hit killed the zombie.
func take_damage(amount: int, direction: Vector3, hit_point: Vector3, explosive := false) -> bool:
	if state == State.DEAD:
		return false
	health -= amount
	_flash_timer = 0.06
	for mesh in _meshes:
		mesh.material_overlay = FLASH_MATERIAL
	var flinch := 1.0 - stagger_resistance
	_stagger = 0.35 * flinch
	var push := Vector3(direction.x, 0.0, direction.z).normalized()
	velocity += push * flinch * (6.0 if explosive else 1.2)
	Effects.spawn(BLOOD_SCENE, self, hit_point, -direction)
	if state == State.IDLE:
		alert()
	if health <= 0:
		_die(is_headshot(hit_point) and not explosive)
		return true
	if flinch > 0.5 and state != State.ATTACK and _hit_anim_time <= 0.0:
		_hit_anim_time = 0.35
		_anim.play("RecieveHit", 0.05)
		_anim.speed_scale = 1.6
	return false


func alert(spread := true) -> void:
	if state != State.IDLE:
		return
	state = State.CHASE
	_repath_timer = 0.0
	_play_groan(true)
	if spread:
		# Zombies nearby join the hunt.
		for node in get_tree().get_nodes_in_group("zombies"):
			var other := node as Zombie
			if other != self and other.global_position.distance_to(global_position) < 10.0:
				other.alert.call_deferred(false)


## Called by StoryEvents.
func activate() -> void:
	alert()


func hear_noise(at: Vector3, radius: float) -> void:
	if state == State.IDLE and global_position.distance_to(at) <= radius:
		alert()


func _build_body() -> void:
	model.scale = Vector3.ONE * body_scale * randf_range(0.93, 1.07)
	if bodies.is_empty():
		return
	var body := (bodies.pick_random() as PackedScene).instantiate()
	model.add_child(body)
	_anim = body.find_children("*", "AnimationPlayer")[0] as AnimationPlayer
	_skeleton = body.find_children("*", "Skeleton3D")[0] as Skeleton3D
	_neck = _skeleton.find_bone("Neck")
	_pose = ZombiePose.new()
	_skeleton.add_child(_pose)
	for name in LOOPING_ANIMATIONS:
		if _anim.has_animation(name):
			_anim.get_animation(name).loop_mode = Animation.LOOP_LINEAR
	_anim.play("Idle")
	_anim.seek(randf() * 3.0, true)
	var skin: Material = null
	if not skin_colors.is_empty():
		var material := StandardMaterial3D.new()
		material.albedo_color = skin_colors.pick_random()
		material.roughness = 0.8
		skin = material
	for node in body.find_children("*", "MeshInstance3D"):
		var mesh := node as MeshInstance3D
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		_meshes.append(mesh)
		if skin == null:
			continue
		for i in mesh.mesh.get_surface_count():
			var surface := mesh.mesh.surface_get_material(i)
			if surface != null and surface.resource_name == "Skin":
				mesh.set_surface_override_material(i, skin)


func _process_idle(delta: float) -> void:
	_sight_timer -= delta
	if _sight_timer <= 0.0:
		_sight_timer = 0.3
		if _can_see_player():
			alert()
			return
	_wander_timer -= delta
	if _wander_timer <= 0.0:
		_wander_timer = randf_range(3.0, 7.0)
		if randf() < 0.6:
			_wander_target = _home + Vector3(randf_range(-3.0, 3.0), 0.0, randf_range(-3.0, 3.0))
		else:
			_wander_target = global_position
	var to_target := _wander_target - global_position
	to_target.y = 0.0
	_move(to_target.normalized() if to_target.length() > 0.4 else Vector3.ZERO, wander_speed, delta)


func _process_chase(delta: float) -> void:
	if player == null or player.is_dead:
		state = State.IDLE
		_home = global_position
		return
	_repath_timer -= delta
	if _repath_timer <= 0.0:
		_repath_timer = 0.3
		agent.target_position = player.global_position
	var to_player := player.global_position - global_position
	var vertical := absf(to_player.y)
	to_player.y = 0.0
	if to_player.length() <= attack_range and vertical < 1.5:
		_start_attack()
		return
	var speed := chase_speed * (0.25 if _stagger > 0.0 else 1.0)
	_move(_path_direction(), speed, delta)


func _start_attack() -> void:
	state = State.ATTACK
	_attack_timer = attack_windup + attack_recovery
	_attack_hit_done = false
	if _anim != null and _anim.has_animation("Punch"):
		_anim.play("Punch", 0.1)
		# Land the punch's swing at the end of the windup.
		_anim.speed_scale = _anim.get_animation("Punch").length * 0.5 / attack_windup


func _process_attack(delta: float) -> void:
	_move(Vector3.ZERO, 0.0, delta)
	var to_player := player.global_position - global_position
	to_player.y = 0.0
	_face(to_player, delta)
	_attack_timer -= delta
	if not _attack_hit_done and _attack_timer <= attack_recovery:
		_attack_hit_done = true
		attack_sound.stream = ATTACKS.pick_random()
		attack_sound.pitch_scale = voice_pitch * randf_range(0.9, 1.1)
		attack_sound.play()
		if not player.is_dead and to_player.length() <= attack_range + 0.7:
			player.take_damage(attack_damage)
			if knockback > 0.0:
				player.apply_knockback(to_player.normalized() * knockback + Vector3.UP * knockback * 0.4)
	if _attack_timer <= 0.0:
		state = State.CHASE


func _move(direction: Vector3, speed: float, delta: float) -> void:
	var weight := clampf(delta * 6.0, 0.0, 1.0)
	velocity.x = lerpf(velocity.x, direction.x * speed, weight)
	velocity.z = lerpf(velocity.z, direction.z * speed, weight)
	if direction != Vector3.ZERO:
		_face(direction, delta)


func _face(direction: Vector3, delta: float) -> void:
	if direction.length_squared() < 0.0001:
		return
	var target_yaw := atan2(-direction.x, -direction.z)
	rotation.y = lerp_angle(rotation.y, target_yaw, clampf(turn_speed * delta, 0.0, 1.0))


func _path_direction() -> Vector3:
	var direction := agent.get_next_path_position() - global_position
	direction.y = 0.0
	# No path yet (navmesh still baking) or already there: head straight for the player.
	if direction.length() < 0.05:
		direction = player.global_position - global_position
		direction.y = 0.0
	return direction.normalized()


func _can_see_player() -> bool:
	if player == null or player.is_dead:
		return false
	var to_player := player.global_position - global_position
	var distance := to_player.length()
	if distance > sight_range:
		return false
	# Beyond arm's length it has to be roughly facing the player.
	if distance > 4.0 and (-global_basis.z).dot(to_player.normalized()) < 0.2:
		return false
	var from := global_position + Vector3.UP * 1.5
	var query := PhysicsRayQueryParameters3D.create(from, player.global_position + Vector3.UP * 1.3, SIGHT_MASK, [get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	return not hit.is_empty() and hit.collider == player


func _animate(delta: float) -> void:
	if _anim == null:
		return
	var speed := Vector2(velocity.x, velocity.z).length()
	var size := model.scale.y / 0.58
	var reaching := 0.0
	if state == State.ATTACK or _hit_anim_time > 0.0:
		pass  # Punch / RecieveHit play out on their own.
	elif state == State.CHASE and speed > 0.3:
		if chase_animation == "Run":
			_play("Run", speed / (RUN_ANIM_SPEED * size))
		else:
			_play("Walk", speed / (WALK_ANIM_SPEED * size))
			reaching = 1.0
	elif speed > 0.2:
		_play("Walk", speed / (WALK_ANIM_SPEED * size))
	else:
		_play("Idle", 1.0)
		reaching = 0.6 if state == State.CHASE else 0.0
	_pose.reach = lerpf(_pose.reach, reaching, clampf(delta * 5.0, 0.0, 1.0))


func _play(animation: String, speed: float) -> void:
	if _anim.current_animation != animation:
		_anim.play(animation, 0.25)
	_anim.speed_scale = clampf(speed, 0.4, 2.5)


func _update_flash(delta: float) -> void:
	if _flash_timer <= 0.0:
		return
	_flash_timer -= delta
	if _flash_timer <= 0.0:
		for mesh in _meshes:
			mesh.material_overlay = null


func _update_groan(delta: float) -> void:
	_groan_timer -= delta
	if _groan_timer <= 0.0:
		_groan_timer = randf_range(5.0, 10.0) if state != State.IDLE else randf_range(10.0, 22.0)
		_play_groan()


func _play_groan(urgent := false) -> void:
	var now := Time.get_ticks_msec() / 1000.0
	if now < _next_groan_time and not urgent:
		return
	_next_groan_time = now + GROAN_GAP
	groan_sound.stream = GROANS.pick_random()
	groan_sound.pitch_scale = voice_pitch * randf_range(0.9, 1.1)
	groan_sound.play()


func _die(headshot: bool) -> void:
	state = State.DEAD
	died.emit(self)
	Game.register_kill()
	collision.set_deferred("disabled", true)
	set_physics_process(false)
	for mesh in _meshes:
		mesh.material_overlay = null
	groan_sound.stop()
	death_sound.stream = DEATHS.pick_random()
	death_sound.pitch_scale = voice_pitch * randf_range(0.9, 1.1)
	death_sound.play()
	if _pose != null:
		_pose.reach = 0.0
		_pose.head_hidden = headshot
	if headshot:
		var head := (_skeleton.global_transform * _skeleton.get_bone_global_pose(_neck)).origin
		var burst := Effects.spawn(BLOOD_SCENE, self, head + Vector3.UP * 0.15, Vector3.UP)
		burst.scale = Vector3.ONE * 2.0
	var decal := Effects.spawn(BLOOD_DECAL_SCENE, self, global_position + Vector3.UP * 0.3)
	decal.rotation = Vector3(0.0, randf() * TAU, 0.0)
	if _anim != null:
		_anim.play("Death", 0.1)
		_anim.speed_scale = randf_range(0.9, 1.2)
	var tween := create_tween()
	tween.tween_interval(CORPSE_TIME)
	tween.tween_property(model, "position:y", -1.2, 3.0)
	tween.tween_callback(queue_free)
