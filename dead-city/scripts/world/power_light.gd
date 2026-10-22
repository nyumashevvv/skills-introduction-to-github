extends Light3D
## A lamp that stays dark until the power comes back (a StoryEvent calls activate()).

@export var powered := false

var _energy := 0.0


func _ready() -> void:
	_energy = light_energy
	if not powered:
		light_energy = 0.0


func activate() -> void:
	if powered:
		return
	powered = true
	# Fluorescent tubes stutter before they catch.
	var tween := create_tween()
	tween.tween_interval(randf() * 0.6)
	for i in 3:
		tween.tween_property(self, "light_energy", _energy * randf_range(0.4, 1.0), 0.05)
		tween.tween_property(self, "light_energy", 0.0, 0.07)
	tween.tween_property(self, "light_energy", _energy, 0.1)
