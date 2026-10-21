@tool
class_name Door
extends Block
## A sliding door or shutter. Opens with E (optionally needing a key) or from a StoryEvent.

@export var required_key := ""
@export var locked_message := "Заперто"
## When false the player cannot open it by hand; only an event can.
@export var player_can_open := true
@export var prompt := "Открыть"
@export var open_offset := Vector3(0.0, 3.0, 0.0)
@export var open_time := 1.2
## StoryEvent fired when the door opens.
@export var event: NodePath

var is_open := false


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
	open()


## Called by StoryEvents.
func activate() -> void:
	open()


func open() -> void:
	if is_open:
		return
	is_open = true
	$OpenSound.play()
	var tween := create_tween()
	tween.tween_property(self, "position", position + open_offset, open_time) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if not event.is_empty():
		get_node(event).call("fire")
