extends Node
## Player options (autoload "Settings"): sound volumes, graphics quality and controls.
## Saved to user://settings.cfg and applied at start-up, whenever a value changes and to every
## WorldEnvironment / light / camera that enters the tree.

signal changed

const PATH := "user://settings.cfg"
const QUALITY_NAMES: Array[String] = ["Низкое", "Среднее", "Высокое"]
const DEFAULTS := {
	"master": 0.8, "music": 0.7, "voice": 1.0,
	"fullscreen": false, "vsync": true, "quality": 2, "render_scale": 1.0, "brightness": 1.0, "fov": 75.0,
	"sensitivity": 1.0,
}

var values := DEFAULTS.duplicate()


func _ready() -> void:
	var config := ConfigFile.new()
	if config.load(PATH) == OK:
		for key: String in DEFAULTS:
			values[key] = config.get_value("settings", key, DEFAULTS[key])
	get_tree().node_added.connect(_on_node_added)
	apply()


func get_value(key: String) -> Variant:
	return values[key]


func set_value(key: String, value: Variant) -> void:
	values[key] = value
	apply()
	save()
	changed.emit()


func save() -> void:
	var config := ConfigFile.new()
	for key: String in values:
		config.set_value("settings", key, values[key])
	config.save(PATH)


func apply() -> void:
	for bus in [["Master", "master"], ["Music", "music"], ["Voice", "voice"]]:
		var index := AudioServer.get_bus_index(bus[0])
		if index >= 0:
			AudioServer.set_bus_volume_db(index, linear_to_db(maxf(values[bus[1]], 0.0001)))
	if DisplayServer.get_name() != "headless":
		var mode := DisplayServer.WINDOW_MODE_FULLSCREEN if values["fullscreen"] else DisplayServer.WINDOW_MODE_WINDOWED
		if DisplayServer.window_get_mode() != mode:
			DisplayServer.window_set_mode(mode)
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if values["vsync"] else DisplayServer.VSYNC_DISABLED)
	var root := get_tree().root
	root.scaling_3d_scale = values["render_scale"]
	var quality: int = values["quality"]
	root.msaa_3d = [Viewport.MSAA_DISABLED, Viewport.MSAA_2X, Viewport.MSAA_4X][quality]
	root.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED if quality == 0 else Viewport.SCREEN_SPACE_AA_FXAA
	RenderingServer.directional_shadow_atlas_set_size([1024, 2048, 4096][quality], true)
	for node in get_tree().root.find_children("*", "WorldEnvironment", true, false):
		_tune_environment(node as WorldEnvironment)
	for node in get_tree().root.find_children("*", "DirectionalLight3D", true, false):
		_tune_light(node as Light3D)
	for node in get_tree().root.find_children("*", "Camera3D", true, false):
		_tune_camera(node as Camera3D)


func _on_node_added(node: Node) -> void:
	if node is WorldEnvironment:
		_tune_environment.call_deferred(node)
	elif node is DirectionalLight3D:
		_tune_light.call_deferred(node)
	elif node is Camera3D:
		_tune_camera.call_deferred(node)


func _tune_environment(world: WorldEnvironment) -> void:
	var env := world.environment
	if env == null:
		return
	# Remember what the level asked for, then scale it by the options.
	if not env.has_meta("base_exposure"):
		env.set_meta("base_exposure", env.tonemap_exposure)
		env.set_meta("base_ssao", env.ssao_enabled)
		env.set_meta("base_glow", env.glow_enabled)
	var quality: int = values["quality"]
	env.tonemap_exposure = env.get_meta("base_exposure") * float(values["brightness"])
	env.ssao_enabled = env.get_meta("base_ssao") and quality >= 2
	env.glow_enabled = env.get_meta("base_glow") and quality >= 1


func _tune_light(light: Light3D) -> void:
	if not is_instance_valid(light):
		return
	if not light.has_meta("base_shadow"):
		light.set_meta("base_shadow", light.shadow_enabled)
	light.shadow_enabled = light.get_meta("base_shadow") and int(values["quality"]) >= 1


func _tune_camera(camera: Camera3D) -> void:
	# Only the player's camera follows the field-of-view option.
	if is_instance_valid(camera) and camera.get_parent() != null and camera.get_parent().name == "Head":
		camera.fov = values["fov"]
