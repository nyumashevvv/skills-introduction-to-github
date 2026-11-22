# Samui Ride

Прототип игры на Godot 4.3: остров Ко Самуи (Таиланд) в масштабе 1:1. Катаешься на скутере по настоящим дорогам острова.

- **Карта**: 24 × 24 км, рельеф с шагом 10 м (до 630 м над уровнем моря).
- **Дороги**: около 10 750 из OpenStreetMap и TomTom (через Overture Maps).
- **Здания**: 76 тыс. контуров из Overture Maps — это OSM, Google Open Buildings и Microsoft ML Buildings без дублей.
- **Земля**: безоблачная мозаика спутниковых снимков Sentinel-2 (10 м), собранная из 20 снимков 2023–2026 годов.
- **Места**: береговая линия, пляжи, посёлки, водопады и храмы из OpenStreetMap.
- **Рельеф**: SRTM через AWS Terrain Tiles.
- **Подгрузка**: местность грузится кусками 1,2 × 1,2 км, у каждого куска три уровня детализации. Дороги, дома и пальмы строятся вокруг игрока.

## Управление

| Клавиша | Действие |
|---|---|
| W / S или ↑ / ↓ | газ / тормоз (задний ход) |
| A / D или ← / → | руль |
| Shift | турбо ×4 (чтобы быстро объехать остров) |
| M или Tab | карта острова (клик по карте — телепорт) |
| C | сменить камеру |
| R | вернуться на ближайшую дорогу |

На телефоне появляются экранные кнопки.

## Как открыть

1. Установи [Godot 4.3](https://godotengine.org/download/archive/4.3-stable/).
2. В менеджере проектов нажми «Импорт» и выбери `samui-game/project.godot`.
3. Нажми F5.

Экспорт: пресеты «Web» и «Windows» лежат в `export_presets.cfg`. После веб-экспорта команда `python3 tools/package_web.py` сжимает большие файлы для простого хостинга (результат в `build/site`).

## Пересборка карты из исходных данных

```bash
pip install numpy pillow scipy
pip install duckdb pyarrow shapely rasterio
python3 tools/fetch_data.py raw/                  # OSM + рельеф
python3 tools/fetch_overture.py raw/overture      # здания OSM/Google/Microsoft + дороги TomTom
python3 tools/fetch_sentinel.py raw/s2_rgb.npy    # спутниковая мозаика (~3 мин)
python3 tools/build_map.py --osm raw/osm --dem raw/dem --overture raw/overture --s2 raw/s2_rgb.npy
```

## Устройство кода

- `scripts/world.gd`: высоты, подгрузка кусков и уровни детализации; меши дорог, домов и пальм.
- `scripts/scooter.gd`: аркадная физика скутера прямо по карте высот; столкновения с домами и морем.
- `scripts/hud.gd`: спидометр, миникарта, большая карта с телепортом, сенсорное управление.
- `scripts/props.gd`: процедурные модели (пальма, скутер с водителем, Большой Будда).
- `tools/build_map.py`: превращает OSM и рельеф в `data/*`.

## Лицензии данных

- Картографические данные © участники OpenStreetMap, ODbL.
- Overture Maps Foundation, ODbL; в том числе Google Open Buildings (CC BY 4.0 / ODbL) и Microsoft ML Building Footprints (ODbL), а также данные TomTom.
- Спутниковые данные: модифицированные данные Copernicus Sentinel (2023–2026).
- Рельеф: SRTM и другие открытые источники через AWS Terrain Tiles.
