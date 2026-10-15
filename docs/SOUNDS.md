# Sound configuration

Built-in sounds are synthesized locally by setup_engine.sh. They approximate pops, clicks, typing, chimes and whooshes; they are not CapCut library recordings. `coin` and `sparkle` resolve to `chime` when no custom file is supplied. Unknown names and missing files fail clearly.

To use your chosen licensed audio, place it under your private REELS_HOME/assets/sounds and configure brand.json:

```json
{"sfx": "lots", "sfx_gain_db": 0, "sfx_files": {"pop": "assets/sounds/pop.wav", "snap": "assets/sounds/mouse-click.wav", "swish": "assets/sounds/whoosh.wav", "typing": "assets/sounds/typing.wav", "chime": "assets/sounds/sparkle.wav"}}
```

The source files are converted to 48 kHz stereo for rendering. Gain applies to their existing level: audition against speech and adjust sfx_gain_db or each card's sfx.db. There is no claim that every source will have equal perceived loudness. Final export normalizes the complete mix to about -14 LUFS. Keep sound files and license receipts outside Git. A lower effect gain is preferable to drowning out the voice.
