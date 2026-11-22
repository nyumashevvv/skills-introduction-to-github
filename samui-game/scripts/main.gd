extends Node3D
## Sets up the scene: environment, island, scooter, camera and HUD.

var world: World
var scooter: Scooter
var camera: Camera3D
var hud: Hud
var cam_mode := 0
var _cam_pos := Vector3.ZERO
var _shot := {}   # debug: --shot=file.png --frames=N --pos=x,z --cam=N --gas --map
var _frame := 0

const ACTIONS := {
	"gas": [KEY_W, KEY_UP], "brake": [KEY_S, KEY_DOWN], "left": [KEY_A, KEY_LEFT], "right": [KEY_D, KEY_RIGHT],
	"turbo": [KEY_SHIFT], "map": [KEY_M, KEY_TAB], "camera": [KEY_C], "reset": [KEY_R],
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
	hud.show_message("Добро пожаловать на Самуи! Остров в масштабе 1:1. M — карта")
	for arg in OS.get_cmdline_user_args():
		var kv := arg.trim_prefix("--").split("=")
		_shot[kv[0]] = kv[1] if kv.size() > 1 else "1"
	if _shot.has("pos"):
		var xz: PackedStringArray = String(_shot["pos"]).split(",")
		scooter.teleport(float(xz[0]), float(xz[1]))
		_cam_pos = scooter.position + Vector3(0, 3, 6)
	cam_mode = int(_shot.get("cam", "0"))
	if _shot.has("gas"):
		Input.action_press("gas")
	if _shot.has("map"):
		hud.bigmap.visible = true


func _setup_environment() -> void:
	var env := Environment.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.22, 0.48, 0.85)
	sky_mat.sky_horizon_color = Color(0.72, 0.84, 0.95)
	sky_mat.ground_horizon_color = Color(0.72, 0.84, 0.95)
	sky_mat.ground_bottom_color = Color(0.2, 0.35, 0.45)
	sky_mat.sun_angle_max = 20
	var sky := Sky.new()
	sky.sky_material = sky_mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.62, 0.68, 0.78)
	env.ambient_light_energy = 0.5
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_white = 1.6
	env.fog_enabled = true
	env.fog_light_color = Color(0.72, 0.82, 0.92)
	env.fog_density = 0.00006
	env.fog_sky_affect = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52, -35, 0)
	sun.light_energy = 1.05
	sun.light_color = Color(1, 0.96, 0.88)
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 160
	add_child(sun)


func _process(dt: float) -> void:
	world.set_focus(scooter.position)
	if _shot.has("shot"):
		_frame += 1
		if _frame == int(_shot.get("frames", "60")):
			get_viewport().get_texture().get_image().save_png(_shot["shot"])
			print("speed ", scooter.speed, " pos ", scooter.position, " fps ", Engine.get_frames_per_second())
			get_tree().quit()
	if Input.is_action_just_pressed("camera"):
		cam_mode = (cam_mode + 1) % 3
	var f := scooter.forward()
	var p := scooter.position
	var target: Vector3
	var want: Vector3
	match cam_mode:
		0:
			var back := 5.5 + absf(scooter.speed) * 0.08
			want = p - f * back + Vector3.UP * (2.4 + absf(scooter.speed) * 0.02)
			target = p + Vector3.UP * 1.3 + f * 2.0
		1:
			want = p - f * 14.0 + Vector3.UP * 7.0
			target = p + Vector3.UP * 1.0 + f * 6.0
		_:
			want = p - f * 60.0 + Vector3.UP * 140.0
			target = p + f * 40.0
	_cam_pos = _cam_pos.lerp(want, clampf(dt * 6.0, 0.0, 1.0))
	if _cam_pos.distance_to(want) > 200.0:
		_cam_pos = want
	var ground := world.height_at(_cam_pos.x, _cam_pos.z)
	_cam_pos.y = maxf(_cam_pos.y, maxf(ground, 0.0) + 1.0)
	camera.position = _cam_pos
	camera.look_at(target, Vector3.UP)
