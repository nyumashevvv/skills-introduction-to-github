# Dead City — Godot 4.7 story FPS

Linear zombie shooter in six chapters (outskirts, station, mall, hospital, subway, stadium). GDScript only, Forward+ renderer. UI and story text are Russian.

## Conventions
- Static typing everywhere, tabs for indentation; match the comment density of existing scripts.
- Scenes in `scenes/<area>/`, scripts in `scripts/<area>/`.
- Characters and first-person weapons are glTF files in `models/`, built by `tools/blender/build_assets.py`
  (Blender 4.5, headless) from CC0 packs fetched by `tools/fetch_assets.sh`; see CREDITS.md.
  Vehicles (`models/vehicles`, scenes in `scenes/world/vehicles/`) and furniture/street/camp props (`models/props`)
  are Kenney CC0 kits run through Blender (part `kenney`: scale, proportions, grime/burnt textures; sizes in
  `models/kenney_sizes.json` feed the collision boxes in `tools/gen_props.py`); the bus is modelled there too.
  Level geometry and the other props are Box/Cylinder meshes; `materials/`, `textures/` and most of `sounds/` are
  procedurally generated. Zombie voices in `sounds/zombie/` and the gunshots are processed CC0 recordings (`tools/fetch_assets.sh`).
- Calling methods on nodes found by NodePath: use `node.call("activate")` (untyped), not direct calls.

## Architecture
- `Game` autoload (`scripts/autoload/game.gd`): chapter list, checkpoint (player state at chapter start),
  save file, kill counter, difficulty (`Game.tuning("health"|"speed"|"damage"|"ammo")`, applied in `Zombie._ready`,
  `Player.take_damage`, `Pickup`). `new_game(difficulty)` plays `intro_cutscene.tscn` first.
  `Game.complete_level(state)` moves on; the last chapter leads to `ending_cutscene.tscn`, then `ending.tscn`.
- `scripts/ui/cutscene.gd` plays both the intro (`intro_cutscene.tscn`, world `backdrop_world.tscn`) and the ending
  (`ending_cutscene.tscn`, world `ending_world.tscn`: the stadium at dawn, `ending_heli.gd` flies the route and carries
  the airborne camera marks); `finish_call` names the Game method run at the end. Text: `CUTSCENE` / `ENDING` in
  `tools/story_text.py`. The last chapter → ending cutscene → `ending.tscn` (stats).
- Main menu plays `music/menu_tension.ogg` (looped). Menu and intro cutscene share `scenes/ui/backdrop_world.tscn` (street + basement set, camera marks `<Shot>A/B`);
  cutscene text lives in `tools/story_text.py`. Radio lines and the intro are voiced by `tools/gen_voice.py` (Piper,
  CC0 / public-domain English voices; the spoken English for each Russian subtitle is in `tools/voice_en.py`)
  into `sounds/voice/<md5(russian text)[:12]>.ogg`; `Hud.voice_line(text)` finds them.
- `Settings` autoload (`scripts/autoload/settings.gd`): volumes on the Master / Music / Voice buses
  (`default_bus_layout.tres`), quality (MSAA, FXAA, shadows, SSAO, glow), window mode, vsync, 3D scale, brightness
  (tonemap exposure), FOV of the player's camera, mouse sensitivity; applied to nodes as they enter the tree.
  UI: `scenes/ui/settings_panel.tscn` (rows built in `settings_panel.gd`) in the main menu and the pause menu.
- Level surfaces use ambientCG CC0 PBR sets in `textures/pbr/` (`material(..., pbr=id)` in `tools/tscn.py`,
  world triplanar, normal + roughness maps; imports are VRAM-compressed with mipmaps, normal maps flagged).
- Knife: `Zombie.can_be_stealth_killed` (unaware or struck in the back) → `stealth_kill` (silent, no alert);
  otherwise `melee_hit` (stagger + knock back). Bosses take `Boss.BACKSTAB_DAMAGE` instead.
- `Level` (`scripts/story/level.gd`) is the root of every chapter: intro card, pause/death/completion,
  wires `Player` signals to `Hud`. Expected children: `Player`, `HUD`, `NavigationRegion3D` (baked at runtime
  from static colliders), plus `Decor`, `Lights`, `Doors`, `Zombies`, `Pickups`, `Story`.
- Story is data-driven: `StoryEvent` (objective + radio message + `targets` with `activate()`),
  `StoryTrigger` (Area3D), `ZombieSpawner`, `Holdout`, `Door` (`swing_degrees`: hinged, swings away from the player,
  else slides by `open_offset`; `event_unlocks`: an event unlocks instead of opening), `Pickup.event`. Anything with `activate()`
  can be a target (doors, spawners, zombies, flicker lights, `power_light` (dark until powered),
  `sound_trigger`, other events, helicopter).
- Player: stamina (sprint and jump spend it, `stamina_changed` → HUD strip), crouch ("crouch" action, C / Ctrl: shorter
  capsule, stays down under low ceilings). `Player` → `Head/Camera3D/WeaponHolder` → weapons. `Weapon` base (ammo, reload, equip/idle anim,
  `fire_ray` with distance falloff) with `Gun` (pistol, rifle, pump shotgun: `pellets`, `pump_delay`,
  `reload_per_round`), `MeleeWeapon` (knife), `Launcher` (RPG-7, id "bazooka" → `Rocket`), `Thrower` (grenades → `Grenade` RigidBody).
  Slots 1–9: knife, pistol, revolver, shotgun, smg, rifle, sniper (`Gun.scope_fov`, "aim" action, HUD scope overlay),
  bazooka, grenade. SMG, AK, revolver and pump shotgun are modelled in `build_assets.py` (`GunKit`), pistol/sniper come from the FPS Pack.
  `Thrower` swings the arm around `SHOULDER` (overarm, grenade released at `RELEASE_AT`). Heavy recoil also punches
  the view (`Player._punch`, springs back) and shakes it. Cars collide as two boxes (body + cabin, `CARS` in
  `gen_props.py`) so shots over a bonnet go through. The helicopter is modelled in Blender (part `heli`).
- `Zombie` (one script, scenes walker / runner / brute / soldier (`body_armor`) / bloater (`explode_damage`,
  bursts on death or on reaching the player); the spitter is a `Boss` with `show_health_bar = false`): IDLE → CHASE → ATTACK (only with a clear line to the player: `_can_reach_player`, so no hits through shut doors), hears weapon noise
  (`hear_noise` via the "zombies" group). Picks a random body from `bodies` (models/characters/*.glb, faces redrawn by `scary_face` in `build_assets.py`,
  Quaternius rig: Idle/Walk/Run/Punch/RecieveHit/Death) and tints its "Skin" material. `ZombiePose`
  (SkeletonModifier3D) layers arms-forward reaching and headshot head removal over the animation.
  Headshot = hit above the Neck bone. Groans are rate-limited globally (`GROAN_GAP`).
- `Boss` (`scripts/zombies/boss.gd`, extends `Zombie`; scenes butcher / warden / mascot (Заяц Гоша, the mall) /
  patient_zero / lineman / colossus): HUD health bar, abilities switched on by exports (charge, `BossProjectile` throw, ground slam,
  summon, `front_armor` shield, enrage) run in `State.SPECIAL` via the `_try_special` / `_process_special` /
  `_damage_scale` hooks in `Zombie`. Bosses ignore noise (`wakes_from_noise = false`). Placed bosses fire
  `alert_event` / `death_event`; spawned ones (subway, stadium) are tracked by `Holdout.boss_spawner`, which
  keeps the exit shut until they die. Boss models are `models/characters/boss_*.glb` (props parented to bones). Easter eggs:
  the Warden is "Боболев" (`fatten`, beanie, face style 'bobolev'), the Colossus is "Алёна" (long hair, earrings,
  face style 'alena'); `scary_face(style=...)` in `build_assets.py`.
  `Boss.music` (CC0 loops in `music/`) plays through `Level.play_music` / `stop_music` during the fight.
  Bosses take `bullet_multiplier` (0.6) from bullets and `explosive_multiplier` (2.0) from blasts;
  `Effects.apply_blast` measures distance to the nearest point of a zombie's capsule.
- Weapon scenes instance `models/weapons/<name>_fp.glb` as `Model` (gun + posed arms in camera space,
  plus a `Muzzle` marker); `Weapon._ready` moves their meshes to render layer 2 (viewmodel layer).
  Pose offsets/rotations (equip, kick, reload tilt) turn around `Weapon.pivot` (the grip, set by `Gun`), never
  around the camera, so the arms stay out of the screen. The rifle is an AK modelled in `build_assets.py`.
- HUD (`scenes/ui/hud.tscn`, generated): panels with an accent edge, Russo One numbers / Oswald text (`fonts/`,
  OFL; Oswald is the theme default), `SegmentBar` (health, boss) and `AmmoPips` (rounds in the magazine).
- `Effects` static helpers: spawn one-shot effects, tracers, `apply_blast` for explosions.

## Physics layers
1 world (also closed doors) · 2 player · 3 zombies · 4 open doors (player only) · 5 pickups. Bullets use mask `1 | 4`; zombie sight `1 | 2`.

## Generators and tests
- `tools/gen_assets.py`, `tools/gen_props.py` (clutter props in `scenes/props/`; solid ones are StaticBody3D and
  `LevelBuilder.clutter` puts them under the navigation region), `tools/gen_levels.py` (run from the project root with `PYTHONPATH=tools`)
  regenerate scenes and overwrite editor changes — only use them if the scenes were not hand-edited.
- Input map: `godot --headless --path . --script tools/setup_input.gd`.
- `LevelBuilder.shell` hollows a building's ground floor (walls with door gaps, ceiling, solid storeys above);
  `fancy_door` / `dress_door` give doors the station-entrance look (frame, window, handles, lamp, sign).
  Signs are Blender models (part `signs` in `build_assets.py`: `SignKit` draws 3D letters in the project fonts, light
  boxes, parody logos and two sets of bulbs `BulbsA` / `BulbsB` into `models/signs/`; `gen_props.signs()` wraps them in
  `scenes/world/signs/` with `sign_bulbs.gd`, which lights the sets in turn). `LevelBuilder.sign` hangs one on a wall
  (optionally with its light), `blade_sign` sticks a double-sided one out of a facade. Shop names are parodies
  ("Двоечка", "Ы.Видео", "Мозгоед"…); the mall maps shop → sign in `SHOP_SIGNS`.
- The mall (`level_mall`, `level_3_mall.tscn`) is multi-storey: floors at y 0/5/10, roof 15; `slab` cuts floors into 8 m
  tiles (fewer lights per mesh), `ramp` makes walkable escalators/stairs, `railing` closes the atrium edges, `front`
  builds a shop front (door, windows, the shop's sign, a power lamp inside). `limits/opengl/max_lights_per_object` is 32.
  Power comes from the generator room (ground floor, east wing, `Doors/PowerSwitch` → `PowerOn`), which lights the
  `power_light`s and raises the shutter to the third floor. Shop furniture and the atrium fountain are Blender models
  (part `mall` in `build_assets.py`: `build_mall_props` — carts, mannequins, racks, shelves, arcade cabinets, food
  stalls; `build_mall_furniture` — bistro sets, food-court tables, booths, sofas, kiosks, vending machines, ATMs, display
  cases, item walls, ball pit, cinema seats…). Shop fronts have real glass (`clear_glass`; the old `glass` material is
  opaque). Kenney / world props face -Z, the Blender mall props face +Z. GPU budget: some drivers run out of buffers
  (VkResult -10) when a chapter has too many meshes / surfaces / materials, so `Kit.export` and `SignKit.export` run
  `palettize` (all flat colours in one palette image, faces' UVs on their swatch, one material per kind: matte,
  metal, see-through, glowing by strength) and `Block` shares meshes and shapes between equal blocks. Keep new props
  flat-coloured through `Kit` and reuse props instead of making one-off variants. Screenshot section `mall_tour` shows every shop.
  The casino "Последняя ставка" (ground floor, north-east) is playable: `CasinoMachine` (StaticBody3D, kind slots /
  roulette / cashier; set on the props in `CASINO` in `gen_props.py`) opens a `CasinoPanel` through `Level.open_panel`
  (state `PANEL`, game paused, Esc closes). `SlotPanel` (weighted reels, `payout`), `RoulettePanel` (European wheel,
  `multiplier`, `RouletteWheel` draws it and lands the ball in the result), `CashierPanel` (welcome gift, prizes).
  Chips live in `Game.chips` (saved). Models: `build_casino` in `build_assets.py`; sounds `casino_*` in `gen_sounds.py`.
  Life in the mall: `tools/gen_mall_art.py` (Pillow) draws posters, ad screens (`materials/mall/ad_screen.gdshader`:
  scanlines, tearing, flicker), banners, graffiti, blood and tape into `textures/mall/` + `materials/mall/`;
  `LevelBuilder.quad` hangs them, `motion` wraps props in `idle_motion.gd` (sway / bob / spin: banners, balloons,
  fans, the car's turntable), `ambient` places `ambient_sound.gd` players (fountain, muzak on the Music bus, the PA
  announcement `sounds/mall_pa.ogg` from `gen_voice.py` with the ru_RU voice, sparks). Effects `dust_motes` and
  `sparks_loop` come from `gen_props.ambient_effects()`. The survivors' corner is in the guards' room (1st floor). The roof exit is a
  bridge over the west alley and a ramp down to the gate (`ExitTrigger`); the alleys round the building are walled in.
- `tools/gen_levels.py`: chapter scenes are `Level` roots — keep `script` the first property of a node or Godot drops
  the script's exported values. After changing radio text, update `tools/voice_en.py` and rerun `tools/gen_voice.py`.
- Tests (must pass before committing):

      godot --headless --path . --import
      godot --headless --path . res://tests/test_story.tscn
      godot --headless --path . res://tests/test_combat.tscn
      godot --headless --path . res://tests/test_holes.tscn   # no spot to fall out of any map
      godot --headless --path . res://tests/test_casino.tscn  # casino rules, odds, every game played in the mall
