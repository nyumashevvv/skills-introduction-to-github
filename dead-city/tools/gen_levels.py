"""Generates the five chapters of Dead City. Run from the project root."""
import math
import random
from tscn import *

ZOMBIE = {k: f'res://scenes/zombies/{k}.tscn' for k in
          ('walker', 'runner', 'brute', 'soldier', 'bloater', 'spitter', 'butcher', 'warden', 'patient_zero', 'lineman',
           'colossus')}
PICKUP = {k: f'res://scenes/pickups/{k}.tscn' for k in
          ('medkit', 'ammo_pistol', 'ammo_rifle', 'ammo_rocket', 'ammo_shells', 'weapon_rifle', 'weapon_shotgun',
           'weapon_bazooka', 'keycard', 'weapon_revolver', 'weapon_smg', 'weapon_sniper', 'weapon_grenade', 'ammo_magnum',
           'ammo_smg', 'ammo_sniper')}
NAV = 'NavigationRegion3D'


PROP = 'res://scenes/props/{}.tscn'
VEHICLE = 'res://scenes/world/vehicles/{}.tscn'
FACING = {'+x': -math.pi / 2, '-x': math.pi / 2, '+z': math.pi, '-z': 0.0}


def is_solid(kind):
    """Props with a collision shape go under the navigation region so zombies path around them."""
    with open(f'scenes/props/{kind}.tscn') as f:
        return 'type="StaticBody3D"' in f.read()


def story_rel(path):
    """Path from a node directly under Story to a root-relative path."""
    return '../' + path[6:] if path.startswith('Story/') else '../../' + path


class LevelBuilder(Scene):
    def __init__(self, root_name, props, script='res://scripts/story/level.gd'):
        super().__init__()
        self.count = {}
        self.rnd = random.Random(root_name)
        if script:
            # The script must come first: Godot drops properties it does not know yet.
            props = dict(script=self.ext_res('Script', script), **props)
        self.node(root_name, 'Node3D', **props)

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

    def shell(self, x0, x1, z0, z1, h, mat, floor_mat='tile', gaps=(), inner_h=4.0):
        """A hollow ground floor inside a building block: perimeter walls (with door gaps), floor, ceiling and the
        solid upper storeys above. gaps: (side, centre, width) with side 'x0' / 'x1' (walls at x) or 'z0' / 'z1'."""
        t = 0.3
        self.floor(floor_mat, x0, x1, z0, z1, top=0.01, thick=0.2)
        self.blk(mat, (abs(x1 - x0), h - inner_h, abs(z1 - z0)), ((x0 + x1) / 2, inner_h + (h - inner_h) / 2, (z0 + z1) / 2))
        for side in ('x0', 'x1', 'z0', 'z1'):
            fixed = {'x0': x0, 'x1': x1, 'z0': z0, 'z1': z1}[side]
            lo, hi = (min(z0, z1), max(z0, z1)) if side[0] == 'x' else (min(x0, x1), max(x0, x1))
            cuts = sorted((c - w / 2, c + w / 2) for sd, c, w in gaps if sd == side)
            start = lo
            for c0, c1 in cuts + [(hi, hi)]:
                if c0 - start > 0.05:
                    if side[0] == 'x':
                        self.wall_x(fixed, start, c0, mat, h=inner_h, t=t)
                    else:
                        self.wall_z(fixed, start, c0, mat, h=inner_h, t=t)
                if c1 < hi:  # lintel over the door
                    size = (t, inner_h - 3.0, c1 - c0) if side[0] == 'x' else (c1 - c0, inner_h - 3.0, t)
                    pos = (fixed, 3.0 + (inner_h - 3.0) / 2, (c0 + c1) / 2) if side[0] == 'x' else ((c0 + c1) / 2, 3.0 + (inner_h - 3.0) / 2, fixed)
                    self.blk(mat, size, pos)
                start = c1

    def fancy_door(self, name, pos, along, face, sign='', sign_color=(1.0, 0.85, 0.4), glass=True, width=1.8,
                   mat='door_steel', lamp=True, **props):
        """A door dressed like the police station's: frame, window, handles, a lamp and a sign over it.
        along: 'x' or 'z' (the axis the door spans); face: the side players arrive from ('+x', '-x', '+z', '-z')."""
        x, y, z = pos
        size = (width, 2.95, 0.14) if along == 'x' else (0.14, 2.95, width)
        props.setdefault('swing_degrees', 100.0)
        self.door(name, size, (x, 1.475, z), mat, **props)
        d = 'Doors/' + name
        n = 1.0 if face[0] == '+' else -1.0
        off = lambda a, b: (a, 0, 0.08 * b) if along == 'x' else (0.08 * b, 0, a)
        pane = 'door_glass_lit' if glass else 'glass'
        p = off(0, 1)
        self.box(self.uid('Pane'), d, (width * 0.6, 1.2, 0.02) if along == 'x' else (0.02, 1.2, width * 0.6),
                 (p[0], 0.55, p[2]), pane, cast_shadow=0)
        for side in (-1, 1):
            q = off(width * 0.32, side)
            self.box(self.uid('Handle'), d, (0.18, 0.05, 0.05) if along == 'x' else (0.05, 0.05, 0.18), (q[0], -0.1, q[2]), 'chrome')
        self.dress_door(pos, along, face, sign, sign_color, width, lamp)

    def dress_door(self, pos, along, face, sign='', sign_color=(1.0, 0.85, 0.4), width=1.8, lamp=True):
        """Frame, lamp and sign around a door opening (static decoration)."""
        x, y, z = pos
        n = 1.0 if face[0] == '+' else -1.0
        for s_ in (-1, 1):
            jamb = (x + s_ * (width / 2 + 0.07), 1.55, z) if along == 'x' else (x, 1.55, z + s_ * (width / 2 + 0.07))
            self.decor((0.14, 3.1, 0.36) if along == 'x' else (0.36, 3.1, 0.14), jamb, 'dark')
        # The header hangs 3 cm below the lintel so their undersides do not z-fight.
        self.decor((width + 0.28, 0.19, 0.36) if along == 'x' else (0.36, 0.19, width + 0.28), (x, 3.065, z), 'dark')
        out = (0, 0, 0.22 * n) if along == 'x' else (0.22 * n, 0, 0)
        if lamp:
            self.decor((0.5, 0.06, 0.2) if along == 'x' else (0.2, 0.06, 0.5), (x + out[0], 3.3, z + out[2]), 'lamp_glow',
                       cast_shadow=0)
            self.omni((x + out[0] * 3, 2.9, z + out[2] * 3), (1, 0.88, 0.7), 1.4, 6.0)
        if sign:
            rot = {'+z': 0.0, '-z': math.pi, '+x': math.pi / 2, '-x': -math.pi / 2}[face]
            self.node(self.uid('Sign'), 'Label3D', 'Decor', position=V3(x + out[0] * 1.2, 3.7, z + out[2] * 1.2),
                      rotation=V3(0, rot, 0), text=S(sign), font_size=72, pixel_size=0.008, modulate=C(*sign_color),
                      outline_size=8)

    NEON = {'pink': (1.0, 0.15, 0.55), 'cyan': (0.15, 0.85, 1.0), 'green': (0.2, 1.0, 0.35), 'red': (1.0, 0.08, 0.06),
            'blue': (0.25, 0.4, 1.0), 'yellow': (1.0, 0.75, 0.15), 'white': (0.9, 0.95, 1.0)}
    FACE_ROT = {'+z': 0.0, '-z': math.pi, '+x': math.pi / 2, '-x': -math.pi / 2}

    def neon(self, text, pos, face, color, font=110, frame=True, flicker=False, light=True, pixel=0.01):
        """A glowing neon sign on a facade: bright letters over a dark board, a neon tube frame and a coloured light
        spilling onto the street. face: the way the sign looks ('+x', '-x', '+z', '-z')."""
        x, y, z = pos
        c = self.NEON[color]
        n = {'+z': (0, 0, 1), '-z': (0, 0, -1), '+x': (1, 0, 0), '-x': (-1, 0, 0)}[face]
        lines = text.split('\n')
        w = max(len(t) for t in lines) * font * pixel * 0.62 + 0.5
        h = font * pixel * (1.25 + 1.42 * (len(lines) - 1)) + 0.2
        along = (lambda a, b, d: (a, b, d)) if face[1] == 'z' else (lambda a, b, d: (d, b, a))
        self.decor(along(w, h, 0.08), (x - n[0] * 0.02, y, z - n[2] * 0.02), 'dark', cast_shadow=0)
        if frame:
            for dy in (-h / 2, h / 2):
                self.decor(along(w, 0.05, 0.05), (x + n[0] * 0.04, y + dy, z + n[2] * 0.04), f'neon_{color}', cast_shadow=0)
            for s_ in (-1, 1):
                o = along(s_ * w / 2, 0, 0)
                self.decor(along(0.05, h, 0.05), (x + o[0] + n[0] * 0.04, y, z + o[2] + n[2] * 0.04), f'neon_{color}',
                           cast_shadow=0)
        self.node(self.uid('Neon'), 'Label3D', 'Decor', position=V3(x + n[0] * 0.06, y, z + n[2] * 0.06),
                  rotation=V3(0, self.FACE_ROT[face], 0), text=S(text), font_size=font, pixel_size=pixel,
                  modulate=C(*(min(1.0, k * 1.6) for k in c)), outline_size=10, outline_modulate=C(*c, 0.5))
        if light:
            self.omni((x + n[0] * 1.5, y, z + n[2] * 1.5), c, 1.6, 8.0, flicker=flicker)

    def blade(self, text, wall_x, out, y, z, color, font=80, flicker=False):
        """A vertical sign hanging out of a facade at wall_x (out: +1 / -1, the way the facade faces), letters stacked
        top to bottom and facing up the street (+z), so it reads from far away."""
        w = font * 0.01 * 0.62 + 0.5
        h = font * 0.01 * (1.25 + 1.42 * (len(text) - 1)) + 0.2
        cx = wall_x + out * (w / 2 + 0.3)
        self.neon('\n'.join(text), (cx, y, z), '+z', color, font=font, flicker=flicker)
        for dy in (-h / 2 + 0.2, h / 2 - 0.2):  # brackets into the wall
            self.decor((w + 0.3, 0.07, 0.07), (wall_x + out * (w + 0.3) / 2, y + dy, z), 'dark')

    def cross(self, pos, face, mat, size=2.0, depth=0.25):
        """A glowing cross (hospital, pharmacy) facing `face`; for a sign that sticks out of a wall use depth along it."""
        x, y, z = pos
        t = size * 0.32
        if face[1] == 'z':
            self.decor((size, t, depth), (x, y, z), mat, cast_shadow=0)
            self.decor((t, size, depth), (x, y, z), mat, cast_shadow=0)
        else:
            self.decor((depth, t, size), (x, y, z), mat, cast_shadow=0)
            self.decor((depth, size, t), (x, y, z), mat, cast_shadow=0)

    def clutter(self, kind, pos, rot_y=None):
        """A prop from scenes/props at (x, y, z); random heading unless given."""
        if rot_y is None:
            rot_y = self.rnd.uniform(-math.pi, math.pi)
        self.prop(PROP.format(kind), pos, rot_y, parent=NAV if is_solid(kind) else 'Decor')

    def on_wall(self, kind, pos, facing):
        """A wall-mounted prop (posters, boards, clocks) whose front looks along `facing` ('+x', '-z', ...)."""
        self.prop(PROP.format(kind), pos, FACING[facing] or 0.0001, parent='Decor')

    def scatter(self, kinds, x0, x1, z0, z1, count, y=0.0):
        """Small floor clutter at random spots in a rectangle."""
        for _ in range(count):
            self.clutter(self.rnd.choice(kinds), (self.rnd.uniform(x0, x1), y, self.rnd.uniform(z0, z1)))

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


def street_1_backyard(L):
    """Chapter 1 side areas: the back yard behind the shop, the cafe, the grocery shop and the pharmacy."""
    c, H = L.clutter, math.pi / 2
    # back yard (x -33.5..-21) reached through the left alley or the shop's back door; a second alley at
    # z -100..-104 leads back to the street past the bus
    L.floor('asphalt', -33.5, -21, -66, -104)
    L.floor('asphalt', -21, -9, -100, -104)
    L.wall_x(-33.8, -65.6, -104.4, 'brick_dark', h=7, t=0.6)
    L.wall_z(-65.6, -33.8, -21, 'brick_dark', h=7, t=0.6)
    L.wall_z(-104.4, -33.8, -21, 'brick_dark', h=7, t=0.6)
    L.prop('res://scenes/world/dumpster.tscn', (-32.6, 0, -70), H)
    L.prop('res://scenes/world/dumpster.tscn', (-32.6, 0, -73), H)
    L.prop(VEHICLE.format('sedan_burnt'), (-27.5, 0, -84), 0.2)
    L.fire((-27.5, 1.0, -84))
    for z in (-77, -78.33, -79.66):
        c('fence_wood', (-25.0, 0, z), H)
    for kind, pos in [('trash_bags', (-30.5, 0, -68)), ('tyre_stack', (-32.8, 0, -99)), ('crate_large', (-22.2, 0, -91)),
                      ('box_pile', (-24.0, 0, -102.6)), ('barrel_open', (-32.6, 0, -88)), ('pallet', (-29.0, 0, -102.8)),
                      ('trash_bags', (-22.5, 0, -97.8)), ('rubble', (-28, 0, -94)), ('debris_door', (-26.0, 0, -88.5))]:
        c(kind, pos)
    L.omni((-27, 5.0, -75), (1, 0.75, 0.45), 1.6, 12, flicker=True)
    L.omni((-27, 5.0, -97), (1, 0.75, 0.45), 1.4, 11)
    for kind, pos in [('walker', (-29, 0, -76)), ('walker', (-24, 0, -98)), ('bloater', (-30, 0, -92)), ('walker', (-31, 0, -82))]:
        L.zombie(kind, pos)
    L.pickup('ammo_pistol', (-32.8, 0, -95))
    L.pickup('medkit', (-21.8, 0, -86))

    # cafe (x -21..-9, z -10..-26)
    L.fancy_door('CafeDoor', (-9, 0, -18), 'z', '+x', sign='КАФЕ «ВСТРЕЧА»', sign_color=(1, 0.75, 0.45))
    for i, z in enumerate((-11.0, -11.95, -12.9, -13.85)):
        c(['fridge', 'kitchen_cabinet', 'kitchen_sink', 'kitchen_stove'][i], (-20.4, 0, z), -H)
    c('coffee_machine', (-20.4, 0.95, -11.95), -H)
    for z in (-15.5, -16.4, -17.3):
        c('kitchen_bar', (-17.6, 0, z), H)
        c('stool_bar', (-16.7, 0, z), -H)
    for tx, tz in [(-12.5, -13), (-12.5, -21.5), (-16.5, -22.5)]:
        c('table_round', (tx, 0, tz), L.rnd.uniform(0, 3))
        for a in (0.4, 2.5, 4.4):
            c('chair_cushion' if L.rnd.random() < 0.7 else 'chair_fallen', (tx + math.cos(a) * 1.0, 0, tz + math.sin(a) * 1.0), -a - H)
        c('mug', (tx, 0.77, tz + 0.2))
    c('plant_tall', (-9.8, 0, -10.8)); c('plant_tall', (-9.8, 0, -25.2)); c('vase_broken', (-14, 0, -18))
    c('papers', (-11, 0, -17)); c('trash_can', (-20.3, 0, -25.3))
    L.ceiling_lamp(-15, -14, y=3.95, energy=1.4, rng=7.0); L.ceiling_lamp(-15, -22, y=3.95, flicker=True, energy=1.2, rng=7.0)
    L.pickup('weapon_grenade', (-17.6, 0.9, -16.4))
    L.pickup('ammo_pistol', (-20.0, 0, -24.0))
    L.zombie('walker', (-14.5, 0, -16.5)); L.zombie('walker', (-18.5, 0, -23.5))

    # grocery shop (x -21..-9, z -74..-100): front door on the street, back door into the yard
    L.fancy_door('ShopDoor', (-9, 0, -80), 'z', '+x', sign='ПРОДУКТЫ', sign_color=(0.5, 0.9, 1.0))
    L.fancy_door('ShopBackDoor', (-21, 0, -95), 'z', '-x', glass=False, sign='ВХОД ДЛЯ ПЕРСОНАЛА', sign_color=(0.9, 0.9, 0.85))
    for x in (-18.0, -14.6):
        for i in range(10):
            L.prop('res://scenes/world/shelf.tscn', (x + (0.26 if i % 2 else -0.26) * 0, 0, -77.0 - i * 1.25), H)
    for x in (-20.0, -18.6, -17.2, -15.8, -14.4):
        c('fridge', (x, 0, -74.6), 0.0)
    for z in (-84.5, -88.5):
        c('kitchen_bar', (-11.3, 0, z), -H); c('kitchen_bar', (-11.3, 0, z - 0.9), -H)
        c('box_closed', (-11.3, 0.88, z - 0.4))
    for kind, pos in [('box_pile', (-19.8, 0, -98.4)), ('crate_large', (-17.5, 0, -98.8)), ('box_open', (-15.6, 0, -98.6)),
                      ('trash_bags', (-12, 0, -98.5)), ('papers', (-16.3, 0, -83)), ('books_floor', (-13, 0, -92)),
                      ('cardboard_box', (-16.4, 0, -94.5)), ('trash_can', (-10, 0, -76))]:
        c(kind, pos)
    for x, z, flicker in [(-15, -78, False), (-15, -87, True), (-15, -96, False), (-11, -86, True)]:
        L.ceiling_lamp(x, z, y=3.95, flicker=flicker, energy=1.2, rng=7.0)
    L.pickup('ammo_pistol', (-16.3, 0, -90))
    L.pickup('ammo_rifle', (-19.6, 0, -86))
    for kind, pos in [('walker', (-16.3, 0, -79)), ('walker', (-19.5, 0, -91)), ('runner', (-12.5, 0, -95)), ('walker', (-12.5, 0, -78))]:
        L.zombie(kind, pos)

    # pharmacy (x 9..21, z -74..-90); the back office behind a partition hides the revolver
    L.fancy_door('PharmacyDoor', (9, 0, -82), 'z', '-x', sign='АПТЕКА', sign_color=(0.4, 1.0, 0.55))
    L.wall_x(16, -74, -85.6, 'hospital_wall', h=4.0, t=0.2); L.wall_x(16, -87.2, -90, 'hospital_wall', h=4.0, t=0.2)
    for x in (10.6, 12.0, 13.4, 14.8):
        L.prop('res://scenes/world/shelf.tscn', (x, 0, -74.5), 0.0)
        c('pills', (x, 0.82, -74.6))
    for z in (-79.5, -80.4, -81.3):
        c('kitchen_bar', (13.6, 0, z), H)
    c('pills', (13.6, 0.88, -80.4)); c('syringes', (13.6, 0.88, -79.6)); c('papers', (11.5, 0, -86))
    L.prop('res://scenes/world/desk.tscn', (18.6, 0, -80), H)
    c('office_chair', (19.6, 0, -80), -H); c('filing_cabinet', (20.5, 0, -76), -H); c('filing_cabinet', (20.5, 0, -76.6), -H)
    c('box_pile', (19.5, 0, -88.6)); c('trashcan_small', (16.6, 0, -76))
    L.ceiling_lamp(12, -79, y=3.95, energy=1.5, rng=7.0); L.ceiling_lamp(18.5, -83, y=3.95, flicker=True, energy=1.0, rng=6.0)
    L.pickup('medkit', (10.4, 0, -88.5)); L.pickup('medkit', (14.8, 0.82, -74.6))
    L.pickup('weapon_revolver', (18.6, 0.85, -80.3))
    L.pickup('ammo_magnum', (20.3, 0, -88.6))
    L.zombie('walker', (11.5, 0, -84)); L.zombie('spitter', (18.5, 0, -85.5))


def street_clutter(L):
    """The abandoned street: rubbish, luggage of people who fled, cones and wrecks along the sidewalks."""
    c = L.clutter
    small = ['trash_bags', 'newspaper', 'suitcase', 'tyre_flat', 'rubble', 'papers', 'backpack', 'suitcase_open']
    doors = [(-1, -18), (-1, -80), (1, -82)]  # keep the shop doors clear
    for i, z in enumerate(range(6, -126, -6)):
        side = -1 if i % 2 else 1
        c(L.rnd.choice(small), (side * L.rnd.uniform(6.6, 8.4), 0, z + L.rnd.uniform(-2, 2)))
        if i % 3 == 0 and not any(sd == -side and abs(z - 2.5 - dz) < 3 for sd, dz in doors):
            c(L.rnd.choice(['trash_can', 'bench', 'box_pile']), (-side * 8.4, 0, z - 2.5), -side * math.pi / 2)
        if i % 4 == 1:
            c(L.rnd.choice(['newspaper', 'rubble', 'papers', 'tyre_flat']), (L.rnd.uniform(-4.5, 4.5), 0, z + 1))
    for pos in [(-4.5, 0, -114.2), (4.6, 0, -114.4), (-6.3, 0, -117), (6.4, 0, -116.8), (3.6, 0, -42), (5.2, 0, -41)]:
        c('traffic_cone', pos)
    c('barrier', (-2.2, 0, -110), 0.15); c('barrier', (2.4, 0, -110.4), -0.2)
    # alleys
    L.prop('res://scenes/world/dumpster.tscn', (11, 0, -67.2), 0.0)
    L.prop('res://scenes/world/dumpster.tscn', (-11.2, 0, -72.8), math.pi)
    for pos in [(13, 0, -67), (-13.4, 0, -73), (15, 0, -73), (-15.5, 0, -67.5)]:
        c('trash_bags', pos)
    c('box_pile', (12.6, 0, -73.2)); c('tyre_stack', (-12.8, 0, -67.2)); c('pallet', (16.5, 0, -67.4), 0.1)
    # power poles, traffic lights, signs, roadworks
    for z in (-2, -38, -110):
        c('electricity_pole', (8.4, 0, z), 0.0)
    for z in (-20, -56, -92):
        c('electricity_pole', (-8.4, 0, z), 0.0)
    c('traffic_light', (6.6, 0, -65.2), math.pi / 2); c('traffic_light', (-6.6, 0, -74.8), -math.pi / 2)
    c('sign_stop', (8.5, 0, -75.5), math.pi / 2); c('sign_warning', (-8.5, 0, -44), -math.pi / 2)
    c('sign_street', (8.5, 0, -64.5), 0.0); c('sign_warning', (8.4, 0, -112), math.pi / 2)
    c('construction_barrier', (5.6, 0, -36.2), 0.2); c('construction_light', (6.2, 0, -41.6))
    c('construction_fence', (-7.6, 0, -114.6), math.pi / 2); c('construction_light', (-6.4, 0, -112.4))
    # car wreckage
    for kind, pos in [('debris_door', (-1.2, 0, -4.2)), ('debris_tire', (-5.2, 0, -0.4)), ('debris_bumper', (-2.2, 0, -81)),
                      ('debris_door_window', (-6.4, 0, -75.6)), ('debris_plate', (4.2, 0, -73)), ('debris_spoiler', (0.6, 0, -68.6)),
                      ('debris_tire', (6.4, 0, -9.5)), ('debris_axle', (1.6, 0, -73.6)), ('debris_plate', (-1.5, 0, -90.5))]:
        c(kind, pos)
    for pos in [(-12.4, 0, -69.6), (13.4, 0, -70.2)]:
        c('barrel_open', pos)
    c('crate_large', (14.6, 0, -73.0), 0.2); c('crate_large_open', (-14.4, 0, -73.2), -0.3)


def hospital_clutter(L):
    """Hospital: lobby, corridor, three wards, the technical wing, the car park and the back yard."""
    c, w = L.clutter, L.on_wall
    H = math.pi / 2
    for pos in [(-11.3, 0, -0.8), (11.3, 0, -0.8), (-11.3, 0, -13.2)]:
        c('potted_plant', pos)
    c('wheelchair', (-6.6, 0, -9.6), 0.8); c('water_cooler', (-11.5, 0, -12.2), -H); c('vending_machine', (-11.4, 0, -9.5), -H)
    c('vase', (2.2, 1.1, -7.1)); c('pills', (-1.5, 1.1, -7.2)); c('phone', (0.6, 1.1, -7.2), 0.2)
    c('office_chair', (0.5, 0, -8.2), math.pi); c('chair_fallen', (4, 0, -4.5)); c('trash_can', (11.4, 0, -13.2))
    for pos in [(-7, 0, -4.5), (3, 0, -11.5), (-4.5, 0, -12)]:
        c(L.rnd.choice(['papers', 'newspaper', 'books_floor']), pos)
    w('noticeboard', (-6, 1.7, -13.83), '+z'); w('wall_clock', (6, 3.0, -13.82), '+z')
    c('lounge_sofa', (9.6, 0, -0.65), 0.0); c('lounge_chair', (-8.6, 0, -4.4), -H + 0.3); c('table_round', (8.0, 0, -4.8), 0.4)
    c('plant_tall', (-4.8, 0, -13.3)); c('coffee_machine', (-2.6, 1.1, -7.3), math.pi); c('tv_old', (-9.0, 0, -13.3), 0.0)
    # staff canteen (west side room)
    for i, z in enumerate((-1.2, -2.15, -3.1, -4.05)):
        c(['fridge', 'kitchen_stove', 'kitchen_sink', 'kitchen_cabinet'][i], (-23.35 if i == 0 else -23.4, 0, z), -H)
    c('microwave', (-23.4, 0.95, -4.05), -H); c('coffee_machine', (-23.4, 0.95, -3.1 + 0.5), -H)
    for tx, tz in [(-19, -5), (-15.5, -5), (-19, -10.5)]:
        c('table_round', (tx, 0, tz), L.rnd.uniform(0, 3))
        for a in (0.3, 2.0, 3.8):
            c('chair_cushion' if L.rnd.random() < 0.7 else 'chair_fallen', (tx + math.cos(a) * 1.1, 0, tz + math.sin(a) * 1.1), -a - H)
        c('mug', (tx + 0.2, 0.77, tz)); c('papers', (tx + 1.5, 0, tz + 1.2))
    c('lounge_sofa', (-15.0, 0, -13.4), math.pi); c('coffee_table', (-15.0, 0, -12.2), 0.0)
    c('vending_machine', (-23.4, 0, -8.0), -H); c('water_cooler', (-23.6, 0, -9.6), -H); c('trash_can', (-13.0, 0, -1.0))
    c('plant_tall', (-23.4, 0, -13.4)); c('tv_cabinet', (-20.0, 0, -13.6), math.pi); c('tv_old', (-20.0, 0.65, -13.6), math.pi)
    w('noticeboard', (-18.0, 1.7, -0.17), '-z'); w('wall_clock', (-23.83, 3.0, -11.0), '+x')
    # records office (east side room)
    for z in (-1.3, -3.1, -9.6, -11.4):
        c('bookcase_wide', (23.65, 0, z), H)
    for x in (14.0, 14.55, 15.1, 15.65):
        c('filing_cabinet', (x, 0, -0.5), 0.0)
    c('workstation', (18.0, 0, -6.5), 0.0); c('workstation', (18.0, 0, -11.5), 0.0); c('desk_corner', (13.5, 0, -12.6), math.pi)
    c('box_pile', (22.4, 0, -6.2), 0.4); c('box_open', (20.6, 0, -2.6), 0.5); c('box_closed', (21.2, 0, -3.3), 0.1)
    c('office_chair_fallen', (15.8, 0, -8.5)); c('chair_fallen', (21.0, 0, -9.0))
    for pos in [(16, 0, -3), (20, 0, -8.5), (14.5, 0, -6.5), (19, 0, -12.8)]:
        c(L.rnd.choice(['papers', 'books_floor', 'papers']), pos)
    w('whiteboard', (18.0, 1.6, -13.83), '+z'); w('wall_clock', (12.17, 3.0, -9.0), '+x')
    # corridor: gurneys along the wall, a wheelchair, drips, rubbish on the floor
    for x in (-15, 3.5, 14):
        c('gurney', (x, 0, -14.6), H)
    c('wheelchair', (-9, 0, -18.3), 2.5); c('iv_stand', (10.5, 0, -18.5)); c('iv_stand', (-3, 0, -14.6))
    for x in (-20, -11, -1, 9, 21):
        c(L.rnd.choice(['syringes_floor', 'papers', 'pills']), (x, 0, -16.8))
    # wards
    for cx in (-18, -6, 6):
        for dx in (-3.5, 0, 3.5):
            c('iv_stand', (cx + dx + 0.9, 0, -27.6))
        c('medical_cart', (cx - 3.6, 0, -20.0), 0.0)
        c('syringes_floor', (cx + 1, 0, -24)); c('pills', (cx - 2, 0, -25.4)); c('chair', (cx + 4.6, 0, -24.5), 0.4)
        w('wall_clock', (cx + 2.5, 3.0, -19.17), '-z')
        c('tv_cabinet', (cx - 4.85, 0, -19.6), 0.0); c('tv_old', (cx - 4.85, 0.65, -19.6), 0.0)
        c('sink', (cx + 5.2, 0, -30.4), math.pi); c('trashcan_small', (cx + 4.4, 0, -30.4))
    c('wheelchair', (-1.2, 0, -22.5), 1.0); c('vase_broken', (9.5, 0, -22))
    # technical wing
    c('toolbox', (15, 0, -29.6)); c('jerrycan', (16.2, 0, -30.3), 0.4); c('cardboard_box', (13.4, 0, -24.2))
    c('box_pile', (22.4, 0, -20.2), 0.2); c('car_battery', (19, 0, -26.3)); c('oil_stain', (20.5, 0, -26.5))
    c('barrel_open', (14.0, 0, -27.4)); c('crate_large', (16.8, 0, -21.0), 0.3); c('bucket', (15.0, 0, -28.2))
    # car park, yard
    for pos in [(-5, 0, 3), (-4, 0, 4.2), (16, 0, 4), (7.5, 0, 11.5)]:
        c('traffic_cone', pos)
    c('stretcher', (-6.5, 0, 9.5), 0.3); c('suitcase', (-12, 0, 4)); c('trash_bags', (18.8, 0, 12.8)); c('tyre', (8.5, 0, 3), 0.7)
    L.prop('res://scenes/world/dumpster.tscn', (-34.8, 0, -24.8), 0.0)
    c('trash_bags', (-35.2, 0, -9)); c('trash_bags', (-31.5, 0, -25.3)); c('box_pile', (-28.5, 0, -25.2), 0.4)
    c('syringes_floor', (-30, 0, -13)); c('rubble', (-27, 0, -21))
    c('barrel_open', (-25.2, 0, -9.0)); c('crate_large_open', (-35.4, 0, -12.5), 0.0)
    c('construction_barrier', (0, 0, 12.6), H); c('sign_warning', (19.5, 0, 1.0), -H)


def subway_clutter(L):
    """Subway: belongings of the people who waited for the last train, rubbish, debris in the tunnel."""
    c = L.clutter
    H = math.pi / 2
    c('vending_machine', (-7.4, 0, -3), -H); c('bench', (7.4, 0, -4), H); c('trash_can', (-7.3, 0, -10.8))
    c('suitcase', (5, 0, -10)); c('newspaper', (-3, 0, -5))
    stuff = ['suitcase', 'backpack', 'newspaper', 'trash_bags', 'suitcase_open', 'papers']
    for z0, z1 in ((-14, -58), (-132, -170)):
        for z in range(int(z0) - 8, int(z1), -16):
            c('bench', (0, 0, z), 0.0 if z % 32 else math.pi)
        for z in range(int(z0) - 4, int(z1), -8):
            c('trash_can', (2.8 if z % 16 else -2.8, 0, z))
        L.scatter(stuff, -3.2, 3.2, z1 + 2, z0 - 2, 10)
    L.scatter(['rubble', 'newspaper', 'trash_bags'], -9.3, -4.7, -126, -64, 9)
    c('toolbox', (-15.3, 0, -104.6)); c('cardboard_box', (-11.2, 0, -105.3), 0.2); c('box_pile', (-15, 0, -87.2), 0.0)
    c('traffic_cone', (-6, 0, -84.5)); c('traffic_cone', (-8, 0, -85)); c('barrier', (-7, 0, -86.6), 0.0)
    c('construction_light', (-9.4, 0, -83.6)); c('construction_fence', (-4.6, 0, -80.0), 0.0)
    c('metal_panel', (-9.6, 0, -70.0), H); c('crate_large', (-9.3, 0, -112.0), 0.0); c('bucket', (-5.0, 0, -100.5))
    for z in (-20, -44, -140, -164):
        c('radio' if z % 3 else 'bottle', (L.rnd.uniform(-2.5, 2.5), 0, z))


def stadium_clutter(L):
    """Stadium: what is left of the army camp around the helipad."""
    c = L.clutter
    for pos, rot in [((-15.5, 0, -16), 0.3), ((-19.5, 0, -5), -0.2), ((14.5, 0, 22), 0.1), ((21, 0, 14.5), 0.5)]:
        c('stretcher', pos, rot)
    for pos in [(-14, 0, -21), (21.5, 0, 9), (-26, 0, -6), (15, 0, 17)]:
        c('ammo_crates', pos)
    for pos in [(18, 0, -19), (-27, 0, 17), (9, 0, -24), (-9, 0, 24)]:
        c('box_pile', pos)
    for x in (-3.5, 3.5):
        for z in (-50, 50):
            c('traffic_cone', (x, 0, z))
    L.scatter(['backpack', 'suitcase', 'suitcase_open', 'trash_bags', 'newspaper', 'papers'], -30, 30, -45, 45, 22)
    c('barrier', (-2, 0, 52), 0.0); c('barrier', (2, 0, -52), 0.0)
    # survivors' corner: small tents around a campfire, a shelter, crates and fences
    for pos, rot in [((-27, 0, -2), 0.4), ((-25, 0, 3.5), 1.2), ((-30, 0, 2.5), -0.6), ((25, 0, -4), 2.6)]:
        c(L.rnd.choice(['tent_small', 'tent_canvas']), pos, rot)
    c('campfire_pit', (-26.8, 0, 1.2)); L.fire((-26.8, 0.15, 1.2))
    for pos in [(-28.2, 0, 0.4), (-25.4, 0, 0.0), (-27.5, 0, 2.6)]:
        c('bedroll', pos)
    c('canvas_shelter', (-22.0, 0, 16.0), 0.3); c('camp_workbench', (-20.4, 0, 15.4), 0.3); c('chest', (-21.8, 0, 18.0))
    for pos in [(22.5, 0, -21), (-27, 0, 23.5), (27.5, 0, 6), (-12, 0, 30)]:
        c('crate_large', pos)
    for i in range(5):
        c('fence_fortified', (-34.0, 0, -12 + i * 1.33), math.pi / 2)
        c('fence_fortified', (34.0, 0, 10 + i * 1.33), math.pi / 2)
    c('signpost', (-3.2, 0, 40), 0.3); c('construction_barrier', (-6, 0, -55), 0.0); c('construction_barrier', (6, 0, -55), 0.0)
    for x, z in [(-9.2, 9.2), (9.2, -9.2)]:
        c('construction_light', (x, 0, z))


def station_clutter(L):
    """Furnishes the police station: lobby, office, locker room, corridor, cells, garage, armory, yard."""
    c, w = L.clutter, L.on_wall
    H = math.pi / 2
    # extra lamps so the rooms (and what is in them) can be seen; some are dying
    for x, z, flicker in [(-6, -11.5, False), (6, -3, True), (-8, -17, False), (-6, -26.5, True), (-11, -24, False),
                          (-8, -32.5, False), (-8, -46, True), (5, -17, False), (9, -31, True), (4, -56, False)]:
        L.ceiling_lamp(x, z, flicker=flicker, energy=1.6, rng=8.0)
    for z in (-17.6, -24.0, -30.4):
        L.omni((15.5, 3.4, z), (0.9, 0.85, 0.7), 0.9, 5.0)
    # lobby
    for pos in [(-9.3, 0, -0.8), (9.3, 0, -0.8), (-9.3, 0, -13.2), (9.3, 0, -13.2)]:
        c('potted_plant', pos)
    c('water_cooler', (9.5, 0, -4.4), H)
    c('vending_machine', (9.35, 0, -7.4), H)
    c('filing_cabinet', (-9.55, 0, -11.2), -H); c('filing_cabinet', (-9.55, 0, -11.75), -H)
    c('office_chair', (-4.1, 0, -9.85), math.pi + 0.3); c('office_chair_fallen', (4.6, 0, -10.3))
    c('desk_clutter', (1.6, 1.1, -6.05), math.pi); c('phone', (-1.6, 1.1, -6.1), 0.3); c('mug', (-0.6, 1.1, -5.9))
    c('book_stack', (4.6, 0.81, -8.9)); c('mug', (-4.6, 0.81, -8.8))
    c('trash_can', (3.4, 0, -7.4)); c('trash_can', (-3.2, 0, -13.3))
    c('waiting_chairs', (6.3, 0, -13.2), math.pi); c('waiting_chairs', (-6.6, 0, -13.2), math.pi)
    c('workstation', (7.0, 0, -11.0), math.pi); c('coffee_table', (7.5, 0, -3.8), 0.1)
    c('fire_extinguisher', (9.7, 0, -12.2))
    for pos in [(-2, 0, -3), (5, 0, -11.5), (1, 0, -12.3), (-6.5, 0, -7.5)]:
        c('papers', pos)
    c('chair_fallen', (2.2, 0, -11)); c('vase_broken', (-3.8, 0, -4.2)); c('books_floor', (6.5, 0, -6.5))
    c('coat_rack', (-9.2, 0, -2.2)); c('plant_tall', (2.6, 0, -13.3)); c('radio', (0.4, 1.1, -6.1), math.pi)
    c('side_table', (9.5, 0, -10.3), H); c('tv_old', (9.5, 0.81, -10.3), H)
    w('noticeboard', (-9.83, 1.7, -6.0), '+x')
    w('wanted_poster', (-9.84, 1.6, -3.2), '+x'); w('wanted_poster', (-9.84, 1.6, -8.8), '+x')
    w('wanted_poster', (9.84, 1.6, -2.4), '-x'); w('wall_clock', (-6.0, 3.0, -13.82), '+z')
    # chief's office
    for x in (-12.6, -10.9, -9.2):
        c('bookshelf', (x, 0, -14.4), 0.0)
    for x in (-3.0, -3.55, -4.1):
        c('filing_cabinet', (x, 0, -28.5), math.pi)
    c('office_chair', (-8.95, 0, -24.1), H + 0.2)
    c('book_stack', (-7.7, 0.81, -23.2)); c('mug', (-7.9, 0.81, -24.9)); c('phone', (-7.7, 0.81, -25.1), 0.4)
    c('potted_plant_dead', (-13.3, 0, -28.3)); c('vase', (-13.5, 1.5, -18.2))
    c('workstation', (-6.0, 0, -17.0), math.pi); c('workstation', (-10.8, 0, -17.2), math.pi)
    c('workstation', (-6.2, 0, -27.6), 0.0)
    c('sofa', (-13.4, 0, -22.0), -H); c('coffee_table', (-11.9, 0, -22.0), H)
    c('box_pile', (-12.2, 0, -28.0), 0.5); c('whiteboard', (-8.5, 1.6, -28.83), math.pi)
    c('papers', (-6, 0, -19)); c('papers', (-10.5, 0, -27)); c('books_floor', (-11.8, 0, -21.5)); c('chair_fallen', (-5, 0, -26))
    c('trash_can', (-2.6, 0, -15.0))
    w('noticeboard', (-2.17, 1.7, -25.5), '-x'); w('wall_clock', (-11.0, 3.0, -28.83), '+z')
    c('kitchen_cabinet', (-2.62, 0, -16.0), H); c('microwave', (-2.62, 0.945, -16.0), H)
    c('kitchen_sink', (-2.62, 0, -16.92), H); c('fridge', (-2.78, 0, -18.1), H)
    c('rug_round', (-12.3, 0, -22.0), 0.0); c('floor_lamp', (-13.5, 0, -23.7)); c('table_lamp', (-5.5, 0.81, -17.2))
    # locker room
    c('backpack', (-7.7, 0.45, -36.5)); c('backpack', (-8.2, 0, -40.8))
    c('suitcase_open', (-9.5, 0, -42.0), 0.2);
    c('shower', (-13.3, 0, -49.3), math.pi); c('shower', (-12.0, 0, -49.3), math.pi); c('sink', (-9.8, 0, -49.6), math.pi)
    c('bucket', (-10.6, 0, -48.4)); c('box_pile', (-5.2, 0, -48.8), 0.3); c('trash_can', (-2.6, 0, -31))
    c('water_cooler', (-2.5, 0, -48.6), H); c('fire_extinguisher', (-2.3, 0, -36.4))
    c('papers', (-6, 0, -32)); c('chair', (-4.2, 0, -44.5), 0.6); c('chair_fallen', (-9.5, 0, -47))
    for z in (-43.6, -45.5):
        L.prop('res://scenes/world/lockers.tscn', (-2.45, 0, z), H)
    c('bench', (-8.0, 0, -45.5), H); c('whiteboard', (-12.0, 1.6, -29.17), 0.0001)
    w('wanted_poster', (-8.0, 1.6, -29.17), '-z'); w('noticeboard', (-6.5, 1.7, -49.83), '+z')
    # corridor (decoration only, keep it clear)
    c('fire_extinguisher', (1.7, 0, -24)); c('fire_extinguisher', (-1.7, 0, -33))
    w('wanted_poster', (-1.84, 1.6, -17), '+x'); w('wanted_poster', (1.84, 1.6, -28), '-x')
    w('wanted_poster', (-1.84, 1.6, -45), '+x'); w('noticeboard', (1.83, 1.7, -35), '-x')
    c('papers', (0.5, 0, -31)); c('papers', (-0.8, 0, -45)); c('trash_bags', (1.3, 0, -47.5)); c('newspaper', (-1.0, 0, -22))
    # cell block: guard post in the hall, bunk and toilet in every cell
    L.prop('res://scenes/world/desk.tscn', (7, 0, -16), 0.0)
    c('office_chair', (7, 0, -16.9), math.pi); c('mug', (7.6, 0.81, -15.8)); c('phone', (6.3, 0.81, -16.1))
    c('radio', (7.0, 0.81, -15.7), math.pi); c('coat_rack', (12.3, 0, -18.0))
    c('bench', (2.5, 0, -27), -H); c('water_cooler', (2.5, 0, -32.6), -H); c('trash_can', (11.6, 0, -15.2))
    c('bench', (2.5, 0, -23.5), -H); c('workstation', (10.5, 0, -32.6), 0.0); c('filing_cabinet', (12.4, 0, -33.4), math.pi)
    c('whiteboard', (5.5, 1.6, -14.17), 0.0001)
    c('papers', (8, 0, -24)); c('papers', (4, 0, -31))
    w('noticeboard', (10, 1.7, -14.17), '-z'); w('wall_clock', (7.0, 3.0, -33.83), '+z')
    for bunk_z, toilet_z in [(-16.0, -19.9), (-22.1, -26.6), (-28.8, -32.7)]:
        c('bunk', (17.5, 0, bunk_z), 0.0); c('toilet', (17.55, 0, toilet_z))
        c('papers', (15, 0, bunk_z - 1.5))
    # garage
    c('workbench', (2.6, 0, -47), -H)
    c('tyre_stack', (3.0, 0, -58.8)); c('tyre_stack', (3.8, 0, -59.3)); c('tyre', (5.0, 0, -59.5), 0.1)
    c('tyre_flat', (11.5, 0, -43)); c('tyre', (12.6, 0, -38.2), H)
    c('jerrycan', (2.7, 0, -44.4), 0.2); c('jerrycan', (3.05, 0, -44.0), -0.3)
    c('toolbox', (4.0, 0, -48.6)); c('car_battery', (3.6, 0, -50.8))
    c('oil_stain', (10, 0, -41)); c('oil_stain', (14, 0, -55.5)); c('oil_stain', (6, 0, -46))
    c('traffic_cone', (12, 0, -45.5)); c('traffic_cone', (13.1, 0, -46.4)); c('traffic_cone', (5.5, 0, -53))
    c('box_pile', (18.6, 0, -58.6), 0.2); c('pallet', (6.5, 0, -58.9), 0.0)
    c('crate_large', (11.0, 0, -59.0), H); c('barrel_open', (19.0, 0, -35.5)); c('bucket', (5.2, 0, -50.2))
    c('shovel', (3.3, 0, -52.6)); c('debris_tire', (8.6, 0, -44.2)); c('metal_panel', (17.5, 0, -35.0), 0.0)
    # armory
    for x, facing in ((-5.7, -H), (5.7, H)):
        for z in (-53.0, -55.6):
            c('weapon_rack', (x, 0, z), facing)
    c('ammo_crates', (4.2, 0, -51.3), 0.0); c('ammo_crates', (-4.6, 0, -51.3), math.pi)
    c('cardboard_box', (1.0, 0, -59.3), 0.1)
    c('crate_stack', (-3.0, 0, -59.0), math.pi); c('crate_stack', (5.2, 0, -58.6), math.pi + 0.1)
    c('ammo_crates', (-4.9, 0, -57.6), H)
    # yard
    L.prop('res://scenes/world/dumpster.tscn', (32.8, 0, -41.2), 0.0)
    c('trash_bags', (24, 0, -41)); c('trash_bags', (33, 0, -54.6)); c('tyre', (22, 0, -55), 0.4)
    c('tyre_stack', (25.5, 0, -55.2)); c('traffic_cone', (23, 0, -46)); c('traffic_cone', (23.5, 0, -50.2))
    c('barrier', (21.6, 0, -42.6), 0.3); c('rubble', (26, 0, -52)); c('newspaper', (27.5, 0, -43))
    c('construction_barrier', (24.6, 0, -53.6), 0.4); c('crate_large', (33.0, 0, -50.5), 0.0); c('barrel_open', (21.2, 0, -54.8))


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
    # buildings (facades towards the road), alleys at z -66..-74 and (left) -100..-104. Some ground floors can be
    # entered: a cafe, the grocery shop (the way round the bus blocking the street) and a pharmacy.
    left = [(14, -10, 10, 'brick'), (-10, -26, 14, 'plaster', 'cafe'), (-26, -40, 14, 'plaster'),
            (-40, -66, 9, 'brick_dark'), (-74, -100, 12, 'plaster_gray', 'shop'), (-104, -128, 10, 'brick')]
    right = [(14, -18, 12, 'plaster_gray'), (-18, -44, 9, 'brick'), (-44, -66, 13, 'plaster'),
             (-74, -90, 10, 'brick_dark', 'pharmacy'), (-90, -104, 10, 'brick_dark'), (-104, -128, 11, 'plaster')]
    for side, rows in ((-1, left), (1, right)):
        for z0, z1, h, mat, *room in rows:
            x0, x1 = (9, 21) if side > 0 else (-21, -9)
            fx = x0 - 0.03 if side > 0 else x1 + 0.03
            if room:
                street = 'x1' if side < 0 else 'x0'
                door_z = {'cafe': -18.0, 'shop': -80.0, 'pharmacy': -82.0}[room[0]]
                gaps = [(street, door_z, 1.8)] + ([('x0', -95.0, 1.6)] if room[0] == 'shop' else [])
                L.shell(x0, x1, z0, z1, h, mat, 'tile' if room[0] != 'pharmacy' else 'linoleum', gaps)
                for zz in (z0 - 2.5, z1 + 2.5):  # shop windows
                    if abs(zz - door_z) > 2.5:
                        L.decor((0.06, 2.0, 2.6), (fx, 1.6, zz), 'window_lit', cast_shadow=0)
            else:
                L.blk(mat, (12, h, z0 - z1), ((x0 + x1) / 2, h / 2, (z0 + z1) / 2))
            for row in range(1 if room else 0, int((h - 1.5) // 3.2)):
                y = 2.4 + row * 3.2
                n = int((z0 - z1 - 1) // 3.5)
                for i in range(n):
                    z = z1 + 1.75 + i * 3.5 + ((z0 - z1) - n * 3.5) / 2
                    lit = L.rnd.random() < 0.1
                    L.decor((0.06, 1.5, 1.1), (fx, y, z), 'window_lit' if lit else 'window_dark', cast_shadow=0)
        # alley floor + back wall (the left alley opens into the back yard)
        ax = 15 * side
        L.floor('asphalt', ax - 6, ax + 6, -66, -74)
        if side > 0:
            L.wall_x(21.5 * side, -66, -74, 'brick_dark', h=8, t=1.0)
    # what each building is, from far down the street: neon over the shops, a pharmacy cross, a bar, a hotel
    L.neon('КАФЕ', (-8.85, 5.4, -18), '+x', 'pink', font=130, flicker=True)
    L.blade('КАФЕ', -8.85, 1, 6.0, -12.0, 'pink', font=80)
    L.neon('ОТКРЫТО', (-8.85, 3.3, -12.5), '+x', 'cyan', font=50, light=False)
    L.neon('ПРОДУКТЫ', (-8.85, 5.2, -87), '+x', 'cyan', font=120)
    L.blade('ПРОДУКТЫ', -8.85, 1, 7.4, -76.0, 'cyan', font=60)
    L.neon('24 ЧАСА', (-8.85, 3.3, -94), '+x', 'yellow', font=60, light=False)
    L.neon('АПТЕКА', (8.85, 5.2, -84.5), '-x', 'green', font=110)
    L.decor((1.2, 0.08, 0.08), (8.25, 4.6, -78.6), 'dark')               # bracket holding the cross out of the wall
    L.cross((7.7, 4.6, -78.6), '+z', 'neon_green', size=1.3, depth=0.2)
    L.omni((7.4, 4.6, -78.6), (0.2, 1.0, 0.35), 1.6, 8.0)
    L.neon('БАР', (-8.85, 4.2, -112), '+x', 'red', font=120, flicker=True)
    L.blade('БАР', -8.85, 1, 5.0, -106.0, 'red', font=80, flicker=True)
    L.blade('АПТЕКА', 8.85, -1, 7.0, -76.0, 'green', font=60)
    L.neon('ГОСТИНИЦА', (8.85, 8.6, -4), '-x', 'white', font=100)
    L.neon('ЛОМБАРД', (8.85, 3.4, -55), '-x', 'yellow', font=70, flicker=True)
    street_1_backyard(L)
    # start: dead end behind the player
    L.wall_z(Z0 + 0.5, -9, 9, 'concrete', h=3, t=1.0)
    L.prop(VEHICLE.format('bus'), (0, 0, 11.5), 1.45)
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
    cars = [('sedan_burnt', (-3.0, 0, -2), 0.45), ('suv', (3.8, 0, -16), -0.15), ('hatchback_sports', (-3.8, 0, -27), 0.1),
            ('van', (-2.0, 0, -38), 1.45), ('taxi', (3.4, 0, -39.5), 1.3), ('police', (4.2, 0, -55), 0.25),
            ('sedan', (-4.8, 0, -63.5), 0.15), ('hatchback_sports_burnt', (2.4, 0, -70.5), 2.0),
            ('suv_burnt', (-4.2, 0, -78), -0.3), ('delivery', (3.5, 0, -100), 0.6), ('ambulance', (-3.6, 0, -106), -0.3),
            ('police', (-3.5, 0, -122), 1.2), ('police', (4.0, 0, -125), -1.3), ('taxi_burnt', (4.6, 0, -6.5), -2.6)]
    for scene, pos, rot in cars:
        L.prop(VEHICLE.format(scene), pos, rot)
    L.fire((-3.0, 1.1, -2))
    L.fire((-4.2, 1.0, -78))
    L.prop(VEHICLE.format('bus'), (0.0, 0, -88), 1.4)
    # the bus and a barricade close the street: go round through the shop or the back yard
    for x in (-7.3, 7.3):
        L.blk('sandbag', (3.6, 2.2, 1.0), (x, 1.1, -88.2))
        L.blk('concrete', (3.6, 0.6, 1.2), (x, 2.5, -88.2))
    L.fire((1.5, 3.2, -88))
    L.blk('concrete', (3.0, 0.9, 0.6), (7.5, 0.45, -39), rot=(0, 0.2, 0))  # jersey barrier
    for x in (-5, -2.5, 2.5, 5):  # police barricade in front of the station
        L.blk('concrete', (2.2, 0.9, 0.6), (x, 0.45, -116), rot=(0, L.rnd.uniform(-0.3, 0.3), 0))
    # police station
    L.blk('plaster_gray', (42, 10, 22), (0, 5, -141))
    L.decor((4.0, 3.2, 0.3), (0, 1.6, -129.9), 'dark')
    L.decor((3.8, 0.12, 1.0), (0, 3.25, -129.3), 'door_steel')                    # canopy with a lamp under it
    L.decor((3.0, 0.03, 0.5), (0, 3.18, -129.2), 'lamp_glow', cast_shadow=0)
    L.node('EntranceSign', 'Label3D', 'Decor', position=V3(0, 3.75, -129.7), text=S('ВХОД'), font_size=90,
           pixel_size=0.01, modulate=C(0.45, 1.0, 0.55), outline_size=0)
    L.decor((42.2, 0.6, 0.4), (0, 9.7, -129.9), 'police_blue')
    L.node('Sign', 'Label3D', 'Decor', position=V3(0, 6.5, -129.8), text=S('ПОЛИЦИЯ'), font_size=200,
           pixel_size=0.01, modulate=C(0.45, 0.65, 1.0), outline_size=0)
    L.omni((0, 6, -128), (0.4, 0.6, 1.0), 2.0, 10, flicker=True)
    L.omni((0, 2.9, -128.2), (1, 0.9, 0.7), 3.0, 9)
    for dy in (-1.4, 1.4):  # blue neon tube around ПОЛИЦИЯ
        L.decor((10.4, 0.06, 0.06), (0, 6.5 + dy, -129.7), 'neon_blue', cast_shadow=0)
    for x in (-5.2, 5.2):
        L.decor((0.06, 2.86, 0.06), (x, 6.5, -129.7), 'neon_blue', cast_shadow=0)
    for x, mat, col in ((-1.2, 'siren_red', (1, 0.1, 0.1)), (1.2, 'siren_blue', (0.2, 0.3, 1))):  # beacons on the roof edge
        L.decor((1.6, 0.4, 0.5), (x, 10.2, -130.4), mat, cast_shadow=0)
        L.omni((x, 10.8, -129.0), col, 2.5, 12, flicker=True)
    street_clutter(L)
    L.door('StationDoor', (3.0, 3.0, 0.2), (0, 1.5, -129.6), 'police_blue', event='Exit',
           prompt='Войти в участок', open_offset=V3(0, 0, -0.01), open_time=0.1, player_can_open=False,
           event_unlocks=True, locked_message='Сначала разберись с Мясником')
    # glass double doors with the lit lobby behind them
    for x in (-0.72, 0.72):
        L.box(L.uid('Pane'), 'Doors/StationDoor', (1.2, 2.3, 0.02), (x, 0.15, 0.11), 'door_glass_lit', cast_shadow=0)
        L.box(L.uid('Handle'), 'Doors/StationDoor', (0.7, 0.06, 0.06), (x, -0.15, 0.16), 'chrome')

    # zombies
    for kind, pos in [('walker', (-2, 0, -14)), ('walker', (2.5, 0, -22)), ('walker', (-4.5, 0, -31)),
                      ('walker', (0, 0, -44)), ('walker', (-5, 0, -47)), ('runner', (4.5, 0, -46)),
                      ('walker', (1.5, 0, -60)), ('walker', (-6.5, 0, -58)), ('walker', (-1, 0, -80)),
                      ('walker', (5, 0, -82)), ('runner', (-6, 0, -84)), ('walker', (4, 0, -96)),
                      ('walker', (-3, 0, -98)), ('walker', (0, 0, -110)), ('walker', (6, 0, -119)),
                      ('walker', (-6.5, 0, -125)), ('soldier', (3, 0, -118)), ('bloater', (2.5, 0, -63))]:
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
    L.trigger('BlockadeTrigger', (0, 1.5, -82), (12, 3, 2), 'Blockade')
    L.event('Blockade', speaker=D, duration=8, objective='Обойди завал: через магазин слева или через двор',
            message='Автобус перегородил всю улицу. Обойди: магазин слева сквозной, выход во двор через подсобку. '
                    'Или переулком — двор выводит обратно на улицу.')
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
           locked_message='Нужна ключ-карта оружейной', prompt='Открыть оружейную', open_offset=V3(-3.8, 0, 0), open_time=1.6)
    # make the armory door stand out: hazard stripes, a sign, a card reader and its own lamp
    A = 'Doors/ArmoryDoor'
    for y in (-1.35, 1.35):
        L.box(L.uid('Band'), A, (4.0, 0.36, 0.02), (0, y, 0.135), 'paint_yellow', cast_shadow=0)
        for i in range(8):
            L.box(L.uid('Slash'), A, (0.16, 0.36, 0.022), (-1.75 + i * 0.5, y, 0.137), 'dark', rot=(0, 0, 0.6),
                  cast_shadow=0)
    L.node('Sign', 'Label3D', A, position=V3(0, 0.45, 0.14), text=S('ОРУЖЕЙНАЯ'), font_size=60, pixel_size=0.008,
           modulate=C(1.0, 0.85, 0.3), outline_size=8)
    L.box('Reader', A, (0.22, 0.32, 0.06), (1.55, -0.1, 0.16), 'dark')
    L.box('ReaderLight', A, (0.1, 0.05, 0.02), (1.55, 0.0, 0.2), 'taillight', cast_shadow=0)
    L.ceiling_lamp(0, -48.4, energy=2.4, rng=7.0)
    L.door('GarageDoor', (0.25, 3.2, 2.5), (2, 1.6, -41.25), 'door_steel', player_can_open=False,
           locked_message='Заблокировано', open_offset=V3(0, 0, -2.4))
    for i, (z0, z1) in enumerate([(-14.6, -20.6), (-20.6, -27.3), (-27.3, -33.4)]):
        L.door(f'Cell{i + 1}', (0.12, 3.6, z0 - z1), (13, 1.8, (z0 + z1) / 2), 'bars', player_can_open=False,
               locked_message='Камера заперта', open_offset=V3(0, 0, -0.6 * (z0 - z1)), open_time=0.8)
    L.door('Shutter', (0.3, 4.0, 8.0), (20, 2.0, -48), 'door_steel', event='ShutterOpened',
           prompt='Поднять ворота', open_offset=V3(0, 3.7, 0), open_time=2.5)
    # Both garage doors face west (-X): slats, hazard stripes and signs so they stand out in the dark.
    def hazard(door, width, y, x):
        L.box(L.uid('Band'), door, (0.02, 0.36, width), (x, y, 0), 'paint_yellow', cast_shadow=0)
        for i in range(int(width / 0.5)):
            L.box(L.uid('Slash'), door, (0.022, 0.36, 0.16), (x - 0.002, y, -width / 2 + 0.25 + i * 0.5), 'dark',
                  rot=(0.6, 0, 0), cast_shadow=0)
    S_ = 'Doors/Shutter'
    for i in range(8):
        L.box(L.uid('Slat'), S_, (0.02, 0.05, 7.9), (-0.16, -1.4 + i * 0.4, 0), 'metal', cast_shadow=0)
    hazard(S_, 8.0, -1.75, -0.17)
    L.node('Sign', 'Label3D', S_, position=V3(-0.18, 1.3, 0), rotation=V3(0, -math.pi / 2, 0), text=S('ВЫЕЗД'),
           font_size=110, pixel_size=0.01, modulate=C(1.0, 0.85, 0.3), outline_size=10)
    L.decor((0.08, 0.5, 0.35), (19.82, 1.3, -43.4), 'dark')                       # control box with a green button
    L.decor((0.04, 0.12, 0.12), (19.77, 1.38, -43.4), 'lamp_glow', cast_shadow=0)
    L.omni((19.4, 1.4, -43.4), (0.4, 1.0, 0.4), 0.8, 2.5)
    L.ceiling_lamp(18.2, -48, energy=2.4, rng=8.0)
    G_ = 'Doors/GarageDoor'
    hazard(G_, 2.5, -1.35, -0.135)
    hazard(G_, 2.5, 1.35, -0.135)
    L.node('Sign', 'Label3D', G_, position=V3(-0.14, 0.3, 0), rotation=V3(0, -math.pi / 2, 0), text=S('ГАРАЖ'),
           font_size=64, pixel_size=0.008, modulate=C(1.0, 0.85, 0.3), outline_size=8)
    L.omni((0.8, 3.2, -41.25), (1, 0.85, 0.6), 1.2, 4)

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
    L.prop(VEHICLE.format('police'), (10, 0, -40), 0.0)
    L.prop(VEHICLE.format('suv'), (14.5, 0, -56), 1.5)
    for pos in [(18, 0, -37), (18.8, 0, -37.8), (8, 0, -58.5), (17, 0, -44)]:
        L.prop('res://scenes/world/barrel.tscn', pos)
    L.prop('res://scenes/world/shelf.tscn', (7.0, 0, -36), math.pi / 2)
    L.prop(VEHICLE.format('sedan'), (28, 0, -48), 1.57)

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
    station_clutter(L)
    L.node('Alarm', 'AudioStreamPlayer3D', 'Decor', position=V3(0, 3.5, -30), stream=L.sound('alarm'),
           unit_size=20.0, volume_db=-4.0, script=L.ext_res('Script', 'res://scripts/world/sound_trigger.gd'))

    # zombies
    L.zombie('soldier', (-6, 0, -20)); L.zombie('walker', (-10, 0, -26))                 # office
    L.zombie('walker', (-9, 0, -34)); L.zombie('runner', (-6, 0, -46))                   # lockers
    L.zombie('walker', (0.5, 0, -27))                                                    # corridor
    for i, z in enumerate((-16.5, -18.5, -23, -25.5, -29.5, -32)):                       # cells
        L.zombie('walker' if i % 3 else 'runner', (15.0 + (i % 2) * 1.0, 0, z), name=f'Prisoner{i + 1}')
    L.zombie('soldier', (8, 0, -18)); L.zombie('walker', (6, 0, -30))
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
    L.pickup('weapon_smg', (-2.4, 0.95, -52.0))
    L.pickup('ammo_smg', (2.4, 0, -52.2))
    L.pickup('weapon_grenade', (-12.5, 0, -40.5))
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
    L.spawner('LobbyHorde', [(-6, 0, -3), (6, 0, -3), (0, 0, -4)], ['walker', 'soldier', 'runner', 'walker'], 8, interval=1.2)
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
    L.neon('ДИНАМО', (0, 11.3, -73.6), '+z', 'blue', font=500, light=False)  # letters standing on the north wall
    L.omni((0, 11.3, -68), (0.25, 0.4, 1.0), 4.0, 22)
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
    L.prop(VEHICLE.format('ambulance'), (-28, 0, 32), 0.8)
    L.prop(VEHICLE.format('police'), (29, 0, 34), -0.6)
    L.fire((-24, 2.4, 20))
    L.fire((26, 0.1, -34))
    stadium_clutter(L)
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
                         ('ammo_shells', (12, 0, -20), 30.0), ('ammo_smg', (-12, 0, -3), 30.0), ('ammo_sniper', (14, 0, 6), 40.0),
                         ('ammo_magnum', (-6, 0, 14), 35.0), ('weapon_grenade', (5, 0, -14), 45.0)]:
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
    mix = ['walker', 'walker', 'soldier', 'runner', 'bloater', 'spitter']
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
    # side rooms off the lobby (staff canteen west, records office east), closed to the outside
    L.wall_x(-12, 0, -4, H); L.wall_x(-12, -6, -14, H); L.wall_x(12, 0, -3.5, H); L.wall_x(12, -5.5, -14, H)
    L.wall_x(-24, 0.15, -14, H); L.wall_x(24, 0.15, -14, H)
    L.wall_z(-14, -24, -3, H); L.wall_z(-14, 3, 24, H)
    L.wall_x(-24, -14, -15.5, H); L.wall_x(-24, -17.5, -31, H); L.wall_x(24, -14, -31, H)
    for x0, x1 in ((-24, -19), (-17, -7), (-5, 5), (7, 17), (19, 24)):
        L.wall_z(-19, x0, x1, H)
    for x in (-12, 0, 12):
        L.wall_x(x, -19, -31, H)
    L.wall_z(-31, -24, 24, H)
    # storeys above the ground floor (solid), lit windows, the name over the entrance and a red cross on the roof
    L.blk('plaster', (48.3, 8.0, 31.3), (0, 8.4, -15.5))
    for row, y in enumerate((6.4, 9.6)):
        for i in range(13):
            x = -21 + i * 3.5
            if row == 0 and abs(x) < 6:
                continue
            L.decor((1.3, 1.5, 0.06), (x, y, 0.19), 'window_lit' if L.rnd.random() < 0.25 else 'window_dark', cast_shadow=0)
    L.neon('БОЛЬНИЦА', (0, 6.0, 0.15), '+z', 'white', font=130)
    L.cross((0, 15.2, -1.5), '+z', 'neon_red', size=3.6, depth=0.35)
    L.decor((0.5, 1.6, 0.5), (0, 13.2, -1.5), 'dark')
    L.omni((0, 15.2, 1.0), (1.0, 0.1, 0.08), 3.0, 18)
    L.decor((0.06, 0.6, 2.6), (-23.8, 3.4, -16.5), 'siren_red', cast_shadow=0)  # EXIT sign
    L.node('ExitSign', 'Label3D', 'Decor', position=V3(-23.7, 3.4, -16.5), rotation=V3(0, math.pi / 2, 0),
           text=S('ВЫХОД'), font_size=64, pixel_size=0.006, modulate=C(0.4, 1.0, 0.5))
    # metro entrance in the yard's west wall
    L.decor((0.1, 2.6, 2.6), (-35.95, 1.3, -17), 'dark')
    L.node('MetroSign', 'Label3D', 'Decor', position=V3(-35.85, 3.2, -17), rotation=V3(0, math.pi / 2, 0),
           text=S('М  МЕТРО'), font_size=80, pixel_size=0.008, modulate=C(1.0, 0.25, 0.2))
    L.omni((-34.5, 3.0, -17), (1, 0.5, 0.4), 1.2, 6)
    L.decor((0.2, 0.9, 0.2), (-36.2, 3.95, -17), 'dark')
    L.neon('М', (-36.0, 5.0, -17), '+x', 'red', font=180)
    L.dress_door((-24, 0, -16.5), 'z', '+x', width=2.0)
    L.door('FireDoor', (0.3, 3.0, 2.0), (-24, 1.5, -16.5), 'door_steel', player_can_open=False,
           locked_message='Электрозамок — нет питания', swing_degrees=100.0, open_time=1.0)

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
    L.prop(VEHICLE.format('sedan_burnt'), (3, 0, 5), 0.9)
    L.fire((3, 1.2, 5))
    L.prop(VEHICLE.format('ambulance'), (-9, 0, 7), 0.25)
    L.prop(VEHICLE.format('van'), (12, 0, 9), -1.2)
    L.prop('res://scenes/world/street_lamp_flicker.tscn', (-15, 0, 12), math.pi)
    L.prop('res://scenes/world/street_lamp.tscn', (15, 0, 12), math.pi)
    L.omni((0, 3.4, -1), (1, 0.85, 0.6), 1.2, 8)

    hospital_clutter(L)
    # light: dim red emergency lamps now, ceiling lights when the power is back
    for pos in [(-18, 3.6, -7), (18, 3.6, -7), (0, 3.6, -10), (-18, 3.6, -16.5), (0, 3.6, -16.5), (18, 3.6, -16.5), (21, 3.6, -25)]:
        L.omni(pos, (1, 0.15, 0.1), 0.8, 7, flicker=True)
    power = []
    for x, z in [(-18, -4), (-18, -10), (18, -4), (18, -10), (-6, -4), (6, -4), (-6, -10), (6, -10), (-20, -16.5), (-12, -16.5), (-4, -16.5), (4, -16.5),
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
    L.pickup('weapon_grenade', (-19.0, 0.8, -10.5)); L.pickup('ammo_smg', (14.2, 0, -12.8))
    L.pickup('ammo_magnum', (20.6, 0, -2.6)); L.pickup('weapon_smg', (18.0, 0.81, -6.4))
    for kind, pos in [('bloater', (-6, 0, -26.5)), ('bloater', (16, 0, -26)), ('spitter', (-30, 0, -24))]:
        L.zombie(kind, pos)
    L.pickup('ammo_shells', (-25.5, 0, -9.5))
    L.zombie('patient_zero', (-33, 0, -17), -math.pi / 2, name='PatientZero', sight_range=11.0,
             alert_event=NP('../../Story/PatientZeroAppears'), death_event=NP('../../Story/PatientZeroDead'))

    D = 'Диспетчер'
    L.event('Intro', speaker=D, duration=9, targets=['Story/Intro2'],
            message='Больница? Плохо, но другого пути нет. Пожарный выход в западном крыле на электрозамке — '
                    'сначала запусти генератор, он в техническом крыле, на востоке.')
    L.event('Intro2', delay=9.5, speaker=D, duration=6, message='Свет отключён. Фонарик — F. И лишний раз не шуми.')
    L.event('ShotgunFound', speaker=D, duration=6,
            message='Дробовик охраны! В тесных коридорах лучше не придумаешь. Клавиша 4.')
    L.event('PowerOn', speaker=D, duration=8, objective='Беги к пожарному выходу в западном конце коридора',
            message='Есть питание! Чёрт… сирена подняла всё здание. Пожарная дверь открыта — беги!',
            targets=power + ['Decor/Alarm', 'Doors/FireDoor', 'Story/WardHorde', 'Story/LobbyHorde'] + patients)
    L.spawner('WardHorde', [(-18, 0, -23), (-6, 0, -23), (6, 0, -23)], ['walker', 'walker', 'runner', 'bloater'], 8, interval=1.0)
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
    L.wall_x(-10, -12, -30, T); L.wall_x(-10, -40, -60, T); L.wall_x(10, -12, -60, T)
    L.wall_z(-60, -4, 10, T)
    for x in (-4.05, 4.05):
        L.decor((0.1, 0.02, 48), (x, 0.01, -36), 'paint_yellow', cast_shadow=0)
    for z in range(-18, -58, -8):
        for x in (-3.6, 3.6):
            L.blk('subway_tile', (0.8, 4.0, 0.8), (x, 2.0, z))
    rails(-7, -12, -60)
    rails(7, -12, -60)
    # the right-hand tunnel has caved in: a heap of rubble in front of the end wall
    for x, z, s_, r in [(7, -58.6, 2.6, 0.3), (5.6, -57.4, 1.4, 0.9), (8.6, -57.0, 1.2, 0.5), (6.6, -56.2, 0.8, 1.4)]:
        L.blk('concrete', (s_, s_ * 0.7, s_), (x, s_ * 0.3, z), rot=(0.2, r, 0.15))
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
    L.dress_door((-10, 0, -89), 'z', '+x', sign='СЛУЖЕБНЫЙ ПРОХОД', width=2.0)
    L.door('ServiceDoor', (0.25, 3.0, 2.0), (-10, 1.5, -89), 'door_steel', event='Bypass',
           prompt='Открыть служебную дверь', swing_degrees=100.0, open_time=1.0)
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
    subway_clutter(L)
    # dispatcher's room off the left track (optional): the sniper rifle
    L.floor('concrete', -16, -10, -30, -40)
    L.floor('concrete', -16.2, -10, -29.8, -40.2, top=4.4, thick=0.4)
    L.wall_x(-16, -30, -40, C_); L.wall_z(-30, -16, -10, C_); L.wall_z(-40, -16, -10, C_)
    L.wall_x(-10, -30, -34, T); L.wall_x(-10, -36, -40, T)
    L.fancy_door('DispatchDoor', (-10, 0, -35), 'z', '+x', glass=False, sign='ДЕЖУРНЫЙ ПО СТАНЦИИ', width=2.0)
    L.prop('res://scenes/world/desk.tscn', (-14.5, 0, -33), math.pi / 2)
    L.clutter('office_chair', (-13.5, 0, -33.2), -math.pi / 2); L.clutter('radio', (-14.5, 0.81, -32.6), math.pi / 2)
    L.clutter('filing_cabinet', (-15.5, 0, -38.8), math.pi / 2); L.clutter('tv_old', (-14.5, 0.81, -33.6), math.pi / 2)
    L.clutter('weapon_rack', (-12.0, 0, -39.6), 0.0); L.clutter('papers', (-12.5, 0, -36))
    L.ceiling_lamp(-13, -35, y=4.15, flicker=True, energy=1.4, rng=7.0)
    L.pickup('weapon_sniper', (-14.5, 0.81, -33.3)); L.pickup('ammo_sniper', (-11.0, 0, -31.0))
    L.zombie('soldier', (-12.5, 0, -37.5))
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
            message='Ты в метро? До «Динамо» два перегона. Иди по левому пути — правый тоннель завалило.')
    L.trigger('BlockageTrigger', (-7, 1.5, -83), (6, 3, 2), 'Blockage')
    L.event('Blockage', speaker=D, duration=7, objective='Найди обход завала',
            message='Впереди сошедший вагон, тоннель перекрыт. Ищи служебную дверь — они есть через каждые сто метров.')
    L.event('Bypass', objective='Пройди служебным коридором')
    L.trigger('AmbushTrigger', (-7, 1.5, -108), (6, 3, 2), 'Ambush')
    L.event('Ambush', speaker=D, duration=6, objective='Беги к станции «Динамо»',
            message='Слышишь топот? Сзади бегуны — не останавливайся!', targets=['Story/Runners'])
    L.spawner('Runners', [(-7, 0, -64), (-7, 0, -68)], ['runner', 'runner', 'walker', 'spitter'], 7, interval=0.9)
    L.trigger('GateTrigger', (0, 1.5, -142), (20, 3, 4), 'GateSiege')
    L.event('GateSiege', speaker=D, duration=8, objective='Продержись, пока диспетчер открывает решётку',
            message='Выход перекрыт решёткой. Взламываю систему станции — продержись минуту!', targets=['Story/Holdout'])
    L.node('Holdout', 'Node', 'Story', script=L.ext_res('Script', 'res://scripts/story/holdout.gd'), duration=60.0,
           timer_text=S('Решётка откроется через %s'),
           spawners=NPS(['../TunnelSpawn', '../PassageSpawn']), boss_spawner=NP('../SpawnBoss'), boss_time=20.0,
           boss_event=NP('../LinemanWarning'), boss_text=S('Убей Обходчика!'), on_finished=NP('../GateOpen'))
    mix = ['walker', 'walker', 'runner', 'bloater', 'spitter']
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

# =================================================================== backdrop for the menu and the intro cutscene
def look(frm, to):
    """Marker rotation so its -Z looks from `frm` at `to`."""
    dx, dy, dz = to[0] - frm[0], to[1] - frm[1], to[2] - frm[2]
    return V3(math.atan2(dy, math.hypot(dx, dz)), math.atan2(-dx, -dz), 0)


def backdrop_world():
    L = LevelBuilder('BackdropWorld', {}, script=None)
    L.setup(night_env(L, fog=0.03, ambient=0.8), MOON)
    c = L.clutter
    # --- the street
    L.floor('asphalt', -6, 6, 14, -74)
    L.floor('sidewalk', -9, -6, 14, -74); L.floor('sidewalk', 6, 9, 14, -74)
    for z in range(10, -72, -6):
        L.decor((0.15, 0.01, 2.5), (0, 0.005, z), 'paint_white')
    for side in (-1, 1):
        for z0, z1, h, mat in [(14, -10, 11, 'brick'), (-10, -30, 14, 'plaster_gray'), (-30, -52, 9, 'brick_dark'),
                               (-52, -74, 12, 'plaster')]:
            x0, x1 = (9, 21) if side > 0 else (-21, -9)
            L.blk(mat, (12, h, z0 - z1), ((x0 + x1) / 2, h / 2, (z0 + z1) / 2))
            fx = x0 - 0.03 if side > 0 else x1 + 0.03
            for row in range(int((h - 1.5) // 3.2)):
                for i in range(int((z0 - z1 - 1) // 3.5)):
                    lit = L.rnd.random() < 0.08
                    L.decor((0.06, 1.5, 1.1), (fx, 2.4 + row * 3.2, z1 + 2.2 + i * 3.5), 'window_lit' if lit else 'window_dark',
                            cast_shadow=0)
    L.wall_z(-74.5, -21, 21, 'brick_dark', h=14, t=1)
    for scene, pos, rot in [('sedan_burnt', (-2.6, 0, -6), 0.5), ('police', (3.2, 0, -15), -0.3), ('bus', (-1.2, 0, -30), 1.3),
                            ('suv_burnt', (3.6, 0, -44), -0.2), ('taxi', (-3.8, 0, -55), 0.15), ('ambulance', (3.0, 0, -62), 2.8)]:
        L.prop(VEHICLE.format(scene), pos, rot)
    for pos in [(-2.6, 1.1, -6), (0.0, 3.2, -30), (3.6, 1.0, -44)]:
        L.fire(pos)
    for i, z in enumerate(range(8, -70, -16)):
        side = -1 if i % 2 else 1
        L.prop(f'res://scenes/world/{"street_lamp_flicker" if i % 2 else "street_lamp"}.tscn', (8.2 * side, 0, z),
               -math.pi / 2 * side)
    L.scatter(['trash_bags', 'newspaper', 'suitcase', 'rubble', 'debris_tire', 'papers', 'backpack'], -8.5, 8.5, -68, 6, 26)
    for pos in [(-8.4, 0, -20), (8.4, 0, -36)]:
        c('electricity_pole', pos, 0.0)
    for x, z in [(-3, -13), (2.2, -21), (-0.6, -24), (4.2, -33), (-4.4, -38), (0.4, -48), (2.6, -10), (-2, -58)]:
        L.zombie('walker', (x, 0, z))
    L.zombie('runner', (5.0, 0, -26))
    # --- the basement where the hero hid (far away from the street)
    B = 300.0
    L.floor('concrete', B - 3.6, B + 3.6, 3.1, -3.1)
    L.floor('concrete', B - 3.75, B + 3.75, 3.25, -3.25, top=2.75, thick=0.3)
    L.wall_z(3.1, B - 3.6, B + 3.6, 'concrete', h=2.6, t=0.3); L.wall_z(-3.1, B - 3.6, B + 3.6, 'concrete', h=2.6, t=0.3)
    L.wall_x(B - 3.6, 3.1, -3.1, 'brick_dark', h=2.6, t=0.3)
    L.wall_x(B + 3.6, 3.1, 0.6, 'concrete', h=2.6, t=0.3); L.wall_x(B + 3.6, -0.9, -3.1, 'concrete', h=2.6, t=0.3)
    L.blk('metal_rust', (0.12, 2.1, 1.5), (B + 3.62, 1.05, -0.15), name='BasementDoor')
    L.decor((0.05, 0.4, 1.2), (B - 3.43, 2.2, 0.5), 'glass', cast_shadow=0)                 # window slit
    for z in (-2.2, 1.8):
        L.decor((7.0, 0.12, 0.12), (B, 2.55, z), 'metal_rust', cast_shadow=0)            # pipes
    c('bed_single', (B - 2.8, 0, 1.6), math.pi / 2)
    L.prop('res://scenes/props/table.tscn', (B + 1.4, 0, -2.2), 0.0)
    c('radio', (B + 1.2, 0.69, -2.25), 0.2); c('table_lamp', (B + 2.0, 0.69, -2.2))
    L.prop('res://scenes/world/shelf.tscn', (B - 3.2, 0, -1.6), math.pi / 2)
    for i, (x, z) in enumerate([(B + 0.6, -2.0), (B + 0.75, -2.15), (B - 0.4, 2.6), (B - 0.2, 2.7), (B + 0.1, 2.55)]):
        L.decor((0.08, 0.11, 0.08), (x, 0.745 if i < 2 else 0.055, z), 'chrome', cast_shadow=0)  # empty tins
    for kind, pos in [('bottle', (B - 1.5, 0, 2.5)), ('box_open', (B + 2.6, 0, 2.3)), ('crate_large', (B + 2.8, 0, 1.2)),
                      ('books_floor', (B - 1.2, 0, 0.6)), ('bucket', (B - 2.9, 0, -0.2)), ('rug', (B - 0.6, 0.0, 0.8)),
                      ('chair', (B + 1.4, 0, -1.3)), ('backpack', (B - 2.2, 0, 2.6))]:
        c(kind, pos)
    L.omni((B + 1.6, 1.4, -1.8), (1, 0.75, 0.45), 1.6, 5.5, flicker=True, name='BasementLamp')
    L.omni((B - 3.0, 2.0, 0.5), (0.45, 0.55, 0.85), 0.6, 4.0)
    L.omni((B + 1.2, 0.95, -2.0), (0.4, 1.0, 0.5), 0.5, 1.5, name='RadioGlow')
    L.omni((B + 4.2, 1.6, -0.15), (1, 0.85, 0.6), 0.6, 3.0, name='StairLight')
    # --- camera marks: <Shot>A -> <Shot>B, used by scripts/ui/cutscene.gd and main_menu.gd
    L.node('Cams', 'Node3D', '.')
    for name, frm, to in [('NewsA', (0, 2, 12), (0, 2, 0)), ('NewsB', (0, 2, 12), (0, 2, 0)),
                          ('CityA', (-6, 30, 26), (0, 0, -30)), ('CityB', (4, 22, 4), (0, 0, -40)),
                          ('StreetA', (2.0, 1.5, 8), (0, 1.3, -30)), ('StreetB', (0.6, 1.3, 1.5), (-1, 1.2, -30)),
                          ('BasementA', (B + 3.0, 2.2, 2.6), (B - 2, 0.5, -1)), ('BasementB', (B + 2.0, 1.9, 2.0), (B - 2.5, 0.6, 0.5)),
                          ('RadioA', (B + 1.0, 1.4, -0.6), (B + 1.2, 0.75, -2.25)), ('RadioB', (B + 1.15, 1.0, -1.25), (B + 1.2, 0.8, -2.25)),
                          ('DoorA', (B - 1.0, 1.6, 0.5), (B + 3.6, 1.1, -0.15)), ('DoorB', (B + 1.6, 1.6, 0.0), (B + 3.6, 1.1, -0.15)),
                          ('MenuA', (-3.0, 2.0, 10), (0.5, 1.4, -20)), ('MenuB', (2.5, 1.8, 7), (-1.0, 1.4, -24))]:
        L.node(name, 'Marker3D', 'Cams', position=V3(*frm), rotation=look(frm, to))
    L.save('scenes/ui/backdrop_world.tscn')



if __name__ == '__main__':
    level_1()
    level_2()
    level_hospital()
    level_subway()
    level_3()
    backdrop_world()
    print('levels ok')
