class_name AmmoPips
extends Control
## One small mark per round in the magazine: lit while loaded, dim once fired.

@export var lit_color := Color(1.0, 0.85, 0.5)
@export var empty_color := Color(1, 1, 1, 0.15)

var capacity := 0:
	set(v):
		capacity = v
		queue_redraw()
var count := 0:
	set(v):
		count = v
		queue_redraw()


func _draw() -> void:
	if capacity <= 0:
		return
	var gap := 2.0 if capacity > 15 else 3.0
	var width := minf((size.x - gap * (capacity - 1)) / capacity, 14.0)
	# Right-aligned, like the numbers above.
	var x := size.x - capacity * (width + gap) + gap
	for i in capacity:
		var lit := i < count
		draw_rect(Rect2(Vector2(x + i * (width + gap), 0.0), Vector2(width, size.y)), lit_color if lit else empty_color)
