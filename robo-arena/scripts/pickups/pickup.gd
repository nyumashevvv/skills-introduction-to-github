class_name Pickup
extends Area3D

enum Kind { HEALTH, AMMO }

@export var kind := Kind.HEALTH
@export var amount := 30
## Seconds until the pickup reappears. 0 means it is used up for good.
@export var respawn_time := 0.0

var _active := true
var _time := 0.0
var _check_timer := 0.0

@onready var visual: Node3D = $Visual


func _ready() -> void:
	_time = randf() * TAU


func _process(delta: float) -> void:
	_time += delta
	visual.rotation.y = _time * 1.5
	visual.position.y = sin(_time * 2.5) * 0.12


func _physics_process(delta: float) -> void:
	if not _active:
		return
	# Polling instead of body_entered: a player standing on the pickup at full
	# health should still get it once they take damage.
	_check_timer -= delta
	if _check_timer > 0.0:
		return
	_check_timer = 0.1
	for body in get_overlapping_bodies():
		if body is Player and _apply(body as Player):
			_consume()
			return


func _apply(player: Player) -> bool:
	match kind:
		Kind.HEALTH:
			return player.heal(amount)
		Kind.AMMO:
			return player.weapon.add_ammo(amount)
	return false


func _consume() -> void:
	var player := get_tree().get_first_node_in_group("player") as Player
	player.play_pickup_sound()
	if respawn_time <= 0.0:
		queue_free()
		return
	_set_active(false)
	get_tree().create_timer(respawn_time, false).timeout.connect(_set_active.bind(true))


func _set_active(value: bool) -> void:
	_active = value
	visible = value
