class_name Weapon
extends Node3D

signal fired(recoil: float)
signal ammo_changed(in_magazine: int, reserve: int)
signal reload_started
signal reload_finished
signal enemy_hit(killed: bool, headshot: bool)

const IMPACT_SCENE := preload("res://scenes/effects/impact.tscn")
## Hitscan collides with the world and enemies, never with the player.
const HIT_MASK := 1 | 4
const WORLD_IMPACT_COLOR := Color(3.0, 2.2, 1.0)
const ENEMY_IMPACT_COLOR := Color(3.0, 0.8, 0.3)

@export var damage := 22
@export var headshot_multiplier := 2.5
@export var fire_rate := 10.0
@export var magazine_size := 30
@export var start_reserve := 120
@export var max_reserve := 240
@export var reload_time := 1.5
@export var max_range := 150.0
@export var base_spread_deg := 0.4
@export var move_spread_deg := 3.0
@export var heat_spread_deg := 1.5
@export var recoil := 0.008

var enabled := true
## 0 when standing still, 1 at full sprint or in the air. Set by the player.
var movement_factor := 0.0
var ammo := 0
var reserve := 0
var is_reloading := false

var _cooldown := 0.0
var _reload_left := 0.0
var _heat := 0.0
var _flash_left := 0.0

@onready var camera: Camera3D = get_parent() as Camera3D
@onready var model: Node3D = $Model
@onready var muzzle: Marker3D = $Model/Muzzle
@onready var flash: Node3D = $Model/Muzzle/Flash
@onready var shoot_sound: AudioStreamPlayer = $ShootSound
@onready var reload_sound: AudioStreamPlayer = $ReloadSound
@onready var empty_sound: AudioStreamPlayer = $EmptySound
@onready var hit_sound: AudioStreamPlayer = $HitSound
@onready var _model_rest := model.position


func _ready() -> void:
	ammo = magazine_size
	reserve = start_reserve
	flash.visible = false


func _process(delta: float) -> void:
	_cooldown = maxf(_cooldown - delta, 0.0)
	_heat = move_toward(_heat, 0.0, delta * 2.0)

	if _flash_left > 0.0:
		_flash_left -= delta
		if _flash_left <= 0.0:
			flash.visible = false

	if is_reloading:
		_reload_left -= delta
		if _reload_left <= 0.0:
			_finish_reload()

	if enabled and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		if Input.is_action_pressed("shoot"):
			_try_fire()
		if Input.is_action_just_pressed("reload"):
			start_reload()

	_animate_model(delta)


func current_spread_deg() -> float:
	return base_spread_deg + move_spread_deg * movement_factor + heat_spread_deg * _heat


func start_reload() -> void:
	if is_reloading or ammo >= magazine_size or reserve <= 0 or not enabled:
		return
	is_reloading = true
	_reload_left = reload_time
	reload_sound.play()
	reload_started.emit()


## Returns false when the reserve is already full.
func add_ammo(amount: int) -> bool:
	if reserve >= max_reserve:
		return false
	reserve = mini(reserve + amount, max_reserve)
	ammo_changed.emit(ammo, reserve)
	return true


func _try_fire() -> void:
	if is_reloading or _cooldown > 0.0:
		return
	if ammo <= 0:
		if reserve > 0:
			start_reload()
		elif Input.is_action_just_pressed("shoot"):
			empty_sound.play()
		return

	_cooldown = 1.0 / fire_rate
	ammo -= 1
	_heat = minf(_heat + 0.15, 1.0)
	ammo_changed.emit(ammo, reserve)

	shoot_sound.play()
	flash.visible = true
	flash.rotation.z = randf() * TAU
	_flash_left = 0.05
	model.position.z += 0.05
	model.rotation.x += 0.04

	_fire_ray()
	fired.emit(recoil)


func _fire_ray() -> void:
	var spread := deg_to_rad(current_spread_deg())
	var basis := camera.global_basis
	var direction := (-basis.z) \
		.rotated(basis.x, randf_range(-spread, spread)) \
		.rotated(basis.y, randf_range(-spread, spread))
	var from := camera.global_position
	var to := from + direction * max_range

	var query := PhysicsRayQueryParameters3D.create(from, to, HIT_MASK)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	var end_point := to
	if not hit.is_empty():
		end_point = hit.position
		var collider: Object = hit.collider
		var impact_color := WORLD_IMPACT_COLOR
		if collider is Enemy:
			var enemy := collider as Enemy
			var headshot := enemy.is_headshot(end_point)
			var amount := roundi(damage * (headshot_multiplier if headshot else 1.0))
			var killed := enemy.take_damage(amount, direction)
			hit_sound.play()
			enemy_hit.emit(killed, headshot)
			impact_color = ENEMY_IMPACT_COLOR
		var impact := Effects.spawn(IMPACT_SCENE, self, end_point, hit.normal) as Impact
		impact.set_color(impact_color)

	Effects.spawn_tracer(self, muzzle.global_position, end_point)


func _finish_reload() -> void:
	is_reloading = false
	var taken := mini(magazine_size - ammo, reserve)
	ammo += taken
	reserve -= taken
	ammo_changed.emit(ammo, reserve)
	reload_finished.emit()


func _animate_model(delta: float) -> void:
	var target_position := _model_rest
	var target_rotation := Vector3.ZERO
	if is_reloading:
		target_position += Vector3(0.0, -0.12, 0.05)
		target_rotation = Vector3(-0.6, 0.3, 0.2)
	target_position.y += sin(Time.get_ticks_msec() * 0.009) * 0.008 * movement_factor
	var weight := clampf(delta * 12.0, 0.0, 1.0)
	model.position = model.position.lerp(target_position, weight)
	model.rotation = model.rotation.lerp(target_rotation, weight)
