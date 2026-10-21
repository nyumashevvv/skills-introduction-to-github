extends Node3D
## Starts every particle emitter below it, fades any lights, and frees itself.

@export var lifetime := 2.0
@export var light_fade_time := 0.4


func _ready() -> void:
	for node in find_children("*", "CPUParticles3D"):
		(node as CPUParticles3D).emitting = true
	for node in find_children("*", "Light3D"):
		var tween := create_tween()
		tween.tween_property(node, "light_energy", 0.0, light_fade_time)
	get_tree().create_timer(lifetime, false).timeout.connect(queue_free)
