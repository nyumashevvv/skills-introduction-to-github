class_name Weapon
extends Node3D
## Base class for everything the player holds: ammo, reloading, equip and idle animation.
## Subclasses implement [method _handle_input] and may drive [member pose_offset]/[member pose_rotation].

signal fired(recoil: float)
signal ammo_changed(weapon: Weapon)
signal reload_changed(weapon: Weapon, reloading: bool)
signal enemy_hit(killed: bool, headshot: bool)

const IMPACT_SCENE := preload("res://scenes/effects/impact.tscn")
## Bullets and blades hit the world and zombies, never the player.
const HIT_MASK := 1 | 4

@export var id := ""
@export var display_name := ""
@export var slot := 1
## Empty for weapons without ammo (the knife).
@export var ammo_type := ""
@export var magazine_size := 0
@export var max_reserve := 0
@export var reload_time := 1.5
@export var equip_time := 0.35
## Zombies within this radius hear the weapon being used.
@export var noise_radius := 0.0

var owned := false
var active := false
var ammo := 0
var reserve := 0
var is_reloading := false
## 0 when standing still, 1 at full sprint or in the air. Set by the holder.
var movement_factor := 0.0
## Extra pose a subclass wants this frame (e.g. a knife swing).
var pose_offset := Vector3.ZERO
var pose_rotation := Vector3.ZERO

var _reload_left := 0.0
var _equip_left := 0.0

@onready var camera: Camera3D = get_parent().get_parent() as Camera3D
@onready var model: Node3D = $Model
@onready var reload_sound: AudioStreamPlayer = get_node_or_null("ReloadSound")
@onready var _model_rest := model.position


func _process(delta: float) -> void:
	if not visible:
		return
	if is_reloading:
		_reload_left -= delta
		if _reload_left <= 0.0:
			_finish_reload()
	_equip_left = maxf(_equip_left - delta, 0.0)
	if active and _equip_left <= 0.0 and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_handle_input(Input.is_action_pressed("shoot"), Input.is_action_just_pressed("shoot"))
		if Input.is_action_just_pressed("reload"):
			start_reload()
	_update(delta)
	_animate(delta)


## Called every frame while the weapon is usable.
func _handle_input(_held: bool, _just_pressed: bool) -> void:
	pass


## Per-frame hook for cooldowns and effects.
func _update(_delta: float) -> void:
	pass


## Current inaccuracy in degrees, shown by the crosshair.
func spread_deg() -> float:
	return 0.0


func uses_ammo() -> bool:
	return ammo_type != ""


func equip() -> void:
	visible = true
	_equip_left = equip_time
	model.position = _model_rest + Vector3(0.0, -0.35, 0.1)
	model.rotation = Vector3(-0.6, 0.0, 0.0)


func unequip() -> void:
	visible = false
	active = false
	if is_reloading:
		is_reloading = false
		reload_changed.emit(self, false)


func start_reload() -> void:
	if not uses_ammo() or is_reloading or ammo >= magazine_size or reserve <= 0:
		return
	is_reloading = true
	_reload_left = reload_time
	if reload_sound != null:
		reload_sound.play()
	reload_changed.emit(self, true)


## Returns false when the reserve is already full.
func add_ammo(amount: int) -> bool:
	if not uses_ammo() or reserve >= max_reserve:
		return false
	reserve = mini(reserve + amount, max_reserve)
	ammo_changed.emit(self)
	return true


func make_noise() -> void:
	if noise_radius > 0.0:
		get_tree().call_group("zombies", "hear_noise", global_position, noise_radius)


## Casts a bullet/blade ray from the camera. Returns the end point.
func fire_ray(direction: Vector3, damage: int, headshot_multiplier: float, max_range: float) -> Vector3:
	var from := camera.global_position
	var query := PhysicsRayQueryParameters3D.create(from, from + direction * max_range, HIT_MASK)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		return from + direction * max_range
	var point: Vector3 = hit.position
	var collider: Object = hit.collider
	if collider is Zombie:
		var zombie := collider as Zombie
		var headshot := zombie.is_headshot(point)
		var amount := roundi(damage * (headshot_multiplier if headshot else 1.0))
		var killed := zombie.take_damage(amount, direction, point)
		enemy_hit.emit(killed, headshot)
	else:
		Effects.spawn(IMPACT_SCENE, self, point, hit.normal)
	return point


func aim_direction(spread_degrees: float) -> Vector3:
	var spread := deg_to_rad(spread_degrees)
	var basis := camera.global_basis
	return (-basis.z) \
		.rotated(basis.x, randf_range(-spread, spread)) \
		.rotated(basis.y, randf_range(-spread, spread))


## Immediately pushes the model back; it springs back to rest in [method _animate].
func kick(back: float, up: float) -> void:
	model.position.z += back
	model.rotation.x += up


func _finish_reload() -> void:
	is_reloading = false
	var taken := mini(magazine_size - ammo, reserve)
	ammo += taken
	reserve -= taken
	ammo_changed.emit(self)
	reload_changed.emit(self, false)


func _animate(delta: float) -> void:
	var target_position := _model_rest + pose_offset
	var target_rotation := pose_rotation
	if is_reloading:
		target_position += Vector3(-0.05, -0.1, 0.05)
		target_rotation += Vector3(-0.5, 0.4, 0.5)
	var time := Time.get_ticks_msec() * 0.001
	target_position.x += sin(time * 7.0) * 0.006 * movement_factor
	target_position.y += absf(cos(time * 7.0)) * 0.01 * movement_factor + sin(time * 1.5) * 0.002
	var weight := clampf(delta * 12.0, 0.0, 1.0)
	model.position = model.position.lerp(target_position, weight)
	model.rotation = model.rotation.lerp(target_rotation, weight)
