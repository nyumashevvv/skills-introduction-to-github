class_name Scooter
extends Node3D
## Arcade scooter driving directly on the heightfield.

signal message(text: String)

var world: World
var heading := 0.0          # radians, 0 = facing north (-Z)
var speed := 0.0            # m/s along heading
var steer := 0.0
var lean := 0.0
var pitch := 0.0
var odometer := 0.0
# fuel and money
const TANK := 4.2               # litres
const USE_PER_KM := 0.03        # litres per km (turbo burns three times as much)
var fuel := 3.0
var money := 1000.0             # THB
var refuelling := false
var _low_warned := false
var turbo := false
var surface := World.ROAD
var model: Node3D
var wheel_front: Node3D
var wheel_rear: Node3D
var headlight: SpotLight3D
const WHEEL_R := 0.28
var _safe_pos := Vector3.ZERO
var _safe_heading := 0.0
var _safe_timer := 0.0
var _msg_cooldown := 0.0
var _hit_cooldown := 0.0

const MAX_ROAD := 22.0      # ~80 km/h
const MAX_OFFROAD := 11.0
const MAX_SAND := 7.0
const TURBO_MULT := 4.0
const ACCEL := 5.5
const BRAKE := 14.0


func _ready() -> void:
	# scooter + rider modelled in Blender (tools/blender/make_scooter_rider.py)
	model = load("res://models/scooter_rider.glb").instantiate()
	add_child(model)
	wheel_front = model.find_child("WheelFront", true, false)
	wheel_rear = model.find_child("WheelRear", true, false)
	headlight = SpotLight3D.new()
	headlight.position = Vector3(0, 1.0, -0.75)
	headlight.rotation_degrees = Vector3(-8, 0, 0)
	headlight.spot_range = 45.0
	headlight.spot_angle = 28.0
	headlight.light_energy = 0.0
	headlight.light_color = Color(1.0, 0.95, 0.85)
	headlight.shadow_enabled = true
	model.add_child(headlight)


func place(p: Vector2, dir: Vector2) -> void:
	heading = atan2(-dir.x, -dir.y)
	speed = 0.0
	position = Vector3(p.x, world.ground_at(p.x, p.y), p.y)
	_safe_pos = position
	_safe_heading = heading
	_update_transform(0.0)


func forward() -> Vector3:
	return Vector3(-sin(heading), 0, -cos(heading))


func _physics_process(dt: float) -> void:
	_msg_cooldown -= dt
	_hit_cooldown -= dt
	world.traffic.update(dt, self)
	var thr := Input.get_action_strength("gas")
	var brk := Input.get_action_strength("brake")
	var st := Input.get_action_strength("left") - Input.get_action_strength("right")
	turbo = Input.is_action_pressed("turbo")
	if Input.is_action_just_pressed("reset"):
		reset_to_safe()
		return

	surface = world.class_at(position.x, position.z)
	_update_fuel(dt)
	var vmax := MAX_ROAD
	if surface == World.SAND:
		vmax = MAX_SAND
	elif surface in [World.GRASS, World.JUNGLE, World.URBAN, World.ROCK]:
		vmax = MAX_OFFROAD
	if turbo:
		vmax *= TURBO_MULT
	if fuel <= 0.0:
		vmax = 1.5   # out of fuel: pushing the scooter
		thr = minf(thr, 0.3)
	var accel := ACCEL * (TURBO_MULT * 0.8 if turbo else 1.0)

	if thr > 0.0:
		if speed < -0.1:
			speed = move_toward(speed, 0.0, BRAKE * dt)
		elif speed < vmax:
			speed = minf(speed + accel * thr * dt * (1.0 - 0.6 * speed / vmax), vmax)
	if brk > 0.0:
		if speed > 0.1:
			speed = move_toward(speed, 0.0, BRAKE * brk * dt)
		else:
			speed = maxf(speed - 3.0 * dt, -4.0)
	if thr == 0.0 and brk == 0.0:
		speed = move_toward(speed, 0.0, (0.8 + 0.02 * speed * speed) * dt)
	if speed > vmax:
		speed = move_toward(speed, vmax, 8.0 * dt)
	# gravity along the slope
	speed -= 9.8 * sin(pitch) * dt * 0.7

	steer = move_toward(steer, st, dt * 3.5)
	var turn_rate := steer * clampf(absf(speed) / 3.0, 0.0, 1.0) * 1.9 / (1.0 + absf(speed) * 0.07)
	heading += turn_rate * dt * signf(speed)

	var step := forward() * speed * dt
	var np := position + step
	var nh := world.ground_at(np.x, np.z)
	if absf(np.x) > World.HALF - 50 or absf(np.z) > World.HALF - 50:
		speed = 0.0
		np = position
	elif nh < -0.6:
		speed = 0.0
		np = position
		_say("Дальше море — скутер не плавает. R — назад на дорогу")
	elif world.is_blocked(np.x, np.z):
		speed = -speed * 0.25
		np = position
		_say("Бум! Здание")
	var moved := (np - position).length()
	odometer += moved
	fuel = maxf(0.0, fuel - moved / 1000.0 * USE_PER_KM * (3.0 if turbo else 1.0))
	position = Vector3(np.x, world.ground_at(np.x, np.z), np.z)

	_safe_timer += dt
	if _safe_timer > 1.0:
		_safe_timer = 0.0
		if surface == World.ROAD and absf(speed) > 2.0:
			_safe_pos = position
			_safe_heading = heading
	_update_transform(dt)


func _update_transform(dt: float) -> void:
	var f := forward()
	var hf := world.ground_at(position.x + f.x * 0.65, position.z + f.z * 0.65)
	var hb := world.ground_at(position.x - f.x * 0.65, position.z - f.z * 0.65)
	pitch = atan2(hf - hb, 1.3)
	var target_lean := -steer * clampf(absf(speed) / 12.0, 0.0, 1.0) * 0.45
	lean = lerpf(lean, target_lean, clampf(dt * 6.0, 0.0, 1.0))
	position.y = (hf + hb) * 0.5
	if wheel_front and dt > 0.0:
		var spin := -speed / WHEEL_R * dt
		wheel_front.rotate_object_local(Vector3.RIGHT, spin)
		wheel_rear.rotate_object_local(Vector3.RIGHT, spin)
	basis = Basis(Vector3.UP, heading) * Basis(Vector3.RIGHT, pitch) * Basis(Vector3.FORWARD, -lean)


func reset_to_safe() -> void:
	var r := world.nearest_road(position.x, position.z)
	if r.has("pos") and Vector2(r["pos"]).distance_to(Vector2(position.x, position.z)) < 400:
		place(r["pos"], r["dir"])
	else:
		heading = _safe_heading
		position = _safe_pos
		speed = 0.0


func teleport(x: float, z: float) -> void:
	world.warm_up(Vector3(x, 0, z))
	world.traffic.clear()
	var r := world.nearest_road(x, z)
	if r.has("pos"):
		place(r["pos"], r["dir"])
	else:
		place(Vector2(x, z), Vector2(0, -1))


func _say(t: String) -> void:
	if _msg_cooldown <= 0.0:
		_msg_cooldown = 2.5
		message.emit(t)



func _process(_dt: float) -> void:
	var night: float = DayNight.night_now
	headlight.light_energy = 4.0 * smoothstep(0.1, 0.6, night)
	headlight.visible = night > 0.1


func _update_fuel(dt: float) -> void:
	refuelling = false
	if fuel < TANK * 0.15 and not _low_warned:
		_low_warned = true
		_say("Бензин на исходе! Ближайшая заправка — на карте (M)")
	if fuel <= 0.0:
		_say("Бензин кончился — толкай скутер до заправки или бутылочного стенда")
	if absf(speed) > 0.6 or fuel >= TANK - 0.01:
		return
	var nf: Array = world.pois.nearest_fuel(Vector2(position.x, position.z))
	if nf[0].is_empty() or nf[1] > nf[0][1]:
		return
	var price: float = nf[0][2]
	var add := minf(minf(0.6 * dt, TANK - fuel), money / price)
	if add <= 0.0:
		_say("Не хватает денег на бензин")
		return
	fuel += add
	money -= add * price
	refuelling = true
	_low_warned = false



## Knocked by a traffic vehicle moving with velocity `v`.
func hit_by(v: Vector3) -> void:
	if _hit_cooldown > 0.0:
		return
	_hit_cooldown = 1.0
	var f := forward()
	speed = speed * -0.3 + f.dot(v) * 0.5
	_say("Осторожно! Столкновение с машиной")
