extends SceneTree
# Writes the input map into project.godot:
#   godot --headless --path . --script tools/setup_input.gd

func key(code: Key) -> InputEventKey:
	var e := InputEventKey.new()
	e.physical_keycode = code
	e.device = -1
	return e

func mouse(button: MouseButton) -> InputEventMouseButton:
	var e := InputEventMouseButton.new()
	e.button_index = button
	e.device = -1
	return e

func _initialize() -> void:
	var actions := {
		"move_forward": [key(KEY_W), key(KEY_UP)],
		"move_back": [key(KEY_S), key(KEY_DOWN)],
		"move_left": [key(KEY_A), key(KEY_LEFT)],
		"move_right": [key(KEY_D), key(KEY_RIGHT)],
		"jump": [key(KEY_SPACE)],
		"sprint": [key(KEY_SHIFT)],
		"crouch": [key(KEY_C), key(KEY_CTRL)],
		"shoot": [mouse(MOUSE_BUTTON_LEFT)],
		"reload": [key(KEY_R)],
		"interact": [key(KEY_E)],
		"flashlight": [key(KEY_F)],
		"weapon_1": [key(KEY_1)],
		"weapon_2": [key(KEY_2)],
		"weapon_3": [key(KEY_3)],
		"weapon_4": [key(KEY_4)],
		"weapon_5": [key(KEY_5)],
		"weapon_6": [key(KEY_6)],
		"weapon_7": [key(KEY_7)],
		"weapon_8": [key(KEY_8)],
		"weapon_9": [key(KEY_9)],
		"aim": [mouse(MOUSE_BUTTON_RIGHT)],
		"weapon_next": [mouse(MOUSE_BUTTON_WHEEL_DOWN)],
		"weapon_prev": [mouse(MOUSE_BUTTON_WHEEL_UP)],
		"pause": [key(KEY_ESCAPE), key(KEY_P)],
	}
	for action: String in actions:
		ProjectSettings.set_setting("input/" + action, {"deadzone": 0.2, "events": actions[action]})
	ProjectSettings.save()
	quit()
