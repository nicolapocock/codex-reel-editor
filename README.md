# Codex reel editor

A Codex port of [Nicola Pocock's Claude reel editor](https://github.com/nicolapocock/claude-reel-editor). Turn a raw talking-head video into a branded vertical reel, review cuts and captions locally, then render an MP4. Optional editable CapCut delivery uses the installed official CapCut plugin.

This version runs in local Codex. It is not yet a hosted editor inside the ChatGPT web or mobile app.

## Start

Open this repository as a local Codex project, then say:

> Read skills/reel-editor/SKILL.md and set up the reel editor. Use a reels folder inside this project as REELS_HOME. Check dependencies and help me set up my brand.

Requirements: macOS (other systems untested), Python 3, Node.js, ffmpeg, HyperFrames skills and about 10 GB free space. Setup downloads the pinned animation engine and HyperFrames motions. Local Whisper transcription may download a model; ElevenLabs is optional and billed separately.

Install HyperFrames skills with `npx skills add heygen-com/hyperframes`, choosing Codex when prompted. Then run `bash skills/reel-editor/scripts/doctor.sh`. The doctor may initialize missing engine assets.

Once set up:

> Use the reel-editor skill to edit this clip into a reel. Keep my original file intact and show me the local review page before cutting.

Use the full path to your video. Codex reads the brand, transcribes, proposes cuts and graphics, opens the local review page, imports saved decisions, and renders after approval.

## Review

The existing review UI now runs through `review_server.py`, a Python localhost server. Decisions are saved as `review_decisions.json` in each reel folder. Word cuts, captions, graphics, sound decisions and timestamped preview notes use the same `core.js` timing engine as the renderer. Video range requests allow seeking. No Claude artifact account is required.

See [the edit workflow](skills/reel-editor/SKILL.md) and [local review instructions](skills/reel-editor/references/review.md).

## Limits and privacy

Rendering and default transcription run locally. Review UI typography currently requests Google Fonts; brand fonts can be served locally. ElevenLabs transcription and optional CapCut uploads send media to those services. CapCut availability and fonts depend on the connected account. Graphics are baked into the video; CapCut captions and sounds can be editable.

The port has been checked for review persistence, media seeking, browser interactions and decision import. A real 36-second spoken reel has been rendered and visually reviewed; broader device and footage testing is still needed before public launch. It preserves the upstream editing engine and MIT license. The original guide's Claude instructions have been replaced by [GUIDE.md](GUIDE.md).

## Verification

Run `python3 tests/test_review_server.py` (requires localhost access) and `python3 tests/test_review_import.py` (requires Node.js).

## Private beta improvements

- One fixed caption zone by default; old gesture overrides are ignored.
- Soft headline/caption shadows, explicit editorial layouts and single-line hooks.
- Actual reel-image orbit carousel and six-page guide scroll behind a supplied alpha cutout.
- Manual CSS subject masks rejected to prevent the head-clipping bug; alpha quality still requires visual review.
- Sound aliases resolve to existing assets, missing files fail clearly, and licensed local files can override each effect with `sfx_files`.
- Copy buttons and full-selection fallback on the local setup page.
- Local review saving, real preview builds, and previous-preview retention on failure.

See [the complete beginner guide](GUIDE.md) and [sound configuration](docs/SOUNDS.md). Run `python3 tests/test_edit_policy.py` alongside the review tests. No personal footage or commercial font files are shipped.

## Guides

- [Download the six-page Codex guide](docs/getgitgirl-codex-edit-guide.pdf)
- [Editable Figma guide](https://www.figma.com/design/iTjBqHg2h05yT6j0SBcwWb/?node-id=221-2)
- [Copyable setup page](skills/reel-editor/review/setup.html) — open locally; GitHub shows its source.

### Thumbnail studio (local beta)
Open `/thumbnail` on the running review server, or click **Thumbnail studio** in the review header. Select local footage, sample six frames, choose a frame, and edit the headline, font, colour, position and shadow/panel style. Download a 1080×1920 PNG or centred 3:4/square crop. Crop guides are preview-only. Fonts come from the reel's prepared `proj/fonts` assets; otherwise system sans is used. Frame suggestions are evenly spaced, not AI-ranked. Use **Save cover settings** to persist the selected frame and styling with the reel. Reopening the studio restores them.
