extends Control
## Sniper scope reticle: thin cross with thicker outer posts and range marks.

const COLOR := Color(0, 0, 0, 0.9)


func _draw() -> void:
	var c := size * 0.5
	var r := size.y * 0.42
	draw_line(c + Vector2(-r, 0), c + Vector2(r, 0), COLOR, 1.5)
	draw_line(c + Vector2(0, -r), c + Vector2(0, r), COLOR, 1.5)
	for dir: Vector2 in [Vector2.LEFT, Vector2.RIGHT, Vector2.DOWN]:
		draw_line(c + dir * r * 0.55, c + dir * r, COLOR, 6.0)
	for i in range(1, 5):
		var y := c.y + i * r * 0.1
		draw_line(Vector2(c.x - 6.0 + i, y), Vector2(c.x + 6.0 - i, y), COLOR, 1.5)
	draw_circle(c, 1.5, Color(0.9, 0.1, 0.05))
