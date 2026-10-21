class_name Launcher
extends Weapon
## Bazooka: fires a rocket that explodes with splash damage.

@export var rocket_scene: PackedScene
@export var rocket_speed := 38.0
@export var damage := 220
@export var blast_radius := 6.5
@export var recoil := 0.08

@onready var muzzle: Node3D = $Model/Muzzle
@onready var loaded_rocket: Node3D = $Model.find_child("LoadedRocket")
@onready var shoot_sound: AudioStreamPlayer = $ShootSound
@onready var empty_sound: AudioStreamPlayer = $EmptySound


func _handle_input(_held: bool, just_pressed: bool) -> void:
	if not just_pressed or is_reloading:
		return
	if ammo <= 0:
		if reserve > 0:
			start_reload()
		else:
			empty_sound.play()
		return
	_fire()


func _update(_delta: float) -> void:
	loaded_rocket.visible = ammo > 0


func spread_deg() -> float:
	return 1.0 + movement_factor * 2.0


func _fire() -> void:
	ammo -= 1
	ammo_changed.emit(self)
	shoot_sound.play()
	kick(0.25, 0.3)

	# Aim the rocket from the muzzle at whatever is under the crosshair.
	var from := camera.global_position
	var forward := -camera.global_basis.z
	var query := PhysicsRayQueryParameters3D.create(from, from + forward * 300.0, HIT_MASK)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	var target: Vector3 = hit.position if not hit.is_empty() else from + forward * 300.0
	var start := muzzle.global_position
	# Point blank: fire straight ahead instead of sideways from the muzzle.
	var direction := (target - start).normalized() if start.distance_to(target) > 2.0 else forward

	var rocket := rocket_scene.instantiate() as Rocket
	get_tree().current_scene.add_child(rocket)
	rocket.launch(start, direction, rocket_speed, damage, blast_radius, self)
	make_noise()
	fired.emit(recoil)
	if ammo == 0 and reserve > 0:
		start_reload()
