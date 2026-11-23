class_name Missions
extends Node3D
## Gameplay on top of the island:
## - food delivery (J): pick up at a real restaurant/café from OSM near you,
##   deliver to a real address 0.8-3 km away before the timer runs out;
## - sightseeing: all OSM viewpoints and waterfalls are collectibles;
## - progress (money, fuel, found places, deliveries) is saved to user://.

const SAVE_PATH := "user://samui_ride.save"
const PICKUP_R := 10.0
const DROP_R := 12.0
const SIGHT_R := 30.0

var world: World
var scooter: Scooter
var hud: Hud
var restaurants := []           # [Vector2, name]
var sights := []                # [Vector2, name, kind]
var found := {}                 # sight index -> true
var deliveries := 0
var job := {}                   # {state: "pickup"/"drop", from, to, name, time_left, reward}
var beacon: MeshInstance3D
var _save_t := 0.0
var _rng := RandomNumberGenerator.new()


func setup() -> void:
	_rng.randomize()
	for p in world.pois.all:
		var at := Vector2(p["x"], p["z"])
		match p["t"]:
			"food":
				if world.road_dist(at.x, at.y) < 40.0:
					restaurants.append([at, p.get("n", "")])
			"viewpoint", "waterfall":
				sights.append([at, p.get("n", ""), p["t"]])
	beacon = MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 1.6
	cyl.bottom_radius = 1.6
	cyl.height = 60.0
	cyl.radial_segments = 16
	cyl.cap_top = false
	cyl.cap_bottom = false
	beacon.mesh = cyl
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = Color(0.2, 1.0, 0.45, 0.35)
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	beacon.material_override = mat
	beacon.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	beacon.visible = false
	add_child(beacon)
	load_game()
	print("missions: %d restaurants, %d sights" % [restaurants.size(), sights.size()])


func _process(dt: float) -> void:
	var p := Vector2(scooter.position.x, scooter.position.z)
	if Input.is_action_just_pressed("job"):
		if job.is_empty():
			start_delivery()
		else:
			job = {}
			beacon.visible = false
			hud.show_message("Заказ отменён")
	if not job.is_empty():
		_update_job(p, dt)
	for i in sights.size():
		if found.has(i):
			continue
		if p.distance_squared_to(sights[i][0]) < SIGHT_R * SIGHT_R:
			found[i] = true
			var kind := "Водопад" if sights[i][2] == "waterfall" else "Смотровая площадка"
			var nm: String = sights[i][1]
			hud.show_message("%s найдена%s! (%d из %d)  +100 ฿" % [kind, (": " + nm) if nm != "" else "", found.size(), sights.size()])
			scooter.money += 100.0
			save_game()
	_save_t += dt
	if _save_t > 20.0:
		_save_t = 0.0
		save_game()


func start_delivery() -> void:
	var p := Vector2(scooter.position.x, scooter.position.z)
	var near := []
	for r in restaurants:
		var d: float = r[0].distance_to(p)
		if d > 150.0 and d < 1500.0:
			near.append(r)
	if near.is_empty():
		hud.show_message("Рядом нет ресторанов с заказами — подъезжай ближе к посёлкам")
		return
	var named := near.filter(func(r): return r[1] != "")
	if not named.is_empty() and _rng.randf() < 0.85:
		near = named
	var from: Array = near[_rng.randi() % near.size()]
	# customer: a real building 0.8-3 km from the restaurant, next to a road
	var to := Vector2.INF
	for attempt in 60:
		var c := world.chunk_of(from[0].x + _rng.randf_range(-3000, 3000), from[0].y + _rng.randf_range(-3000, 3000))
		var list: Array = world.buildings_data[c]
		if list.is_empty():
			continue
		var b: Dictionary = list[_rng.randi() % list.size()]
		var pts: Array = b["p"]
		var q := Vector2(pts[0], pts[1])
		var d: float = q.distance_to(from[0])
		if d < 800.0 or d > 3000.0 or world.road_dist(q.x, q.y) > 25.0:
			continue
		var r := world.nearest_road(q.x, q.y)
		if r.has("pos"):
			to = r["pos"]
			break
	if to == Vector2.INF:
		hud.show_message("Не нашёл адрес доставки, попробуй ещё раз (J)")
		return
	var dist: float = from[0].distance_to(p) + to.distance_to(from[0])
	job = {"state": "pickup", "from": from[0], "to": to, "name": from[1] if from[1] != "" else "ресторан",
		"time_left": 90.0 + dist / 9.0, "reward": round(60.0 + to.distance_to(from[0]) * 0.08)}
	_show_beacon(from[0])
	hud.show_message("Новый заказ: забрать еду в «%s» (%.1f км)" % [job["name"], from[0].distance_to(p) / 1000.0])


func _update_job(p: Vector2, dt: float) -> void:
	job["time_left"] -= dt
	var target: Vector2 = job["from"] if job["state"] == "pickup" else job["to"]
	if job["state"] == "pickup" and p.distance_to(target) < PICKUP_R and absf(scooter.speed) < 3.0:
		job["state"] = "drop"
		_show_beacon(job["to"])
		hud.show_message("Еда у тебя! Вези клиенту (%.1f км)" % [p.distance_to(job["to"]) / 1000.0])
	elif job["state"] == "drop" and p.distance_to(target) < DROP_R and absf(scooter.speed) < 3.0:
		var late: bool = job["time_left"] < 0.0
		var pay: float = job["reward"] * (0.5 if late else 1.0) + (0.0 if late else round(job["time_left"] * 0.3))
		scooter.money += pay
		deliveries += 1
		hud.show_message("Доставлено%s! +%d ฿   (доставок: %d)" % [" с опозданием" if late else "", pay, deliveries])
		job = {}
		beacon.visible = false
		save_game()


func _show_beacon(at: Vector2) -> void:
	beacon.position = Vector3(at.x, world.height_at(at.x, at.y) + 30.0, at.y)
	beacon.visible = true


func target() -> Vector2:
	if job.is_empty():
		return Vector2.INF
	return job["from"] if job["state"] == "pickup" else job["to"]


func status() -> String:
	var s := "Находки: %d / %d   Доставки: %d" % [found.size(), sights.size(), deliveries]
	if not job.is_empty():
		var p := Vector2(scooter.position.x, scooter.position.z)
		var t := target()
		var what := "забрать в «%s»" % job["name"] if job["state"] == "pickup" else "доставить клиенту"
		var tl: float = job["time_left"]
		s = "Заказ: %s — %.1f км %s   ⏱ %s" % [what, p.distance_to(t) / 1000.0, hud._compass(t - p),
			("%d:%02d" % [int(tl) / 60, int(tl) % 60]) if tl > 0 else "опоздание"]
	else:
		s += "   J — взять заказ"
	return s


# ------------------------------------------------------------ save / load
func save_game() -> void:
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({"money": scooter.money, "fuel": scooter.fuel, "found": found.keys(),
		"deliveries": deliveries, "odo": scooter.odometer, "hour": get_parent().daynight.hour}))


func load_game() -> void:
	if not FileAccess.file_exists(SAVE_PATH) or OS.get_cmdline_user_args().has("--fresh"):
		return
	var d = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if typeof(d) != TYPE_DICTIONARY:
		return
	scooter.money = d.get("money", scooter.money)
	scooter.fuel = d.get("fuel", scooter.fuel)
	scooter.odometer = d.get("odo", 0.0)
	deliveries = int(d.get("deliveries", 0))
	for i in d.get("found", []):
		found[int(i)] = true
