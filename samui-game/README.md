# Samui Ride

Остров Ко Самуи (Таиланд) в масштабе 1:1 на Godot 4.3 (рендер Forward+, для ПК). Катаешься на скутере по настоящим дорогам острова.

## Что есть
- **Остров 24 × 24 км.** Рельеф с шагом 10 м (до 630 м над морем), земля по безоблачной мозаике спутниковых снимков Sentinel-2.
- **Дороги.** Около 10 750 штук из OpenStreetMap и TomTom.
  - Ширина и число полос берутся из тегов OSM.
  - Покрытие: асфальт с разметкой, бетонные сои со швами и лежачими полицейскими, красные грунтовки.
  - На перекрёстках разметки нет.
  - В посёлках тротуары, крашеные бордюры и фонари. Вдоль дорог электрические столбы с проводами, на кольцевой синие указатели.
- **76 тыс. зданий** из Overture Maps (OSM, Google Open Buildings, Microsoft). Стиль выбирается по месту:
  - шопхаусы с навесами и вывесками вдоль главных дорог;
  - бунгало и отели у моря;
  - виллы с бассейнами на склонах;
  - храмы с трёхъярусными крышами и золотыми чофа;
  - склады;
  - деревянные дома Fisherman's Village в Бопхуте.
- **Растительность.** Кокосовые пальмы трёх видов, деревья джунглей, бананы, кусты, бугенвиллея, трава. Плотность зависит от типа местности. Три уровня детализации, видно до 3,6 км, листья колышутся на ветру.
- **Достопримечательности.**
  - Big Buddha (Wat Phra Yai) с лестницей и нагами;
  - 18-рукая Гуаньинь и Майтрейя в Wat Plai Laem;
  - скалы Hin Ta & Hin Yai;
  - все пирсы из OSM, включая пирс Натона. На пирсы можно заехать.
- **Модели из Blender:** скутер и водитель в чёрно-зелёной экипировке, растения, достопримечательности.

## Управление

| Клавиша | Действие |
|---|---|
| W / S или ↑ / ↓ | газ / тормоз (задний ход) |
| A / D или ← / → | руль |
| Shift | турбо ×4 |
| M или Tab | карта острова (клик по карте — телепорт) |
| C | сменить камеру |
| R | вернуться на ближайшую дорогу |
| Q | качество: высокое → низкое → среднее |

## Как открыть
1. Установи [Godot 4.3](https://godotengine.org/download/archive/4.3-stable/), обычную версию, не .NET.
2. Нажми «Импорт» и выбери `project.godot`, затем F5.
3. Нужна видеокарта с поддержкой Vulkan.

На высоком качестве кадр — около 1,7 млн треугольников, на низком — около 0,7 млн.

## Как пересобрать данные и модели
```bash
pip install numpy pillow scipy duckdb pyarrow shapely rasterio
python3 tools/fetch_data.py raw/                  # OSM + рельеф
python3 tools/fetch_overture.py raw/overture      # здания OSM/Google/Microsoft + дороги TomTom
python3 tools/fetch_sentinel.py raw/s2_rgb.npy    # спутниковая мозаика (~3 мин)
python3 tools/build_map.py --osm raw/osm --dem raw/dem --overture raw/overture --s2 raw/s2_rgb.npy

# модели (Blender 4.2)
python3 tools/blender/make_leaf_textures.py tools/blender/tex
blender -b -P tools/blender/make_vegetation.py -- models/vegetation.glb
blender -b -P tools/blender/make_landmarks.py -- models/landmarks.glb
blender -b -P tools/blender/make_scooter_rider.py -- models/scooter_rider.glb
```
Файлы `.blend` лежат в `tools/blender/`, их можно править руками и экспортировать в glTF поверх файлов в `models/`.

## Устройство кода
- `scripts/world.gd`: рельеф и подгрузка кусков; дороги, тротуары, столбы, фонари; здания по стилям.
- `scripts/vegetation.gd`: растительность ячейками по 150 м с тремя уровнями детализации и травой.
- `scripts/landmarks.gd`: достопримечательности и пирсы.
- `scripts/scooter.gd`, `scripts/hud.gd`, `scripts/main.gd`: езда, интерфейс, окружение и качество.
- `shaders/`: земля, вода, дороги, фасады, растительность.
- `docs/reference.md`: заметки о том, как выглядит Самуи, с источниками.

## Лицензии данных
- Картографические данные © участники OpenStreetMap, ODbL.
- Overture Maps Foundation, ODbL, в том числе Google Open Buildings (CC BY 4.0 / ODbL), Microsoft ML Building Footprints (ODbL) и данные TomTom.
- Спутниковые данные: модифицированные данные Copernicus Sentinel (2023–2026).
- Рельеф: SRTM и другие открытые источники через AWS Terrain Tiles.
