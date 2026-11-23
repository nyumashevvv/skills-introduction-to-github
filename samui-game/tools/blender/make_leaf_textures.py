#!/usr/bin/env python3
"""Paints the leaf textures (RGBA, alpha = cut-out) used by the vegetation models.

  python3 tools/blender/make_leaf_textures.py tools/blender/tex
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

out = sys.argv[1] if len(sys.argv) > 1 else "tex"
os.makedirs(out, exist_ok=True)
rnd = random.Random(4)


def jitter(c, a=14):
    return tuple(max(0, min(255, v + rnd.randint(-a, a))) for v in c[:3]) + (255,)


def palm_frond(path, dry=False):
    """Coconut frond: rib down the middle (v = along), leaflets hanging to both sides."""
    W, H = 256, 1024
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    base = (150, 120, 70) if dry else (62, 118, 38)
    tip = (175, 140, 85) if dry else (98, 150, 52)
    cx = W // 2
    for y in range(40, H - 10, 7):
        t = y / H
        length = (W * 0.5 - 6) * math.sin(math.pi * min(1.0, 0.15 + t * 0.95)) * (0.85 + 0.15 * rnd.random())
        for side in (-1, 1):
            if rnd.random() < 0.05:
                continue  # a missing leaflet now and then
            col = jitter(tuple(int(base[i] + (tip[i] - base[i]) * t) for i in range(3)))
            ang = math.radians(28 + 10 * rnd.random())
            x1 = cx + side * length * math.cos(ang)
            y1 = y + length * math.sin(ang)
            w = 5
            d.polygon([(cx, y - w / 2), (cx + side * 6, y - w), (x1, y1), (cx + side * 6, y + w)], fill=col)
            # lighter midline on each leaflet
            d.line([(cx + side * 6, y), (x1, y1)], fill=jitter(tuple(min(255, c + 25) for c in col[:3]), 6), width=1)
    d.line([(cx, 0), (cx, H)], fill=(196, 182, 112, 255) if not dry else (120, 95, 60, 255), width=6)
    im.save(path)


def leaf_cluster(path, base=(58, 108, 40), flowers=None, n=170):
    """Square card full of overlapping broad leaves (and optional flowers)."""
    S = 512
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(n):
        r = math.hypot(*(rnd.gauss(0, 0.26) for _ in range(2)))
        a = rnd.random() * math.tau
        x = S / 2 + math.cos(a) * r * S * 0.9
        y = S / 2 + math.sin(a) * r * S * 0.9
        if not (30 < x < S - 30 and 30 < y < S - 30):
            continue
        ang = rnd.random() * math.tau
        L, Wd = rnd.uniform(26, 44), rnd.uniform(10, 16)
        ca, sa = math.cos(ang), math.sin(ang)
        pts = []
        for k in range(12):
            t = k / 11 * math.pi
            px = math.cos(t) * L
            py = math.sin(t) * Wd * (1 - 0.3 * math.cos(t))
            pts.append((x + px * ca - py * sa, y + px * sa + py * ca))
        for k in range(12):
            t = math.pi + k / 11 * math.pi
            px = math.cos(t) * L
            py = math.sin(t) * Wd * (1 + 0.3 * math.cos(t))
            pts.append((x + px * ca - py * sa, y + px * sa + py * ca))
        shade = 0.7 + 0.5 * (1 - y / S)                     # lighter at the top of the card
        col = jitter(tuple(int(c * shade) for c in base), 16)
        d.polygon(pts, fill=col)
        d.line([(x - L * ca, y - L * sa), (x + L * ca, y + L * sa)], fill=jitter(tuple(min(255, int(c * 1.25)) for c in col[:3]), 4), width=1)
    if flowers:
        for i in range(n // 2):
            x, y = rnd.uniform(60, S - 60), rnd.uniform(60, S - 60)
            if (x - S / 2) ** 2 + (y - S / 2) ** 2 > (S * 0.42) ** 2:
                continue
            r = rnd.uniform(7, 13)
            d.ellipse([x - r, y - r, x + r, y + r], fill=jitter(flowers, 22))
    im = im.filter(ImageFilter.SMOOTH)
    im.save(path)


def banana_leaf(path):
    W, H = 256, 1024
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = W / 2
    pts_l, pts_r = [], []
    for k in range(60):
        t = k / 59
        y = 20 + t * (H - 40)
        w = (W * 0.47) * math.sin(math.pi * min(1, 0.06 + t)) ** 0.6
        pts_l.append((cx - w, y))
        pts_r.append((cx + w, y))
    d.polygon(pts_l + pts_r[::-1], fill=(84, 150, 52, 255))
    for y in range(30, H - 30, 9):
        col = jitter((84, 150, 52), 18)
        d.line([(cx, y), (0, y + 50)], fill=col, width=4)
        d.line([(cx, y), (W, y + 50)], fill=col, width=4)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(pts_l + pts_r[::-1], fill=255)
    for k in range(9):  # wind tears down to the midrib
        y = rnd.uniform(120, H - 80)
        side = rnd.choice((-1, 1))
        ImageDraw.Draw(mask).polygon([(cx + side * 8, y), (cx + side * W, y + 30), (cx + side * W, y + 38), (cx + side * 8, y + 4)], fill=0)
    # brown dried edge
    d.line(pts_l, fill=(150, 130, 60, 255), width=3)
    d.line(pts_r, fill=(150, 130, 60, 255), width=3)
    d.line([(cx, 0), (cx, H)], fill=(190, 200, 120, 255), width=8)
    ImageDraw.Draw(mask).line([(cx, 0), (cx, H)], fill=255, width=8)
    im.putalpha(mask)
    im.save(path)


def canopy(path):
    """Opaque, tileable mass of leaves for canopy volumes seen from a distance."""
    S = 512
    im = Image.new("RGBA", (S, S), (28, 52, 22, 255))
    d = ImageDraw.Draw(im)
    for i in range(1400):
        x, y = rnd.uniform(0, S), rnd.uniform(0, S)
        L, Wd = rnd.uniform(10, 22), rnd.uniform(5, 9)
        ang = rnd.uniform(0, math.tau)
        ca, sa = math.cos(ang), math.sin(ang)
        col = jitter(rnd.choice([(46, 88, 32), (60, 104, 40), (38, 74, 28), (74, 116, 46)]), 12)
        for ox in (-S, 0, S):
            for oy in (-S, 0, S):
                pts = []
                for k in range(10):
                    t = k / 10 * math.tau
                    px, py = math.cos(t) * L, math.sin(t) * Wd
                    pts.append((x + ox + px * ca - py * sa, y + oy + px * sa + py * ca))
                d.polygon(pts, fill=col)
    im.save(path)


def grass(path):
    W, H = 512, 256
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(140):
        x = rnd.uniform(10, W - 10)
        h = rnd.uniform(0.45, 1.0) * H
        lean = rnd.uniform(-40, 40)
        col = jitter(rnd.choice([(82, 120, 40), (104, 138, 52), (128, 140, 66), (70, 104, 36)]), 12)
        d.polygon([(x - 3, H), (x + 3, H), (x + lean, H - h)], fill=col)
    im.save(path)


def trunk(path):
    """Palm bark: grey-brown with leaf-scar rings (v repeats along the trunk)."""
    W, H = 128, 256
    im = Image.new("RGBA", (W, H), (118, 104, 86, 255))
    d = ImageDraw.Draw(im)
    for y in range(0, H, 2):
        c = jitter((118, 104, 86), 10)
        d.line([(0, y), (W, y)], fill=c)
    for y in range(0, H, 32):
        d.rectangle([0, y, W, y + 5], fill=(84, 72, 60, 255))
        d.line([(0, y + 6), (W, y + 6)], fill=(150, 136, 116, 255))
    for i in range(300):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        d.point((x, y), fill=jitter((90, 80, 66), 20))
    im.save(path)


def bark(path):
    W, H = 128, 256
    im = Image.new("RGBA", (W, H), (96, 84, 72, 255))
    d = ImageDraw.Draw(im)
    for i in range(60):
        x = rnd.uniform(0, W)
        d.line([(x, 0), (x + rnd.uniform(-6, 6), H)], fill=jitter((70, 62, 54), 12), width=rnd.randint(1, 3))
    im.save(path)


palm_frond(os.path.join(out, "palm_frond.png"))
palm_frond(os.path.join(out, "palm_frond_dry.png"), dry=True)
leaf_cluster(os.path.join(out, "leaves_jungle.png"), base=(54, 100, 38))
leaf_cluster(os.path.join(out, "leaves_light.png"), base=(84, 132, 50))
leaf_cluster(os.path.join(out, "leaves_bougainvillea.png"), base=(60, 110, 44), flowers=(214, 40, 150), n=150)
banana_leaf(os.path.join(out, "banana_leaf.png"))
grass(os.path.join(out, "grass.png"))
canopy(os.path.join(out, "canopy.png"))
trunk(os.path.join(out, "palm_trunk.png"))
bark(os.path.join(out, "bark.png"))
print("textures in", out, sorted(os.listdir(out)))
