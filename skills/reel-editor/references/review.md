# Local Reel Review

The review page runs on localhost and saves decisions into the reel folder. Footage stays local. Run commands with the same `REELS_HOME` used for the brand and edit. Script paths below are relative to this skill.

## Prepare

1. After transcription and audio cleanup, run `python3 scripts/tighten.py <reel> --detect`. Exit 3 means fillers were not detected: disclose that limitation. Write `proposal.json` using the schema in `scripts/review_sync.py` (kept source spans, accent words, cards anchored to spoken words).
   Shortcut for steps 2-4: `python3 scripts/prepare_review.py <reel> --brand-home "$REELS_HOME"` runs the export, makes the proxy, audio comparisons, fonts and card thumbnails, and sets every URL.
2. `python3 scripts/review_sync.py export <reel> <proposal.json> <reel>/review-export`. This also writes `<reel>/review_reel.json`.
3. Create `<reel>/review-assets/source.mp4`, a 540x960 proxy of the raw footage with `voice.wav` as its audio. Example (replace raw extension as needed):
   ```bash
   mkdir -p "<reel>/review-assets"
   ffmpeg -y -i "<reel>/raw.mov" -i "<reel>/voice.wav" -map 0:v:0 -map 1:a:0 -vf "scale=540:960:force_original_aspect_ratio=increase,crop=540:960" -c:v libx264 -preset veryfast -b:v 900k -c:a aac -shortest "<reel>/review-assets/source.mp4"
   ```
4. Set `srcUrl` in `review_reel.json` to `/media/review-assets/source.mp4`. Add per-card `thumbUrl` and `imgUrl`, sound comparisons, colour comparisons, SFX and fonts when prepared, all as `/media/<relative-path>` URLs. Copy assets inside the reel folder; the server rejects paths outside it. Only use fonts the user owns. Omit unavailable assets rather than showing broken comparisons.
5. Run `python3 scripts/review_server.py <reel>` as a background terminal session. It prints a localhost URL with a free port. Open it in Codex's browser panel when available, otherwise provide a link. Do not bind to a public address. Tell the user to tap words and review graphics, captions, sound and colour, then select Build preview and say “build preview” in chat. The button saves a request; rendering is performed by Codex after reading it.

## Build preview

1. Read `<reel>/review_decisions.json`. If absent, ask whether to use the proposal; absence is not approval. Wait for their approval before cutting.
2. `python3 scripts/review_sync.py import <reel> <reel>/review_decisions.json`. Handle every printed change request, note and revision before rendering. Confirm requested persistent brand changes before updating the brand.
3. `REEL_PREVIEW=1 python3 scripts/cut.py <reel>` then `REEL_PREVIEW=1 bash scripts/render.sh <reel>`. Check frames at graphics and long captions.
4. Make `review-assets/preview.mp4`, a 540p proxy of `final.mp4`. Write `<reel>/review_build.json` with `url: "/media/review-assets/preview.mp4"`, `hash` from `edit.json`, `at` (ISO timestamp) and `cutDur` (preview duration). The open page polls for this file and marks it stale when decisions change.
5. Read timestamped revisions from the decisions file before making the next preview. Keep the review server session alive while reviewing, and stop it when finished.

## Final

After draft approval, run `bash scripts/render.sh <reel> --final`, QA and delivery. Follow `capcut.md` only for a requested editable draft. Retain review decisions with the reel; do not overwrite another reel's notes.
