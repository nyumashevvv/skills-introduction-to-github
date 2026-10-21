"""Generates materials and every non-level scene of Dead City. Run from the project root."""
import math
import zlib, struct
from tscn import *

# ------------------------------------------------------------------ materials
def mats():
    T = 'materials/'
    # textured (world-space triplanar)
    material(T + 'asphalt.tres', (1, 1, 1), roughness=0.95, texture='asphalt', uv_scale=0.25)
    material(T + 'sidewalk.tres', (0.95, 0.93, 0.9), roughness=0.9, texture='concrete', uv_scale=0.35)
    material(T + 'concrete.tres', (0.75, 0.75, 0.75), roughness=0.9, texture='concrete', uv_scale=0.3)
    material(T + 'brick.tres', (1, 1, 1), roughness=0.9, texture='brick', uv_scale=0.4)
    material(T + 'brick_dark.tres', (0.6, 0.55, 0.55), roughness=0.9, texture='brick', uv_scale=0.4)
    material(T + 'plaster.tres', (0.78, 0.7, 0.58), roughness=0.95, texture='concrete', uv_scale=0.25)
    material(T + 'plaster_gray.tres', (0.45, 0.47, 0.5), roughness=0.95, texture='concrete', uv_scale=0.25)
    material(T + 'wall_interior.tres', (0.62, 0.66, 0.6), roughness=0.9, texture='concrete', uv_scale=0.4)
    material(T + 'tile.tres', (0.85, 0.85, 0.82), roughness=0.5, texture='tile', uv_scale=0.5)
    material(T + 'wood.tres', (1, 1, 1), roughness=0.8, texture='wood', uv_scale=0.6)
    material(T + 'crate.tres', (0.8, 0.65, 0.45), roughness=0.85, texture='wood', uv_scale=0.8)
    material(T + 'metal.tres', (0.55, 0.57, 0.6), metallic=0.6, roughness=0.5, texture='metal', uv_scale=0.4)
    material(T + 'metal_rust.tres', (0.5, 0.33, 0.22), metallic=0.3, roughness=0.8, texture='metal', uv_scale=0.4)
    material(T + 'grass.tres', (1, 1, 1), roughness=1.0, texture='grass', uv_scale=0.12)
    material(T + 'stands.tres', (0.45, 0.47, 0.52), roughness=0.9, texture='concrete', uv_scale=0.3)
    material(T + 'sandbag.tres', (0.62, 0.54, 0.4), roughness=1.0, texture='concrete', uv_scale=1.2)
    # plain
    for name, col in [('car_red', (0.45, 0.06, 0.05)), ('car_blue', (0.08, 0.15, 0.35)), ('car_white', (0.75, 0.75, 0.72)),
                      ('car_black', (0.04, 0.04, 0.05)), ('car_green', (0.12, 0.25, 0.15)), ('bus_yellow', (0.75, 0.55, 0.08))]:
        material(T + name + '.tres', col, metallic=0.5, roughness=0.35)
    material(T + 'glass.tres', (0.05, 0.07, 0.09), metallic=0.8, roughness=0.08)
    material(T + 'tire.tres', (0.03, 0.03, 0.03), roughness=0.9)
    material(T + 'chrome.tres', (0.7, 0.7, 0.72), metallic=0.6, roughness=0.25)
    material(T + 'dark.tres', (0.06, 0.06, 0.07), roughness=0.8)
    material(T + 'lamp_glow.tres', (0, 0, 0), emission=(1.0, 0.78, 0.45), energy=6.0)
    material(T + 'headlight.tres', (0, 0, 0), emission=(1.0, 0.95, 0.8), energy=4.0)
    material(T + 'taillight.tres', (0.2, 0, 0), emission=(1.0, 0.05, 0.02), energy=3.0)
    material(T + 'siren_red.tres', (0.2, 0, 0), emission=(1.0, 0.05, 0.05), energy=5.0)
    material(T + 'siren_blue.tres', (0, 0, 0.2), emission=(0.1, 0.25, 1.0), energy=5.0)
    material(T + 'window_lit.tres', (0, 0, 0), emission=(0.95, 0.65, 0.35), energy=0.9)
    material(T + 'window_dark.tres', (0.04, 0.05, 0.07), metallic=0.6, roughness=0.15)
    material(T + 'flood_glow.tres', (0, 0, 0), emission=(0.9, 0.95, 1.0), energy=10.0)
    material(T + 'paint_white.tres', (0.85, 0.85, 0.8), roughness=0.7)
    material(T + 'paint_yellow.tres', (0.9, 0.7, 0.1), roughness=0.7, emission=(0.9, 0.7, 0.1), energy=0.3)
    material(T + 'police_blue.tres', (0.05, 0.1, 0.3), metallic=0.4, roughness=0.4)
    material(T + 'military.tres', (0.22, 0.26, 0.17), roughness=0.85)
    material(T + 'tent.tres', (0.3, 0.33, 0.22), roughness=1.0)
    material(T + 'fire_glow.tres', (0, 0, 0), emission=(1.0, 0.45, 0.1), energy=4.0)
    # weapons & hands
    material(T + 'gun_black.tres', (0.05, 0.05, 0.055), metallic=0.3, roughness=0.55)
    material(T + 'gun_steel.tres', (0.26, 0.27, 0.29), metallic=0.5, roughness=0.38)
    material(T + 'gun_wood.tres', (0.38, 0.18, 0.07), roughness=0.55)
    material(T + 'bakelite.tres', (0.3, 0.1, 0.04), roughness=0.4)
    material(T + 'olive.tres', (0.22, 0.26, 0.14), metallic=0.2, roughness=0.6)
    material(T + 'blade.tres', (0.8, 0.82, 0.85), metallic=0.45, roughness=0.25)
    material(T + 'glove.tres', (0.07, 0.07, 0.07), roughness=0.85)
    material(T + 'sleeve.tres', (0.16, 0.18, 0.12), roughness=0.95)
    material(T + 'brass.tres', (0.7, 0.5, 0.2), metallic=0.9, roughness=0.3)
    material(T + 'rocket_red.tres', (0.45, 0.08, 0.05), metallic=0.3, roughness=0.5)
    # zombies
    material(T + 'z_skin.tres', (0.42, 0.5, 0.4), roughness=0.75)
    material(T + 'z_skin_dark.tres', (0.3, 0.34, 0.28), roughness=0.8)
    material(T + 'z_skin_pale.tres', (0.6, 0.6, 0.55), roughness=0.75)
    material(T + 'z_pants.tres', (0.14, 0.17, 0.26), roughness=0.95)
    material(T + 'z_pants_brown.tres', (0.25, 0.18, 0.12), roughness=0.95)
    material(T + 'z_shirt.tres', (0.5, 0.5, 0.5), roughness=0.95)
    material(T + 'z_shoes.tres', (0.06, 0.05, 0.05), roughness=0.8)
    material(T + 'z_hair.tres', (0.08, 0.06, 0.05), roughness=1.0)
    material(T + 'z_blood.tres', (0.28, 0.01, 0.01), roughness=0.3)
    material(T + 'z_eyes.tres', (0, 0, 0), emission=(1.0, 0.9, 0.5), energy=2.5)
    material(T + 'z_eyes_red.tres', (0, 0, 0), emission=(1.0, 0.1, 0.05), energy=4.0)
    material(T + 'z_teeth.tres', (0.65, 0.6, 0.45), roughness=0.5)
    # pickups / misc
    material(T + 'medkit_white.tres', (0.9, 0.92, 0.95), roughness=0.5)
    material(T + 'medkit_red.tres', (0.3, 0, 0), emission=(1.0, 0.1, 0.1), energy=2.0)
    material(T + 'ammo_green.tres', (0.25, 0.3, 0.18), roughness=0.6)
    material(T + 'keycard.tres', (0.1, 0.2, 0.5), emission=(0.2, 0.5, 1.0), energy=2.5)
    material(T + 'hit_flash.tres', (1, 0.85, 0.85, 0.6), roughness=1.0, extra={'transparency': 1, 'shading_mode': 0})
    material(T + 'muzzle_flash.tres', (1, 0.75, 0.35), extra={'transparency': 1, 'blend_mode': 1, 'shading_mode': 0,
                                                              'cull_mode': 2})
    # bars for prison cells (alpha scissor texture)
    W = 64
    rows = []
    for y in range(W):
        row = bytearray([0])
        for x in range(W):
            bar = x % 16 < 3 or y % 64 < 3
            row += bytes([60, 62, 66, 255 if bar else 0])
        rows.append(bytes(row))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open('textures/bars.png', 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, W, 8, 6, 0, 0, 0))
                                         + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))
    material(T + 'bars.tres', (1, 1, 1), metallic=0.7, roughness=0.4, texture='bars', uv_scale=0.6,
             extra={'transparency': 2, 'alpha_scissor_threshold': 0.5, 'cull_mode': 2})


# ------------------------------------------------------------------ weapons
def weapon_root(s, script, props):
    s.node(props.pop('node_name'), 'Node3D', script=s.ext_res('Script', f'res://scripts/weapons/{script}.gd'), **props)


def rocket_parts(s, p, z=0.0):
    s.cyl('Warhead', p, 0.05, 0.14, (0, 0, z), 'rocket_red', rot=(RX, 0, 0), cast_shadow=0)
    s.cyl('Tip', p, 0.05, 0.12, (0, 0, z - 0.13), 'rocket_red', rot=(-RX, 0, 0), top=0.0, cast_shadow=0)


def flash_node(s, parent, size=0.18, light=4.0):
    """Muzzle flash; the Gun script moves it onto the model's Muzzle marker."""
    s.node('Flash', 'Node3D', parent)
    quad = s.sub_res('QuadMesh', material=s.mat('muzzle_flash'), size=V2(size, size))
    s.node('Quad', 'MeshInstance3D', parent + '/Flash', mesh=quad, cast_shadow=0, layers=2)
    s.node('Quad2', 'MeshInstance3D', parent + '/Flash', mesh=quad, cast_shadow=0, layers=2, rotation=V3(0, 0, 0.7854))
    side = s.sub_res('QuadMesh', material=s.mat('muzzle_flash'), size=V2(size * 0.6, size * 1.6))
    s.node('Side', 'MeshInstance3D', parent + '/Flash', mesh=side, cast_shadow=0, layers=2, rotation=V3(RX, 0, 0),
           position=V3(0, 0, -size * 0.5))
    s.node('Light', 'OmniLight3D', parent + '/Flash', light_color=C(1, 0.7, 0.35), light_energy=light, omni_range=7.0)


def viewmodel(s, name):
    s.node('Model', None, '.', instance=s.ext_res('PackedScene', f'res://models/weapons/{name}_fp.glb'))


def weapons():
    # Pistol
    s = Scene()
    weapon_root(s, 'gun', dict(node_name='Pistol', id=S('pistol'), display_name=S('Пистолет'), slot=2,
                ammo_type=S('pistol'), magazine_size=12, max_reserve=96, reload_time=1.3, noise_radius=28.0,
                damage=34, headshot_multiplier=3.0, fire_rate=6.0, base_spread_deg=0.25, move_spread_deg=1.8,
                heat_spread_deg=0.8, recoil=0.018, kick_back=0.05, kick_up=0.12))
    viewmodel(s, 'pistol')
    flash_node(s, 'Model', 0.13, 3.0)
    for name, snd, vol in [('ShootSound', 'pistol', -5.0), ('ReloadSound', 'reload_pistol', -4.0), ('EmptySound', 'empty', -4.0)]:
        s.node(name, 'AudioStreamPlayer', '.', stream=s.sound(snd), volume_db=vol, max_polyphony=3)
    s.save('scenes/weapons/pistol.tscn')

    # Rifle
    s = Scene()
    weapon_root(s, 'gun', dict(node_name='Rifle', id=S('rifle'), display_name=S('Автомат'), slot=3,
                ammo_type=S('rifle'), magazine_size=30, max_reserve=210, reload_time=2.0, noise_radius=40.0,
                automatic=True, damage=26, headshot_multiplier=2.5, fire_rate=10.0, base_spread_deg=0.35,
                move_spread_deg=3.0, heat_spread_deg=1.6, recoil=0.009, kick_back=0.03, kick_up=0.03))
    viewmodel(s, 'rifle')
    flash_node(s, 'Model', 0.2, 4.0)
    for name, snd, vol in [('ShootSound', 'rifle', -6.0), ('ReloadSound', 'reload_rifle', -4.0), ('EmptySound', 'empty', -4.0)]:
        s.node(name, 'AudioStreamPlayer', '.', stream=s.sound(snd), volume_db=vol, max_polyphony=6)
    s.save('scenes/weapons/rifle.tscn')

    # RPG-7 (slot "bazooka")
    s = Scene()
    weapon_root(s, 'launcher', dict(node_name='Bazooka', id=S('bazooka'), display_name=S('РПГ-7'), slot=4,
                ammo_type=S('rocket'), magazine_size=1, max_reserve=8, reload_time=2.3, noise_radius=60.0,
                equip_time=0.6, rocket_scene=s.ext_res('PackedScene', 'res://scenes/weapons/rocket.tscn')))
    viewmodel(s, 'rpg')
    for name, snd, vol in [('ShootSound', 'rocket_launch', -2.0), ('ReloadSound', 'reload_rocket', -3.0), ('EmptySound', 'empty', -4.0)]:
        s.node(name, 'AudioStreamPlayer', '.', stream=s.sound(snd), volume_db=vol)
    s.save('scenes/weapons/bazooka.tscn')

    # Knife (modelled in Blender by tools/blender/build_assets.py)
    s = Scene()
    weapon_root(s, 'melee_weapon', dict(node_name='Knife', id=S('knife'), display_name=S('Нож'), slot=1,
                equip_time=0.2))
    viewmodel(s, 'knife')
    s.node('SwingSound', 'AudioStreamPlayer', '.', stream=s.sound('knife_swing'), volume_db=-4.0, max_polyphony=2)
    s.node('StabSound', 'AudioStreamPlayer', '.', stream=s.sound('knife_hit'), volume_db=-2.0)
    s.save('scenes/weapons/knife.tscn')

    # Rocket projectile
    s = Scene()
    s.node('Rocket', 'Node3D', script=s.ext_res('Script', 'res://scripts/weapons/rocket.gd'))
    s.node('Model', None, '.', instance=s.ext_res('PackedScene', 'res://models/weapons/rocket.glb'))
    smoke_mat = s.sub_res('StandardMaterial3D', transparency=1, shading_mode=0, vertex_color_use_as_albedo=True,
                          billboard_mode=3)
    smoke_mesh = s.sub_res('QuadMesh', material=smoke_mat, size=V2(0.4, 0.4))
    ramp = s.sub_res('Gradient', offsets='PackedFloat32Array(0, 0.15, 1)',
                     colors='PackedColorArray(3, 2, 0.8, 1, 0.6, 0.6, 0.6, 0.6, 0.4, 0.4, 0.4, 0)')
    grow = s.sub_res('Curve', _data='[Vector2(0, 0.3), 0.0, 0.0, 0, 0, Vector2(1, 1.5), 0.0, 0.0, 0, 0]', point_count=2)
    s.node('Smoke', 'CPUParticles3D', '.', position=V3(0, 0, 0.5), amount=60, lifetime=1.2, local_coords=False,
           mesh=smoke_mesh, direction=V3(0, 0, 1), spread=10.0, initial_velocity_min=1.0, initial_velocity_max=2.0,
           gravity=V3(0, 0.6, 0), scale_amount_curve=grow, color_ramp=ramp)
    s.node('Light', 'OmniLight3D', '.', position=V3(0, 0, 0.55), light_color=C(1, 0.6, 0.25), light_energy=3.0, omni_range=5.0)
    s.save('scenes/weapons/rocket.tscn')


# ------------------------------------------------------------------ player
def player():
    s = Scene()
    shape = s.sub_res('CapsuleShape3D', radius=0.4, height=1.8)
    s.node('Player', 'CharacterBody3D', groups=['player'], collision_layer=2, collision_mask=5,
           script=s.ext_res('Script', 'res://scripts/player/player.gd'))
    s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, 0.9, 0), shape=shape)
    s.node('Head', 'Node3D', '.', position=V3(0, 1.6, 0))
    s.node('Camera3D', 'Camera3D', 'Head', fov=78.0, near=0.02, current=True)
    s.node('Flashlight', 'SpotLight3D', 'Head/Camera3D', position=V3(-0.15, 0.05, 0), light_color=C(1, 0.95, 0.85),
           light_energy=3.0, spot_range=28.0, spot_angle=26.0, spot_attenuation=0.8, shadow_enabled=True,
           light_cull_mask=1048573)
    s.node('ViewmodelLight', 'OmniLight3D', 'Head/Camera3D', position=V3(-0.1, 0.25, 0.1), light_color=C(0.85, 0.85, 1),
           light_energy=0.7, omni_range=2.0, light_cull_mask=2)
    s.node('WeaponHolder', 'Node3D', 'Head/Camera3D', script=s.ext_res('Script', 'res://scripts/player/weapon_holder.gd'))
    for name in ('knife', 'pistol', 'rifle', 'bazooka'):
        s.node(name.capitalize(), None, 'Head/Camera3D/WeaponHolder',
               instance=s.ext_res('PackedScene', f'res://scenes/weapons/{name}.tscn'))
    s.node('SwitchSound', 'AudioStreamPlayer', 'Head/Camera3D/WeaponHolder', stream=s.sound('weapon_switch'), volume_db=-6.0)
    s.node('HitSound', 'AudioStreamPlayer', 'Head/Camera3D/WeaponHolder', stream=s.sound('flesh_hit'), volume_db=-6.0, max_polyphony=4)
    for name, snd, vol in [('HurtSound', 'hurt', -2.0), ('PickupSound', 'pickup', -4.0), ('KeySound', 'key_pickup', -4.0),
                           ('FootstepSound', 'footstep', -10.0), ('FlashlightSound', 'flashlight', -6.0)]:
        s.node(name, 'AudioStreamPlayer', '.', stream=s.sound(snd), volume_db=vol, max_polyphony=2)
    s.save('scenes/player/player.tscn')


# ------------------------------------------------------------------ zombies
def zombie(path, root_name, stats, bodies, radius=0.35, height=1.8, body_scale=0.58, skin=True):
    s = Scene()
    shape = s.sub_res('CapsuleShape3D', radius=radius, height=height)
    props = dict(collision_layer=4, collision_mask=7, script=s.ext_res('Script', 'res://scripts/zombies/zombie.gd'))
    props.update(stats)
    props['bodies'] = 'Array[PackedScene]([' + ', '.join(
        s.ext_res('PackedScene', f'res://models/characters/{b}.glb') for b in bodies) + '])'
    props['body_scale'] = body_scale
    if skin:
        props['skin_colors'] = 'Array[Color]([' + ', '.join(C(*c) for c in ZOMBIE_SKINS) + '])'
    s.node(root_name, 'CharacterBody3D', groups=['zombies'], **props)
    s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, height / 2, 0), shape=shape)
    # The character models face +Z; turn them to Godot's forward (-Z).
    s.node('Model', 'Node3D', '.', rotation=V3(0, math.pi, 0))
    s.node('NavigationAgent3D', 'NavigationAgent3D', '.', path_desired_distance=0.8, target_desired_distance=0.8,
           height=height, radius=radius)
    for name, snd, vol in [('GroanSound', 'zombie/groan1', -8.0), ('AttackSound', 'zombie/attack1', -3.0),
                           ('DeathSound', 'zombie/death1', -4.0)]:
        s.node(name, 'AudioStreamPlayer3D', '.', stream=s.ext_res('AudioStream', f'res://sounds/{snd}.ogg'),
               position=V3(0, 1.6 * body_scale / 0.58, 0), volume_db=vol, unit_size=3.0, max_distance=30.0)
    s.save(path)


ZOMBIE_SKINS = [(0.42, 0.5, 0.38), (0.5, 0.55, 0.45), (0.36, 0.42, 0.34), (0.55, 0.52, 0.45), (0.45, 0.47, 0.5)]


def zombies():
    zombie('scenes/zombies/walker.tscn', 'Walker',
           dict(max_health=70, chase_speed=1.9, wander_speed=0.45, attack_damage=14, attack_range=1.5,
                attack_windup=0.55, attack_recovery=0.6, sight_range=18.0),
           ['zombie_male', 'zombie_female', 'worker', 'doctor', 'chef'])
    zombie('scenes/zombies/runner.tscn', 'Runner',
           dict(max_health=45, chase_speed=5.4, wander_speed=0.8, turn_speed=10.0, attack_damage=10,
                attack_range=1.4, attack_windup=0.35, attack_recovery=0.45, sight_range=26.0,
                chase_animation=S('Run'), voice_pitch=1.15),
           ['soldier', 'worker', 'zombie_female'], radius=0.3)
    zombie('scenes/zombies/brute.tscn', 'Brute',
           dict(max_health=1000, chase_speed=2.6, wander_speed=0.4, turn_speed=3.5, attack_damage=34,
                attack_range=2.4, attack_windup=0.8, attack_recovery=0.9, knockback=7.0, sight_range=30.0,
                stagger_resistance=0.92, voice_pitch=0.65),
           ['zombie_male'], radius=0.65, height=2.9, body_scale=0.95)


# ------------------------------------------------------------------ pickups
def pickup(path, root_name, props, build, light=(1, 0.9, 0.6)):
    s = Scene()
    shape = s.sub_res('SphereShape3D', radius=0.8)
    s.node(root_name, 'Area3D', collision_layer=16, collision_mask=2, monitorable=False,
           script=s.ext_res('Script', 'res://scripts/pickups/pickup.gd'), **props)
    s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, 0.5, 0), shape=shape)
    s.node('Visual', 'Node3D', '.')
    s.node('Item', 'Node3D', 'Visual', position=V3(0, 0.5, 0))
    build(s, 'Visual/Item')
    s.node('Light', 'OmniLight3D', '.', position=V3(0, 0.8, 0), light_color=C(*light), light_energy=0.8, omni_range=2.5)
    s.save(path)


def pickups():
    def medkit(s, p):
        s.box('Case', p, (0.5, 0.32, 0.3), (0, 0, 0), 'medkit_white')
        s.box('Handle', p, (0.18, 0.05, 0.05), (0, 0.18, 0), 'dark')
        s.box('CrossH', p, (0.26, 0.08, 0.31), (0, 0, 0), 'medkit_red')
        s.box('CrossV', p, (0.08, 0.24, 0.31), (0, 0, 0), 'medkit_red')
    pickup('scenes/pickups/medkit.tscn', 'Medkit', dict(kind=0, amount=40, display_name=S('Аптечка')), medkit, (1, 0.4, 0.4))

    def ammo_box(s, p, w, color):
        s.box('Box', p, (w, 0.2, 0.22), (0, 0, 0), 'ammo_green')
        s.box('Lid', p, (w + 0.02, 0.04, 0.24), (0, 0.11, 0), 'dark')
        s.box('Label', p, (w * 0.6, 0.08, 0.005), (0, 0, -0.112), color)
    pickup('scenes/pickups/ammo_pistol.tscn', 'AmmoPistol',
           dict(kind=1, amount=24, ammo_type=S('pistol'), display_name=S('Патроны для пистолета')),
           lambda s, p: ammo_box(s, p, 0.26, 'brass'))
    pickup('scenes/pickups/ammo_rifle.tscn', 'AmmoRifle',
           dict(kind=1, amount=60, ammo_type=S('rifle'), display_name=S('Патроны для автомата')),
           lambda s, p: (ammo_box(s, p, 0.4, 'paint_yellow'),
                         s.box('Mag', p, (0.04, 0.16, 0.08), (0.12, 0.2, 0), 'bakelite', rot=(0, 0, 0.3))))
    def rockets(s, p):
        for i, x in enumerate((-0.08, 0.08)):
            s.node(f'R{i}', 'Node3D', p, position=V3(x, 0, 0.1))
            rocket_parts(s, f'{p}/R{i}')
            s.cyl('Body', f'{p}/R{i}', 0.035, 0.3, (0, 0, 0.2), 'olive', rot=(RX, 0, 0))
    pickup('scenes/pickups/ammo_rocket.tscn', 'AmmoRocket',
           dict(kind=1, amount=2, ammo_type=S('rocket'), display_name=S('Ракеты')), rockets, (1, 0.6, 0.3))

    def weapon_visual(name, scale):
        def build(s, p):
            s.node('Model', None, p, instance=s.ext_res('PackedScene', f'res://models/weapons/{name}_world.glb'),
                   scale=V3(scale, scale, scale), rotation=V3(0, RX, 0))
        return build
    pickup('scenes/pickups/weapon_rifle.tscn', 'WeaponRifle',
           dict(kind=2, item_id=S('rifle'), display_name=S('Автомат')), weapon_visual('rifle', 1.0))
    pickup('scenes/pickups/weapon_bazooka.tscn', 'WeaponBazooka',
           dict(kind=2, item_id=S('bazooka'), display_name=S('РПГ-7')), weapon_visual('rpg', 0.9))
    def card(s, p):
        s.box('Card', p, (0.2, 0.13, 0.01), (0, 0, 0), 'keycard')
        s.box('Stripe', p, (0.2, 0.025, 0.012), (0, 0.03, 0), 'dark')
    pickup('scenes/pickups/keycard.tscn', 'Keycard',
           dict(kind=3, item_id=S('armory'), display_name=S('Ключ-карта оружейной')), card, (0.3, 0.6, 1))


# ------------------------------------------------------------------ effects
def particle_mat(s, transparent=False, billboard=False):
    props = dict(shading_mode=0, vertex_color_use_as_albedo=True)
    if transparent: props['transparency'] = 1
    if billboard: props['billboard_mode'] = 3
    return s.sub_res('StandardMaterial3D', **props)


def effects():
    script = 'res://scripts/effects/one_shot_effect.gd'
    # Bullet impact on walls: sparks + dust puff
    s = Scene()
    s.node('Impact', 'Node3D', script=s.ext_res('Script', script), lifetime=1.0, light_fade_time=0.08)
    spark = s.sub_res('BoxMesh', size=V3(0.02, 0.02, 0.06), material=particle_mat(s))
    dust = s.sub_res('QuadMesh', size=V2(0.25, 0.25), material=particle_mat(s, True, True))
    dust_ramp = s.sub_res('Gradient', offsets='PackedFloat32Array(0, 1)',
                          colors='PackedColorArray(0.55, 0.52, 0.48, 0.7, 0.5, 0.48, 0.45, 0)')
    s.node('Sparks', 'CPUParticles3D', '.', emitting=False, amount=10, lifetime=0.3, one_shot=True, explosiveness=1.0,
           mesh=spark, direction=V3(0, 0, -1), spread=50.0, gravity=V3(0, -12, 0), initial_velocity_min=3.0,
           initial_velocity_max=8.0, particle_flag_align_y=True, color=C(3, 2.2, 1))
    s.node('Dust', 'CPUParticles3D', '.', emitting=False, amount=6, lifetime=0.7, one_shot=True, explosiveness=0.9,
           mesh=dust, direction=V3(0, 0, -1), spread=30.0, gravity=V3(0, 0.3, 0), initial_velocity_min=0.3,
           initial_velocity_max=1.2, scale_amount_min=0.6, scale_amount_max=1.4, color_ramp=dust_ramp)
    s.node('Sound', 'AudioStreamPlayer3D', '.', stream=s.sound('impact'), autoplay=True, volume_db=-8.0, unit_size=3.0)
    s.save('scenes/effects/impact.tscn')

    # Blood burst
    s = Scene()
    s.node('BloodBurst', 'Node3D', script=s.ext_res('Script', script), lifetime=1.2)
    drop = s.sub_res('SphereMesh', radius=0.025, height=0.05, radial_segments=6, rings=3, material=particle_mat(s))
    mist = s.sub_res('QuadMesh', size=V2(0.35, 0.35), material=particle_mat(s, True, True))
    mist_ramp = s.sub_res('Gradient', offsets='PackedFloat32Array(0, 1)',
                          colors='PackedColorArray(0.45, 0.02, 0.02, 0.8, 0.3, 0.0, 0.0, 0)')
    s.node('Drops', 'CPUParticles3D', '.', emitting=False, amount=16, lifetime=0.6, one_shot=True, explosiveness=1.0,
           mesh=drop, direction=V3(0, 0, -1), spread=40.0, gravity=V3(0, -14, 0), initial_velocity_min=1.5,
           initial_velocity_max=4.5, scale_amount_min=0.6, scale_amount_max=1.6, color=C(0.35, 0.02, 0.02))
    s.node('Mist', 'CPUParticles3D', '.', emitting=False, amount=5, lifetime=0.5, one_shot=True, explosiveness=1.0,
           mesh=mist, direction=V3(0, 0, -1), spread=35.0, gravity=V3(0, -1, 0), initial_velocity_min=0.5,
           initial_velocity_max=1.5, scale_amount_min=0.6, scale_amount_max=1.3, color_ramp=mist_ramp)
    s.save('scenes/effects/blood_burst.tscn')

    # Blood pool decal
    s = Scene()
    s.node('BloodDecal', 'Decal', script=s.ext_res('Script', script), lifetime=45.0,
           size=V3(1.8, 1.0, 1.8), texture_albedo=s.ext_res('Texture2D', 'res://textures/blood.png'),
           cull_mask=1)
    s.save('scenes/effects/blood_decal.tscn')

    # Explosion
    s = Scene()
    shrink = s.sub_res('Curve', _data='[Vector2(0, 1), 0.0, 0.0, 0, 0, Vector2(1, 0), 0.0, 0.0, 0, 0]', point_count=2)
    grow = s.sub_res('Curve', _data='[Vector2(0, 0.4), 0.0, 0.0, 0, 0, Vector2(1, 1.6), 0.0, 0.0, 0, 0]', point_count=2)
    fire_mesh = s.sub_res('SphereMesh', radius=0.45, height=0.9, radial_segments=8, rings=4, material=particle_mat(s))
    smoke_mesh = s.sub_res('QuadMesh', size=V2(1.6, 1.6), material=particle_mat(s, True, True))
    debris_mesh = s.sub_res('BoxMesh', size=V3(0.12, 0.08, 0.15), material=s.mat('dark'))
    fire_ramp = s.sub_res('Gradient', offsets='PackedFloat32Array(0, 0.3, 1)',
                          colors='PackedColorArray(5, 3.5, 1.5, 1, 3, 0.9, 0.2, 1, 0.15, 0.12, 0.12, 1)')
    smoke_ramp = s.sub_res('Gradient', offsets='PackedFloat32Array(0, 0.2, 1)',
                           colors='PackedColorArray(0.2, 0.18, 0.16, 0, 0.18, 0.16, 0.15, 0.75, 0.25, 0.24, 0.23, 0)')
    s.node('Explosion', 'Node3D', script=s.ext_res('Script', script), lifetime=4.0, light_fade_time=0.6)
    s.node('Fire', 'CPUParticles3D', '.', emitting=False, amount=30, lifetime=0.7, one_shot=True, explosiveness=0.95,
           mesh=fire_mesh, emission_shape=1, emission_sphere_radius=0.6, direction=V3(0, 1, 0), spread=180.0,
           gravity=V3(0, 2, 0), initial_velocity_min=2.0, initial_velocity_max=6.0, damping_min=3.0, damping_max=5.0,
           scale_amount_min=0.7, scale_amount_max=1.6, scale_amount_curve=shrink, color_ramp=fire_ramp)
    s.node('Smoke', 'CPUParticles3D', '.', emitting=False, amount=16, lifetime=3.0, one_shot=True, explosiveness=0.8,
           mesh=smoke_mesh, emission_shape=1, emission_sphere_radius=0.8, direction=V3(0, 1, 0), spread=60.0,
           gravity=V3(0, 0.8, 0), initial_velocity_min=0.5, initial_velocity_max=2.0, damping_min=0.5, damping_max=1.0,
           scale_amount_curve=grow, color_ramp=smoke_ramp)
    s.node('Debris', 'CPUParticles3D', '.', emitting=False, amount=18, lifetime=1.6, one_shot=True, explosiveness=1.0,
           mesh=debris_mesh, direction=V3(0, 1, 0), spread=75.0, gravity=V3(0, -14, 0), initial_velocity_min=5.0,
           initial_velocity_max=11.0, angular_velocity_min=-400.0, angular_velocity_max=400.0, scale_amount_min=0.5,
           scale_amount_max=1.5)
    s.node('Light', 'OmniLight3D', '.', light_color=C(1, 0.55, 0.2), light_energy=12.0, omni_range=14.0)
    s.node('Sound', 'AudioStreamPlayer3D', '.', stream=s.sound('explosion'), autoplay=True, unit_size=15.0, volume_db=2.0)
    s.save('scenes/effects/explosion.tscn')

    # Looping fire (burning cars, barrels)
    s = Scene()
    shrink = s.sub_res('Curve', _data='[Vector2(0, 1), 0.0, 0.0, 0, 0, Vector2(1, 0), 0.0, 0.0, 0, 0]', point_count=2)
    grow = s.sub_res('Curve', _data='[Vector2(0, 0.4), 0.0, 0.0, 0, 0, Vector2(1, 1.6), 0.0, 0.0, 0, 0]', point_count=2)
    flame = s.sub_res('QuadMesh', size=V2(0.8, 0.8), material=particle_mat(s, True, True))
    flame_ramp = s.sub_res('Gradient', offsets='PackedFloat32Array(0, 0.25, 0.7, 1)',
                           colors='PackedColorArray(4, 2.6, 0.8, 0, 3.5, 1.2, 0.2, 0.9, 0.6, 0.15, 0.05, 0.5, 0.05, 0.05, 0.05, 0)')
    smoke = s.sub_res('QuadMesh', size=V2(1.4, 1.4), material=particle_mat(s, True, True))
    smoke_ramp = s.sub_res('Gradient', offsets='PackedFloat32Array(0, 0.3, 1)',
                           colors='PackedColorArray(0.1, 0.1, 0.1, 0, 0.12, 0.11, 0.1, 0.5, 0.2, 0.2, 0.2, 0)')
    s.node('Fire', 'Node3D')
    s.node('Flames', 'CPUParticles3D', '.', amount=40, lifetime=0.8, mesh=flame, emission_shape=3,
           emission_box_extents=V3(0.6, 0.1, 0.6), direction=V3(0, 1, 0), spread=15.0, gravity=V3(0, 2.5, 0),
           initial_velocity_min=0.5, initial_velocity_max=1.5, scale_amount_min=0.5, scale_amount_max=1.2,
           scale_amount_curve=shrink, color_ramp=flame_ramp)
    s.node('Smoke', 'CPUParticles3D', '.', position=V3(0, 1.2, 0), amount=20, lifetime=4.0, mesh=smoke,
           emission_shape=3, emission_box_extents=V3(0.4, 0.1, 0.4), direction=V3(0, 1, 0), spread=15.0,
           gravity=V3(0.3, 0.8, 0), initial_velocity_min=0.6, initial_velocity_max=1.2, scale_amount_curve=grow,
           color_ramp=smoke_ramp)
    s.node('Light', 'OmniLight3D', '.', position=V3(0, 1, 0), light_color=C(1, 0.5, 0.15), light_energy=3.0,
           omni_range=9.0, shadow_enabled=True, script=s.ext_res('Script', 'res://scripts/world/flicker_light.gd'),
           flicker_chance=0.3)
    s.save('scenes/effects/fire.tscn')


# ------------------------------------------------------------------ world prefabs
def prefabs():
    s = Scene()
    s.node('Block', 'StaticBody3D', script=s.ext_res('Script', 'res://scripts/world/block.gd'))
    s.node('MeshInstance3D', 'MeshInstance3D', '.')
    s.node('CollisionShape3D', 'CollisionShape3D', '.')
    s.save('scenes/world/block.tscn')

    s = Scene()
    s.node('Door', 'StaticBody3D', script=s.ext_res('Script', 'res://scripts/world/door.gd'))
    s.node('MeshInstance3D', 'MeshInstance3D', '.')
    s.node('CollisionShape3D', 'CollisionShape3D', '.')
    s.node('OpenSound', 'AudioStreamPlayer3D', '.', stream=s.sound('door_open'), unit_size=6.0)
    s.node('LockedSound', 'AudioStreamPlayer3D', '.', stream=s.sound('door_locked'), unit_size=4.0)
    s.save('scenes/world/door.tscn')

    def car(path, name, paint, police=False):
        s = Scene()
        shape = s.sub_res('BoxShape3D', size=V3(1.9, 1.45, 4.4))
        s.node(name, 'StaticBody3D')
        s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, 0.75, 0), shape=shape)
        s.box('Body', '.', (1.85, 0.65, 4.3), (0, 0.6, 0), paint)
        s.box('Cabin', '.', (1.6, 0.55, 2.2), (0, 1.2, 0.2), paint)
        s.box('Windshield', '.', (1.5, 0.48, 0.05), (0, 1.2, -0.91), 'glass', rot=(-0.35, 0, 0))
        s.box('RearWindow', '.', (1.5, 0.45, 0.05), (0, 1.2, 1.31), 'glass', rot=(0.35, 0, 0))
        s.box('WindowsL', '.', (0.02, 0.4, 1.8), (-0.81, 1.22, 0.2), 'glass')
        s.box('WindowsR', '.', (0.02, 0.4, 1.8), (0.81, 1.22, 0.2), 'glass')
        s.box('BumperF', '.', (1.9, 0.18, 0.12), (0, 0.35, -2.17), 'dark')
        s.box('BumperB', '.', (1.9, 0.18, 0.12), (0, 0.35, 2.17), 'dark')
        s.box('HeadlightL', '.', (0.35, 0.12, 0.03), (-0.6, 0.7, -2.15), 'headlight')
        s.box('HeadlightR', '.', (0.35, 0.12, 0.03), (0.6, 0.7, -2.15), 'headlight')
        s.box('TailL', '.', (0.3, 0.1, 0.03), (-0.65, 0.72, 2.15), 'taillight')
        s.box('TailR', '.', (0.3, 0.1, 0.03), (0.65, 0.72, 2.15), 'taillight')
        for i, (x, z) in enumerate([(-0.85, -1.35), (0.85, -1.35), (-0.85, 1.35), (0.85, 1.35)]):
            s.cyl(f'Wheel{i}', '.', 0.34, 0.24, (x, 0.34, z), 'tire', rot=(0, 0, RX))
        if police:
            s.box('Bar', '.', (1.2, 0.1, 0.25), (0, 1.52, 0.2), 'dark')
            s.box('SirenR', '.', (0.5, 0.1, 0.22), (-0.3, 1.6, 0.2), 'siren_red')
            s.box('SirenB', '.', (0.5, 0.1, 0.22), (0.3, 1.6, 0.2), 'siren_blue')
            s.box('DoorStripeL', '.', (0.02, 0.2, 2.0), (-0.935, 0.65, 0.0), 'paint_white')
            s.box('DoorStripeR', '.', (0.02, 0.2, 2.0), (0.935, 0.65, 0.0), 'paint_white')
            s.node('SirenLightR', 'OmniLight3D', '.', position=V3(-0.4, 1.9, 0.2), light_color=C(1, 0.1, 0.1),
                   light_energy=2.0, omni_range=7.0, script=s.ext_res('Script', 'res://scripts/world/flicker_light.gd'),
                   flicker_chance=0.5)
            s.node('SirenLightB', 'OmniLight3D', '.', position=V3(0.4, 1.9, 0.2), light_color=C(0.2, 0.3, 1),
                   light_energy=2.0, omni_range=7.0, script=s.ext_res('Script', 'res://scripts/world/flicker_light.gd'),
                   flicker_chance=0.5)
        s.save(path)
    car('scenes/world/car_red.tscn', 'CarRed', 'car_red')
    car('scenes/world/car_blue.tscn', 'CarBlue', 'car_blue')
    car('scenes/world/car_white.tscn', 'CarWhite', 'car_white')
    car('scenes/world/car_black.tscn', 'CarBlack', 'car_black')
    car('scenes/world/police_car.tscn', 'PoliceCar', 'police_blue', police=True)

    s = Scene()
    shape = s.sub_res('BoxShape3D', size=V3(2.6, 3.0, 11.0))
    s.node('Bus', 'StaticBody3D')
    s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, 1.6, 0), shape=shape)
    s.box('Body', '.', (2.55, 2.4, 10.9), (0, 1.75, 0), 'bus_yellow')
    s.box('Roof', '.', (2.4, 0.15, 10.6), (0, 3.0, 0), 'car_white')
    s.box('WindowsL', '.', (0.02, 0.9, 9.0), (-1.28, 2.2, 0.4), 'glass')
    s.box('WindowsR', '.', (0.02, 0.9, 9.0), (1.28, 2.2, 0.4), 'glass')
    s.box('Front', '.', (2.3, 1.2, 0.02), (0, 2.0, -5.46), 'glass')
    s.box('Stripe', '.', (2.57, 0.15, 10.9), (0, 1.3, 0), 'dark')
    for i, (x, z) in enumerate([(-1.15, -3.8), (1.15, -3.8), (-1.15, 3.6), (1.15, 3.6)]):
        s.cyl(f'Wheel{i}', '.', 0.5, 0.3, (x, 0.5, z), 'tire', rot=(0, 0, RX))
    s.save('scenes/world/bus.tscn')

    def lamp(path, flicker):
        s = Scene()
        shape = s.sub_res('CylinderShape3D', radius=0.12, height=6.0)
        s.node('StreetLamp', 'StaticBody3D')
        s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, 3, 0), shape=shape)
        s.cyl('Pole', '.', 0.08, 6.0, (0, 3, 0), 'metal', top=0.06)
        s.box('Arm', '.', (0.08, 0.08, 1.4), (0, 5.9, -0.65), 'metal')
        s.box('Head', '.', (0.35, 0.12, 0.6), (0, 5.85, -1.3), 'dark')
        s.box('Bulb', '.', (0.28, 0.03, 0.5), (0, 5.78, -1.3), 'lamp_glow')
        props = dict(position=V3(0, 5.6, -1.3), rotation=V3(-RX, 0, 0), light_color=C(1, 0.78, 0.5), light_energy=4.0,
                     spot_range=14.0, spot_angle=60.0, spot_attenuation=0.7, shadow_enabled=True)
        if flicker:
            props.update(script=s.ext_res('Script', 'res://scripts/world/flicker_light.gd'), flicker_chance=0.08)
        s.node('Light', 'SpotLight3D', '.', **props)
        s.save(path)
    lamp('scenes/world/street_lamp.tscn', False)
    lamp('scenes/world/street_lamp_flicker.tscn', True)

    s = Scene()
    shape = s.sub_res('CylinderShape3D', radius=0.3, height=0.9)
    s.node('Barrel', 'StaticBody3D')
    s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, 0.45, 0), shape=shape)
    s.cyl('Body', '.', 0.3, 0.9, (0, 0.45, 0), 'metal_rust')
    s.cyl('Ring1', '.', 0.31, 0.04, (0, 0.25, 0), 'dark')
    s.cyl('Ring2', '.', 0.31, 0.04, (0, 0.65, 0), 'dark')
    s.save('scenes/world/barrel.tscn')

    s = Scene()
    shape = s.sub_res('BoxShape3D', size=V3(1.8, 1.3, 1.1))
    s.node('Dumpster', 'StaticBody3D')
    s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, 0.65, 0), shape=shape)
    s.box('Body', '.', (1.8, 1.1, 1.1), (0, 0.6, 0), 'car_green')
    s.box('Lid', '.', (1.85, 0.08, 1.15), (0, 1.18, 0.05), 'dark', rot=(-0.1, 0, 0))
    s.save('scenes/world/dumpster.tscn')

    s = Scene()
    shape = s.sub_res('BoxShape3D', size=V3(2.0, 0.8, 1.0))
    s.node('Desk', 'StaticBody3D')
    s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, 0.4, 0), shape=shape)
    s.box('Top', '.', (2.0, 0.06, 1.0), (0, 0.78, 0), 'wood')
    s.box('SideL', '.', (0.06, 0.75, 0.95), (-0.95, 0.375, 0), 'wood')
    s.box('SideR', '.', (0.06, 0.75, 0.95), (0.95, 0.375, 0), 'wood')
    s.box('Monitor', '.', (0.5, 0.35, 0.05), (0.3, 1.05, 0.2), 'dark')
    s.box('Screen', '.', (0.44, 0.28, 0.01), (0.3, 1.05, 0.17), 'glass')
    s.box('Papers', '.', (0.3, 0.02, 0.22), (-0.5, 0.82, 0.1), 'paint_white', rot=(0, 0.3, 0))
    s.save('scenes/world/desk.tscn')

    s = Scene()
    shape = s.sub_res('BoxShape3D', size=V3(1.8, 2.0, 0.5))
    s.node('Lockers', 'StaticBody3D')
    s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, 1.0, 0), shape=shape)
    s.box('Body', '.', (1.8, 2.0, 0.5), (0, 1.0, 0), 'metal')
    for i in range(3):
        s.box(f'Line{i}', '.', (0.02, 1.9, 0.01), (-0.6 + i * 0.6, 1.0, -0.255), 'dark')
        s.box(f'Vent{i}', '.', (0.3, 0.15, 0.01), (-0.3 + (i - 1) * 0.6 + 0.3, 1.7, -0.255), 'dark')
    s.save('scenes/world/lockers.tscn')

    s = Scene()
    shape = s.sub_res('BoxShape3D', size=V3(1.2, 2.2, 0.5))
    s.node('Shelf', 'StaticBody3D')
    s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(0, 1.1, 0), shape=shape)
    for i, y in enumerate((0.1, 0.8, 1.5, 2.15)):
        s.box(f'Board{i}', '.', (1.2, 0.04, 0.5), (0, y, 0), 'metal')
    s.box('PostL', '.', (0.04, 2.2, 0.5), (-0.58, 1.1, 0), 'metal')
    s.box('PostR', '.', (0.04, 2.2, 0.5), (0.58, 1.1, 0), 'metal')
    for i, (x, y) in enumerate([(-0.3, 0.95), (0.25, 0.95), (0.0, 1.65), (-0.35, 0.25)]):
        s.box(f'Box{i}', '.', (0.35, 0.28, 0.35), (x, y, 0), 'ammo_green')
    s.save('scenes/world/shelf.tscn')

    s = Scene()
    s.node('FloodlightTower', 'Node3D')
    s.node('Body', 'StaticBody3D', '.')
    shape = s.sub_res('BoxShape3D', size=V3(0.8, 18.0, 0.8))
    s.node('CollisionShape3D', 'CollisionShape3D', 'Body', position=V3(0, 9, 0), shape=shape)
    s.box('Mast', '.', (0.6, 18, 0.6), (0, 9, 0), 'metal')
    s.box('Frame', '.', (4.0, 2.2, 0.4), (0, 18.5, 0), 'dark', rot=(-0.4, 0, 0))
    for i, (x, y) in enumerate([(-1.3, 0.5), (0, 0.5), (1.3, 0.5), (-1.3, -0.5), (0, -0.5), (1.3, -0.5)]):
        s.box(f'Lamp{i}', '.', (1.0, 0.8, 0.05), (x, 18.5 + y * 0.92, -0.23 + y * 0.39), 'flood_glow', rot=(-0.4, 0, 0))
    s.node('Light', 'SpotLight3D', '.', position=V3(0, 18, -1), rotation=V3(-0.38, 0, 0), light_color=C(0.9, 0.95, 1),
           light_energy=5.0, spot_range=100.0, spot_angle=30.0, spot_attenuation=0.9, shadow_enabled=True)
    s.save('scenes/world/floodlight_tower.tscn')

    s = Scene()
    s.node('Helicopter', 'Node3D', script=s.ext_res('Script', 'res://scripts/world/helicopter.gd'))
    s.box('Cabin', '.', (2.4, 2.2, 4.5), (0, 1.6, 0), 'military')
    s.box('Nose', '.', (2.0, 1.4, 1.4), (0, 1.3, -2.8), 'military', rot=(0.25, 0, 0))
    s.box('Glass', '.', (1.8, 1.0, 0.05), (0, 2.0, -3.35), 'glass', rot=(-0.5, 0, 0))
    s.box('Tail', '.', (0.6, 0.6, 6.0), (0, 2.3, 5.0), 'military')
    s.box('Fin', '.', (0.15, 1.8, 1.0), (0, 3.0, 7.8), 'military')
    s.box('SkidL', '.', (0.12, 0.12, 4.5), (-1.2, 0.06, 0), 'dark')
    s.box('SkidR', '.', (0.12, 0.12, 4.5), (1.2, 0.06, 0), 'dark')
    s.box('StrutL', '.', (0.1, 0.5, 0.1), (-1.15, 0.3, 0), 'dark')
    s.box('StrutR', '.', (0.1, 0.5, 0.1), (1.15, 0.3, 0), 'dark')
    s.box('Door', '.', (0.05, 1.4, 1.6), (1.21, 1.4, 0.3), 'dark')
    s.node('MainRotor', 'Node3D', '.', position=V3(0, 2.95, 0))
    s.cyl('Hub', 'MainRotor', 0.25, 0.3, (0, 0, 0), 'dark')
    s.box('Blade1', 'MainRotor', (12.0, 0.04, 0.4), (0, 0.15, 0), 'dark')
    s.box('Blade2', 'MainRotor', (0.4, 0.04, 12.0), (0, 0.15, 0), 'dark')
    s.node('TailRotor', 'Node3D', '.', position=V3(0.25, 3.2, 7.8))
    s.box('Blade1', 'TailRotor', (0.04, 2.0, 0.2), (0, 0, 0), 'dark')
    s.box('Blade2', 'TailRotor', (0.04, 0.2, 2.0), (0, 0, 0), 'dark')
    s.node('Searchlight', 'SpotLight3D', '.', position=V3(0, 0.8, -3.0), rotation=V3(-1.0, 0, 0),
           light_color=C(1, 1, 0.9), light_energy=6.0, spot_range=40.0, spot_angle=20.0)
    s.node('Beacon', 'OmniLight3D', '.', position=V3(0, 0.3, 0), light_color=C(1, 0.1, 0.1), light_energy=2.0,
           omni_range=6.0, script=s.ext_res('Script', 'res://scripts/world/flicker_light.gd'), flicker_chance=0.4)
    s.node('Sound', 'AudioStreamPlayer3D', '.', stream=s.sound('helicopter'), unit_size=30.0, max_distance=200.0,
           volume_db=4.0)
    s.save('scenes/world/helicopter.tscn')


# ------------------------------------------------------------------ UI
FULL = dict(anchors_preset=15, anchor_right=1.0, anchor_bottom=1.0, grow_horizontal=2, grow_vertical=2)
CENTER = dict(anchors_preset=8, anchor_left=0.5, anchor_top=0.5, anchor_right=0.5, anchor_bottom=0.5,
              grow_horizontal=2, grow_vertical=2)
BLOOD = C(0.75, 0.08, 0.06)


def ui_files():
    open('scenes/ui/vignette.gdshader', 'w').write('''shader_type canvas_item;

uniform float intensity : hint_range(0.0, 1.0) = 0.0;
uniform vec4 tint : source_color = vec4(0.6, 0.0, 0.0, 1.0);

void fragment() {
	float d = distance(UV, vec2(0.5));
	COLOR = vec4(tint.rgb, smoothstep(0.2, 0.75, d) * intensity);
}
''')

    def stylebox(rid, bg, border, extra=''):
        return f'''[sub_resource type="StyleBoxFlat" id="{rid}"]
content_margin_left = 22.0
content_margin_top = 10.0
content_margin_right = 22.0
content_margin_bottom = 10.0
bg_color = {bg}
border_width_left = 2
border_width_top = 2
border_width_right = 2
border_width_bottom = 2
border_color = {border}
corner_radius_top_left = 3
corner_radius_top_right = 3
corner_radius_bottom_right = 3
corner_radius_bottom_left = 3
{extra}'''
    theme = '[gd_resource type="Theme" format=3]\n\n' + '\n\n'.join([
        stylebox('normal', C(0.06, 0.05, 0.05, 0.92), C(0.55, 0.1, 0.08, 0.6)),
        stylebox('hover', C(0.2, 0.05, 0.04, 0.95), C(0.85, 0.15, 0.1, 1)),
        stylebox('pressed', C(0.45, 0.07, 0.05, 1), C(1, 0.3, 0.2, 1)),
        stylebox('panel', C(0, 0, 0, 0.6), C(0, 0, 0, 0)),
        '[sub_resource type="StyleBoxFlat" id="bar_bg"]\nbg_color = Color(0, 0, 0, 0.55)',
        '[sub_resource type="StyleBoxFlat" id="bar_fill"]\nbg_color = Color(1, 1, 1, 1)',
    ]) + '''

[resource]
default_font_size = 22
Button/colors/font_hover_color = Color(1, 1, 1, 1)
Button/styles/focus = SubResource("hover")
Button/styles/hover = SubResource("hover")
Button/styles/normal = SubResource("normal")
Button/styles/pressed = SubResource("pressed")
Label/colors/font_outline_color = Color(0, 0, 0, 1)
Label/constants/outline_size = 5
PanelContainer/styles/panel = SubResource("panel")
ProgressBar/styles/background = SubResource("bar_bg")
ProgressBar/styles/fill = SubResource("bar_fill")
RichTextLabel/colors/font_outline_color = Color(0, 0, 0, 1)
RichTextLabel/constants/outline_size = 4
'''
    open('scenes/ui/theme.tres', 'w').write(theme)


def label(s, name, parent, text='', size=None, color=None, align=None, **props):
    p = dict(props)
    if text: p['text'] = S(text)
    if size: p['theme_override_font_sizes/font_size'] = size
    if color: p['theme_override_colors/font_color'] = color
    if align is not None: p['horizontal_alignment'] = align
    s.node(name, 'Label', parent, **p)


def menu_screen(s, name, title, title_color, buttons, labels=(), parent='.', bg=0.8):
    s.node(name, 'Control', parent, **FULL)
    base = name if parent == '.' else f'{parent}/{name}'
    s.node('Background', 'ColorRect', base, color=C(0.02, 0.01, 0.01, bg), **FULL)
    s.node('Center', 'CenterContainer', base, **FULL)
    s.node('VBox', 'VBoxContainer', f'{base}/Center', **{'theme_override_constants/separation': 14})
    vb = f'{base}/Center/VBox'
    if title is not None:
        label(s, 'Title', vb, title, 64, title_color, 1, **{'theme_override_constants/outline_size': 10})
    for lname, text, size, extra in labels:
        label(s, lname, vb, text, size, None, 1, **extra)
    s.node('Spacer', 'Control', vb, custom_minimum_size=V2(0, 10))
    for bname, text in buttons:
        s.node(bname, 'Button', vb, custom_minimum_size=V2(340, 0), size_flags_horizontal=4, text=S(text))


def hud():
    s = Scene()
    vig = s.sub_res('ShaderMaterial', shader=s.ext_res('Shader', 'res://scenes/ui/vignette.gdshader'),
                    **{'shader_parameter/intensity': 0.0})
    s.node('HUD', 'CanvasLayer', process_mode=3, script=s.ext_res('Script', 'res://scripts/ui/hud.gd'))
    s.node('Gameplay', 'Control', '.', mouse_filter=2, **FULL)
    g = 'Gameplay'
    s.node('Vignette', 'ColorRect', g, material=vig, mouse_filter=2, **FULL)
    s.node('Crosshair', 'Control', g, mouse_filter=2, script=s.ext_res('Script', 'res://scripts/ui/crosshair.gd'), **CENTER)
    s.node('HitMarker', 'Control', g, mouse_filter=2, script=s.ext_res('Script', 'res://scripts/ui/hit_marker.gd'), **CENTER)
    label(s, 'PromptLabel', g, '', 20, C(1, 0.95, 0.8), 1, anchors_preset=8, anchor_left=0.5, anchor_top=0.5,
          anchor_right=0.5, anchor_bottom=0.5, offset_left=-300.0, offset_top=40.0, offset_right=300.0,
          offset_bottom=70.0, grow_horizontal=2)
    label(s, 'PickupLabel', g, '', 20, C(0.7, 1, 0.6), 1, anchors_preset=8, anchor_left=0.5, anchor_top=0.5,
          anchor_right=0.5, anchor_bottom=0.5, offset_left=-300.0, offset_top=75.0, offset_right=300.0,
          offset_bottom=105.0, grow_horizontal=2)
    label(s, 'TimerLabel', g, '', 34, C(1, 0.85, 0.5), 1, anchors_preset=5, anchor_left=0.5, anchor_right=0.5,
          offset_left=-300.0, offset_top=16.0, offset_right=300.0, offset_bottom=60.0, grow_horizontal=2)
    s.node('ObjectiveBox', 'VBoxContainer', g, offset_left=24.0, offset_top=20.0, offset_right=520.0,
           offset_bottom=110.0, mouse_filter=2)
    label(s, 'Header', f'{g}/ObjectiveBox', 'ЦЕЛЬ', 15, C(0.9, 0.3, 0.2))
    label(s, 'ObjectiveLabel', f'{g}/ObjectiveBox', '', 20, None, None, autowrap_mode=3)
    s.node('Subtitle', 'PanelContainer', g, anchors_preset=7, anchor_left=0.5, anchor_top=1.0, anchor_right=0.5,
           anchor_bottom=1.0, offset_left=-380.0, offset_top=-200.0, offset_right=380.0, offset_bottom=-130.0,
           grow_horizontal=2, grow_vertical=0, mouse_filter=2)
    s.node('Text', 'RichTextLabel', f'{g}/Subtitle', bbcode_enabled=True, fit_content=True, scroll_active=False,
           mouse_filter=2, **{'theme_override_font_sizes/normal_font_size': 20})
    s.node('HealthBox', 'VBoxContainer', g, anchors_preset=2, anchor_top=1.0, anchor_bottom=1.0, offset_left=24.0,
           offset_top=-90.0, offset_right=300.0, offset_bottom=-24.0, grow_vertical=0, alignment=2, mouse_filter=2)
    label(s, 'HealthLabel', f'{g}/HealthBox', '+ 100', 32)
    s.node('HealthBar', 'ProgressBar', f'{g}/HealthBox', custom_minimum_size=V2(0, 12), value=100.0,
           show_percentage=False, mouse_filter=2)
    s.node('WeaponBox', 'VBoxContainer', g, anchors_preset=3, anchor_left=1.0, anchor_top=1.0, anchor_right=1.0,
           anchor_bottom=1.0, offset_left=-344.0, offset_top=-130.0, offset_right=-24.0, offset_bottom=-24.0,
           grow_horizontal=0, grow_vertical=0, alignment=2, mouse_filter=2)
    label(s, 'ReloadLabel', f'{g}/WeaponBox', 'ПЕРЕЗАРЯДКА...', 18, C(1, 0.8, 0.3), 2)
    label(s, 'WeaponLabel', f'{g}/WeaponBox', '', 18, C(0.85, 0.85, 0.8), 2)
    label(s, 'AmmoLabel', f'{g}/WeaponBox', '', 42, None, 2)
    s.node('Slots', 'HBoxContainer', g, anchors_preset=7, anchor_left=0.5, anchor_top=1.0, anchor_right=0.5,
           anchor_bottom=1.0, offset_left=-300.0, offset_top=-44.0, offset_right=300.0, offset_bottom=-16.0,
           grow_horizontal=2, grow_vertical=0, alignment=1, mouse_filter=2, **{'theme_override_constants/separation': 24})

    s.node('IntroScreen', 'Control', '.', **FULL)
    s.node('Background', 'ColorRect', 'IntroScreen', color=C(0, 0, 0, 0.92), **FULL)
    s.node('Center', 'CenterContainer', 'IntroScreen', **FULL)
    s.node('VBox', 'VBoxContainer', 'IntroScreen/Center', custom_minimum_size=V2(760, 0),
           **{'theme_override_constants/separation': 14})
    vb = 'IntroScreen/Center/VBox'
    label(s, 'Chapter', vb, '', 22, C(0.8, 0.2, 0.15), 1)
    label(s, 'Title', vb, '', 60, None, 1, **{'theme_override_constants/outline_size': 10})
    label(s, 'Story', vb, '', 21, C(0.85, 0.82, 0.78), 1, autowrap_mode=3)
    s.node('Spacer', 'Control', vb, custom_minimum_size=V2(0, 16))
    s.node('ContinueButton', 'Button', vb, custom_minimum_size=V2(300, 0), size_flags_horizontal=4, text=S('Начать'))
    label(s, 'Hint', vb, 'WASD — движение · Shift — бег · Пробел — прыжок · ЛКМ — атака · R — перезарядка\n'
                         '1–4 / колесо — оружие · E — использовать · F — фонарик · Esc — пауза', 15,
          C(0.6, 0.6, 0.6), 1)

    menu_screen(s, 'PauseMenu', 'ПАУЗА', C(1, 1, 1),
                [('ResumeButton', 'Продолжить'), ('RestartButton', 'Начать главу заново'), ('MenuButton', 'Главное меню')])
    menu_screen(s, 'DeathScreen', 'ВЫ ПОГИБЛИ', BLOOD,
                [('RestartButton', 'Начать главу заново'), ('MenuButton', 'Главное меню')], bg=0.7)
    s.node('Fade', 'ColorRect', '.', mouse_filter=2, color=C(0, 0, 0, 0), **FULL)
    s.node('RadioSound', 'AudioStreamPlayer', '.', stream=s.sound('radio'), volume_db=-8.0)
    s.save('scenes/ui/hud.tscn')

    # Main menu
    s = Scene()
    grad = s.sub_res('Gradient', offsets='PackedFloat32Array(0, 1)',
                     colors='PackedColorArray(0.18, 0.02, 0.02, 1, 0.01, 0.01, 0.01, 1)')
    tex = s.sub_res('GradientTexture2D', gradient=grad, fill=2, fill_from=V2(0.5, 0.35), fill_to=V2(1.1, 1.1))
    s.node('MainMenu', 'Control', script=s.ext_res('Script', 'res://scripts/ui/main_menu.gd'), **FULL)
    s.node('Background', 'TextureRect', '.', texture=tex, expand_mode=1, stretch_mode=0, **FULL)
    s.node('Center', 'CenterContainer', '.', **FULL)
    s.node('VBox', 'VBoxContainer', 'Center', **{'theme_override_constants/separation': 14})
    label(s, 'Title', 'Center/VBox', 'МЁРТВЫЙ ГОРОД', 84, BLOOD, 1, **{'theme_override_constants/outline_size': 14})
    label(s, 'Subtitle', 'Center/VBox', 'Последний вертолёт улетает на рассвете', 22, C(0.8, 0.75, 0.7), 1)
    s.node('Spacer', 'Control', 'Center/VBox', custom_minimum_size=V2(0, 30))
    for b, t in [('ContinueButton', 'Продолжить'), ('NewGameButton', 'Новая игра'), ('QuitButton', 'Выход')]:
        s.node(b, 'Button', 'Center/VBox', custom_minimum_size=V2(340, 0), size_flags_horizontal=4, text=S(t))
    s.node('Ambience', 'AudioStreamPlayer', '.', stream=s.sound('ambience'), autoplay=True, volume_db=-6.0)
    s.save('scenes/ui/main_menu.tscn')

    # Ending
    s = Scene()
    s.node('Ending', 'Control', script=s.ext_res('Script', 'res://scripts/ui/ending.gd'), **FULL)
    s.node('Background', 'ColorRect', '.', color=C(0.01, 0.01, 0.015, 1), **FULL)
    s.node('Center', 'CenterContainer', '.', **FULL)
    s.node('VBox', 'VBoxContainer', 'Center', custom_minimum_size=V2(800, 0), **{'theme_override_constants/separation': 16})
    label(s, 'Title', 'Center/VBox', 'ЭВАКУАЦИЯ', 64, C(0.95, 0.8, 0.5), 1, **{'theme_override_constants/outline_size': 10})
    label(s, 'Story', 'Center/VBox',
          'Вертолёт уходит в рассветное небо. Внизу догорает город, который ещё неделю назад был домом.\n\n'
          '«Говорит диспетчер. Борт с выжившим принят. Ты справился. Добро пожаловать в Безопасную зону.»\n\n'
          'Мёртвые остались внизу. Пока что.', 21, C(0.85, 0.82, 0.78), 1, autowrap_mode=3)
    label(s, 'Stats', 'Center/VBox', '', 22, C(0.7, 0.7, 0.7), 1)
    s.node('Spacer', 'Control', 'Center/VBox', custom_minimum_size=V2(0, 20))
    s.node('MenuButton', 'Button', 'Center/VBox', custom_minimum_size=V2(340, 0), size_flags_horizontal=4,
           text=S('Главное меню'))
    s.node('Ambience', 'AudioStreamPlayer', '.', stream=s.sound('ambience'), autoplay=True, volume_db=-10.0)
    s.save('scenes/ui/ending.tscn')


if __name__ == '__main__':
    mats()
    weapons()
    player()
    zombies()
    pickups()
    effects()
    prefabs()
    ui_files()
    hud()
    print('assets ok')
