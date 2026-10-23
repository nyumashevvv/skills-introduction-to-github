class_name Player
extends CharacterBody3D

signal health_changed(current: int, maximum: int)
signal damaged
signal died
signal interact_prompt_changed(text: String)
signal stamina_changed(current: float, maximum: float, winded: bool)

const INTERACT_DISTANCE := 2.6
const INTERACT_MASK := 1
const STAND_HEIGHT := 1.8
const CROUCH_HEIGHT := 1.1
const HEAD_STAND := 1.6
const HEAD_CROUCH := 0.95

@export var walk_speed := 5.5
@export var sprint_speed := 8.5
@export var jump_velocity := 5.0
@export var acceleration := 12.0
@export var air_acceleration := 3.0
@export var mouse_sensitivity := 0.0025
@export var max_health := 100
@export var crouch_speed := 2.6
@export_group("Stamina")
@export var max_stamina := 100.0
## Spent per second of sprinting and per jump.
@export var sprint_cost := 20.0
@export var jump_cost := 15.0
@export var stamina_regen := 22.0
## Seconds after spending stamina before it starts to come back.
@export var regen_delay := 0.9
## Once drained, sprinting is blocked until stamina is back to this much.
@export var winded_until := 35.0

var health := 0
var is_dead := false
var keys: Array[String] = []
var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

var _bob_time := 0.0
var _shake := 0.0
var _knockback := Vector3.ZERO
## Visual recoil: the view jumps up on a shot and springs back (the aim keeps only part of it).
var _punch := 0.0
var _prompt := ""
var stamina := 0.0
var crouching := false
var _winded := false
var _regen_wait := 0.0
var _shape: CapsuleShape3D

@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D
@onready var holder: WeaponHolder = $Head/Camera3D/WeaponHolder
@onready var flashlight: SpotLight3D = $Head/Camera3D/Flashlight
@onready var hurt_sound: AudioStreamPlayer = $HurtSound
@onready var pickup_sound: AudioStreamPlayer = $PickupSound
@onready var key_sound: AudioStreamPlayer = $KeySound
@onready var footstep_sound: AudioStreamPlayer = $FootstepSound
@onready var flashlight_sound: AudioStreamPlayer = $FlashlightSound
@onready var collision: CollisionShape3D = $CollisionShape3D


func _ready() -> void:
	health = max_health
	stamina = max_stamina
	_shape = collision.shape.duplicate() as CapsuleShape3D
	collision.shape = _shape
	holder.fired.connect(_on_weapon_fired)
	flashlight.visible = false


func _unhandled_input(event: InputEvent) -> void:
	if is_dead or Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return
	if event is InputEventMouseMotion:
		var motion := event as InputEventMouseMotion
		var sensitivity: float = mouse_sensitivity * float(Settings.get_value("sensitivity"))
		rotate_y(-motion.relative.x * sensitivity)
		head.rotate_x(-motion.relative.y * sensitivity)
		head.rotation.x = clampf(head.rotation.x, deg_to_rad(-89.0), deg_to_rad(89.0))
		holder.add_sway(motion.relative)
	elif event.is_action_pressed("flashlight"):
		flashlight.visible = not flashlight.visible
		flashlight_sound.play()
	elif event.is_action_pressed("interact"):
		var target := _find_interactable()
		if target != null:
			target.call("interact", self)


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta

	var input_dir := Vector2.ZERO
	if not is_dead:
		input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		if Input.is_action_just_pressed("jump") and is_on_floor() and stamina >= jump_cost:
			if crouching:
				_set_crouch(false)
			if not crouching:
				velocity.y = jump_velocity
				_spend(jump_cost)
	_update_crouch(delta)

	var sprinting := Input.is_action_pressed("sprint") and input_dir.y < 0.0 and not _winded and not crouching \
		and is_on_floor() and not is_dead
	if sprinting:
		_spend(sprint_cost * delta)
	_update_stamina(delta)
	var speed := sprint_speed if sprinting else (crouch_speed if crouching else walk_speed)
	var direction := (transform.basis * Vector3(input_dir.x, 0.0, input_dir.y)).normalized()
	var accel := acceleration if is_on_floor() else air_acceleration
	velocity.x = lerpf(velocity.x, direction.x * speed, accel * delta) + _knockback.x
	velocity.z = lerpf(velocity.z, direction.z * speed, accel * delta) + _knockback.z
	velocity.y += _knockback.y
	_knockback = Vector3.ZERO
	move_and_slide()

	var horizontal_speed := Vector2(velocity.x, velocity.z).length()
	holder.movement_factor = clampf(horizontal_speed / sprint_speed, 0.0, 1.0) if is_on_floor() else 1.0
	_update_head_bob(delta, horizontal_speed)
	_update_shake(delta)
	_update_interact_prompt()


func _spend(amount: float) -> void:
	stamina = maxf(stamina - amount, 0.0)
	_regen_wait = regen_delay
	if stamina <= 0.0:
		_winded = true


func _update_stamina(delta: float) -> void:
	var before := stamina
	if _regen_wait > 0.0:
		_regen_wait -= delta
	else:
		stamina = minf(stamina + stamina_regen * delta, max_stamina)
	if _winded and stamina >= winded_until:
		_winded = false
	if stamina != before or _winded:
		stamina_changed.emit(stamina, max_stamina, _winded)


## Hold C or Ctrl to crouch; the player stays down while there is no room to stand.
func _update_crouch(delta: float) -> void:
	var want := Input.is_action_pressed("crouch") and not is_dead
	if want != crouching:
		_set_crouch(want)
	var target := HEAD_CROUCH if crouching else HEAD_STAND
	if not is_dead:
		head.position.y = move_toward(head.position.y, target, delta * 5.0)


func _set_crouch(down: bool) -> void:
	if not down and not _room_to_stand():
		return
	crouching = down
	_shape.height = CROUCH_HEIGHT if down else STAND_HEIGHT
	collision.position.y = _shape.height * 0.5


func _room_to_stand() -> bool:
	var query := PhysicsShapeQueryParameters3D.new()
	var probe := CapsuleShape3D.new()
	probe.radius = _shape.radius - 0.05
	probe.height = STAND_HEIGHT
	query.shape = probe
	query.transform = Transform3D(Basis.IDENTITY, global_position + Vector3(0.0, STAND_HEIGHT * 0.5 + 0.05, 0.0))
	query.collision_mask = collision_mask
	query.exclude = [get_rid()]
	return get_world_3d().direct_space_state.intersect_shape(query, 1).is_empty()


func take_damage(amount: int) -> void:
	if is_dead or amount <= 0:
		return
	amount = maxi(roundi(amount * Game.tuning("damage")), 1)
	health = maxi(health - amount, 0)
	health_changed.emit(health, max_health)
	damaged.emit()
	hurt_sound.play()
	shake(0.25)
	if health == 0:
		_die()


## Returns false when already at full health, so the pickup stays on the map.
func heal(amount: int) -> bool:
	if is_dead or health >= max_health:
		return false
	health = mini(health + amount, max_health)
	health_changed.emit(health, max_health)
	return true


func apply_knockback(force: Vector3) -> void:
	_knockback += force


func shake(amount: float) -> void:
	_shake = maxf(_shake, amount)


func add_key(id: String) -> void:
	if not keys.has(id):
		keys.append(id)
	key_sound.play()


func has_key(id: String) -> bool:
	return keys.has(id)


func play_pickup_sound() -> void:
	pickup_sound.play()


func get_state() -> Dictionary:
	return {"health": health, "weapons": holder.get_state()}


func apply_state(state: Dictionary) -> void:
	health = clampi(int(state.get("health", max_health)), 1, max_health)
	holder.apply_state(state.get("weapons", {}))
	health_changed.emit(health, max_health)


func _find_interactable() -> Object:
	var from := camera.global_position
	var to := from - camera.global_basis.z * INTERACT_DISTANCE
	var query := PhysicsRayQueryParameters3D.create(from, to, INTERACT_MASK, [get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		return null
	var collider: Object = hit.collider
	return collider if collider.has_method("interact") else null


func _update_interact_prompt() -> void:
	var text := ""
	if not is_dead:
		var target := _find_interactable()
		if target != null:
			text = target.call("get_prompt", self)
	if text != _prompt:
		_prompt = text
		interact_prompt_changed.emit(text)


func _update_head_bob(delta: float, horizontal_speed: float) -> void:
	var target_y := 0.0
	if is_on_floor() and horizontal_speed > 1.0:
		var before := sin(_bob_time)
		_bob_time += delta * horizontal_speed * 1.8
		target_y = sin(_bob_time) * 0.04
		if before > 0.0 and sin(_bob_time) <= 0.0:
			footstep_sound.pitch_scale = randf_range(0.85, 1.15)
			footstep_sound.play()
	camera.position.y = lerpf(camera.position.y, target_y, 10.0 * delta)


func _update_shake(delta: float) -> void:
	_punch = lerpf(_punch, 0.0, clampf(delta * 9.0, 0.0, 1.0))
	camera.rotation.x = _punch
	_shake = move_toward(_shake, 0.0, delta * 1.5)
	camera.h_offset = randf_range(-1.0, 1.0) * _shake * 0.08
	camera.v_offset = randf_range(-1.0, 1.0) * _shake * 0.08


func _on_weapon_fired(recoil: float) -> void:
	head.rotation.x = clampf(head.rotation.x + recoil, deg_to_rad(-89.0), deg_to_rad(89.0))
	rotate_y(randf_range(-recoil, recoil) * 0.4)
	# Heavy guns (revolver, shotgun, sniper) throw the view up and shake it.
	if recoil >= 0.04:
		_punch = minf(_punch + recoil * 2.2, 0.35)
		shake(recoil * 3.0)


func _die() -> void:
	is_dead = true
	holder.set_enabled(false)
	var tween := create_tween().set_parallel()
	tween.tween_property(head, "position:y", 0.35, 0.7).set_ease(Tween.EASE_IN)
	tween.tween_property(head, "rotation:z", 0.7, 0.7)
	died.emit()
