extends Node3D
## The helicopter of the ending: spins its rotors and flies its route on its own clock (lift off the pad, climb over
## the stadium, cross the city towards the sunrise); the cutscene's camera marks ride along as its children.

## Route: [time (s), position, nose pitch (rad)], eased between the points.
const ROUTE := [
	[0.0, Vector3(0, 0, 0), 0.0],
	[4.0, Vector3(0, 3, 0), 0.0],
	[12.0, Vector3(0, 30, -14), -0.18],
	[22.0, Vector3(-6, 62, -90), -0.22],
	[34.0, Vector3(-10, 75, -230), -0.2],
	[60.0, Vector3(-14, 85, -560), -0.2],
]

var _time := 0.0

@onready var main_rotor: Node3D = $Model/MainRotor
@onready var tail_rotor: Node3D = $Model/TailRotor


func _process(delta: float) -> void:
	_time += delta
	main_rotor.rotate_y(delta * 25.0)
	tail_rotor.rotate_x(delta * 35.0)
	for i in ROUTE.size() - 1:
		var a: Array = ROUTE[i]
		var b: Array = ROUTE[i + 1]
		if _time <= b[0] or i == ROUTE.size() - 2:
			var t := smoothstep(a[0], b[0], _time)
			position = (a[1] as Vector3).lerp(b[1], t)
			rotation.x = lerpf(a[2], b[2], t)
			rotation.z = sin(_time * 0.7) * 0.03
			break
