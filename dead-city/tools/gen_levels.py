"""Generates the five chapters of Dead City. Run from the project root."""
import math
import random
from tscn import *

ZOMBIE = {k: f'res://scenes/zombies/{k}.tscn' for k in
          ('walker', 'runner', 'brute', 'butcher', 'warden', 'patient_zero', 'lineman', 'colossus')}
PICKUP = {k: f'res://scenes/pickups/{k}.tscn' for k in
          ('medkit', 'ammo_pistol', 'ammo_rifle', 'ammo_rocket', 'ammo_shells', 'weapon_rifle', 'weapon_shotgun',
           'weapon_bazooka', 'keycard')}
NAV = 'NavigationRegion3D'


def story_rel(path):
    """Path from a node directly under Story to a root-relative path."""
    return '../' + path[6:] if path.startswith('Story/') else '../../' + path


class LevelBuilder(Scene):
    def __init__(self, root_name, props):
        super().__init__()
        self.count = {}
        self.rnd = random.Random(root_name)
        self.node(root_name, 'Node3D', script=self.ext_res('Script', 'res://scripts/story/level.gd'), **props)

    def uid(self, prefix):
        self.count[prefix] = self.count.get(prefix, 0) + 1
        return f'{prefix}{self.count[prefix]}'

    def setup(self, env, moon=None):
        self.node('WorldEnvironment', 'WorldEnvironment', '.', environment=self.sub_res('Environment', **env))
        if moon:
            self.node('Moon', 'DirectionalLight3D', '.', **moon)
        nav = self.sub_res('NavigationMesh', geometry_parsed_geometry_type=1, geometry_collision_mask=1,
                           agent_height=2.0, agent_radius=0.5, agent_max_climb=0.25, agent_max_slope=40.0)
        self.node(NAV, 'NavigationRegion3D', '.', navigation_mesh=nav)
        for name in ('Decor', 'Lights', 'Doors', 'Zombies', 'Pickups', 'Story'):
            self.node(name, 'Node3D', '.')

    # -- geometry
    def blk(self, mat, size, pos, rot=None, cyl=False, name=None, parent=NAV):
        props = dict(position=V3(*pos), size=V3(*size), material=self.mat(mat))
        if rot: props['rotation'] = V3(*rot)
        if cyl: props['cylinder'] = True
        self.node(name or self.uid('Block'), None, parent,
                  instance=self.ext_res('PackedScene', 'res://scenes/world/block.tscn'), **props)

    def floor(self, mat, x0, x1, z0, z1, top=0.0, thick=1.0, tile=16.0):
        """Split into tiles: renderers limit how many lights can touch one mesh."""
        xa, xb = sorted((x0, x1))
        za, zb = sorted((z0, z1))
        nx, nz = max(1, math.ceil((xb - xa) / tile)), max(1, math.ceil((zb - za) / tile))
        sx, sz = (xb - xa) / nx, (zb - za) / nz
        for i in range(nx):
            for j in range(nz):
                cx, cz = xa + sx * (i + 0.5), za + sz * (j + 0.5)
                self.blk(mat, (sx, thick, sz), (cx, top - thick / 2, cz))

    def wall_x(self, x, z0, z1, mat, h=4.0, t=0.3, y0=0.0):
        """Wall along Z at a fixed x."""
        if abs(z1 - z0) > 0.01:
            self.blk(mat, (t, h, abs(z1 - z0)), (x, y0 + h / 2, (z0 + z1) / 2))

    def wall_z(self, z, x0, x1, mat, h=4.0, t=0.3, y0=0.0):
        """Wall along X at a fixed z."""
        if abs(x1 - x0) > 0.01:
            self.blk(mat, (abs(x1 - x0), h, t), ((x0 + x1) / 2, y0 + h / 2, z))

    def prop(self, scene, pos, rot_y=0.0, parent=NAV, name=None, **props):
        p = dict(position=V3(*pos))
        if rot_y: p['rotation'] = V3(0, rot_y, 0)
        p.update(props)
        base = scene.split('/')[-1].split('.')[0].title().replace('_', '')
        self.node(name or self.uid(base), None, parent, instance=self.ext_res('PackedScene', scene), **p)

    def decor(self, size, pos, mat, rot=None, **extra):
        self.box(self.uid('D'), 'Decor', size, pos, mat, rot=rot, **extra)

    def fire(self, pos):
        self.prop('res://scenes/effects/fire.tscn', pos, parent='Decor')

    def omni(self, pos, color, energy, rng, flicker=False, shadow=False, name=None):
        props = dict(position=V3(*pos), light_color=C(*color), light_energy=energy, omni_range=rng)
        if shadow: props['shadow_enabled'] = True
        if flicker:
            props['script'] = self.ext_res('Script', 'res://scripts/world/flicker_light.gd')
        self.node(name or self.uid('Light'), 'OmniLight3D', 'Lights', **props)

    def ceiling_lamp(self, x, z, y=3.95, flicker=False, energy=2.2, rng=9.0, name=None, power=False):
        """power=True: dark until a StoryEvent activates it (power_light.gd)."""
        self.decor((1.0, 0.05, 0.35), (x, y, z), 'lamp_off' if power else 'lamp_glow', cast_shadow=0)
        if power:
            self.node(name or self.uid('PowerLight'), 'OmniLight3D', 'Lights', position=V3(x, y - 0.4, z),
                      light_color=C(0.9, 0.95, 1.0), light_energy=energy, omni_range=rng,
                      script=self.ext_res('Script', 'res://scripts/world/power_light.gd'))
            return
        self.omni((x, y - 0.4, z), (1, 0.88, 0.7), energy, rng, flicker, name=name)

    # -- gameplay
    def zombie(self, kind, pos, rot_y=None, name=None, **props):
        p = dict(position=V3(*pos), rotation=V3(0, self.rnd.uniform(-math.pi, math.pi) if rot_y is None else rot_y, 0))
        p.update(props)
        self.node(name or self.uid(kind.title()), None, 'Zombies', instance=self.ext_res('PackedScene', ZOMBIE[kind]), **p)

    def pickup(self, kind, pos, name=None, **props):
        self.node(name or self.uid(kind.title().replace('_', '')), None, 'Pickups',
                  instance=self.ext_res('PackedScene', PICKUP[kind]), position=V3(*pos), **props)

    def event(self, name, objective='', speaker='', message='', duration=6.0, delay=0.0, targets=(), complete=False):
        props = dict(script=self.ext_res('Script', 'res://scripts/story/story_event.gd'))
        if delay: props['delay'] = float(delay)
        if objective: props['objective'] = S(objective)
        if speaker: props['speaker'] = S(speaker)
        if message: props['message'] = S(message)
        if message: props['message_duration'] = float(duration)
        if targets: props['targets'] = NPS([story_rel(t) for t in targets])
        if complete: props['complete_level'] = True
        self.node(name, 'Node', 'Story', **props)

    def trigger(self, name, pos, size, event, enabled=True):
        props = dict(position=V3(*pos), collision_layer=0, collision_mask=2, monitorable=False,
                     script=self.ext_res('Script', 'res://scripts/story/story_trigger.gd'), event=NP('../' + event))
        if not enabled: props['enabled'] = False
        self.node(name, 'Area3D', 'Story', **props)
        self.node('CollisionShape3D', 'CollisionShape3D', f'Story/{name}', shape=self.sub_res('BoxShape3D', size=V3(*size)))

    def spawner(self, name, markers, kinds, count, interval=0.7, alerted=True, continuous=False, max_alive=10,
                on_cleared=None):
        scenes = 'Array[PackedScene]([' + ', '.join(self.ext_res('PackedScene', ZOMBIE[k]) for k in kinds) + '])'
        props = dict(script=self.ext_res('Script', 'res://scripts/story/zombie_spawner.gd'), zombie_scenes=scenes,
                     count=count, interval=float(interval), max_alive=max_alive)
        if not alerted: props['alerted'] = False
        if continuous: props['continuous'] = True
        if on_cleared: props['on_cleared'] = NP('../' + on_cleared)
        self.node(name, 'Node3D', 'Story', **props)
        for i, m in enumerate(markers):
            self.node(f'M{i}', 'Marker3D', f'Story/{name}', position=V3(*m))

    def door(self, name, size, pos, mat, event=None, **props):
        p = dict(position=V3(*pos), size=V3(*size), material=self.mat(mat))
        for k, v in props.items():
            p[k] = S(v) if isinstance(v, str) else v
        if event: p['event'] = NP('../../Story/' + event)
        self.node(name, None, 'Doors', instance=self.ext_res('PackedScene', 'res://scenes/world/door.tscn'), **p)

    def finish(self, player_pos, player_rot=0.0, ambience_db=-8.0):
        self.node('Player', None, '.', instance=self.ext_res('PackedScene', 'res://scenes/player/player.tscn'),
                  position=V3(*player_pos), rotation=V3(0, player_rot, 0))
        self.node('HUD', None, '.', instance=self.ext_res('PackedScene', 'res://scenes/ui/hud.tscn'))
        self.node('Ambience', 'AudioStreamPlayer', '.', stream=self.sound('ambience'), autoplay=True, volume_db=ambience_db)


def night_env(L, fog=0.025, ambient=0.9, horizon=(0.08, 0.07, 0.1)):
    sky = L.sub_res('ProceduralSkyMaterial', sky_top_color=C(0.01, 0.012, 0.03), sky_horizon_color=C(*horizon),
                    ground_bottom_color=C(0.01, 0.01, 0.01), ground_horizon_color=C(*horizon),
                    sun_angle_max=8.0, sun_curve=0.05)
    # Flat moonlit ambient so shadows are dark but never pitch black.
    return dict(background_mode=2, sky=L.sub_res('Sky', sky_material=sky), ambient_light_source=2,
                ambient_light_color=C(0.1, 0.11, 0.16), ambient_light_energy=ambient, tonemap_mode=3, ssao_enabled=True, glow_enabled=True,
                glow_intensity=1.0, glow_bloom=0.06, fog_enabled=True, fog_light_color=C(0.05, 0.05, 0.08),
                fog_density=fog, fog_sky_affect=0.6)


MOON = dict(rotation=V3(-0.9, 0.6, 0), light_color=C(0.55, 0.62, 0.85), light_energy=0.35, shadow_enabled=True,
            directional_shadow_max_distance=80.0)


# =================================================================== CHAPTER 1
def level_1():
    L = LevelBuilder('Outskirts', dict(
        chapter_number=1, chapter_title=S('Окраина'),
        intro_text=S('Девять дней назад мёртвые поднялись. Город пал за двое суток.\n'
                     'Ты прятался в подвале, пока не кончилась еда. Сегодня ночью старая рация наконец ожила — '
                     'кто-то ещё жив. И у них есть вертолёт.'),
        start_objective=S('Доберись до полицейского участка в конце улицы'),
        start_event=NP('Story/Intro'), default_weapons=PSA(['knife', 'pistol']), default_ammo='{"pistol": 24}'))
    L.setup(night_env(L), MOON)
    Z0, Z1 = 14.0, -152.0
    # road and sidewalks (flush with the road so the player never snags on a curb)
    L.floor('asphalt', -6, 6, Z0, Z1)
    L.floor('sidewalk', -9, -6, Z0, Z1)
    L.floor('sidewalk', 6, 9, Z0, Z1)
    for z in range(10, -150, -6):  # lane markings
        L.decor((0.15, 0.01, 2.5), (0, 0.005, z), 'paint_white')
    # buildings (facades towards the road), alleys at z -66..-74
    left = [(14, -10, 10, 'brick'), (-10, -40, 14, 'plaster'), (-40, -66, 9, 'brick_dark'),
            (-74, -100, 12, 'plaster_gray'), (-100, -128, 10, 'brick')]
    right = [(14, -18, 12, 'plaster_gray'), (-18, -44, 9, 'brick'), (-44, -66, 13, 'plaster'),
             (-74, -104, 10, 'brick_dark'), (-104, -128, 11, 'plaster')]
    for side, rows in ((-1, left), (1, right)):
        for z0, z1, h, mat in rows:
            x0, x1 = (9, 21) if side > 0 else (-21, -9)
            L.blk(mat, (12, h, z0 - z1), ((x0 + x1) / 2, h / 2, (z0 + z1) / 2))
            fx = x0 - 0.03 if side > 0 else x1 + 0.03
            for row in range(int((h - 1.5) // 3.2)):
                y = 2.4 + row * 3.2
                n = int((z0 - z1 - 1) // 3.5)
                for i in range(n):
                    z = z1 + 1.75 + i * 3.5 + ((z0 - z1) - n * 3.5) / 2
                    lit = L.rnd.random() < 0.1
                    L.decor((0.06, 1.5, 1.1), (fx, y, z), 'window_lit' if lit else 'window_dark', cast_shadow=0)
        # alley floor + back wall
        ax = 15 * side
        L.floor('asphalt', ax - 6, ax + 6, -66, -74)
        L.wall_x(21.5 * side, -66, -74, 'brick_dark', h=8, t=1.0)
    # start: dead end behind the player
    L.wall_z(Z0 + 0.5, -9, 9, 'concrete', h=3, t=1.0)
    L.prop('res://scenes/world/bus.tscn', (0, 0, 11.5), 1.45)
    # street furniture
    for i, z in enumerate(range(4, -128, -18)):
        side = -1 if i % 2 == 0 else 1
        scene = 'street_lamp_flicker' if i in (2, 5) else 'street_lamp'
        L.prop(f'res://scenes/world/{scene}.tscn', (8.2 * side, 0, z), -math.pi / 2 * side)
    for pos, rot in [((-7.5, 0, -6), 0.0), ((7.5, 0, -33), 0.0), ((-7.6, 0, -62), 0.0), ((7.6, 0, -95), 0.0)]:
        L.prop('res://scenes/world/dumpster.tscn', pos, math.pi / 2)
    for pos in [(-8, 0, -20), (-8.2, 0, -20.8), (8, 0, -58), (-14, 0, -68), (16, 0, -71), (8.2, 0, -110)]:
        L.prop('res://scenes/world/barrel.tscn', pos)
    # cars
    cars = [('car_red', (-3.0, 0, -2), 0.45), ('car_white', (3.8, 0, -16), -0.15), ('car_black', (-3.8, 0, -27), 0.1),
            ('car_blue', (-1.6, 0, -38), 1.45), ('car_white', (3.2, 0, -39.5), 1.3), ('police_car', (4.2, 0, -55), 0.25),
            ('car_red', (-4.2, 0, -78), -0.3), ('car_black', (3.5, 0, -100), 0.6), ('police_car', (-3.5, 0, -122), 1.2),
            ('police_car', (4.0, 0, -125), -1.3)]
    for scene, pos, rot in cars:
        L.prop(f'res://scenes/world/{scene}.tscn', pos, rot)
    L.fire((-3.0, 1.2, -2))
    L.prop('res://scenes/world/bus.tscn', (0.0, 0, -88), 1.4)
    L.fire((1.5, 3.2, -88))
    L.blk('concrete', (3.0, 0.9, 0.6), (7.5, 0.45, -39), rot=(0, 0.2, 0))  # jersey barrier
    for x in (-5, -2.5, 2.5, 5):  # police barricade in front of the station
        L.blk('concrete', (2.2, 0.9, 0.6), (x, 0.45, -116), rot=(0, L.rnd.uniform(-0.3, 0.3), 0))
    # police station
    L.blk('plaster_gray', (42, 10, 22), (0, 5, -141))
    L.decor((4.0, 3.2, 0.3), (0, 1.6, -129.9), 'dark')
    L.decor((42.2, 0.6, 0.4), (0, 9.7, -129.9), 'police_blue')
    L.node('Sign', 'Label3D', 'Decor', position=V3(0, 6.5, -129.8), text=S('ПОЛИЦИЯ'), font_size=200,
           pixel_size=0.01, modulate=C(0.45, 0.65, 1.0), outline_size=0)
    L.omni((0, 6, -128), (0.4, 0.6, 1.0), 2.0, 10, flicker=True)
    L.omni((0, 3.5, -127), (1, 0.85, 0.6), 1.5, 8)
    L.door('StationDoor', (3.0, 3.0, 0.2), (0, 1.5, -129.6), 'police_blue', event='Exit',
           prompt='Войти в участок', open_offset=V3(0, 0, -0.01), open_time=0.1, player_can_open=False,
           event_unlocks=True, locked_message='Сначала разберись с Мясником')

    # zombies
    for kind, pos in [('walker', (-2, 0, -14)), ('walker', (2.5, 0, -22)), ('walker', (-4.5, 0, -31)),
                      ('walker', (0, 0, -44)), ('walker', (-5, 0, -47)), ('runner', (4.5, 0, -46)),
                      ('walker', (1.5, 0, -60)), ('walker', (-6.5, 0, -58)), ('walker', (-1, 0, -80)),
                      ('walker', (5, 0, -82)), ('runner', (-6, 0, -84)), ('walker', (4, 0, -96)),
                      ('walker', (-3, 0, -98)), ('walker', (0, 0, -110)), ('walker', (6, 0, -119)),
                      ('walker', (-6.5, 0, -125))]:
        L.zombie(kind, pos)
    L.zombie('butcher', (0, 0, -125), math.pi, name='Butcher', sight_range=14.0,
             alert_event=NP('../../Story/ButcherAppears'), death_event=NP('../../Story/ButcherDead'))
    # pickups
    L.pickup('ammo_pistol', (7.0, 0, -12))
    L.pickup('medkit', (-7.5, 0, -50))
    L.pickup('weapon_rifle', (2.0, 0, -54.5), event=NP('../../Story/RifleFound'))
    L.pickup('ammo_rifle', (-13, 0, -71))
    L.pickup('ammo_pistol', (-7.2, 0, -90))
    L.pickup('medkit', (7.3, 0, -104))
    L.pickup('ammo_rifle', (0.5, 0, -120))
    L.pickup('ammo_pistol', (-7.6, 0, -121))
    L.pickup('ammo_rifle', (7.6, 0, -112))

    # story
    D = 'Диспетчер'
    L.event('Intro', speaker=D, duration=7, message='…если кто-то слышит — эвакуация со стадиона «Динамо» на рассвете. '
            'Повторяю: стадион, на рассвете.', targets=['Story/Intro2'])
    L.event('Intro2', delay=7.5, speaker=D, duration=8,
            message='Ты меня слышишь? Хорошо. Через центр не пройти — иди по Садовой к полицейскому участку. '
                    'Там оружейная, она тебе понадобится.')
    L.trigger('KnifeHintTrigger', (0, 1.5, -9), (18, 3, 2), 'KnifeHint')
    L.event('KnifeHint', speaker=D, duration=7,
            message='Совет: нож бьёт бесшумно. Выстрелы слышно на весь квартал — мертвецы сбегутся.')
    L.event('RifleFound', speaker=D, duration=7, objective='Отбейся от толпы из переулков',
            message='Автомат? Отличная находка. Только… слышишь? Они лезут из переулков!',
            targets=['Story/AlleyLeft', 'Story/AlleyRight'])
    L.spawner('AlleyLeft', [(-17, 0, -70), (-19, 0, -68)], ['walker', 'walker', 'runner'], 6, interval=1.0)
    L.spawner('AlleyRight', [(17, 0, -70), (19, 0, -72)], ['walker', 'walker', 'runner'], 6, interval=1.1,
              on_cleared='AlleyCleared')
    L.event('AlleyCleared', speaker=D, objective='Доберись до полицейского участка',
            message='Тихо? Двигай дальше, участок сразу за автобусом.')
    L.trigger('AmbushTrigger', (0, 1.5, -104), (18, 3, 2), 'Ambush')
    L.event('Ambush', speaker=D, duration=6, objective='Беги к полицейскому участку',
            message='Сзади! Целая толпа — беги к участку!', targets=['Story/Horde'])
    L.spawner('Horde', [(-3, 0, -62), (3, 0, -64), (0, 0, -60)], ['runner', 'walker', 'walker'], 6, interval=0.9)
    L.trigger('ButcherTrigger', (0, 1.5, -112), (18, 3, 2), 'WakeButcher')
    L.event('WakeButcher', targets=['Zombies/Butcher'])
    L.event('ButcherAppears', speaker=D, duration=8, objective='Убей Мясника',
            message='У входа в участок… повар с тесаком? Он не человек уже. Осторожно, он бросается с разбега — '
                    'отходи в сторону, а если врежется в стену, бей!')
    L.event('ButcherDead', speaker=D, objective='Войди в полицейский участок',
            message='Готов! Заходи в участок, пока толпа не догнала.', targets=['Doors/StationDoor'])
    L.event('Exit', complete=True)

    L.finish((0, 0, 8))
    L.save('scenes/levels/level_1_outskirts.tscn')


# =================================================================== CHAPTER 2
def level_2():
    L = LevelBuilder('Station', dict(
        chapter_number=2, chapter_title=S('Участок'),
        intro_text=S('Дверь участка захлопнулась за спиной. Внутри тихо — слишком тихо.\n'
                     'Где-то здесь оружейная. Если повезёт, там найдётся то, что поможет пережить эту ночь.'),
        start_objective=S('Найди ключ-карту от оружейной'), start_event=NP('Story/Intro'),
        default_weapons=PSA(['knife', 'pistol', 'rifle']), default_ammo='{"pistol": 24, "rifle": 90}'))
    env = dict(background_mode=1, background_color=C(0, 0, 0), ambient_light_source=2,
               ambient_light_color=C(0.12, 0.13, 0.17), ambient_light_energy=0.5, tonemap_mode=3, ssao_enabled=True,
               glow_enabled=True, glow_intensity=0.8, glow_bloom=0.04, fog_enabled=True,
               fog_light_color=C(0.02, 0.02, 0.03), fog_density=0.03)
    L.setup(env, dict(rotation=V3(-0.9, 0.6, 0), light_color=C(0.55, 0.62, 0.85), light_energy=0.25,
                      shadow_enabled=True))
    W, WI = 'wall_interior', 'plaster_gray'
    # floors & ceiling
    L.floor('tile', -14, 20, 1, -61)
    L.floor('concrete', 20, 34, -40, -56)  # back yard
    L.blk('concrete', (34.6, 0.4, 62), (3, 4.2, -30), name='Ceiling')
    # outer & room walls (height 4)
    L.wall_z(0, -10, -1.5, W); L.wall_z(0, 1.5, 10, W)
    L.wall_x(-10, 0, -14, W); L.wall_x(10, 0, -14, W)
    L.wall_z(-14, -14, -2, W); L.wall_z(-14, 2, 20, W)
    L.wall_x(-14, -14, -50, W)
    L.wall_x(-2, -14, -20, W); L.wall_x(-2, -22.5, -38, W); L.wall_x(-2, -40.5, -50, W)   # corridor west
    L.wall_z(-29, -14, -2, W)                                                              # office / lockers
    L.wall_x(2, -14, -18, W); L.wall_x(2, -21, -40, W); L.wall_x(2, -42.5, -50, W)         # corridor east
    L.wall_z(-50, -14, -2, W); L.wall_z(-50, 2, 6, W)                                      # north end
    L.wall_x(-6, -50, -60, W); L.wall_x(6, -50, -60, W); L.wall_z(-60, -6, 6, W)           # armory
    L.wall_z(-34, 2, 20, W)                                                                # cells / garage
    L.wall_x(18, -14, -34, W); L.wall_x(20, -14, -34, W)
    L.wall_x(20, -34, -44, WI); L.wall_x(20, -52, -60, WI)                                 # garage east (shutter gap)
    L.wall_z(-60, 6, 20, WI)
    # cells: dividers + back
    L.wall_z(-20.6, 13, 18, W); L.wall_z(-27.3, 13, 18, W)
    L.wall_x(13, -14, -14.6, W); L.wall_x(13, -33.4, -34, W)
    # yard walls
    L.wall_z(-40, 20, 34, 'brick_dark', h=5); L.wall_z(-56, 20, 34, 'brick_dark', h=5)
    L.wall_x(34, -40, -56, 'brick_dark', h=5)

    # doors
    L.door('EntranceDoor', (3.0, 3.0, 0.2), (0, 1.5, 0), 'police_blue', player_can_open=False,
           locked_message='Снаружи слишком много мертвецов')
    L.door('ArmoryDoor', (4.0, 3.2, 0.25), (0, 1.6, -50), 'metal', event='ArmoryOpened', required_key='armory',
           locked_message='Нужна ключ-карта оружейной', prompt='Открыть оружейную', open_offset=V3(0, 3.0, 0))
    L.door('GarageDoor', (0.25, 3.2, 2.5), (2, 1.6, -41.25), 'metal', player_can_open=False,
           locked_message='Заблокировано', open_offset=V3(0, 3.0, 0))
    for i, (z0, z1) in enumerate([(-14.6, -20.6), (-20.6, -27.3), (-27.3, -33.4)]):
        L.door(f'Cell{i + 1}', (0.12, 3.6, z0 - z1), (13, 1.8, (z0 + z1) / 2), 'bars', player_can_open=False,
               locked_message='Камера заперта', open_offset=V3(0, 3.4, 0), open_time=0.6)
    L.door('Shutter', (0.3, 4.0, 8.0), (20, 2.0, -48), 'metal_rust', event='ShutterOpened',
           prompt='Поднять ворота', open_offset=V3(0, 3.7, 0), open_time=2.5)

    # furniture
    L.prop('res://scenes/world/desk.tscn', (-4, 0, -9), 0.0)
    L.prop('res://scenes/world/desk.tscn', (4, 0, -9), 0.0)
    L.blk('wood', (6, 1.1, 0.6), (0, 0.55, -6), name='Reception')
    L.prop('res://scenes/world/desk.tscn', (-8, 0, -24), math.pi / 2)       # office
    L.prop('res://scenes/world/shelf.tscn', (-13.5, 0, -18), math.pi / 2)
    L.prop('res://scenes/world/shelf.tscn', (-13.5, 0, -26), math.pi / 2)
    for z in (-31, -33, -35, -42, -44):
        L.prop('res://scenes/world/lockers.tscn', (-13.6, 0, z), math.pi / 2)
    L.blk('wood', (1.0, 0.45, 5.0), (-8, 0.22, -38), name='Bench')
    for x in (-5, -1, 3):
        L.prop('res://scenes/world/shelf.tscn', (x, 0, -59.4), 0.0)
    L.prop('res://scenes/world/police_car.tscn', (10, 0, -40), 0.0)
    L.prop('res://scenes/world/car_black.tscn', (14.5, 0, -56), 1.5)
    for pos in [(18, 0, -37), (18.8, 0, -37.8), (8, 0, -58.5), (17, 0, -44)]:
        L.prop('res://scenes/world/barrel.tscn', pos)
    L.prop('res://scenes/world/shelf.tscn', (7.0, 0, -36), math.pi / 2)
    L.prop('res://scenes/world/car_red.tscn', (28, 0, -48), 1.57)

    # lights
    L.ceiling_lamp(-4, -5); L.ceiling_lamp(4, -10, flicker=True)
    L.ceiling_lamp(0, -18, flicker=True, name='CorridorLamp1'); L.ceiling_lamp(0, -30, energy=1.2, name='CorridorLamp2')
    L.ceiling_lamp(0, -44, flicker=True, name='CorridorLamp3')
    L.ceiling_lamp(-8, -21, flicker=True)
    L.ceiling_lamp(-8, -40, energy=0.8, flicker=True)
    L.ceiling_lamp(8, -24, flicker=True, name='CellLamp')
    L.ceiling_lamp(0, -55, energy=2.5)
    L.ceiling_lamp(11, -46, flicker=True, name='GarageLamp1'); L.ceiling_lamp(13, -56, energy=1.5)
    L.omni((27, 4, -48), (1, 0.8, 0.55), 2.0, 12)
    L.fire((31, 0.0, -53))
    L.node('Alarm', 'AudioStreamPlayer3D', 'Decor', position=V3(0, 3.5, -30), stream=L.sound('alarm'),
           unit_size=20.0, volume_db=-4.0, script=L.ext_res('Script', 'res://scripts/world/sound_trigger.gd'))

    # zombies
    L.zombie('walker', (-6, 0, -20)); L.zombie('walker', (-10, 0, -26))                  # office
    L.zombie('walker', (-9, 0, -34)); L.zombie('runner', (-6, 0, -46))                   # lockers
    L.zombie('walker', (0.5, 0, -27))                                                    # corridor
    for i, z in enumerate((-16.5, -18.5, -23, -25.5, -29.5, -32)):                       # cells
        L.zombie('walker' if i % 3 else 'runner', (15.5 + (i % 2) * 1.5, 0, z), name=f'Prisoner{i + 1}')
    L.zombie('walker', (8, 0, -18)); L.zombie('walker', (6, 0, -30))
    L.zombie('walker', (12, 0, -52)); L.zombie('runner', (9, 0, -55))                   # garage
    L.zombie('warden', (30, 0, -44), math.pi / 2, name='Warden', sight_range=12.0,
             alert_event=NP('../../Story/WardenAppears'), death_event=NP('../../Story/WardenDead'))
    L.zombie('walker', (16, 0, -40))

    # pickups
    L.pickup('keycard', (-8.2, 0.8, -24.3), event=NP('../../Story/CardFound'))
    L.pickup('ammo_pistol', (4, 0.8, -9))
    L.pickup('medkit', (-12.5, 0, -36))
    L.pickup('ammo_rifle', (-12.5, 0, -46))
    L.pickup('weapon_bazooka', (0, 0, -57), event=NP('../../Story/Alarm'))
    L.pickup('ammo_rocket', (-4, 0, -57.5))
    L.pickup('ammo_rocket', (4, 0, -57.5))
    L.pickup('ammo_rifle', (2.5, 0, -54))
    L.pickup('medkit', (-2.5, 0, -54))
    L.pickup('medkit', (17, 0, -58))
    L.pickup('ammo_rifle', (18.5, 0, -55))

    D = 'Диспетчер'
    L.event('Intro', speaker=D, duration=8, targets=['Story/Intro2'],
            message='Ты внутри? Хорошо. Оружейная в конце коридора, но она под ключ-картой. '
                    'Проверь кабинет начальника — первая дверь слева.')
    L.event('Intro2', delay=8.5, speaker=D, duration=5, message='И включи фонарик — клавиша F. Там темно, как в могиле.')
    L.event('CardFound', speaker=D, objective='Открой оружейную в конце коридора',
            message='Карта у тебя? Отлично, теперь в оружейную.')
    L.event('ArmoryOpened', speaker=D, objective='Забери оружие', message='Бери всё, что унесёшь.')
    L.event('Alarm', speaker=D, duration=8, objective='Прорвись через гараж и подними ворота',
            message='Чёрт, это сигнализация! Замки камер открылись! Уходи через гараж — ворота в восточной стене!',
            targets=['Decor/Alarm', 'Doors/Cell1', 'Doors/Cell2', 'Doors/Cell3', 'Doors/GarageDoor',
                     'Lights/CorridorLamp1', 'Lights/CorridorLamp3', 'Lights/CellLamp', 'Lights/GarageLamp1',
                     'Story/LobbyHorde', 'Story/AlertPrisoners'])
    L.event('AlertPrisoners', delay=1.0, targets=[f'Zombies/Prisoner{i}' for i in range(1, 7)])
    L.spawner('LobbyHorde', [(-6, 0, -3), (6, 0, -3), (0, 0, -4)], ['walker', 'walker', 'runner'], 8, interval=1.2)
    L.event('ShutterOpened', targets=['Zombies/Warden'])
    L.event('WardenAppears', speaker=D, duration=9, objective='Убей Надзирателя',
            message='Во дворе машина… и охранник со щитом! Щит держит пули — целься в голову, заходи сбоку '
                    'или стреляй из РПГ.')
    L.event('WardenDead', speaker=D, objective='Садись в машину во дворе', message='Чисто! Машина ждёт — давай!',
            targets=['Story/ExitTrigger'])
    L.trigger('ExitTrigger', (30, 1.5, -48), (4, 3, 14), 'Exit', enabled=False)
    L.event('Exit', complete=True)

    L.finish((0, 0, -2), ambience_db=-14.0)
    L.save('scenes/levels/level_2_station.tscn')


# =================================================================== CHAPTER 3
def level_3():
    L = LevelBuilder('Stadium', dict(
        chapter_number=5, chapter_title=S('Стадион'),
        intro_text=S('Лестница метро выводит прямо к южным воротам стадиона.\n'
                     'Над трибунами горят прожекторы. Где-то там, в темноте, гудит вертолёт.'),
        start_objective=S('Доберись до вертолётной площадки в центре поля'), start_event=NP('Story/Intro'),
        default_weapons=PSA(['knife', 'pistol', 'shotgun', 'rifle', 'bazooka']),
        default_ammo='{"pistol": 24, "shells": 16, "rifle": 120, "rocket": 3}'))
    L.setup(night_env(L, fog=0.014, ambient=0.9, horizon=(0.14, 0.09, 0.11)),
            dict(MOON, light_energy=0.55))
    # field, running track
    L.floor('grass', -35, 35, 55, -55)
    L.floor('concrete', -41, -35, 61, -61); L.floor('concrete', 35, 41, 61, -61)
    L.floor('concrete', -35, 35, 61, 55); L.floor('concrete', -35, 35, -55, -61)
    for x in (-34.8, 34.8):  # field lines
        L.decor((0.12, 0.01, 110), (x, 0.01, 0), 'paint_white')
    for z in (-54.8, 0, 54.8):
        L.decor((70, 0.01, 0.12), (0, 0.01, z), 'paint_white')
    # stands: 4 steps per side with tunnel gaps (N/S: |x|<4, E/W: |z|<4)
    for i in range(4):
        h, d = 1.2 * (i + 1), 3.0
        for sx in (-1, 1):  # west / east stands along z, with gap at |z|<4
            x = sx * (41 + d / 2 + i * d)
            for z0, z1 in ((-61, -4), (4, 61)):
                L.blk('stands', (d, h, z1 - z0), (x, h / 2, (z0 + z1) / 2))
        for sz in (-1, 1):  # north / south stands along x, gap at |x|<4
            z = sz * (61 + d / 2 + i * d)
            for x0, x1 in ((-53, -4), (4, 53)):
                L.blk('stands', (x1 - x0, h, d), ((x0 + x1) / 2, h / 2, z))
    # tunnels through the gaps (floors, walls, roof), each closed at the far end except the south one
    for name, horizontal in (('N', False), ('S', False), ('E', True), ('W', True)):
        sign = {'N': -1, 'S': 1, 'E': 1, 'W': -1}[name]
        if horizontal:
            L.floor('concrete', sign * 41, sign * 53, -4, 4)
            L.wall_z(-4.15, sign * 41, sign * 53, 'concrete', h=5); L.wall_z(4.15, sign * 41, sign * 53, 'concrete', h=5)
            L.blk('concrete', (12, 0.5, 8.6), (sign * 47, 5.25, 0))
        else:
            far = 73.5
            L.floor('concrete', -4, 4, sign * 61, sign * far)
            L.wall_x(-4.15, sign * 61, sign * far, 'concrete', h=5); L.wall_x(4.15, sign * 61, sign * far, 'concrete', h=5)
            L.blk('concrete', (8.6, 0.5, far - 61), (0, 5.25, sign * (61 + far) / 2))
        L.omni((sign * 47, 3.5, 0) if horizontal else (0, 3.5, sign * 66), (1, 0.6, 0.4), 1.5, 10, flicker=True)
    # outer wall behind the stands
    L.wall_z(-74, -53, 53, 'concrete', h=8, t=1); L.wall_z(74, -53, 53, 'concrete', h=8, t=1)
    L.wall_x(-53.5, -74, 74, 'concrete', h=8, t=1); L.wall_x(53.5, -74, 74, 'concrete', h=8, t=1)

    # helipad
    L.decor((14, 0.02, 14), (0, 0.01, 0), 'concrete')
    for size, pos in [((0.6, 0.03, 6), (-1.6, 0.02, 0)), ((0.6, 0.03, 6), (1.6, 0.02, 0)), ((2.6, 0.03, 0.6), (0, 0.02, 0))]:
        L.decor(size, pos, 'paint_yellow')
    for x, z in [(-7, -7), (7, -7), (-7, 7), (7, 7)]:
        L.decor((0.3, 0.15, 0.3), (x, 0.08, z), 'taillight')
        L.omni((x, 0.6, z), (1, 0.15, 0.1), 1.0, 4)
    # military camp: sandbag rings around the pad with gaps
    for size, pos in [((6, 1.0, 1.0), (-6, 0.5, -10)), ((6, 1.0, 1.0), (6, 0.5, 10)), ((1.0, 1.0, 6), (-10, 0.5, 6)),
                      ((1.0, 1.0, 6), (10, 0.5, -6)), ((4, 1.0, 1.0), (7, 0.5, -11)), ((4, 1.0, 1.0), (-7, 0.5, 11))]:
        L.blk('sandbag', size, pos)
    for pos, rot in [((-18, 0, -18), 0.3), ((-22, 0, -8), -0.2), ((17, 0, 20), 0.1), ((24, 0, 12), 0.5)]:
        L.blk('tent', (4, 2.6, 5), (pos[0], 1.3, pos[2]), rot=(0, rot, 0))
    for pos, rot in [((20, 0, -16), 0.4), ((-24, 0, 20), -0.3)]:  # army trucks
        L.blk('military', (2.6, 2.4, 3.0), (pos[0], 1.2, pos[2]), rot=(0, rot, 0))
        L.blk('tent', (2.7, 2.8, 5.0), (pos[0] + math.sin(rot) * 4, 1.4, pos[2] + math.cos(rot) * 4), rot=(0, rot, 0))
    for pos in [(-12, 0, 16), (12.5, 0, -15), (-15, 0, -3), (16, 0, 3), (-3, 0, 22), (3, 0, -22)]:
        L.blk('crate', (1.4, 1.4, 1.4), (pos[0], 0.7, pos[2]), rot=(0, L.rnd.uniform(0, 1.5), 0))
    for pos in [(-11.5, 0, 17.5), (13.2, 0, -16.4), (8, 0, 25), (-26, 0, -25), (27, 0, -26)]:
        L.prop('res://scenes/world/barrel.tscn', pos)
    L.prop('res://scenes/world/car_white.tscn', (-28, 0, 32), 0.8)
    L.prop('res://scenes/world/police_car.tscn', (29, 0, 34), -0.6)
    L.fire((-24, 2.4, 20))
    L.fire((26, 0.1, -34))
    # floodlights in the corners, aimed at the centre
    for x, z in [(-38, -58), (38, -58), (-38, 58), (38, 58)]:
        L.prop('res://scenes/world/floodlight_tower.tscn', (x, 0, z), math.atan2(x, z), parent='Decor')

    # zombies on the field
    for kind, pos in [('walker', (-8, 0, 40)), ('walker', (6, 0, 34)), ('walker', (12, 0, 28)), ('runner', (-15, 0, 26)),
                      ('walker', (-4, 0, 14)), ('walker', (18, 0, 8)), ('walker', (-20, 0, -4)), ('runner', (9, 0, -20)),
                      ('walker', (-10, 0, -30)), ('walker', (22, 0, -30))]:
        L.zombie(kind, pos)

    # supplies (respawning during the siege)
    for kind, pos, t in [('ammo_rifle', (-3, 0, -3), 25.0), ('ammo_rifle', (3, 0, 3), 25.0), ('medkit', (-8, 0, 8), 40.0),
                         ('medkit', (8, 0, -8), 40.0), ('ammo_rocket', (-17, 0, -12), 45.0), ('ammo_pistol', (17, 0, 14), 30.0),
                         ('ammo_rocket', (21, 0, -12), 45.0), ('ammo_shells', (-17, 0, 14), 30.0),
                         ('ammo_shells', (12, 0, -20), 30.0)]:
        L.pickup(kind, pos, respawn_time=t)

    L.prop('res://scenes/world/helicopter.tscn', (0, 0, 0), 0.0, parent='.', name='Helicopter')

    D, P = 'Диспетчер', 'Пилот'
    L.event('Intro', speaker=D, duration=7,
            message='Ты на стадионе? Вертолёт на подходе. Площадка в центре поля — жди там.')
    L.trigger('PadTrigger', (0, 1.5, 0), (12, 3, 12), 'Siege')
    L.event('Siege', speaker=P, duration=9, objective='Продержись до прилёта вертолёта',
            message='Борт-двенадцать на связи. Вижу площадку, но вокруг толпа — сесть не могу! '
                    'Продержись две минуты, я сделаю круг.', targets=['Story/Holdout'])
    L.node('Holdout', 'Node', 'Story', script=L.ext_res('Script', 'res://scripts/story/holdout.gd'), duration=120.0,
           spawners=NPS(['../SpawnNorth', '../SpawnEast', '../SpawnWest', '../SpawnSouth']),
           boss_spawner=NP('../SpawnBoss'), boss_time=55.0, boss_event=NP('../BossWarning'),
           boss_text=S('Убей Колосса! Вертолёт не сядет'), on_finished=NP('../HeliArrives'))
    mix = ['walker', 'walker', 'walker', 'runner']
    L.spawner('SpawnNorth', [(-2, 0, -66), (2, 0, -68)], mix, 0, interval=2.6, continuous=True, max_alive=6)
    L.spawner('SpawnEast', [(52, 0, -2), (50, 0, 2)], mix, 0, interval=3.2, continuous=True, max_alive=5)
    L.spawner('SpawnWest', [(-52, 0, 2), (-50, 0, -2)], mix, 0, interval=3.2, continuous=True, max_alive=5)
    L.spawner('SpawnSouth', [(-2, 0, 63), (2, 0, 64)], mix, 0, interval=5.0, continuous=True, max_alive=3)
    L.spawner('SpawnBoss', [(0, 0, -67)], ['colossus'], 1, interval=0.1)
    L.event('BossWarning', speaker=D, duration=9,
            message='С севера идёт что-то огромное… Это Колосс! Он швыряет обломки и бьёт о землю — '
                    'прыгай, когда замахивается. Пока он жив, вертолёт не сядет!')
    L.event('HeliArrives', speaker=P, duration=7, objective='Вертолёт садится — держись!',
            message='Захожу на посадку! Держись, я почти над тобой!', targets=['Helicopter', 'Story/HeliLanded'])
    L.event('HeliLanded', delay=9.5, speaker=P, objective='Садись в вертолёт!', message='Сел! Запрыгивай, живо!',
            targets=['Story/BoardTrigger'])
    L.trigger('BoardTrigger', (0, 1.5, 0), (8, 3, 8), 'Exit', enabled=False)
    L.event('Exit', complete=True)

    L.finish((0, 0, 70))
    L.save('scenes/levels/level_5_stadium.tscn')


INTERIOR_ENV = dict(background_mode=1, background_color=C(0, 0, 0), ambient_light_source=2,
                    ambient_light_color=C(0.1, 0.11, 0.14), ambient_light_energy=0.5, tonemap_mode=3, ssao_enabled=True,
                    glow_enabled=True, glow_intensity=0.8, glow_bloom=0.04, fog_enabled=True,
                    fog_light_color=C(0.02, 0.02, 0.03), fog_density=0.03)


# =================================================================== CHAPTER 3
def level_hospital():
    L = LevelBuilder('Hospital', dict(
        chapter_number=3, chapter_title=S('Больница'),
        intro_text=S('Машина заглохла у ворот городской больницы. Мост к стадиону забит брошенными машинами — '
                     'остаётся метро, а вход в него сразу за больницей.\n'
                     'Внутри темно и тихо. Слишком тихо для места, где лечили сотни людей.'),
        start_objective=S('Запусти генератор в техническом крыле, чтобы открыть пожарный выход'),
        start_event=NP('Story/Intro'), default_weapons=PSA(['knife', 'pistol', 'rifle', 'bazooka']),
        default_ammo='{"pistol": 24, "rifle": 90, "rocket": 2}'))
    L.setup(night_env(L, fog=0.02, ambient=0.5), MOON)
    H = 'hospital_wall'
    # parking lot in front, yard behind the fire exit
    L.floor('asphalt', -20, 20, 14, 0)
    L.wall_z(14.5, -20, 20, 'concrete', h=3, t=1)
    L.wall_x(-20.5, 14, 0, 'concrete', h=3, t=1)
    L.wall_x(20.5, 14, 0, 'concrete', h=3, t=1)
    L.floor('asphalt', -36, -24, -8, -26)
    L.wall_z(-7.5, -36.5, -24, 'brick_dark', h=3.5, t=1)
    L.wall_z(-26.5, -36.5, -24, 'brick_dark', h=3.5, t=1)
    L.wall_x(-36.5, -8, -26, 'brick_dark', h=3.5, t=1)
    # building: floor, ceiling, walls (height 4)
    L.floor('linoleum', -24, 24, 0, -31)
    L.floor('concrete', -24.15, 24.15, 0.15, -31.15, top=4.4, thick=0.4)
    L.wall_z(0, -24, -2.5, 'plaster'); L.wall_z(0, 2.5, 24, 'plaster')
    L.wall_x(-12, 0, -14, H); L.wall_x(12, 0, -14, H)
    L.wall_z(-14, -24, -3, H); L.wall_z(-14, 3, 24, H)
    L.wall_x(-24, -14, -15.5, H); L.wall_x(-24, -17.5, -31, H); L.wall_x(24, -14, -31, H)
    for x0, x1 in ((-24, -19), (-17, -7), (-5, 5), (7, 17), (19, 24)):
        L.wall_z(-19, x0, x1, H)
    for x in (-12, 0, 12):
        L.wall_x(x, -19, -31, H)
    L.wall_z(-31, -24, 24, H)
    L.decor((0.06, 0.6, 2.6), (-23.8, 3.4, -16.5), 'siren_red', cast_shadow=0)  # EXIT sign
    L.node('ExitSign', 'Label3D', 'Decor', position=V3(-23.7, 3.4, -16.5), rotation=V3(0, math.pi / 2, 0),
           text=S('ВЫХОД'), font_size=64, pixel_size=0.006, modulate=C(0.4, 1.0, 0.5))
    # metro entrance in the yard's west wall
    L.decor((0.1, 2.6, 2.6), (-35.95, 1.3, -17), 'dark')
    L.node('MetroSign', 'Label3D', 'Decor', position=V3(-35.85, 3.2, -17), rotation=V3(0, math.pi / 2, 0),
           text=S('М  МЕТРО'), font_size=80, pixel_size=0.008, modulate=C(1.0, 0.25, 0.2))
    L.omni((-34.5, 3.0, -17), (1, 0.5, 0.4), 1.2, 6)
    L.door('FireDoor', (0.3, 3.0, 2.0), (-24, 1.5, -16.5), 'metal', player_can_open=False,
           locked_message='Электрозамок — нет питания', open_offset=V3(0, 0, -2.0), open_time=1.0)

    # lobby: reception, benches, security post
    L.blk('wood', (6, 1.1, 0.8), (0, 0.55, -7), name='Reception')
    L.blk('wood', (0.8, 1.1, 3), (-3.4, 0.55, -5.5), name='ReceptionSide')
    for x in (-9, -6, 6):
        L.blk('wood', (2.4, 0.45, 0.6), (x, 0.22, -2.5))
    L.prop('res://scenes/world/desk.tscn', (9, 0, -11), math.pi / 2, name='SecurityDesk')
    L.prop('res://scenes/world/lockers.tscn', (11.6, 0, -8), -math.pi / 2)
    # wards: three beds each
    for cx in (-18, -6, 6):
        for i, dx in enumerate((-3.5, 0, 3.5)):
            L.prop('res://scenes/world/bed.tscn', (cx + dx, 0, -28.6), math.pi)
            L.decor((0.04, 2.2, 2.4), (cx + dx + 1.7, 1.3, -28.4), 'sheet', cast_shadow=0)  # curtain
    # technical wing: generator, shelves, barrels
    L.blk('metal', (3.0, 1.8, 1.6), (20.5, 0.9, -28.5), name='Generator')
    L.blk('dark', (0.6, 0.6, 1.6), (18.7, 1.2, -28.5), name='GeneratorPanel')
    L.door('GeneratorSwitch', (0.12, 0.5, 0.5), (18.35, 1.3, -28.2), 'siren_red', event='PowerOn',
           prompt='Запустить генератор', open_offset=V3(0, -0.08, 0), open_time=0.3)
    L.prop('res://scenes/world/shelf.tscn', (23.4, 0, -22), -math.pi / 2)
    L.prop('res://scenes/world/shelf.tscn', (23.4, 0, -24), -math.pi / 2)
    for pos in [(14, 0, -30), (14.8, 0, -30.2), (13.5, 0, -21)]:
        L.prop('res://scenes/world/barrel.tscn', pos)
    # outside: the car from the station yard, an ambulance, a fire
    L.prop('res://scenes/world/car_red.tscn', (3, 0, 5), 0.9)
    L.fire((3, 1.2, 5))
    L.prop('res://scenes/world/car_white.tscn', (-9, 0, 7), 0.25)
    L.decor((1.9, 0.25, 4.3), (-9, 1.05, 7), 'siren_red', rot=(0, 0.25, 0))
    L.prop('res://scenes/world/car_blue.tscn', (12, 0, 9), -1.2)
    L.prop('res://scenes/world/street_lamp_flicker.tscn', (-15, 0, 12), math.pi)
    L.prop('res://scenes/world/street_lamp.tscn', (15, 0, 12), math.pi)
    L.omni((0, 3.4, -1), (1, 0.85, 0.6), 1.2, 8)

    # light: dim red emergency lamps now, ceiling lights when the power is back
    for pos in [(0, 3.6, -10), (-18, 3.6, -16.5), (0, 3.6, -16.5), (18, 3.6, -16.5), (21, 3.6, -25)]:
        L.omni(pos, (1, 0.15, 0.1), 0.8, 7, flicker=True)
    power = []
    for x, z in [(-6, -4), (6, -4), (-6, -10), (6, -10), (-20, -16.5), (-12, -16.5), (-4, -16.5), (4, -16.5),
                 (12, -16.5), (20, -16.5), (-18, -25), (-6, -25), (6, -25), (18, -25)]:
        name = f'Ceiling{len(power) + 1}'
        L.ceiling_lamp(x, z, energy=2.0, rng=9.0, name=name, power=True)
        power.append('Lights/' + name)
    L.node('Alarm', 'AudioStreamPlayer3D', 'Decor', position=V3(0, 3.5, -16.5), stream=L.sound('alarm'),
           unit_size=25.0, volume_db=-6.0, script=L.ext_res('Script', 'res://scripts/world/sound_trigger.gd'))

    # zombies: the lobby, wards (patients), the technical wing
    for kind, pos in [('walker', (-6, 0, -9)), ('walker', (7, 0, -4)), ('walker', (-14, 0, -17))]:
        L.zombie(kind, pos)
    patients = []
    for i, (kind, pos) in enumerate([('walker', (-20, 0, -24)), ('walker', (-15, 0, -27)), ('runner', (-8, 0, -23)),
                                     ('walker', (-3, 0, -26)), ('walker', (4, 0, -24)), ('walker', (9, 0, -27)),
                                     ('runner', (16, 0, -23)), ('walker', (22, 0, -21))]):
        L.zombie(kind, pos, name=f'Patient{i + 1}')
        patients.append(f'Zombies/Patient{i + 1}')

    # pickups
    L.pickup('weapon_shotgun', (9, 0.8, -11), event=NP('../../Story/ShotgunFound'))
    L.pickup('ammo_shells', (10.5, 0, -12.8))
    L.pickup('ammo_shells', (-9.5, 0, -29.5))
    L.pickup('medkit', (-2.5, 0, -29.5))
    L.pickup('ammo_pistol', (-2, 1.1, -7))
    L.pickup('ammo_rifle', (22.5, 0, -30))
    L.pickup('medkit', (10.5, 0, -29.5))
    L.pickup('medkit', (-25.5, 0, -24.5))
    L.pickup('ammo_shells', (-25.5, 0, -9.5))
    L.zombie('patient_zero', (-33, 0, -17), -math.pi / 2, name='PatientZero', sight_range=11.0,
             alert_event=NP('../../Story/PatientZeroAppears'), death_event=NP('../../Story/PatientZeroDead'))

    D = 'Диспетчер'
    L.event('Intro', speaker=D, duration=9, targets=['Story/Intro2'],
            message='Больница? Плохо, но другого пути нет. Пожарный выход в западном крыле на электрозамке — '
                    'сначала запусти генератор, он в техническом крыле, на востоке.')
    L.event('Intro2', delay=9.5, speaker=D, duration=6, message='Свет отключён. Фонарик — F. И лишний раз не шуми.')
    L.event('ShotgunFound', speaker=D, duration=6,
            message='Дробовик охраны! В тесных коридорах лучше не придумаешь. Клавиша 3.')
    L.event('PowerOn', speaker=D, duration=8, objective='Беги к пожарному выходу в западном конце коридора',
            message='Есть питание! Чёрт… сирена подняла всё здание. Пожарная дверь открыта — беги!',
            targets=power + ['Decor/Alarm', 'Doors/FireDoor', 'Story/WardHorde', 'Story/LobbyHorde'] + patients)
    L.spawner('WardHorde', [(-18, 0, -23), (-6, 0, -23), (6, 0, -23)], ['walker', 'walker', 'runner'], 7, interval=1.0)
    L.spawner('LobbyHorde', [(-2, 0, 6), (2, 0, 8)], ['runner', 'walker'], 5, interval=1.3)
    L.trigger('YardTrigger', (-26.5, 1.5, -17), (3, 3, 8), 'WakePatientZero')
    L.event('WakePatientZero', targets=['Zombies/PatientZero'])
    L.event('PatientZeroAppears', speaker=D, duration=8, objective='Убей Пациента Ноль',
            message='Во дворе… оно светится?! Это нулевой пациент, с него всё началось. '
                    'Не попадай под его плевки и не дай ему созвать больных!')
    L.event('PatientZeroDead', speaker=D, objective='Спускайся в метро',
            message='Он мёртв. Вход в метро в углу двора — иди!', targets=['Story/ExitTrigger'])
    L.trigger('ExitTrigger', (-34.5, 1.5, -17), (3, 3, 5), 'Exit', enabled=False)
    L.event('Exit', complete=True)

    L.finish((0, 0, 9))
    L.save('scenes/levels/level_3_hospital.tscn')


# =================================================================== CHAPTER 4
def level_subway():
    L = LevelBuilder('Subway', dict(
        chapter_number=4, chapter_title=S('Метро'),
        intro_text=S('Станция «Больничная». Эскалаторы стоят, турникеты погнуты, на стенах — выцветшие объявления '
                     'об эвакуации.\nДо «Динамо» два перегона по тоннелю. Поезда давно не ходят. Наверное.'),
        start_objective=S('Пройди по тоннелю до станции «Динамо»'), start_event=NP('Story/Intro'),
        default_weapons=PSA(['knife', 'pistol', 'shotgun', 'rifle', 'bazooka']),
        default_ammo='{"pistol": 24, "shells": 16, "rifle": 90, "rocket": 2}'))
    L.setup(INTERIOR_ENV)
    T, C_ = 'subway_tile', 'concrete'

    def rails(x, z0, z1):
        for dx in (-0.75, 0.75):
            L.decor((0.12, 0.12, abs(z1 - z0)), (x + dx, 0.06, (z0 + z1) / 2), 'rail', cast_shadow=0)

    # vestibule
    L.floor('concrete', -8, 8, 1, -12)
    L.wall_z(0.5, -8, 8, C_, t=1)
    L.wall_x(-8, 0, -12, T); L.wall_x(8, 0, -12, T)
    for x in (-6, -4, -2, 2, 4, 6):
        L.blk('metal', (0.3, 1.0, 1.4), (x, 0.5, -8))
    L.blk('dark', (4, 2.5, 0.5), (0, 1.25, 0.1), name='Rubble')
    L.node('StationSign', 'Label3D', 'Decor', position=V3(0, 3.2, -11.9), text=S('БОЛЬНИЧНАЯ'), font_size=96,
           pixel_size=0.01, modulate=C(0.85, 0.85, 0.9))
    # platform hall "Bolnichnaya": platform in the middle, tracks on both sides
    L.floor('subway_tile', -4, 4, -12, -60)
    L.floor('concrete', -10, -4, -12, -60); L.floor('concrete', 4, 10, -12, -60)
    L.wall_z(-12, -10, -8, T); L.wall_z(-12, 8, 10, T)
    L.wall_x(-10, -12, -60, T); L.wall_x(10, -12, -60, T)
    L.wall_z(-60, -4, 10, T)
    for x in (-4.05, 4.05):
        L.decor((0.1, 0.02, 48), (x, 0.01, -36), 'paint_yellow', cast_shadow=0)
    for z in range(-18, -58, -8):
        for x in (-3.6, 3.6):
            L.blk('subway_tile', (0.8, 4.0, 0.8), (x, 2.0, z))
    rails(-7, -12, -60)
    rails(7, -12, -60)
    # parked train on the right track
    L.blk('train_red', (2.9, 3.0, 24), (7, 1.55, -34), name='Train')
    for z in range(-44, -23, 4):
        L.decor((0.05, 0.9, 2.4), (5.53, 2.0, z), 'glass', cast_shadow=0)
    # tunnel along the left track, with a derailed car blocking it
    L.floor('concrete', -10, -4, -60, -130)
    L.wall_x(-10, -60, -88, C_); L.wall_x(-10, -90, -102, C_); L.wall_x(-10, -104, -130, C_)
    L.wall_x(-4, -60, -130, C_)
    rails(-7, -60, -130)
    L.blk('train_gray', (5.9, 3.2, 12), (-7, 1.6, -96), rot=(0, 0.04, 0.06), name='Derailed')
    for z in (-70, -80, -110, -122):
        L.blk('dark', (1.2, 0.8, 1.6), (-8.6 + (z % 3) * 0.5, 0.4, z), rot=(0, 0.4, 0))
    # service corridor around the blockage
    L.floor('concrete', -16, -10, -86, -106)
    L.wall_x(-16, -86, -106, C_)
    L.wall_z(-86, -16, -10, C_); L.wall_z(-106, -16, -10, C_)
    L.door('ServiceDoor', (0.25, 3.0, 2.0), (-10, 1.5, -89), 'metal_rust', event='Bypass',
           prompt='Открыть служебную дверь', open_offset=V3(0, 2.9, 0), open_time=1.0)
    for z in (-93, -97):
        L.prop('res://scenes/world/lockers.tscn', (-15.6, 0, z), math.pi / 2)
    # station "Dinamo"
    L.floor('subway_tile', -4, 4, -130, -172)
    L.floor('concrete', -10, -4, -130, -172); L.floor('concrete', 4, 10, -130, -172)
    L.wall_z(-130, -4, 10, T)
    L.wall_x(-10, -130, -172, T)
    L.wall_x(10, -130, -148, T); L.wall_x(10, -154, -172, T)
    L.wall_z(-172, -10, -3, T); L.wall_z(-172, 3, 10, T)
    for z in range(-136, -170, -8):
        for x in (-3.6, 3.6):
            L.blk('subway_tile', (0.8, 4.0, 0.8), (x, 2.0, z))
    rails(-7, -130, -172)
    rails(7, -130, -172)
    L.node('DinamoSign', 'Label3D', 'Decor', position=V3(9.9, 3.0, -160), rotation=V3(0, -math.pi / 2, 0),
           text=S('ДИНАМО'), font_size=110, pixel_size=0.01, modulate=C(0.85, 0.85, 0.9))
    # side passage (zombies pour in from here during the siege)
    L.floor('concrete', 10, 16, -147, -155)
    L.wall_z(-147, 10, 16, C_); L.wall_z(-155, 10, 16, C_); L.wall_x(16, -147, -155, C_)
    # exit stairs behind the gate
    L.floor('concrete', -3, 3, -172, -182)
    L.wall_x(-3, -172, -182, C_); L.wall_x(3, -172, -182, C_); L.wall_z(-182, -3, 3, C_, t=1)
    L.door('Gate', (6.0, 4.0, 0.12), (0, 2.0, -172), 'bars', player_can_open=False,
           locked_message='Решётка заперта', open_offset=V3(0, 3.8, 0), open_time=2.0)
    # one ceiling for everything (tiled)
    L.floor('concrete', -10.2, 10.2, 1, -60, top=4.4, thick=0.4)
    L.floor('concrete', -16.2, -3.9, -60, -130, top=4.4, thick=0.4)
    L.floor('concrete', -10.2, 16.2, -130, -182, top=4.4, thick=0.4)

    # lights
    for z in (-4, -9):
        L.ceiling_lamp(-3, z); L.ceiling_lamp(3, z, flicker=(z == -9))
    for i, z in enumerate(range(-16, -60, -8)):
        L.ceiling_lamp(0, z, flicker=i % 3 == 1, energy=1.8)
    for z in range(-66, -130, -12):
        L.omni((-4.4, 3.4, z), (1, 0.25, 0.15), 1.2, 9, flicker=True)
    L.omni((-13, 3.5, -96), (1, 0.8, 0.5), 1.2, 8, flicker=True)
    for i, z in enumerate(range(-134, -172, -8)):
        L.ceiling_lamp(0, z, flicker=i % 2 == 0, energy=1.8)
    L.omni((0, 3.5, -178), (1, 0.9, 0.7), 1.5, 8)

    # zombies
    for kind, pos in [('walker', (-1, 0, -24)), ('walker', (2, 0, -35)), ('walker', (-7, 0, -44)),
                      ('walker', (-2, 0, -52)), ('walker', (-7, 0, -72)), ('walker', (-6, 0, -84)),
                      ('walker', (-13, 0, -95)), ('runner', (-13, 0, -101)), ('walker', (-6, 0, -118)),
                      ('walker', (1, 0, -145)), ('walker', (-6, 0, -158))]:
        L.zombie(kind, pos)

    # pickups
    L.pickup('ammo_shells', (-1, 0, -15))
    L.pickup('medkit', (2.5, 0, -50))
    L.pickup('ammo_rifle', (-14.5, 0, -100))
    L.pickup('ammo_shells', (-14.5, 0, -88))
    L.pickup('medkit', (-5, 0, -126))
    for kind, pos in [('ammo_shells', (-2, 0, -150)), ('ammo_rifle', (2, 0, -150)), ('medkit', (0, 0, -165))]:
        L.pickup(kind, pos, respawn_time=25.0)
    L.pickup('ammo_rocket', (-8.5, 0, -168))

    D = 'Диспетчер'
    L.event('Intro', speaker=D, duration=8,
            message='Ты в метро? До «Динамо» два перегона. Иди по левому пути — правый перекрыт составом.')
    L.trigger('BlockageTrigger', (-7, 1.5, -83), (6, 3, 2), 'Blockage')
    L.event('Blockage', speaker=D, duration=7, objective='Найди обход завала',
            message='Впереди сошедший вагон, тоннель перекрыт. Ищи служебную дверь — они есть через каждые сто метров.')
    L.event('Bypass', objective='Пройди служебным коридором')
    L.trigger('AmbushTrigger', (-7, 1.5, -108), (6, 3, 2), 'Ambush')
    L.event('Ambush', speaker=D, duration=6, objective='Беги к станции «Динамо»',
            message='Слышишь топот? Сзади бегуны — не останавливайся!', targets=['Story/Runners'])
    L.spawner('Runners', [(-7, 0, -64), (-7, 0, -68)], ['runner', 'runner', 'walker'], 6, interval=0.9)
    L.trigger('GateTrigger', (0, 1.5, -142), (20, 3, 4), 'GateSiege')
    L.event('GateSiege', speaker=D, duration=8, objective='Продержись, пока диспетчер открывает решётку',
            message='Выход перекрыт решёткой. Взламываю систему станции — продержись минуту!', targets=['Story/Holdout'])
    L.node('Holdout', 'Node', 'Story', script=L.ext_res('Script', 'res://scripts/story/holdout.gd'), duration=60.0,
           timer_text=S('Решётка откроется через %s'),
           spawners=NPS(['../TunnelSpawn', '../PassageSpawn']), boss_spawner=NP('../SpawnBoss'), boss_time=20.0,
           boss_event=NP('../LinemanWarning'), boss_text=S('Убей Обходчика!'), on_finished=NP('../GateOpen'))
    mix = ['walker', 'walker', 'runner']
    L.spawner('TunnelSpawn', [(-7, 0, -122), (-7, 0, -126)], mix, 0, interval=3.0, continuous=True, max_alive=5)
    L.spawner('PassageSpawn', [(14, 0, -150), (14, 0, -152)], mix, 0, interval=3.5, continuous=True, max_alive=4)
    L.spawner('SpawnBoss', [(14, 0, -151)], ['lineman'], 1, interval=0.1)
    L.event('LinemanWarning', speaker=D, duration=9,
            message='По боковому проходу идёт что-то тяжёлое… Обходчик с кувалдой! Когда он бьёт по земле — '
                    'подпрыгни, ударная волна идёт по полу.')
    L.event('GateOpen', speaker=D, duration=6, objective='Поднимайся к выходу',
            message='Есть! Решётка поднята — наверх, стадион прямо над тобой!', targets=['Doors/Gate', 'Story/ExitTrigger'])
    L.trigger('ExitTrigger', (0, 1.5, -179), (6, 3, 5), 'Exit', enabled=False)
    L.event('Exit', complete=True)

    L.finish((0, 0, -3), ambience_db=-12.0)
    L.save('scenes/levels/level_4_subway.tscn')


if __name__ == '__main__':
    level_1()
    level_2()
    level_hospital()
    level_subway()
    level_3()
    print('levels ok')
