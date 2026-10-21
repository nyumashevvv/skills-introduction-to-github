class_name Pickup
extends Area3D
## Collected by walking into it.

enum Kind { HEALTH, AMMO, WEAPON, KEY }

@export var kind := Kind.HEALTH
@export var amount := 30
## For AMMO: "pistol", "rifle" or "rocket".
@export var ammo_type := ""
## For WEAPON: "pistol", "rifle", "bazooka"; for KEY: any id doors ask for.
@export var item_id := ""
## Shown to the player when picked up.
@export var display_name := ""
## Seconds until it reappears. 0 means it is used up for good.
@export var respawn_time := 0.0
## StoryEvent fired the first time this is collected.
@export var event: NodePath

var _active := true
var _time := 0.0
var _check_timer := 0.0
var _event_fired := false

@onready var visual: Node3D = $Visual


func _ready() -> void:
	_time = randf() * TAU


func _process(delta: float) -> void:
	_time += delta
	visual.rotation.y = _time * 1.5
	visual.position.y = sin(_time * 2.5) * 0.1


func _physics_process(delta: float) -> void:
	if not _active:
		return
	# Polling instead of body_entered: a player standing on a medkit at full
	# health still gets it once they take damage.
	_check_timer -= delta
	if _check_timer > 0.0:
		return
	_check_timer = 0.1
	for body in get_overlapping_bodies():
		if body is Player and _apply(body as Player):
			_consume(body as Player)
			return


func _apply(player: Player) -> bool:
	match kind:
		Kind.HEALTH:
			return player.heal(amount)
		Kind.AMMO:
			return player.holder.add_ammo(ammo_type, amount)
		Kind.WEAPON:
			return player.holder.give_weapon(item_id)
		Kind.KEY:
			player.add_key(item_id)
			return true
	return false


func _consume(player: Player) -> void:
	if kind != Kind.KEY:
		player.play_pickup_sound()
	var level := get_tree().current_scene as Level
	if level != null and display_name != "":
		level.show_pickup(display_name)
	if not _event_fired and not event.is_empty():
		_event_fired = true
		get_node(event).call("fire")
	if respawn_time <= 0.0:
		queue_free()
		return
	_set_active(false)
	get_tree().create_timer(respawn_time, false).timeout.connect(_set_active.bind(true))


func _set_active(value: bool) -> void:
	_active = value
	visible = value
