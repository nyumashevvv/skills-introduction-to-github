class_name Level
extends Node3D
## Root of every chapter: starts it, connects the player to the HUD and
## handles pause, death and completion.

enum State { INTRO, PLAYING, PAUSED, DEAD, COMPLETE }

const MUSIC_DB := -7.0
const SILENT_DB := -40.0

@export var chapter_number := 1
@export var chapter_title := ""
@export_multiline var intro_text := ""
@export_multiline var start_objective := ""
## StoryEvent fired when the player closes the intro card.
@export var start_event: NodePath
## Loadout when starting this chapter without a checkpoint (new game / testing the scene).
@export var default_weapons: PackedStringArray = ["knife", "pistol"]
@export var default_ammo := {"pistol": 24}

var state := State.INTRO

var _music: AudioStreamPlayer
var _music_tween: Tween

@onready var player: Player = $Player
@onready var hud: Hud = $HUD
@onready var nav_region: NavigationRegion3D = $NavigationRegion3D


func _ready() -> void:
	Game.level_started()
	nav_region.bake_navigation_mesh(true)

	player.health_changed.connect(hud.set_health)
	player.damaged.connect(hud.flash_damage)
	player.died.connect(_on_player_died)
	player.interact_prompt_changed.connect(hud.set_prompt)
	player.holder.weapon_changed.connect(hud.set_weapon)
	player.holder.ammo_changed.connect(hud.update_ammo)
	player.holder.reload_changed.connect(hud.set_reloading)
	player.holder.inventory_changed.connect(_refresh_inventory)
	player.holder.enemy_hit.connect(hud.show_hit_marker)
	hud.continue_pressed.connect(start_playing)
	hud.resume_pressed.connect(resume)
	hud.restart_pressed.connect(Game.restart_level)
	hud.menu_pressed.connect(Game.go_to_menu)
	hud.pause_toggle_requested.connect(toggle_pause)

	if Game.checkpoint.is_empty():
		player.holder.setup_default(default_weapons, default_ammo)
	else:
		player.apply_state(Game.checkpoint)
	hud.bind_holder(player.holder)
	hud.set_health(player.health, player.max_health)
	_refresh_inventory()

	get_tree().paused = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	hud.show_intro("Глава %d" % chapter_number, chapter_title, intro_text)


func _unhandled_input(event: InputEvent) -> void:
	# Clicking back into the window after alt-tab recaptures the mouse.
	if state == State.PLAYING and event is InputEventMouseButton and event.is_pressed() \
			and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and state == State.PLAYING:
		toggle_pause()


func start_playing() -> void:
	state = State.PLAYING
	hud.hide_menus()
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	if start_objective != "":
		set_objective(start_objective)
	if not start_event.is_empty():
		get_node(start_event).call("fire")


func set_objective(text: String) -> void:
	hud.set_objective(text)


func radio(speaker: String, text: String, duration := 6.0) -> void:
	hud.show_subtitle(speaker, text, duration)


## Fades in a looping track (boss fights). Playing the same track again does nothing.
func play_music(stream: AudioStream, fade := 1.5) -> void:
	if _music == null:
		_music = AudioStreamPlayer.new()
		_music.name = "Music"
		_music.bus = &"Music"
		add_child(_music)
	if _music.stream == stream and _music.playing:
		return
	if stream is AudioStreamOggVorbis:
		(stream as AudioStreamOggVorbis).loop = true
	_music.stream = stream
	_music.volume_db = SILENT_DB
	_music.play()
	_fade_music(MUSIC_DB, fade)


func stop_music(fade := 3.0) -> void:
	if _music == null or not _music.playing:
		return
	_fade_music(SILENT_DB, fade)
	_music_tween.tween_callback(_music.stop)


func is_music_playing() -> bool:
	return _music != null and _music.playing


func _fade_music(volume_db: float, duration: float) -> void:
	if _music_tween != null:
		_music_tween.kill()
	_music_tween = create_tween()
	_music_tween.tween_property(_music, "volume_db", volume_db, duration)


func show_pickup(text: String) -> void:
	hud.show_pickup(text)


func complete() -> void:
	if state == State.COMPLETE:
		return
	state = State.COMPLETE
	player.holder.set_enabled(false)
	await hud.fade_out(1.5)
	Game.complete_level(player.get_state())


func toggle_pause() -> void:
	match state:
		State.PLAYING:
			state = State.PAUSED
			get_tree().paused = true
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
			hud.show_pause_menu()
		State.PAUSED:
			resume()


func resume() -> void:
	state = State.PLAYING
	hud.hide_menus()
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _refresh_inventory() -> void:
	hud.set_inventory(player.holder.weapons)


func _on_player_died() -> void:
	state = State.DEAD
	await get_tree().create_timer(1.5).timeout
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	hud.show_death_screen()
