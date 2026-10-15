# How this Codex version works

This project adapts Nicola's Claude reel editor to a local Codex workflow. The upstream MIT license and attribution are retained. It is a private beta, not a hosted service or an official OpenAI editor.

1. `prepare_review.py` creates local review assets and transcript data.
2. `review_server.py` serves the review UI and persists decisions on this computer.
3. `review_sync.py` maps word selections and graphic decisions to an edit decision list.
4. `cut.py` builds the master clip; `auto_edit.py` drafts captions.
5. `build_reel.py` applies brand fonts, graphics, sounds and the shared `edit_policy.py` guardrails.
6. `render.sh` renders with the pinned HyperFrames version and normalizes the final audio mix.
7. `qa.py` checks the export; an editor still needs to inspect visuals and listen to the result.

The review Build preview button uses `build_preview.py`. It renders an immutable snapshot and retains the last successful preview if a new build fails. Creative written notes are sent back to Codex for interpretation before building.

## Extend it carefully

Add a new card type in the template and document its inputs. Use timed local assets and deterministic animation. Test a small composition before a whole reel. Keep media outside Git. Do not make silent fallbacks for missing sounds, unsafe crops or unsupported formats.

Start from [GUIDE.md](GUIDE.md). Read [sound configuration](docs/SOUNDS.md) before importing third-party audio. The next product stage—three edits, carousel slides, stories and a thumbnail from one source—is not implemented in this beta.
