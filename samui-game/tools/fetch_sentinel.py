#!/usr/bin/env python3
"""Builds a cloud-free Sentinel-2 true-colour image of Koh Samui on the game grid.

Searches the Earth Search STAC catalogue (AWS open data), reads the 10 m TCI
image and the scene classification (SCL) of the clearest scenes, masks clouds,
shadows and haze per pixel and takes the median of what is left.

  python3 tools/fetch_sentinel.py raw/s2_rgb.npy
Contains modified Copernicus Sentinel data.
"""
import json, math, sys, urllib.request
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform as warp_transform
from scipy import ndimage

LON0, LAT0 = 100.01, 9.495
KX = 111320.0 * math.cos(math.radians(LAT0))
KZ = 110574.0
N, CELL, HALF = 2400, 10.0, 12000.0
out = sys.argv[1] if len(sys.argv) > 1 else "s2_rgb.npy"
SCENES_PER_TILE = int(sys.argv[2]) if len(sys.argv) > 2 else 10

q = {"collections": ["sentinel-2-l2a"], "bbox": [99.90, 9.39, 100.11, 9.60],
     "datetime": "2023-01-01T00:00:00Z/2026-12-31T00:00:00Z", "query": {"eo:cloud_cover": {"lt": 15}},
     "limit": 100, "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}]}
req = urllib.request.Request("https://earth-search.aws.element84.com/v1/search", json.dumps(q).encode(),
                             {"Content-Type": "application/json"})
feats = json.load(urllib.request.urlopen(req))["features"]
by_tile = {}
for f in feats:
    if (f["properties"].get("s2:nodata_pixel_percentage") or 0) > 1:
        continue
    by_tile.setdefault(f["properties"]["s2:mgrs_tile"] if "s2:mgrs_tile" in f["properties"] else f["id"].split("_")[1], []).append(f)

# game grid -> lon/lat
g = np.arange(N) * CELL - HALF
X, Z = np.meshgrid(g, g)
lon = X / KX + LON0
lat = -Z / KZ + LAT0

stack = []
for tile, fs in by_tile.items():
    for f in fs[:SCENES_PER_TILE]:
        tci, scl = f["assets"]["visual"]["href"], f["assets"]["scl"]["href"]
        try:
            with rasterio.open(tci) as src:
                xs, ys = warp_transform("EPSG:4326", src.crs, lon.ravel(), lat.ravel())
                xs, ys = np.array(xs).reshape(N, N), np.array(ys).reshape(N, N)
                win = from_bounds(xs.min() - 50, ys.min() - 50, xs.max() + 50, ys.max() + 50, src.transform)
                win = win.round_offsets().round_lengths()
                rgb = src.read(window=win, boundless=True, fill_value=0).astype(np.float32)
                wt = src.window_transform(win)
                col = (xs - wt.c) / wt.a - 0.5
                row = (ys - wt.f) / wt.e - 0.5
            with rasterio.open(scl) as s2:
                w2 = from_bounds(xs.min() - 50, ys.min() - 50, xs.max() + 50, ys.max() + 50, s2.transform)
                w2 = w2.round_offsets().round_lengths()
                cls = s2.read(1, window=w2, boundless=True, fill_value=0)
                wt2 = s2.window_transform(w2)
                col2 = (xs - wt2.c) / wt2.a - 0.5
                row2 = (ys - wt2.f) / wt2.e - 0.5
        except Exception as e:
            print("skip", f["id"], e)
            continue
        c = ndimage.map_coordinates(cls, [row2, col2], order=0, mode="constant", cval=0)
        # 0 nodata, 1 saturated, 3 cloud shadow, 8/9 cloud, 10 cirrus
        bad = np.isin(c, [0, 1, 3, 8, 9, 10])
        bad = ndimage.binary_dilation(bad, iterations=3)
        img = np.stack([ndimage.map_coordinates(rgb[b], [row, col], order=1, mode="constant", cval=0) for b in range(3)], -1)
        bad |= img.sum(-1) == 0
        img[bad] = np.nan
        stack.append(img)
        print(f["id"], f"clear {100 * (1 - bad.mean()):.1f}%")

stack = np.array(stack)
med = np.nanmedian(stack, axis=0)
holes = np.isnan(med[..., 0])
print("pixels with no clear view:", holes.mean())
np.save(out, np.nan_to_num(med, nan=-1).astype(np.float32))
