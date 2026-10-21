class_name StoryTrigger
extends Area3D
## Fires a StoryEvent once when the player walks in.

@export var event: NodePath
## Disabled triggers do nothing until a StoryEvent activates them.
@export var enabled := true


func _ready() -> void:
	body_entered.connect(_on_body_entered)


func activate() -> void:
	enabled = true
	# The player may already be standing inside.
	for body in get_overlapping_bodies():
		_on_body_entered(body)


func _on_body_entered(body: Node3D) -> void:
	if not enabled or not body is Player:
		return
	enabled = false
	get_node(event).call("fire")
