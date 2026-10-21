class_name StoryEvent
extends Node
## One beat of the story. When fired it can update the objective, play a radio
## message and activate other nodes (doors, spawners, other events...).
## Anything with an activate() method can be a target.

@export var delay := 0.0
@export_multiline var objective := ""
@export var speaker := ""
@export_multiline var message := ""
@export var message_duration := 6.0
@export var targets: Array[NodePath] = []
@export var complete_level := false

var _fired := false


func fire() -> void:
	if _fired:
		return
	_fired = true
	if delay > 0.0:
		await get_tree().create_timer(delay, false).timeout
	var level := get_tree().current_scene as Level
	if level != null:
		if objective != "":
			level.set_objective(objective)
		if message != "":
			level.radio(speaker, message, message_duration)
	for path in targets:
		var node := get_node_or_null(path)
		if node != null and node.has_method("activate"):
			node.call("activate")
	if complete_level and level != null:
		level.complete()


## Lets one event trigger another.
func activate() -> void:
	fire()
