class_name Grenade
extends RigidBody3D
## A thrown frag grenade: bounces, then explodes when its fuse runs out.

const EXPLOSION_SCENE := preload("res://scenes/effects/explosion.tscn")
const FUSE := 2.2

var damage := 260
var radius := 6.5
var source: Weapon
var _fuse := FUSE
var _bounce_cooldown := 0.0

@onready var bounce_sound: AudioStreamPlayer3D = $BounceSound


func setup(amount: int, blast_radius: float, weapon: Weapon) -> void:
	damage = amount
	radius = blast_radius
	source = weapon


func _ready() -> void:
	contact_monitor = true
	max_contacts_reported = 2
	body_entered.connect(_on_body_entered)


func _physics_process(delta: float) -> void:
	_fuse -= delta
	_bounce_cooldown -= delta
	if _fuse <= 0.0:
		Effects.spawn(EXPLOSION_SCENE, self, global_position + Vector3.UP * 0.2)
		Effects.apply_blast(self, global_position + Vector3.UP * 0.3, damage, radius, source)
		if source != null:
			source.make_noise()
		queue_free()


func _on_body_entered(_body: Node) -> void:
	if _bounce_cooldown <= 0.0 and linear_velocity.length() > 1.5:
		_bounce_cooldown = 0.15
		bounce_sound.play()
