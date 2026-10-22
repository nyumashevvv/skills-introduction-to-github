extends PanelContainer
## Options screen shared by the main menu and the pause menu. Builds its rows from [constant ROWS]
## and writes every change straight to the Settings autoload.

signal closed

const RUSSO := preload("res://fonts/RussoOne-Regular.ttf")
const ACCENT := Color(0.95, 0.3, 0.2)
## [section] or [key, label, kind, min, max, step, unit]; kind: slider (shown ×100 when unit is "%"), toggle, quality.
const ROWS := [
	["ЗВУК"],
	["master", "Общая громкость", "slider", 0.0, 1.0, 0.05, "%"],
	["music", "Музыка", "slider", 0.0, 1.0, 0.05, "%"],
	["voice", "Голоса и рация", "slider", 0.0, 1.0, 0.05, "%"],
	["ГРАФИКА"],
	["quality", "Качество", "quality"],
	["fullscreen", "Полный экран", "toggle"],
	["vsync", "Вертикальная синхронизация", "toggle"],
	["render_scale", "Разрешение 3D", "slider", 0.5, 1.0, 0.05, "%"],
	["brightness", "Яркость", "slider", 0.6, 1.6, 0.05, "%"],
	["fov", "Поле зрения", "slider", 60.0, 100.0, 1.0, "°"],
	["УПРАВЛЕНИЕ"],
	["sensitivity", "Чувствительность мыши", "slider", 0.3, 2.0, 0.05, "%"],
]

var _first_control: Control


func _ready() -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.03, 0.03, 0.035, 0.92)
	style.border_width_left = 5
	style.border_color = ACCENT
	style.content_margin_left = 28.0
	style.content_margin_right = 28.0
	style.content_margin_top = 18.0
	style.content_margin_bottom = 18.0
	add_theme_stylebox_override("panel", style)
	custom_minimum_size = Vector2(620, 0)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	add_child(box)
	var title := Label.new()
	title.text = "НАСТРОЙКИ"
	title.add_theme_font_override("font", RUSSO)
	title.add_theme_font_size_override("font_size", 34)
	box.add_child(title)
	for row: Array in ROWS:
		if row.size() == 1:
			box.add_child(_section(row[0]))
		else:
			box.add_child(_row(row))
	var back := Button.new()
	back.text = "НАЗАД"
	back.custom_minimum_size = Vector2(200, 0)
	back.size_flags_horizontal = Control.SIZE_SHRINK_END
	back.pressed.connect(close)
	box.add_child(back)


func open() -> void:
	visible = true
	if _first_control != null:
		_first_control.grab_focus()


func close() -> void:
	visible = false
	closed.emit()


func _unhandled_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		get_viewport().set_input_as_handled()
		close()


func _section(text: String) -> Control:
	var label := Label.new()
	label.text = text
	label.add_theme_font_override("font", RUSSO)
	label.add_theme_font_size_override("font_size", 15)
	label.add_theme_color_override("font_color", ACCENT)
	return label


func _row(row: Array) -> Control:
	var key: String = row[0]
	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", 14)
	var name_label := Label.new()
	name_label.text = row[1]
	name_label.custom_minimum_size = Vector2(250, 0)
	name_label.add_theme_font_size_override("font_size", 19)
	line.add_child(name_label)
	var control: Control
	match row[2]:
		"slider":
			var slider := HSlider.new()
			slider.min_value = row[3]
			slider.max_value = row[4]
			slider.step = row[5]
			slider.value = Settings.get_value(key)
			slider.custom_minimum_size = Vector2(230, 24)
			slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
			var value_label := Label.new()
			value_label.custom_minimum_size = Vector2(60, 0)
			var unit: String = row[6]
			var show := func(v: float) -> void:
				value_label.text = ("%d%%" % roundi(v * 100.0)) if unit == "%" else ("%d%s" % [roundi(v), unit])
			show.call(slider.value)
			slider.value_changed.connect(func(v: float) -> void:
				show.call(v)
				Settings.set_value(key, v))
			line.add_child(slider)
			line.add_child(value_label)
			control = slider
		"toggle":
			var toggle := CheckButton.new()
			toggle.button_pressed = Settings.get_value(key)
			toggle.toggled.connect(func(on: bool) -> void: Settings.set_value(key, on))
			line.add_child(toggle)
			control = toggle
		"quality":
			var option := OptionButton.new()
			for name: String in Settings.QUALITY_NAMES:
				option.add_item(name)
			option.selected = Settings.get_value(key)
			option.custom_minimum_size = Vector2(230, 0)
			option.item_selected.connect(func(index: int) -> void: Settings.set_value(key, index))
			line.add_child(option)
			control = option
	if _first_control == null:
		_first_control = control
	return line
