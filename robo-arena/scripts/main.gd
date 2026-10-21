extends Node3D

enum State { MENU, PLAYING, PAUSED, GAME_OVER }

const SAVE_PATH := "user://best_score.cfg"
const WAVE_CLEAR_BONUS := 250

## Survives scene reloads so "Restart" skips the start screen.
static var skip_menu := false

var state := State.MENU
var score := 0
var kills := 0
var best_score := 0

@onready var player: Player = $Player
@onready var waves: WaveManager = $WaveManager
@onready var hud: Hud = $HUD
@onready var nav_region: NavigationRegion3D = $NavigationRegion3D
@onready var wave_sound: AudioStreamPlayer = $WaveSound


func _ready() -> void:
	_load_best_score()
	nav_region.bake_navigation_mesh(true)

	player.health_changed.connect(hud.set_health)
	player.damaged.connect(hud.flash_damage)
	player.died.connect(_on_player_died)
	player.weapon.ammo_changed.connect(hud.set_ammo)
	player.weapon.reload_started.connect(hud.set_reloading.bind(true))
	player.weapon.reload_finished.connect(hud.set_reloading.bind(false))
	player.weapon.enemy_hit.connect(hud.show_hit_marker)
	waves.wave_started.connect(_on_wave_started)
	waves.wave_cleared.connect(_on_wave_cleared)
	waves.enemies_left_changed.connect(hud.set_enemies_left)
	waves.enemy_killed.connect(_on_enemy_killed)
	hud.start_pressed.connect(start_game)
	hud.resume_pressed.connect(resume)
	hud.restart_pressed.connect(restart)
	hud.quit_pressed.connect(get_tree().quit)
	hud.pause_toggle_requested.connect(toggle_pause)

	hud.bind_weapon(player.weapon)
	hud.set_health(player.health, player.max_health)
	hud.set_ammo(player.weapon.ammo, player.weapon.reserve)
	hud.set_score(score)
	hud.set_wave(0)

	if skip_menu:
		start_game()
	else:
		get_tree().paused = true
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		hud.show_start_screen(best_score)


func _unhandled_input(event: InputEvent) -> void:
	# Clicking back into the window after alt-tab recaptures the mouse.
	if state == State.PLAYING and event is InputEventMouseButton and event.is_pressed() \
			and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and state == State.PLAYING:
		toggle_pause()


func start_game() -> void:
	state = State.PLAYING
	hud.hide_menus()
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	waves.start()
	hud.show_message("Приготовься!", 1.8)


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


func restart() -> void:
	skip_menu = true
	get_tree().paused = false
	get_tree().reload_current_scene()


func _on_wave_started(number: int) -> void:
	hud.set_wave(number)
	hud.show_message("Волна %d" % number, 2.0)
	wave_sound.play()


func _on_wave_cleared(number: int) -> void:
	var bonus := WAVE_CLEAR_BONUS * number
	_add_score(bonus)
	hud.show_message("Волна пройдена!  +%d" % bonus, 3.0)


func _on_enemy_killed(enemy: Enemy) -> void:
	kills += 1
	_add_score(enemy.score_value)


func _add_score(amount: int) -> void:
	score += amount
	hud.set_score(score)


func _on_player_died() -> void:
	state = State.GAME_OVER
	waves.stop()
	var new_record := score > best_score
	if new_record:
		best_score = score
		_save_best_score()
	await get_tree().create_timer(1.5).timeout
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	hud.show_game_over(waves.wave, kills, score, best_score, new_record)


func _load_best_score() -> void:
	var config := ConfigFile.new()
	if config.load(SAVE_PATH) == OK:
		best_score = config.get_value("scores", "best", 0)


func _save_best_score() -> void:
	var config := ConfigFile.new()
	config.set_value("scores", "best", best_score)
	config.save(SAVE_PATH)
