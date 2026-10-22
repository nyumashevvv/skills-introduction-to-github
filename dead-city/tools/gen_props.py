"""Generates the small clutter props in scenes/props/ (and their materials). Run from the project root.

Props with a collision shape are StaticBody3D (place them under NavigationRegion3D so zombies walk around
them); the rest are plain Node3D decoration.
"""
import math
import os
import random
from tscn import *

T = 'materials/'
HALF = math.pi / 2


def mats():
    for name, col, extra in [
        ('paper', (0.86, 0.85, 0.8), {}), ('cardboard', (0.55, 0.42, 0.26), {}),
        ('book_red', (0.45, 0.08, 0.07), {}), ('book_blue', (0.1, 0.16, 0.38), {}),
        ('book_green', (0.12, 0.3, 0.16), {}), ('book_brown', (0.35, 0.22, 0.12), {}),
        ('book_cream', (0.75, 0.7, 0.55), {}), ('plant', (0.12, 0.32, 0.1), {}), ('plant_dry', (0.38, 0.32, 0.12), {}),
        ('terracotta', (0.55, 0.25, 0.14), {}), ('ceramic', (0.8, 0.82, 0.86), dict(roughness=0.25)),
        ('ceramic_blue', (0.16, 0.3, 0.55), dict(roughness=0.25)), ('cone_orange', (0.95, 0.35, 0.05), {}),
        ('trash_bag', (0.03, 0.03, 0.035), dict(roughness=0.3)), ('fabric_red', (0.5, 0.1, 0.1), {}),
        ('fabric_gray', (0.35, 0.36, 0.38), {}), ('leather', (0.2, 0.12, 0.07), dict(roughness=0.5)),
        ('plastic_white', (0.85, 0.87, 0.88), dict(roughness=0.35)), ('cork', (0.55, 0.4, 0.25), {}),
        ('extinguisher', (0.7, 0.04, 0.03), dict(roughness=0.35, metallic=0.3)),
        ('pill_orange', (0.85, 0.45, 0.1), dict(roughness=0.3)), ('liquid', (0.7, 0.75, 0.2), dict(roughness=0.1)),
    ]:
        material(T + name + '.tres', col, roughness=extra.get('roughness', 0.85), metallic=extra.get('metallic', 0.0))
    material(T + 'screen_glow.tres', (0.02, 0.03, 0.05), roughness=0.2, emission=(0.25, 0.45, 0.7), energy=0.6)
    material(T + 'vending_glow.tres', (0.1, 0.1, 0.1), emission=(0.9, 0.85, 0.75), energy=1.2)
    material(T + 'water_blue.tres', (0.3, 0.5, 0.8), roughness=0.1)


def prop(name, parts, shape=None, root=None):
    """parts: ('b', size, pos, mat[, rot]) boxes, ('c', radius, height, pos, mat[, rot[, top]]) cylinders,
    ('s', radius, pos, mat[, scale]) spheres. shape: ('box', size, center) or ('cyl', radius, height, center)."""
    s = Scene()
    root = root or ''.join(w.title() for w in name.split('_'))
    if shape:
        s.node(root, 'StaticBody3D')
        if shape[0] == 'box':
            sh = s.sub_res('BoxShape3D', size=V3(*shape[1]))
            s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(*shape[2]), shape=sh)
        else:
            sh = s.sub_res('CylinderShape3D', radius=shape[1], height=shape[2])
            s.node('CollisionShape3D', 'CollisionShape3D', '.', position=V3(*shape[3]), shape=sh)
    else:
        s.node(root, 'Node3D')
    for i, p in enumerate(parts):
        n = f'P{i}'
        if p[0] == 'b':
            s.box(n, '.', p[1], p[2], p[3], rot=p[4] if len(p) > 4 else None)
        elif p[0] == 'c':
            s.cyl(n, '.', p[1], p[2], p[3], p[4], rot=p[5] if len(p) > 5 else None,
                  top=p[6] if len(p) > 6 else None, segments=12)
        else:
            extra = {'scale': V3(*p[4])} if len(p) > 4 else {}
            s.sphere(n, '.', p[1], p[2], p[3], **extra)
    os.makedirs('scenes/props', exist_ok=True)
    s.save(f'scenes/props/{name}.tscn')


BOOKS = ['book_red', 'book_blue', 'book_green', 'book_brown', 'book_cream']


def books_row(rnd, x0, x1, y, z, depth=0.22):
    """Upright books standing on a shelf board from x0 to x1."""
    parts, x = [], x0
    while x < x1 - 0.05:
        w, h = rnd.uniform(0.03, 0.07), rnd.uniform(0.2, 0.3)
        if rnd.random() < 0.12:  # a gap or a book lying flat
            x += 0.08
            continue
        parts.append(('b', (w, h, depth * rnd.uniform(0.8, 1.0)), (x + w / 2, y + h / 2, z), rnd.choice(BOOKS)))
        x += w + 0.004
    return parts


def build():
    rnd = random.Random(5)
    # ---------------------------------------------------------------- tyres, garage, street
    tyre = lambda y, rot=(0, 0, 0), x=0.0, z=0.0: [('c', 0.33, 0.22, (x, y, z), 'tire', rot), ('c', 0.17, 0.225, (x, y, z), 'chrome', rot)]
    prop('tyre', tyre(0.33, (HALF, 0, 0.3)))                                  # standing, leaning a bit
    prop('tyre_flat', tyre(0.11))
    prop('tyre_stack', sum((tyre(0.11 + i * 0.22, x=rnd.uniform(-0.03, 0.03)) for i in range(4)), []),
         ('cyl', 0.34, 0.9, (0, 0.45, 0)))
    prop('traffic_cone', [('b', (0.4, 0.04, 0.4), (0, 0.02, 0), 'cone_orange'),
                          ('c', 0.13, 0.62, (0, 0.33, 0), 'cone_orange', None, 0.03),
                          ('c', 0.1, 0.08, (0, 0.3, 0), 'paint_white', None, 0.08)])
    prop('jerrycan', [('b', (0.17, 0.45, 0.34), (0, 0.225, 0), 'car_red'), ('b', (0.04, 0.05, 0.12), (0, 0.48, 0.05), 'dark'),
                      ('c', 0.025, 0.08, (0, 0.47, -0.13), 'dark', (0.6, 0, 0))])
    prop('toolbox', [('b', (0.5, 0.22, 0.24), (0, 0.11, 0), 'car_red'), ('b', (0.3, 0.03, 0.03), (0, 0.27, 0), 'dark'),
                     ('b', (0.04, 0.05, 0.03), (-0.14, 0.24, 0), 'dark'), ('b', (0.04, 0.05, 0.03), (0.14, 0.24, 0), 'dark')])
    prop('car_battery', [('b', (0.3, 0.2, 0.18), (0, 0.1, 0), 'dark'), ('c', 0.02, 0.03, (-0.1, 0.21, 0), 'car_red'),
                         ('c', 0.02, 0.03, (0.1, 0.21, 0), 'chrome')])
    prop('workbench', [('b', (2.2, 0.07, 0.8), (0, 0.9, 0), 'wood'), ('b', (2.2, 0.04, 0.7), (0, 0.25, 0), 'wood'),
                       *[('b', (0.07, 0.9, 0.07), (x, 0.45, z), 'metal') for x in (-1.05, 1.05) for z in (-0.35, 0.35)],
                       ('b', (2.2, 1.0, 0.04), (0, 1.43, 0.38), 'metal'),                      # pegboard
                       ('b', (0.04, 0.3, 0.04), (-0.7, 1.45, 0.34), 'metal'), ('b', (0.2, 0.06, 0.05), (-0.7, 1.6, 0.34), 'dark'),
                       ('b', (0.03, 0.25, 0.03), (-0.3, 1.4, 0.34), 'car_red'), ('b', (0.3, 0.03, 0.03), (0.2, 1.5, 0.34), 'chrome'),
                       ('b', (0.5, 0.22, 0.24), (0.55, 1.05, 0.0), 'car_red'), ('b', (0.3, 0.2, 0.18), (-0.5, 1.03, -0.1), 'dark'),
                       ('c', 0.06, 0.12, (0.0, 1.0, -0.15), 'metal_rust')],
         ('box', (2.2, 1.0, 0.8), (0, 0.5, 0)))
    prop('oil_stain', [('c', 0.6, 0.004, (0, 0.003, 0), 'dark'), ('c', 0.35, 0.005, (0.5, 0.004, 0.3), 'dark')])
    prop('pallet', [*[('b', (1.2, 0.03, 0.12), (0, 0.13, z), 'crate') for z in (-0.44, -0.22, 0, 0.22, 0.44)],
                    *[('b', (0.12, 0.1, 1.0), (x, 0.05, 0), 'crate') for x in (-0.54, 0, 0.54)]])

    # ---------------------------------------------------------------- boxes, trash
    prop('cardboard_box', [('b', (0.6, 0.45, 0.45), (0, 0.225, 0), 'cardboard'), ('b', (0.61, 0.02, 0.08), (0, 0.45, 0), 'paint_yellow')],
         ('box', (0.6, 0.45, 0.45), (0, 0.225, 0)))
    pile = [('b', (0.6, 0.45, 0.45), (0, 0.225, 0), 'cardboard'), ('b', (0.6, 0.45, 0.45), (0.65, 0.225, 0.05), 'cardboard', (0, 0.2, 0)),
            ('b', (0.5, 0.4, 0.4), (0.3, 0.65, 0), 'cardboard', (0, -0.3, 0)), ('b', (0.4, 0.3, 0.35), (0.1, 0.25, 0.55), 'cardboard', (0, 0.5, 0))]
    prop('box_pile', pile, ('box', (1.3, 0.85, 1.0), (0.32, 0.42, 0.15)))
    prop('trash_bags', [('s', 0.3, (0, 0.24, 0), 'trash_bag', (1, 0.8, 1)), ('s', 0.26, (0.45, 0.2, 0.15), 'trash_bag', (1, 0.8, 1.1)),
                        ('s', 0.22, (0.2, 0.18, -0.38), 'trash_bag', (1.1, 0.8, 1)), ('b', (0.06, 0.08, 0.06), (0, 0.48, 0), 'trash_bag')])
    prop('trash_can', [('c', 0.24, 0.7, (0, 0.35, 0), 'metal'), ('c', 0.25, 0.04, (0, 0.7, 0), 'dark'),
                       ('b', (0.2, 0.02, 0.15), (0.05, 0.72, 0), 'paper', (0.3, 0.4, 0)), ('s', 0.08, (-0.05, 0.72, 0.05), 'paper')],
         ('cyl', 0.25, 0.75, (0, 0.37, 0)))
    prop('papers', [('b', (0.21, 0.004, 0.3), (rnd.uniform(-0.6, 0.6), 0.003 + i * 0.001, rnd.uniform(-0.5, 0.5)), 'paper',
                     (0, rnd.uniform(0, 3), 0)) for i in range(8)])
    prop('newspaper', [('b', (0.4, 0.006, 0.55), (0, 0.004, 0), 'paper', (0, 0.4, 0)),
                       ('b', (0.38, 0.004, 0.5), (0.25, 0.006, 0.2), 'paper', (0.05, -0.7, 0)),
                       ('b', (0.3, 0.007, 0.05), (0.0, 0.008, -0.1), 'dark', (0, 0.4, 0))])
    prop('rubble', [('b', (rnd.uniform(0.15, 0.4), rnd.uniform(0.08, 0.2), rnd.uniform(0.15, 0.35)),
                     (rnd.uniform(-0.7, 0.7), 0.05, rnd.uniform(-0.6, 0.6)), rnd.choice(['concrete', 'brick', 'concrete']),
                     (rnd.uniform(-0.3, 0.3), rnd.uniform(0, 3), rnd.uniform(-0.3, 0.3))) for _ in range(12)])
    prop('suitcase', [('b', (0.5, 0.7, 0.22), (0, 0.38, 0), 'fabric_red'), ('b', (0.2, 0.03, 0.04), (0, 0.76, 0), 'dark'),
                      ('c', 0.03, 0.03, (-0.18, 0.03, 0.06), 'dark', (0, 0, HALF)), ('c', 0.03, 0.03, (0.18, 0.03, 0.06), 'dark', (0, 0, HALF))])
    prop('suitcase_open', [('b', (0.7, 0.12, 0.5), (0, 0.06, 0), 'leather'), ('b', (0.7, 0.5, 0.06), (0, 0.3, 0.28), 'leather', (-0.3, 0, 0)),
                           ('b', (0.3, 0.06, 0.4), (-0.15, 0.12, 0), 'fabric_gray', (0, 0.2, 0)),
                           ('b', (0.25, 0.05, 0.3), (0.18, 0.13, -0.05), 'paint_white', (0, -0.3, 0))])
    prop('backpack', [('b', (0.35, 0.45, 0.2), (0, 0.22, 0), 'military', (-0.2, 0, 0)), ('b', (0.25, 0.18, 0.08), (0, 0.15, -0.14), 'military', (-0.2, 0, 0))])

    # ---------------------------------------------------------------- office
    shelf_parts = [('b', (1.6, 2.0, 0.04), (0, 1.0, 0.18), 'wood'), ('b', (0.04, 2.0, 0.4), (-0.78, 1.0, 0), 'wood'),
                   ('b', (0.04, 2.0, 0.4), (0.78, 1.0, 0), 'wood')]
    for y in (0.05, 0.5, 0.95, 1.4, 1.98):
        shelf_parts.append(('b', (1.56, 0.03, 0.38), (0, y, 0), 'wood'))
    for y in (0.07, 0.52, 0.97, 1.42):
        shelf_parts += books_row(rnd, -0.74, 0.74, y, 0.0)
    prop('bookshelf', shelf_parts, ('box', (1.6, 2.0, 0.4), (0, 1.0, 0)))
    stack = []
    y = 0.0
    for i in range(5):
        h = rnd.uniform(0.03, 0.06)
        stack.append(('b', (rnd.uniform(0.17, 0.24), h, rnd.uniform(0.22, 0.3)), (0, y + h / 2, 0), rnd.choice(BOOKS), (0, rnd.uniform(-0.3, 0.3), 0)))
        y += h
    prop('book_stack', stack)
    prop('books_floor', [('b', (0.18, 0.04, 0.25), (rnd.uniform(-0.4, 0.4), 0.02, rnd.uniform(-0.3, 0.3)), rnd.choice(BOOKS),
                          (0, rnd.uniform(0, 3), 0)) for _ in range(5)] + [('b', (0.36, 0.02, 0.25), (0.1, 0.012, 0.1), 'book_cream', (0, 0.5, 0))])
    prop('filing_cabinet', [('b', (0.5, 1.3, 0.6), (0, 0.65, 0), 'metal'),
                            *[('b', (0.44, 0.005, 0.01), (0, 0.33 + i * 0.4, -0.302), 'dark') for i in range(3)],
                            *[('b', (0.14, 0.03, 0.03), (0, 0.47 + i * 0.4, -0.31), 'chrome') for i in range(3)],
                            ('b', (0.44, 0.3, 0.52), (0, 0.85, -0.35), 'metal'),                         # a drawer pulled out
                            ('b', (0.3, 0.25, 0.01), (0, 0.95, -0.35), 'paper')],
         ('box', (0.5, 1.3, 0.6), (0, 0.65, 0)))
    prop('office_chair', [('b', (0.5, 0.08, 0.5), (0, 0.5, 0), 'dark'), ('b', (0.48, 0.55, 0.07), (0, 0.85, 0.24), 'dark', (-0.15, 0, 0)),
                          ('c', 0.03, 0.42, (0, 0.27, 0), 'chrome'),
                          *[('b', (0.35, 0.03, 0.05), (math.sin(a) * 0.17, 0.05, math.cos(a) * 0.17), 'dark', (0, a + HALF, 0))
                            for a in [i * math.tau / 5 for i in range(5)]]],
         ('box', (0.55, 1.0, 0.55), (0, 0.5, 0)))
    prop('office_chair_fallen', [('b', (0.5, 0.08, 0.5), (0, 0.27, 0.2), 'dark', (HALF, 0, 0)), ('b', (0.48, 0.55, 0.07), (0, 0.06, 0.6), 'dark'),
                                 ('c', 0.03, 0.42, (0, 0.27, -0.12), 'chrome', (HALF, 0, 0))])
    prop('chair', [('b', (0.45, 0.05, 0.45), (0, 0.45, 0), 'wood'), ('b', (0.45, 0.45, 0.04), (0, 0.7, 0.21), 'wood'),
                   *[('b', (0.04, 0.45, 0.04), (x, 0.22, z), 'wood') for x in (-0.2, 0.2) for z in (-0.2, 0.2)]],
         ('box', (0.45, 0.9, 0.45), (0, 0.45, 0)))
    prop('chair_fallen', [('b', (0.45, 0.05, 0.45), (0, 0.22, 0.0), 'wood', (HALF, 0, 0)), ('b', (0.45, 0.45, 0.04), (0, 0.02, 0.25), 'wood'),
                          *[('b', (0.04, 0.04, 0.45), (x, y, -0.22), 'wood') for x in (-0.2, 0.2) for y in (0.02, 0.42)]])
    prop('desk_clutter', [('b', (0.45, 0.3, 0.04), (0, 0.17, 0.1), 'dark'), ('b', (0.4, 0.24, 0.005), (0, 0.17, 0.078), 'screen_glow'),
                          ('b', (0.04, 0.12, 0.04), (0, 0.04, 0.12), 'dark'), ('b', (0.42, 0.015, 0.14), (0, 0.008, -0.12), 'dark'),
                          ('c', 0.04, 0.09, (0.35, 0.045, -0.05), 'ceramic'), ('b', (0.21, 0.01, 0.3), (-0.4, 0.005, -0.05), 'paper', (0, 0.3, 0)),
                          ('b', (0.2, 0.06, 0.15), (-0.45, 0.03, 0.18), 'dark')])                    # monitor, keyboard, mug, papers, phone
    prop('phone', [('b', (0.2, 0.06, 0.15), (0, 0.03, 0), 'dark'), ('b', (0.2, 0.04, 0.05), (0, 0.08, 0.04), 'dark')])
    prop('mug', [('c', 0.04, 0.09, (0, 0.045, 0), 'ceramic_blue'), ('c', 0.035, 0.005, (0, 0.088, 0), 'leather')])
    prop('noticeboard', [('b', (1.4, 0.9, 0.03), (0, 0, 0), 'cork'), ('b', (1.46, 0.96, 0.02), (0, 0, 0.01), 'wood'),
                         *[('b', (rnd.uniform(0.2, 0.3), rnd.uniform(0.28, 0.36), 0.005),
                            (-0.5 + i * 0.25 + rnd.uniform(-0.03, 0.03), rnd.uniform(-0.2, 0.2), -0.018), 'paper',
                            (0, 0, rnd.uniform(-0.12, 0.12))) for i in range(5)],
                         ('b', (0.22, 0.28, 0.006), (0.45, 0.22, -0.02), 'paint_yellow')])     # faces -Z
    prop('wanted_poster', [('b', (0.45, 0.6, 0.005), (0, 0, 0), 'paper'), ('b', (0.3, 0.3, 0.006), (0, 0.06, -0.001), 'dark'),
                           ('b', (0.38, 0.06, 0.006), (0, 0.24, -0.001), 'car_red')])
    prop('wall_clock', [('c', 0.18, 0.04, (0, 0, 0), 'paint_white', (HALF, 0, 0)), ('c', 0.19, 0.035, (0, 0, 0.005), 'dark', (HALF, 0, 0)),
                        ('b', (0.015, 0.12, 0.005), (0, 0.05, -0.022), 'dark'), ('b', (0.09, 0.015, 0.005), (0.04, 0, -0.022), 'dark', (0, 0, 0.6))])
    prop('fire_extinguisher', [('c', 0.08, 0.5, (0, 0.25, 0), 'extinguisher'), ('c', 0.03, 0.08, (0, 0.53, 0), 'dark'),
                               ('b', (0.12, 0.03, 0.03), (0.05, 0.58, 0), 'dark'), ('c', 0.012, 0.3, (0.08, 0.35, -0.03), 'dark')])
    prop('water_cooler', [('b', (0.35, 1.0, 0.35), (0, 0.5, 0), 'plastic_white'), ('c', 0.15, 0.45, (0, 1.24, 0), 'water_blue'),
                          ('b', (0.06, 0.05, 0.04), (0, 0.8, -0.19), 'car_blue'), ('b', (0.2, 0.02, 0.1), (0, 0.6, -0.2), 'dark')],
         ('box', (0.36, 1.5, 0.36), (0, 0.75, 0)))
    prop('vending_machine', [('b', (1.0, 1.9, 0.8), (0, 0.95, 0), 'car_red'), ('b', (0.6, 1.3, 0.02), (-0.12, 1.15, -0.41), 'vending_glow'),
                             *[('b', (0.55, 0.02, 0.05), (-0.12, 0.65 + i * 0.3, -0.4), 'dark') for i in range(5)],
                             ('b', (0.15, 0.5, 0.02), (0.36, 1.2, -0.41), 'dark'), ('b', (0.6, 0.15, 0.03), (-0.12, 0.3, -0.41), 'dark')],
         ('box', (1.0, 1.9, 0.8), (0, 0.95, 0)))
    prop('bench', [('b', (1.8, 0.06, 0.45), (0, 0.45, 0), 'wood'), ('b', (1.8, 0.4, 0.05), (0, 0.72, 0.22), 'wood', (-0.15, 0, 0)),
                   *[('b', (0.06, 0.45, 0.45), (x, 0.22, 0), 'metal') for x in (-0.8, 0.8)]],
         ('box', (1.8, 0.95, 0.5), (0, 0.47, 0)))
    # plants and vases
    leaves = [('s', rnd.uniform(0.18, 0.26), (rnd.uniform(-0.15, 0.15), rnd.uniform(0.75, 1.45), rnd.uniform(-0.15, 0.15)), 'plant',
               (1, 1.3, 1)) for _ in range(7)]
    prop('potted_plant', [('c', 0.22, 0.4, (0, 0.2, 0), 'terracotta', None, 0.26), ('c', 0.03, 0.8, (0, 0.7, 0), 'leather'),
                          *leaves], ('cyl', 0.25, 0.5, (0, 0.25, 0)))
    prop('potted_plant_dead', [('c', 0.18, 0.32, (0, 0.16, 0), 'terracotta', None, 0.21),
                               *[('c', 0.012, 0.6, (math.sin(a) * 0.08, 0.5, math.cos(a) * 0.08), 'plant_dry', (math.sin(a) * 0.4, 0, math.cos(a) * 0.4))
                                 for a in [i * 1.3 for i in range(5)]]])
    prop('vase', [('c', 0.09, 0.3, (0, 0.15, 0), 'ceramic_blue', None, 0.05), ('c', 0.05, 0.08, (0, 0.33, 0), 'ceramic_blue', None, 0.07),
                  *[('c', 0.006, 0.35, (math.sin(a) * 0.03, 0.5, math.cos(a) * 0.03), 'plant', (math.sin(a) * 0.3, 0, math.cos(a) * 0.3))
                    for a in (0, 2, 4)],
                  *[('s', 0.035, (math.sin(a) * 0.08, 0.66, math.cos(a) * 0.08), 'book_red') for a in (0, 2, 4)]])
    prop('vase_broken', [('c', 0.09, 0.18, (0, 0.09, 0), 'ceramic', None, 0.07),
                         *[('b', (0.08, 0.01, 0.06), (rnd.uniform(-0.3, 0.3), 0.005, rnd.uniform(-0.3, 0.3)), 'ceramic', (0, rnd.uniform(0, 3), 0))
                           for _ in range(6)], ('s', 0.03, (0.2, 0.02, 0.1), 'plant_dry')])

    # ---------------------------------------------------------------- police
    rifle = lambda x: [('b', (0.05, 0.75, 0.1), (x, 1.2, -0.05), 'gun_black'), ('b', (0.05, 0.25, 0.06), (x, 0.75, -0.06), 'gun_wood')]
    prop('weapon_rack', [('b', (1.6, 1.7, 0.1), (0, 0.85, 0.1), 'metal'), ('b', (1.6, 0.06, 0.25), (0, 0.6, -0.05), 'dark'),
                         ('b', (1.6, 0.06, 0.15), (0, 1.55, 0), 'dark'), *sum((rifle(-0.6 + i * 0.3) for i in range(5)), [])],
         ('box', (1.6, 1.7, 0.3), (0, 0.85, 0.02)))
    prop('ammo_crates', [('b', (0.8, 0.35, 0.45), (0, 0.175, 0), 'ammo_green'), ('b', (0.8, 0.35, 0.45), (0.05, 0.53, 0), 'ammo_green', (0, 0.1, 0)),
                         ('b', (0.6, 0.3, 0.4), (0.9, 0.15, 0.1), 'ammo_green', (0, -0.3, 0)),
                         *[('b', (0.25, 0.08, 0.01), (x, 0.2 + y, -0.23), 'paint_yellow') for x in (0,) for y in (0, 0.36)]],
         ('box', (1.5, 0.75, 0.6), (0.4, 0.37, 0.05)))
    prop('bunk', [('b', (0.85, 0.12, 2.0), (0, 0.45, 0), 'metal'), ('b', (0.78, 0.12, 1.9), (0, 0.57, 0), 'fabric_gray'),
                  ('b', (0.5, 0.1, 0.3), (0, 0.67, 0.75), 'sheet'), *[('b', (0.05, 0.45, 0.05), (x, 0.22, z), 'metal') for x in (-0.4, 0.4) for z in (-0.95, 0.95)]],
         ('box', (0.85, 0.7, 2.0), (0, 0.35, 0)))
    prop('toilet', [('c', 0.2, 0.4, (0, 0.2, 0), 'chrome', None, 0.15), ('c', 0.22, 0.04, (0, 0.42, 0), 'chrome')],
         ('cyl', 0.22, 0.45, (0, 0.22, 0)))
    prop('barrier', [('b', (1.6, 0.25, 0.04), (0, 0.85, 0), 'paint_white'),
                     *[('b', (0.25, 0.25, 0.045), (-0.6 + i * 0.4, 0.85, 0), 'car_red') for i in range(4)],
                     *[('b', (0.05, 0.9, 0.05), (x, 0.45, z), 'wood', (z * 0.6, 0, 0)) for x in (-0.7, 0.7) for z in (-0.15, 0.15)]],
         ('box', (1.6, 1.0, 0.4), (0, 0.5, 0)))

    # ---------------------------------------------------------------- medical
    syr = lambda x, z, a: [('c', 0.008, 0.09, (x, 0.012, z), 'plastic_white', (HALF, a, 0)),
                           ('c', 0.0015, 0.04, (x + math.sin(a) * 0.065, 0.012, z + math.cos(a) * 0.065), 'chrome', (HALF, a, 0)),
                           ('c', 0.012, 0.004, (x - math.sin(a) * 0.05, 0.012, z - math.cos(a) * 0.05), 'plastic_white', (HALF, a, 0))]
    prop('syringes', [('b', (0.35, 0.015, 0.25), (0, 0.0075, 0), 'chrome'),
                      *[p for i in range(3) for p in [(q[0], q[1], q[2], (q[3][0], q[3][1] + 0.015, q[3][2]), *q[4:]) for q in syr(-0.1 + i * 0.1, 0, 0.2 * i)]],
                      ('c', 0.02, 0.06, (0.12, 0.045, 0.07), 'liquid'), ('c', 0.012, 0.012, (0.12, 0.081, 0.07), 'dark')])
    prop('syringes_floor', [p for i in range(4) for p in syr(rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, 3))])
    prop('pills', [('c', 0.03, 0.08, (0, 0.04, 0), 'pill_orange'), ('c', 0.031, 0.02, (0, 0.09, 0), 'plastic_white'),
                   ('c', 0.025, 0.07, (0.08, 0.035, 0.03), 'plastic_white'), ('c', 0.03, 0.08, (-0.05, 0.03, 0.12), 'pill_orange', (HALF, 0.5, 0)),
                   *[('s', 0.008, (rnd.uniform(-0.15, 0.1), 0.005, rnd.uniform(0.1, 0.25)), 'plastic_white', (1, 0.5, 1)) for _ in range(6)]])
    prop('iv_stand', [('c', 0.012, 1.9, (0, 0.95, 0), 'chrome'), ('b', (0.3, 0.012, 0.012), (0, 1.85, 0), 'chrome'),
                      ('b', (0.12, 0.2, 0.04), (0.12, 1.68, 0), 'water_blue'), ('c', 0.003, 0.9, (0.12, 1.15, 0), 'plastic_white'),
                      *[('b', (0.3, 0.02, 0.03), (math.sin(a) * 0.15, 0.05, math.cos(a) * 0.15), 'chrome', (0, a + HALF, 0))
                        for a in [i * math.tau / 5 for i in range(5)]]])
    prop('medical_cart', [('b', (0.7, 0.04, 0.45), (0, 0.9, 0), 'chrome'), ('b', (0.7, 0.04, 0.45), (0, 0.45, 0), 'chrome'),
                          *[('b', (0.03, 0.88, 0.03), (x, 0.47, z), 'chrome') for x in (-0.33, 0.33) for z in (-0.2, 0.2)],
                          *[('c', 0.04, 0.03, (x, 0.04, z), 'dark', (0, 0, HALF)) for x in (-0.3, 0.3) for z in (-0.18, 0.18)],
                          ('b', (0.3, 0.015, 0.2), (-0.15, 0.93, 0), 'chrome'), *[(q[0], q[1], q[2], (q[3][0] - 0.15, q[3][1] + 0.93, q[3][2]), *q[4:]) for q in syr(0, 0, 0.3)],
                          ('c', 0.03, 0.08, (0.15, 0.96, 0.05), 'pill_orange'), ('c', 0.025, 0.07, (0.25, 0.955, -0.05), 'plastic_white'),
                          ('b', (0.3, 0.12, 0.25), (0, 0.53, 0), 'medkit_white'), ('b', (0.3, 0.02, 0.02), (-0.1, 0.93, -0.12), 'sheet')],
         ('box', (0.7, 0.95, 0.45), (0, 0.47, 0)))
    prop('wheelchair', [('b', (0.45, 0.05, 0.42), (0, 0.48, 0), 'fabric_gray'), ('b', (0.45, 0.45, 0.04), (0, 0.75, 0.22), 'fabric_gray'),
                        *[('c', 0.3, 0.03, (x, 0.3, 0.05), 'dark', (0, 0, HALF)) for x in (-0.27, 0.27)],
                        *[('c', 0.24, 0.015, (x, 0.3, 0.05), 'chrome', (0, 0, HALF)) for x in (-0.29, 0.29)],
                        *[('c', 0.07, 0.03, (x, 0.07, -0.25), 'dark', (0, 0, HALF)) for x in (-0.2, 0.2)],
                        *[('b', (0.03, 0.5, 0.03), (x, 0.75, 0.25), 'chrome') for x in (-0.22, 0.22)]],
         ('box', (0.65, 1.0, 0.7), (0, 0.5, 0)))
    prop('gurney', [('b', (0.7, 0.08, 2.0), (0, 0.75, 0), 'chrome'), ('b', (0.65, 0.1, 1.9), (0, 0.84, 0), 'sheet'),
                    ('b', (0.4, 0.02, 0.6), (0.05, 0.9, -0.2), 'z_blood'),
                    *[('b', (0.03, 0.72, 0.03), (x, 0.38, z), 'chrome') for x in (-0.3, 0.3) for z in (-0.9, 0.9)],
                    *[('c', 0.05, 0.03, (x, 0.05, z), 'dark', (0, 0, HALF)) for x in (-0.3, 0.3) for z in (-0.9, 0.9)]],
         ('box', (0.7, 0.9, 2.0), (0, 0.45, 0)))
    prop('stretcher', [('b', (0.6, 0.05, 1.9), (0, 0.12, 0), 'military'), *[('b', (0.04, 0.04, 2.2), (x, 0.12, 0), 'metal') for x in (-0.32, 0.32)],
                       *[('b', (0.04, 0.1, 0.04), (x, 0.05, z), 'metal') for x in (-0.32, 0.32) for z in (-0.8, 0.8)],
                       ('b', (0.5, 0.06, 0.8), (0, 0.17, -0.3), 'sheet', (0, 0.1, 0))])

    # ---------------------------------------------------------------- bigger furniture
    prop('workstation', [('b', (1.6, 0.05, 0.8), (0, 0.76, 0), 'wood'), ('b', (0.05, 0.74, 0.75), (-0.77, 0.37, 0), 'metal'),
                         ('b', (0.45, 0.6, 0.75), (0.55, 0.37, 0), 'metal'), ('b', (0.4, 0.005, 0.01), (0.55, 0.55, -0.376), 'dark'),
                         ('b', (0.4, 0.005, 0.01), (0.55, 0.3, -0.376), 'dark'),
                         ('b', (0.5, 0.33, 0.04), (-0.1, 1.0, 0.22), 'dark'), ('b', (0.45, 0.27, 0.005), (-0.1, 1.0, 0.198), 'screen_glow'),
                         ('b', (0.05, 0.14, 0.05), (-0.1, 0.84, 0.25), 'dark'), ('b', (0.42, 0.015, 0.14), (-0.1, 0.79, -0.05), 'dark'),
                         ('b', (0.21, 0.01, 0.3), (0.5, 0.79, 0.05), 'paper', (0, 0.4, 0)), ('c', 0.04, 0.09, (-0.6, 0.83, 0.1), 'ceramic_blue'),
                         ('b', (0.5, 0.08, 0.5), (0, 0.48, -0.75), 'dark'), ('b', (0.48, 0.5, 0.06), (0, 0.8, -1.0), 'dark', (0.12, 0, 0)),
                         ('c', 0.03, 0.4, (0, 0.25, -0.75), 'chrome'), ('b', (0.5, 0.03, 0.06), (0, 0.04, -0.75), 'dark'),
                         ('b', (0.06, 0.03, 0.5), (0, 0.04, -0.75), 'dark')],
         ('box', (1.6, 0.8, 0.8), (0, 0.4, 0)))                                          # the chair is on the -Z side
    prop('waiting_chairs', [('b', (2.4, 0.06, 0.08), (0, 0.38, 0), 'metal'),
                            *[p for i in range(4) for p in [('b', (0.5, 0.06, 0.45), (-0.87 + i * 0.58, 0.45, 0), 'fabric_gray'),
                                                            ('b', (0.5, 0.45, 0.05), (-0.87 + i * 0.58, 0.72, 0.22), 'fabric_gray', (-0.12, 0, 0))]],
                            *[('b', (0.05, 0.4, 0.4), (x, 0.2, 0), 'metal') for x in (-1.1, 1.1)],
                            ('b', (0.3, 0.04, 0.4), (0.3, 0.5, 0), 'paper', (0, 0.2, 0))],
         ('box', (2.4, 0.95, 0.5), (0, 0.47, 0)))
    prop('sofa', [('b', (2.0, 0.4, 0.85), (0, 0.25, 0), 'leather'), ('b', (2.0, 0.5, 0.2), (0, 0.65, 0.33), 'leather'),
                  ('b', (0.2, 0.3, 0.85), (-0.95, 0.55, 0), 'leather'), ('b', (0.2, 0.3, 0.85), (0.95, 0.55, 0), 'leather'),
                  ('b', (0.85, 0.12, 0.6), (-0.45, 0.5, -0.05), 'leather'), ('b', (0.4, 0.12, 0.4), (0.5, 0.52, 0.0), 'fabric_red', (0.3, 0.4, 0))],
         ('box', (2.0, 0.9, 0.85), (0, 0.45, 0)))
    prop('coffee_table', [('b', (1.1, 0.05, 0.6), (0, 0.42, 0), 'wood'), *[('b', (0.05, 0.4, 0.05), (x, 0.2, z), 'wood') for x in (-0.5, 0.5) for z in (-0.25, 0.25)],
                          ('b', (0.3, 0.01, 0.4), (-0.2, 0.45, 0), 'paper', (0, 0.3, 0)), ('c', 0.04, 0.09, (0.3, 0.49, 0.1), 'ceramic'),
                          ('b', (0.22, 0.03, 0.3), (0.15, 0.46, -0.1), 'book_blue', (0, -0.2, 0))],
         ('box', (1.1, 0.45, 0.6), (0, 0.22, 0)))
    prop('whiteboard', [('b', (1.8, 1.1, 0.03), (0, 0, 0), 'paint_white'), ('b', (1.86, 1.16, 0.02), (0, 0, 0.01), 'metal'),
                        *[('b', (rnd.uniform(0.3, 0.8), 0.015, 0.005), (rnd.uniform(-0.4, 0.4), 0.35 - i * 0.12, -0.018), rnd.choice(['car_blue', 'car_red', 'dark']))
                          for i in range(6)], ('b', (0.25, 0.3, 0.005), (0.6, -0.15, -0.018), 'paper'), ('b', (0.25, 0.3, 0.005), (0.3, -0.2, -0.018), 'paper')])
    prop('crate_stack', [('b', (1.0, 0.6, 0.6), (0, 0.3, 0), 'military'), ('b', (1.0, 0.6, 0.6), (0.05, 0.9, 0.0), 'military', (0, 0.08, 0)),
                         ('b', (1.0, 0.6, 0.6), (0, 0.3, 0.65), 'military'), ('b', (0.9, 0.08, 0.02), (0, 0.45, -0.305), 'paint_yellow'),
                         ('b', (0.9, 0.08, 0.02), (0.05, 1.05, -0.305), 'paint_yellow')],
         ('box', (1.05, 1.2, 1.25), (0.02, 0.6, 0.32)))


if __name__ == '__main__':
    mats()
    build()
    print('props ok')
