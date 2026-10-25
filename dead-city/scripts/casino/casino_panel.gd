class_name CasinoPanel
extends Control
## Base of the casino screens (slots, roulette, cashier): a framed window over the paused game with the chip count,
## a line for results and an exit button. Opened by CasinoMachine through Level.open_panel; Esc closes it too.

const RUSSO := preload("res://fonts/RussoOne-Regular.ttf")
const GOLD := Color(1.0, 0.78, 0.3)
const RED := Color(0.75, 0.08, 0.08)
const FELT := Color(0.05, 0.35, 0.18)

var player: Player
var chips_label: Label
var message: Label
var _sound: AudioStreamPlayer


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_anchors_preset(Control.PRESET_FULL_RECT)


func _ready() -> void:
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.65)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var frame := PanelContainer.new()
	frame.add_theme_stylebox_override("panel", box_style(Color(0.07, 0.03, 0.05, 0.97), GOLD, 3, 12, 22))
	center.add_child(frame)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	frame.add_child(box)
	box.add_child(make_label(title(), 38, GOLD, RUSSO))
	chips_label = make_label("", 24, Color.WHITE, RUSSO)
	box.add_child(chips_label)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 10)
	box.add_child(content)
	message = make_label(" ", 22, Color(0.85, 0.9, 1.0))
	box.add_child(message)
	var exit := make_button("Выйти  [Esc]", close_panel, 220)
	exit.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	box.add_child(exit)
	_sound = AudioStreamPlayer.new()
	add_child(_sound)
	build(content)
	refresh_chips()


## The window's heading.
func title() -> String:
	return ""


## Fills the window; overridden by each game.
func build(_box: VBoxContainer) -> void:
	pass


func refresh_chips() -> void:
	chips_label.text = "Фишки: %d" % Game.chips


func say(text: String, color := Color(0.85, 0.9, 1.0)) -> void:
	message.text = text
	message.add_theme_color_override("font_color", color)


func play(sound: String) -> void:
	_sound.stream = load("res://sounds/%s.wav" % sound)
	_sound.play()


func close_panel() -> void:
	queue_free()


static func make_label(text: String, font_size: int, color := Color.WHITE, font: Font = null) -> Label:
	var label := Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	if font != null:
		label.add_theme_font_override("font", font)
	return label


static func make_button(text: String, on_press: Callable, width := 0, color := Color(0.2, 0.12, 0.16)) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(width, 40)
	button.add_theme_font_size_override("font_size", 20)
	button.add_theme_stylebox_override("normal", box_style(color, GOLD.darkened(0.4), 1, 6, 8))
	button.add_theme_stylebox_override("hover", box_style(color.lightened(0.2), GOLD, 2, 6, 8))
	button.add_theme_stylebox_override("pressed", box_style(color.darkened(0.3), GOLD, 2, 6, 8))
	button.add_theme_stylebox_override("focus", box_style(Color(0, 0, 0, 0), GOLD, 2, 6, 8))
	button.add_theme_stylebox_override("disabled", box_style(color.darkened(0.5), Color(0.3, 0.3, 0.3), 1, 6, 8))
	button.pressed.connect(on_press)
	return button


static func box_style(bg: Color, border: Color, border_width: int, radius: int, margin: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	style.set_border_width_all(border_width)
	style.set_corner_radius_all(radius)
	style.set_content_margin_all(margin)
	return style
