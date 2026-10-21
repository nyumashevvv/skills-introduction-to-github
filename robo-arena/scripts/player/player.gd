class_name Player
extends CharacterBody3D

signal health_changed(current: int, maximum: int)
signal damaged
signal died

@export var walk_speed := 6.0
@export var sprint_speed := 9.5
@export var jump_velocity := 5.2
@export var acceleration := 12.0
@export var air_acceleration := 3.0
@export var mouse_sensitivity := 0.0025
@export var max_health := 100

var health := 0
var is_dead := false
var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

var _bob_time := 0.0

@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D
@onready var weapon: Weapon = $Head/Camera3D/Weapon
@onready var hurt_sound: AudioStreamPlayer = $HurtSound
@onready var pickup_sound: AudioStreamPlayer = $PickupSound


func _ready() -> void:
	health = max_health
	weapon.fired.connect(_on_weapon_fired)


func _unhandled_input(event: InputEvent) -> void:
	if is_dead or Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return
	if event is InputEventMouseMotion:
		var motion := event as InputEventMouseMotion
		rotate_y(-motion.relative.x * mouse_sensitivity)
		head.rotate_x(-motion.relative.y * mouse_sensitivity)
		head.rotation.x = clampf(head.rotation.x, deg_to_rad(-89.0), deg_to_rad(89.0))


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta

	var input_dir := Vector2.ZERO
	if not is_dead:
		input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		if Input.is_action_just_pressed("jump") and is_on_floor():
			velocity.y = jump_velocity

	var sprinting := Input.is_action_pressed("sprint") and input_dir.y < 0.0
	var speed := sprint_speed if sprinting else walk_speed
	var direction := (transform.basis * Vector3(input_dir.x, 0.0, input_dir.y)).normalized()
	var accel := acceleration if is_on_floor() else air_acceleration
	velocity.x = lerpf(velocity.x, direction.x * speed, accel * delta)
	velocity.z = lerpf(velocity.z, direction.z * speed, accel * delta)
	move_and_slide()

	var horizontal_speed := Vector2(velocity.x, velocity.z).length()
	weapon.movement_factor = clampf(horizontal_speed / sprint_speed, 0.0, 1.0) if is_on_floor() else 1.0
	_update_head_bob(delta, horizontal_speed)


func take_damage(amount: int) -> void:
	if is_dead:
		return
	health = maxi(health - amount, 0)
	health_changed.emit(health, max_health)
	damaged.emit()
	hurt_sound.play()
	if health == 0:
		_die()


## Returns false when already at full health, so the pickup stays on the map.
func heal(amount: int) -> bool:
	if is_dead or health >= max_health:
		return false
	health = mini(health + amount, max_health)
	health_changed.emit(health, max_health)
	return true


func play_pickup_sound() -> void:
	pickup_sound.play()


func _update_head_bob(delta: float, horizontal_speed: float) -> void:
	var target_y := 0.0
	if is_on_floor() and horizontal_speed > 1.0:
		_bob_time += delta * horizontal_speed * 1.8
		target_y = sin(_bob_time) * 0.04
	camera.position.y = lerpf(camera.position.y, target_y, 10.0 * delta)


func _on_weapon_fired(recoil: float) -> void:
	head.rotation.x = clampf(head.rotation.x + recoil, deg_to_rad(-89.0), deg_to_rad(89.0))
	rotate_y(randf_range(-recoil, recoil) * 0.4)


func _die() -> void:
	is_dead = true
	weapon.enabled = false
	var tween := create_tween().set_parallel()
	tween.tween_property(head, "position:y", 0.35, 0.7).set_ease(Tween.EASE_IN)
	tween.tween_property(head, "rotation:z", 0.7, 0.7)
	died.emit()
