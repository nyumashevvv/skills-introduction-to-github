class_name Enemy
extends CharacterBody3D

signal died(enemy: Enemy)

const EXPLOSION_SCENE := preload("res://scenes/effects/explosion.tscn")
const HEALTH_PICKUP_SCENE := preload("res://scenes/pickups/health_pickup.tscn")
const AMMO_PICKUP_SCENE := preload("res://scenes/pickups/ammo_pickup.tscn")
const FLASH_MATERIAL := preload("res://materials/hit_flash.tres")
## Line of sight is blocked by the world and ends on the player.
const SIGHT_MASK := 1 | 2

@export var max_health := 60
@export var move_speed := 3.5
@export var turn_speed := 8.0
@export_group("Attack")
@export var ranged := true
@export var attack_range := 18.0
## Ranged enemies stop approaching and strafe once this close.
@export var preferred_distance := 10.0
@export var attack_damage := 10
@export var attack_cooldown := 1.5
@export var projectile_scene: PackedScene
@export var projectile_speed := 20.0
@export var projectiles_per_attack := 1
@export var projectile_spread_deg := 8.0
@export var aim_error := 0.4
@export_group("Misc")
## Hits higher than this (relative to the feet) are headshots.
@export var head_height := 1.45
@export var score_value := 100
@export_range(0.0, 1.0) var drop_chance := 0.25

var health := 0
var player: Player
var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

var _is_dead := false
var _attack_timer := 0.0
var _repath_timer := 0.0
var _sight_timer := 0.0
var _has_line_of_sight := false
var _strafe_sign := 1.0
var _strafe_timer := 0.0
var _flash_timer := 0.0
var _meshes: Array[MeshInstance3D] = []

@onready var agent: NavigationAgent3D = $NavigationAgent3D
@onready var model: Node3D = $Model
@onready var muzzle: Marker3D = $Model/Muzzle
@onready var attack_sound: AudioStreamPlayer3D = $AttackSound
@onready var _model_rest := model.position


func _ready() -> void:
	health = max_health
	player = get_tree().get_first_node_in_group("player") as Player
	_attack_timer = randf_range(0.6, attack_cooldown + 0.6)
	_strafe_sign = 1.0 if randf() < 0.5 else -1.0
	for node in model.find_children("*", "MeshInstance3D"):
		_meshes.append(node as MeshInstance3D)


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	_update_flash(delta)
	model.position = model.position.lerp(_model_rest, clampf(delta * 10.0, 0.0, 1.0))

	if player == null or player.is_dead:
		velocity.x = move_toward(velocity.x, 0.0, move_speed * delta * 4.0)
		velocity.z = move_toward(velocity.z, 0.0, move_speed * delta * 4.0)
		move_and_slide()
		return

	var to_player := player.global_position - global_position
	to_player.y = 0.0
	var distance := to_player.length()

	_sight_timer -= delta
	if _sight_timer <= 0.0:
		_sight_timer = 0.2
		_has_line_of_sight = _check_line_of_sight()

	_repath_timer -= delta
	if _repath_timer <= 0.0:
		_repath_timer = 0.25
		agent.target_position = player.global_position

	var in_attack_range := distance <= attack_range and _has_line_of_sight
	var move_dir := Vector3.ZERO
	var speed := move_speed
	if not in_attack_range or (ranged and distance > preferred_distance):
		move_dir = _get_path_direction()
	elif ranged:
		_strafe_timer -= delta
		if _strafe_timer <= 0.0:
			_strafe_timer = randf_range(1.0, 2.5)
			_strafe_sign = -_strafe_sign
		move_dir = to_player.normalized().cross(Vector3.UP) * _strafe_sign
		speed *= 0.5

	var weight := clampf(delta * 8.0, 0.0, 1.0)
	velocity.x = lerpf(velocity.x, move_dir.x * speed, weight)
	velocity.z = lerpf(velocity.z, move_dir.z * speed, weight)
	_face(to_player if in_attack_range or move_dir == Vector3.ZERO else move_dir, delta)
	move_and_slide()

	_attack_timer -= delta
	if in_attack_range and _attack_timer <= 0.0:
		_attack_timer = attack_cooldown
		_attack()


func is_headshot(point: Vector3) -> bool:
	return point.y - global_position.y >= head_height


## Returns true when this hit killed the enemy.
func take_damage(amount: int, direction: Vector3) -> bool:
	if _is_dead:
		return false
	health -= amount
	_flash_timer = 0.08
	for mesh in _meshes:
		mesh.material_overlay = FLASH_MATERIAL
	var push := Vector3(direction.x, 0.0, direction.z).normalized()
	velocity += push * 1.5
	# Getting shot reveals the shooter.
	_has_line_of_sight = true
	if health <= 0:
		_die()
		return true
	return false


func _get_path_direction() -> Vector3:
	var direction := agent.get_next_path_position() - global_position
	direction.y = 0.0
	# No path yet (navmesh still baking) or already there: head straight for the player.
	if direction.length() < 0.05:
		direction = player.global_position - global_position
		direction.y = 0.0
	return direction.normalized()


func _check_line_of_sight() -> bool:
	var target := player.global_position + Vector3.UP * 1.3
	var query := PhysicsRayQueryParameters3D.create(muzzle.global_position, target, SIGHT_MASK, [get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	return not hit.is_empty() and hit.collider == player


func _face(direction: Vector3, delta: float) -> void:
	if direction.length_squared() < 0.0001:
		return
	var target_yaw := atan2(-direction.x, -direction.z)
	rotation.y = lerp_angle(rotation.y, target_yaw, clampf(turn_speed * delta, 0.0, 1.0))


func _attack() -> void:
	attack_sound.play()
	if not ranged:
		model.position.z -= 0.4
		player.take_damage(attack_damage)
		return

	var target := player.global_position + Vector3.UP * 1.2
	target += Vector3(randf_range(-aim_error, aim_error), randf_range(-aim_error, aim_error) * 0.5, randf_range(-aim_error, aim_error))
	var aim := (target - muzzle.global_position).normalized()
	model.position.z += 0.15
	for i in projectiles_per_attack:
		var offset := (i - (projectiles_per_attack - 1) / 2.0) * deg_to_rad(projectile_spread_deg)
		var projectile := projectile_scene.instantiate() as Projectile
		get_tree().current_scene.add_child(projectile)
		projectile.launch(muzzle.global_position, aim.rotated(Vector3.UP, offset), projectile_speed, attack_damage)


func _update_flash(delta: float) -> void:
	if _flash_timer <= 0.0:
		return
	_flash_timer -= delta
	if _flash_timer <= 0.0:
		for mesh in _meshes:
			mesh.material_overlay = null


func _die() -> void:
	_is_dead = true
	died.emit(self)
	Effects.spawn(EXPLOSION_SCENE, self, global_position + Vector3.UP)
	if randf() < drop_chance:
		var low_health := player != null and player.health < player.max_health / 2
		var scene := HEALTH_PICKUP_SCENE if low_health or randf() < 0.4 else AMMO_PICKUP_SCENE
		Effects.spawn(scene, self, global_position + Vector3.UP * 0.6)
	queue_free()
