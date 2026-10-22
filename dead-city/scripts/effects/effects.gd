class_name Effects
extends RefCounted
## Helpers for spawning short-lived effects and applying explosion damage.

const TRACER_LIFETIME := 0.06

static var _tracer_mesh: BoxMesh


## Spawns [param scene] at [param at], with its -Z axis pointing along [param normal].
static func spawn(scene: PackedScene, context: Node, at: Vector3, normal := Vector3.UP) -> Node3D:
	var node := scene.instantiate() as Node3D
	node.transform = Transform3D(basis_facing(normal), at)
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
		basis_facing(to - from) * Basis.from_scale(Vector3(1.0, 1.0, length)),
		(from + to) * 0.5)
	context.get_tree().current_scene.add_child(tracer)
	var tween := tracer.create_tween()
	tween.tween_property(tracer, "transparency", 1.0, TRACER_LIFETIME)
	tween.tween_callback(tracer.queue_free)


## Damages every zombie in [param radius] (falling off with distance) and,
## less, the player. Shakes the camera depending on distance.
static func apply_blast(context: Node, at: Vector3, damage: int, radius: float, source: Weapon) -> void:
	var tree := context.get_tree()
	for node in tree.get_nodes_in_group("zombies"):
		var zombie := node as Zombie
		if zombie.state == Zombie.State.DEAD:
			continue
		# Distance to the nearest point of the body (a vertical segment as tall as its capsule),
		# so a rocket in a giant's chest counts as a direct hit.
		var shape := zombie.collision.shape as CapsuleShape3D
		var height := shape.height if shape != null else 1.8
		var base := zombie.global_position
		var center := Vector3(base.x, clampf(at.y, base.y + 0.3, base.y + height - 0.3), base.z)
		var distance := maxf(center.distance_to(at) - (shape.radius if shape != null else 0.35), 0.0)
		if distance > radius:
			continue
		var amount := roundi(damage * (1.0 - 0.7 * distance / radius))
		var killed := zombie.take_damage(amount, (center - at).normalized(), center, true)
		if source != null:
			source.enemy_hit.emit(killed, false)
	var player := tree.get_first_node_in_group("player") as Player
	if player != null:
		var distance := (player.global_position + Vector3.UP).distance_to(at)
		if distance < radius:
			player.take_damage(roundi(damage * 0.25 * (1.0 - distance / radius)))
		player.shake(clampf(1.0 - distance / (radius * 4.0), 0.0, 1.0) * 0.8)


static func basis_facing(direction: Vector3) -> Basis:
	var dir := direction.normalized()
	if dir.is_zero_approx():
		return Basis.IDENTITY
	var up := Vector3.UP if absf(dir.dot(Vector3.UP)) < 0.99 else Vector3.FORWARD
	return Basis.looking_at(dir, up)


static func _get_tracer_mesh() -> BoxMesh:
	if _tracer_mesh == null:
		var material := StandardMaterial3D.new()
		material.albedo_color = Color.BLACK
		material.emission_enabled = true
		material.emission = Color(1.0, 0.8, 0.45)
		material.emission_energy_multiplier = 6.0
		_tracer_mesh = BoxMesh.new()
		_tracer_mesh.size = Vector3(0.01, 0.01, 1.0)
		_tracer_mesh.material = material
	return _tracer_mesh
