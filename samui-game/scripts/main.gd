extends Node3D
## Sets up the scene: environment, island, scooter, camera and HUD.

var world: World
var scooter: Scooter
var camera: Camera3D
var hud: Hud
var cam_mode := 0
var quality := 2
var env: Environment
var sun: DirectionalLight3D
var daynight: DayNight
var missions: Missions
var audio: GameAudio
var _cam_pos := Vector3.ZERO
var _shot := {}   # debug: --shot=file.png --frames=N --pos=x,z --cam=N --gas --map
var _frame := 0

const ACTIONS := {
	"gas": [KEY_W, KEY_UP], "brake": [KEY_S, KEY_DOWN], "left": [KEY_A, KEY_LEFT], "right": [KEY_D, KEY_RIGHT],
	"turbo": [KEY_SHIFT], "map": [KEY_M, KEY_TAB], "camera": [KEY_C], "reset": [KEY_R], "quality": [KEY_Q], "time": [KEY_N], "job": [KEY_J],
}


func _ready() -> void:
	for a in ACTIONS:
		if not InputMap.has_action(a):
			InputMap.add_action(a)
		for k in ACTIONS[a]:
			var ev := InputEventKey.new()
			ev.physical_keycode = k
			InputMap.action_add_event(a, ev)

	_setup_environment()
	world = World.new()
	add_child(world)
	scooter = Scooter.new()
	scooter.world = world
	add_child(scooter)
	camera = Camera3D.new()
	camera.fov = 70
	camera.near = 0.2
	camera.far = 40000
	add_child(camera)

	# start on the main road in Chaweng
	var start := Vector2(4600, -2600)
	world.warm_up(Vector3(start.x, 0, start.y))
	var r := world.nearest_road(start.x, start.y, true)
	scooter.place(r.get("pos", start), r.get("dir", Vector2(0, -1)))
	_cam_pos = scooter.position + Vector3(0, 3, 6)

	hud = Hud.new()
	hud.world = world
	hud.scooter = scooter
	add_child(hud)
	scooter.message.connect(hud.show_message)
	missions = Missions.new()
	missions.world = world
	missions.scooter = scooter
	missions.hud = hud
	add_child(missions)
	missions.setup()
	audio = GameAudio.new()
	audio.world = world
	audio.scooter = scooter
	add_child(audio)
	audio.setup()
	hud.show_message("Добро пожаловать на Самуи! Остров в масштабе 1:1. M — карта")
	for arg in OS.get_cmdline_user_args():
		var kv := arg.trim_prefix("--").split("=")
		_shot[kv[0]] = kv[1] if kv.size() > 1 else "1"
	if _shot.has("pos"):
		var xz: PackedStringArray = String(_shot["pos"]).split(",")
		scooter.teleport(float(xz[0]), float(xz[1]))
		_cam_pos = scooter.position + Vector3(0, 3, 6)
	cam_mode = int(_shot.get("cam", "0"))
	if _shot.has("heading"):
		scooter.heading = deg_to_rad(float(_shot["heading"]))
		scooter._update_transform(0.0)
		_cam_pos = scooter.position - scooter.forward() * 5.0 + Vector3.UP * 2.5
	if _shot.has("time"):
		daynight.hour = float(_shot["time"])
		daynight.apply()
	if _shot.has("quality"):
		set_quality(int(_shot["quality"]))
	if _shot.has("gas"):
		Input.action_press("gas")
	if _shot.has("map"):
		hud.bigmap.visible = true


func _setup_environment() -> void:
	# Forward+ look for a tropical afternoon: high sun, humid haze, soft AO
	env = Environment.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.16, 0.42, 0.82)
	sky_mat.sky_horizon_color = Color(0.66, 0.80, 0.93)
	sky_mat.ground_horizon_color = Color(0.66, 0.80, 0.93)
	sky_mat.ground_bottom_color = Color(0.18, 0.3, 0.4)
	sky_mat.sun_angle_max = 20
	sky_mat.sky_energy_multiplier = 1.0
	var sky := Sky.new()
	sky.sky_material = sky_mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_sky_contribution = 0.35
	env.ambient_light_color = Color(0.78, 0.78, 0.76)
	env.ambient_light_energy = 0.7
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.tonemap_exposure = 0.78
	env.tonemap_white = 6.0
	env.ssao_enabled = true
	env.ssao_radius = 1.2
	env.ssao_intensity = 1.6
	env.glow_enabled = true
	env.glow_intensity = 0.35
	env.glow_bloom = 0.04
	env.fog_enabled = true
	env.fog_light_color = Color(0.70, 0.80, 0.90)
	env.fog_density = 0.00012
	env.fog_aerial_perspective = 0.6
	env.fog_sky_affect = 0.0
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.12
	env.adjustment_contrast = 1.05
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55, -35, 0)
	sun.light_energy = 1.5
	sun.light_color = Color(1, 0.95, 0.86)
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 220
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.shadow_blur = 1.5
	add_child(sun)
	daynight = DayNight.new()
	add_child(daynight)
	daynight.setup(env, sun, self)


func _process(dt: float) -> void:
	world.set_focus(scooter.position)
	if _shot.has("shot"):
		_frame += 1
		if _frame == int(_shot.get("frames", "60")):
			get_viewport().get_texture().get_image().save_png(_shot["shot"])
			print("speed ", scooter.speed, " pos ", scooter.position, " fps ", Engine.get_frames_per_second(),
				" triangles ", RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
				" draw calls ", RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
				" night %.2f lights %d lamps-near %d" % [DayNight.night_now, world._light_pool.filter(func(l): return l.visible).size(), world.lamp_points.get(world.chunk_of(scooter.position.x, scooter.position.z), []).size()])
			get_tree().quit()
	if Input.is_action_just_pressed("time"):
		daynight.hour = fposmod(daynight.hour + 1.0, 24.0)
		hud.show_message("Время: " + daynight.clock())
	if Input.is_action_just_pressed("quality"):
		set_quality((quality + 2) % 3)
	if Input.is_action_just_pressed("camera"):
		cam_mode = (cam_mode + 1) % 3
	var f := scooter.forward()
	var p := scooter.position
	var target: Vector3
	var want: Vector3
	match cam_mode:
		0:
			var back := 4.3 + absf(scooter.speed) * 0.07
			want = p - f * back + Vector3.UP * (2.0 + absf(scooter.speed) * 0.02)
			target = p + Vector3.UP * 1.3 + f * 2.0
		1:
			want = p - f * 14.0 + Vector3.UP * 7.0
			target = p + Vector3.UP * 1.0 + f * 6.0
		_:
			want = p - f * 60.0 + Vector3.UP * 140.0
			target = p + f * 40.0
	if _shot.has("look"):
		# debug: look at a point from a given distance/direction: --look=x,z[,dist,height,bearing_deg]
		var lv: PackedStringArray = String(_shot["look"]).split(",")
		var lp := Vector2(float(lv[0]), float(lv[1]))
		var ld := float(lv[2]) if lv.size() > 2 else 30.0
		var lh := float(lv[3]) if lv.size() > 3 else 12.0
		var lb := deg_to_rad(float(lv[4])) if lv.size() > 4 else 0.0
		target = Vector3(lp.x, world.height_at(lp.x, lp.y) + 2.0, lp.y)
		want = target + Vector3(sin(lb) * ld, lh, cos(lb) * ld)
		_cam_pos = want
	if _shot.has("follow-car") and world.traffic.cars.size() > int(_shot["follow-car"]):
		var car: Dictionary = world.traffic.cars[int(_shot["follow-car"])]
		var cf: Vector3 = car["fwd"]
		want = car["pos"] - cf * 9.0 + Vector3.UP * 4.0 + Vector3(-cf.z, 0, cf.x) * 3.0
		target = car["pos"] + cf * 6.0
		_cam_pos = want
	_cam_pos = _cam_pos.lerp(want, clampf(dt * 6.0, 0.0, 1.0))
	if _cam_pos.distance_to(want) > 200.0:
		_cam_pos = want
	var ground := world.height_at(_cam_pos.x, _cam_pos.z)
	_cam_pos.y = maxf(_cam_pos.y, maxf(ground, 0.0) + 1.0)
	camera.position = _cam_pos
	camera.look_at(target, Vector3.UP)


## Q cycles quality: high -> low -> medium -> high.
func set_quality(level: int) -> void:
	quality = level
	world.vegetation.set_quality(level)
	world.traffic.target_count = [18, 30, 45][level]
	env.ssao_enabled = level >= 1
	env.glow_enabled = level >= 1
	sun.directional_shadow_max_distance = [90.0, 150.0, 220.0][level]
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS if level == 0 else DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	hud.show_message("Качество: " + ["низкое", "среднее", "высокое"][level])
