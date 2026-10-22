extends Control
## Main menu over the burning street: the camera drifts between two marks while the dead shuffle about.
## "Новая игра" opens the difficulty choice.

const DRIFT_TIME := 22.0
const DIFFICULTY_TEXT: Array[String] = [
	"Зомби слабее и медленнее, больше патронов. Для тех, кто хочет сюжет.",
	"Как задумано: патронов впритык, каждый бой — испытание.",
	"Зомби крепче, быстрее и бьют больнее, патронов меньше. Только для выживших.",
]

@onready var continue_button: Button = $Menu/Buttons/ContinueButton
@onready var new_game_button: Button = $Menu/Buttons/NewGameButton
@onready var buttons: Control = $Menu/Buttons
@onready var difficulty_panel: Control = $Menu/Difficulty
@onready var difficulty_info: Label = $Menu/Difficulty/Info
@onready var title: Label = $Menu/Title
@onready var settings: Control = $Menu/Settings
@onready var camera: Camera3D = $Camera3D
@onready var music: AudioStreamPlayer = $Music


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	new_game_button.pressed.connect(_show_difficulty)
	continue_button.pressed.connect(Game.continue_game)
	$Menu/Buttons/QuitButton.pressed.connect(get_tree().quit)
	$Menu/Buttons/SettingsButton.pressed.connect(_show_settings)
	settings.connect("closed", _show_main)
	$Menu/Difficulty/BackButton.pressed.connect(_show_main)
	for i in 3:
		var button := difficulty_panel.get_node("Level%d" % i) as Button
		button.pressed.connect(Game.new_game.bind(i))
		button.focus_entered.connect(_describe.bind(i))
		button.mouse_entered.connect(_describe.bind(i))
	if Game.has_save():
		continue_button.text = "Продолжить — глава %d" % Game.saved_chapter()
	else:
		continue_button.visible = false
	_show_main()
	for node in get_tree().get_nodes_in_group("zombies"):
		var zombie := node as Zombie
		zombie._home = Vector3(randf_range(-4.0, 4.0), 0.0, randf_range(-26.0, -6.0))
		zombie.wander_speed = 0.55
	_drift()
	_start_music()


func _process(_delta: float) -> void:
	# A dying neon sign.
	title.modulate.a = 0.55 if randf() < 0.015 else 1.0


func _drift() -> void:
	var a := ($World/Cams/MenuA as Node3D).global_transform
	var b := ($World/Cams/MenuB as Node3D).global_transform
	camera.global_transform = a
	var tween := create_tween().set_loops()
	tween.tween_property(camera, "global_transform", b, DRIFT_TIME).set_trans(Tween.TRANS_SINE)
	tween.tween_property(camera, "global_transform", a, DRIFT_TIME).set_trans(Tween.TRANS_SINE)


## Heartbeat and a lone piano, faded in under the street ambience and looped.
func _start_music() -> void:
	(music.stream as AudioStreamOggVorbis).loop = true
	music.play()
	create_tween().tween_property(music, "volume_db", -3.0, 4.0).set_ease(Tween.EASE_OUT)


func _show_main() -> void:
	buttons.visible = true
	difficulty_panel.visible = false
	settings.visible = false
	title.visible = true
	$Menu/Subtitle.visible = true
	$Footer.visible = true
	(continue_button if continue_button.visible else new_game_button).grab_focus()


func _show_settings() -> void:
	buttons.visible = false
	title.visible = false
	$Menu/Subtitle.visible = false
	$Footer.visible = false
	settings.call("open")


func _show_difficulty() -> void:
	buttons.visible = false
	difficulty_panel.visible = true
	(difficulty_panel.get_node("Level1") as Button).grab_focus()


func _describe(level: int) -> void:
	difficulty_info.text = DIFFICULTY_TEXT[level]
