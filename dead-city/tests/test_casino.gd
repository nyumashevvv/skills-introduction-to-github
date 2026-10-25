extends Node
## The mall's casino: payout rules, the long-run return of each game, and playing every machine in the real chapter.
##   godot --headless --path . res://tests/test_casino.tscn

var failures := 0


func check(cond: bool, what: String) -> void:
	print(("PASS  " if cond else "FAIL  ") + what)
	if not cond:
		failures += 1


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
	_rules()
	await _in_the_mall()
	print("FAILURES: %d" % failures)
	get_tree().quit(failures)


func _rules() -> void:
	var a: Array[int] = [0, 0, 0]
	var b: Array[int] = [4, 4, 2]
	var c: Array[int] = [1, 2, 3]
	check(SlotPanel.payout(a, 10) == 500, "slots: three sevens pay 50×")
	check(SlotPanel.payout(b, 10) == 10, "slots: a pair returns the stake")
	check(SlotPanel.payout(c, 10) == 0, "slots: nothing matching loses")
	var back := 0
	for i in 200000:
		var spin: Array[int] = [SlotPanel.roll(), SlotPanel.roll(), SlotPanel.roll()]
		back += SlotPanel.payout(spin, 1)
	var rtp := back / 200000.0
	check(rtp > 0.85 and rtp < 1.0, "slots return %.3f of the stakes over time (the house wins a little)" % rtp)
	check(RoulettePanel.multiplier("n17", 17) == 36 and RoulettePanel.multiplier("n17", 18) == 0, "roulette: a number pays 36×")
	check(RoulettePanel.multiplier("red", 1) == 2 and RoulettePanel.multiplier("red", 2) == 0, "roulette: 1 is red, 2 is black")
	check(RoulettePanel.multiplier("black", 0) == 0 and RoulettePanel.multiplier("even", 0) == 0, "roulette: zero beats the outside bets")
	check(RoulettePanel.multiplier("d2", 13) == 3 and RoulettePanel.multiplier("d2", 25) == 0, "roulette: dozens pay 3×")
	check(RoulettePanel.REDS.size() == 18 and RouletteWheel.ORDER.size() == 37, "roulette: 18 reds, 37 pockets")


func _in_the_mall() -> void:
	var level := (load("res://scenes/levels/level_3_mall.tscn") as PackedScene).instantiate() as Level
	get_tree().root.add_child(level)
	get_tree().current_scene = level
	await get_tree().physics_frame
	level.start_playing()
	var machines := {}
	for node in level.find_children("*", "CasinoMachine", true, false):
		var machine := node as CasinoMachine
		machines[machine.kind] = machines.get(machine.kind, []) + [machine]
	check(machines.get(CasinoMachine.Kind.SLOTS, []).size() >= 10, "the casino has slot machines (%d)" % machines.get(0, []).size())
	check(machines.get(CasinoMachine.Kind.ROULETTE, []).size() == 2, "two roulette tables")
	check(machines.get(CasinoMachine.Kind.CASHIER, []).size() == 1, "one cash desk")
	Game.chips = 0
	Game.casino_bonus_taken = false

	# the cash desk: the gift, then a prize
	var desk := (machines[CasinoMachine.Kind.CASHIER] as Array)[0] as CasinoMachine
	check(desk.get_prompt(level.player).contains("Касса"), "the desk offers itself: " + desk.get_prompt(level.player))
	desk.interact(level.player)
	await get_tree().process_frame
	var cashier := _panel(level) as CashierPanel
	check(cashier != null and level.state == Level.State.PANEL and get_tree().paused, "E at the desk opens the cash desk, the game pauses")
	cashier.take_gift()
	cashier.take_gift()
	check(Game.chips == CashierPanel.GIFT, "the gift is given once (%d chips)" % Game.chips)
	level.player.take_damage(60)
	var hurt := level.player.health
	cashier.buy(CashierPanel.PRIZES[0])
	check(level.player.health > hurt and Game.chips == CashierPanel.GIFT - 60, "a medkit for 60 chips heals")
	level.toggle_pause()
	await get_tree().process_frame
	check(_panel(level) == null and level.state == Level.State.PLAYING and not get_tree().paused, "Esc closes the screen and the game goes on")

	# the slots
	Game.chips = 100
	(machines[CasinoMachine.Kind.SLOTS] as Array)[0].interact(level.player)
	await get_tree().process_frame
	var slots := _panel(level) as SlotPanel
	check(slots != null, "E at a slot machine opens the reels")
	slots.bet = 10
	slots.spin()
	check(Game.chips == 90, "a spin takes the stake")
	await get_tree().create_timer(2.6).timeout
	check(not slots._spinning, "the reels stop")
	check(Game.chips == 90 + SlotPanel.payout(slots._result, 10), "the win is paid (%d chips)" % Game.chips)
	slots.close_panel()
	await get_tree().process_frame

	# the roulette
	Game.chips = 100
	(machines[CasinoMachine.Kind.ROULETTE] as Array)[0].interact(level.player)
	await get_tree().process_frame
	var roulette := _panel(level) as RoulettePanel
	check(roulette != null, "E at a roulette table opens the wheel")
	roulette.stake = 10
	roulette.place_bet("red")
	roulette.place_bet("n7")
	check(Game.chips == 80 and roulette.bets.size() == 2, "bets take their chips")
	roulette.spin()
	await get_tree().create_timer(RouletteWheel.SPIN_TIME + 0.5).timeout
	var expected := 80 + 10 * RoulettePanel.multiplier("red", roulette._result) + 10 * RoulettePanel.multiplier("n7", roulette._result)
	check(Game.chips == expected, "the wheel stopped on %d and paid %d" % [roulette._result, Game.chips - 80])
	check(RouletteWheel.ORDER[posmod(roundi((roulette.wheel.ball_angle - roulette.wheel.rotation_angle) / (TAU / 37)), 37)]
			== roulette._result, "the ball sits in the winning pocket")
	roulette.close_panel()
	await get_tree().process_frame
	check(level.state == Level.State.PLAYING, "back to the game")


func _panel(level: Level) -> CasinoPanel:
	for child in level.hud.get_children():
		if child is CasinoPanel and not child.is_queued_for_deletion():
			return child
	return null
