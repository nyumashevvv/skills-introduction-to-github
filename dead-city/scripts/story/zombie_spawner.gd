class_name ZombieSpawner
extends Node3D
## Spawns zombies at its Marker3D children once activated.

@export var zombie_scenes: Array[PackedScene] = []
@export var count := 6
@export var interval := 0.7
@export var alerted := true
## Keeps spawning (respecting max_alive) until deactivate() is called.
@export var continuous := false
@export var max_alive := 10
## StoryEvent fired when everything this spawner made is dead.
@export var on_cleared: NodePath

var active := false
var _left := 0
var _alive := 0
var _timer := 0.0


func activate() -> void:
	active = true
	_left = count


func deactivate() -> void:
	active = false
	continuous = false
	_left = 0


func alive_count() -> int:
	return _alive


func spawn_one(scene: PackedScene) -> Zombie:
	var markers := get_children().filter(func(n: Node) -> bool: return n is Marker3D)
	var origin: Vector3 = (markers.pick_random() as Marker3D).global_position if not markers.is_empty() else global_position
	var zombie := scene.instantiate() as Zombie
	zombie.start_alerted = alerted
	zombie.position = origin + Vector3(randf_range(-1.0, 1.0), 0.0, randf_range(-1.0, 1.0))
	zombie.died.connect(_on_zombie_died)
	get_tree().current_scene.add_child(zombie)
	_alive += 1
	return zombie


func _process(delta: float) -> void:
	if not active:
		return
	if _left <= 0 and not continuous:
		return
	_timer -= delta
	if _timer > 0.0 or _alive >= max_alive:
		return
	_timer = interval
	spawn_one(zombie_scenes.pick_random())
	_left -= 1


func _on_zombie_died(_zombie: Zombie) -> void:
	_alive -= 1
	if _alive == 0 and _left <= 0 and not continuous and not on_cleared.is_empty():
		get_node(on_cleared).call("fire")
