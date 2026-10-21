class_name MeleeWeapon
extends Weapon
## Knife: silent, never runs out, alternates left/right slashes.

@export var damage := 45
@export var headshot_multiplier := 1.6
@export var reach := 2.2
@export var swing_time := 0.45
## Seconds into the swing when the blade connects.
@export var hit_time := 0.12

var _swing_left := 0.0
var _hit_done := true
var _side := 1.0

@onready var swing_sound: AudioStreamPlayer = $SwingSound
@onready var stab_sound: AudioStreamPlayer = $StabSound


func _handle_input(held: bool, _just_pressed: bool) -> void:
	if held and _swing_left <= 0.0:
		_swing_left = swing_time
		_hit_done = false
		_side = -_side
		swing_sound.pitch_scale = randf_range(0.9, 1.1)
		swing_sound.play()


func _update(delta: float) -> void:
	if _swing_left <= 0.0:
		pose_offset = Vector3.ZERO
		pose_rotation = Vector3.ZERO
		return
	_swing_left = maxf(_swing_left - delta, 0.0)
	var elapsed := swing_time - _swing_left
	if not _hit_done and elapsed >= hit_time:
		_hit_done = true
		_strike()
	# Fast slash across the screen, then a slower return.
	var t := elapsed / swing_time
	var arc := sin(minf(t * 2.5, 1.0) * PI) if t < 0.4 else (1.0 - t) / 0.6 * 0.3
	var sweep := lerpf(1.0, -1.0, minf(t * 2.5, 1.0)) * _side
	pose_offset = Vector3(-0.2 * sweep, 0.06 * arc, -0.18 * arc)
	pose_rotation = Vector3(-0.4 * arc, 0.9 * sweep * arc, 0.7 * _side * arc)


func _strike() -> void:
	# A small fan of rays makes the knife forgiving to aim.
	for angle: float in [0.0, -10.0, 10.0]:
		var direction := (-camera.global_basis.z).rotated(camera.global_basis.y, deg_to_rad(angle))
		var from := camera.global_position
		var query := PhysicsRayQueryParameters3D.create(from, from + direction * reach, HIT_MASK)
		var hit := get_world_3d().direct_space_state.intersect_ray(query)
		if hit.is_empty():
			continue
		if hit.collider is Zombie or angle == 0.0:
			fire_ray(direction, damage, headshot_multiplier, reach)
			stab_sound.play()
			fired.emit(0.0)
			return
