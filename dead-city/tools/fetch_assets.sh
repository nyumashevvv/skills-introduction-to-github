#!/usr/bin/env bash
# Downloads the CC0 source packs used by tools/blender/build_assets.py and prepares the zombie voices.
#   tools/fetch_assets.sh <sources dir>
# Needs: curl, unzip, ffmpeg, python3 (+ pip install py7zr for the arms .7z).
# Then build the models (Blender 4.5+):
#   blender -b --python tools/blender/build_assets.py -- <sources dir> .
set -euo pipefail
SRC=${1:?usage: fetch_assets.sh <sources dir>}
PROJECT=$(cd "$(dirname "$0")/.." && pwd)
OGA=https://opengameart.org/sites/default/files
mkdir -p "$SRC"/{uacp,guns/rpg,guns/fpsarms,sounds}
cd "$SRC"

get() { [ -f "$2" ] || curl -sSL -o "$2" "$OGA/$1"; }

# Characters: Ultimate Animated Character Pack by Quaternius
get ultimate_animated_character_pack_by_quaternius.zip uacp.zip
unzip -oq uacp.zip "*/Blends/*" -d uacp
# Weapons: Low Poly Animated Guns + Low poly Guns (Quaternius), Low poly RPG7 (Lucian Pavel), fps arms (para)
get "FPS%20Pack_0.zip" fps_pack.zip && unzip -oq fps_pack.zip -d guns
get "GunPack%20Vol.1.zip" gunpack.zip && unzip -oq gunpack.zip -d guns
get RPG7.zip rpg7.zip && unzip -oq rpg7.zip -d guns/rpg
get "fps%20arms.7z" fpsarms.7z && python3 -c "import py7zr; py7zr.SevenZipFile('fpsarms.7z').extractall('guns/fpsarms')"

# Zombie voices: Zombie noises and moans (ianzazz), Zombies Sound Pack (artisticdude),
# Undead Moans (AntumDeluge), Zombie / Skeleton / Monster Voice Effects (ArcadeParty)
cd sounds
get zombienoises.zip zombienoises.zip && unzip -oq zombienoises.zip -d zombienoises
get zombies.zip zombies.zip && unzip -oq zombies.zip -d zombies
get undead-moans.zip undead.zip && unzip -oq undead.zip -d undead
get "Voice%20Effects%20Zombie-Skeleton-Monster%20Human%20Male.zip" voice.zip && unzip -oq voice.zip -d voice
VE="voice/Voice Effects Zombie-Skeleton-Monster Human Male"
OUT="$PROJECT/sounds/zombie"
mkdir -p "$OUT"
# Mono, band-limited (no shrill highs), loudness-normalised, short fade-out.
proc() { ffmpeg -v error -y -i "$1" -ac 1 -ar 22050 \
  -af "highpass=f=70,lowpass=f=3800,loudnorm=I=$3:TP=-2:LRA=11,areverse,afade=t=in:d=0.08,areverse" \
  -c:a libvorbis -q:a 4 "$OUT/$2.ogg"; }
i=1; for f in undead/undead-2.ogg undead/undead-4.ogg zombienoises/zombienoise1.ogg zombienoises/zombienoise2.ogg \
    zombies/zombies/zombie-16.wav zombies/zombies/zombie-17.wav zombies/zombies/zombie-18.wav zombies/zombies/zombie-21.wav; do
  proc "$f" "groan$i" -24; i=$((i + 1)); done
i=1; for f in "$VE/zombieYell2.wav" "$VE/zombieYell8.wav" "$VE/zombieYell4.wav" zombies/zombies/zombie-4.wav zombies/zombies/zombie-7.wav; do
  proc "$f" "attack$i" -20; i=$((i + 1)); done
i=1; for f in "$VE/zombieDeath3.wav" "$VE/zombieDeath4.wav" "$VE/zombieDeath2.wav" zombies/zombies/zombie-15.wav; do
  proc "$f" "death$i" -21; i=$((i + 1)); done
# Boss roars: the same yells pitched down an octave-ish, with a short echo.
roar() { ffmpeg -v error -y -i "$1" -ac 1 \
  -af "asetrate=44100*0.62,aresample=22050,aecho=0.8:0.5:70:0.35,highpass=f=50,lowpass=f=3000,loudnorm=I=-18:TP=-2:LRA=11" \
  -c:a libvorbis -q:a 4 "$OUT/$2.ogg"; }
roar "$VE/zombieYell1.wav" roar1; roar "$VE/zombieYell6.wav" roar2; roar "$VE/zombieYell9.wav" roar3

# Boss music (CC0): nene "Boss Battle #9 Metal", emmama "Determined Pursuit",
# Juhani Junkala "Epic Boss Battle". Seamless loops; only a constant gain is applied.
MUS="$PROJECT/music"
mkdir -p "$MUS"
get boss_battle_9_metal_loop.wav metal.wav
get determined_pursuit_loop.wav pursuit.wav
get "Juhani%20Junkala%20-%20Epic%20Boss%20Battle%20%5BSeamlessly%20Looping%5D.wav" epic.wav
ffmpeg -v error -y -i metal.wav -af volume=-6.3dB -c:a libvorbis -q:a 3 "$MUS/boss_metal.ogg"
ffmpeg -v error -y -i pursuit.wav -c:a libvorbis -q:a 3 "$MUS/boss_pursuit.ogg"
ffmpeg -v error -y -i epic.wav -af volume=-6.5dB -c:a libvorbis -q:a 3 "$MUS/boss_epic.ogg"

# Kenney kits (CC0): Car Kit, Furniture Kit, City Kit (Roads), Survival Kit
cd "$SRC"
mkdir -p kenney
kenney() { [ -d "kenney/$1" ] || { curl -sSL -o "kenney/$1.zip" "https://kenney.nl/media/pages/assets/$1/$2/kenney_$1.zip" &&
  unzip -oq "kenney/$1.zip" -d "kenney/$1"; }; }
kenney car-kit 1a312ec241-1775131960
kenney furniture-kit 440e0608a4-1677580847
kenney city-kit-roads 74288c9459-1791628607
kenney survival-kit 4065a8185b-1712149243

# Reload sounds (CC0, OpenGameArt): "Handgun Reload Sound Effect", "Gun Reload Sounds",
# "Gun Reload Sound Effects", "2 Gun Reloads" (starninjas)
cd "$SRC/sounds"
for f in reload.wav assaultriflereload1_0.wav singlebullet1.wav shotguncock_0.wav clipload2.wav; do get "$f" "$f"; done
get gun_reload_-_starninjas.zip starninjas.zip && unzip -oq starninjas.zip -d starninjas
rl() { ffmpeg -v error -y -i "$1" -ac 1 -ar 44100 -af "silenceremove=start_periods=1:start_threshold=-50dB,highpass=f=80,volume=$3" \
  -c:a pcm_s16le "$PROJECT/sounds/$2.wav"; }
rl reload.wav reload_pistol 0dB; rl assaultriflereload1_0.wav reload_rifle 3dB; rl singlebullet1.wav shell_insert 6dB
rl shotguncock_0.wav shotgun_pump -4dB
ffmpeg -v error -y -i starninjas/gun_reload.2.ogg -i clipload2.wav -filter_complex \
  "[1]adelay=1500|1500,volume=2[b];[0][b]amix=inputs=2:duration=longest:normalize=0,aformat=channel_layouts=mono" \
  -ar 44100 -c:a pcm_s16le "$PROJECT/sounds/reload_rocket.wav"

# PBR textures (CC0, ambientCG): colour, normal (GL) and roughness, scaled into textures/pbr/
mkdir -p "$SRC/ambientcg" "$PROJECT/textures/pbr"
for id in Asphalt012 PavingStones070 Concrete044B Concrete034 Bricks059 Plaster001 PaintedPlaster017 Tiles107 \
    Terrazzo009 Wood049 Metal032 Rust004 Grass004; do
  [ -d "$SRC/ambientcg/$id" ] || { curl -sSL -o "$SRC/ambientcg/$id.zip" "https://ambientcg.com/get?file=${id}_1K-JPG.zip" &&
    unzip -oq "$SRC/ambientcg/$id.zip" -d "$SRC/ambientcg/$id"; }
  ffmpeg -v error -y -i "$SRC/ambientcg/$id/${id}_1K-JPG_Color.jpg" -q:v 3 "$PROJECT/textures/pbr/${id}_color.jpg"
  ffmpeg -v error -y -i "$SRC/ambientcg/$id/${id}_1K-JPG_NormalGL.jpg" -q:v 3 "$PROJECT/textures/pbr/${id}_normal.jpg"
  ffmpeg -v error -y -i "$SRC/ambientcg/$id/${id}_1K-JPG_Roughness.jpg" -vf "scale=512:512,format=gray" -q:v 3 \
    "$PROJECT/textures/pbr/${id}_rough.jpg"
done
echo "Sources ready in $SRC"
