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
var turbo := false
var surface := World.ROAD
var model: Node3D
var wheel_front: Node3D
var wheel_rear: Node3D
const WHEEL_R := 0.28
var _safe_pos := Vector3.ZERO
var _safe_heading := 0.0
var _safe_timer := 0.0
var _msg_cooldown := 0.0

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
	var thr := Input.get_action_strength("gas")
	var brk := Input.get_action_strength("brake")
	var st := Input.get_action_strength("left") - Input.get_action_strength("right")
	turbo = Input.is_action_pressed("turbo")
	if Input.is_action_just_pressed("reset"):
		reset_to_safe()
		return

	surface = world.class_at(position.x, position.z)
	var vmax := MAX_ROAD
	if surface == World.SAND:
		vmax = MAX_SAND
	elif surface in [World.GRASS, World.JUNGLE, World.URBAN, World.ROCK]:
		vmax = MAX_OFFROAD
	if turbo:
		vmax *= TURBO_MULT
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
	odometer += (np - position).length()
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
	var r := world.nearest_road(x, z)
	if r.has("pos"):
		place(r["pos"], r["dir"])
	else:
		place(Vector2(x, z), Vector2(0, -1))


func _say(t: String) -> void:
	if _msg_cooldown <= 0.0:
		_msg_cooldown = 2.5
		message.emit(t)
