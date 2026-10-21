extends Control


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var minutes := int(Game.play_time) / 60
	var seconds := int(Game.play_time) % 60
	$Center/VBox/Stats.text = "Время в пути: %d:%02d\nУпокоено мертвецов: %d" % [minutes, seconds, Game.kills]
	$Center/VBox/MenuButton.pressed.connect(Game.go_to_menu)
	$Center/VBox/MenuButton.grab_focus()
	modulate.a = 0.0
	create_tween().tween_property(self, "modulate:a", 1.0, 2.0)
