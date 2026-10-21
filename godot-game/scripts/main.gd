extends Node2D

var score := 0
var total := 0

@onready var score_label: Label = $UI/ScoreLabel


func _ready() -> void:
	var coins := get_tree().get_nodes_in_group("coins")
	total = coins.size()
	for coin: Coin in coins:
		coin.collected.connect(_on_coin_collected)
	_update_label()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_R:
		get_tree().reload_current_scene()


func _on_coin_collected() -> void:
	score += 1
	_update_label()


func _update_label() -> void:
	if score >= total:
		score_label.text = "Все монеты собраны! Нажми R, чтобы начать заново"
	else:
		score_label.text = "Монеты: %d / %d" % [score, total]
