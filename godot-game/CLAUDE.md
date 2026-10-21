# Coin Jumper — Godot project

- Engine: Godot 4.3, GDScript only, renderer "GL Compatibility".
- Use static typing in GDScript (`var x: int`, `-> void`), tabs for indentation.
- Layout: scenes in `scenes/`, scripts in `scripts/` (one script per scene, same name).
- No external art yet: visuals are ColorRect / `_draw()` placeholders.
- Input uses built-in `ui_*` actions (ui_left, ui_right, ui_accept, ui_up).
- UI text is in Russian.

## Checking changes
Run from this folder (`godot` = path to the Godot 4.3 binary):

    godot --headless --path . --import          # parse/import, reports script errors
    godot --headless --path . --quit-after 180  # run the main scene for 180 frames
