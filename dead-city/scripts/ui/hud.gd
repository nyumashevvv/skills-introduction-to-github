class_name Hud
extends CanvasLayer

signal continue_pressed
signal resume_pressed
signal restart_pressed
signal menu_pressed
signal pause_toggle_requested

const HEALTH_COLOR := Color(0.85, 0.85, 0.8)
const LOW_COLOR := Color(1.0, 0.25, 0.2)
const HIT_COLOR := Color(1, 1, 1)
const HEADSHOT_COLOR := Color(1.0, 0.8, 0.2)
const KILL_COLOR := Color(1.0, 0.2, 0.15)
const SPEAKER_COLOR := "#e8c06a"
const ACCENT := Color(0.85, 0.2, 0.14)
const OBJECTIVE_X := 24.0
const RUSSO := preload("res://fonts/RussoOne-Regular.ttf")

var _damage_flash := 0.0
var _low_health := 0.0
var _hit_marker_time := 0.0
var _subtitle_time := 0.0
var _pickup_time := 0.0
var _subtitle_queue: Array[Array] = []
var _holder: WeaponHolder
var _objective_flash := 0.0
var _slot_on: StyleBoxFlat
var _slot_off: StyleBoxFlat

@onready var gameplay: Control = $Gameplay
@onready var vignette: ColorRect = $Gameplay/Vignette
@onready var crosshair: Crosshair = $Gameplay/Crosshair
@onready var hit_marker: Control = $Gameplay/HitMarker
@onready var objective_label: Label = $Gameplay/ObjectiveBox/VBox/ObjectiveLabel
@onready var objective_header: Label = $Gameplay/ObjectiveBox/VBox/Header
@onready var objective_box: Control = $Gameplay/ObjectiveBox
@onready var timer_label: Label = $Gameplay/TimerLabel
@onready var boss_box: Control = $Gameplay/BossBox
@onready var boss_label: Label = $Gameplay/BossBox/BossLabel
@onready var boss_bar: SegmentBar = $Gameplay/BossBox/BossBar
@onready var prompt_label: Label = $Gameplay/PromptLabel
@onready var pickup_label: Label = $Gameplay/PickupLabel
@onready var subtitle_panel: PanelContainer = $Gameplay/Subtitle
@onready var subtitle_label: RichTextLabel = $Gameplay/Subtitle/Text
@onready var health_label: Label = $Gameplay/HealthBox/HBox/VBox/HealthLabel
@onready var health_bar: SegmentBar = $Gameplay/HealthBox/HBox/VBox/HealthBar
@onready var health_cross: Label = $Gameplay/HealthBox/HBox/Cross
@onready var weapon_label: Label = $Gameplay/WeaponBox/VBox/Row/Side/WeaponLabel
@onready var ammo_label: Label = $Gameplay/WeaponBox/VBox/Row/AmmoLabel
@onready var reserve_label: Label = $Gameplay/WeaponBox/VBox/Row/Side/ReserveLabel
@onready var ammo_pips: AmmoPips = $Gameplay/WeaponBox/VBox/AmmoPips
@onready var reload_label: Label = $Gameplay/WeaponBox/VBox/ReloadLabel
@onready var slots: HBoxContainer = $Gameplay/Slots
@onready var fade: ColorRect = $Fade
@onready var intro_screen: Control = $IntroScreen
@onready var pause_menu: Control = $PauseMenu
@onready var death_screen: Control = $DeathScreen
@onready var radio_sound: AudioStreamPlayer = $RadioSound


func _ready() -> void:
	$IntroScreen/Center/VBox/ContinueButton.pressed.connect(continue_pressed.emit)
	$PauseMenu/Center/VBox/ResumeButton.pressed.connect(resume_pressed.emit)
	$PauseMenu/Center/VBox/RestartButton.pressed.connect(restart_pressed.emit)
	$PauseMenu/Center/VBox/MenuButton.pressed.connect(menu_pressed.emit)
	$DeathScreen/Center/VBox/RestartButton.pressed.connect(restart_pressed.emit)
	$DeathScreen/Center/VBox/MenuButton.pressed.connect(menu_pressed.emit)
	hit_marker.modulate.a = 0.0
	pickup_label.modulate.a = 0.0
	subtitle_panel.modulate.a = 0.0
	reload_label.visible = false
	objective_box.visible = false
	_slot_on = _slot_style(Color(ACCENT, 0.9))
	_slot_off = _slot_style(Color(0, 0, 0, 0.45))
	timer_label.text = ""
	boss_box.visible = false
	prompt_label.text = ""
	fade.color.a = 0.0
	hide_menus()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		pause_toggle_requested.emit()
		get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	_damage_flash = move_toward(_damage_flash, 0.0, delta * 1.5)
	(vignette.material as ShaderMaterial).set_shader_parameter("intensity", maxf(_damage_flash, _low_health))

	_hit_marker_time = maxf(_hit_marker_time - delta, 0.0)
	hit_marker.modulate.a = clampf(_hit_marker_time / 0.2, 0.0, 1.0)

	_pickup_time = maxf(_pickup_time - delta, 0.0)
	pickup_label.modulate.a = clampf(_pickup_time / 0.5, 0.0, 1.0)

	if _subtitle_time > 0.0:
		_subtitle_time -= delta
		subtitle_panel.modulate.a = clampf(_subtitle_time / 0.5, 0.0, 1.0)
		if _subtitle_time <= 0.0 and not _subtitle_queue.is_empty():
			var next: Array = _subtitle_queue.pop_front()
			_show_subtitle_now(next[0], next[1], next[2])

	if _objective_flash > 0.0:
		_objective_flash -= delta
		# "NEW OBJECTIVE" blinks for a moment, then settles back to "OBJECTIVE".
		objective_header.modulate.a = 0.35 + 0.65 * absf(sin(_objective_flash * 6.0)) if _objective_flash > 0.0 else 1.0
		if _objective_flash <= 0.0:
			objective_header.text = "ЦЕЛЬ"
	if reload_label.visible:
		reload_label.modulate.a = 0.5 + 0.5 * absf(sin(Time.get_ticks_msec() * 0.006))

	if _holder != null and _holder.current != null:
		crosshair.spread = _holder.current.spread_deg()
		crosshair.dot_only = not _holder.current.uses_ammo()


func bind_holder(holder: WeaponHolder) -> void:
	_holder = holder
	if holder.current != null:
		set_weapon(holder.current)


func set_health(current: int, maximum: int) -> void:
	health_bar.max_value = maximum
	health_bar.value = current
	health_label.text = "%d" % maxi(current, 0)
	var ratio := float(current) / maximum
	health_bar.fill_color = LOW_COLOR if ratio <= 0.3 else HEALTH_COLOR
	health_label.modulate = LOW_COLOR if ratio <= 0.3 else Color.WHITE
	health_bar.queue_redraw()
	_low_health = clampf((0.35 - ratio) / 0.35, 0.0, 1.0) * 0.5 if current > 0 else 0.0


func set_weapon(weapon: Weapon) -> void:
	weapon_label.text = weapon.display_name.to_upper()
	update_ammo(weapon)
	reload_label.visible = weapon.is_reloading
	_highlight_slot(weapon)


func update_ammo(weapon: Weapon) -> void:
	if _holder != null and weapon != _holder.current:
		return
	var uses_ammo := weapon.uses_ammo()
	ammo_label.visible = uses_ammo
	ammo_pips.visible = uses_ammo
	reserve_label.text = "/ %d" % weapon.reserve if uses_ammo else "БЕСШУМНО"
	if not uses_ammo:
		return
	ammo_label.text = "%d" % weapon.ammo
	ammo_label.modulate = LOW_COLOR if weapon.ammo <= weapon.magazine_size / 5 else Color.WHITE
	reserve_label.modulate = LOW_COLOR if weapon.reserve == 0 else Color.WHITE
	ammo_pips.capacity = weapon.magazine_size
	ammo_pips.count = weapon.ammo


func set_reloading(weapon: Weapon, reloading: bool) -> void:
	if _holder == null or weapon == _holder.current:
		reload_label.visible = reloading


func set_inventory(weapons: Array[Weapon]) -> void:
	for child in slots.get_children():
		slots.remove_child(child)
		child.queue_free()
	for weapon in weapons:
		# A small plate per weapon: slot number in a block font, then the name.
		var plate := PanelContainer.new()
		plate.set_meta("weapon", weapon)
		plate.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 6)
		var number := Label.new()
		number.text = str(weapon.slot)
		number.add_theme_font_override("font", RUSSO)
		number.add_theme_font_size_override("font_size", 15)
		var name_label := Label.new()
		name_label.text = weapon.display_name.to_upper()
		name_label.add_theme_font_size_override("font_size", 14)
		row.add_child(number)
		row.add_child(name_label)
		plate.add_child(row)
		plate.visible = weapon.owned
		slots.add_child(plate)
	if _holder != null and _holder.current != null:
		_highlight_slot(_holder.current)


func set_objective(text: String) -> void:
	var changed := text != objective_label.text
	objective_box.visible = text != ""
	objective_label.text = text
	if changed and text != "":
		objective_header.text = "НОВАЯ ЦЕЛЬ"
		_objective_flash = 3.0
		# Slide in from the left edge.
		objective_box.position.x = -objective_box.size.x
		create_tween().tween_property(objective_box, "position:x", OBJECTIVE_X, 0.35) \
			.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)


func set_timer(text: String) -> void:
	timer_label.text = text


func show_boss(title: String, health: int, max_health: int) -> void:
	boss_box.visible = true
	boss_label.text = title
	boss_bar.max_value = max_health
	boss_bar.value = maxi(health, 0)


func hide_boss() -> void:
	boss_box.visible = false


func set_prompt(text: String) -> void:
	prompt_label.text = text


func show_pickup(text: String) -> void:
	pickup_label.text = "+ " + text.to_upper()
	_pickup_time = 2.5


func show_subtitle(speaker: String, text: String, duration: float) -> void:
	if _subtitle_time > 0.5:
		_subtitle_queue.append([speaker, text, duration])
	else:
		_show_subtitle_now(speaker, text, duration)


func flash_damage() -> void:
	_damage_flash = 0.75


func show_hit_marker(killed: bool, headshot: bool) -> void:
	_hit_marker_time = 0.35 if killed else 0.2
	hit_marker.self_modulate = KILL_COLOR if killed else (HEADSHOT_COLOR if headshot else HIT_COLOR)
	hit_marker.scale = Vector2.ONE * (1.5 if killed else 1.0)


func show_intro(chapter: String, title: String, text: String) -> void:
	hide_menus()
	gameplay.visible = false
	$IntroScreen/Center/VBox/Chapter.text = chapter
	$IntroScreen/Center/VBox/Title.text = title
	$IntroScreen/Center/VBox/Story.text = text
	intro_screen.visible = true
	$IntroScreen/Center/VBox/ContinueButton.grab_focus()


func show_pause_menu() -> void:
	hide_menus()
	pause_menu.visible = true
	$PauseMenu/Center/VBox/ResumeButton.grab_focus()


func show_death_screen() -> void:
	hide_menus()
	death_screen.visible = true
	$DeathScreen/Center/VBox/RestartButton.grab_focus()


func hide_menus() -> void:
	gameplay.visible = true
	intro_screen.visible = false
	pause_menu.visible = false
	death_screen.visible = false


func fade_out(duration: float) -> void:
	var tween := create_tween()
	tween.tween_property(fade, "color:a", 1.0, duration)
	await tween.finished


func _show_subtitle_now(speaker: String, text: String, duration: float) -> void:
	subtitle_label.text = "[color=%s]%s:[/color] %s" % [SPEAKER_COLOR, speaker, text] if speaker != "" else text
	_subtitle_time = duration
	subtitle_panel.modulate.a = 1.0
	radio_sound.play()


func _highlight_slot(weapon: Weapon) -> void:
	for child in slots.get_children():
		var plate := child as PanelContainer
		var slot_weapon: Weapon = plate.get_meta("weapon")
		var current := slot_weapon == weapon
		plate.add_theme_stylebox_override("panel", _slot_on if current else _slot_off)
		plate.modulate = Color.WHITE if current else Color(1, 1, 1, 0.6)
		plate.visible = slot_weapon.owned


func _slot_style(color: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.content_margin_left = 8.0
	style.content_margin_right = 9.0
	style.content_margin_top = 2.0
	style.content_margin_bottom = 3.0
	return style
