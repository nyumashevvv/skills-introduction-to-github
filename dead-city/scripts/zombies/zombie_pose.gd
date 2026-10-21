class_name ZombiePose
extends SkeletonModifier3D
## Layered on top of the body animation: arms reaching forward like a classic
## zombie, and a head that can be "removed" by a headshot.

## 0 = plain animation, 1 = arms fully stretched towards the player.
var reach := 0.0
var head_hidden := false

var _upper := PackedInt32Array()
var _lower := PackedInt32Array()
var _head := -1


func _ready() -> void:
	var skeleton := get_skeleton()
	for side in ["L", "R"]:
		_upper.append(skeleton.find_bone("UpperArm." + side))
		_lower.append(skeleton.find_bone("LowerArm." + side))
	_head = skeleton.find_bone("Head")


func _process_modification() -> void:
	var skeleton := get_skeleton()
	if skeleton == null:
		return
	if reach > 0.01:
		for i in 2:
			var bone := _upper[i]
			if bone < 0:
				continue
			var parent_global := skeleton.get_bone_global_pose(skeleton.get_bone_parent(bone))
			var global := parent_global * skeleton.get_bone_pose(bone)
			# Models face +Z in skeleton space; a character's left side is +X.
			var target := Vector3(0.2 if i == 0 else -0.2, -0.1, 1.0).normalized()
			var turn := Quaternion(global.basis.y.normalized(), target)
			var wanted := (parent_global.basis.inverse() * (Basis(turn) * global.basis)).get_rotation_quaternion()
			skeleton.set_bone_pose_rotation(bone, skeleton.get_bone_pose_rotation(bone).slerp(wanted, reach))
			# Straighten the elbow.
			var lower := _lower[i]
			var straight := skeleton.get_bone_rest(lower).basis.get_rotation_quaternion()
			skeleton.set_bone_pose_rotation(lower, skeleton.get_bone_pose_rotation(lower).slerp(straight, reach * 0.8))
	if head_hidden and _head >= 0:
		skeleton.set_bone_pose_scale(_head, Vector3.ONE * 0.001)
