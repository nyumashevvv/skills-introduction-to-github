class_name RouletteWheel
extends Control
## A European roulette wheel drawn in 2D: 37 pockets in casino order, a ball running the other way. spin_to(n)
## slows both down so the ball settles in pocket n, then emits finished.

signal finished

const ORDER: Array[int] = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14,
		31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
const SPIN_TIME := 4.2
const WHEEL_SPEED := 3.2
const BALL_SPEED := 9.0

var rotation_angle := 0.0
var ball_angle := -PI / 2
var ball_radius := 0.93
var _spinning := false
var _time := 0.0
var _wheel_from := 0.0
var _ball_from := 0.0


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	custom_minimum_size = Vector2(330, 330)


func spin_to(number: int) -> void:
	var slot := ORDER.find(number)
	var seg := TAU / ORDER.size()
	_wheel_from = rotation_angle
	var wheel_end := _wheel_from + WHEEL_SPEED * SPIN_TIME / 2.0
	# The ball's path is fixed by where it must end: in the pocket, wherever the wheel has turned to by then.
	_ball_from = wheel_end + slot * seg + BALL_SPEED * SPIN_TIME / 2.0
	_time = 0.0
	_spinning = true


func _process(delta: float) -> void:
	if not _spinning:
		return
	_time = minf(_time + delta, SPIN_TIME)
	var eased := _time - _time * _time / (2.0 * SPIN_TIME)   # distance covered while slowing to a stop
	rotation_angle = _wheel_from + WHEEL_SPEED * eased
	ball_angle = _ball_from - BALL_SPEED * eased
	ball_radius = lerpf(0.93, 0.7, clampf((_time / SPIN_TIME - 0.55) / 0.35, 0.0, 1.0))
	queue_redraw()
	if _time >= SPIN_TIME:
		_spinning = false
		finished.emit()


func _draw() -> void:
	var c := size / 2.0
	var r := minf(size.x, size.y) / 2.0 - 4.0
	var seg := TAU / ORDER.size()
	draw_circle(c, r + 3.0, Color(0.35, 0.2, 0.08))
	draw_circle(c, r, Color(0.12, 0.07, 0.03))
	var font := ThemeDB.fallback_font
	for i in ORDER.size():
		var a := rotation_angle + i * seg
		var points := PackedVector2Array([c + Vector2.from_angle(a - seg / 2) * r * 0.62,
				c + Vector2.from_angle(a - seg / 2) * r * 0.97, c + Vector2.from_angle(a) * r * 0.97,
				c + Vector2.from_angle(a + seg / 2) * r * 0.97, c + Vector2.from_angle(a + seg / 2) * r * 0.62])
		draw_colored_polygon(points, pocket_color(ORDER[i]))
		draw_set_transform(c + Vector2.from_angle(a) * r * 0.84, a + PI / 2)
		draw_string(font, Vector2(-9, 5), str(ORDER[i]), HORIZONTAL_ALIGNMENT_CENTER, 18, 12, Color.WHITE)
		draw_set_transform(Vector2.ZERO)
	draw_circle(c, r * 0.62, Color(0.45, 0.28, 0.12))
	draw_circle(c, r * 0.3, Color(0.8, 0.62, 0.25))
	for k in 4:
		draw_line(c, c + Vector2.from_angle(rotation_angle + k * PI / 2) * r * 0.55, Color(0.9, 0.75, 0.35), 4.0)
	draw_circle(c + Vector2.from_angle(ball_angle) * r * ball_radius, 7.0, Color(0.96, 0.96, 0.96))


static func pocket_color(number: int) -> Color:
	if number == 0:
		return Color(0.05, 0.5, 0.2)
	return Color(0.75, 0.08, 0.08) if RoulettePanel.is_red(number) else Color(0.08, 0.08, 0.08)
