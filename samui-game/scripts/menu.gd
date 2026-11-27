extends Control
## Start menu: continue / new game / settings / controls / about / quit,
## over a picture of the island. Starting a game shows a loading screen.

var main_box: VBoxContainer
var side: PanelContainer
var loading: Control


func _ready() -> void:
	# screenshot and test runs go straight into the game
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shot") or a == "--skip-menu":
			Settings.new_game = OS.get_cmdline_user_args().has("--fresh")
			get_tree().change_scene_to_file.call_deferred("res://main.tscn")
			return
	theme = UiTheme.make()
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := TextureRect.new()
	bg.texture = load("res://ui/menu_bg.jpg")
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	add_child(bg)
	# dark gradient on the left so the text stays readable
	var shade := TextureRect.new()
	var grad := GradientTexture2D.new()
	grad.gradient = Gradient.new()
	grad.gradient.set_color(0, Color(0.01, 0.02, 0.02, 0.92))
	grad.gradient.set_color(1, Color(0.01, 0.02, 0.02, 0.0))
	grad.fill_from = Vector2(0, 0)
	grad.fill_to = Vector2(0.75, 0)
	shade.texture = grad
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.stretch_mode = TextureRect.STRETCH_SCALE
	add_child(shade)

	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	for s in ["left", "right"]:
		margin.add_theme_constant_override("margin_" + s, 64)
	margin.add_theme_constant_override("margin_top", 36)
	margin.add_theme_constant_override("margin_bottom", 56)
	add_child(margin)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 48)
	margin.add_child(row)

	main_box = VBoxContainer.new()
	main_box.add_theme_constant_override("separation", 10)
	main_box.custom_minimum_size = Vector2(380, 0)
	main_box.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(main_box)
	main_box.add_child(UiTheme.label("9.50° N · 100.01° E · 1 : 1", 16, UiTheme.GREEN))
	var title := UiTheme.label("SAMUI RIDE", 66)
	title.autowrap_mode = TextServer.AUTOWRAP_OFF
	main_box.add_child(title)
	var sub := UiTheme.label("Остров Ко Самуи в натуральную величину", 20, UiTheme.MUTED)
	sub.autowrap_mode = TextServer.AUTOWRAP_OFF
	main_box.add_child(sub)
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(0, 14)
	main_box.add_child(gap)
	var cont := UiTheme.button("▶  Продолжить", _continue)
	cont.disabled = not Settings.has_save()
	main_box.add_child(cont)
	if Settings.has_save():
		cont.text = "▶  Продолжить\n      " + Settings.save_summary()
		cont.add_theme_font_size_override("font_size", 19)
		cont.custom_minimum_size.y = 66
	main_box.add_child(UiTheme.button("✚  Новая игра", _new_game))
	main_box.add_child(UiTheme.button("⚙  Настройки", func(): _show(UiTheme.settings_panel(_hide_side))))
	main_box.add_child(UiTheme.button("⌨  Управление", func(): _show(UiTheme.controls_panel(_hide_side))))
	main_box.add_child(UiTheme.button("ℹ  Об игре", func(): _show(_about())))
	main_box.add_child(UiTheme.button("✕  Выход", func(): get_tree().quit()))
	(cont if not cont.disabled else main_box.get_child(main_box.get_child_count() - 5)).grab_focus.call_deferred()

	side = PanelContainer.new()
	side.visible = false
	side.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(side)

	var credit := UiTheme.label("Карта © участники OpenStreetMap (ODbL) · здания: Overture Maps, Google Open Buildings, Microsoft · снимки: Copernicus Sentinel-2 · рельеф: SRTM", 13, UiTheme.MUTED)
	add_child(credit)
	credit.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	credit.offset_left = 64
	credit.offset_top = -40
	credit.offset_bottom = -16


func _show(panel: Control) -> void:
	for c in side.get_children():
		c.queue_free()
	side.add_child(panel)
	side.visible = true


func _hide_side() -> void:
	side.visible = false
	for c in side.get_children():
		c.queue_free()


func _about() -> Control:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	box.custom_minimum_size = Vector2(520, 0)
	box.add_child(UiTheme.label("Об игре", 34))
	box.add_child(UiTheme.label("Ко Самуи (Таиланд) в масштабе 1:1: 24 × 24 км рельефа, 10 тыс. дорог и 76 тыс. зданий с настоящей карты, " +
		"заправки, магазины, рынки, пляжи и водопады на своих местах. Катайся на скутере, развози еду и собирай смотровые площадки.", 18))
	box.add_child(UiTheme.label("Данные: OpenStreetMap (ODbL), Overture Maps (Google Open Buildings, Microsoft), Copernicus Sentinel-2, SRTM. " +
		"Модели сделаны в Blender, звуки синтезированы.", 16, UiTheme.MUTED))
	box.add_child(UiTheme.button("← Назад", _hide_side, 420))
	return box


func _continue() -> void:
	Settings.new_game = false
	_start()


func _new_game() -> void:
	if not Settings.has_save():
		Settings.new_game = true
		_start()
		return
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 14)
	box.custom_minimum_size = Vector2(460, 0)
	box.add_child(UiTheme.label("Начать заново?", 30))
	box.add_child(UiTheme.label("Деньги, находки и доставки из сохранения будут сброшены.", 18, UiTheme.MUTED))
	box.add_child(UiTheme.button("Да, новая игра", func():
		Settings.new_game = true
		_start(), 420))
	box.add_child(UiTheme.button("Отмена", _hide_side, 420))
	_show(box)


func _start() -> void:
	loading = ColorRect.new()
	loading.color = Color(0.01, 0.02, 0.02, 0.85)
	loading.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(loading)
	var l := UiTheme.label("Загружаем остров…", 34)
	l.set_anchors_preset(Control.PRESET_CENTER)
	l.position -= Vector2(150, 20)
	loading.add_child(l)
	var hint := UiTheme.label("рельеф, 10 тыс. дорог, 76 тыс. зданий — это займёт несколько секунд", 17, UiTheme.MUTED)
	hint.set_anchors_preset(Control.PRESET_CENTER)
	hint.position += Vector2(-280, 30)
	hint.size.x = 600
	loading.add_child(hint)
	# let the loading screen draw before the heavy work starts
	await get_tree().process_frame
	await get_tree().process_frame
	get_tree().change_scene_to_file("res://main.tscn")
