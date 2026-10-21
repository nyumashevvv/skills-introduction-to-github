class_name Impact
extends Node3D

@onready var particles: CPUParticles3D = $Particles


func _ready() -> void:
	particles.emitting = true
	get_tree().create_timer(particles.lifetime + 0.2, false).timeout.connect(queue_free)


func set_color(color: Color) -> void:
	$Particles.color = color
