class_name SlotPanel
extends CasinoPanel
## The one-armed bandit: three reels, five symbols. Three of a kind pays by the table, any two of a kind returns the
## stake (about 94 % back over time, like a real machine).

const SYMBOLS: Array[String] = ["7", "$", "BAR", "МОЗГ", "ГОША"]
const COLORS: Array[Color] = [Color(1, 0.2, 0.15), Color(0.3, 1, 0.4), Color(1, 0.8, 0.25), Color(1, 0.45, 0.7),
		Color(0.9, 0.9, 1)]
const WEIGHTS: Array[int] = [1, 2, 3, 4, 5]
## Three of a kind pays the stake times this.
const PAYS: Array[int] = [50, 20, 10, 6, 4]
const BETS: Array[int] = [5, 10, 25, 50]
const STOP_TIMES: Array[float] = [0.9, 1.35, 1.8]

var bet := 10
var reels: Array[Label] = []
var _bet_buttons: Array[Button] = []
var _spin_button: Button
var _spinning := false
var _result: Array[int] = []
var _stopped: Array[bool] = [false, false, false]
var _time := 0.0
var _tick := 0.0


func title() -> String:
	return "ОДНОРУКИЙ БАНДИТ"


func build(box: VBoxContainer) -> void:
	box.add_child(make_label("Три одинаковых:  7 ×50 · $ ×20 · BAR ×10 · МОЗГ ×6 · ГОША ×4\nДва одинаковых — ставка возвращается",
			18, Color(0.8, 0.8, 0.85)))
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 14)
	box.add_child(row)
	for i in 3:
		var window := PanelContainer.new()
		window.custom_minimum_size = Vector2(180, 130)
		window.add_theme_stylebox_override("panel", box_style(Color(0.96, 0.94, 0.88), GOLD, 4, 8, 6))
		row.add_child(window)
		var label := make_label("7", 54, COLORS[0], RUSSO)
		label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		label.add_theme_color_override("font_outline_color", Color(0.1, 0.05, 0.05))
		label.add_theme_constant_override("outline_size", 6)
		window.add_child(label)
		reels.append(label)
	var bets := HBoxContainer.new()
	bets.alignment = BoxContainer.ALIGNMENT_CENTER
	bets.add_theme_constant_override("separation", 8)
	box.add_child(bets)
	bets.add_child(make_label("Ставка:", 20))
	for amount in BETS:
		var button := make_button(str(amount), _set_bet.bind(amount), 70)
		bets.add_child(button)
		_bet_buttons.append(button)
	_spin_button = make_button("КРУТИТЬ", spin, 320, RED)
	_spin_button.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	box.add_child(_spin_button)
	for i in 3:
		_show(i, randi() % SYMBOLS.size())
	_set_bet(bet)
	_spin_button.grab_focus.call_deferred()


func _set_bet(amount: int) -> void:
	bet = amount
	for i in BETS.size():
		_bet_buttons[i].modulate = Color(1.3, 1.1, 0.6) if BETS[i] == bet else Color.WHITE


func spin() -> void:
	if _spinning:
		return
	if Game.chips < bet:
		say("Не хватает фишек — загляни в кассу", Color(1, 0.5, 0.4))
		play("casino_lose")
		return
	Game.chips -= bet
	refresh_chips()
	_result = [roll(), roll(), roll()]
	_stopped = [false, false, false]
	_spinning = true
	_time = 0.0
	_spin_button.disabled = true
	say(" ")


func _process(delta: float) -> void:
	if not _spinning:
		return
	_time += delta
	_tick -= delta
	var shuffle := _tick <= 0.0
	if shuffle:
		_tick = 0.07
		play("casino_tick")
	for i in 3:
		if _stopped[i]:
			continue
		if _time >= STOP_TIMES[i]:
			_stopped[i] = true
			_show(i, _result[i])
			play("casino_reel_stop")
		elif shuffle:
			_show(i, randi() % SYMBOLS.size())
	if _stopped[2] and _time >= STOP_TIMES[2] + 0.25:
		_spinning = false
		_spin_button.disabled = false
		_spin_button.grab_focus()
		var win := payout(_result, bet)
		Game.chips += win
		refresh_chips()
		if win == 0:
			say("Мимо. Ещё разок?")
			play("casino_lose")
		elif win == bet:
			say("Пара — ставка вернулась", Color(0.9, 0.9, 0.6))
			play("casino_chips")
		else:
			say(("ДЖЕКПОТ! " if _result[0] == 0 else "Выигрыш! ") + "+%d фишек" % win, GOLD)
			play("casino_win")


func _show(reel: int, symbol: int) -> void:
	reels[reel].text = SYMBOLS[symbol]
	reels[reel].add_theme_font_size_override("font_size", 56 if SYMBOLS[symbol].length() <= 3 else 40)
	reels[reel].add_theme_color_override("font_color", COLORS[symbol])


## A weighted random symbol: sevens are rare, Gosha is common.
static func roll() -> int:
	var total := 0
	for w in WEIGHTS:
		total += w
	var pick := randi() % total
	for i in WEIGHTS.size():
		pick -= WEIGHTS[i]
		if pick < 0:
			return i
	return WEIGHTS.size() - 1


## Chips paid back for a spin (the stake included).
static func payout(result: Array[int], stake: int) -> int:
	if result[0] == result[1] and result[1] == result[2]:
		return stake * PAYS[result[0]]
	if result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
		return stake
	return 0
