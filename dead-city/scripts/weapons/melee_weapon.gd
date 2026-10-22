class_name MeleeWeapon
extends Weapon
## Knife: silent, never runs out, alternates left/right slashes. Kills outright and without a sound
## when the zombie has not noticed you or is struck in the back; otherwise knocks it off balance.

const STEALTH_HINT := "ЛКМ — тихое убийство"

@export var damage := 45
@export var headshot_multiplier := 1.6
@export var reach := 2.2
@export var swing_time := 0.45
## Seconds into the swing when the blade connects.
@export var hit_time := 0.12

var _swing_left := 0.0
var _hit_done := true
var _side := 1.0
## The swing is an overhead stab (a takedown) rather than a slash.
var _stab := false
var _hint_timer := 0.0

@onready var swing_sound: AudioStreamPlayer = $SwingSound
@onready var stab_sound: AudioStreamPlayer = $StabSound


func _handle_input(held: bool, _just_pressed: bool) -> void:
	if held and _swing_left <= 0.0:
		_swing_left = swing_time
		_hit_done = false
		_side = -_side
		_stab = _target_for_takedown() != null
		swing_sound.pitch_scale = randf_range(0.9, 1.1)
		swing_sound.play()


func _update(delta: float) -> void:
	_hint_timer -= delta
	if _hint_timer <= 0.0:
		_hint_timer = 0.1
		_show_hint(_target_for_takedown() != null and _swing_left <= 0.0)
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
	if _stab:
		# Raise, then drive the blade forward and down.
		pose_offset = Vector3(-0.08 * arc, 0.12 * arc - 0.1 * t, -0.3 * arc)
		pose_rotation = Vector3(-1.0 * arc, 0.2 * arc, 0.0)
		return
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
		if hit.collider is Zombie:
			_hit_zombie(hit.collider as Zombie, direction, hit.position)
			return
		if angle == 0.0:
			fire_ray(direction, damage, headshot_multiplier, reach)
			stab_sound.play()
			fired.emit(0.0)
			return


func _hit_zombie(zombie: Zombie, direction: Vector3, point: Vector3) -> void:
	stab_sound.play()
	fired.emit(0.0)
	if zombie.can_be_stealth_killed(direction):
		var was_boss := zombie is Boss
		zombie.stealth_kill(direction, point)
		var killed := zombie.state == Zombie.State.DEAD
		enemy_hit.emit(killed, false)
		var level := get_tree().current_scene as Level
		if level != null and killed and not was_boss:
			level.show_pickup("Тихое убийство")
		return
	var headshot := zombie.is_headshot(point)
	var amount := roundi(damage * (headshot_multiplier if headshot else 1.0))
	enemy_hit.emit(zombie.melee_hit(amount, direction, point), headshot)


## The zombie right in front of the blade that does not see us coming, if any.
func _target_for_takedown() -> Zombie:
	if camera == null:
		return null
	var direction := -camera.global_basis.z
	var from := camera.global_position
	var query := PhysicsRayQueryParameters3D.create(from, from + direction * reach, HIT_MASK)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty() or not hit.collider is Zombie:
		return null
	var zombie := hit.collider as Zombie
	return zombie if zombie.can_be_stealth_killed(direction) and not zombie is Boss else null


func _show_hint(show: bool) -> void:
	var level := get_tree().current_scene as Level
	if level != null and level.hud != null:
		level.hud.set_hint(STEALTH_HINT if show and active else "")


func unequip() -> void:
	super.unequip()
	_show_hint(false)
