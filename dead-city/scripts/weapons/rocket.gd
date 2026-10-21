class_name Rocket
extends Node3D

const EXPLOSION_SCENE := preload("res://scenes/effects/explosion.tscn")
const HIT_MASK := 1 | 4

var velocity := Vector3.ZERO
var damage := 200
var radius := 6.0
var source: Weapon

var _life := 6.0


func launch(from: Vector3, direction: Vector3, speed: float, amount: int, blast_radius: float, weapon: Weapon) -> void:
	velocity = direction.normalized() * speed
	damage = amount
	radius = blast_radius
	source = weapon
	global_transform = Transform3D(Effects.basis_facing(direction), from)


func _physics_process(delta: float) -> void:
	var from := global_position
	var to := from + velocity * delta
	# Ray per step so fast rockets never tunnel through thin walls.
	var query := PhysicsRayQueryParameters3D.create(from, to, HIT_MASK)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		_explode(hit.position - velocity.normalized() * 0.2)
		return
	global_position = to
	_life -= delta
	if _life <= 0.0:
		_explode(global_position)


func _explode(at: Vector3) -> void:
	Effects.spawn(EXPLOSION_SCENE, self, at)
	Effects.apply_blast(self, at, damage, radius, source)
	queue_free()
