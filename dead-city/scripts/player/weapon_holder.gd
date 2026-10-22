class_name WeaponHolder
extends Node3D
## Owns the player's weapons (its children), switching between them and their ammo.

signal fired(recoil: float)
signal weapon_changed(weapon: Weapon)
signal ammo_changed(weapon: Weapon)
signal reload_changed(weapon: Weapon, reloading: bool)
signal enemy_hit(killed: bool, headshot: bool)
signal inventory_changed

var current: Weapon
var enabled := true
var movement_factor := 0.0:
	set(value):
		movement_factor = value
		for weapon in weapons:
			weapon.movement_factor = value

var weapons: Array[Weapon] = []
var _sway := Vector2.ZERO

@onready var switch_sound: AudioStreamPlayer = $SwitchSound
@onready var hit_sound: AudioStreamPlayer = $HitSound


func _ready() -> void:
	for child in get_children():
		if child is Weapon:
			var weapon := child as Weapon
			weapons.append(weapon)
			weapon.unequip()
			weapon.fired.connect(fired.emit)
			weapon.ammo_changed.connect(ammo_changed.emit)
			weapon.reload_changed.connect(reload_changed.emit)
			weapon.enemy_hit.connect(_on_enemy_hit)
	weapons.sort_custom(func(a: Weapon, b: Weapon) -> bool: return a.slot < b.slot)


func _unhandled_input(event: InputEvent) -> void:
	if not enabled or Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return
	for slot in range(1, 10):
		if event.is_action_pressed("weapon_%d" % slot):
			for weapon in weapons:
				if weapon.slot == slot:
					switch_to(weapon)
	if event.is_action_pressed("weapon_next"):
		_cycle(1)
	elif event.is_action_pressed("weapon_prev"):
		_cycle(-1)


func _process(delta: float) -> void:
	# Weapons lag a little behind mouse movement.
	_sway = _sway.lerp(Vector2.ZERO, clampf(delta * 6.0, 0.0, 1.0))
	rotation = Vector3(_sway.y, _sway.x, 0.0)


func add_sway(mouse_relative: Vector2) -> void:
	_sway = (_sway + mouse_relative * 0.0006).limit_length(0.08)


func get_weapon(id: String) -> Weapon:
	for weapon in weapons:
		if weapon.id == id:
			return weapon
	return null


func setup_default(ids: PackedStringArray, ammo: Dictionary) -> void:
	for id in ids:
		give_weapon(id, false)
	for ammo_type: String in ammo:
		add_ammo(ammo_type, int(ammo[ammo_type]))
	if not ids.is_empty():
		switch_to(get_weapon(ids[ids.size() - 1]), false)


## Gives the weapon, or a magazine of ammo for it if it is already owned.
func give_weapon(id: String, auto_equip := true) -> bool:
	var weapon := get_weapon(id)
	if weapon == null:
		return false
	if weapon.owned:
		return weapon.uses_ammo() and weapon.add_ammo(weapon.magazine_size)
	weapon.owned = true
	# A found weapon comes loaded, with one spare magazine.
	weapon.ammo = weapon.magazine_size
	weapon.add_ammo(weapon.magazine_size)
	inventory_changed.emit()
	if auto_equip:
		switch_to(weapon)
	return true


## Ammo is stored even for weapons the player has not found yet.
func add_ammo(ammo_type: String, amount: int) -> bool:
	for weapon in weapons:
		if weapon.ammo_type == ammo_type:
			return weapon.add_ammo(amount)
	return false


func switch_to(weapon: Weapon, play_sound := true) -> void:
	if weapon == null or weapon == current or not weapon.owned:
		return
	if current != null:
		current.unequip()
	current = weapon
	current.equip()
	current.active = enabled
	if play_sound:
		switch_sound.play()
	weapon_changed.emit(current)


func set_enabled(value: bool) -> void:
	enabled = value
	if current != null:
		current.active = value


func get_state() -> Dictionary:
	var owned: Array[String] = []
	var ammo := {}
	for weapon in weapons:
		if weapon.owned:
			owned.append(weapon.id)
		ammo[weapon.id] = [weapon.ammo, weapon.reserve]
	return {"owned": owned, "ammo": ammo, "current": current.id if current != null else ""}


func apply_state(state: Dictionary) -> void:
	var owned: Array = state.get("owned", [])
	var ammo: Dictionary = state.get("ammo", {})
	for weapon in weapons:
		weapon.owned = owned.has(weapon.id)
		if ammo.has(weapon.id):
			weapon.ammo = ammo[weapon.id][0]
			weapon.reserve = ammo[weapon.id][1]
	inventory_changed.emit()
	switch_to(get_weapon(state.get("current", "")), false)


func _cycle(step: int) -> void:
	var owned := weapons.filter(func(w: Weapon) -> bool: return w.owned)
	if owned.size() < 2:
		return
	var index := owned.find(current)
	switch_to(owned[(index + step + owned.size()) % owned.size()])


func _on_enemy_hit(killed: bool, headshot: bool) -> void:
	hit_sound.pitch_scale = 0.8 if killed else randf_range(1.0, 1.2)
	hit_sound.play()
	enemy_hit.emit(killed, headshot)
