class_name Thrower
extends Weapon
## Hand grenades: one in the hand, the rest in the pouch. Thrown in an arc; it bounces and explodes after its fuse.

@export var grenade_scene: PackedScene
@export var throw_speed := 15.0
@export var damage := 260
@export var blast_radius := 6.5

const THROW_TIME := 0.5
## Wind-up share of the throw; the rest is the snap forward.
const WIND_UP := 0.4
## The grenade leaves the hand here, as the arm passes the head; the rest is follow-through.
const RELEASE_AT := 0.72
## The arm turns around the right shoulder (below, right of and behind the camera).
const SHOULDER := Vector3(0.22, -0.38, 0.2)

var _throw_left := 0.0
var _released := false

@onready var throw_sound: AudioStreamPlayer = $ThrowSound


func _handle_input(_held: bool, just_pressed: bool) -> void:
	if not just_pressed or is_reloading or _throw_left > 0.0:
		return
	if ammo <= 0:
		if reserve > 0:
			start_reload()
		return
	_throw_left = THROW_TIME
	_released = false


func _setup() -> void:
	pivot = SHOULDER


func _update(delta: float) -> void:
	model.visible = (ammo > 0 and not _released) or is_reloading
	if _throw_left <= 0.0:
		pose_offset = Vector3.ZERO
		pose_rotation = Vector3.ZERO
		return
	_throw_left = maxf(_throw_left - delta, 0.0)
	var t := 1.0 - _throw_left / THROW_TIME
	# Overarm: raise the hand up and back over the shoulder, then whip it forward and down, letting go mid-swing.
	if t < WIND_UP:
		var u := ease(t / WIND_UP, 0.5)
		pose_rotation = Vector3(0.6 * u, 0.0, -0.15 * u)
		pose_offset = Vector3(0.0, 0.03, 0.05) * u
	else:
		var v := ease((t - WIND_UP) / (1.0 - WIND_UP), 1.6)
		pose_rotation = Vector3(0.6 - 1.3 * v, 0.0, -0.15 + 0.1 * v)
		pose_offset = Vector3(-0.03 * v, 0.03 - 0.06 * v, 0.05 - 0.2 * v)
	if t >= RELEASE_AT and not _released:
		_released = true
		_release()
	if _throw_left <= 0.0:
		# Follow-through done: the next grenade comes out of the pouch.
		_released = false
		if ammo == 0 and reserve > 0:
			start_reload()


func spread_deg() -> float:
	return 0.0


func _release() -> void:
	ammo -= 1
	ammo_changed.emit(self)
	throw_sound.play()
	var grenade := grenade_scene.instantiate() as Grenade
	get_tree().current_scene.add_child(grenade)
	var forward := -camera.global_basis.z
	grenade.global_position = camera.global_position + forward * 0.6 + camera.global_basis.x * 0.15
	grenade.linear_velocity = forward * throw_speed + Vector3.UP * 3.5
	grenade.angular_velocity = Vector3(randf_range(-8, 8), randf_range(-8, 8), randf_range(-8, 8))
	grenade.setup(damage, blast_radius, self)
