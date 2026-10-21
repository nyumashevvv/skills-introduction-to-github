@tool
class_name Platform
extends StaticBody2D

@export var size := Vector2(200, 24):
	set(value):
		size = value
		_update()

@export var color := Color(0.33, 0.55, 0.29):
	set(value):
		color = value
		_update()


func _ready() -> void:
	_update()


func _update() -> void:
	if not is_node_ready():
		return
	var shape := RectangleShape2D.new()
	shape.size = size
	$CollisionShape2D.shape = shape
	$ColorRect.size = size
	$ColorRect.position = -size / 2.0
	$ColorRect.color = color
