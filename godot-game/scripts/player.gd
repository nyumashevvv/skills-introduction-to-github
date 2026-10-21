class_name Player
extends CharacterBody2D

const SPEED := 300.0
const ACCELERATION := 2000.0
const JUMP_VELOCITY := -520.0
const MAX_JUMPS := 2
## Below this Y the player is considered fallen and respawns.
const FALL_LIMIT := 1200.0

var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")
var jumps_left := MAX_JUMPS
var spawn_position := Vector2.ZERO


func _ready() -> void:
	spawn_position = global_position


func _physics_process(delta: float) -> void:
	if is_on_floor():
		jumps_left = MAX_JUMPS
	else:
		velocity.y += gravity * delta

	if Input.is_action_just_pressed("ui_accept") or Input.is_action_just_pressed("ui_up"):
		if jumps_left > 0:
			velocity.y = JUMP_VELOCITY
			jumps_left -= 1

	var direction := Input.get_axis("ui_left", "ui_right")
	velocity.x = move_toward(velocity.x, direction * SPEED, ACCELERATION * delta)

	move_and_slide()

	if global_position.y > FALL_LIMIT:
		respawn()


func respawn() -> void:
	global_position = spawn_position
	velocity = Vector2.ZERO
