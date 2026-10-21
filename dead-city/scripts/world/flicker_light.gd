extends Light3D
## A failing lamp: mostly steady with random dropouts.

@export_range(0.0, 1.0) var flicker_chance := 0.06
## Set by StoryEvents (e.g. an alarm) to make every lamp go crazy.
@export var panic := false

var _base_energy := 0.0


func _ready() -> void:
	_base_energy = light_energy


func activate() -> void:
	panic = true


func _process(delta: float) -> void:
	var chance := 0.35 if panic else flicker_chance
	if randf() < chance:
		light_energy = _base_energy * randf_range(0.0, 0.35)
	else:
		light_energy = lerpf(light_energy, _base_energy, clampf(delta * 12.0, 0.0, 1.0))
