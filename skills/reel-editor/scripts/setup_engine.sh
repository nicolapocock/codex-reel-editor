#!/usr/bin/env bash
# One-time: fetch the animation library and make the sound effects. Re-run safely any time.
set -euo pipefail
E="$(cd "$(dirname "$0")/.." && pwd)/engine"; mkdir -p "$E/sfx"

GSAP_SHA=96c01b81f44a3290e2b4532f55e2c9534b2adc43273a19f3756b2cb41f0fd0b6   # gsap 3.13.0: refuse a tampered download
if [ ! -s "$E/gsap.min.js" ]; then
  curl -fsSL https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js -o "$E/gsap.min.js.tmp"
  [ "$(shasum -a 256 "$E/gsap.min.js.tmp" | cut -d' ' -f1)" = "$GSAP_SHA" ] || { rm -f "$E/gsap.min.js.tmp"; echo "gsap download failed its checksum - not installing it" >&2; exit 1; }
  mv "$E/gsap.min.js.tmp" "$E/gsap.min.js"
fi

# Sound effects synthesised with ffmpeg: no downloads, no licences to worry about.
mk() { [ -s "$E/sfx/$1.wav" ] || ffmpeg -v error -y -f lavfi -i "$2" -af "$3" -ar 48000 -ac 2 "$E/sfx/$1.wav"; }
mk whoosh "anoisesrc=d=0.5:c=pink:a=0.6"        "highpass=f=500,lowpass=f=6000,afade=t=in:d=0.28:curve=exp,afade=t=out:st=0.28:d=0.22"
mk pop    "sine=f=620:d=0.12"                   "vibrato=f=12:d=0.4,afade=t=out:st=0.02:d=0.10,volume=1.6"
mk snap   "anoisesrc=d=0.06:c=white:a=0.9"      "highpass=f=2200,afade=t=out:st=0.005:d=0.05"
mk chime  "sine=f=1320:d=0.7"                   "aecho=0.6:0.5:60:0.35,afade=t=out:st=0.05:d=0.65"
mk swish  "anoisesrc=d=0.25:c=pink:a=0.5"       "highpass=f=900,lowpass=f=7000,afade=t=in:d=0.12:curve=exp,afade=t=out:st=0.12:d=0.13"
mk typing "aevalsrc='0.7*random(0)*lt(mod(t\\,0.085)\\,0.006)':d=0.9" "highpass=f=1500,lowpass=f=8000,volume=1.8"
# Bring every effect up to a -1 dB peak: synthesised noise comes out ~20 dB quieter than a voice and disappears in the mix.
for f in "$E"/sfx/*.wav; do
  [ -e "$f.norm" ] && continue
  PK="$(ffmpeg -hide_banner -i "$f" -af volumedetect -f null - 2>&1 | sed -n 's/.*max_volume: \(-*[0-9.]*\) dB/\1/p')"
  ffmpeg -v error -y -i "$f" -af "volume=$(python3 -c "print(round(-1-($PK),2))")dB" "$f.tmp.wav" && mv "$f.tmp.wav" "$f" && touch "$f.norm"
done
# HyperFrames catalog motions (carousels, captions, charts, social cards): fetched from HyperFrames, not shipped in this repo.
H="$E/hf"; mkdir -p "$H"
[ -f "$H/hyperframes.json" ] || printf '%s' '{"$schema":"https://hyperframes.heygen.com/schema/hyperframes.json","registry":"https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry","paths":{"blocks":"compositions","components":"compositions/components","assets":"assets"}}' > "$H/hyperframes.json"
[ -f "$H/package.json" ] || echo '{"name":"engine","private":true,"type":"module"}' > "$H/package.json"
for m in caption-camera-follow carousel-vision-1 carousel-path-1 carousel-circle-1 carousel-orbit-1 hw-arrow hw-underline \
         oversized-cursor notification-stack code-terminal-run chat-message yt-comment-card instagram-follow count-up \
         animated-bar-chart mk-line-graph native-notification-pop x-follow-card chart-story; do
  ls "$H"/compositions/"$m".html "$H"/compositions/components/"$m".html >/dev/null 2>&1 || (cd "$H" && npx -y hyperframes@0.8.157 add "$m" >/dev/null 2>&1) || echo "note: couldn't fetch motion $m" >&2
done
echo "engine ready: $E"
