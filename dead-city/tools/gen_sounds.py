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

# weapons. Gunshots (pistol, rifle, shotgun, revolver, smg, sniper) are CC0 recordings now (tools/fetch_assets.sh);
# the old synthesised ones are still computed so the sounds below keep their noise.
_ = (mix(env_noise(0.3, 35, 0.55), scale(tone(lambda t: 180 * math.exp(-t * 15) + 50, 0.25, lambda t: math.exp(-t * 28)), 0.9)))
_ = (mix(env_noise(0.35, 24, 0.4), scale(tone(lambda t: 120 * math.exp(-t * 10) + 40, 0.3, lambda t: math.exp(-t * 20)), 1.0)))
whoosh = [noise() * min(1, i / n(0.05)) * math.exp(-i / SR * 3) for i in range(n(0.9))]
save('rocket_launch', mix(lowpass(env_noise(0.4, 12), 0.2), scale(lowpass(whoosh, 0.3), 0.7), scale(tone(lambda t: 60, 0.4, lambda t: math.exp(-t * 8)), 0.8)))
save('explosion', mix(lowpass(env_noise(1.6, 2.8), 0.07), tone(lambda t: 55 * math.exp(-t * 1.5) + 22, 1.6, lambda t: math.exp(-t * 3)), scale(env_noise(0.15, 30, 0.6), 0.5)))
sw = [noise() * math.sin(math.pi * min(1, i / n(0.16))) * math.exp(-i / SR * 8) for i in range(n(0.22))]
save('knife_swing', bandpass(sw, 1800, 1.2), 0.5)
save('knife_hit', mix(lowpass(env_noise(0.18, 25), 0.12), tone(lambda t: 90, 0.15, lambda t: math.exp(-t * 30))), 0.7)
save('flesh_hit', mix(lowpass(env_noise(0.12, 40), 0.18), tone(lambda t: 140, 0.08, lambda t: math.exp(-t * 50))), 0.55)
_ = mix(delay(click(800), 0.1), delay(click(500, 0.08, 40), 0.55), delay(click(1400), 0.95))  # reload_pistol: now a CC0 recording; still computed so the sounds below keep their noise
_ = mix(delay(click(900), 0.1), delay(click(600, 0.1, 40), 0.8), delay(click(1300), 1.4), delay(click(1100), 1.5))  # reload_rifle: now a CC0 recording; still computed so the sounds below keep their noise
_ = mix(delay(lowpass(env_noise(0.5, 6), 0.15), 0.2), delay(click(400, 0.12, 30), 1.6), delay(click(900), 2.0))  # reload_rocket: now a CC0 recording; still computed so the sounds below keep their noise
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
_ = blast  # shotgun: now a CC0 recording
rack = lambda f1, f2: mix(click(f1, 0.07, 45), delay(lowpass(env_noise(0.08, 30), 0.3), 0.02), delay(click(f2, 0.06, 55), 0.12))
_ = mix(rack(500, 900), delay(rack(700, 1200), 0.16))  # shotgun_pump: now a CC0 recording; still computed so the sounds below keep their noise
_ = mix(click(1800, 0.04, 90), delay(click(600, 0.07, 50), 0.05))  # shell_insert: now a CC0 recording; still computed so the sounds below keep their noise

# bosses (own seed as well)
random.seed(31)
save('slam', mix(lowpass(env_noise(1.2, 4), 0.05), tone(lambda t: 48 * math.exp(-t * 2) + 20, 1.0, lambda t: math.exp(-t * 4)),
                 delay(scale(lowpass(env_noise(0.8, 6), 0.25), 0.35), 0.05)))
save('spit', mix(bandpass(env_noise(0.35, 12), 900, 1.5), scale(lowpass(env_noise(0.2, 20), 0.15), 0.8)), 0.6)
save('splash', mix(lowpass(env_noise(0.5, 9), 0.2), scale(highpass(env_noise(0.7, 5), 0.5), 0.25)), 0.6)
save('shield_hit', mix(tone(lambda t: 1250, 0.35, lambda t: math.exp(-t * 14)), scale(tone(lambda t: 1890, 0.3, lambda t: math.exp(-t * 18)), 0.6),
                       scale(env_noise(0.05, 80, 0.6), 0.8)), 0.45)
random.seed(41)
save('tv_static', mix(bandpass(env_noise(6.0, 0.0), 2500, 0.8), scale(highpass(env_noise(6.0, 0.0), 0.6), 0.4)), 0.5)
random.seed(53)
_ = (mix(env_noise(0.45, 18, 0.45), scale(tone(lambda t: 95 * math.exp(-t * 9) + 38, 0.45, lambda t: math.exp(-t * 11)), 1.1)))
_ = (mix(env_noise(0.2, 40, 0.5), scale(tone(lambda t: 170 * math.exp(-t * 20) + 60, 0.15, lambda t: math.exp(-t * 35)), 0.7)), 0.8)
_ = (mix(env_noise(1.2, 5, 0.5), scale(env_noise(0.08, 60, 0.9), 0.9),
                   scale(tone(lambda t: 70 * math.exp(-t * 4) + 30, 1.0, lambda t: math.exp(-t * 5)), 1.0)))
save('throw', bandpass([noise() * math.sin(math.pi * min(1, i / n(0.25))) for i in range(n(0.25))], 700, 1.0), 0.5)
print('sounds ok')

# casino (the mall): reels, wins, the roulette ball, chips
random.seed(67)
save('casino_tick', click(1800, 0.03, 140), 0.35)
save('casino_reel_stop', mix(click(380, 0.12, 40), scale(click(1200, 0.04, 90), 0.5)), 0.55)
save('casino_win', mix(*[delay(tone(lambda t, f=f: f, 0.18, lambda t: math.exp(-t * 6), 'square'), i * 0.09)
                         for i, f in enumerate((523, 659, 784, 1047, 1319))]), 0.35)
save('casino_lose', tone(lambda t: 220 - 80 * t, 0.45, lambda t: math.exp(-t * 4), 'square'), 0.25)
ball, t = [0.0] * n(3.6), 0.0
while t < 3.4:                                      # the ball rattling round the wheel, slower and slower
    for i, x in enumerate(click(2600 + random.uniform(-400, 400), 0.02, 160)):
        if n(t) + i < len(ball):
            ball[n(t) + i] += x * (1.0 - t / 4.5)
    t += 0.03 + 0.09 * (t / 3.4) ** 2
save('casino_ball', mix(ball, scale(lowpass(env_noise(3.6, 0.6), 0.04), 0.25)), 0.5)
save('casino_chips', mix(*[delay(click(random.uniform(2500, 4200), 0.05, 90), i * random.uniform(0.03, 0.06)) for i in range(7)]), 0.45)

# the mall's life: the fountain, muzak from the ceiling speakers, the PA chime, a shorting lamp
random.seed(71)
water = bandpass([noise() for _ in range(n(6.0))], 900, 0.6)
water = [x * (0.8 + 0.2 * math.sin(i / SR * 2.1) + 0.1 * math.sin(i / SR * 7.7)) for i, x in enumerate(water)]
for k in range(n(0.4)):                                   # cross-fade the ends so it loops without a click
    a = k / n(0.4)
    water[k] = water[k] * a + water[-n(0.4) + k] * (1 - a)
save('mall_fountain', water[:-n(0.4)], 0.5)


def muzak():
    """Sixteen seconds of shopping-centre easy listening through a tired speaker: soft chords, a slow tune, wow."""
    chords = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7)]
    tune = [523.3, 587.3, 659.3, 587.3, 523.3, 440.0, 392.0, 440.0, 523.3, 659.3, 698.5, 659.3, 587.3, 523.3, 493.9, 523.3]
    out = [0.0] * n(16.0)
    for i in range(len(out)):
        t = i / SR
        wow = 1.0 + 0.004 * math.sin(t * 2 * math.pi * 0.7)
        bar = int(t / 4.0) % 4
        x = sum(math.sin(2 * math.pi * f * wow * t) for f in chords[bar]) * 0.18 * (0.75 + 0.25 * math.sin(t * math.pi / 2))
        note, nt = tune[int(t / 1.0) % 16], t % 1.0
        x += math.sin(2 * math.pi * note * wow * t) * 0.3 * math.exp(-nt * 2.5) * min(1.0, nt * 40)
        x += math.sin(2 * math.pi * chords[bar][0] / 2 * t) * 0.25 * math.exp(-(t % 1.0) * 3)  # soft bass
        out[i] = x
    return lowpass(highpass(out, 0.05), 0.35)


save('mall_muzak', muzak(), 0.4)
save('mall_chime', mix(tone(lambda t: 784, 0.9, lambda t: math.exp(-t * 3)), delay(tone(lambda t: 659, 0.9, lambda t: math.exp(-t * 3)), 0.45),
                       delay(tone(lambda t: 523, 1.3, lambda t: math.exp(-t * 2.5)), 0.9)), 0.4)
save('mall_sparks', mix(*[delay(scale(highpass(env_noise(0.06, 60), 0.4), random.uniform(0.3, 1.0)), random.uniform(0, 0.5))
                         for _ in range(9)]), 0.5)
