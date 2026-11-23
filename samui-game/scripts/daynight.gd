class_name DayNight
extends Node
## Time of day on Koh Samui (about 9.5° N): sunrise ~6:10, sunset ~18:20.
## Drives the sun, moon, sky, ambient light, fog and the global shader values
## `night` (0 day .. 1 night) and `dusk` used by buildings, lamps and signs.

const SUNRISE := 6.15
const SUNSET := 18.35
const MINUTES_PER_GAME_DAY := 24.0

var hour := 16.5
var speed := 1.0                # time multiplier (N key skips ahead)
var env: Environment
var sun: DirectionalLight3D
var moon: DirectionalLight3D
var sky_mat: ShaderMaterial
var night := 0.0
var dusk := 0.0
static var night_now := 0.0     # readable from anywhere (lights, signs, headlight)


func setup(e: Environment, s: DirectionalLight3D, parent: Node3D) -> void:
	env = e
	sun = s
	sky_mat = ShaderMaterial.new()
	sky_mat.shader = load("res://shaders/sky.gdshader")
	env.sky.sky_material = sky_mat
	moon = DirectionalLight3D.new()
	moon.light_color = Color(0.6, 0.7, 1.0)
	moon.shadow_enabled = false
	moon.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
	parent.add_child(moon)
	moon.look_at_from_position(Vector3.ZERO, Vector3(-0.3, -0.6, 0.74), Vector3.UP)
	apply()


func _process(dt: float) -> void:
	hour = fposmod(hour + dt * speed * 24.0 / (MINUTES_PER_GAME_DAY * 60.0), 24.0)
	apply()


func clock() -> String:
	return "%02d:%02d" % [int(hour), int(fmod(hour, 1.0) * 60.0)]


func apply() -> void:
	# continuous sun path over 24 h: east at sunrise, high in the south at noon, west at sunset
	var noon := (SUNRISE + SUNSET) * 0.5
	var ang := (hour - noon) / 24.0 * TAU
	var s := Vector3(-sin(ang), cos(ang) * 0.95 - 0.02, 0.35).normalized()
	sun.look_at_from_position(Vector3.ZERO, -s, Vector3.UP)
	# civil twilight: it only gets dark once the sun is well below the horizon
	var day := smoothstep(-0.04, 0.14, s.y)
	night = 1.0 - smoothstep(-0.16, -0.03, s.y)
	dusk = clampf(1.0 - absf(s.y - 0.0) / 0.2, 0.0, 1.0)
	var warm := Color(1.0, 0.45, 0.2).lerp(Color(1.0, 0.95, 0.86), smoothstep(0.03, 0.45, s.y))
	sun.light_color = warm
	sun.light_energy = 1.5 * day
	sun.visible = day > 0.001
	moon.light_energy = 0.22 * night
	moon.visible = night > 0.01
	env.ambient_light_color = Color(0.78, 0.78, 0.76).lerp(Color(0.22, 0.27, 0.42), night).lerp(Color(0.9, 0.7, 0.6), dusk * 0.4)
	env.ambient_light_energy = lerpf(0.7, 0.5, night) - dusk * 0.15
	env.ambient_light_sky_contribution = lerpf(0.35, 0.1, night)
	env.fog_light_color = Color(0.70, 0.80, 0.90).lerp(Color(0.03, 0.05, 0.1), night).lerp(Color(0.85, 0.5, 0.4), dusk * 0.6)
	env.tonemap_exposure = lerpf(0.78, 1.45, night)
	env.glow_intensity = lerpf(0.35, 1.0, night)
	sky_mat.set_shader_parameter("night", night)
	sky_mat.set_shader_parameter("dusk", dusk)
	night_now = night
	RenderingServer.global_shader_parameter_set("night", night)
	RenderingServer.global_shader_parameter_set("dusk", dusk)
