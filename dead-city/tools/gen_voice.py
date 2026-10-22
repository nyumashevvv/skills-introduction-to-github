"""Voices every radio message in the chapters and the intro cutscene with Piper TTS (Russian CC0 voices).

    pip install piper-tts
    python3 tools/gen_voice.py <dir with ru_RU-denis-medium.onnx and ru_RU-dmitri-medium.onnx>

Run from the project root after tools/gen_levels.py. Files land in sounds/voice/<md5(text)[:12]>.ogg, which is
what the game looks up (`text.md5_text().left(12)`); lines that already have a file are skipped.
"""
import glob
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import wave

from piper import PiperVoice, SynthesisConfig

sys.path.insert(0, os.path.dirname(__file__))
from story_text import CUTSCENE  # noqa: E402

OUT = 'sounds/voice'
# speaker: (voice, length scale, ffmpeg filter)
RADIO = ('highpass=f=320,lowpass=f=3300,acompressor=threshold=-22dB:ratio=5:attack=5:release=60,'
         'volume=5dB,asoftclip=type=tanh,volume=-2dB')
VOICES = {
    'Диспетчер': ('denis', 1.0, RADIO),
    'Пилот': ('dmitri', 0.95, 'asetrate=22050*0.93,aresample=22050,' + RADIO),
    'Новости': ('denis', 0.95, 'highpass=f=150,lowpass=f=5000,acompressor=threshold=-20dB:ratio=3,volume=2dB'),
    '': ('dmitri', 1.12, 'highpass=f=70,aecho=0.8:0.4:35:0.18,volume=1dB'),
}
# Words the synthesiser would spell out badly.
SAY = [('РПГ', 'эр-пэ-гэ'), ('клавиша F', 'клавиша эф'), ('Клавиша 3', 'Клавиша три'), ('F.', 'эф.'),
       ('«', ''), ('»', ''), ('…', ''), ('Борт-двенадцать', 'Борт двенадцать')]


def voice_name(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]


def level_lines():
    """(speaker, message) of every StoryEvent in the chapter scenes."""
    lines = []
    for path in sorted(glob.glob('scenes/levels/*.tscn')):
        for block in open(path, encoding='utf-8').read().split('\n[node ')[1:]:
            msg = re.search(r'^message = "((?:[^"\\]|\\.)*)"', block, re.M)
            if not msg:
                continue
            spk = re.search(r'^speaker = "((?:[^"\\]|\\.)*)"', block, re.M)
            unescape = lambda s: s.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            lines.append((unescape(spk.group(1)) if spk else '', unescape(msg.group(1))))
    return lines


def main():
    models = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(OUT, exist_ok=True)
    loaded = {}
    lines = level_lines() + [(speaker, text) for _, speaker, text in CUTSCENE]
    made = 0
    for speaker, text in lines:
        out = os.path.join(OUT, voice_name(text) + '.ogg')
        if os.path.exists(out):
            continue
        name, length, chain = VOICES.get(speaker, VOICES['Диспетчер'])
        if name not in loaded:
            loaded[name] = PiperVoice.load(os.path.join(models, f'ru_RU-{name}-medium.onnx'))
        spoken = text
        for a, b in SAY:
            spoken = spoken.replace(a, b)
        with tempfile.NamedTemporaryFile(suffix='.wav') as tmp:
            with wave.open(tmp.name, 'wb') as wav:
                loaded[name].synthesize_wav(spoken, wav, syn_config=SynthesisConfig(length_scale=length))
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp.name, '-ac', '1', '-ar', '22050', '-af',
                            chain + ',volume=8dB,alimiter=limit=0.9',
                            '-c:a', 'libvorbis', '-q:a', '4', out], check=True)
        made += 1
    print(f'voice ok: {made} new, {len(lines)} lines')


if __name__ == '__main__':
    main()
