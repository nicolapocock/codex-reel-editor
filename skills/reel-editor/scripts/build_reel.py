#!/usr/bin/env python3
"""Turn edit.json + brand.json into a HyperFrames project (one fixed template, no per-reel installs), ready to render.
Usage: python3 build_reel.py <reel-folder> [--capcut]
  --capcut  leave captions and sound effects out of the render and write captions.json + sfx.json for CapCut instead.

edit.json (written by auto_edit.py, then Claude marks accents and adds cards):
  captions: [{start, end, words: [{text, t, accent}], plain?}]   plain = basic white sans (a "before" look), not brand
  punch:    [seconds | [seconds, scale]]    quick zoom-ins on the camera (alternate in/out; [t, 1.25] forces a level)
  cards:    [{type, start, end, ...}]       types:
     title  {text: "line one / line two"}            big headline in the space above the head (hook)
     block  {top: "don't", bottom: "worry"}          full brand-colour screen with the clip framed in it (reveal)
     card   {title: "my stack", rows: ["a","b"], y?: 150}  white UI card, rows appear one by one (lists, steps, tools)
     tag    {text: "open source", y: 300}            small pill label that pops on (name drops)
     (every card: leave out "end" and it clears when the phrase it starts in finishes)
     cta    {text: "comment EDIT", y?: 1360}         call-to-action pill (kept above the bottom ~420 px IG covers); CAPS word = pop colour
     shot   {src: "shots/tool.png", label: "heyclicky.com", y?: 130}   website screenshot in a browser window (make it with screenshot.sh);
                                                     set y lower (e.g. 1000) when the face sits high in frame
     image  {src: ["a.png", "b.jpg"]}               1-3 images fanned out above the head (their own photos, screenshots, stock)
     sticker {src: "sticker.png", x: 760, y: 420, size: 260}  transparent PNG that bounces on (brand stickers, emoji, logos)
     page   {bg: "image.jpg" or "#hex", title: "how it works"}   full-screen background with the clip framed below it
                                                     (the fast green-screen look: no cut-out, renders in seconds)
     editorial {layout: [{text, x, y, size, z?}], subject?: "alpha.webm"} positioned hook words; optional synchronized cutout
     orbit_carousel {images: [...], subject: "alpha.webm"} six reel covers orbiting a synchronized torso cutout
     motion {name: "carousel-vision-1", vars: {...}, box: [x, y, w, h]}   any HyperFrames catalog motion cached in
                                                     engine/hf (see references/motions.md for names + vars). Carousels take
                                                     images: {"images": ["a.png", ...]} and the slots are filled for you.
     follow {words: [{text, accent}], framing: "wide"}   caption-camera-follow in brand colours/font: one sentence
                                                     written word by word across a camera that pulls back (hook moments)
  Any card: "glass": true gives the frosted liquid-glass look (card, tag).
  Image paths: relative to the reel folder, or to $REELS_HOME/assets/, or absolute.
"""
import html, json, math, os, re, shutil, subprocess, sys
from pathlib import Path
from edit_policy import prepare_edit, sound_name

reel = Path(sys.argv[1]).expanduser()
CAPCUT = "--capcut" in sys.argv
HOME = Path(os.environ.get("REELS_HOME", "~/reels")).expanduser()
ENGINE = Path(__file__).resolve().parent.parent / "engine"
brand = json.load(open(HOME / "brand.json"))
edit = prepare_edit(json.load(open(reel / "edit.json")), brand)

C = brand["colors"]
MAIN, POP, LIGHT = C["main"], C["pop"], C.get("light", "#FFFFFF")
CAP, CAP_ACC = C.get("caption", "#FFFFFF"), C.get("caption_accent", POP)
CAPS = brand.get("captions", {})
CASE = CAPS.get("case", "lower")
CAP_PX = max(32, min(150, edit.get("captionStyle", {}).get("capSize", CAPS.get("size", 96))))
CAP_Y = max(200, min(1550, edit.get("captionStyle", {}).get("capY", CAPS.get("y", 1250))))
W, H, FPS = 1080, 1920, 30                     # authored at 1080x1920; 4K brands render with --resolution portrait-4k
SAFE = 900                                     # guardrail: no text line may be wider than this (90 px margin each side)
EM = 0.66                                      # conservative average glyph width (bold display fonts run ~0.6-0.66 em)
def fit(text, want, extra=0):
    """Largest size <= want at which `text` stays inside the safe area (extra = outline px on each side)."""
    return max(24, min(int(want), int((SAFE - 2 * extra) / (max(len(text), 1) * EM))))

def dur_of(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True, check=True).stdout)
DUR = round(dur_of(reel / "master.mp4") - 0.02, 2)
q = lambda t: round(round(max(t, 0) * FPS) / FPS, 4)
esc = lambda s: html.escape(s, quote=False)
case = lambda s: s.lower() if CASE == "lower" else s

# ---- project folder: template files are copied, never installed -------------------------------------------------
proj = reel / "proj"
if proj.exists(): shutil.rmtree(proj)
(proj / "fonts").mkdir(parents=True); (proj / "sfx").mkdir(); (proj / "vendor").mkdir()
shutil.copy(ENGINE / "gsap.min.js", proj / "vendor/gsap.min.js")
try: os.link(reel / "master.mp4", proj / "master.mp4")
except OSError: shutil.copy(reel / "master.mp4", proj / "master.mp4")
for f in (ENGINE / "sfx").glob("*.wav"): shutil.copy(f, proj / "sfx" / f.name)
(proj / "img").mkdir()
HF = ENGINE / "hf"
if any(k["type"] in ("motion", "follow") for k in edit.get("cards", [])):
    (proj / "compositions/components").mkdir(parents=True); shutil.copytree(HF / "assets", proj / "assets", dirs_exist_ok=True)
def mount(src):
    """Copy one cached motion into the reel, minus any audio it ships with (our own sound effects do that job)."""
    rel = src.relative_to(HF).as_posix()
    (proj / rel).write_text(re.sub(r"<audio[^>]*>(</audio>)?", "", src.read_text()))
    return rel
def img(src):
    """Copy an image into the project and return its path there. Looks in the reel folder, $REELS_HOME/assets/, then as given."""
    for cand in (reel / src, HOME / "assets" / src, Path(src).expanduser()):
        if cand.exists():
            dst = proj / "img" / f"{len(list((proj / 'img').iterdir()))}_{cand.stem}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cand), "-vf", "scale='min(1280,iw)':-2", str(dst)], check=True)
            return f"img/{dst.name}"
    print(f"warning: image not found: {src}"); return ""

# fonts: brand.json "fonts": {"head": {...}, "body": {...}, "accent": {...}}, each {family, file?, weight?, style?}
FALLBACK = "'Helvetica Neue', Helvetica, Arial, sans-serif"   # single quotes: these go inside style="..." attributes
font_css, FAM = [], {}
for role, default in (("head", {"family": "Helvetica Neue", "weight": 700}), ("body", {"family": "Helvetica Neue", "weight": 500}),
                      ("accent", {"family": "Georgia", "weight": 400, "style": "italic"})):
    f = {**default, **brand.get("fonts", {}).get(role, {})}
    if f.get("file"):
        src = Path(f["file"]).expanduser()
        if src.exists():
            shutil.copy(src, proj / "fonts" / src.name)
            fmt = {"otf": "opentype", "ttf": "truetype", "woff2": "woff2", "woff": "woff"}.get(src.suffix[1:].lower(), "opentype")
            font_css.append(f'@font-face {{ font-family: "{f["family"]}-{role}"; src: url("fonts/{src.name}") format("{fmt}"); font-display: block; }}')
            f["family"] = f'{f["family"]}-{role}'
        else:
            print(f"warning: font file not found, using fallback: {src}")
    FAM[role] = (f"'{f['family']}', {FALLBACK}", f.get("weight", 400), f.get("style", "normal"))
def font(role, px):
    fam, wt, st = FAM[role]
    return f"font-family:{fam};font-weight:{wt};font-style:{st};font-size:{px}px"

back, mid, front, audio, js = [], [], [], [], []
n_sfx = 0
CAPCUT_NAME = {"swish": "whoosh-short", "whoosh": "whoosh-short", "pop": "pop", "snap": "snap", "typing": "typing",
               "chime": "chime", "sparkle": "sparkle", "coin": "coin"}   # local file -> CapCut library sound (capcut_draft.py)
def sfx(name, t, db=-12, level="subtle", dur=None):
    """Subtle, ASMR-clean accents: every effect sits 10-15 dB under the voice (db = level relative to full scale).
    level = lowest brand sfx setting that still plays it. CapCut route: recorded for CapCut's real library sounds."""
    global n_sfx
    global CARD_SFX
    if CARD_MUTE: return                                  # this graphic's sound was switched off in the review
    if CARD_SFX and level == "subtle":                    # the sound approved in the review replaces the entrance sound
        name, db = {"sparkle": "chime"}.get(CARD_SFX["name"], CARD_SFX["name"]) if not CAPCUT else CARD_SFX["name"], CARD_SFX.get("db", db)
        CARD_SFX = None
    if brand.get("sfx", "subtle") == "none" or (level == "lots" and brand.get("sfx") != "lots") or t >= DUR: return
    vol = round(min(1.0, 10 ** ((db + brand.get("sfx_gain_db", 0)) / 20)), 3)   # explicit brand gain; keep effects under speech by default
    if CAPCUT:
        SFX_OUT.append({"name": CAPCUT_NAME.get(name, name), "t": round(max(t, 0), 2), "vol": vol, **({"dur": dur} if dur else {})}); return
    overrides = brand.get("sfx_files", {})
    custom = overrides.get(name) or overrides.get(sound_name(name))
    if custom:
        source = Path(custom).expanduser()
        if not source.is_absolute(): source = HOME / source
        if not source.is_file(): raise ValueError(f"Sound file missing: {source}")
        p = proj / "sfx" / f"custom-{n_sfx+1}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-ar", "48000", "-ac", "2", str(p)], check=True)
    else:
        name = sound_name(name)
        p = proj / "sfx" / f"{name}.wav"
    if not p.exists(): raise ValueError(f"Sound {name!r} unavailable. Run setup_engine.sh or set brand.sfx_files.")
    n_sfx += 1
    d = min(dur or dur_of(p), dur_of(p), DUR - t)
    audio.append(f'<audio id="sx{n_sfx}" src="sfx/{p.name}" data-start="{q(t)}" data-duration="{q(d)}" '
                 f'data-track-index="{20 + n_sfx}" data-volume="{vol}"></audio>')
SFX_OUT = []
CARD_MUTE = False
CARD_SFX = None
def show(sel, a, b, fade=0.18):
    b = max(b, a + 0.12); fade = min(fade, (b - a) / 2)              # very short words: keep the fade after the reveal
    js.append(f'tl.set("{sel}",{{autoAlpha:1}},{q(a)});tl.to("{sel}",{{autoAlpha:0,duration:{fade}}},{q(b - fade)});')

# ---- camera punch-ins ---------------------------------------------------------------------------------------------
for k, t in enumerate(edit.get("punch", [])):   # [t, scale] forces a zoom level (e.g. a spoken "zoom in")
    t, z = t if isinstance(t, list) else (t, 1.0 if k % 2 else 1.07)
    js.append(f'tl.to("#cam",{{scale:{z},duration:0.22,ease:"power3.out",overwrite:"auto"}},{q(t)});')

# ---- cards --------------------------------------------------------------------------------------------------------
# Phrases from the cut's transcript: a phrase ends at punctuation or a gap over 0.35 s. A card with no "end" clears
# when the phrase it starts in finishes (min 1 s on screen), so overlays leave with their line.
_tw = json.load(open(reel / "master_transcript.json")) if (reel / "master_transcript.json").exists() else []
PHRASE_ENDS = [w["end"] for k, w in enumerate(_tw) if re.search(r"[.,!?;:]$", w["text"]) or k + 1 == len(_tw)
               or _tw[k + 1]["start"] - w["end"] > 0.35]
def phrase_end(t):
    return next((e + 0.15 for e in PHRASE_ENDS if e > t + 1.0), min(t + 2.5, DUR))

quiet = []                                      # spans where a card carries its own words, so captions step aside
for i, c in enumerate(edit.get("cards", [])):
    CARD_MUTE = c.get("sfx") is False
    CARD_SFX = c.get("sfx") if isinstance(c.get("sfx"), dict) else None
    a, b, cid = c["start"], c.get("end") or phrase_end(c["start"]), f"k{i}"
    b = min(b, DUR)
    kind = c["type"]
    if kind in ("editorial", "orbit_carousel", "guide_scroll"):
        # These effects share the camera transform with the source footage.
        # A synchronized alpha foreground provides real subject occlusion.
        pieces = []
        if c.get("subject"):
            source = reel / c["subject"]
            target = f"subject-{i}{source.suffix}"
            shutil.copy(source, proj / target)
            pieces.append(f'<video id="{cid}subject" class="clip" src="{target}" muted playsinline data-start="{q(a)}" data-duration="{q(b-a)}" data-track-index="{70+i}" style="position:absolute;inset:0;width:1080px;height:1920px;z-index:100;{c.get("subject_style", "")}"></video>')
        if kind == "editorial":
            for j, word in enumerate(c["layout"]):
                pieces.append(f'<div id="{cid}w{j}" style="position:absolute;left:{word["x"]}px;top:{word["y"]}px;{font("head", word["size"])};color:{MAIN};letter-spacing:-.055em;line-height:.9;white-space:nowrap;text-shadow:0 5px 8px #0005,0 12px 26px #0006;z-index:{word.get("z", 0)}">{esc(word["text"])}</div>')
                js.append(f'tl.fromTo("#{cid}w{j}",{{y:22,opacity:0}},{{y:0,opacity:1,duration:.22,ease:"power3.out"}},{q(a+j*.10)});')
        elif kind == "guide_scroll":
            pages = c["images"]
            page_height, gap, viewport_height = 1273, 28, 1740
            pieces.append(f'<div style="position:absolute;left:90px;top:70px;width:900px;height:{viewport_height}px;overflow:hidden;border-radius:18px;background:#FFEEF5;box-shadow:0 18px 50px #0004"><div id="{cid}pages" style="position:absolute;inset:0 auto auto 0;width:900px">'+"".join(f'<img src="{img(source)}" style="display:block;width:900px;height:{page_height}px;object-fit:contain;margin-bottom:{gap}px"/>' for source in pages)+'</div></div>')
            distance = len(pages)*(page_height+gap)-gap-viewport_height
            js.append(f'tl.fromTo("#{cid}pages",{{y:0}},{{y:-{distance},duration:{b-a-.65},ease:"none"}},{q(a+.45)});')
        else:
            images = c["images"]
            for j, source in enumerate(images):
                pieces.append(f'<img id="{cid}im{j}" src="{img(source)}" style="position:absolute;left:0;top:0;width:300px;height:534px;object-fit:cover;border-radius:14px;box-shadow:0 12px 25px #0003;transform-origin:50% 50%"/>')
                steps = 40
                for n in range(steps+1):
                    progress = n / steps
                    angle = 2*math.pi*j/len(images) + progress*1.45 - .42
                    depth = math.cos(angle)
                    scale = .80 + .24*(depth+1)/2
                    props = {"x":540+485*math.sin(angle)-150,"y":1020+95*depth-267,"scale":scale,"rotationY":-math.sin(angle)*22,"zIndex":int(200+depth*50) if depth>=0 else int(40+depth*30)}
                    if n == 0: js.append(f'tl.set("#{cid}im{j}",{json.dumps(props)},{q(a)});')
                    else: js.append(f'tl.to("#{cid}im{j}",{json.dumps({**props,"duration":(b-a)/steps,"ease":"none"})},{q(a+(n-1)*(b-a)/steps)});')
        back.append(f'<div id="{cid}" style="position:absolute;inset:0">'+"".join(pieces)+'</div>')
        show(f"#{cid}",a,b,.10)
        sfx("swish" if kind in ("orbit_carousel", "guide_scroll") else "snap",a,-12)
    elif kind == "title":
        lines = [case(x.strip()) for x in c["text"].split("/")]
        if c.get("quiet", True): quiet.append((a, b))                    # the hook says it: captions step aside ("quiet": false keeps them)
        sizes = [c.get("size") or fit(x, 230, 230 // 16) for x in lines]   # each line fitted on its own, outline included; "size" overrides (tight-tracked fonts fit bigger)
        ol = brand.get("title_outline", "#FFFFFF")                     # outline is for the hook title only, never captions
        olw = brand.get("title_outline_px")                            # fixed outline width (e.g. 2 for a faint hairline); default scales with size
        st = lambda px: f";-webkit-text-stroke:{olw or max(6, px // 16)}px {ol};paint-order:stroke fill" if ol else ""
        back.append(f'<div id="{cid}" class="title" style="{font("head", sizes[0])};top:{c.get("y", brand.get("title_y", 360))}px;color:{c.get("color", MAIN)};letter-spacing:{brand.get("title_tracking", -0.045)}em">'
                    + "".join(f'<div class="tl" style="font-size:{px}px;text-align:{("left", "right")[j % 2] if len(lines) > 1 else "center"}{st(px)}">{esc(x)}</div>' for j, (x, px) in enumerate(zip(lines, sizes))) + "</div>")
        show(f"#{cid}", a, b)
        js.append(f'tl.fromTo("#{cid} .tl",{{clipPath:"inset(-40% 100% -40% 0%)",x:-30}},{{clipPath:"inset(-40% 0% -40% 0%)",x:0,duration:0.34,ease:"power3.out",stagger:0.25}},{q(a)});')
        sfx("snap", a + 0.03, -11)
    elif kind == "block":
        quiet.append((a, b))
        mid.append(f'<div id="{cid}" class="block" style="opacity:0;visibility:hidden;background:{c.get("color", MAIN)}">'
                   f'<div class="frame"><video id="{cid}v" src="master.mp4" muted playsinline data-start="{q(a)}" data-duration="{q(b - a)}" data-media-start="{q(a)}" data-track-index="{9 + i}"></video></div>'
                   f'<div class="bl" style="{font("head", fit(c.get("top", ""), 210))};top:230px;text-align:left;color:{LIGHT}">{esc(case(c.get("top", "")))}</div>'
                   f'<div class="bl" style="{font("head", fit(c.get("bottom", ""), 210))};top:1500px;text-align:right;color:#fff">{esc(case(c.get("bottom", "")))}</div></div>')
        js.append(f'tl.set("#{cid}",{{autoAlpha:1}},{q(a)});tl.fromTo("#{cid}",{{clipPath:"inset(0% 0% 0% 100%)"}},{{clipPath:"inset(0% 0% 0% 0%)",duration:0.22,ease:"power3.out"}},{q(a)});'
                  f'tl.fromTo("#{cid} .frame",{{scale:0.82}},{{scale:1,duration:0.5,ease:"back.out(1.6)"}},{q(a + 0.05)});'
                  f'tl.fromTo("#{cid} .bl",{{clipPath:"inset(0% 100% 0% 0%)"}},{{clipPath:"inset(0% 0% 0% 0%)",duration:0.34,ease:"power3.out",stagger:0.3}},{q(a + 0.12)});'
                  f'tl.to("#{cid}",{{clipPath:"inset(0% 100% 0% 0%)",duration:0.2,ease:"power3.in"}},{q(b - 0.2)});tl.set("#{cid}",{{autoAlpha:0}},{q(b)});')
        sfx("swish", a - 0.08, -12)
    elif kind == "card":
        rows = c.get("rows", [])
        rt = c.get("row_times") or [a + 0.45 + 0.35 * j for j in range(len(rows))]
        front.append(f'<div id="{cid}" class="card{" glass" if c.get("glass") else ""}" style="top:{c.get("y", 150)}px"><div class="ch" style="background:{MAIN};{font("head", 40)}"><i></i>{esc(case(c.get("title", "")))}</div>'
                     + "".join(f'<div class="cr" id="{cid}r{j}" style="{font("body", 50)};color:{MAIN}"><b style="background:{POP}"></b>{esc(case(r))}</div>' for j, r in enumerate(rows)) + "</div>")
        show(f"#{cid}", a, b)
        js.append(f'tl.fromTo("#{cid}",{{y:-160,scale:0.85,rotation:-3}},{{y:0,scale:1,rotation:-1.5,duration:0.5,ease:"back.out(1.6)"}},{q(a)});')
        for j, t in enumerate(rt):
            js.append(f'tl.fromTo("#{cid}r{j}",{{autoAlpha:0,x:-60}},{{autoAlpha:1,x:0,duration:0.3,ease:"back.out(2)"}},{q(t)});')
            sfx("pop", t, -16, "lots")
        sfx("swish", a - 0.05, -13)
    elif kind == "tag":
        front.append(f'<div id="{cid}" class="tagw" style="top:{c.get("y", 300)}px"><span class="tag{" glass" if c.get("glass") else ""}" style="background:{c.get("color", POP)};{font("head", 58)}">{esc(case(c["text"]))}</span></div>')
        show(f"#{cid}", a, b)
        js.append(f'tl.fromTo("#{cid} .tag",{{scale:0.4,y:30,opacity:0}},{{scale:1,y:0,opacity:1,duration:0.42,ease:"back.out(3)"}},{q(a)});')
        sfx("pop", a, -14)
    elif kind == "cta":
        if c.get("quiet", True): quiet.append((a, b))
        words = c["text"].split()
        inner = " ".join(f'<span style="color:{POP}">{esc(w)}</span>' if w.isupper() and len(w) > 1 else esc(case(w)) for w in words)
        front.append(f'<div id="{cid}" class="ctaw" style="top:{c.get("y", 1360)}px"><span class="cta" style="{font("head", 78)};color:{MAIN};background:{LIGHT}">{inner}</span></div>')
        show(f"#{cid}", a, b)
        js.append(f'tl.fromTo("#{cid} .cta",{{scale:0.5,y:60,opacity:0}},{{scale:1,y:0,opacity:1,duration:0.5,ease:"back.out(2.4)"}},{q(a)});')
        sfx("coin", a + 0.1, -12)
    elif kind == "shot":
        if c.get("y", 130) + 700 > CAP_Y: quiet.append((a, b))         # screenshot covers the caption zone: captions step aside
        front.append(f'<div id="{cid}" class="shot" style="top:{c.get("y", 130)}px"><div class="bar"><i style="background:#FF5F57"></i><i style="background:#FEBC2E"></i><i style="background:#28C840"></i>'
                     f'<span style="{font("body", 30)}">{esc(c.get("label", ""))}</span></div><div class="vp"><img src="{img(c["src"])}" /></div></div>')
        show(f"#{cid}", a, b)
        js.append(f'tl.fromTo("#{cid}",{{y:-200,scale:0.8,rotation:3}},{{y:0,scale:1,rotation:1.5,duration:0.55,ease:"back.out(1.5)"}},{q(a)});'
                  f'tl.fromTo("#{cid} img",{{y:0}},{{y:-120,duration:{max(b - a - 0.8, 0.5):.2f},ease:"sine.inOut"}},{q(a + 0.6)});')
        sfx("swish", a - 0.05, -12); sfx("typing", a + 0.5, -17, dur=0.8)
    elif kind == "image":
        srcs = c["src"] if isinstance(c["src"], list) else [c["src"]]
        spots = {1: [(540, 0)], 2: [(380, -6), (700, 7)], 3: [(300, -8), (540, 3), (780, 9)]}[min(len(srcs), 3)]
        front.append(f'<div id="{cid}" class="imgs">' + "".join(
            f'<img class="ph" src="{img(s)}" style="left:{x - 210}px;transform:rotate({r}deg)" />' for s, (x, r) in zip(srcs, spots)) + "</div>")
        show(f"#{cid}", a, b)
        js.append(f'tl.fromTo("#{cid} .ph",{{y:-260,opacity:0,scale:0.7}},{{y:0,opacity:1,scale:1,duration:0.5,ease:"back.out(1.7)",stagger:0.18}},{q(a)});')
        sfx("swish", a, -13)
    elif kind == "sticker":
        sz = c.get("size", 260)
        front.append(f'<div id="{cid}" class="stk" style="left:{c.get("x", 760) - sz // 2}px;top:{c.get("y", 420) - sz // 2}px;width:{sz}px"><img src="{img(c["src"])}" /></div>')
        show(f"#{cid}", a, b, 0.15)
        js.append(f'tl.fromTo("#{cid}",{{scale:0,rotation:-25}},{{scale:1,rotation:{c.get("rotate", 6)},duration:0.5,ease:"back.out(3)"}},{q(a)});')
        sfx("pop", a, -13)
    elif kind == "page":
        bg = c.get("bg", LIGHT)
        rgb = tuple(int(LIGHT.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4))
        fade = f"linear-gradient(rgba({rgb[0]},{rgb[1]},{rgb[2]},.92) 0%, rgba({rgb[0]},{rgb[1]},{rgb[2]},.55) 28%, rgba({rgb[0]},{rgb[1]},{rgb[2]},.15) 60%)"
        bgcss = f"background:{bg}" if bg.startswith("#") else f"background:{fade}, url('{img(bg)}') center/cover"   # fade keeps the title readable
        mid.append(f'<div id="{cid}" class="page" style="opacity:0;visibility:hidden;{bgcss}">'
                   + (f'<div class="pt" style="{font("head", 92)};color:{c.get("color", MAIN)}">{esc(case(c["title"]))}</div>' if c.get("title") else "")
                   + f'<div class="pf"><video id="{cid}v" src="master.mp4" muted playsinline data-start="{q(a)}" data-duration="{q(b - a)}" data-media-start="{q(a)}" data-track-index="{9 + i}"></video></div></div>')
        js.append(f'tl.set("#{cid}",{{autoAlpha:1}},{q(a)});tl.fromTo("#{cid}",{{clipPath:"inset(100% 0% 0% 0%)"}},{{clipPath:"inset(0% 0% 0% 0%)",duration:0.3,ease:"power3.out"}},{q(a)});'
                  f'tl.fromTo("#{cid} .pf",{{y:300}},{{y:0,duration:0.5,ease:"back.out(1.4)"}},{q(a + 0.08)});'
                  f'tl.to("#{cid}",{{clipPath:"inset(0% 0% 100% 0%)",duration:0.25,ease:"power3.in"}},{q(b - 0.25)});tl.set("#{cid}",{{autoAlpha:0}},{q(b)});')
        sfx("swish", a - 0.08, -12)
    elif kind == "motion":
        src = next((f for f in (HF / "compositions").rglob(f"{c['name']}.html")), None)
        if not src:
            print(f"warning: motion {c['name']!r} not cached - add it: cd {HF} && npx hyperframes add {c['name']}"); continue
        rel = mount(src); txt = src.read_text()
        comp_id = re.search(r'data-composition-id="([^"]+)"', txt).group(1)
        nw, nh = (int(re.search(r'data-width="(\d+)"', txt).group(1)), int(re.search(r'data-height="(\d+)"', txt).group(1))) \
            if re.search(r'data-width="(\d+)"', txt) else (1080, 1080)
        vars_ = dict(c.get("vars", {}))
        if c.get("images"):                              # carousels: fill every image slot, cycling the supplied images
            slots = sorted({int(m) for m in re.findall(r'"id":\s*"image(\d+)"', txt)})
            ims = [img(x) for x in c["images"]]
            for k, sl in enumerate(slots): vars_[f"image{sl}"] = ims[k % len(ims)]
            vars_.setdefault("background", "transparent")
        x, y, bw, bh = c.get("box", [0, 160, W, int(W * nh / nw)])
        sc = bw / nw
        if y + bh * 0.7 > CAP_Y: quiet.append((a, b))   # motion sits over the caption zone: captions step aside
        vals = html.escape(json.dumps(vars_), quote=True)
        mid.append(f'<div id="{cid}" class="clip" data-composition-id="{comp_id}" data-composition-src="{rel}" data-variable-values="{vals}" '
                   f'data-start="{q(a)}" data-duration="{q(b - a)}" data-track-index="{40 + i}" data-width="{nw}" data-height="{nh}" '
                   f'style="position:absolute;left:{x}px;top:{y}px;width:{nw}px;height:{nh}px;transform:scale({sc:.4f});transform-origin:0 0;'
                   f'--brand:{MAIN};--accent:{POP};--accent-2:{C.get("soft", POP)};--surface:{LIGHT};--fg:{MAIN};--muted:{C.get("soft", POP)}"></div>')
        sfx("swish", a - 0.05, -12)
    elif kind == "follow":
        src = HF / "compositions/components/caption-camera-follow.html"
        t = src.read_text()
        words = [{"text": case(w["text"]), **({"accent": True} if w.get("accent") else {})} for w in c["words"]]
        n = max(len(words), 1); dur = b - a
        t = re.sub(r"var WORDS = \[.*?\];", "var WORDS = " + json.dumps(words) + ";", t, flags=re.S)
        t = t.replace("var DUR = 9;", f"var DUR = {dur:.2f};").replace("var STEP = 0.52;", f"var STEP = {max(0.22, (dur - 1.2) / n):.3f};")
        t = t.replace('var ACCENT = ACCENTS[pick(ACCENTS, vars.accent, "gold")];', f'var ACCENT = "{CAP_ACC}";')
        t = t.replace('data-duration="9"', f'data-duration="{dur:.2f}"')
        fam = FAM["head"][0].replace("'", '"')
        t = t.replace('font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;', f"font-family: {fam};")
        t = t.replace("'font-family:\"Helvetica Neue\",Helvetica,Arial,sans-serif;font-weight:700;'", "'font-family:" + fam.replace('"', '\\"') + ";font-weight:700;'")
        if CASE == "lower": t = t.replace("text-transform: uppercase;", "text-transform: none;").replace('"text-transform:uppercase;', '"text-transform:none;')
        t = t.replace("<style>", "<style>\n" + "\n".join(font_css), 1)   # sub-compositions need their own @font-face
        out = proj / "compositions" / f"follow-{i}.html"; out.write_text(t)
        vals = html.escape(json.dumps({"framing": c.get("framing", "wide"), "smear": c.get("smear", "subtle")}), quote=True)
        front.append(f'<div id="{cid}" class="clip" data-composition-id="caption-camera-follow" data-composition-src="compositions/follow-{i}.html" '
                     f'data-variable-values="{vals}" data-start="{q(a)}" data-duration="{q(dur)}" data-track-index="{40 + i}" '
                     f'style="position:absolute;inset:0;width:{W}px;height:{H}px"></div>')
        quiet.append((a, b)); sfx("sparkle", a, -12)
    else:
        print(f"warning: unknown card type {kind!r} - skipped")

CARD_MUTE = False
# ---- brand rule: every edit has a carousel (unless the person said no for this reel) --------------------------------
if brand.get("require_carousel") and not edit.get("no_carousel_ok") and not any(
        (k["type"] == "orbit_carousel" or (k["type"] == "motion" and "carousel" in k.get("name", ""))) for k in edit.get("cards", [])):
    sys.exit("brand rule: add a carousel motion card (or ask them; if they say no, set \"no_carousel_ok\": true in edit.json)")

# ---- captions -----------------------------------------------------------------------------------------------------
cap_json = []
for i, c in enumerate(edit.get("captions", [])):
    if any(a - 0.05 <= c["start"] < b for a, b in quiet): continue
    ws = c["words"]
    plain = c.get("plain")                                             # "before" captions: basic white sans, no brand styling
    cap_json.append({"start": c["start"], "end": c["end"], "over_light": False,
                     "lines": [[{"text": w["text"] if plain else case(w["text"]), "kind": "sm" if plain else "acc" if w.get("accent") else "big", "t": w["t"]} for w in ws]]})
    if CAPCUT: continue
    if plain:
        front.append(f'<div id="c{i}" class="cap" style="top:{CAP_Y}px;font-family:-apple-system,Helvetica,Arial,sans-serif;font-weight:500;font-size:46px;letter-spacing:0;color:#fff">{esc(" ".join(w["text"] for w in ws))}</div>')
        show(f"#c{i}", c["start"], c["end"], 0.04); continue
    fixed = edit.get("captionStyle", {}).get("fixedPosition", False)
    chars = sum(len(w["text"]) + 1 for w in ws)
    px = fit(" ".join(w["text"] for w in ws), c.get("size", CAP_PX * (1.35 if len(ws) == 1 else 1)))
    big = 1.7 if CAPS.get("style") == "editorial" else 1.12          # editorial = dramatic size contrast on the emphasis word
    big = min(big, min((fit(w["text"], px * big) / px) for w in ws if w.get("accent")) if any(w.get("accent") for w in ws) else big)
    if fixed: px, big = CAP_PX, 1.0
    blk = "display:block;line-height:.95;" if CAPS.get("style") == "editorial" and len(ws) > 1 else ""
    spans = "".join(f'<span class="acc" style="{blk}{font("accent", int(px * big))};color:{CAP_ACC}">{esc(case(w["text"]))}</span> ' if w.get("accent")
                    else f'<span>{esc(case(w["text"]))}</span> ' for w in ws)
    front.append(f'<div id="c{i}" class="cap" style="top:{c.get("y", CAP_Y)}px;left:{c.get("x", 60)}px;right:auto;width:{c.get("width", 960)}px;{font("body", int(px))};color:{CAP};letter-spacing:{CAPS.get("tracking", -0.02)}em">{spans.strip()}</div>')
    show(f"#c{i}", c["start"], c["end"], 0.06)
    if not fixed: js.append(f'tl.fromTo("#c{i}",{{scale:0.86,y:14}},{{scale:1,y:0,duration:0.16,ease:"back.out(2)"}},{q(c["start"])});')

# ---- assemble -----------------------------------------------------------------------------------------------------
doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" />
<style>
{chr(10).join(font_css)}
html, body {{ margin: 0; background: #000; overflow: hidden; }}
#stage {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
#cam {{ position: absolute; inset: 0; transform-origin: 50% 38%; }}
#cam > video {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; }}
#back, #mid, #front {{ position: absolute; inset: 0; }}
#back > :not(.clip), #mid > :not(.clip), #front > :not(.clip) {{ visibility: hidden; opacity: 0; }}   /* .clip = HyperFrames motions, timed by the runtime */
.title {{ position: absolute; left: 0; top: 170px; width: {W}px; padding: 0 90px; box-sizing: border-box; line-height: .88; letter-spacing: -.045em; text-shadow: 0 0 3px rgba(0,0,0,.18), 0 6px 34px rgba(0,0,0,.4); }}
.tl {{ white-space: nowrap; }}
.block {{ position: absolute; inset: 0; }}
.frame {{ position: absolute; left: 250px; top: 470px; width: 580px; height: 1030px; overflow: hidden; border: 10px solid #fff; border-radius: 8px; box-shadow: 0 24px 60px rgba(0,0,0,.22); }}
.frame video {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.bl {{ position: absolute; left: 0; width: {W}px; padding: 0 90px; box-sizing: border-box; line-height: .82; letter-spacing: -.05em; white-space: nowrap; }}
.card {{ position: absolute; left: 90px; top: 150px; width: 900px; background: #fff; border-radius: 40px; overflow: hidden; padding-bottom: 22px; box-shadow: 0 30px 70px rgba(0,0,0,.25); }}
.ch {{ color: #fff; padding: 24px 36px; display: flex; align-items: center; gap: 18px; letter-spacing: -.02em; }}
.ch i {{ width: 22px; height: 22px; border-radius: 50%; background: rgba(255,255,255,.7); display: inline-block; }}
.cr {{ display: flex; align-items: center; gap: 24px; height: 110px; margin: 0 36px; border-bottom: 3px solid rgba(0,0,0,.06); letter-spacing: -.02em; }}
.cr b {{ width: 26px; height: 26px; border-radius: 50%; flex: none; }}
.tagw, .ctaw {{ position: absolute; left: 0; right: 0; text-align: center; }}
.ctaw {{ top: 1360px; }}   /* above Instagram's caption + buttons zone (bottom ~420 px) */
.tag, .cta {{ display: inline-block; color: #fff; padding: 18px 42px; border-radius: 80px; letter-spacing: -.02em; box-shadow: 0 14px 34px rgba(0,0,0,.2); }}
.shot {{ position: absolute; left: 70px; top: 130px; width: 940px; border-radius: 26px; overflow: hidden; background: #fff; box-shadow: 0 34px 80px rgba(0,0,0,.3); }}
.bar {{ height: 64px; display: flex; align-items: center; gap: 12px; padding: 0 24px; background: #F2F2F4; color: #555; }}
.bar i {{ width: 18px; height: 18px; border-radius: 50%; display: inline-block; }}
.bar span {{ margin-left: 18px; background: #fff; border-radius: 14px; padding: 6px 22px; }}
.vp {{ height: 620px; overflow: hidden; }}
.vp img {{ width: 100%; display: block; }}
.imgs {{ position: absolute; left: 0; top: 140px; width: {W}px; height: 560px; }}
.ph {{ position: absolute; top: 0; width: 420px; height: 520px; object-fit: cover; border: 12px solid #fff; border-radius: 18px; box-shadow: 0 26px 60px rgba(0,0,0,.28); }}
.stk {{ position: absolute; }}
.stk img {{ width: 100%; display: block; filter: drop-shadow(0 14px 22px rgba(0,0,0,.25)); }}
.page {{ position: absolute; inset: 0; }}
.pt {{ position: absolute; left: 0; right: 0; top: 150px; text-align: center; line-height: .9; letter-spacing: -.04em; padding: 0 60px; }}
.pf {{ position: absolute; left: 190px; top: 560px; width: 700px; height: 1240px; overflow: hidden; border: 12px solid #fff; border-radius: 34px; box-shadow: 0 30px 70px rgba(0,0,0,.28); }}
.pf video {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.glass {{ background: rgba(28,22,34,.34) !important; backdrop-filter: blur(22px) saturate(1.4); -webkit-backdrop-filter: blur(22px) saturate(1.4); border: 1.5px solid rgba(255,255,255,.55); box-shadow: 0 20px 60px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.6); }}
.card.glass .cr {{ color: #fff !important; border-bottom-color: rgba(255,255,255,.25); }}
.cap {{ position: absolute; left: 60px; right: 60px; text-align: center; line-height: 1.02; letter-spacing: -.02em; height:130px;display:flex;align-items:center;justify-content:center;gap:.2em;text-shadow:0 4px 7px rgba(0,0,0,.55),0 9px 22px rgba(0,0,0,.45); }}
.cap .acc {{ text-shadow:0 4px 7px rgba(0,0,0,.55),0 9px 22px rgba(0,0,0,.45); }}   /* accent colour stays readable over white screens, no outline */
</style></head>
<body>
<div id="stage" data-composition-id="main" data-start="0" data-duration="{DUR}" data-fps="{FPS}" data-width="{W}" data-height="{H}">
  <div id="cam"><video id="bg" class="clip" src="master.mp4" playsinline data-has-audio="true" data-start="0" data-duration="{DUR}" data-track-index="1"></video>
    <div id="back">{"".join(back)}</div></div>
  <div id="mid">{"".join(mid)}</div>
  <div id="front">{"".join(front)}</div>
  {"".join(audio)}
  <script src="vendor/gsap.min.js"></script>
  <script>(function () {{ window.__timelines = window.__timelines || {{}};
    const tl = window.gsap.timeline({{ paused: true }});
    {chr(10).join(js)}
    window.__timelines["main"] = tl; }})();</script>
</div></body></html>"""
(proj / "index.html").write_text(doc)
(proj / "package.json").write_text('{"name":"reel","private":true,"type":"module"}')
if CAPCUT:
    json.dump(cap_json, open(reel / "captions.json", "w"), indent=1)
    json.dump(SFX_OUT, open(reel / "sfx.json", "w"), indent=1)
print(f"built {proj/'index.html'}: {DUR}s, {len(edit.get('cards', []))} cards, {len(cap_json)} captions, {n_sfx} sounds"
      + (" (capcut: captions.json + sfx.json written)" if CAPCUT else ""))
