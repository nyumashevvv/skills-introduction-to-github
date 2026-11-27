class_name PauseMenu
extends CanvasLayer
## Esc in the game: pauses everything and offers resume / settings / controls /
## save & main menu / save & quit.

var main: Node
var root: Control
var side: PanelContainer
var buttons: VBoxContainer


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 10
	root = Control.new()
	root.theme = UiTheme.make()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.visible = false
	add_child(root)
	var dim := ColorRect.new()
	dim.color = Color(0.01, 0.02, 0.02, 0.6)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(center)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 32)
	center.add_child(row)
	var panel := PanelContainer.new()
	row.add_child(panel)
	buttons = VBoxContainer.new()
	buttons.add_theme_constant_override("separation", 12)
	panel.add_child(buttons)
	buttons.add_child(UiTheme.label("Пауза", 38))
	buttons.add_child(UiTheme.button("▶  Продолжить", toggle))
	buttons.add_child(UiTheme.button("⚙  Настройки", func(): _show(UiTheme.settings_panel(_hide_side, func(q): main.set_quality(q)))))
	buttons.add_child(UiTheme.button("⌨  Управление", func(): _show(UiTheme.controls_panel(_hide_side))))
	buttons.add_child(UiTheme.button("⌂  Сохранить и выйти в меню", _to_menu))
	buttons.add_child(UiTheme.button("✕  Сохранить и выйти из игры", _quit))
	side = PanelContainer.new()
	side.visible = false
	row.add_child(side)


func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("ui_cancel"):
		if side.visible:
			_hide_side()
		else:
			toggle()
		get_viewport().set_input_as_handled()


func toggle() -> void:
	root.visible = not root.visible
	get_tree().paused = root.visible
	_hide_side()
	if root.visible:
		buttons.get_child(1).grab_focus()


func _show(p: Control) -> void:
	for c in side.get_children():
		c.queue_free()
	side.add_child(p)
	side.visible = true


func _hide_side() -> void:
	side.visible = false
	for c in side.get_children():
		c.queue_free()


func _to_menu() -> void:
	main.missions.save_game()
	get_tree().paused = false
	get_tree().change_scene_to_file("res://menu.tscn")


func _quit() -> void:
	main.missions.save_game()
	get_tree().quit()
