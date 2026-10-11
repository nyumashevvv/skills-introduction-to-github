# Кристаллы Тихолесья: iOS-приложение

Обёртка над игрой на Capacitor 8.5. Игра лежит в `www/` и работает без интернета (шрифт Pixelify Sans встроен, лицензия OFL: `www/fonts/OFL.txt`).

## Что уже готово

- Xcode-проект `ios/App` (Swift Package Manager, без CocoaPods).
- Название на экране «Домой»: «Тихолесье». Bundle ID: `com.tikholesye.crystals` (поменяйте на свой в Xcode и в `capacitor.config.json`).
- Иконка 1024×1024 и экран загрузки уже в `ios/App/App/Assets.xcassets`.
- В `Info.plist` указано, что шифрование не используется, и включён полноэкранный режим.
- Тексты для App Store, скриншоты и иконка: папка `../store`. Политика конфиденциальности: `../docs/privacy.html`.

## Сборка на Mac

Нужны Xcode 16 или новее и Node.js 20 или новее.

```bash
cd ios-app
npm install
npm run sync      # собирает www/index.html из ../pixel-game/game.html и копирует в Xcode-проект
npm run open      # открывает проект в Xcode
```

В Xcode:
1. Выберите цель **App** → **Signing & Capabilities** → свою команду (Team), включите автоматическую подпись.
2. При необходимости поменяйте **Bundle Identifier**.
3. Подключите iPhone и нажмите ▶, чтобы проверить игру.
4. **Product → Archive**, затем **Distribute App → App Store Connect → Upload**.

После каждого изменения игры запускайте `npm run sync` ещё раз.
