# CapCut route (optional)

Gives the person an **editable CapCut Web draft**: the edited video with graphics baked in, plus captions and sound effects as separate CapCut layers they can change. The MP4 route is always delivered too.

## Who can use it

| Where | Works? |
|---|---|
| Australia, UK, most of Europe and Asia | Usually yes |
| United States | No - CapCut's own plugin docs say plugin features aren't available on US networks yet |
| India | No - the CapCut app is not available there |

Never promise it works. If the connector fails, deliver the MP4 and say why.

## One-time setup

1. A free CapCut account.
2. Install and connect the official CapCut plugin in Codex. Check available account tools in the current session; do not assume a connection from files alone.
3. Set `CAPCUT_SKILLS_DIR` to the installed plugin's skills folder (containing `capcut-stdraft-builder` and `capcut-upload`). Load those skills before upload or draft actions. Use their current collaboration workflow for importing a draft and obtaining an editor link.
4. Fonts: CapCut's connector only offers a small font list. To use the person's brand font, they add it to their CapCut brand kit, apply it to one caption in the editor, then you read its `vimo://` URI back with `get_stdraft_snapshot` and save it as `capcut_font` in brand.json.

## What step 5 must produce on this route

Render the HyperFrames graphics with **no captions and no sound effects baked in** (CapCut adds those), then write two files in the reel folder:

`captions.json` - one entry per caption, words in order, each word tagged with a size:

```json
[{ "start": 1.20, "end": 2.05, "over_light": false,
   "lines": [[{ "text": "claude", "kind": "big", "t": 1.20 }, { "text": "edits", "kind": "acc", "t": 1.55 }]] }]
```

- `kind`: `sm` (small), `big` (normal), `acc` (accent word: pop colour, bigger)
- `over_light: true` when the caption sits on a white or very light background (caption turns pop colour so it doesn't vanish)
- Pick accent words with the person's taste: usually one emotional or key word per caption.

`sfx.json` - `[{ "name": "whoosh", "t": 3.4, "vol": 0.35 }]` using names from the `SFX` table in `scripts/capcut_draft.py`.

## Build and push

1. Upload `final.mp4` with the `capcut-upload` skill from `CAPCUT_SKILLS_DIR`; save its JSON result as `upload.json`. Trust `"success": true` + a `vid`, even if the script exits 1.
2. `python3 scripts/capcut_draft.py <reel-folder>` → `draft.json`. It must print `valid: True`.
3. Push with the CapCut tools: `start_stdraft_session` → `push_stdraft_snapshot` with `draft.json`. Give them the editor link.
4. Rename the project in CapCut (every push names it with a timestamp).

## Known limits (tell them)

- Text animations aren't available through the connector: select all captions in the editor and add an "in" animation by hand (10 seconds).
- CapCut drops caption background boxes and adds a drop shadow when the editor saves. The script sets the shadow to zero; boxes aren't possible.
- If they have the draft open in a browser tab while you push, you get a version conflict: ask them to close the tab, then push again.
- A push can report an error and still land - check with `check_stdraft_state` before retrying.
