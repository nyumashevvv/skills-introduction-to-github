extends Control
## The intro: a few voiced shots (TV news, the fallen city, the basement, the radio) between letterbox bars.
## Each shot moves the camera from marker <Shot>A to <Shot>B in the backdrop world while its line plays.
## Any key skips to chapter 1.

const MIN_SHOT := 4.0
const FADE := 0.6

## Parallel arrays, one entry per shot (written by tools/gen_assets.py from tools/story_text.py).
@export var shots: PackedStringArray = []
@export var speakers: PackedStringArray = []
@export var lines: PackedStringArray = []

var _finished := false

@onready var camera: Camera3D = $Camera3D
@onready var cams: Node3D = $World/Cams
@onready var subtitle: RichTextLabel = $Subtitle/Text
@onready var subtitle_panel: Control = $Subtitle
@onready var news: Control = $News
@onready var fade: ColorRect = $Fade
@onready var voice: AudioStreamPlayer = $Voice
@onready var static_sound: AudioStreamPlayer = $Static
@onready var radio_sound: AudioStreamPlayer = $RadioClick


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_HIDDEN
	news.visible = false
	voice.bus = &"Voice"
	subtitle_panel.modulate.a = 0.0
	fade.color.a = 1.0
	# Zombies in the street shuffle about in front of the cameras.
	for node in get_tree().get_nodes_in_group("zombies"):
		var zombie := node as Zombie
		zombie._home = Vector3(randf_range(-4.0, 4.0), 0.0, randf_range(-30.0, -8.0))
		zombie.wander_speed = 0.6
	_play.call_deferred()


func _unhandled_input(event: InputEvent) -> void:
	var pressed := (event is InputEventKey or event is InputEventMouseButton or event is InputEventJoypadButton) \
		and event.is_pressed()
	if pressed and not _finished:
		get_viewport().set_input_as_handled()
		_finish()


func _play() -> void:
	for i in shots.size():
		if _finished:
			return
		await _shot(shots[i], speakers[i], lines[i])
	_finish()


func _shot(shot: String, speaker: String, text: String) -> void:
	var from := cams.get_node(shot + "A") as Node3D
	var to := cams.get_node(shot + "B") as Node3D
	var stream := Hud.voice_line(text)
	var length := maxf(MIN_SHOT, stream.get_length() + 1.4 if stream != null else text.length() * 0.07)
	camera.global_transform = from.global_transform
	news.visible = shot == "News"
	if shot == "News" or shot == "Radio":
		static_sound.play()
	else:
		static_sound.stop()
	var move := create_tween()
	move.tween_property(camera, "global_transform", to.global_transform, length + FADE * 2.0) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	await _fade_to(0.0)
	if _finished:
		return
	_say(speaker, text, stream)
	await get_tree().create_timer(length).timeout
	if _finished:
		return
	create_tween().tween_property(subtitle_panel, "modulate:a", 0.0, 0.3)
	await _fade_to(1.0)


func _say(speaker: String, text: String, stream: AudioStream) -> void:
	if speaker == "":
		subtitle.text = "[i]%s[/i]" % text  # the hero's thoughts
	else:
		subtitle.text = "[color=#e8c06a]%s:[/color] %s" % [speaker, text]
	create_tween().tween_property(subtitle_panel, "modulate:a", 1.0, 0.3)
	if speaker == "Диспетчер":
		radio_sound.play()
	if stream != null:
		voice.stream = stream
		voice.play()


func _fade_to(alpha: float) -> void:
	var tween := create_tween()
	tween.tween_property(fade, "color:a", alpha, FADE)
	await tween.finished


func _finish() -> void:
	if _finished:
		return
	_finished = true
	voice.stop()
	await _fade_to(1.0)
	Game.start_first_chapter()
