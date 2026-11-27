extends Node
## Autoload "Settings": player options saved to user://settings.cfg, plus how
## the next game should start (new game or continue).

const PATH := "user://settings.cfg"
const SAVE_PATH := "user://samui_ride.save"

var quality := 2                # 0 low, 1 medium, 2 high
var master_volume := 0.8        # 0..1
var fullscreen := false
var vsync := true
var start_hour := 16.5          # time of day for a new game
var new_game := false           # set by the start menu


func _ready() -> void:
	var cf := ConfigFile.new()
	if cf.load(PATH) == OK:
		quality = cf.get_value("graphics", "quality", quality)
		fullscreen = cf.get_value("graphics", "fullscreen", fullscreen)
		vsync = cf.get_value("graphics", "vsync", vsync)
		master_volume = cf.get_value("audio", "master", master_volume)
		start_hour = cf.get_value("game", "start_hour", start_hour)
	apply()


func save() -> void:
	var cf := ConfigFile.new()
	cf.set_value("graphics", "quality", quality)
	cf.set_value("graphics", "fullscreen", fullscreen)
	cf.set_value("graphics", "vsync", vsync)
	cf.set_value("audio", "master", master_volume)
	cf.set_value("game", "start_hour", start_hour)
	cf.save(PATH)


func apply() -> void:
	AudioServer.set_bus_volume_db(0, linear_to_db(maxf(master_volume, 0.0001)))
	AudioServer.set_bus_mute(0, master_volume <= 0.001)
	if DisplayServer.get_name() != "headless":
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if fullscreen else DisplayServer.WINDOW_MODE_WINDOWED)
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if vsync else DisplayServer.VSYNC_DISABLED)


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func save_summary() -> String:
	if not has_save():
		return ""
	var d = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if typeof(d) != TYPE_DICTIONARY:
		return ""
	return "%d ฿ · %.1f км · доставок %d · находок %d" % [
		d.get("money", 0), d.get("odo", 0.0) / 1000.0, d.get("deliveries", 0), d.get("found", []).size()]
