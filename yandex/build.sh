#!/bin/sh
# Builds the Yandex Games archive: yandex/dist/ (index.html + fonts) and yandex/tikholesye-yandex.zip.
# The SDK is loaded from /sdk.js, which Yandex serves next to the game; nothing else is fetched from outside.
set -e
cd "$(dirname "$0")"
rm -rf dist && mkdir -p dist/fonts
cp ../ios-app/www/fonts/*.woff2 ../ios-app/www/fonts/pixelify.css ../ios-app/www/fonts/OFL.txt dist/fonts/
{
  printf '%s\n' '<!doctype html>' '<html lang="ru">' '<head>' \
    '<meta charset="utf-8">' \
    '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">' \
    '<meta name="theme-color" content="#1e1b2e">' \
    '<link rel="icon" href="data:,">' \
    '<script src="/sdk.js"></script>' \
    '<link rel="stylesheet" href="fonts/pixelify.css">' \
    '</head>' '<body>'
  grep -v 'fonts.googleapis.com\|fonts.gstatic.com' ../pixel-game/game.html
  printf '%s\n' '</body>' '</html>'
} > dist/index.html
rm -f tikholesye-yandex.zip
python3 -c "
import zipfile, os
with zipfile.ZipFile('tikholesye-yandex.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk('dist'):
        for f in files:
            p = os.path.join(root, f); z.write(p, os.path.relpath(p, 'dist'))
"
echo "built yandex/tikholesye-yandex.zip ($(du -k tikholesye-yandex.zip | cut -f1) KB)"
