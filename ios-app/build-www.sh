#!/bin/sh
# Builds www/index.html for the iOS app: the game page with the font bundled locally (works offline).
set -e
cd "$(dirname "$0")"
{
  printf '%s\n' '<!doctype html>' '<html lang="ru">' '<head>' \
    '<meta charset="utf-8">' \
    '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">' \
    '<meta name="theme-color" content="#1e1b2e">' \
    '<link rel="stylesheet" href="fonts/pixelify.css">' \
    '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>' \
    '</head>' '<body>'
  grep -v 'fonts.googleapis.com\|fonts.gstatic.com' ../pixel-game/game.html
  printf '%s\n' '</body>' '</html>'
} > www/index.html
echo "built www/index.html"
