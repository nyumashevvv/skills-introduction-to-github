extends Control
## An "X" drawn around the screen center; the HUD fades it in on every hit.

const INNER := 6.0
const OUTER := 14.0


func _draw() -> void:
	for dir: Vector2 in [Vector2(1, 1), Vector2(-1, 1), Vector2(1, -1), Vector2(-1, -1)]:
		var d := dir.normalized()
		draw_line(d * INNER, d * OUTER, Color.WHITE, 3.0)
