# Codex reel editor

Turn a raw talking-head video into a branded vertical reel with Codex. It cuts the ums and pauses, adds captions and graphics in your brand, lets you review every cut on a local page, then renders an MP4 ready to post. It can also make your reel cover.

This is the Codex version of [Nicola Pocock's Claude reel editor](https://github.com/nicolapocock/claude-reel-editor). Everything runs on your Mac in the Codex app. Your footage stays on your computer.

**New to this? Start with the [setup guide](GUIDE.md).** It walks you through every step, no coding needed. There's also a [six-page PDF version](docs/getgitgirl-codex-edit-guide.pdf).

## What you need

- A Mac (other systems untested)
- The [Codex app](https://developers.openai.com/codex/app) and a ChatGPT plan that includes Codex (Plus or higher)
- Python 3, Node.js and ffmpeg (the guide installs them)
- About 10 GB of free space

## Quick start (if you've used Codex before)

Install the tools, then open this folder as a Codex project:

```bash
brew install ffmpeg node python
```

Then paste this into Codex:

> Read AGENTS.md and skills/reel-editor/SKILL.md. Set up the reel editor in this project. Use the project's reels folder as REELS_HOME for every command. Run npm ci, install the hyperframes skills (npx skills add heygen-com/hyperframes, choosing codex), then run the doctor check and tell me if anything is missing. Do not upload my footage.

The first time, Codex asks about your brand (colours, fonts, caption style, sounds, pacing). Then give it a clip:

> Edit this into a reel: /full/path/to/your/video.mov

Codex transcribes the clip, proposes cuts and graphics, and opens the review page. It renders only after you approve.

## The review page

`review_server.py` runs the review page on `127.0.0.1`, so only your Mac can open it. Your decisions save to `review_decisions.json` in the reel folder. You can cut words, fix captions, keep or drop graphics, switch sounds off and leave notes at a timestamp. The rough cut uses the same timing engine as the renderer, so what you approve is what you get. No Claude or artifact account is needed.

See [the edit workflow](skills/reel-editor/SKILL.md) and [the review steps](skills/reel-editor/references/review.md).

## Thumbnail studio

Click **Thumbnail studio** at the top of the review page, or open `/thumbnail` on the running review server. Pick your footage, show six evenly sampled frames (or use the slider for an exact frame), type a headline and choose the font, size, colour, height and style (soft shadow, cream title panel or dark fade). Your saved brand fonts and colours load automatically, with a system font as the fallback. Download a 1080×1920 portrait PNG, a 1080×1440 3:4 crop or a 1080×1080 square. The crop guides only show while you edit and never appear in downloads. **Save cover settings** keeps your choices with the reel for next time.

## What's different from the Claude version

- The review page runs locally instead of as a claude.ai artifact.
- Captions sit in one fixed zone by default.
- Hooks can be forced onto a single line, and headlines get a soft shadow.
- A carousel can orbit around you when you supply a cutout of yourself.
- Missing sound files stop the render with a clear message instead of going silent. You can swap in your own licensed sounds with `sfx_files` (see [sound configuration](docs/SOUNDS.md)).
- If a preview build fails, your last good preview stays on the page.
- A thumbnail studio for reel covers.

## Privacy and limits

Rendering and the default transcription (local Whisper) run on your Mac. Two things send data elsewhere, and only if you choose them: ElevenLabs transcription (optional, paid separately) and the CapCut route (uploads your reel to your CapCut account). The review page loads its interface fonts from Google Fonts. Your brand fonts are served from your own Mac.

The CapCut route doesn't work in the US or India. Graphics are baked into the video. CapCut captions and sounds stay editable.

No personal footage or paid font files are included in this repo. Your reels folder is ignored by Git.

## Tests

```bash
python3 tests/test_review_server.py
python3 tests/test_review_import.py
python3 tests/test_edit_policy.py
python3 tests/test_template_build.py
```

The review import and template tests need Node.js and ffmpeg. The template test downloads the pinned animation engine on a fresh copy.

## Guides

- [Setup guide](GUIDE.md)
- [Six-page PDF guide](docs/getgitgirl-codex-edit-guide.pdf)
- [Copyable setup page](skills/reel-editor/review/setup.html). Download the repo and open it in your browser (GitHub only shows its code).
- [How it works](BUILD-IT-YOURSELF.md)

MIT licensed. Made by [@getgitgirl](https://instagram.com/getgitgirl).
