"""Draws the mall's printed and painted things into textures/mall/: ad posters, the pictures on the digital screens,
atrium banners, survivors' graffiti, blood splats and warning tape; writes their materials into materials/mall/.
Run from the project root (needs Pillow)."""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

TEX, MAT = 'textures/mall', 'materials/mall'
RUSSO, OSWALD = 'fonts/RussoOne-Regular.ttf', 'fonts/Oswald.ttf'
rnd = random.Random(5)


def font(path, size):
    return ImageFont.truetype(path, size)


def centred(d, y, text, f, fill, w, stroke=0, stroke_fill=None):
    """Draws `text` centred across a picture `w` wide, lines split by \\n; returns the y under it."""
    for line in text.split('\n'):
        box = d.textbbox((0, 0), line, font=f, stroke_width=stroke)
        d.text(((w - (box[2] - box[0])) / 2 - box[0], y), line, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        y += (box[3] - box[1]) * 1.25 + 4
    return y


def fit(text, path, w, size):
    """The largest font no bigger than `size` that fits the widest line into `w`."""
    while size > 10:
        f = font(path, size)
        if max(f.getbbox(line)[2] for line in text.split('\n')) <= w:
            return f
        size -= 4
    return font(path, size)


def poster(name, bg, lines, w=768, h=1024, border=None, art=None):
    """lines: [(text, font path, size, colour)] stacked from the top; art(d, w, h) draws a picture first."""
    im = Image.new('RGB', (w, h), bg)
    d = ImageDraw.Draw(im)
    if art:
        art(d, w, h)
    y = 60
    for text, path, size, colour in lines:
        if text is None:
            y += size
            continue
        y = centred(d, y, text, fit(text, path, w - 80, size), colour, w, stroke=3 if size > 60 else 0,
                    stroke_fill=(0, 0, 0)) + 14
    if border:
        d.rectangle((10, 10, w - 11, h - 11), outline=border, width=12)
    # worn: faded, a little dirty and creased
    noise = Image.effect_noise((w, h), 30).convert('RGB')
    im = Image.blend(im, noise, 0.06)
    d = ImageDraw.Draw(im)
    for _ in range(3):
        x = rnd.randint(0, w)
        d.line((x, 0, x + rnd.randint(-80, 80), h), fill=(255, 255, 255), width=1)
    im.save(f'{TEX}/{name}.png')


def spray(name, text, colour, w=1024, h=384, size=150, path=RUSSO):
    """Spray-painted words: soft edges, uneven, with drips; transparent background."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    mask = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(mask)
    f = fit(text, path, w - 60, size)
    lines = text.split('\n')
    y = (h - sum(f.getbbox(l)[3] * 1.15 for l in lines)) / 2
    for line in lines:
        box = d.textbbox((0, 0), line, font=f)
        x0 = (w - (box[2] - box[0])) / 2
        for i, ch in enumerate(line):                       # every letter a little off, like by hand
            dy = rnd.uniform(-8, 8)
            d.text((x0, y + dy), ch, font=f, fill=255)
            cb = d.textbbox((x0, y + dy), ch, font=f)
            if ch.strip() and rnd.random() < 0.35:          # a drip
                dx = rnd.uniform(cb[0] + 4, max(cb[0] + 5, cb[2] - 4))
                d.line((dx, cb[3] - 6, dx, cb[3] + rnd.uniform(15, 60)), fill=255, width=rnd.randint(3, 6))
            x0 += d.textlength(ch, font=f)
        y += f.getbbox(line)[3] * 1.15
    mask = mask.filter(ImageFilter.GaussianBlur(2.2))
    speckle = Image.effect_noise((w, h), 60).point(lambda v: 255 if v > 150 else 0).filter(ImageFilter.GaussianBlur(1))
    mask = Image.composite(mask, mask.point(lambda v: int(v * 0.75)), speckle)
    im.paste(Image.new('RGBA', (w, h), colour + (255,)), (0, 0), mask)
    im.save(f'{TEX}/{name}.png')


def splat(name, w=512, h=512, trail=False):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    mask = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(mask)
    if trail:                                               # something dragged along the floor
        for i in range(60):
            t = i / 59
            x, y = w * 0.5 + math.sin(t * 5) * 30, h * (0.05 + 0.9 * t)
            r = 26 * (1 - t * 0.6) * rnd.uniform(0.7, 1.1)
            d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=int(255 * (1 - t * 0.5)))
    else:
        d.ellipse((w * 0.3, h * 0.3, w * 0.7, h * 0.7), fill=255)
        for _ in range(26):
            a, dist = rnd.uniform(0, math.tau), rnd.uniform(0.15, 0.45)
            x, y, r = w / 2 + math.cos(a) * w * dist, h / 2 + math.sin(a) * h * dist, rnd.uniform(6, 34)
            d.ellipse((x - r, y - r, x + r, y + r), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(3)).point(lambda v: 255 if v > 110 else int(v * 1.8))
    im.paste(Image.new('RGBA', (w, h), (95, 6, 8, 235)), (0, 0), mask)
    im.save(f'{TEX}/{name}.png')


def tape(name):
    w, h = 1024, 96
    im = Image.new('RGBA', (w, h), (245, 200, 20, 255))
    d = ImageDraw.Draw(im)
    for x in range(-h, w, 120):
        d.polygon(((x, h), (x + 40, h), (x + 40 + h, 0), (x + h, 0)), fill=(25, 25, 25, 255))
    f = font(RUSSO, 46)
    for x in (60, 560):
        d.rectangle((x - 10, 18, x + 410, 78), fill=(245, 200, 20, 255))
        d.text((x, 20), 'НЕ ВХОДИТЬ · ОПАСНО', font=f, fill=(20, 20, 20, 255))
    im.save(f'{TEX}/{name}.png')


def write_material(name, kind):
    tex = f'res://{TEX}/{name}.png'
    if kind == 'screen':
        body = (f'[gd_resource type="ShaderMaterial" load_steps=3 format=3]\n\n'
                f'[ext_resource type="Shader" path="res://materials/mall/ad_screen.gdshader" id="1"]\n'
                f'[ext_resource type="Texture2D" path="{tex}" id="2"]\n\n'
                f'[resource]\nshader = ExtResource("1")\nshader_parameter/tex = ExtResource("2")\n'
                f'shader_parameter/seed = {rnd.uniform(0, 10):.2f}\n')
    else:
        extra = {'poster': 'roughness = 0.85\n',
                 'banner': 'roughness = 0.9\ncull_mode = 2\n',
                 'decal': 'transparency = 1\nroughness = 0.9\n',
                 'blood': 'transparency = 1\nroughness = 0.25\nmetallic_specular = 0.8\n'}[kind]
        body = (f'[gd_resource type="StandardMaterial3D" load_steps=2 format=3]\n\n'
                f'[ext_resource type="Texture2D" path="{tex}" id="1"]\n\n'
                f'[resource]\nalbedo_texture = ExtResource("1")\n{extra}')
    with open(f'{MAT}/{name}.tres', 'w') as f:
        f.write(body)


SHADER = """shader_type spatial;
render_mode cull_disabled;
// A digital ad screen: the picture glows, scanlines crawl, now and then the image tears and the panel flickers.
uniform sampler2D tex : source_color, filter_linear_mipmap;
uniform float energy = 2.2;
uniform float seed = 0.0;

void fragment() {
	float t = TIME + seed * 17.0;
	float tear = step(0.96, fract(sin(floor(t * 5.0) * 43.7 + seed) * 4375.5));
	vec2 uv = UV;
	uv.x += tear * 0.04 * sin(uv.y * 60.0 + t * 30.0);
	vec3 c = texture(tex, uv).rgb;
	float scan = 0.82 + 0.18 * sin(uv.y * 500.0 - t * 6.0);
	float flicker = 0.92 + 0.08 * sin(t * 31.0) * sin(t * 7.3);
	ALBEDO = c * 0.05;
	ROUGHNESS = 0.15;
	EMISSION = c * energy * scan * flicker;
}
"""


def main():
    os.makedirs(TEX, exist_ok=True)
    os.makedirs(MAT, exist_ok=True)
    with open(f'{MAT}/ad_screen.gdshader', 'w') as f:
        f.write(SHADER)

    def bunny(d, w, h):
        d.ellipse((w * 0.3, h * 0.45, w * 0.7, h * 0.8), fill=(255, 245, 250))
        for x in (0.36, 0.56):
            d.ellipse((w * x, h * 0.2, w * (x + 0.08), h * 0.5), fill=(255, 190, 215))
        for x in (0.42, 0.55):
            d.ellipse((w * x, h * 0.58, w * (x + 0.04), h * 0.62), fill=(20, 10, 10))
        d.arc((w * 0.43, h * 0.62, w * 0.57, h * 0.72), 20, 160, fill=(200, 30, 40), width=8)

    def skull(d, w, h):
        d.ellipse((w * 0.28, h * 0.42, w * 0.72, h * 0.8), fill=(225, 220, 200))
        d.rectangle((w * 0.38, h * 0.74, w * 0.62, h * 0.88), fill=(225, 220, 200))
        for x in (0.36, 0.53):
            d.ellipse((w * x, h * 0.55, w * (x + 0.11), h * 0.67), fill=(15, 0, 0))

    posters = [
        ('poster_black_friday', (15, 15, 15), [('ЧЁРНАЯ\nПЯТНИЦА', RUSSO, 150, (255, 215, 0)), (None, '', 40, None),
                                               ('-70%', RUSSO, 260, (255, 255, 255)), ('НА ВСЁ!', RUSSO, 110, (255, 215, 0)),
                                               ('только в «Галактике»', OSWALD, 60, (200, 200, 200))], (255, 215, 0)),
        ('poster_dvoechka', (230, 30, 30), [('ДВОЕЧКА', RUSSO, 150, (255, 255, 255)), ('ГРЕЧКА\nПО АКЦИИ', RUSSO, 130, (255, 235, 60)),
                                            ('2 руб./кг*', RUSSO, 200, (255, 255, 255)), ('*в одни руки — 1 кг', OSWALD, 46, (255, 210, 210))],
         (255, 235, 60)),
        ('poster_cinema', (25, 5, 10), [('СИНЕМА МОРГ', RUSSO, 100, (255, 60, 60)), ('НОЧЬ\nЖИВЫХ\nМЕРТВЕЦОВ', RUSSO, 140, (240, 230, 210)),
                                        (None, '', 360, None), ('СКОРО В ПРОКАТЕ · 18+', OSWALD, 60, (255, 200, 200))], None, skull),
        ('poster_gosha', (255, 120, 180), [('ЗАЙКИНА ПОЛЯНА', RUSSO, 100, (255, 255, 255)), ('ГОША ЖДЁТ\nДЕТЕЙ!', RUSSO, 130, (120, 0, 60)),
                                           (None, '', 400, None), ('3 этаж · каждый день', OSWALD, 60, (255, 255, 255))], (255, 255, 255), bunny),
        ('poster_evacuation', (240, 240, 235), [('ВНИМАНИЕ!', RUSSO, 150, (210, 20, 20)), ('ЭВАКУАЦИЯ', RUSSO, 140, (20, 20, 20)),
                                                ('Пункт сбора жителей —\nстадион «Динамо».\nВертолёты МЧС\nежедневно в 6:00', OSWALD, 80, (30, 30, 30)),
                                                ('Штаб ГО и ЧС города', OSWALD, 46, (100, 100, 100))], (210, 20, 20)),
        ('poster_quarantine', (250, 220, 40), [('КАРАНТИН', RUSSO, 170, (20, 20, 20)), ('При укусе\nНЕМЕДЛЕННО\nобратитесь к врачу.\nНе подходите\nк заболевшим!', OSWALD, 90, (20, 20, 20)),
                                               ('Минздрав', OSWALD, 50, (60, 60, 60))], (20, 20, 20)),
        ('poster_y_video', (200, 20, 30), [('Ы.ВИДЕО', RUSSO, 170, (255, 255, 255)), ('ТЕЛЕВИЗОРЫ\nВ КРЕДИТ', RUSSO, 120, (255, 255, 255)),
                                           ('0%', RUSSO, 300, (255, 230, 60)), ('платить не придётся', OSWALD, 60, (255, 210, 210))], None),
        ('poster_lost_cat', (245, 245, 240), [('ПРОПАЛ КОТ', RUSSO, 130, (20, 20, 20)), (None, '', 330, None),
                                              ('Рыжий, откликается\nна «Мурзик».\nЕсли он странно\nсебя ведёт —\nне подходите!', OSWALD, 70, (30, 30, 30))], None,
         lambda d, w, h: (d.ellipse((w * 0.3, h * 0.2, w * 0.7, h * 0.5), fill=(230, 140, 40)),
                          d.polygon(((w * 0.32, h * 0.26), (w * 0.38, h * 0.12), (w * 0.45, h * 0.22)), fill=(230, 140, 40)),
                          d.polygon(((w * 0.68, h * 0.26), (w * 0.62, h * 0.12), (w * 0.55, h * 0.22)), fill=(230, 140, 40)))),
    ]
    for name, bg, lines, border, *art in posters:
        poster(name, bg, lines, border=border, art=art[0] if art else None)
        write_material(name, 'poster')
    screens = [
        ('screen_sale', (200, 0, 40), [('СКИДКИ', RUSSO, 170, (255, 255, 255)), ('ДО -90%', RUSSO, 190, (255, 230, 60))]),
        ('screen_galaktika', (40, 0, 80), [('ГАЛАКТИКА', RUSSO, 170, (255, 120, 220)), ('всё для жизни', OSWALD, 110, (180, 230, 255))]),
        ('screen_casino', (60, 0, 0), [('КАЗИНО', RUSSO, 170, (255, 200, 60)), ('ПОСЛЕДНЯЯ СТАВКА · 1 этаж', OSWALD, 80, (255, 255, 255))]),
        ('screen_pizza', (230, 110, 10), [('ДОХЛО ПИЦЦА', RUSSO, 150, (255, 255, 255)), ('2 по цене 1', RUSSO, 150, (90, 20, 0))]),
        ('screen_exit', (180, 0, 0), [('ЭВАКУАЦИЯ', RUSSO, 180, (255, 255, 255)), ('ВЫХОД ЧЕРЕЗ КРЫШУ', RUSSO, 100, (255, 230, 60))]),
    ]
    for name, bg, lines in screens:
        poster(name, bg, lines, w=1024, h=576, border=None)
        write_material(name, 'screen')
    for name, bg, text, colour in (('banner_galaktika', (60, 10, 90), 'Г\nА\nЛ\nА\nК\nТ\nИ\nК\nА', (255, 150, 230)),
                                   ('banner_sale', (200, 20, 30), 'Р\nА\nС\nП\nР\nО\nД\nА\nЖ\nА', (255, 255, 255)),
                                   ('banner_new', (10, 60, 90), 'НОВАЯ\nКОЛ-\nЛЕК-\nЦИЯ\n\nВЕСНА\n2026', (255, 255, 255))):
        poster(name, bg, [(text, RUSSO, 130, colour)], w=512, h=1536, border=colour)
        write_material(name, 'banner')
    graffiti = [('graffiti_cinema', 'НЕ ХОДИ\nВ КИНО!', (220, 20, 20)), ('graffiti_gosha', 'ГОША — ЗЛО', (240, 240, 240)),
                ('graffiti_stadium', 'МЫ УШЛИ НА СТАДИОН\nВЕРТОЛЁТ В 6:00', (40, 200, 60)),
                ('graffiti_help', 'ПОМОГИТЕ', (220, 20, 20)), ('graffiti_vasya', 'ЗДЕСЬ БЫЛ ВАСЯ', (40, 120, 255)),
                ('graffiti_doshirak', 'КТО СЪЕЛ\nМОЙ ДОШИРАК?!', (255, 140, 0)), ('graffiti_alive', 'ЖИВЫЕ ЕСТЬ?', (230, 230, 230)),
                ('graffiti_roof', 'КРЫША >>>', (255, 220, 40)), ('graffiti_days', 'ДЕНЬ 1  IIII IIII\nIIII IIII', (230, 230, 230))]
    for name, text, colour in graffiti:
        spray(name, text, colour)
        write_material(name, 'decal')
    for i in range(3):
        splat(f'blood_{i}')
        write_material(f'blood_{i}', 'blood')
    splat('blood_trail', 256, 1024, trail=True)
    write_material('blood_trail', 'blood')
    tape('tape')
    write_material('tape', 'banner')
    print('mall art ok')


if __name__ == '__main__':
    main()
