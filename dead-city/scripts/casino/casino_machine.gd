class_name CasinoMachine
extends StaticBody3D
## A slot machine, a roulette table or the cash desk in the mall's casino: E opens its screen over the paused game.

enum Kind { SLOTS, ROULETTE, CASHIER }

const PROMPTS: Array[String] = ["Сыграть в автомат", "Сыграть в рулетку", "Касса казино"]

@export var kind := Kind.SLOTS


func get_prompt(_player: Player) -> String:
	return "[E] %s  (фишки: %d)" % [PROMPTS[kind], Game.chips]


func interact(player: Player) -> void:
	var level := get_tree().current_scene as Level
	if level == null:
		return
	var panel: CasinoPanel
	match kind:
		Kind.SLOTS:
			panel = SlotPanel.new()
		Kind.ROULETTE:
			panel = RoulettePanel.new()
		_:
			panel = CashierPanel.new()
	panel.player = player
	level.open_panel(panel)
