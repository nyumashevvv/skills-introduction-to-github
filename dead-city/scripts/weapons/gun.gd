class_name Gun
extends Weapon
## Hitscan firearm: pistol (semi-auto) or rifle (automatic).

@export var automatic := false
@export var damage := 25
@export var headshot_multiplier := 2.5
@export var fire_rate := 5.0
@export var max_range := 150.0
@export var base_spread_deg := 0.3
@export var move_spread_deg := 2.5
@export var heat_spread_deg := 1.2
@export var recoil := 0.01
@export var kick_back := 0.05
@export var kick_up := 0.06

var _cooldown := 0.0
var _heat := 0.0
var _flash_left := 0.0

@onready var muzzle: Node3D = $Model/Muzzle
@onready var flash: Node3D = $Model/Flash
@onready var shoot_sound: AudioStreamPlayer = $ShootSound
@onready var empty_sound: AudioStreamPlayer = $EmptySound


func _setup() -> void:
	flash.position = muzzle.position
	flash.visible = false


func _handle_input(held: bool, just_pressed: bool) -> void:
	if just_pressed or (automatic and held):
		_try_fire(just_pressed)


func _update(delta: float) -> void:
	_cooldown = maxf(_cooldown - delta, 0.0)
	_heat = move_toward(_heat, 0.0, delta * 2.0)
	if _flash_left > 0.0:
		_flash_left -= delta
		if _flash_left <= 0.0:
			flash.visible = false


func spread_deg() -> float:
	return base_spread_deg + move_spread_deg * movement_factor + heat_spread_deg * _heat


func _try_fire(just_pressed: bool) -> void:
	if is_reloading or _cooldown > 0.0:
		return
	if ammo <= 0:
		if reserve > 0:
			start_reload()
		elif just_pressed:
			empty_sound.play()
		return

	_cooldown = 1.0 / fire_rate
	ammo -= 1
	_heat = minf(_heat + 0.2, 1.0)
	ammo_changed.emit(self)

	shoot_sound.pitch_scale = randf_range(0.95, 1.05)
	shoot_sound.play()
	flash.visible = true
	flash.rotation.z = randf() * TAU
	_flash_left = 0.05
	kick(kick_back, kick_up)

	var end := fire_ray(aim_direction(spread_deg()), damage, headshot_multiplier, max_range)
	Effects.spawn_tracer(self, muzzle.global_position, end)
	make_noise()
	fired.emit(recoil)
