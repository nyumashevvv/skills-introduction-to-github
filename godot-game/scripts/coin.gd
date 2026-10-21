class_name Coin
extends Area2D

signal collected

const RADIUS := 12.0

var _time := 0.0
var _base_y := 0.0


func _ready() -> void:
	_base_y = position.y
	_time = randf() * TAU
	body_entered.connect(_on_body_entered)


func _process(delta: float) -> void:
	_time += delta * 3.0
	position.y = _base_y + sin(_time) * 4.0


func _draw() -> void:
	draw_circle(Vector2.ZERO, RADIUS, Color(0.96, 0.77, 0.26))
	draw_arc(Vector2.ZERO, RADIUS, 0.0, TAU, 24, Color(0.79, 0.58, 0.16), 3.0)


func _on_body_entered(body: Node2D) -> void:
	if body is Player:
		collected.emit()
		queue_free()
