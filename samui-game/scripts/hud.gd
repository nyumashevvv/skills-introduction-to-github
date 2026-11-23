class_name Hud
extends CanvasLayer
## Speedometer, location, minimap, full island map with teleport, touch controls.

var world: World
var scooter: Scooter
var speed_label: Label
var place_label: Label
var info_label: Label
var msg_label: Label
var help_label: Label
var minimap: MiniMap
var bigmap: BigMap
var touch: TouchPad
var _msg_t := 0.0


func _ready() -> void:
	var font_big := 44
	speed_label = _label(Vector2(24, -96), font_big, Control.PRESET_BOTTOM_LEFT)
	place_label = _label(Vector2(24, 18), 30, Control.PRESET_TOP_LEFT)
	info_label = _label(Vector2(24, 60), 16, Control.PRESET_TOP_LEFT)
	help_label = _label(Vector2(24, -40), 15, Control.PRESET_BOTTOM_LEFT)
	help_label.text = "W/S — газ/тормоз   A/D — руль   Shift — турбо   M — карта   C — камера   R — на дорогу   Q — качество"
	msg_label = _label(Vector2(0, 120), 24, Control.PRESET_TOP_WIDE)
	msg_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	minimap = MiniMap.new()
	minimap.world = world
	minimap.scooter = scooter
	minimap.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	minimap.position = Vector2(-244, 16)
	minimap.size = Vector2(228, 228)
	add_child(minimap)
	bigmap = BigMap.new()
	bigmap.world = world
	bigmap.scooter = scooter
	bigmap.set_anchors_preset(Control.PRESET_FULL_RECT)
	bigmap.visible = false
	add_child(bigmap)
	touch = TouchPad.new()
	touch.set_anchors_preset(Control.PRESET_FULL_RECT)
	touch.mouse_filter = Control.MOUSE_FILTER_IGNORE
	touch.visible = DisplayServer.is_touchscreen_available()
	add_child(touch)
	if touch.visible:
		help_label.text = "Слева — руль, справа — газ/тормоз. Кнопки сверху: карта, турбо"


func _label(pos: Vector2, size: int, preset: int) -> Label:
	var l := Label.new()
	l.set_anchors_preset(preset)
	l.position = pos
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	l.add_theme_constant_override("outline_size", 8)
	add_child(l)
	return l


func show_message(t: String) -> void:
	msg_label.text = t
	_msg_t = 3.0


func _process(dt: float) -> void:
	var kmh := absf(scooter.speed) * 3.6
	speed_label.text = "%d км/ч%s" % [kmh, "  ТУРБО" if scooter.turbo else ""]
	var p := scooter.position
	place_label.text = _where(p)
	var lon := p.x / (111320.0 * cos(deg_to_rad(9.495))) + 100.01
	var lat := -p.z / 110574.0 + 9.495
	info_label.text = "%.5f° N  %.5f° E    высота %d м    пройдено %.1f км" % [lat, lon, p.y, scooter.odometer / 1000.0]
	_msg_t -= dt
	msg_label.modulate.a = clampf(_msg_t, 0.0, 1.0)
	if Input.is_action_just_pressed("map"):
		bigmap.visible = not bigmap.visible


func _where(p: Vector3) -> String:
	var best := ""
	var bd := INF
	var spot := ""
	var sd := INF
	for pl in world.places:
		var d := Vector2(pl["x"] - p.x, pl["z"] - p.z).length()
		if pl["k"] == "town":
			if d < bd:
				bd = d
				best = pl["n"]
		elif d < sd:
			sd = d
			spot = pl["n"]
	var s := best if bd < 2500 else "Ко Самуи"
	if sd < 300:
		s += " · " + spot
	if world.class_at(p.x, p.z) == World.SAND:
		s += " · пляж"
	return s


# ---------------------------------------------------------------- minimap
class MiniMap extends Control:
	var world: World
	var scooter: Scooter
	const RANGE := 1500.0  # metres from centre to edge

	func _process(_dt: float) -> void:
		queue_redraw()

	func _draw() -> void:
		var tex := world.colormap
		var p := scooter.position
		var c := Vector2(p.x + World.HALF, p.z + World.HALF) / World.CELL
		var r := RANGE / World.CELL
		draw_rect(Rect2(Vector2.ZERO, size).grow(3), Color(0, 0, 0, 0.6))
		draw_texture_rect_region(tex, Rect2(Vector2.ZERO, size), Rect2(c - Vector2(r, r), Vector2(r, r) * 2))
		var k := size.x / (RANGE * 2)
		for pl in world.places:
			if pl["k"] != "town":
				continue
			var q := (Vector2(pl["x"] - p.x, pl["z"] - p.z)) * k + size / 2
			if Rect2(Vector2.ZERO, size).has_point(q):
				draw_circle(q, 3, Color.WHITE)
				draw_string(ThemeDB.fallback_font, q + Vector2(5, 4), pl["n"], HORIZONTAL_ALIGNMENT_LEFT, -1, 12)
		_arrow(self, size / 2, scooter.heading, 9.0)
		draw_string(ThemeDB.fallback_font, Vector2(size.x / 2 - 4, 14), "С", HORIZONTAL_ALIGNMENT_LEFT, -1, 14)

	static func _arrow(ci: CanvasItem, at: Vector2, heading: float, s: float) -> void:
		var f := Vector2(-sin(heading), -cos(heading))
		var sd := Vector2(-f.y, f.x)
		var pts := PackedVector2Array([at + f * s * 1.4, at - f * s * 0.8 + sd * s, at - f * s * 0.3, at - f * s * 0.8 - sd * s])
		ci.draw_colored_polygon(pts, Color(1, 0.2, 0.2))
		ci.draw_polyline(pts + PackedVector2Array([pts[0]]), Color.WHITE, 1.5)


# ---------------------------------------------------------------- full map
class BigMap extends Control:
	var world: World
	var scooter: Scooter
	var _rect := Rect2()

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP

	func _process(_dt: float) -> void:
		if visible:
			queue_redraw()

	func _draw() -> void:
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.02, 0.1, 0.15, 0.92))
		var s := minf(size.x, size.y - 60) * 0.98
		# crop to the island area (the outer sea is not interesting)
		var crop := Rect2(Vector2(250, 250), Vector2(1900, 1900))
		_rect = Rect2((size - Vector2(s, s)) / 2 + Vector2(0, 20), Vector2(s, s))
		draw_texture_rect_region(world.colormap, _rect, crop)
		for pl in world.places:
			if pl["k"] in ["town", "airport", "waterfall"] or pl["en"] in ["Big Buddha"]:
				var q := _to_screen(pl["x"], pl["z"])
				var col := Color.WHITE if pl["k"] == "town" else Color(1, 0.85, 0.5)
				draw_circle(q, 3.5, col)
				if pl["k"] != "waterfall":
					draw_string(ThemeDB.fallback_font, q + Vector2(6, 5), pl["n"], HORIZONTAL_ALIGNMENT_LEFT, -1, 14, col)
		MiniMap._arrow(self, _to_screen(scooter.position.x, scooter.position.z), scooter.heading, 10.0)
		draw_string(ThemeDB.fallback_font, Vector2(20, 34), "Ко Самуи 1:1 — нажми на карту, чтобы переместиться.  M — закрыть", HORIZONTAL_ALIGNMENT_LEFT, -1, 20)
		draw_string(ThemeDB.fallback_font, Vector2(20, size.y - 14), "© OpenStreetMap contributors (ODbL) · здания: Overture Maps, Google Open Buildings, Microsoft · снимок: Copernicus Sentinel-2 · рельеф: SRTM", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(1, 1, 1, 0.6))

	func _to_screen(x: float, z: float) -> Vector2:
		var px := (Vector2(x, z) + Vector2(World.HALF, World.HALF)) / World.CELL
		return _rect.position + (px - Vector2(250, 250)) / 1900.0 * _rect.size.x

	func _gui_input(e: InputEvent) -> void:
		var pos := Vector2.INF
		if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			pos = e.position
		elif e is InputEventScreenTouch and e.pressed:
			pos = e.position
		if pos != Vector2.INF and _rect.has_point(pos):
			var px := (pos - _rect.position) / _rect.size.x * 1900.0 + Vector2(250, 250)
			var w := px * World.CELL - Vector2(World.HALF, World.HALF)
			scooter.teleport(w.x, w.y)
			visible = false
			accept_event()


# ---------------------------------------------------------------- touch
class TouchPad extends Control:
	var _held := {}   # touch index -> action
	var _buttons := {}

	func _layout() -> void:
		var w := size.x
		var h := size.y
		var b := minf(w, h) * 0.2
		_buttons = {
			"left": Rect2(20, h - b - 30, b, b),
			"right": Rect2(40 + b, h - b - 30, b, b),
			"gas": Rect2(w - b - 20, h - b * 2.2 - 30, b, b * 1.2),
			"brake": Rect2(w - b - 20, h - b - 20, b, b * 0.8),
			"map": Rect2(w - 290 - b * 0.7, 20, b * 0.7, b * 0.45),
			"turbo": Rect2(w - 290 - b * 0.7, 30 + b * 0.45, b * 0.7, b * 0.45),
		}

	func _process(_dt: float) -> void:
		if visible:
			queue_redraw()

	func _draw() -> void:
		_layout()
		var names := {"left": "◀", "right": "▶", "gas": "ГАЗ", "brake": "ТОРМ", "map": "КАРТА", "turbo": "ТУРБО"}
		for k in _buttons:
			var r: Rect2 = _buttons[k]
			var on := _held.values().has(k)
			draw_rect(r, Color(1, 1, 1, 0.35 if on else 0.18))
			draw_string(ThemeDB.fallback_font, r.position + Vector2(10, r.size.y / 2 + 8), names[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 22)

	func _input(e: InputEvent) -> void:
		if not visible:
			return
		if e is InputEventScreenTouch:
			if e.pressed:
				_press(e.index, e.position)
			elif _held.has(e.index):
				_release(e.index)
		elif e is InputEventScreenDrag:
			if _held.has(e.index) and not _hit(e.position) == _held[e.index]:
				_release(e.index)
				_press(e.index, e.position)

	func _hit(p: Vector2) -> String:
		for k in _buttons:
			if _buttons[k].has_point(p):
				return k
		return ""

	func _press(i: int, p: Vector2) -> void:
		var k := _hit(p)
		if k == "":
			return
		_held[i] = k
		Input.action_press(k)

	func _release(i: int) -> void:
		Input.action_release(_held[i])
		_held.erase(i)
