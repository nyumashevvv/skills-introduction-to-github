class_name Hud
extends CanvasLayer

signal start_pressed
signal resume_pressed
signal restart_pressed
signal quit_pressed
signal pause_toggle_requested

const HEALTH_COLOR := Color(0.35, 0.9, 0.45)
const LOW_HEALTH_COLOR := Color(1.0, 0.25, 0.2)
const HIT_COLOR := Color(1, 1, 1)
const HEADSHOT_COLOR := Color(1.0, 0.85, 0.2)
const KILL_COLOR := Color(1.0, 0.25, 0.2)

var _damage_flash := 0.0
var _low_health := 0.0
var _hit_marker_time := 0.0
var _message_time := 0.0

@onready var gameplay: Control = $Gameplay
@onready var vignette: ColorRect = $Gameplay/Vignette
@onready var crosshair: Crosshair = $Gameplay/Crosshair
@onready var hit_marker: Control = $Gameplay/HitMarker
@onready var wave_label: Label = $Gameplay/WaveLabel
@onready var enemies_label: Label = $Gameplay/EnemiesLabel
@onready var score_label: Label = $Gameplay/ScoreLabel
@onready var health_label: Label = $Gameplay/HealthBox/HealthLabel
@onready var health_bar: ProgressBar = $Gameplay/HealthBox/HealthBar
@onready var ammo_label: Label = $Gameplay/AmmoBox/AmmoLabel
@onready var reload_label: Label = $Gameplay/AmmoBox/ReloadLabel
@onready var message_label: Label = $Gameplay/MessageLabel
@onready var start_screen: Control = $StartScreen
@onready var best_label: Label = $StartScreen/Center/VBox/BestLabel
@onready var pause_menu: Control = $PauseMenu
@onready var game_over_screen: Control = $GameOverScreen
@onready var game_over_stats: Label = $GameOverScreen/Center/VBox/StatsLabel


func _ready() -> void:
	$StartScreen/Center/VBox/StartButton.pressed.connect(start_pressed.emit)
	$StartScreen/Center/VBox/QuitButton.pressed.connect(quit_pressed.emit)
	$PauseMenu/Center/VBox/ResumeButton.pressed.connect(resume_pressed.emit)
	$PauseMenu/Center/VBox/RestartButton.pressed.connect(restart_pressed.emit)
	$PauseMenu/Center/VBox/QuitButton.pressed.connect(quit_pressed.emit)
	$GameOverScreen/Center/VBox/RestartButton.pressed.connect(restart_pressed.emit)
	$GameOverScreen/Center/VBox/QuitButton.pressed.connect(quit_pressed.emit)
	hit_marker.modulate.a = 0.0
	message_label.modulate.a = 0.0
	reload_label.visible = false
	hide_menus()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		pause_toggle_requested.emit()
		get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	_damage_flash = move_toward(_damage_flash, 0.0, delta * 1.5)
	(vignette.material as ShaderMaterial).set_shader_parameter("intensity", maxf(_damage_flash, _low_health))

	_hit_marker_time = maxf(_hit_marker_time - delta, 0.0)
	hit_marker.modulate.a = clampf(_hit_marker_time / 0.2, 0.0, 1.0)

	_message_time = maxf(_message_time - delta, 0.0)
	message_label.modulate.a = clampf(_message_time / 0.4, 0.0, 1.0)


func bind_weapon(weapon: Weapon) -> void:
	crosshair.weapon = weapon


func set_health(current: int, maximum: int) -> void:
	health_bar.max_value = maximum
	health_bar.value = current
	health_label.text = "♥ %d" % current
	var ratio := float(current) / maximum
	health_bar.modulate = LOW_HEALTH_COLOR if ratio <= 0.3 else HEALTH_COLOR
	_low_health = clampf((0.35 - ratio) / 0.35, 0.0, 1.0) * 0.5 if current > 0 else 0.0


func set_ammo(in_magazine: int, reserve: int) -> void:
	ammo_label.text = "%d / %d" % [in_magazine, reserve]
	ammo_label.modulate = LOW_HEALTH_COLOR if in_magazine <= 5 else Color.WHITE


func set_reloading(reloading: bool) -> void:
	reload_label.visible = reloading


func set_wave(number: int) -> void:
	wave_label.text = "ВОЛНА %d" % number if number > 0 else ""


func set_enemies_left(count: int) -> void:
	enemies_label.text = "Врагов: %d" % count if count > 0 else ""


func set_score(value: int) -> void:
	score_label.text = "Очки: %d" % value


func flash_damage() -> void:
	_damage_flash = 0.7


func show_hit_marker(killed: bool, headshot: bool) -> void:
	_hit_marker_time = 0.35 if killed else 0.2
	hit_marker.self_modulate = KILL_COLOR if killed else (HEADSHOT_COLOR if headshot else HIT_COLOR)
	hit_marker.scale = Vector2.ONE * (1.5 if killed else 1.0)


func show_message(text: String, duration := 2.0) -> void:
	message_label.text = text
	_message_time = duration


func show_start_screen(best_score: int) -> void:
	hide_menus()
	gameplay.visible = false
	best_label.text = "Рекорд: %d" % best_score if best_score > 0 else ""
	start_screen.visible = true
	$StartScreen/Center/VBox/StartButton.grab_focus()


func show_pause_menu() -> void:
	hide_menus()
	pause_menu.visible = true
	$PauseMenu/Center/VBox/ResumeButton.grab_focus()


func show_game_over(wave: int, kills: int, score: int, best_score: int, new_record: bool) -> void:
	hide_menus()
	var text := "Волна: %d\nУничтожено роботов: %d\nОчки: %d" % [wave, kills, score]
	text += "\n\nНОВЫЙ РЕКОРД!" if new_record else "\n\nРекорд: %d" % best_score
	game_over_stats.text = text
	game_over_screen.visible = true
	$GameOverScreen/Center/VBox/RestartButton.grab_focus()


func hide_menus() -> void:
	gameplay.visible = true
	start_screen.visible = false
	pause_menu.visible = false
	game_over_screen.visible = false
