#!/usr/bin/env python3
"""Turns the Godot web export (build/web) into a static bundle (build/site) whose
large files are gzip-compressed (*.gz.wasm, a type static hosts serve) and unpacked in the browser, so every file
stays small enough for simple static hosting."""
import gzip, os, shutil, sys

src = sys.argv[1] if len(sys.argv) > 1 else "build/web"
dst = sys.argv[2] if len(sys.argv) > 2 else "build/site"
shutil.rmtree(dst, ignore_errors=True)
os.makedirs(dst)
big = ["index.wasm", "index.pck"]
for f in os.listdir(src):
    if f in big:
        with open(os.path.join(src, f), "rb") as i, gzip.open(os.path.join(dst, f + ".gz.wasm"), "wb", 9) as o:
            shutil.copyfileobj(i, o)
    elif f != "index.html" and not f.endswith(".png"):
        shutil.copy(os.path.join(src, f), dst)

shim = """<script>
(function () {
  const packed = { 'index.wasm': 'application/wasm', 'index.pck': 'application/octet-stream' };
  const realFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const url = typeof input === 'string' ? input : input.url;
    const name = url.split('?')[0].split('/').pop();
    if (packed[name]) {
      return realFetch(url + '.gz.wasm', init).then(function (r) {
        if (!r.ok) return r;
        return r.arrayBuffer().then(function (buf) {
          const head = new Uint8Array(buf, 0, 2);
          // the host may already have removed the gzip layer (Content-Encoding)
          let body = new Blob([buf]).stream();
          if (head[0] === 0x1f && head[1] === 0x8b) body = body.pipeThrough(new DecompressionStream('gzip'));
          return new Response(body, { status: 200, headers: { 'Content-Type': packed[name] } });
        });
      });
    }
    return realFetch(input, init);
  };
})();
</script>
"""
import re
src_html = open(os.path.join(src, "index.html"), encoding="utf-8").read()
config = re.search(r"const GODOT_CONFIG = (\{.*?\});", src_html).group(1)
page = """<title>Samui Ride</title>
<style>
:root { --sea: #0b2a36; --sea-deep: #06161d; --sand: #e9d9ae; --palm: #7fbf5a; --ink: #eef4f2; --muted: #9db7b5;
  --display: "Space Grotesk", system-ui, sans-serif; --body: "Inter", system-ui, sans-serif; color-scheme: dark; }
html, body { height: 100%; }
body { margin: 0; background: var(--sea-deep); color: var(--ink); font-family: var(--body); overflow: hidden; }
#canvas { display: block; width: 100%; height: 100%; outline: none; touch-action: none; }
#boot { position: fixed; inset: 0; display: grid; place-items: center; background:
  radial-gradient(120% 90% at 50% 100%, var(--sea) 0%, var(--sea-deep) 70%); padding-inline: max(16px, env(safe-area-inset-left, 0px)) max(16px, env(safe-area-inset-right, 0px)); }
#boot[hidden] { display: none !important; }
.card { width: min(440px, 100%); display: grid; gap: 14px; }
.card h1 { font-family: var(--display); font-size: clamp(30px, 6vw, 44px); margin: 0; letter-spacing: -0.01em; text-wrap: balance; }
.card h1 span { color: var(--palm); }
.card p { margin: 0; color: var(--muted); line-height: 1.5; font-size: 15px; }
.coords { font-variant-numeric: tabular-nums; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--sand); }
.bar { height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; }
.bar i { display: block; height: 100%; width: 0%; background: linear-gradient(90deg, var(--sand), var(--palm)); transition: width .2s; }
#status { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }
.err { color: #ffb4a8 !important; }
@media (prefers-reduced-motion: reduce) { .bar i { transition: none; } }
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=Space+Grotesk:wght@600&display=swap">
<canvas id="canvas" tabindex="0">Нужен браузер с поддержкой WebGL 2.</canvas>
<div id="boot">
  <div class="card">
    <div class="coords">9.50° N · 100.01° E · 1 : 1</div>
    <h1>Samui <span>Ride</span></h1>
    <p>Остров Ко Самуи в натуральную величину: настоящие дороги, здания и рельеф. Загружаем остров (около 20 МБ).</p>
    <div class="bar"><i id="bar"></i></div>
    <div id="status">Загрузка…</div>
  </div>
</div>
""" + shim + """<script src="index.js"></script>
<script>
(function () {
  const GODOT_CONFIG = """ + config + """;
  const bar = document.getElementById('bar');
  const status = document.getElementById('status');
  const canvas = document.getElementById('canvas');
  const engine = new Engine(GODOT_CONFIG);
  const missing = Engine.getMissingFeatures({ threads: false });
  if (missing.length) {
    status.textContent = 'Браузер не поддерживает: ' + missing.join(', ');
    status.className = 'err';
    return;
  }
  engine.startGame({
    onProgress: function (cur, total) {
      if (total > 0) {
        bar.style.width = Math.round(cur / total * 100) + '%';
        status.textContent = (cur / 1e6).toFixed(1) + ' из ' + (total / 1e6).toFixed(1) + ' МБ';
      } else {
        status.textContent = (cur / 1e6).toFixed(1) + ' МБ';
      }
    },
  }).then(function () {
    document.getElementById('boot').hidden = true;
    canvas.focus();
  }).catch(function (err) {
    status.textContent = 'Не удалось запустить игру: ' + (err && err.message ? err.message : err);
    status.className = 'err';
  });
  canvas.addEventListener('pointerdown', function () { canvas.focus(); });
})();
</script>
"""
open(os.path.join(dst, "index.html"), "w", encoding="utf-8").write(page)
for f in sorted(os.listdir(dst)):
    print(f"{f}: {os.path.getsize(os.path.join(dst, f)) / 1e6:.2f} MB")
