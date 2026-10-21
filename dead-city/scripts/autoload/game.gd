extends Node
## Global game flow (autoload "Game"): chapters, checkpoints and the save file.

const LEVELS: Array[String] = [
	"res://scenes/levels/level_1_outskirts.tscn",
	"res://scenes/levels/level_2_station.tscn",
	"res://scenes/levels/level_3_stadium.tscn",
]
const MAIN_MENU := "res://scenes/ui/main_menu.tscn"
const ENDING := "res://scenes/ui/ending.tscn"
const SAVE_PATH := "user://progress.cfg"

var current_level := 0
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


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func saved_chapter() -> int:
	var config := ConfigFile.new()
	if config.load(SAVE_PATH) != OK:
		return 0
	return int(config.get_value("progress", "level", 0)) + 1


func new_game() -> void:
	current_level = 0
	checkpoint = {}
	kills = 0
	play_time = 0.0
	_change_to_level()


func continue_game() -> void:
	var config := ConfigFile.new()
	if config.load(SAVE_PATH) != OK:
		new_game()
		return
	current_level = config.get_value("progress", "level", 0)
	checkpoint = config.get_value("progress", "checkpoint", {})
	kills = config.get_value("progress", "kills", 0)
	play_time = config.get_value("progress", "time", 0.0)
	_change_to_level()


func complete_level(player_state: Dictionary) -> void:
	current_level += 1
	checkpoint = player_state
	if current_level >= LEVELS.size():
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))
		_change_scene(ENDING)
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
	config.set_value("progress", "checkpoint", checkpoint)
	config.set_value("progress", "kills", kills)
	config.set_value("progress", "time", play_time)
	config.save(SAVE_PATH)
