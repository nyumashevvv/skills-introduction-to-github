extends Node3D
## A sign from models/signs: its two sets of bulbs (BulbsA / BulbsB) light in turn, so the marquee runs.

@export var period := 0.45

var _a: Node3D
var _b: Node3D
var _t := 0.0


func _ready() -> void:
	_a = find_child("BulbsA", true, false) as Node3D
	_b = find_child("BulbsB", true, false) as Node3D
	_t = randf() * period
	set_process(_a != null and _b != null)


func _process(delta: float) -> void:
	_t += delta
	var on := fmod(_t, period * 2.0) < period
	_a.visible = on
	_b.visible = not on
