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

## Meshes and shapes shared by every block of the same size, shape and material: a big chapter has hundreds of
## blocks but only a few dozen different ones, and one mesh each would run some GPUs out of buffers.
static var _meshes := {}
static var _shapes := {}


func _ready() -> void:
	_update()


func _update() -> void:
	if not is_node_ready():
		return
	var key := "%s|%s|%s" % [size, cylinder, material.get_rid() if material else RID()]
	var mesh: PrimitiveMesh = _meshes.get(key)
	if mesh == null:
		if cylinder:
			var cyl := CylinderMesh.new()
			cyl.top_radius = size.x / 2.0
			cyl.bottom_radius = size.x / 2.0
			cyl.height = size.y
			mesh = cyl
		else:
			var box := BoxMesh.new()
			box.size = size
			mesh = box
		mesh.material = material
		_meshes[key] = mesh
	$MeshInstance3D.mesh = mesh
	var shape_key := "%s|%s" % [size, cylinder]
	var shape: Shape3D = _shapes.get(shape_key)
	if shape == null:
		if cylinder:
			var round_shape := CylinderShape3D.new()
			round_shape.radius = size.x / 2.0
			round_shape.height = size.y
			shape = round_shape
		else:
			var box_shape := BoxShape3D.new()
			box_shape.size = size
			shape = box_shape
		_shapes[shape_key] = shape
	$CollisionShape3D.shape = shape
