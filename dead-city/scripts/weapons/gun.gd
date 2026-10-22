class_name Gun
extends Weapon
## Hitscan firearm: pistol (semi-auto), rifle (automatic) or pump shotgun (pellets).

const PUMP_TIME := 0.3

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
@export_group("Shotgun")
## Rays per shot; each does `damage`.
@export var pellets := 1
@export var pellet_spread_deg := 0.0
## Distance range (m) over which damage drops to a quarter. (0, 0) = no falloff.
@export var falloff := Vector2.ZERO
## Seconds after a shot when the pump is racked (PumpSound plays). 0 = no pump.
@export var pump_delay := 0.0

var _cooldown := 0.0
var _heat := 0.0
var _flash_left := 0.0
var _pump_wait := 0.0
var _pump_left := 0.0

@onready var muzzle: Node3D = $Model/Muzzle
@onready var flash: Node3D = $Model/Flash
@onready var shoot_sound: AudioStreamPlayer = $ShootSound
@onready var empty_sound: AudioStreamPlayer = $EmptySound
@onready var pump_sound: AudioStreamPlayer = get_node_or_null("PumpSound")


func _setup() -> void:
	# The hands hold the gun about a third of the way back from the muzzle.
	pivot = muzzle.position * Vector3(1.0, 1.0, 0.55) + Vector3(0.0, -0.06, 0.0)
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
	if _pump_wait > 0.0:
		_pump_wait -= delta
		if _pump_wait <= 0.0:
			_pump_left = PUMP_TIME
			if pump_sound != null:
				pump_sound.play()
	if _pump_left > 0.0:
		_pump_left = maxf(_pump_left - delta, 0.0)
		# Rack the pump: the gun jerks back and down, then returns.
		pose_offset = Vector3(0.0, -0.025, 0.07) * sin((1.0 - _pump_left / PUMP_TIME) * PI)


func spread_deg() -> float:
	return base_spread_deg + move_spread_deg * movement_factor + heat_spread_deg * _heat


func _try_fire(just_pressed: bool) -> void:
	# A pump gun can interrupt its shell-by-shell reload to shoot.
	if is_reloading and reload_per_round and ammo > 0 and just_pressed:
		cancel_reload()
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
	if pump_delay > 0.0:
		_pump_wait = pump_delay

	var spread := spread_deg() + (pellet_spread_deg if pellets > 1 else 0.0)
	for i in pellets:
		# Only some pellets leave sparks and tracers, so a blast doesn't spawn dozens of effects.
		var end := fire_ray(aim_direction(spread), damage, headshot_multiplier, max_range, falloff, i % 2 == 0)
		if i % 3 == 0:
			Effects.spawn_tracer(self, muzzle.global_position, end)
	make_noise()
	fired.emit(recoil)
