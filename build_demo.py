#!/usr/bin/env python3
"""
build_demo.py — builds demo.html, the single self-contained demo page.

Reads the generated receipts (showcase_a/, showcase_b/) and embeds them via
receipt.py's own renderer, so the page shows real engine output — never
hand-typed numbers. Paper-style clean design, inline CSS/JS only, no
external assets. The Showcase B gate buttons flip the decision in-page so a
human can demo both outcomes live; the recorded pipeline state stays
BLOCKED until a human acts, which is the point of the product.

Run generate_showcase_a.py and generate_showcase_b.py first (build_demo
runs them itself if their outputs are missing).
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from receipt import render_receipt_html, _CSS, _esc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

PAGE_CSS = _CSS + """
.hero{padding:26px 0 6px}
.hero h1{font-size:2.3rem}
.tag{font-size:1.1rem;color:#333;max-width:640px}
.eventline{color:var(--muted);font-size:.95rem}
.script td{padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.script td.t{font-weight:700;white-space:nowrap;color:var(--muted)}
.gateflow{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0}
.step{border:1px solid var(--line);border-radius:10px;padding:8px 12px;background:#fff;font-size:.9rem}
.step.done{border-color:var(--human)}
.step.blocked{border-color:var(--ai);border-width:2px;font-weight:700}
.arrow{color:var(--muted)}
button{font:inherit;border-radius:999px;padding:8px 18px;border:1px solid var(--ink);
background:var(--ink);color:#fff;cursor:pointer;margin-right:8px}
button.reject{background:#fff;color:var(--ai);border-color:var(--ai)}
button.approve{background:var(--human);border-color:var(--human)}
#gateDecision{font-weight:700;margin-top:10px}
.sponsors{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.sponsors .card{margin:0}
footer{color:var(--muted);font-size:.85rem;margin-top:40px;border-top:1px solid var(--line);padding-top:14px}
details{margin:10px 0}
summary{cursor:pointer;font-weight:600}
"""


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def pct(x):
    return f"{x * 100:.0f}%"


def main():
    a_dir, b_dir = os.path.join(HERE, "showcase_a"), os.path.join(HERE, "showcase_b")
    if not os.path.exists(os.path.join(a_dir, "one_apply_packet.receipt.json")):
        subprocess.run([sys.executable, os.path.join(HERE, "generate_showcase_a.py")], check=True)
    if not os.path.exists(os.path.join(b_dir, "gate_record.json")):
        subprocess.run([sys.executable, os.path.join(HERE, "generate_showcase_b.py")], check=True)

    packet_r = load_json(os.path.join(a_dir, "one_apply_packet.receipt.json"))
    slop_r = load_json(os.path.join(a_dir, "slop_control.receipt.json"))
    gate = load_json(os.path.join(b_dir, "gate_record.json"))
    sub_r = load_json(os.path.join(b_dir, "agent_submission.receipt.json"))
    ps, ss, bs = packet_r["summary"], slop_r["summary"], sub_r["summary"]
    mode_banner = ('<div class="demo-banner">DEMO MODE — heuristic scoring, not Pangram. '
                   'Live mode activates when PANGRAM_API_KEY is set.</div>'
                   if packet_r["mode"] == "demo" else
                   '<div class="live-banner">Scored with the Pangram API (live)</div>')

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Receipts, Not Vibes — SF Non-Slop Hackathon</title>
<style>{PAGE_CSS}</style></head>
<body><div class="wrap">

<div class="hero">
<h1>Receipts, Not Vibes</h1>
<p class="tag">Every document our agents produce ships with a <strong>provenance receipt</strong> —
a passage-by-passage account of what a human wrote and what an AI drafted. Slop is output
without receipts. This is the receipt.</p>
<p class="eventline">SF Non-Slop Hackathon | Pangram x Kino x Capy x Paper · Tue Nov 24, 2026 ·
San Francisco · hosted by Pangram Labs · built tonight by the AGI Future Foundation team</p>
</div>

{mode_banner}

<h2>The 60-second demo</h2>
<div class="card"><table class="script">
<tr><td class="t">0:00</td><td>Run the <strong>slop control</strong> — a generic AI grant blurb.
It lights up: <strong>{pct(ss['overall_fraction_ai'])} AI-generated, {pct(ss['overall_fraction_human'])} human</strong>,
window by window.</td></tr>
<tr><td class="t">0:15</td><td>“Now ours.” A real <strong>One-Apply packet</strong> — generated from the live
528-programme dataset for an actual submission — scores <strong>{pct(ps['overall_fraction_human'])} human</strong>.</td></tr>
<tr><td class="t">0:30</td><td>Open its receipt: the verified facts (entity record, credits ledger) read
human-authored; the drafted narrative is labelled AI-assisted, windows highlighted. Nothing hidden.</td></tr>
<tr><td class="t">0:45</td><td>Showcase B: an agent's package hits <strong>SparkHub's merge gate</strong> and stops.
Receipt attached — <strong>{pct(bs['overall_fraction_ai'])} AI, {pct(bs['overall_fraction_human'])} human</strong> —
and no agent can merge its own work. A human decides, below, live.</td></tr>
<tr><td class="t">0:55</td><td>Close: “The agents did the typing. Every decision you just saw was a person's —
and every word carries its receipt.”</td></tr>
</table></div>

<h2>Showcase A — One-Apply: the packet that proves who wrote it</h2>
<p>One-Apply matches founders against 528 funding programmes with structured eligibility gates.
Tonight it also proves authorship: the packet below was generated from the real dataset for the
Transformative AI Fund (a programme the Foundation actually applied to), and it cannot be exported
without its receipt.</p>
<details><summary>Slop control receipt — the generic blurb, scored</summary>
{render_receipt_html(slop_r, fragment=True)}
</details>
<details open><summary>One-Apply packet receipt — the real application, scored</summary>
{render_receipt_html(packet_r, fragment=True)}
</details>

<h2>Showcase B — SparkHub: the merge gate, with receipt attached</h2>
<p>An agent crew member submits a package to SparkHub. The pipeline attaches its provenance
receipt automatically — then stops. Merging is a human's job.</p>
<div class="card">
<div class="gateflow">
<span class="step done">1 · Agent submits<br><small>{_esc(gate['package'])} v{_esc(gate['version'])}</small></span>
<span class="arrow">→</span>
<span class="step done">2 · Receipt attached<br><small>AI {pct(bs['overall_fraction_ai'])} · assisted {pct(bs['overall_fraction_ai_assisted'])} · human {pct(bs['overall_fraction_human'])}</small></span>
<span class="arrow">→</span>
<span class="step blocked" id="gateStep">3 · Human merge gate<br><small>BLOCKED — awaiting human decision</small></span>
<span class="arrow">→</span>
<span class="step">4 · Publish to registry<br><small>not reached</small></span>
</div>
<p><em>{_esc(gate['change_summary'])}</em> — submitted by {_esc(gate['submitted_by_agent'])}</p>
<button class="approve" onclick="decide(true)">Approve merge</button>
<button class="reject" onclick="decide(false)">Reject with reason</button>
<p id="gateDecision">No decision yet. In the real pipeline, this is where every agent's work waits for a person.</p>
</div>
<details><summary>The submission's provenance receipt</summary>
{render_receipt_html(sub_r, fragment=True)}
</details>

<h2>Our sponsors tonight</h2>
<div class="sponsors">
<div class="card"><strong>Pangram</strong><br>AI-content detection API — the engine inside every
receipt on this page. $1,000 participant credits; $1,000 cash prize.</div>
<div class="card"><strong>Kino</strong><br>Code-first, agent-drivable video editor — our demo-film
toolchain. 2 months of Kino Pro for participants; $1,000 cash + 1 year of Kino Pro prize.</div>
<div class="card"><strong>Capy</strong><br>Cloud coding-agent crews that ship PRs — the hands;
SparkHub's gate stays the judge. 1 month of Capy Max for participants; $1,000 cash prize.</div>
<div class="card"><strong>Paper</strong><br>Design canvas that is real HTML/CSS — this page's
design language. Paper Pro free during the event; $1,000 cash + 1 year of Paper Pro prize.</div>
</div>

<h2>Our work</h2>
<div class="card">
<p><strong>Founders One-Apply</strong> — one application matched against 528 programmes from 483
providers. <a href="https://builderspace.tech/one-apply.html">builderspace.tech/one-apply.html</a><br>
<strong>SparkHub</strong> — NANDA-protocol agent registry with human merge gates.
<a href="https://sparkhub.agi.lease">sparkhub.agi.lease</a><br>
<strong>Ask Humanity</strong> — consent-first alignment research; answers belong to the people who
give them. <a href="https://ask.fellowship.chat">ask.fellowship.chat</a><br>
<strong>Bayou to the Bay</strong> — Louisiana food concierge, full menus and ordering flow.<br>
<strong>LoopForge</strong> — consent-data loop built at the European Startup House hackathon.
<a href="https://loopforge.agi.lease">loopforge.agi.lease</a></p>
</div>

<footer>
Receipts, Not Vibes — built at the SF Non-Slop Hackathon, Nov 24 2026, by the AGI Future Foundation.
Scoring mode for every receipt on this page: <strong>{_esc(packet_r['mode_label'])}</strong>.
Live Pangram mode activates the moment the API key lands; until then, demo-mode receipts are
labelled as demo mode, on the receipt itself, every time.
</footer>

</div>
<script>
function decide(ok){{
  var step = document.getElementById('gateStep');
  var out = document.getElementById('gateDecision');
  if(ok){{
    step.className = 'step done';
    step.innerHTML = '3 · Human merge gate<br><small>APPROVED by a human — publishing</small>';
    out.textContent = 'Decision recorded: a human approved this merge, receipt attached. That decision — not the agent\u2019s work — is what publishes.';
  }} else {{
    step.className = 'step blocked';
    step.innerHTML = '3 · Human merge gate<br><small>REJECTED by a human — returned to the agent</small>';
    out.textContent = 'Decision recorded: rejected with a reason. The agent thread wakes, reads the reason, and revises. Nothing merged.';
  }}
}}
</script>
</body></html>"""

    out = os.path.join(HERE, "demo.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {out} ({len(html)} bytes)")
    print(f"scores on page: packet human={ps['overall_fraction_human']} · slop ai={ss['overall_fraction_ai']} · gate ai={bs['overall_fraction_ai']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
