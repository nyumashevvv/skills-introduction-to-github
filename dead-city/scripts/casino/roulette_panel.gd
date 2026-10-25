class_name RoulettePanel
extends CasinoPanel
## European roulette: put chips on numbers (pays 36×), colours, even/odd, halves (2×) or dozens (3×), then spin.

const REDS: Array[int] = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
const STAKES: Array[int] = [5, 10, 25, 50, 100]
const OUTSIDE := {"d1": "1–12", "d2": "13–24", "d3": "25–36", "low": "1–18", "even": "ЧЁТ", "red": "КРАСНОЕ",
		"black": "ЧЁРНОЕ", "odd": "НЕЧЕТ", "high": "19–36"}

var stake := 10
var bets := {}
var wheel: RouletteWheel
var _stake_buttons: Array[Button] = []
var _bet_buttons := {}
var _summary: Label
var _spin_button: Button
var _clear_button: Button
var _spinning := false
var _result := 0


func title() -> String:
	return "РУЛЕТКА"


func build(box: VBoxContainer) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 18)
	box.add_child(row)
	wheel = RouletteWheel.new()
	wheel.finished.connect(_on_wheel_stopped)
	row.add_child(wheel)
	var table := VBoxContainer.new()
	table.add_theme_constant_override("separation", 6)
	row.add_child(table)
	# the numbers in three rows of twelve, the zero on the left
	var grid_row := HBoxContainer.new()
	grid_row.add_theme_constant_override("separation", 4)
	table.add_child(grid_row)
	var zero := _bet_button("n0", "0", 44, Color(0.05, 0.45, 0.2))
	zero.custom_minimum_size = Vector2(44, 3 * 40 + 8)
	grid_row.add_child(zero)
	var grid := GridContainer.new()
	grid.columns = 12
	grid.add_theme_constant_override("h_separation", 4)
	grid.add_theme_constant_override("v_separation", 4)
	grid_row.add_child(grid)
	for line in 3:
		for col in 12:
			var n := col * 3 + 3 - line
			grid.add_child(_bet_button("n%d" % n, str(n), 44, Color(0.6, 0.06, 0.06) if is_red(n) else Color(0.1, 0.1, 0.1)))
	for keys: Array in [["d1", "d2", "d3"], ["low", "even", "red", "black", "odd", "high"]]:
		var outside := HBoxContainer.new()
		outside.add_theme_constant_override("separation", 4)
		table.add_child(outside)
		for key: String in keys:
			var color := Color(0.6, 0.06, 0.06) if key == "red" else (Color(0.1, 0.1, 0.1) if key == "black" else FELT)
			var button := _bet_button(key, OUTSIDE[key], 0, color)
			button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			outside.add_child(button)
	var stakes := HBoxContainer.new()
	stakes.add_theme_constant_override("separation", 6)
	table.add_child(stakes)
	stakes.add_child(make_label("Фишка:", 20))
	for amount in STAKES:
		var button := make_button(str(amount), _set_stake.bind(amount), 64)
		stakes.add_child(button)
		_stake_buttons.append(button)
	_summary = make_label("Ставок нет — нажми на поле", 18, Color(0.8, 0.8, 0.85))
	_summary.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_summary.custom_minimum_size = Vector2(560, 0)
	table.add_child(_summary)
	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", 10)
	table.add_child(actions)
	_spin_button = make_button("КРУТИТЬ", spin, 260, RED)
	actions.add_child(_spin_button)
	_clear_button = make_button("Снять ставки", clear_bets, 200)
	actions.add_child(_clear_button)
	_set_stake(stake)


func _bet_button(key: String, text: String, width: int, color: Color) -> Button:
	var button := make_button(text, place_bet.bind(key), width, color)
	button.add_theme_font_size_override("font_size", 17)
	_bet_buttons[key] = button
	return button


func _set_stake(amount: int) -> void:
	stake = amount
	for i in STAKES.size():
		_stake_buttons[i].modulate = Color(1.3, 1.1, 0.6) if STAKES[i] == stake else Color.WHITE


func place_bet(key: String) -> void:
	if _spinning:
		return
	if Game.chips < stake:
		say("Не хватает фишек — загляни в кассу", Color(1, 0.5, 0.4))
		return
	Game.chips -= stake
	bets[key] = int(bets.get(key, 0)) + stake
	(_bet_buttons[key] as Button).modulate = Color(1.4, 1.25, 0.6)
	play("casino_chips")
	refresh_chips()
	_update_summary()


func clear_bets() -> void:
	if _spinning:
		return
	for key: String in bets:
		Game.chips += int(bets[key])
		(_bet_buttons[key] as Button).modulate = Color.WHITE
	bets.clear()
	refresh_chips()
	_update_summary()


func spin() -> void:
	if _spinning:
		return
	if bets.is_empty():
		say("Сначала поставь фишки на поле", Color(1, 0.5, 0.4))
		return
	_spinning = true
	_spin_button.disabled = true
	_clear_button.disabled = true
	_result = randi() % 37
	wheel.spin_to(_result)
	play("casino_ball")
	say("Ставки сделаны, ставок больше нет…")


func _on_wheel_stopped() -> void:
	var win := 0
	for key: String in bets:
		win += int(bets[key]) * multiplier(key, _result)
		(_bet_buttons[key] as Button).modulate = Color.WHITE
	bets.clear()
	Game.chips += win
	refresh_chips()
	_update_summary()
	var color_name := "зеро" if _result == 0 else ("красное" if is_red(_result) else "чёрное")
	if win > 0:
		say("Выпало %d, %s. Выигрыш +%d фишек!" % [_result, color_name, win], GOLD)
		play("casino_win")
	else:
		say("Выпало %d, %s. Не повезло." % [_result, color_name])
		play("casino_lose")
	_spinning = false
	_spin_button.disabled = false
	_clear_button.disabled = false


func _update_summary() -> void:
	if bets.is_empty():
		_summary.text = "Ставок нет — нажми на поле"
		return
	var parts: Array[String] = []
	var total := 0
	for key: String in bets:
		parts.append("%s: %d" % [("№" + key.substr(1)) if key.begins_with("n") else OUTSIDE[key], bets[key]])
		total += int(bets[key])
	_summary.text = "Ставки — %s (всего %d)" % [", ".join(parts), total]


static func is_red(number: int) -> bool:
	return number in REDS


## What a bet returns per chip when `number` comes up (the chip included); 0 if it loses.
static func multiplier(key: String, number: int) -> int:
	if key.begins_with("n"):
		return 36 if int(key.substr(1)) == number else 0
	if number == 0:
		return 0
	match key:
		"red": return 2 if is_red(number) else 0
		"black": return 0 if is_red(number) else 2
		"even": return 2 if number % 2 == 0 else 0
		"odd": return 2 if number % 2 == 1 else 0
		"low": return 2 if number <= 18 else 0
		"high": return 2 if number >= 19 else 0
		"d1": return 3 if number <= 12 else 0
		"d2": return 3 if number >= 13 and number <= 24 else 0
		"d3": return 3 if number >= 25 else 0
	return 0
