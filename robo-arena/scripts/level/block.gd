@tool
class_name Block
extends StaticBody3D
## A solid box: mesh and collision always match [member size].

@export var size := Vector3(2.0, 2.0, 2.0):
	set(value):
		size = value
		_update()

@export var material: Material:
	set(value):
		material = value
		_update()


func _ready() -> void:
	_update()


func _update() -> void:
	if not is_node_ready():
		return
	var mesh := BoxMesh.new()
	mesh.size = size
	mesh.material = material
	$MeshInstance3D.mesh = mesh
	var shape := BoxShape3D.new()
	shape.size = size
	$CollisionShape3D.shape = shape
