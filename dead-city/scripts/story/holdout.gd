class_name Holdout
extends Node
## "Survive until help arrives": runs spawners for a while, sends a boss midway.

@export var duration := 120.0
@export var timer_text := "Вертолёт через %s"
@export var spawners: Array[NodePath] = []
@export var boss_spawner: NodePath
@export var boss_time := 60.0
@export var boss_event: NodePath
## When time runs out with the boss still alive, the other spawners stop and this shows
## until it is dead; only then does the holdout finish.
@export var boss_text := "Убей босса!"
## StoryEvent fired when time runs out.
@export var on_finished: NodePath

var running := false
var time_left := 0.0
var _boss_sent := false


func activate() -> void:
	running = true
	time_left = duration
	for path in spawners:
		(get_node(path) as ZombieSpawner).activate()


func _process(delta: float) -> void:
	if not running:
		return
	time_left = maxf(time_left - delta, 0.0)
	var level := get_tree().current_scene as Level
	var boss_alive := _boss_sent and (get_node(boss_spawner) as ZombieSpawner).alive_count() > 0
	if level != null:
		if time_left <= 0.0 and boss_alive:
			level.hud.set_timer(boss_text)
		else:
			level.hud.set_timer(timer_text % ("%d:%02d" % [int(time_left) / 60, int(time_left) % 60]))
	if not _boss_sent and duration - time_left >= boss_time and not boss_spawner.is_empty():
		_boss_sent = true
		(get_node(boss_spawner) as ZombieSpawner).activate()
		if not boss_event.is_empty():
			get_node(boss_event).call("fire")
	if time_left <= 0.0:
		if boss_alive:
			_stop_spawners()
		else:
			_finish(level)


func _finish(level: Level) -> void:
	running = false
	if level != null:
		level.hud.set_timer("")
	_stop_spawners()
	if not on_finished.is_empty():
		get_node(on_finished).call("fire")


func _stop_spawners() -> void:
	for path in spawners:
		(get_node(path) as ZombieSpawner).deactivate()
