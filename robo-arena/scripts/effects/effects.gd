class_name Effects
extends RefCounted
## Helpers for spawning short-lived visual effects into the current scene.

const TRACER_LIFETIME := 0.06

static var _tracer_mesh: BoxMesh


## Spawns [param scene] at [param at], with its -Z axis pointing along [param normal].
static func spawn(scene: PackedScene, context: Node, at: Vector3, normal := Vector3.UP) -> Node3D:
	var node := scene.instantiate() as Node3D
	node.transform = Transform3D(_basis_facing(normal), at)
	context.get_tree().current_scene.add_child(node)
	return node


static func spawn_tracer(context: Node, from: Vector3, to: Vector3) -> void:
	var length := from.distance_to(to)
	if length < 1.0:
		return
	var tracer := MeshInstance3D.new()
	tracer.mesh = _get_tracer_mesh()
	tracer.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	tracer.transform = Transform3D(
		_basis_facing(to - from) * Basis.from_scale(Vector3(1.0, 1.0, length)),
		(from + to) * 0.5)
	context.get_tree().current_scene.add_child(tracer)
	var tween := tracer.create_tween()
	tween.tween_property(tracer, "transparency", 1.0, TRACER_LIFETIME)
	tween.tween_callback(tracer.queue_free)


static func _get_tracer_mesh() -> BoxMesh:
	if _tracer_mesh == null:
		var material := StandardMaterial3D.new()
		material.albedo_color = Color.BLACK
		material.emission_enabled = true
		material.emission = Color(1.0, 0.8, 0.45)
		material.emission_energy_multiplier = 6.0
		_tracer_mesh = BoxMesh.new()
		_tracer_mesh.size = Vector3(0.012, 0.012, 1.0)
		_tracer_mesh.material = material
	return _tracer_mesh


static func _basis_facing(direction: Vector3) -> Basis:
	var dir := direction.normalized()
	if dir.is_zero_approx():
		return Basis.IDENTITY
	var up := Vector3.UP if absf(dir.dot(Vector3.UP)) < 0.99 else Vector3.FORWARD
	return Basis.looking_at(dir, up)
