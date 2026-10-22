class_name Thrower
extends Weapon
## Hand grenades: one in the hand, the rest in the pouch. Thrown in an arc; it bounces and explodes after its fuse.

@export var grenade_scene: PackedScene
@export var throw_speed := 15.0
@export var damage := 260
@export var blast_radius := 6.5

var _throw_left := 0.0

@onready var throw_sound: AudioStreamPlayer = $ThrowSound


func _handle_input(_held: bool, just_pressed: bool) -> void:
	if not just_pressed or is_reloading or _throw_left > 0.0:
		return
	if ammo <= 0:
		if reserve > 0:
			start_reload()
		return
	_throw_left = 0.35


func _update(delta: float) -> void:
	model.visible = ammo > 0 or is_reloading
	if _throw_left <= 0.0:
		pose_offset = Vector3.ZERO
		pose_rotation = Vector3.ZERO
		return
	_throw_left = maxf(_throw_left - delta, 0.0)
	var t := 1.0 - _throw_left / 0.35
	# Wind up behind the shoulder, then snap forward and let go.
	var swing := sin(t * PI)
	pose_offset = Vector3(0.0, 0.1 * swing, 0.15 * (1.0 - t) - 0.2 * t) * swing
	pose_rotation = Vector3(0.9 * swing * (1.0 - 2.0 * t), 0.0, 0.0)
	if _throw_left <= 0.0:
		_release()


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
	if ammo == 0 and reserve > 0:
		start_reload()
