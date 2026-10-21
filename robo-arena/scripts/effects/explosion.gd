extends Node3D

@onready var light: OmniLight3D = $Light


func _ready() -> void:
	for child in get_children():
		if child is CPUParticles3D:
			(child as CPUParticles3D).emitting = true
	var tween := create_tween()
	tween.tween_property(light, "light_energy", 0.0, 0.5)
	get_tree().create_timer(2.0, false).timeout.connect(queue_free)
