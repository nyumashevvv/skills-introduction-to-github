# Dead City — Godot 4.7 story FPS

Linear zombie shooter in five chapters (outskirts, station, hospital, subway, stadium). GDScript only, Forward+ renderer. UI and story text are Russian.

## Conventions
- Static typing everywhere, tabs for indentation; match the comment density of existing scripts.
- Scenes in `scenes/<area>/`, scripts in `scripts/<area>/`.
- Characters and first-person weapons are glTF files in `models/`, built by `tools/blender/build_assets.py`
  (Blender 4.5, headless) from CC0 packs fetched by `tools/fetch_assets.sh`; see CREDITS.md.
  Level geometry and props are Box/Cylinder meshes; `materials/`, `textures/` and most of `sounds/` are
  procedurally generated. Zombie voices in `sounds/zombie/` are processed CC0 recordings.
- Calling methods on nodes found by NodePath: use `node.call("activate")` (untyped), not direct calls.

## Architecture
- `Game` autoload (`scripts/autoload/game.gd`): chapter list, checkpoint (player state at chapter start),
  save file, kill counter. `Game.complete_level(state)` moves on; the last chapter leads to `ending.tscn`.
- `Level` (`scripts/story/level.gd`) is the root of every chapter: intro card, pause/death/completion,
  wires `Player` signals to `Hud`. Expected children: `Player`, `HUD`, `NavigationRegion3D` (baked at runtime
  from static colliders), plus `Decor`, `Lights`, `Doors`, `Zombies`, `Pickups`, `Story`.
- Story is data-driven: `StoryEvent` (objective + radio message + `targets` with `activate()`),
  `StoryTrigger` (Area3D), `ZombieSpawner`, `Holdout`, `Door` (`event_unlocks`: an event unlocks instead of
  opening), `Pickup.event`. Anything with `activate()`
  can be a target (doors, spawners, zombies, flicker lights, `power_light` (dark until powered),
  `sound_trigger`, other events, helicopter).
- Player: `Player` → `Head/Camera3D/WeaponHolder` → weapons. `Weapon` base (ammo, reload, equip/idle anim,
  `fire_ray` with distance falloff) with `Gun` (pistol, rifle, pump shotgun: `pellets`, `pump_delay`,
  `reload_per_round`), `MeleeWeapon` (knife), `Launcher` (RPG-7, id "bazooka" → `Rocket`). Slots 1–5.
- `Zombie` (one script, scenes walker / runner / brute): IDLE → CHASE → ATTACK, hears weapon noise
  (`hear_noise` via the "zombies" group). Picks a random body from `bodies` (models/characters/*.glb,
  Quaternius rig: Idle/Walk/Run/Punch/RecieveHit/Death) and tints its "Skin" material. `ZombiePose`
  (SkeletonModifier3D) layers arms-forward reaching and headshot head removal over the animation.
  Headshot = hit above the Neck bone. Groans are rate-limited globally (`GROAN_GAP`).
- `Boss` (`scripts/zombies/boss.gd`, extends `Zombie`; scenes butcher / warden / patient_zero / lineman /
  colossus): HUD health bar, abilities switched on by exports (charge, `BossProjectile` throw, ground slam,
  summon, `front_armor` shield, enrage) run in `State.SPECIAL` via the `_try_special` / `_process_special` /
  `_damage_scale` hooks in `Zombie`. Bosses ignore noise (`wakes_from_noise = false`). Placed bosses fire
  `alert_event` / `death_event`; spawned ones (subway, stadium) are tracked by `Holdout.boss_spawner`, which
  keeps the exit shut until they die. Boss models are `models/characters/boss_*.glb` (props parented to bones).
- Weapon scenes instance `models/weapons/<name>_fp.glb` as `Model` (gun + posed arms in camera space,
  plus a `Muzzle` marker); `Weapon._ready` moves their meshes to render layer 2 (viewmodel layer).
- `Effects` static helpers: spawn one-shot effects, tracers, `apply_blast` for explosions.

## Physics layers
1 world (also doors) · 2 player · 3 zombies · 5 pickups. Bullets use mask `1 | 4`; zombie sight `1 | 2`.

## Generators and tests
- `tools/gen_assets.py`, `tools/gen_levels.py` (run from the project root with `PYTHONPATH=tools`)
  regenerate scenes and overwrite editor changes — only use them if the scenes were not hand-edited.
- Input map: `godot --headless --path . --script tools/setup_input.gd`.
- Tests (must pass before committing):

      godot --headless --path . --import
      godot --headless --path . res://tests/test_story.tscn
      godot --headless --path . res://tests/test_combat.tscn
