# Robo Arena — Godot 4.7 FPS

Wave-survival first-person shooter. GDScript only, Forward+ renderer.

## Conventions
- Static typing everywhere (`var x: int`, `-> void`), tabs for indentation.
- Scenes in `scenes/<area>/`, their scripts in `scripts/<area>/` with the same name.
- No imported art: models are built from BoxMesh parts, materials live in `materials/*.tres`,
  sounds in `sounds/` are procedurally synthesized WAVs.
- UI text is in Russian.

## Architecture
- `scenes/main.tscn` — the arena level, player, `WaveManager`, HUD. `scripts/main.gd` owns game
  state (menu / playing / paused / game over), score and the saved best score.
- Level geometry uses `scenes/level/block.tscn` (`Block`: box mesh + matching collision, set `size`).
  It sits under `NavigationRegion3D`, which bakes the navmesh from static colliders at startup.
- `Player` (CharacterBody3D) → `Weapon` (hitscan, ammo, reload, spread, recoil via `fired` signal).
- `Enemy` (one script, three scenes: grunt / rusher / brute) uses NavigationAgent3D to chase,
  ranged ones fire `Projectile`s and strafe. `WaveManager` spawns them at `SpawnPoints` markers.
- `Effects` has static helpers to spawn one-shot effects and bullet tracers.

## Physics layers
1 world · 2 player · 3 enemies · 4 enemy projectiles · 5 pickups.
Hitscan uses mask `1 | 4`; enemy line of sight uses `1 | 2`.

## Checking changes
Run from this folder (`godot` = Godot 4.7 binary):

    godot --headless --path . --import          # reports parse / script errors
    godot --headless --path . --quit-after 300  # runs the main scene (start screen)
