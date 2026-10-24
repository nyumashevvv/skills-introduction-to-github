extends Node
## Global game flow (autoload "Game"): chapters, checkpoints and the save file.

const LEVELS: Array[String] = [
	"res://scenes/levels/level_1_outskirts.tscn",
	"res://scenes/levels/level_2_station.tscn",
	"res://scenes/levels/level_3_mall.tscn",
	"res://scenes/levels/level_3_hospital.tscn",
	"res://scenes/levels/level_4_subway.tscn",
	"res://scenes/levels/level_5_stadium.tscn",
]
const MAIN_MENU := "res://scenes/ui/main_menu.tscn"
const ENDING := "res://scenes/ui/ending.tscn"
const SAVE_PATH := "user://progress.cfg"
const CUTSCENE := "res://scenes/ui/intro_cutscene.tscn"
const ENDING_CUTSCENE := "res://scenes/ui/ending_cutscene.tscn"

enum Difficulty { EASY, NORMAL, HARD }
const DIFFICULTY_NAMES: Array[String] = ["Лёгкая", "Нормальная", "Сложная"]
## Multipliers per difficulty: zombie health and speed, damage the player takes, ammo in pickups.
const DIFFICULTY_TUNING: Array[Dictionary] = [
	{"health": 0.7, "speed": 0.9, "damage": 0.55, "ammo": 1.5},
	{"health": 1.0, "speed": 1.0, "damage": 1.0, "ammo": 1.0},
	{"health": 1.35, "speed": 1.12, "damage": 1.5, "ammo": 0.7},
]

var current_level := 0
var difficulty := Difficulty.NORMAL
## Player loadout captured when the current chapter started. Empty means "use the level's defaults".
var checkpoint: Dictionary = {}
var kills := 0
var play_time := 0.0

var _kills_at_level_start := 0


func _process(delta: float) -> void:
	if get_tree().current_scene is Level and not get_tree().paused:
		play_time += delta


func register_kill() -> void:
	kills += 1


## Called by every level when it loads, so restarting a chapter rolls the kill counter back.
func level_started() -> void:
	_kills_at_level_start = kills


func tuning(key: String) -> float:
	return DIFFICULTY_TUNING[difficulty][key]


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func saved_chapter() -> int:
	var config := ConfigFile.new()
	if config.load(SAVE_PATH) != OK:
		return 0
	return int(config.get_value("progress", "level", 0)) + 1


func new_game(level_difficulty := Difficulty.NORMAL, with_cutscene := true) -> void:
	difficulty = level_difficulty
	current_level = 0
	checkpoint = {}
	kills = 0
	play_time = 0.0
	if with_cutscene:
		_change_scene(CUTSCENE)
	else:
		_change_to_level()


## Called by the intro cutscene when it ends or is skipped.
func start_first_chapter() -> void:
	_change_to_level()


## Called by the ending cutscene when it ends or is skipped.
func show_ending() -> void:
	_change_scene(ENDING)


func continue_game() -> void:
	var config := ConfigFile.new()
	if config.load(SAVE_PATH) != OK:
		new_game()
		return
	current_level = config.get_value("progress", "level", 0)
	difficulty = config.get_value("progress", "difficulty", Difficulty.NORMAL)
	checkpoint = config.get_value("progress", "checkpoint", {})
	kills = config.get_value("progress", "kills", 0)
	play_time = config.get_value("progress", "time", 0.0)
	_change_to_level()


func complete_level(player_state: Dictionary) -> void:
	current_level += 1
	checkpoint = player_state
	if current_level >= LEVELS.size():
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))
		_change_scene(ENDING_CUTSCENE)
		return
	_save()
	_change_to_level()


func restart_level() -> void:
	kills = _kills_at_level_start
	get_tree().paused = false
	get_tree().reload_current_scene()


func go_to_menu() -> void:
	_change_scene(MAIN_MENU)


func _change_to_level() -> void:
	_change_scene(LEVELS[current_level])


func _change_scene(path: String) -> void:
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	get_tree().change_scene_to_file(path)


func _save() -> void:
	var config := ConfigFile.new()
	config.set_value("progress", "level", current_level)
	config.set_value("progress", "difficulty", difficulty)
	config.set_value("progress", "checkpoint", checkpoint)
	config.set_value("progress", "kills", kills)
	config.set_value("progress", "time", play_time)
	config.save(SAVE_PATH)
