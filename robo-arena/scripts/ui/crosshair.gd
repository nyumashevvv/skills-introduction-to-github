class_name Crosshair
extends Control
## Four lines that spread apart with the weapon's current inaccuracy.

const COLOR := Color(1, 1, 1, 0.9)
const SHADOW := Color(0, 0, 0, 0.5)
const LINE_LENGTH := 8.0
const MIN_GAP := 4.0
## Rough screen pixels per degree of spread at the default FOV.
const PIXELS_PER_DEGREE := 9.0

var weapon: Weapon


func _process(_delta: float) -> void:
	queue_redraw()


func _draw() -> void:
	var gap := MIN_GAP
	if weapon != null:
		gap += weapon.current_spread_deg() * PIXELS_PER_DEGREE
	for dir: Vector2 in [Vector2.RIGHT, Vector2.LEFT, Vector2.UP, Vector2.DOWN]:
		draw_line(dir * gap, dir * (gap + LINE_LENGTH), SHADOW, 4.0)
		draw_line(dir * gap, dir * (gap + LINE_LENGTH), COLOR, 2.0)
	draw_circle(Vector2.ZERO, 1.5, COLOR)
