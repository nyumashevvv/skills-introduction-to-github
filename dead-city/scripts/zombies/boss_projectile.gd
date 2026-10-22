class_name BossProjectile
extends Node3D
## Something a boss throws or spits: flies in an arc and splashes the player near where it lands.

## Stops on the world and the player.
const HIT_MASK := 1 | 2
const MAX_LIFETIME := 6.0

@export var damage := 15
@export var splash_radius := 1.5
@export var speed := 16.0
@export var gravity := 9.0
## Degrees per second it tumbles around (thrown debris).
@export var spin := 0.0
@export var hit_effect: PackedScene
@export var effect_scale := 1.0

var velocity := Vector3.ZERO
var _life := 0.0
var _thrower: Node3D


## Aims a ballistic arc from [param from] that reaches [param target] at [member speed].
func launch(from: Vector3, target: Vector3, thrower: Node3D) -> void:
	global_position = from
	_thrower = thrower
	var flight := maxf(from.distance_to(target) / speed, 0.15)
	velocity = (target - from) / flight + Vector3.UP * gravity * flight * 0.5


func _physics_process(delta: float) -> void:
	_life += delta
	if _life > MAX_LIFETIME:
		queue_free()
		return
	velocity.y -= gravity * delta
	var next := global_position + velocity * delta
	var exclude: Array[RID] = []
	if is_instance_valid(_thrower) and _thrower is CollisionObject3D:
		exclude.append((_thrower as CollisionObject3D).get_rid())
	var query := PhysicsRayQueryParameters3D.create(global_position, next, HIT_MASK, exclude)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		_splash(hit.position, hit.normal, hit.collider is Player)
		return
	global_position = next
	if spin != 0.0:
		rotate_x(deg_to_rad(spin) * delta)
		rotate_y(deg_to_rad(spin * 0.6) * delta)


func _splash(at: Vector3, normal: Vector3, direct: bool) -> void:
	if hit_effect != null:
		var effect := Effects.spawn(hit_effect, self, at, normal)
		effect.scale = Vector3.ONE * effect_scale
	var player := get_tree().get_first_node_in_group("player") as Player
	if player != null and not player.is_dead:
		var distance := (player.global_position + Vector3.UP * 0.9).distance_to(at)
		if direct or distance < splash_radius:
			var falloff := 1.0 if direct else 1.0 - 0.5 * distance / splash_radius
			player.take_damage(roundi(damage * falloff))
	queue_free()
