# edit your reels with codex

Private beta · getgitgirl · macOS first

## 1. Get the project

Use the desktop app with local Codex access. See the [official app setup](https://learn.chatgpt.com/docs/app) for current downloads and account access. This editor runs against files on your Mac; it is not a custom GPT in ordinary ChatGPT chat.

While this repository is private, your GitHub account needs access. Sign in on GitHub, open [the repository](https://github.com/nicolapocock/codex-reel-editor), choose **Code → Download ZIP**, unzip it, and open that folder as a local Codex project. Git users can clone it after authenticating.

## 2. Set it up

Paste this into Codex:

```text
Read AGENTS.md and skills/reel-editor/SKILL.md. Set up the Codex reel editor in this project. Use the project's reels folder as REELS_HOME for every command. Check Node.js, Python 3 and ffmpeg. Run npm ci and the doctor check. Help me configure my brand. Open skills/reel-editor/review/setup.html so I can use its copy buttons. Do not upload my footage.
```

On a Mac that already has Homebrew, the video dependencies are:

```sh
brew install ffmpeg node python
```

If Homebrew is missing, ask Codex to guide you through [the official Homebrew installation](https://brew.sh). Let each command finish. Never copy another person's machine-specific “Next steps”.

Inside the project:

```sh
npm ci
```

Install HyperFrames skills if missing:

```sh
npx skills add heygen-com/hyperframes
```

Choose Codex when prompted. Check the setup:

```sh
bash skills/reel-editor/scripts/doctor.sh
```

READY means the required tools are present. READY WITH LIMITS means an optional feature is unavailable. If a required tool is missing, paste the error into Codex. The first setup downloads engine assets and may take several minutes.

## 3. Set your brand once

Provide your colours, licensed font files, caption style, pacing and a reference reel. Fixed caption positioning is the default. Headline shadows are included. Use actual screenshots for carousels.

Sounds: local defaults are simple synthesized effects, not the originals in CapCut. Give Codex sound files you have permission to use and ask it to configure `sfx_files` in your brand. Audition them with your voice before finalising. Missing sound files now stop the render instead of disappearing silently.

## 4. Your first reel

Film a short talking-head clip and save it on your Mac. Give Codex its full path, then paste:

```text
Edit this raw clip with the reel-editor skill. Preserve my original. Use my saved brand and keep captions in one fixed position with a soft shadow. Show me the proposed cuts and graphics before cutting. Start the local review server with --enable-builds and open its URL. Check hook placement against my gestures and preview all head/hair edges for any cutout effects.
```

The local review page opens once Codex has prepared the transcript and started its server. Correct words, approve cuts and adjust graphics. Click **Build preview**. Simple saved decisions can render directly; written creative changes need Codex to apply them first. The page tells you when that is needed. Keep the server running while reviewing.

## 5. Review, revise, export

Watch with sound. Check names, cut joins, hook placement, shadow, caption position, sound levels and the entire head/hair during cutouts. Leave a timestamp and describe the change. When happy, tell Codex “final”. It supplies the checked MP4 in your configured delivery folder.

Optional CapCut delivery needs the installed CapCut plugin and an account connection. Availability depends on that connection. Graphics are baked into the video; ask for graphic changes before final export. Follow the skill's CapCut reference, not Claude terminal commands.

## If you get stuck

- **Cannot copy a command:** open `skills/reel-editor/review/setup.html` and use Copy. If clipboard access is blocked, the entire command is selected for Command+C.
- **No review page:** ask Codex to run `prepare_review.py`, start `review_server.py --enable-builds`, then open the printed localhost URL. No claude.ai login is required.
- **Sound missing:** check `sfx_files` paths and run engine setup. Do not replace a missing file with silence.
- **Hook misplaced:** supply a timestamp; Codex should inspect that frame and use explicit positions. Request `single_line: true` for an unbroken title.
- **Captions wander:** keep `captionStyle.fixedPosition` enabled. It ignores older per-word position overrides.
- **Hair clipped:** remove any static CSS polygon mask. Refine the alpha cutout and inspect the whole segment; if it still fails, use a layout without a cutout.
- **Build failed:** the last successful review preview is retained. Ask Codex to inspect `review_build.log`.

Your footage, transcripts, sound files and renders stay outside Git. Do not commit them or API keys. This beta has been exercised on one real reel; broader device testing is still needed before a public launch.
