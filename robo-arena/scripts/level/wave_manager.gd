class_name WaveManager
extends Node

signal wave_started(number: int)
signal wave_cleared(number: int)
signal enemies_left_changed(count: int)
signal enemy_killed(enemy: Enemy)

@export var grunt_scene: PackedScene
@export var rusher_scene: PackedScene
@export var brute_scene: PackedScene
@export var spawn_points: Node3D
@export var enemies_root: Node3D
@export var first_wave_delay := 2.0
@export var time_between_waves := 6.0
@export var spawn_interval := 0.8
## Spawn points closer than this to the player are skipped when possible.
@export var min_spawn_distance := 15.0

var wave := 0
var running := false

var _queue: Array[PackedScene] = []
var _alive := 0
var _in_wave := false
var _spawn_timer := 0.0
var _break_timer := 0.0
var _player: Player


func start() -> void:
	_player = get_tree().get_first_node_in_group("player") as Player
	running = true
	_break_timer = first_wave_delay


func stop() -> void:
	running = false


func time_until_next_wave() -> float:
	return _break_timer


func _process(delta: float) -> void:
	if not running:
		return
	if not _in_wave:
		_break_timer -= delta
		if _break_timer <= 0.0:
			_start_next_wave()
		return

	if not _queue.is_empty():
		_spawn_timer -= delta
		if _spawn_timer <= 0.0:
			_spawn_timer = spawn_interval
			_spawn(_queue.pop_back())
	elif _alive == 0:
		_in_wave = false
		_break_timer = time_between_waves
		wave_cleared.emit(wave)


func _start_next_wave() -> void:
	wave += 1
	_in_wave = true
	_spawn_timer = 0.0
	_queue.clear()
	for i in 2 + wave:
		_queue.append(rusher_scene)
	for i in wave:
		_queue.append(grunt_scene)
	for i in maxi(0, (wave - 2) / 2):
		_queue.append(brute_scene)
	_queue.shuffle()
	wave_started.emit(wave)
	enemies_left_changed.emit(_queue.size())


func _spawn(scene: PackedScene) -> void:
	var enemy := scene.instantiate() as Enemy
	enemy.max_health = roundi(enemy.max_health * (1.0 + 0.12 * (wave - 1)))
	enemy.move_speed *= minf(1.0 + 0.03 * (wave - 1), 1.4)
	enemy.position = _pick_spawn_position()
	enemy.died.connect(_on_enemy_died)
	enemies_root.add_child(enemy)
	_alive += 1


func _pick_spawn_position() -> Vector3:
	var all: Array[Vector3] = []
	var far: Array[Vector3] = []
	for point in spawn_points.get_children():
		var position := (point as Node3D).global_position
		all.append(position)
		if _player == null or position.distance_to(_player.global_position) >= min_spawn_distance:
			far.append(position)
	var chosen: Vector3 = far.pick_random() if not far.is_empty() else all.pick_random()
	return chosen + Vector3(randf_range(-1.5, 1.5), 0.0, randf_range(-1.5, 1.5))


func _on_enemy_died(enemy: Enemy) -> void:
	_alive -= 1
	enemy_killed.emit(enemy)
	enemies_left_changed.emit(_alive + _queue.size())
