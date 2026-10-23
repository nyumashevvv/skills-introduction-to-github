@tool
class_name Door
extends Block
## A hinged door, a sliding gate or a shutter. Opens with E (optionally needing a key) or from a StoryEvent.
## With [member swing_degrees] set it turns on a hinge at one edge, away from whoever opened it;
## otherwise it slides by [member open_offset].

@export var required_key := ""
@export var locked_message := "Заперто"
## When false the player cannot open it by hand; only an event can.
@export var player_can_open := true
@export var prompt := "Открыть"
@export var open_offset := Vector3(0.0, 3.0, 0.0)
## Swing open on a vertical hinge by this many degrees instead of sliding (0 = slide).
@export var swing_degrees := 0.0
@export var open_time := 1.2
## When true a StoryEvent only unlocks the door (the player still opens it by hand).
@export var event_unlocks := false
## StoryEvent fired when the door opens.
@export var event: NodePath

## Physics layer 4: once a door starts to open only the player bumps into it, so zombies standing behind it
## are not shoved along by the panel and do not snag on it afterwards (the navmesh does not know about doors).
const OPEN_LAYER := 8

var is_open := false
var _opener := Vector3.INF


func get_prompt(player: Player) -> String:
	if is_open:
		return ""
	if not player_can_open:
		return locked_message
	if required_key != "" and not player.has_key(required_key):
		return locked_message
	return "[E] " + prompt


func interact(player: Player) -> void:
	if is_open:
		return
	if not player_can_open or (required_key != "" and not player.has_key(required_key)):
		$LockedSound.play()
		return
	_opener = player.global_position
	open()


## Called by StoryEvents.
func activate() -> void:
	if event_unlocks:
		player_can_open = true
	else:
		open()


func open() -> void:
	if is_open:
		return
	is_open = true
	collision_layer = OPEN_LAYER
	$OpenSound.play()
	var tween := create_tween()
	if swing_degrees != 0.0:
		tween.tween_method(_swing.bind(transform, _swing_angle()), 0.0, 1.0, open_time) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	else:
		tween.tween_property(self, "position", position + open_offset, open_time) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if not event.is_empty():
		get_node(event).call("fire")


## Hinge on the +edge of the door's long side; the free edge moves away from the opener.
func _hinge() -> Vector3:
	return Vector3(size.x * 0.5, 0.0, 0.0) if size.x >= size.z else Vector3(0.0, 0.0, size.z * 0.5)


func _swing_angle() -> float:
	var angle := deg_to_rad(swing_degrees)
	if _opener == Vector3.INF:
		return angle
	var local := to_local(_opener)
	# A positive turn sends the free edge towards +z (door along x) or -x (door along z).
	var side := local.z if size.x >= size.z else -local.x
	return -angle if side > 0.0 else angle


func _swing(t: float, closed: Transform3D, angle: float) -> void:
	var hinge := closed * _hinge()
	var turn := Transform3D(Basis(Vector3.UP, angle * t), Vector3.ZERO)
	transform = Transform3D(Basis.IDENTITY, hinge) * turn * Transform3D(Basis.IDENTITY, -hinge) * closed
