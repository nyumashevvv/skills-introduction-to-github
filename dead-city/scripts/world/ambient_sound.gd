extends AudioStreamPlayer3D
## Background sound that keeps coming back: a loop (gap 0, the fountain, the muzak) or something every so often
## (the PA announcement, a shorting lamp), after a random pause between gap_min and gap_max seconds.

@export var gap_min := 0.0
@export var gap_max := 0.0

var _wait := 0.0


func _ready() -> void:
	finished.connect(_on_finished)
	_wait = randf_range(0.0, gap_max) if gap_max > 0.0 else 0.0
	if _wait == 0.0:
		play(randf() * maxf(stream.get_length() - 0.1, 0.0) if stream else 0.0)


func _process(delta: float) -> void:
	if _wait <= 0.0:
		return
	_wait -= delta
	if _wait <= 0.0:
		play()


func _on_finished() -> void:
	_wait = randf_range(gap_min, gap_max)
	if _wait <= 0.0:
		play()
