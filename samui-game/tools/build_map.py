#!/usr/bin/env python3
"""Builds the Koh Samui game map from real-world data.

Inputs
  --osm  folder with *.osm XML chunks from the OpenStreetMap API (see fetch_data.py)
  --dem  folder with Terrarium elevation tiles, zoom 13, named X_Y.png

Outputs (into ../data)
  heights.bin   float32 heightfield, N x N, 10 m spacing, zlib-compressed
  landclass.bin uint8 surface class per cell, zlib-compressed
  colormap.png  terrain colour texture, N x N
  roads.json    road polylines grouped by chunk
  buildings.json building footprints grouped by chunk
  places.json   named places (towns, beaches, sights)

Map data (c) OpenStreetMap contributors, ODbL.
Elevation: Mapzen/AWS Terrain Tiles (SRTM and other open sources).
"""
import argparse, glob, json, math, os, random, zlib
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

LON0, LAT0 = 100.01, 9.495
KX = 111320.0 * math.cos(math.radians(LAT0))
KZ = 110574.0
CELL = 10.0            # metres per heightfield cell
N = 2400               # cells per side -> 24 km
HALF = N * CELL / 2    # 12000 m
CHUNK = 1200.0         # metres per chunk (must match game)
NC = int(N * CELL / CHUNK)

# land classes (must match game)
WATER, SAND, GRASS, JUNGLE, URBAN, ROAD, BUILDING, ROCK = range(8)


def to_local(lon, lat):
    return (lon - LON0) * KX, -(lat - LAT0) * KZ


def to_grid(x, z):
    return (x + HALF) / CELL, (z + HALF) / CELL


# ---------------------------------------------------------------- OSM parse
def load_osm(folder):
    nodes, ways, rels, pois = {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(folder, "*.osm"))):
        for _, el in ET.iterparse(f):
            if el.tag == "node":
                nid = int(el.get("id"))
                nodes[nid] = (float(el.get("lon")), float(el.get("lat")))
                tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
                if tags:
                    pois[nid] = tags
                el.clear()
            elif el.tag == "way":
                wid = int(el.get("id"))
                if wid not in ways:
                    ways[wid] = ([int(n.get("ref")) for n in el.findall("nd")],
                                 {t.get("k"): t.get("v") for t in el.findall("tag")})
                el.clear()
            elif el.tag == "relation":
                rid = int(el.get("id"))
                if rid not in rels:
                    rels[rid] = ([(m.get("type"), int(m.get("ref")), m.get("role")) for m in el.findall("member")],
                                 {t.get("k"): t.get("v") for t in el.findall("tag")})
                el.clear()
    print(f"osm: {len(nodes)} nodes, {len(ways)} ways, {len(rels)} relations")
    return nodes, ways, rels, pois


def merge_rings(seqs):
    """Join node-id sequences sharing endpoints into rings (closed if possible)."""
    seqs = [list(s) for s in seqs if len(s) > 1]
    rings = []
    while seqs:
        cur = seqs.pop()
        changed = True
        while cur[0] != cur[-1] and changed:
            changed = False
            for i, s in enumerate(seqs):
                if s[0] == cur[-1]:
                    cur += s[1:]
                elif s[-1] == cur[-1]:
                    cur += s[::-1][1:]
                elif s[-1] == cur[0]:
                    cur = s[:-1] + cur
                elif s[0] == cur[0]:
                    cur = s[::-1][:-1] + cur
                else:
                    continue
                seqs.pop(i)
                changed = True
                break
        rings.append(cur)
    return rings


def ring_xy(ring, nodes):
    pts = [nodes[n] for n in ring if n in nodes]
    return [to_local(lon, lat) for lon, lat in pts]


def area_polygons(ways, rels, nodes, pred):
    """Polygons (outer rings only) for closed ways / multipolygons matching pred(tags)."""
    out = []
    for nds, tags in ways.values():
        if len(nds) > 3 and nds[0] == nds[-1] and pred(tags):
            out.append(ring_xy(nds, nodes))
    for members, tags in rels.values():
        if tags.get("type") == "multipolygon" and pred(tags):
            outer = [ways[r][0] for t, r, role in members if t == "way" and role == "outer" and r in ways]
            for ring in merge_rings(outer):
                if len(ring) > 3:
                    out.append(ring_xy(ring, nodes))
    return out


# ---------------------------------------------------------------- DEM
def load_dem(folder, z=13):
    files = glob.glob(os.path.join(folder, "*_*.png"))
    xs = sorted({int(os.path.basename(f).split("_")[0]) for f in files})
    ys = sorted({int(os.path.basename(f).split("_")[1].split(".")[0]) for f in files})
    mosaic = np.zeros((len(ys) * 256, len(xs) * 256), np.float32)
    for f in files:
        tx, ty = os.path.basename(f)[:-4].split("_")
        a = np.asarray(Image.open(f).convert("RGB"), np.float32)
        h = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
        i, j = xs.index(int(tx)), ys.index(int(ty))
        mosaic[j * 256:(j + 1) * 256, i * 256:(i + 1) * 256] = h
    n = 2 ** z
    gx = (np.arange(N) * CELL - HALF)
    X, Z = np.meshgrid(gx, gx)
    lon = X / KX + LON0
    lat = -Z / KZ + LAT0
    px = (lon + 180) / 360 * n * 256 - xs[0] * 256
    py = (1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n * 256 - ys[0] * 256
    return ndimage.map_coordinates(mosaic, [py - 0.5, px - 0.5], order=3, mode="nearest")


# ---------------------------------------------------------------- raster helpers
SS = 2  # supersampling for polygon rasterisation


def raster_polys(polys, ss=SS):
    img = Image.new("L", (N * ss, N * ss), 0)
    d = ImageDraw.Draw(img)
    for p in polys:
        if len(p) < 3:
            continue
        d.polygon([((x + HALF) / CELL * ss, (z + HALF) / CELL * ss) for x, z in p], fill=255)
    a = np.asarray(img, np.float32) / 255
    if ss > 1:
        a = a.reshape(N, ss, N, ss).mean(axis=(1, 3))
    return a


def resample_line(pts, step):
    out = [pts[0]]
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, z1 - z0)
        k = max(1, int(L / step))
        for s in range(1, k + 1):
            t = s / k
            out.append((x0 + (x1 - x0) * t, z0 + (z1 - z0) * t))
    return out


ROAD_CLASSES = {
    # highway: (width m, kind)   kind: 0 asphalt main, 1 asphalt minor, 2 dirt
    "motorway": (10, 0), "trunk": (10, 0), "primary": (9, 0), "secondary": (8, 0),
    "tertiary": (7, 1), "unclassified": (6, 1), "road": (6, 1),
    "residential": (5, 1), "living_street": (5, 1), "service": (4, 1), "pedestrian": (4, 1),
    "track": (3.5, 2), "raceway": (6, 1),
    "primary_link": (7, 0), "secondary_link": (6, 0), "tertiary_link": (6, 1),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", required=True)
    ap.add_argument("--dem", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(7)

    nodes, ways, rels, pois = load_osm(a.osm)
    dem = load_dem(a.dem)
    print("dem range", dem.min(), dem.max())

    # ---- land mask from coastline
    coast = merge_rings([nds for nds, t in ways.values() if t.get("natural") == "coastline"])
    open_rings = [r for r in coast if r[0] != r[-1]]
    print(f"coastline rings: {len(coast)} ({len(open_rings)} not closed)")
    land = raster_polys([ring_xy(r, nodes) for r in coast if len(r) > 3])
    landb = land > 0.5
    d_land = ndimage.distance_transform_edt(landb) * CELL      # inside land: dist to sea
    d_sea = ndimage.distance_transform_edt(~landb) * CELL      # in sea: dist to land

    # ---- heights
    h = np.where(
        landb,
        0.5 + np.minimum(np.maximum(dem, 0.0), d_land * 0.12),
        -0.4 - np.minimum(d_sea * 0.025, np.maximum(-dem, 3.0) + d_sea * 0.002),
    )
    h = ndimage.gaussian_filter(h, 0.7)
    h = np.where(landb, np.maximum(h, 0.35), np.minimum(h, -0.3))

    # ---- roads
    roads = []  # (pts, width, kind, name)
    for nds, t in ways.values():
        hw = t.get("highway")
        width = kind = None
        if hw in ROAD_CLASSES:
            width, kind = ROAD_CLASSES[hw]
        elif t.get("aeroway") == "runway":
            width, kind = 45, 3
        elif t.get("aeroway") == "taxiway":
            width, kind = 18, 3
        if width is None or t.get("area") == "yes":
            continue
        pts = ring_xy(nds, nodes)
        if len(pts) < 2:
            continue
        name = t.get("name:ru") or t.get("name:en") or t.get("name") or ""
        roads.append((pts, width, kind, name))
    print("roads:", len(roads))

    # flatten terrain along roads (weighted stamp of smoothed road profile)
    sw = np.zeros((N, N), np.float32)
    swh = np.zeros((N, N), np.float32)
    wmax = np.zeros((N, N), np.float32)
    road_out = [[] for _ in range(NC * NC)]
    hs = ndimage.map_coordinates
    for pts, width, kind, name in roads:
        rp = np.array(resample_line(pts, 4.0), np.float32)
        gi, gj = to_grid(rp[:, 0], rp[:, 1])
        th = hs(h, [gj, gi], order=1, mode="nearest")
        win = max(1, int(40 / 4))
        prof = ndimage.uniform_filter1d(th, 2 * win + 1, mode="nearest")
        prof = np.maximum(prof, 0.45)
        R = width / 2 + 12
        rc = int(math.ceil(R / CELL))
        ci0, cj0 = np.round(gi).astype(int), np.round(gj).astype(int)
        for di in range(-rc, rc + 1):
            for dj in range(-rc, rc + 1):
                ci, cj = ci0 + di, cj0 + dj
                ok = (ci >= 0) & (ci < N) & (cj >= 0) & (cj < N)
                dist = np.hypot((ci - gi) * CELL, (cj - gj) * CELL)
                w = np.clip(1 - (dist - (width / 2 + 3)) / 9, 0, 1)
                ok &= w > 0
                np.add.at(sw, (cj[ok], ci[ok]), w[ok])
                np.add.at(swh, (cj[ok], ci[ok]), w[ok] * prof[ok])
                np.maximum.at(wmax, (cj[ok], ci[ok]), w[ok])
        # export resampled at 8 m, split into chunks
        ep = resample_line(pts, 8.0)
        cur, cur_c = [], None
        for x, z in ep:
            c = int((z + HALF) // CHUNK) * NC + int((x + HALF) // CHUNK)
            if not (0 <= c < NC * NC):
                cur, cur_c = [], None
                continue
            if c != cur_c and cur:
                cur.append((x, z))  # overlap one point to avoid gaps
                road_out[cur_c].append({"w": width, "k": kind, "p": [round(v, 1) for q in cur for v in q]})
                cur = [cur[-2]] if len(cur) > 1 else []
            cur_c = c
            cur.append((x, z))
        if len(cur) > 1:
            road_out[cur_c].append({"w": width, "k": kind, "p": [round(v, 1) for q in cur for v in q]})
    m = sw > 0
    h[m] = h[m] * (1 - wmax[m]) + (swh[m] / sw[m]) * wmax[m]

    # ---- land classes & colour
    cls = np.full((N, N), WATER, np.uint8)
    cls[landb] = GRASS
    slope = np.hypot(*np.gradient(h, CELL))
    jungle = landb & ((h > 14) | (slope > 0.14))
    cls[jungle] = JUNGLE

    def poly_mask(pred):
        return raster_polys(area_polygons(ways, rels, nodes, pred), 1) > 0.5

    woods = poly_mask(lambda t: t.get("natural") in ("wood", "scrub") or t.get("landuse") in ("forest", "orchard"))
    cls[woods & landb] = JUNGLE
    urban = poly_mask(lambda t: t.get("landuse") in ("residential", "commercial", "retail", "industrial"))
    cls[urban & landb] = URBAN
    grass = poly_mask(lambda t: t.get("landuse") in ("grass", "farmland", "meadow") or t.get("leisure") in ("golf_course", "park", "pitch"))
    cls[grass & landb] = GRASS
    sand = poly_mask(lambda t: t.get("natural") in ("beach", "sand"))
    beach = landb & (((d_land < 35) & (h < 3.5)) | sand)
    cls[beach] = SAND
    rock = poly_mask(lambda t: t.get("natural") in ("bare_rock",))
    cls[rock & landb] = ROCK
    fresh = poly_mask(lambda t: t.get("natural") == "water" or t.get("landuse") in ("reservoir", "basin"))

    # buildings
    bld_out = [[] for _ in range(NC * NC)]
    bld_polys = []
    nb = 0
    for nds, t in ways.values():
        if "building" not in t or len(nds) < 4 or nds[0] != nds[-1]:
            continue
        p = ring_xy(nds[:-1], nodes)
        if len(p) < 3:
            continue
        cx = sum(q[0] for q in p) / len(p)
        cz = sum(q[1] for q in p) / len(p)
        if abs(cx) >= HALF or abs(cz) >= HALF:
            continue
        lv = t.get("building:levels")
        try:
            hh = float(t["height"].replace("m", "")) if "height" in t else (float(lv) * 3.2 if lv else 0)
        except ValueError:
            hh = 0
        if hh <= 0:
            area = abs(sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))) / 2
            hh = 3.4 if area < 120 else (6.5 if area < 600 else 9.5)
            hh *= 0.85 + 0.3 * random.random()
        c = int((cz + HALF) // CHUNK) * NC + int((cx + HALF) // CHUNK)
        bld_out[c].append({"h": round(hh, 1), "p": [round(v, 1) for q in p for v in q]})
        bld_polys.append(p)
        nb += 1
    print("buildings:", nb)
    bmask = raster_polys(bld_polys, 1) > 0.5
    rmask_img = Image.new("L", (N, N), 0)
    rd = ImageDraw.Draw(rmask_img)
    for pts, width, kind, name in roads:
        rd.line([to_grid(x, z) for x, z in pts], fill=255 if kind != 2 else 128, width=max(1, int(round(width / CELL))))
    rmask = np.asarray(rmask_img)
    cls[(rmask > 0) & landb] = ROAD
    cls[bmask & landb] = BUILDING

    # colour map
    pal = {
        GRASS: (108, 140, 60), JUNGLE: (60, 104, 44), URBAN: (112, 118, 82), SAND: (226, 208, 160),
        ROAD: (90, 90, 88), BUILDING: (135, 132, 122), ROCK: (120, 115, 105),
    }
    col = np.zeros((N, N, 3), np.float32)
    for k, c in pal.items():
        col[cls == k] = c
    dirt = (rmask == 128) & landb
    col[dirt] = (150, 112, 74)
    # sea floor: turquoise shallow -> deep blue
    depth = np.clip(-h, 0, 30)
    t = np.clip(depth / 7, 0, 1)[..., None] ** 0.7
    sea = (1 - t) * np.array([200, 196, 150]) + t * np.array([30, 70, 90])
    col[~landb] = sea[~landb]
    col[fresh & landb] = (60, 90, 80)
    # variation noise
    noise = ndimage.gaussian_filter(rng.standard_normal((N, N)), 3) * 4 + ndimage.gaussian_filter(rng.standard_normal((N, N)), 1)
    col *= (1 + 0.08 * noise)[..., None]
    shade = np.clip(1 - slope * 0.6, 0.7, 1)[..., None]
    col[landb] *= shade[landb]
    col = np.clip(col, 0, 255).astype(np.uint8)
    Image.fromarray(col, "RGB").save(os.path.join(a.out, "colormap.png"), optimize=True)

    # ---- write binaries
    hq = (np.round(h / 0.05) * 0.05).astype("<f4")
    with open(os.path.join(a.out, "heights.bin"), "wb") as f:
        f.write(zlib.compress(hq.tobytes(), 9))
    with open(os.path.join(a.out, "landclass.bin"), "wb") as f:
        f.write(zlib.compress(cls.tobytes(), 9))

    with open(os.path.join(a.out, "roads.json"), "w") as f:
        json.dump(road_out, f, separators=(",", ":"))
    with open(os.path.join(a.out, "buildings.json"), "w") as f:
        json.dump(bld_out, f, separators=(",", ":"))

    # ---- places
    places = []

    def add(tags, lon, lat, kind):
        nm = tags.get("name:ru") or tags.get("name:en") or tags.get("name")
        if nm and any("\u0e00" <= ch <= "\u0e7f" for ch in nm):
            nm = tags.get("name:en")  # the game font has no Thai glyphs
        if not nm or any("\u0e00" <= ch <= "\u0e7f" for ch in nm):
            return
        x, z = to_local(lon, lat)
        if abs(x) < HALF and abs(z) < HALF:
            places.append({"n": nm, "en": tags.get("name:en") or nm, "k": kind, "x": round(x, 1), "z": round(z, 1)})

    def kind_of(t):
        if t.get("place") in ("town", "village", "suburb", "city"):
            return "town"
        if t.get("natural") == "beach":
            return "beach"
        if t.get("waterway") == "waterfall":
            return "waterfall"
        if t.get("tourism") in ("viewpoint", "attraction") or t.get("historic"):
            return "sight"
        if t.get("aeroway") == "aerodrome":
            return "airport"
        if t.get("amenity") == "place_of_worship" and t.get("religion") == "buddhist":
            return "temple"
        return None

    for nid, t in pois.items():
        k = kind_of(t)
        if k:
            add(t, *nodes[nid], k)
    for nds, t in ways.values():
        k = kind_of(t)
        if k and nds:
            pts = [nodes[n] for n in nds if n in nodes]
            if pts:
                add(t, sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), k)
    seen = set()
    places = [p for p in places if not (p["n"] in seen or seen.add(p["n"]))]
    print("places:", len(places), [p["n"] for p in places if p["k"] == "town"])
    with open(os.path.join(a.out, "places.json"), "w") as f:
        json.dump(places, f, ensure_ascii=False, separators=(",", ":"))
    for fn in os.listdir(a.out):
        print(f"  {fn}: {os.path.getsize(os.path.join(a.out, fn)) / 1e6:.2f} MB")


if __name__ == "__main__":
    random.seed(3)
    main()
