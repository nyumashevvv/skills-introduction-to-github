class_name Crosshair
extends Control
## Four lines that spread apart with the weapon's inaccuracy; a dot for melee.

const COLOR := Color(1, 1, 1, 0.85)
const SHADOW := Color(0, 0, 0, 0.5)
const LINE_LENGTH := 7.0
const MIN_GAP := 4.0
## Rough screen pixels per degree of spread at the default FOV.
const PIXELS_PER_DEGREE := 9.0

var spread := 0.0
var dot_only := false


func _process(_delta: float) -> void:
	queue_redraw()


func _draw() -> void:
	draw_circle(Vector2.ZERO, 2.5, SHADOW)
	draw_circle(Vector2.ZERO, 1.5, COLOR)
	if dot_only:
		return
	var gap := MIN_GAP + spread * PIXELS_PER_DEGREE
	for dir: Vector2 in [Vector2.RIGHT, Vector2.LEFT, Vector2.UP, Vector2.DOWN]:
		draw_line(dir * gap, dir * (gap + LINE_LENGTH), SHADOW, 4.0)
		draw_line(dir * gap, dir * (gap + LINE_LENGTH), COLOR, 2.0)
