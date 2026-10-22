@tool
class_name SegmentBar
extends Control
## A flat bar split into segments (health) or one solid strip (segments = 0, boss health).

@export var max_value := 100.0:
	set(v):
		max_value = v
		queue_redraw()
@export var value := 100.0:
	set(v):
		value = v
		queue_redraw()
@export var segments := 10
@export var fill_color := Color(0.9, 0.9, 0.85)
@export var back_color := Color(0, 0, 0, 0.55)
@export var gap := 3.0


func _draw() -> void:
	var ratio := clampf(value / maxf(max_value, 1.0), 0.0, 1.0)
	if segments <= 0:
		draw_rect(Rect2(Vector2.ZERO, size), back_color)
		draw_rect(Rect2(Vector2.ZERO, Vector2(size.x * ratio, size.y)), fill_color)
		draw_rect(Rect2(Vector2.ZERO, size), Color(fill_color, 0.6), false, 1.0)
		return
	var width := (size.x - gap * (segments - 1)) / segments
	for i in segments:
		var rect := Rect2(Vector2(i * (width + gap), 0.0), Vector2(width, size.y))
		draw_rect(rect, back_color)
		# Partially filled last segment.
		var fill := clampf(ratio * segments - i, 0.0, 1.0)
		if fill > 0.0:
			draw_rect(Rect2(rect.position, Vector2(width * fill, size.y)), fill_color)
