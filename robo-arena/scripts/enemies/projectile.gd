class_name Projectile
extends Area3D

const IMPACT_SCENE := preload("res://scenes/effects/impact.tscn")
const IMPACT_COLOR := Color(4.0, 0.6, 0.8)

var damage := 10
var velocity := Vector3.ZERO

var _life := 6.0
var _done := false


func _ready() -> void:
	body_entered.connect(_on_body_entered)


func launch(from: Vector3, direction: Vector3, speed: float, amount: int) -> void:
	global_position = from
	velocity = direction.normalized() * speed
	damage = amount


func _physics_process(delta: float) -> void:
	global_position += velocity * delta
	_life -= delta
	if _life <= 0.0:
		queue_free()


func _on_body_entered(body: Node3D) -> void:
	if _done:
		return
	_done = true
	if body is Player:
		(body as Player).take_damage(damage)
	var impact := Effects.spawn(IMPACT_SCENE, self, global_position, -velocity) as Impact
	impact.set_color(IMPACT_COLOR)
	queue_free()
