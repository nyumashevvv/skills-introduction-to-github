class_name CashierPanel
extends CasinoPanel
## The casino's cash desk: a welcome gift of chips, and prizes the player can take for winnings.

const GIFT := 100
## [name, price, what it gives]
const PRIZES: Array[Array] = [
	["Аптечка: +50 здоровья", 60, "heal"],
	["Магазин патронов к оружию в руках", 40, "ammo"],
	["Граната", 80, "grenade"],
	["РПГ-7 (или ракета к нему)", 350, "bazooka"],
]

var _gift_button: Button


func title() -> String:
	return "КАССА"


func build(box: VBoxContainer) -> void:
	box.add_child(make_label("Выиграл фишки — меняй на полезное", 18, Color(0.8, 0.8, 0.85)))
	_gift_button = make_button("Подарок новичку: %d фишек" % GIFT, take_gift, 460, FELT)
	_gift_button.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_gift_button.disabled = Game.casino_bonus_taken
	if Game.casino_bonus_taken:
		_gift_button.text = "Подарок уже получен"
	box.add_child(_gift_button)
	for prize in PRIZES:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		box.add_child(row)
		var name_label := make_label(prize[0], 20)
		name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
		name_label.custom_minimum_size = Vector2(380, 0)
		row.add_child(name_label)
		row.add_child(make_button("%d фишек" % prize[1], buy.bind(prize), 150, RED))


func take_gift() -> void:
	if Game.casino_bonus_taken:
		return
	Game.casino_bonus_taken = true
	Game.chips += GIFT
	_gift_button.disabled = true
	_gift_button.text = "Подарок уже получен"
	refresh_chips()
	say("Держи %d фишек. Удачи за столами!" % GIFT, GOLD)
	play("casino_chips")


func buy(prize: Array) -> void:
	var price: int = prize[1]
	if Game.chips < price:
		say("Не хватает фишек", Color(1, 0.5, 0.4))
		play("casino_lose")
		return
	if not grant(player, prize[2]):
		say("Это тебе сейчас не нужно", Color(1, 0.8, 0.5))
		return
	Game.chips -= price
	refresh_chips()
	say("Получено: %s" % prize[0], GOLD)
	play("casino_win")


## Gives a prize; false when it would be wasted (full health, a weapon without ammo...).
static func grant(who: Player, what: String) -> bool:
	match what:
		"heal":
			return who.heal(50)
		"ammo":
			var weapon := who.holder.current
			return weapon != null and weapon.uses_ammo() and weapon.add_ammo(weapon.magazine_size)
		_:
			return who.holder.give_weapon(what, false)
