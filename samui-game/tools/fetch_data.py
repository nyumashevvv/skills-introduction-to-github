#!/usr/bin/env python3
"""Downloads the raw data for Koh Samui: OpenStreetMap XML in small chunks from the
official OSM API, and Terrarium elevation tiles (zoom 13) from AWS Terrain Tiles.

  python3 tools/fetch_data.py raw/      # then: python3 tools/build_map.py --osm raw/osm --dem raw/dem
"""
import math, os, sys, time, urllib.request

out = sys.argv[1] if len(sys.argv) > 1 else "raw"
UA = {"User-Agent": "samui-ride-map-builder/0.1"}


def get(url, path):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                open(path, "wb").write(r.read())
            return
        except Exception as e:
            print("retry", url, e)
            time.sleep(5 * (attempt + 1))
    raise SystemExit("failed: " + url)


os.makedirs(os.path.join(out, "osm"), exist_ok=True)
for i in range(7):
    for j in range(7):
        lo, la = 99.90 + 0.03 * i, 9.39 + 0.03 * j
        f = os.path.join(out, "osm", f"c_{i}_{j}.osm")
        if not os.path.exists(f):
            get(f"https://api.openstreetmap.org/api/0.6/map?bbox={lo:.2f},{la:.2f},{lo + 0.03:.2f},{la + 0.03:.2f}", f)
            time.sleep(1)  # be gentle with the OSM API

os.makedirs(os.path.join(out, "dem"), exist_ok=True)
z = 13


def tile(lon, lat):
    n = 2 ** z
    return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)


x0, y0 = tile(99.90, 9.60)
x1, y1 = tile(100.11, 9.39)
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        f = os.path.join(out, "dem", f"{x}_{y}.png")
        if not os.path.exists(f):
            get(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png", f)
print("done")
