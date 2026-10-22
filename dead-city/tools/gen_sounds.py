"""Synthesizes every sound effect in sounds/. Run from the project root."""
import wave, struct, math, random
SR = 22050
random.seed(11)


def save(name, s, gain=0.9):
    peak = max(1e-6, max(abs(x) for x in s))
    with wave.open(f'sounds/{name}.wav', 'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b''.join(struct.pack('<h', int(x / peak * gain * 32000)) for x in s))

def n(sec): return int(sec * SR)
def noise(): return random.uniform(-1, 1)
def lowpass(s, a):
    out, y = [], 0.0
    for x in s:
        y += a * (x - y); out.append(y)
    return out
def highpass(s, a):
    return [x - l for x, l in zip(s, lowpass(s, a))]
def bandpass(s, f, q=4.0):
    w0 = 2 * math.pi * f / SR; al = math.sin(w0) / (2 * q)
    b0, b2 = al, -al; a0, a1, a2 = 1 + al, -2 * math.cos(w0), 1 - al
    out, x1, x2, y1, y2 = [], 0, 0, 0, 0
    for x in s:
        y = (b0 * x + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x, y1, y
        out.append(y)
    return out
def tone(freq_fn, dur, amp_fn, shape='sine'):
    out, ph = [], 0.0
    for i in range(n(dur)):
        t = i / SR
        ph += 2 * math.pi * freq_fn(t) / SR
        if shape == 'sine': v = math.sin(ph)
        elif shape == 'square': v = 1 if math.sin(ph) > 0 else -1
        else: v = ((ph / (2 * math.pi)) % 1) * 2 - 1
        out.append(v * amp_fn(t))
    return out
def mix(*tracks):
    L = max(len(t) for t in tracks)
    return [sum(t[i] if i < len(t) else 0 for t in tracks) for i in range(L)]
def delay(s, sec): return [0.0] * n(sec) + s
def scale(s, k): return [x * k for x in s]
def env_noise(dur, decay, lp=None):
    s = [noise() * math.exp(-i / SR * decay) for i in range(n(dur))]
    return lowpass(s, lp) if lp else s
def click(f, d=0.05, decay=70):
    return mix(tone(lambda t: f, d, lambda t: math.exp(-t * decay)), scale(env_noise(d, decay * 1.5), 0.6))

# weapons
save('pistol', mix(env_noise(0.3, 35, 0.55), scale(tone(lambda t: 180 * math.exp(-t * 15) + 50, 0.25, lambda t: math.exp(-t * 28)), 0.9)))
save('rifle', mix(env_noise(0.35, 24, 0.4), scale(tone(lambda t: 120 * math.exp(-t * 10) + 40, 0.3, lambda t: math.exp(-t * 20)), 1.0)))
whoosh = [noise() * min(1, i / n(0.05)) * math.exp(-i / SR * 3) for i in range(n(0.9))]
save('rocket_launch', mix(lowpass(env_noise(0.4, 12), 0.2), scale(lowpass(whoosh, 0.3), 0.7), scale(tone(lambda t: 60, 0.4, lambda t: math.exp(-t * 8)), 0.8)))
save('explosion', mix(lowpass(env_noise(1.6, 2.8), 0.07), tone(lambda t: 55 * math.exp(-t * 1.5) + 22, 1.6, lambda t: math.exp(-t * 3)), scale(env_noise(0.15, 30, 0.6), 0.5)))
sw = [noise() * math.sin(math.pi * min(1, i / n(0.16))) * math.exp(-i / SR * 8) for i in range(n(0.22))]
save('knife_swing', bandpass(sw, 1800, 1.2), 0.5)
save('knife_hit', mix(lowpass(env_noise(0.18, 25), 0.12), tone(lambda t: 90, 0.15, lambda t: math.exp(-t * 30))), 0.7)
save('flesh_hit', mix(lowpass(env_noise(0.12, 40), 0.18), tone(lambda t: 140, 0.08, lambda t: math.exp(-t * 50))), 0.55)
save('reload_pistol', mix(delay(click(800), 0.1), delay(click(500, 0.08, 40), 0.55), delay(click(1400), 0.95)), 0.6)
save('reload_rifle', mix(delay(click(900), 0.1), delay(click(600, 0.1, 40), 0.8), delay(click(1300), 1.4), delay(click(1100), 1.5)), 0.6)
save('reload_rocket', mix(delay(lowpass(env_noise(0.5, 6), 0.15), 0.2), delay(click(400, 0.12, 30), 1.6), delay(click(900), 2.0)), 0.6)
save('empty', click(1500, 0.05, 90), 0.4)
save('weapon_switch', mix(click(700, 0.05, 80), delay(click(1100, 0.04, 90), 0.12)), 0.4)
save('impact', mix(env_noise(0.08, 60, 0.6), click(2500, 0.03, 120)), 0.35)

# player / world
save('hurt', mix(tone(lambda t: 110 * math.exp(-t * 5), 0.3, lambda t: math.exp(-t * 14)), lowpass(env_noise(0.3, 20), 0.15)), 0.8)
save('footstep', mix(lowpass(env_noise(0.12, 45), 0.25), tone(lambda t: 70, 0.08, lambda t: math.exp(-t * 60))), 0.35)
save('pickup', mix(*[delay(tone(lambda t, f=f: f, 0.12, lambda t: math.exp(-t * 20)), k * 0.07) for k, f in enumerate([660, 880, 1320])]), 0.5)
save('key_pickup', mix(tone(lambda t: 1200, 0.1, lambda t: 1), delay(tone(lambda t: 1600, 0.15, lambda t: math.exp(-t * 10)), 0.12)), 0.4)
save('flashlight', click(2000, 0.03, 120), 0.3)
door = [noise() * (0.6 + 0.4 * math.sin(i / SR * 70)) * min(1, i / n(0.1)) * min(1, (n(1.0) - i) / n(0.2)) for i in range(n(1.0))]
save('door_open', mix(lowpass(door, 0.06), delay(click(300, 0.15, 25), 0.9)), 0.7)
save('door_locked', mix(tone(lambda t: 160, 0.25, lambda t: 1, 'square'), delay(tone(lambda t: 120, 0.3, lambda t: 1, 'square'), 0.3)), 0.3)
save('radio', mix(scale(highpass(env_noise(0.25, 8), 0.3), 0.5), delay(tone(lambda t: 1000, 0.08, lambda t: 1), 0.05)), 0.4)
save('alarm', lowpass(tone(lambda t: 650 + 250 * (1 if (t * 2) % 1 < 0.5 else 0), 2.0, lambda t: 1, 'square'), 0.3), 0.35)

# Zombie voices are real CC0 recordings in sounds/zombie/ (see tools/fetch_assets.sh).

# loops (loop_mode is set in their .import files)
heli = []
for i in range(n(2.0)):
    t = i / SR
    thump = math.exp(-((t * 7) % 1) * 9)
    heli.append(noise() * (0.25 + thump) + math.sin(t * 2 * math.pi * 55) * thump * 0.8)
save('helicopter', lowpass(heli, 0.12), 0.7)
wind = lowpass([noise() for _ in range(n(8.0))], 0.02)
wind = [w * (0.6 + 0.4 * math.sin(i / SR * 2 * math.pi / 8.0)) for i, w in enumerate(wind)]
amb = mix(wind, scale(tone(lambda t: 55, 8.0, lambda t: 0.25 + 0.1 * math.sin(t * 2 * math.pi / 4.0)), 0.5))
fade = n(0.3)
for i in range(fade):
    k = i / fade
    amb[i] = amb[i] * k + amb[-fade + i] * (1 - k)
save('ambience', amb[:-fade], 0.5)
# shotgun (own seed so adding it does not change the sounds above)
random.seed(23)
blast = mix(lowpass(env_noise(0.6, 9), 0.3), scale(lowpass(env_noise(0.25, 25), 0.7), 0.6),
            tone(lambda t: 90 * math.exp(-t * 8) + 35, 0.5, lambda t: math.exp(-t * 9)))
save('shotgun', blast)
rack = lambda f1, f2: mix(click(f1, 0.07, 45), delay(lowpass(env_noise(0.08, 30), 0.3), 0.02), delay(click(f2, 0.06, 55), 0.12))
save('shotgun_pump', mix(rack(500, 900), delay(rack(700, 1200), 0.16)), 0.6)
save('shell_insert', mix(click(1800, 0.04, 90), delay(click(600, 0.07, 50), 0.05)), 0.5)

# bosses (own seed as well)
random.seed(31)
save('slam', mix(lowpass(env_noise(1.2, 4), 0.05), tone(lambda t: 48 * math.exp(-t * 2) + 20, 1.0, lambda t: math.exp(-t * 4)),
                 delay(scale(lowpass(env_noise(0.8, 6), 0.25), 0.35), 0.05)))
save('spit', mix(bandpass(env_noise(0.35, 12), 900, 1.5), scale(lowpass(env_noise(0.2, 20), 0.15), 0.8)), 0.6)
save('splash', mix(lowpass(env_noise(0.5, 9), 0.2), scale(highpass(env_noise(0.7, 5), 0.5), 0.25)), 0.6)
save('shield_hit', mix(tone(lambda t: 1250, 0.35, lambda t: math.exp(-t * 14)), scale(tone(lambda t: 1890, 0.3, lambda t: math.exp(-t * 18)), 0.6),
                       scale(env_noise(0.05, 80, 0.6), 0.8)), 0.45)
print('sounds ok')
