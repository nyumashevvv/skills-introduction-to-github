class_name GameAudio
extends Node
## Sound: scooter engine pitched by speed and throttle, horn (H), and ambient
## layers mixed by where you are and the time of day: surf near the sea,
## cicadas in jungle and plantations by day, crickets and frogs at night,
## town noise among buildings.

var world: World
var scooter: Scooter
var players := {}
var _probe_t := 0.0
var _mix := {"surf": 0.0, "cicadas": 0.0, "night": 0.0, "town": 0.0}


func setup() -> void:
	for n in ["engine", "surf", "cicadas", "night", "town", "horn"]:
		var st: AudioStreamWAV = load("res://sounds/%s.wav" % n)
		if n != "horn":
			st.loop_mode = AudioStreamWAV.LOOP_FORWARD
			st.loop_begin = 0
			st.loop_end = st.data.size() / 2
		var p := AudioStreamPlayer.new()
		p.stream = st
		p.volume_db = -80.0
		add_child(p)
		if n != "horn":
			p.play()
		players[n] = p
	players["horn"].volume_db = -6.0
	if not InputMap.has_action("horn"):
		InputMap.add_action("horn")
		var ev := InputEventKey.new()
		ev.physical_keycode = KEY_H
		InputMap.action_add_event("horn", ev)


func _process(dt: float) -> void:
	# engine: idle 0.55x .. full speed 2.2x pitch, louder on throttle
	var v := absf(scooter.speed)
	var thr := Input.get_action_strength("gas")
	var e: AudioStreamPlayer = players["engine"]
	var target_pitch := 0.55 + v / 22.0 * 1.45 + thr * 0.12
	if scooter.turbo:
		target_pitch = minf(target_pitch, 2.6)
	e.pitch_scale = lerpf(e.pitch_scale, clampf(target_pitch, 0.4, 2.8), clampf(dt * 5.0, 0.0, 1.0))
	var eng_db := -16.0 + thr * 6.0 + minf(v, 22.0) * 0.15
	if scooter.fuel <= 0.0:
		eng_db = -80.0
	e.volume_db = lerpf(e.volume_db, eng_db, clampf(dt * 6.0, 0.0, 1.0))
	if Input.is_action_just_pressed("horn"):
		players["horn"].play()
	# ambience: probe the surroundings a few times a second
	_probe_t -= dt
	if _probe_t <= 0.0:
		_probe_t = 0.35
		_probe()
	for n in _mix:
		var p: AudioStreamPlayer = players[n]
		var db := linear_to_db(maxf(_mix[n], 0.0001))
		p.volume_db = lerpf(p.volume_db, db, clampf(dt * 2.0, 0.0, 1.0))


func _probe() -> void:
	var p := scooter.position
	var sea := 0
	var green := 0
	var town := 0
	var n := 0
	for r in [25.0, 70.0, 140.0]:
		for k in 8:
			var a := k * TAU / 8.0
			var x: float = p.x + cos(a) * r
			var z: float = p.z + sin(a) * r
			n += 1
			if world.height_at(x, z) < 0.0:
				sea += 1
				continue
			var cl := world.class_at(x, z)
			if cl == World.JUNGLE or cl == World.GRASS:
				green += 1
			elif cl == World.BUILDING or cl == World.URBAN or cl == World.ROAD:
				town += 1
	var night := DayNight.night_now
	_mix["surf"] = 0.8 * minf(1.0, sea / 6.0)
	_mix["cicadas"] = 0.35 * (green / float(n)) * (1.0 - night)
	_mix["night"] = 0.5 * (0.3 + 0.7 * green / float(n)) * night
	_mix["town"] = 0.45 * (town / float(n)) * (1.0 - 0.6 * night)


## Current ambience mix (for tests / debugging).
func mix() -> Dictionary:
	return _mix.duplicate()
