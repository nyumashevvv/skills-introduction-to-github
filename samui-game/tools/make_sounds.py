#!/usr/bin/env python3
"""Synthesises the game's sound loops (no recorded samples, so no licensing):

  engine.wav    small 4-stroke scooter engine at idle (pitch-shifted in game)
  surf.wav      waves breaking on a beach
  cicadas.wav   daytime jungle cicadas
  night.wav     crickets and frogs after dark
  town.wav      distant traffic and voices
  horn.wav      scooter horn

  python3 tools/make_sounds.py sounds/
Every loop is periodic (filtered circularly in the frequency domain), so it repeats without a click.
"""
import os
import sys
import wave

import numpy as np

SR = 22050
out = sys.argv[1] if len(sys.argv) > 1 else "sounds"
os.makedirs(out, exist_ok=True)
rng = np.random.default_rng(3)


def shape(x, lo, hi, tilt=0.0):
    """Band-limit a loop in the frequency domain. Filtering a whole loop circularly
    keeps it periodic, so the loop point is seamless by construction."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = (1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)) * (1 / (1 + (f / hi) ** 4))
    if tilt:
        g = g * (np.maximum(f, 20) / 1000.0) ** tilt
    return np.fft.irfft(X * g, len(x))


def lowpass(x, cutoff):
    return shape(x, 1.0, cutoff)


def bandpass(x, lo, hi):
    return shape(x, lo, hi)


def seamless(x, fade=0.0):
    return x  # loops are periodic already (circular filtering, whole-cycle envelopes)


def save(name, x, peak=0.8):
    x = x / max(np.abs(x).max(), 1e-9) * peak
    with wave.open(os.path.join(out, name), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((x * 32767).astype("<i2").tobytes())
    print(f"{name}: {len(x) / SR:.2f} s, peak {np.abs(x).max():.2f}, rms {np.sqrt(np.mean(x ** 2)):.3f}")


def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


# engine: firing pulses at ~25 Hz (1500 rpm idle, one power stroke per 2 revs = 12.5 Hz; doubled for a twin-ish buzz)
t = t_axis(2.0)
f0 = 50.0  # loop must hold a whole number of cycles: 2.0 s of loop * 50 Hz
phase = (t * f0) % 1.0
pulse = np.exp(-phase * 9.0) * (1 + 0.15 * rng.standard_normal(len(t)))
engine = shape(pulse - pulse.mean(), 30, 700) + 0.3 * np.sin(2 * np.pi * f0 * 2 * t)
engine += 0.04 * bandpass(rng.standard_normal(len(t)), 200, 1500)   # intake/exhaust hiss
save("engine.wav", engine)

# surf: pink-ish noise shaped by slow wave envelopes (period 6-9 s)
t = t_axis(16.0)
noise = rng.standard_normal(len(t))
roar = shape(noise, 40, 1200, -0.5)
env = np.zeros(len(t))
for c in (1.5, 8.6, 13.0):              # three breakers per loop, wrapped around the loop point
    d = (t - c + 8.0) % 16.0 - 8.0
    env += np.exp(-(d ** 2) / 0.4) + 0.6 * np.exp(-np.maximum(d, 0) / 1.8) * (d > 0)
env = 0.3 + env / env.max()
save("surf.wav", roar * env, 0.7)

# cicadas: 4-6 kHz buzz, amplitude-modulated at ~90 Hz, swelling in and out
t = t_axis(10.0)
buzz = bandpass(rng.standard_normal(len(t)), 3800, 6500)
am = 0.5 + 0.5 * np.sin(2 * np.pi * 92 * t)
swell = 0.4 + 0.6 * np.clip(np.sin(2 * np.pi * t / 10.0) * 1.4, 0, 1)
save("cicadas.wav", buzz * am * swell, 0.6)

# night: cricket chirps (4.5 kHz) + frog croaks (low pulses)
t = t_axis(8.0)
night = np.zeros(len(t))
for k in range(5):
    f = rng.uniform(4200, 4900)
    rate = rng.uniform(2.5, 4.0)
    rate = round(rate * 8.0) / 8.0       # whole chirps per loop
    gate = ((t * rate + rng.random()) % 1.0) < 0.12
    night += np.sin(2 * np.pi * f * t) * gate * (0.5 + 0.5 * np.sin(2 * np.pi * 30 * t)) * rng.uniform(0.3, 0.7)
for k in range(10):
    start = rng.uniform(0, 7.6)
    m = (t >= start) & (t < start + 0.25)
    tt = t[m] - start
    night[m] += 0.9 * np.sin(2 * np.pi * rng.uniform(180, 320) * tt) * np.sin(np.pi * tt / 0.25) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 22 * tt)))
save("night.wav", lowpass(night, 7000), 0.55)

# town: low traffic rumble, passing scooters, faint voices-like band noise
t = t_axis(12.0)
rumble = lowpass(rng.standard_normal(len(t)), 220) * 2.0
for k in range(6):
    c = rng.uniform(1.5, 10.5)
    dopp = 1 + 0.15 * np.tanh((c - t) * 2)
    env = np.exp(-((t - c) ** 2) / 0.8)
    rumble += 0.6 * env * np.sin(2 * np.pi * 95 * dopp * t) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 47 * t)))
voices = bandpass(rng.standard_normal(len(t)), 300, 1500) * (0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t) * np.sin(2 * np.pi * 0.75 * t))
save("town.wav", rumble + 0.25 * voices, 0.6)

# horn: two slightly detuned square-ish tones, 0.45 s
t = t_axis(0.45)
horn = np.sign(np.sin(2 * np.pi * 420 * t)) * 0.5 + np.sign(np.sin(2 * np.pi * 508 * t)) * 0.5
horn = shape(horn, 200, 2500) * np.minimum(1, t / 0.01) * np.minimum(1, (0.45 - t) / 0.03)
save("horn.wav", horn, 0.7)
