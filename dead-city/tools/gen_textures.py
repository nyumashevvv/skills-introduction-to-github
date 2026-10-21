"""Generates the tileable textures and the blood decal in textures/. Run from the project root."""
import zlib, struct, random, math
random.seed(42)


def save_png(path, w, h, pixels, alpha=False):
    rows = []
    ch = 4 if alpha else 3
    for y in range(h):
        row = bytearray([0])
        for x in range(w):
            p = pixels[y * w + x]
            row += bytes(max(0, min(255, int(v))) for v in p[:ch])
        rows.append(bytes(row))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6 if alpha else 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b'')
    open(path, 'wb').write(png)


def noise_layer(size, cells):
    g = [[random.random() for _ in range(cells)] for _ in range(cells)]
    def f(x, y):
        gx, gy = x / size * cells, y / size * cells
        x0, y0 = int(gx) % cells, int(gy) % cells
        x1, y1 = (x0 + 1) % cells, (y0 + 1) % cells
        tx, ty = gx - int(gx), gy - int(gy)
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        a = g[y0][x0] * (1 - tx) + g[y0][x1] * tx
        b = g[y1][x0] * (1 - tx) + g[y1][x1] * tx
        return a * (1 - ty) + b * ty
    return f


def fbm(size, octaves=((4, .5), (8, .25), (16, .15), (32, .1))):
    layers = [(noise_layer(size, c), w) for c, w in octaves]
    return lambda x, y: sum(f(x, y) * w for f, w in layers)


S = 256
def make(name, fn):
    save_png(f'textures/{name}.png', S, S, [fn(x, y) for y in range(S) for x in range(S)])

n = fbm(S)
grain = lambda: random.uniform(-1, 1)

make('asphalt', lambda x, y: [52 + n(x, y) * 40 + grain() * 10] * 3)
make('concrete', lambda x, y: [v := 120 + n(x, y) * 50 + grain() * 6, v, v - 4])

def brick(x, y):
    bh, bw = 32, 64
    row = y // bh
    off = (bw // 2) if row % 2 else 0
    bx, by = (x + off) % bw, y % bh
    if bx < 4 or by < 4:
        v = 150 + grain() * 8
        return [v, v - 5, v - 12]
    tone = ((row * 7 + (x + off) // bw * 13) % 5) * 8
    k = n(x, y) * 30
    return [130 + tone + k + grain() * 8, 62 + tone * 0.5 + k * 0.5, 48 + k * 0.4]
make('brick', brick)

def tile(x, y):
    if x % 64 < 3 or y % 64 < 3:
        return [90, 90, 88]
    v = 205 + n(x, y) * 25 + grain() * 4
    return [v, v, v - 6]
make('tile', tile)

n2 = fbm(S, ((8, .5), (16, .3), (64, .2)))
make('grass', lambda x, y: [40 + n2(x, y) * 30, 78 + n2(x, y) * 50 + grain() * 12, 30 + n2(x, y) * 15])

def wood(x, y):
    plank = x // 64
    v = math.sin((y + plank * 37) * 0.15 + n(x, y) * 6) * 0.5 + 0.5
    edge = 0.6 if x % 64 < 2 else 1.0
    return [(110 + v * 40) * edge, (70 + v * 25) * edge, (40 + v * 12) * edge]
make('wood', wood)

n3 = fbm(S, ((4, .6), (16, .4)))
make('metal', lambda x, y: [v := 140 + n3(x, y) * 40 + grain() * 5 + math.sin(y * 0.8) * 3, v + 2, v + 6])

B = 256
blobs = [(128, 128, 60)] + [(128 + random.gauss(0, 50), 128 + random.gauss(0, 50), random.uniform(6, 26)) for _ in range(22)]
blobs += [(128 + math.cos(a) * r, 128 + math.sin(a) * r, random.uniform(2, 6))
          for a, r in ((random.uniform(0, 6.28), random.uniform(60, 120)) for _ in range(40))]
bn = noise_layer(B, 16)
px = []
for y in range(B):
    for x in range(B):
        a = 0.0
        for bx, by, r in blobs:
            d = math.hypot(x - bx, y - by)
            if d < r: a = max(a, min(1, (r - d) / 3))
        a *= 0.75 + bn(x, y) * 0.35
        px.append([95 + bn(x, y) * 40, 5, 8, a * 235])
save_png('textures/blood.png', B, B, px, alpha=True)
print('textures ok')
