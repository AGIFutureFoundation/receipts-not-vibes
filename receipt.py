#!/usr/bin/env python3
"""
receipt.py — the "Receipts, Not Vibes" provenance engine.

Takes a text document, splits it into passages, scores each passage for AI
authorship, and produces a PROVENANCE RECEIPT (JSON + rendered HTML):
per-passage fraction_ai / fraction_ai_assisted / fraction_human, window-level
segments, and a summary separating human-authored facts from AI-drafted prose.

Scoring goes through a Pangram adapter:
  * If PANGRAM_API_KEY is set in the environment (and the pangram SDK is
    installed), passages are scored with the real Pangram API
    (Pangram().predict(text, model="pangram-4")).
  * Otherwise the engine falls back to DEMO MODE — a deterministic heuristic
    scorer. Every receipt produced in demo mode is labelled, in the JSON and
    at the top of the rendered HTML:

        "DEMO MODE — heuristic scoring, not Pangram"

    Nothing produced by the heuristic is ever presented as a Pangram result.

Export rule (the product's point): a document may not be exported without
its receipt attached. The receipt carries that rule in its own text.

Usage:
    python3 receipt.py INPUT.txt --title "My document" \
        --out-json receipt.json --out-html receipt.html
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone

DEMO_LABEL = "DEMO MODE — heuristic scoring, not Pangram"
EXPORT_RULE = "This document may not be exported without this receipt attached."
TOOL_NAME = "Receipts, Not Vibes — provenance receipt engine"
TOOL_VERSION = "0.1.0 (SF Non-Slop Hackathon, 2026-11-24)"

# ---------------------------------------------------------------------------
# Passage splitting
# ---------------------------------------------------------------------------

def split_passages(text):
    """Split a document into passages on blank lines. Returns list of dicts."""
    raw = re.split(r"\n\s*\n", text.strip())
    passages = []
    for chunk in raw:
        chunk = chunk.strip()
        if not chunk:
            continue
        passages.append({
            "index": len(passages) + 1,
            "text": chunk,
            "word_count": len(chunk.split()),
        })
    return passages


def split_windows(text, target_words=45):
    """Split a passage into window segments of roughly `target_words` words,
    breaking on sentence boundaries where possible (Pangram-style windows)."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    windows, current = [], ""
    for sent in sentences:
        if not sent:
            continue
        candidate = (current + " " + sent).strip()
        if current and len(candidate.split()) > target_words:
            windows.append(current)
            current = sent
        else:
            current = candidate
    if current:
        windows.append(current)
    return windows or [text]

# ---------------------------------------------------------------------------
# DEMO MODE heuristic scorer (deterministic; clearly labelled everywhere)
# ---------------------------------------------------------------------------

_SLOP_LEXICON = [
    "delve", "leverage", "leveraging", "synergy", "synergies", "furthermore",
    "moreover", "in conclusion", "it's important to note", "it is important to note",
    "in today's", "fast-paced world", "robust", "seamless", "seamlessly",
    "cutting-edge", "cutting edge", "revolutionary", "game-changer", "game changer",
    "unlock", "unlocking", "empower", "empowering", "elevate", "streamline",
    "holistic", "tapestry", "ever-evolving", "ever evolving", "vibrant", "pivotal",
    "utilize", "utilizing", "in order to", "navigate the landscape",
    "at the forefront", "world-class", "best-in-class", "state-of-the-art",
    "transformative journey", "foster", "fostering", "harness the power",
    "landscape of", "realm of", "journey towards", "furthermore,", "additionally,",
    "not only", "but also", "whether you're", "whether you are",
]

_HUMANIZER_FILLERS = [
    "honestly", "to be fair", "fwiw", "tbh", "lol", "gonna", "kinda",
    "stuff like that", "you know", "i mean", "— wait", "oops",
]


def _features(text):
    low = text.lower()
    words = text.split()
    n = max(len(words), 1)
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    sent_lens = [len(s.split()) for s in sentences] or [n]

    slop_hits = sum(low.count(w) for w in _SLOP_LEXICON)
    filler_hits = sum(low.count(w) for w in _HUMANIZER_FILLERS)
    digits = sum(ch.isdigit() for ch in text)
    urls = len(re.findall(r"https?://|www\.", low))
    dates = len(re.findall(r"\b(19|20)\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b", text))
    money = len(re.findall(r"\$[\d,]+", text))
    # Proper nouns: capitalised words that are not sentence-initial.
    proper = 0
    for sent in sentences:
        toks = sent.split()
        for tok in toks[1:]:
            if tok[:1].isupper() and tok.strip(".,;:()\"'").isalpha():
                proper += 1
    em_dashes = text.count("—") + text.count(" -- ")

    mean_len = sum(sent_lens) / len(sent_lens)
    if len(sent_lens) > 1:
        var = sum((x - mean_len) ** 2 for x in sent_lens) / len(sent_lens)
        std_len = math.sqrt(var)
    else:
        std_len = mean_len * 0.5
    uniformity = 1.0 / (1.0 + (std_len / max(mean_len, 1.0)) * 2.0)  # 0..1, high = uniform

    unique_ratio = len(set(w.strip(".,;:!?\"'()").lower() for w in words)) / n

    return {
        "slop_per_100w": slop_hits / n * 100.0,
        "filler_per_100w": filler_hits / n * 100.0,
        "fact_signals": digits / n * 30.0 + urls * 2.0 + dates * 1.5 + money * 1.5 + proper / n * 8.0,
        "uniformity": uniformity,
        "unique_ratio": unique_ratio,
        "em_dash_per_100w": em_dashes / n * 100.0,
    }


def _clamp01(x):
    return max(0.0, min(1.0, x))


def heuristic_score(text):
    """Deterministic demo scorer. Returns (fraction_ai, fraction_ai_assisted,
    fraction_human, humanizer_score) with fractions summing to 1.0."""
    f = _features(text)
    ai_signal = (
        0.16 * f["slop_per_100w"]
        + 0.35 * f["uniformity"]
        + 0.10 * f["em_dash_per_100w"]
        + 0.20 * (1.0 - f["unique_ratio"])
        - 0.22 * min(f["fact_signals"], 2.5)
    )
    fraction_ai = _clamp01(0.08 + ai_signal)
    # Assisted share: text with some AI markers but strong factual grounding
    # reads as human-led, AI-assisted.
    assisted_signal = _clamp01(
        0.10 + 0.10 * f["slop_per_100w"] + 0.15 * f["uniformity"] - 0.10 * min(f["fact_signals"], 2.0)
    )
    fraction_ai_assisted = _clamp01(assisted_signal * (1.0 - fraction_ai))
    fraction_human = _clamp01(1.0 - fraction_ai - fraction_ai_assisted)
    total = fraction_ai + fraction_ai_assisted + fraction_human
    fraction_ai, fraction_ai_assisted, fraction_human = (
        fraction_ai / total, fraction_ai_assisted / total, fraction_human / total)
    humanizer = _clamp01(0.05 + 0.25 * f["filler_per_100w"] + (0.3 if f["slop_per_100w"] > 1.5 and f["filler_per_100w"] > 0 else 0.0))
    return fraction_ai, fraction_ai_assisted, fraction_human, humanizer

# ---------------------------------------------------------------------------
# Pangram adapter (real API when PANGRAM_API_KEY is set)
# ---------------------------------------------------------------------------

def pangram_available():
    return bool(os.environ.get("PANGRAM_API_KEY"))


def _pangram_client():
    from pangram import Pangram  # pangram-sdk; imported lazily, live mode only
    return Pangram()


def pangram_score(client, text):
    """Score one passage with the real Pangram API. Mirrors the documented
    predict() shape: fraction_ai / fraction_ai_assisted / fraction_human and
    window segments with ai_assistance_score and humanizer flags."""
    result = client.predict(text, model="pangram-4")
    get = (lambda k, d=None: result.get(k, d)) if isinstance(result, dict) else (lambda k, d=None: getattr(result, k, d))
    segments = []
    for seg in (get("windows") or get("segments") or []):
        sget = (lambda k, d=None: seg.get(k, d)) if isinstance(seg, dict) else (lambda k, d=None: getattr(seg, k, d))
        segments.append({
            "text": sget("text", ""),
            "ai_assistance_score": sget("ai_assistance_score", sget("fraction_ai", 0.0)),
            "is_humanized": bool(sget("is_humanized", False)),
            "humanizer_score": sget("humanizer_score", 0.0),
        })
    return {
        "fraction_ai": float(get("fraction_ai", 0.0)),
        "fraction_ai_assisted": float(get("fraction_ai_assisted", 0.0)),
        "fraction_human": float(get("fraction_human", 0.0)),
        "segments": segments,
        "dashboard_link": get("dashboard_link") or get("link"),
    }

# ---------------------------------------------------------------------------
# Receipt construction
# ---------------------------------------------------------------------------

def verdict_for(f_ai, f_assisted, f_human):
    if f_human >= 0.60:
        return "human-authored"
    if f_ai >= 0.60:
        return "ai-generated"
    if f_assisted >= f_human and f_assisted >= f_ai:
        return "ai-assisted"
    return "mixed"


def build_receipt(text, title, source=""):
    """Build the receipt dict for a document. Chooses Pangram live mode when
    PANGRAM_API_KEY is set and the SDK call succeeds; otherwise DEMO MODE."""
    passages = split_passages(text)
    mode = "demo"
    client = None
    if pangram_available():
        try:
            client = _pangram_client()
            mode = "pangram"
        except Exception:
            client = None
            mode = "demo"

    scored = []
    for p in passages:
        if mode == "pangram":
            try:
                s = pangram_score(client, p["text"])
            except Exception:
                mode = "demo"  # fall back honestly, label applies receipt-wide
                s = None
            if s is None:
                f_ai, f_as, f_hu, _hz = heuristic_score(p["text"])
                segments = [{
                    "text": w,
                    "ai_assistance_score": round(heuristic_score(w)[0] + heuristic_score(w)[1] / 2.0, 4),
                    "is_humanized": heuristic_score(w)[3] > 0.6,
                    "humanizer_score": round(heuristic_score(w)[3], 4),
                } for w in split_windows(p["text"])]
                s = {"fraction_ai": f_ai, "fraction_ai_assisted": f_as,
                     "fraction_human": f_hu, "segments": segments, "dashboard_link": None}
        else:
            f_ai, f_as, f_hu, _hz = heuristic_score(p["text"])
            segments = []
            for w in split_windows(p["text"]):
                w_ai, w_as, _w_hu, w_hz = heuristic_score(w)
                segments.append({
                    "text": w,
                    "ai_assistance_score": round(w_ai + w_as / 2.0, 4),
                    "is_humanized": w_hz > 0.6,
                    "humanizer_score": round(w_hz, 4),
                })
            s = {"fraction_ai": f_ai, "fraction_ai_assisted": f_as,
                 "fraction_human": f_hu, "segments": segments, "dashboard_link": None}

        scored.append({
            "index": p["index"],
            "text": p["text"],
            "word_count": p["word_count"],
            "fraction_ai": round(s["fraction_ai"], 4),
            "fraction_ai_assisted": round(s["fraction_ai_assisted"], 4),
            "fraction_human": round(s["fraction_human"], 4),
            "verdict": verdict_for(s["fraction_ai"], s["fraction_ai_assisted"], s["fraction_human"]),
            "segments": s["segments"],
            **({"pangram_dashboard_link": s["dashboard_link"]} if s.get("dashboard_link") else {}),
        })

    total_words = sum(p["word_count"] for p in scored) or 1
    wmean = lambda key: round(sum(p[key] * p["word_count"] for p in scored) / total_words, 4)
    human_idx = [p["index"] for p in scored if p["verdict"] == "human-authored"]
    ai_idx = [p["index"] for p in scored if p["verdict"] in ("ai-generated", "ai-assisted")]
    human_words = sum(p["word_count"] for p in scored if p["verdict"] == "human-authored")
    ai_words = sum(p["word_count"] for p in scored if p["verdict"] in ("ai-generated", "ai-assisted"))

    receipt = {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "mode": mode,
        "mode_label": ("Pangram API (live)" if mode == "pangram" else DEMO_LABEL),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "document_title": title,
        "source": source,
        "export_rule": EXPORT_RULE,
        "summary": {
            "passage_count": len(scored),
            "total_words": total_words,
            "overall_fraction_ai": wmean("fraction_ai"),
            "overall_fraction_ai_assisted": wmean("fraction_ai_assisted"),
            "overall_fraction_human": wmean("fraction_human"),
            "human_authored_facts": {
                "passage_indices": human_idx,
                "word_share": round(human_words / total_words, 4),
            },
            "ai_drafted_prose": {
                "passage_indices": ai_idx,
                "word_share": round(ai_words / total_words, 4),
            },
            "note": ("The receipt is a disclosure, not a verdict of quality: "
                     "it separates human-authored facts from AI-drafted prose so "
                     "a reader can see the choices, not just the output."),
        },
        "passages": scored,
    }
    return receipt

# ---------------------------------------------------------------------------
# HTML rendering (Paper-style: clean, white, generous whitespace)
# ---------------------------------------------------------------------------

_CSS = """
:root{--ink:#141414;--muted:#6b6b6b;--line:#e7e2d6;--paper:#fffdf7;--card:#ffffff;
--ai:#c2452d;--assist:#d9930d;--human:#2e7d4f}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;line-height:1.55}
.wrap{max-width:820px;margin:0 auto;padding:40px 22px 64px}
h1{font-size:1.7rem;margin:0 0 4px;letter-spacing:-.01em}
h2{font-size:1.15rem;margin:34px 0 10px}
.sub{color:var(--muted);margin:0 0 18px}
.demo-banner{border:2px solid var(--ai);color:var(--ai);border-radius:10px;
padding:10px 14px;font-weight:700;text-align:center;margin:16px 0;background:#fff}
.live-banner{border:2px solid var(--human);color:var(--human);border-radius:10px;
padding:10px 14px;font-weight:700;text-align:center;margin:16px 0;background:#fff}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:16px 18px;margin:14px 0}
.bar{display:flex;height:14px;border-radius:7px;overflow:hidden;margin:8px 0 4px;border:1px solid var(--line)}
.bar .ai{background:var(--ai)} .bar .assist{background:var(--assist)} .bar .human{background:var(--human)}
.legend{font-size:.82rem;color:var(--muted)}
.legend b{color:var(--ink)}
.verdict{display:inline-block;font-size:.78rem;font-weight:700;border:1px solid var(--line);
border-radius:999px;padding:2px 10px;margin-left:8px;background:var(--paper)}
p.txt{white-space:pre-wrap;margin:8px 0}
.seg{font-size:.82rem;border-top:1px dashed var(--line);padding:7px 0;color:#333}
.seg .score{font-weight:700}
.hum{color:var(--ai);font-weight:700}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:640px){.grid{grid-template-columns:1fr}}
.rule{font-style:italic;color:var(--muted);border-left:3px solid var(--line);padding-left:12px}
"""


def _esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def render_receipt_html(receipt, fragment=False):
    r = receipt
    banner = (f'<div class="demo-banner">{_esc(r["mode_label"])}</div>' if r["mode"] == "demo"
              else f'<div class="live-banner">Scored with the Pangram API (live)</div>')
    s = r["summary"]
    parts = []
    if not fragment:
        parts.append(f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
                     f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
                     f"<title>Provenance Receipt — {_esc(r['document_title'])}</title>"
                     f"<style>{_CSS}</style></head><body><div class='wrap'>")
    parts.append(f"<h1>Provenance Receipt</h1>")
    parts.append(f"<p class='sub'><strong>{_esc(r['document_title'])}</strong>"
                 + (f" · source: {_esc(r['source'])}" if r["source"] else "")
                 + f"<br>Generated {r['generated_at']} · {r['tool']} v{r['version']}</p>")
    parts.append(banner)
    parts.append(
        "<div class='card'><h2 style='margin-top:0'>Summary — facts vs prose</h2>"
        f"<div class='bar'><div class='ai' style='width:{s['overall_fraction_ai']*100:.1f}%'></div>"
        f"<div class='assist' style='width:{s['overall_fraction_ai_assisted']*100:.1f}%'></div>"
        f"<div class='human' style='width:{s['overall_fraction_human']*100:.1f}%'></div></div>"
        f"<p class='legend'><b>AI-generated {s['overall_fraction_ai']*100:.0f}%</b> · "
        f"<b>AI-assisted {s['overall_fraction_ai_assisted']*100:.0f}%</b> · "
        f"<b>Human {s['overall_fraction_human']*100:.0f}%</b> (word-weighted, {s['total_words']} words, "
        f"{s['passage_count']} passages)</p>"
        "<div class='grid'>"
        f"<div><strong>Human-authored facts</strong><br>Passages "
        f"{', '.join(map(str, s['human_authored_facts']['passage_indices'])) or '—'} "
        f"({s['human_authored_facts']['word_share']*100:.0f}% of words)</div>"
        f"<div><strong>AI-drafted prose</strong><br>Passages "
        f"{', '.join(map(str, s['ai_drafted_prose']['passage_indices'])) or '—'} "
        f"({s['ai_drafted_prose']['word_share']*100:.0f}% of words)</div>"
        "</div>"
        f"<p class='legend'>{_esc(s['note'])}</p></div>")
    for p in r["passages"]:
        parts.append("<div class='card'>")
        parts.append(f"<strong>Passage {p['index']}</strong> · {p['word_count']} words"
                     f"<span class='verdict'>{_esc(p['verdict'])}</span>")
        parts.append(
            f"<div class='bar'><div class='ai' style='width:{p['fraction_ai']*100:.1f}%'></div>"
            f"<div class='assist' style='width:{p['fraction_ai_assisted']*100:.1f}%'></div>"
            f"<div class='human' style='width:{p['fraction_human']*100:.1f}%'></div></div>")
        parts.append(
            f"<p class='legend'>AI {p['fraction_ai']*100:.0f}% · AI-assisted "
            f"{p['fraction_ai_assisted']*100:.0f}% · Human {p['fraction_human']*100:.0f}%</p>")
        parts.append(f"<p class='txt'>{_esc(p['text'])}</p>")
        for seg in p["segments"]:
            hum = " · <span class='hum'>humanizer detected</span>" if seg.get("is_humanized") else ""
            parts.append(
                f"<div class='seg'><span class='score'>window ai_assistance_score "
                f"{float(seg.get('ai_assistance_score', 0)):.2f}</span>{hum}<br>{_esc(seg.get('text',''))}</div>")
        parts.append("</div>")
    parts.append(f"<p class='rule'>{_esc(r['export_rule'])}</p>")
    if not fragment:
        parts.append("</div></body></html>")
    return "\n".join(parts)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate a provenance receipt for a text document.")
    ap.add_argument("input", help="Path to the text document")
    ap.add_argument("--title", default=None)
    ap.add_argument("--source", default="")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-html", default=None)
    args = ap.parse_args(argv)

    with open(args.input, encoding="utf-8") as fh:
        text = fh.read()
    title = args.title or os.path.basename(args.input)
    receipt = build_receipt(text, title, source=args.source or args.input)

    stem = os.path.splitext(args.input)[0]
    out_json = args.out_json or (stem + ".receipt.json")
    out_html = args.out_html or (stem + ".receipt.html")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2, ensure_ascii=False)
    with open(out_html, "w", encoding="utf-8") as fh:
        fh.write(render_receipt_html(receipt))

    s = receipt["summary"]
    print(f"mode: {receipt['mode']} — {receipt['mode_label']}")
    print(f"passages: {s['passage_count']} · words: {s['total_words']}")
    print(f"overall: ai={s['overall_fraction_ai']} assisted={s['overall_fraction_ai_assisted']} human={s['overall_fraction_human']}")
    print(f"wrote {out_json} and {out_html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
