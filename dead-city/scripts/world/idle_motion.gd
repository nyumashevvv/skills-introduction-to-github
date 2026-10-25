extends Node3D
## A little life for props: sways (hanging banners), bobs (balloons) or spins (turntables, ceiling fans).

@export var sway_degrees := 0.0
@export var bob_height := 0.0
@export var spin_speed := 0.0
@export var period := 3.0

var _rest_rotation := Vector3.ZERO
var _rest_y := 0.0
var _phase := 0.0


func _ready() -> void:
	_rest_rotation = rotation
	_rest_y = position.y
	_phase = randf() * TAU


func _process(delta: float) -> void:
	var wave := sin(Time.get_ticks_msec() / 1000.0 * TAU / period + _phase)
	if sway_degrees != 0.0:
		rotation.z = _rest_rotation.z + deg_to_rad(sway_degrees) * wave
		rotation.x = _rest_rotation.x + deg_to_rad(sway_degrees) * 0.4 * cos(wave * 2.0)
	if bob_height != 0.0:
		position.y = _rest_y + bob_height * wave
	if spin_speed != 0.0:
		rotation.y += spin_speed * delta
