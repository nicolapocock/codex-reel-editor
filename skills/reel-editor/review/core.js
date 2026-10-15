// Reel review core: turns review decisions into the cut timeline. The review page and the render bridge
// (scripts/review_sync.py, which runs this same file with node) both use it, so what you approve is what renders.
// Times: "src" = seconds in the raw clip; "cut" = seconds in the finished reel (after cuts and speed-up).
(function (root) {
  // defaults (tight pacing) when a reel has no pacing: pause = gap between kept words over 0.25 s, 0.06 s air at every edit

  // decisions: {cut: [wordIdx...], restoredFillers: [wordIdx...], restoredPauses: [wordIdx...]}
  // A pause is keyed by the index of the word BEFORE it.
  function plan(reel, d) {
    const PAUSE = (reel.pacing || {}).pause_min ?? 0.25, PAD = (reel.pacing || {}).air ?? 0.06;   // from brand pacing
    const W = reel.words, cut = new Set(d.cut || []);
    const fillerBack = new Set(d.restoredFillers || []), pauseBack = new Set(d.restoredPauses || []);
    const removed = i => cut.has(i) || (W[i].filler && !fillerBack.has(i));
    const kept = []; for (let i = 0; i < W.length; i++) if (!removed(i)) kept.push(i);
    const spans = [], pauses = [];
    let a = null;
    for (let k = 0; k < kept.length; k++) {
      const i = kept[k], w = W[i];
      if (a === null) a = Math.max(0, w.s - PAD);
      const j = kept[k + 1];
      if (j === undefined) { spans.push([a, Math.min(reel.srcDur, w.e + 0.1)]); break; }
      const nxt = W[j], gap = nxt.s - w.e, adjacent = j === i + 1;
      const isPause = adjacent && gap > PAUSE;
      if (isPause) pauses.push({ after: i, s: w.e, e: nxt.s, len: gap, kept: pauseBack.has(i) || (reel.keepPauses || []).includes(i) && !(d.trimmedPauses || []).includes(i) });
      const pauseKept = isPause && pauses[pauses.length - 1].kept;
      if (!adjacent || (isPause && !pauseKept)) { spans.push([a, w.e + PAD]); a = Math.max(w.e + PAD, nxt.s - PAD); }
    }
    // cut-timeline map (speed applied)
    const speed = reel.speed || 1.1, starts = []; let acc = 0;
    for (const [s, e] of spans) { starts.push(acc); acc += (e - s) / speed; }
    const cutDur = acc;
    function toCut(t) {   // source time -> cut time; a time inside a removed stretch snaps to the next kept moment
      for (let k = 0; k < spans.length; k++) {
        const [s, e] = spans[k];
        if (t < s) return starts[k];
        if (t <= e) return starts[k] + (t - s) / speed;
      }
      return cutDur;
    }
    function toSrc(c) {   // cut time -> source time (for rough-cut playback seeking)
      for (let k = 0; k < spans.length; k++) {
        const len = (spans[k][1] - spans[k][0]) / speed;
        if (c <= starts[k] + len) return spans[k][0] + (c - starts[k]) * speed;
      }
      return spans.length ? spans[spans.length - 1][1] : 0;
    }
    return { spans, pauses, kept, removed, toCut, toSrc, cutDur, speed };
  }

  // captions: [{w:[idx...], acc:[idx...], text?:"override", nudge?:sec}] in source words -> cut-time captions
  function captions(reel, d, P) {
    const caps = d.captions || reel.captions, out = [];
    caps.forEach((c, ci) => {
      const live = c.w.filter(i => !P.removed(i));
      if (!live.length) { out.push({ ci, gone: true }); return; }
      const t0 = P.toCut(reel.words[live[0]].s) + (c.nudge || 0);
      const last = reel.words[live[live.length - 1]];
      let words;
      if (c.text) {   // reworded: spread the new words across the caption's span
        const toks = c.text.split(/\s+/).filter(Boolean), span = Math.max(P.toCut(last.e) - t0, 0.12);
        words = toks.map((t, k) => ({ text: t, t: t0 + span * k / toks.length, accent: (c.accText || []).includes(k) }));
      } else words = live.map(i => ({ text: reel.words[i].text, t: Math.max(t0, P.toCut(reel.words[i].s)), accent: (c.acc || []).includes(i), i }));
      out.push({ ci, start: t0, end: P.toCut(last.e) + 0.2, words });
    });
    // overlaps and boundaries: each caption ends where the next begins; never shorter than 0.12 s; clamp to the reel
    const live = out.filter(c => !c.gone).sort((a, b) => a.start - b.start);
    for (let k = 0; k < live.length; k++) {
      const c = live[k], n = live[k + 1];
      c.start = Math.max(0, Math.min(c.start, P.cutDur - 0.12));
      if (n) c.end = Math.min(c.end, Math.max(n.start, c.start + 0.12));
      c.end = Math.min(Math.max(c.end, c.start + 0.12), P.cutDur);
      if (n && n.start < c.start + 0.12) { n.start = c.start + 0.12; c.overlapFixed = true; }
    }
    return out;
  }

  // graphics anchored to source words -> cut-time windows; a card ends with its phrase unless endWord is set
  function graphics(reel, d, P) {
    const W = reel.words, firstKeptFrom = i => { for (let k = i; k < W.length; k++) if (!P.removed(k)) return k; return null; };
    return reel.board.map(g => {
      const state = ((d.board || {})[g.id] || {}).state || "k";
      const a = firstKeptFrom(g.w0);
      if (a === null) return { ...g, state, gone: true };
      let endSrc;
      if (g.w1 != null && !P.removed(g.w1)) endSrc = W[g.w1].e;
      else { let k = a; while (k < W.length - 1 && !/[.,!?;:]$/.test(W[k].text) && W[k + 1].s - W[k].e < 0.35 && P.toCut(W[k].e) - P.toCut(W[a].s) < 4) k++; endSrc = W[k].e; }
      const start = P.toCut(W[a].s), end = Math.max(start + 1, P.toCut(endSrc) + 0.15);
      return { ...g, state, start, end: Math.min(end, P.cutDur), moved: a !== g.w0 };
    });
  }

  // a fingerprint of everything that changes the render, to tell whether a built preview is outdated
  function hash(d) {
    const s = JSON.stringify([d.cut, d.restoredFillers, d.restoredPauses, d.trimmedPauses, d.captions, d.board, d.sfxOff, d.captionStyle || {}, d.audioMode || "cleaned"]);
    let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
    return (h >>> 0).toString(36);
  }

  const api = { plan, captions, graphics, hash };
  if (typeof module !== "undefined") module.exports = api; else root.ReelCore = api;
})(this);
