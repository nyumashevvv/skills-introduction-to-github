@tool
class_name Block
extends StaticBody3D
## A solid box (or cylinder): mesh and collision always match [member size].

@export var size := Vector3(2.0, 2.0, 2.0):
	set(value):
		size = value
		_update()

@export var material: Material:
	set(value):
		material = value
		_update()

## Uses size.x as the diameter and size.y as the height.
@export var cylinder := false:
	set(value):
		cylinder = value
		_update()


func _ready() -> void:
	_update()


func _update() -> void:
	if not is_node_ready():
		return
	if cylinder:
		var mesh := CylinderMesh.new()
		mesh.top_radius = size.x / 2.0
		mesh.bottom_radius = size.x / 2.0
		mesh.height = size.y
		mesh.material = material
		$MeshInstance3D.mesh = mesh
		var shape := CylinderShape3D.new()
		shape.radius = size.x / 2.0
		shape.height = size.y
		$CollisionShape3D.shape = shape
	else:
		var mesh := BoxMesh.new()
		mesh.size = size
		mesh.material = material
		$MeshInstance3D.mesh = mesh
		var shape := BoxShape3D.new()
		shape.size = size
		$CollisionShape3D.shape = shape
