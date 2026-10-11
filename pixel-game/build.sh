#!/bin/sh
# Wraps pixel-game/game.html into a standalone page (docs/index.html) for GitHub Pages / iPhone home screen.
set -e
cd "$(dirname "$0")/.."
mkdir -p docs
{
  printf '%s\n' '<!doctype html>' '<html lang="ru">' '<head>' \
    '<meta charset="utf-8">' \
    '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">' \
    '<meta name="apple-mobile-web-app-capable" content="yes">' \
    '<meta name="mobile-web-app-capable" content="yes">' \
    '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">' \
    '<meta name="apple-mobile-web-app-title" content="Тихолесье">' \
    '<meta name="theme-color" content="#1e1b2e">' \
    '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>' \
    '</head>' '<body>'
  cat pixel-game/game.html
  printf '%s\n' '</body>' '</html>'
} > docs/index.html
echo "built docs/index.html"
