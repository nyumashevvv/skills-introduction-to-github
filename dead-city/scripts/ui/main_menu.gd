extends Control

@onready var continue_button: Button = $Center/VBox/ContinueButton


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	$Center/VBox/NewGameButton.pressed.connect(Game.new_game)
	continue_button.pressed.connect(Game.continue_game)
	$Center/VBox/QuitButton.pressed.connect(get_tree().quit)
	if Game.has_save():
		continue_button.text = "Продолжить (глава %d)" % Game.saved_chapter()
		continue_button.grab_focus()
	else:
		continue_button.visible = false
		$Center/VBox/NewGameButton.grab_focus()
