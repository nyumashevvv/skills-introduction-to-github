class_name UiTheme
## Shared look for the start and pause menus: black and green, like the rider's outfit.

const BG := Color(0.03, 0.05, 0.045, 0.88)
const PANEL := Color(0.06, 0.08, 0.075, 0.94)
const GREEN := Color(0.12, 0.81, 0.38)
const GREEN_DIM := Color(0.08, 0.42, 0.22)
const TEXT := Color(0.93, 0.96, 0.94)
const MUTED := Color(0.62, 0.70, 0.66)


static func make() -> Theme:
	var t := Theme.new()
	t.default_font_size = 20
	var normal := _box(Color(0.10, 0.13, 0.12), Color(0.18, 0.24, 0.21), 1)
	var hover := _box(Color(0.10, 0.20, 0.15), GREEN, 2)
	var pressed := _box(GREEN_DIM, GREEN, 2)
	var focus := _box(Color(0, 0, 0, 0), GREEN, 2)
	var disabled := _box(Color(0.07, 0.08, 0.08), Color(0.12, 0.14, 0.13), 1)
	for type in ["Button", "OptionButton", "CheckButton"]:
		t.set_stylebox("normal", type, normal)
		t.set_stylebox("hover", type, hover)
		t.set_stylebox("pressed", type, pressed)
		t.set_stylebox("focus", type, focus)
		t.set_stylebox("disabled", type, disabled)
		t.set_color("font_color", type, TEXT)
		t.set_color("font_hover_color", type, Color.WHITE)
		t.set_color("font_pressed_color", type, Color.WHITE)
		t.set_color("font_focus_color", type, Color.WHITE)
		t.set_color("font_disabled_color", type, Color(0.4, 0.45, 0.43))
	# toggles: the switch shows the state, the box must not look "pressed"
	t.set_stylebox("pressed", "CheckButton", normal)
	t.set_stylebox("hover_pressed", "CheckButton", hover)
	t.set_stylebox("panel", "PanelContainer", _box(PANEL, Color(0.14, 0.2, 0.17), 1, 10))
	t.set_color("font_color", "Label", TEXT)
	var grab := StyleBoxFlat.new()
	grab.bg_color = GREEN
	grab.set_corner_radius_all(8)
	var track := StyleBoxFlat.new()
	track.bg_color = Color(0.15, 0.2, 0.18)
	track.set_corner_radius_all(3)
	track.content_margin_top = 3
	track.content_margin_bottom = 3
	t.set_stylebox("slider", "HSlider", track)
	t.set_stylebox("grabber_area", "HSlider", grab)
	t.set_stylebox("grabber_area_highlight", "HSlider", grab)
	return t


static func _box(bg: Color, border: Color, bw: int, radius := 6) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(bw)
	s.set_corner_radius_all(radius)
	s.content_margin_left = 18
	s.content_margin_right = 18
	s.content_margin_top = 10
	s.content_margin_bottom = 10
	return s


static func label(text: String, size := 20, color := TEXT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l


static func button(text: String, cb: Callable, min_w := 320) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(min_w, 48)
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.pressed.connect(cb)
	return b


## Settings panel shared by both menus. `on_change` gets the new quality level.
static func settings_panel(on_back: Callable, on_quality := Callable()) -> Control:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 14)
	box.add_child(label("Настройки", 34))
	var q := OptionButton.new()
	for item in ["Качество: низкое", "Качество: среднее", "Качество: высокое"]:
		q.add_item(item)
	q.selected = Settings.quality
	q.custom_minimum_size = Vector2(420, 50)
	q.item_selected.connect(func(i):
		Settings.quality = i
		Settings.save()
		if on_quality.is_valid():
			on_quality.call(i))
	box.add_child(q)
	var vol_row := HBoxContainer.new()
	vol_row.add_theme_constant_override("separation", 16)
	var vol_lbl := label("Громкость %d%%" % int(Settings.master_volume * 100), 20)
	vol_lbl.custom_minimum_size = Vector2(170, 0)
	var vol := HSlider.new()
	vol.min_value = 0.0
	vol.max_value = 1.0
	vol.step = 0.05
	vol.value = Settings.master_volume
	vol.custom_minimum_size = Vector2(230, 30)
	vol.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	vol.value_changed.connect(func(v):
		Settings.master_volume = v
		vol_lbl.text = "Громкость %d%%" % int(v * 100)
		Settings.apply()
		Settings.save())
	vol_row.add_child(vol_lbl)
	vol_row.add_child(vol)
	box.add_child(vol_row)
	var fs := CheckButton.new()
	fs.text = "Полный экран"
	fs.button_pressed = Settings.fullscreen
	fs.toggled.connect(func(on):
		Settings.fullscreen = on
		Settings.apply()
		Settings.save())
	box.add_child(fs)
	var vs := CheckButton.new()
	vs.text = "Вертикальная синхронизация"
	vs.button_pressed = Settings.vsync
	vs.toggled.connect(func(on):
		Settings.vsync = on
		Settings.apply()
		Settings.save())
	box.add_child(vs)
	var th := OptionButton.new()
	var hours := [[7.0, "Утро (7:00)"], [12.0, "Полдень (12:00)"], [16.5, "Вечер (16:30)"], [18.0, "Закат (18:00)"], [21.0, "Ночь (21:00)"]]
	for h in hours:
		th.add_item("Новая игра начинается: " + h[1])
	th.selected = 2
	for i in hours.size():
		if absf(hours[i][0] - Settings.start_hour) < 0.01:
			th.selected = i
	th.custom_minimum_size = Vector2(420, 50)
	th.item_selected.connect(func(i):
		Settings.start_hour = hours[i][0]
		Settings.save())
	box.add_child(th)
	box.add_child(button("← Назад", on_back, 420))
	return box


static func controls_panel(on_back: Callable) -> Control:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	box.add_child(label("Управление", 34))
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 28)
	grid.add_theme_constant_override("v_separation", 6)
	for row in [["W / S, ↑ / ↓", "газ / тормоз, задний ход"], ["A / D, ← / →", "руль"], ["Shift", "турбо ×4"],
			["M или Tab", "карта острова, клик — телепорт"], ["C", "сменить камеру"], ["R", "вернуться на дорогу"],
			["J", "взять / отменить заказ"], ["H", "гудок"], ["N", "+1 час игрового времени"],
			["Q", "качество графики"], ["Esc", "пауза и меню"]]:
		grid.add_child(label(row[0], 20, GREEN))
		grid.add_child(label(row[1], 20))
	box.add_child(grid)
	box.add_child(label("Чтобы заправиться, остановись у колонки или у полки с бутылками.", 17, MUTED))
	box.add_child(button("← Назад", on_back, 420))
	return box
