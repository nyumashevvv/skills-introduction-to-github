extends Node3D
## The rescue helicopter. Hidden until activated, then flies in and lands where it was placed.

@export var approach_offset := Vector3(-60.0, 45.0, -80.0)
@export var flight_time := 9.0

var _landing := Vector3.ZERO

@onready var main_rotor: Node3D = $Model/MainRotor
@onready var tail_rotor: Node3D = $Model/TailRotor
@onready var sound: AudioStreamPlayer3D = $Sound


func _ready() -> void:
	_landing = position
	visible = false
	set_process(false)


func activate() -> void:
	visible = true
	set_process(true)
	position = _landing + approach_offset
	# Nose (-Z) towards the landing spot.
	rotation.y = atan2(approach_offset.x, approach_offset.z)
	sound.play()
	var tween := create_tween()
	tween.tween_property(self, "position", _landing + Vector3.UP * 6.0, flight_time * 0.75) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, "position", _landing, flight_time * 0.25).set_ease(Tween.EASE_IN_OUT)


func _process(delta: float) -> void:
	main_rotor.rotate_y(delta * 25.0)
	tail_rotor.rotate_x(delta * 35.0)
