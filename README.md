# Receipts, Not Vibes

**Every document our agents produce ships with a provenance receipt — a passage-by-passage account of what a human wrote and what an AI drafted. Slop is output without receipts. This is the receipt.**

Built at the **SF Non-Slop Hackathon | Pangram x Kino x Capy x Paper** — Tuesday, November 24, 2026, 5:00–10:00 PM, San Francisco, hosted by **Pangram Labs**.

---

## What it does

One engine, two showcases:

- **The engine** (`receipt.py`) takes a text document, splits it into passages, scores each passage for AI authorship, and produces a **provenance receipt** (JSON + rendered HTML): per-passage `fraction_ai` / `fraction_ai_assisted` / `fraction_human`, window-level segments with humanizer detection, and a summary that separates **human-authored facts** from **AI-drafted prose**. The receipt carries an export rule: *a document may not be exported without its receipt attached.*
- **Showcase A — One-Apply.** A real application packet, generated from the live Founders One-Apply dataset (528 programmes, 483 providers) for the Transformative AI Fund, gets its receipt. A "slop control" — a generic AI-sounding grant blurb written for this demo — is scored alongside it, and scores visibly worse.
- **Showcase B — the SparkHub gate.** An agent-submitted package description enters SparkHub's publishing pipeline, gets its receipt attached automatically, and stops at the **human merge gate**. No agent merges its own work.

### Scoring: Pangram live mode, and an honestly labelled demo mode

Scoring goes through a Pangram adapter:

- If `PANGRAM_API_KEY` is set in the environment (and `pangram-sdk` is installed), passages are scored with the real Pangram API (`predict(text, model="pangram-4")`).
- If not, the engine falls back to a deterministic heuristic scorer — **DEMO MODE**. Every demo-mode receipt prints `DEMO MODE — heuristic scoring, not Pangram` in its JSON and at the top of its HTML. Nothing the heuristic produces is ever presented as a Pangram result.

Current demo-mode results (recorded in `TEST_RESULTS.txt`):

| Document | AI-generated | AI-assisted | Human |
|---|---|---|---|
| One-Apply packet (real application) | 15% | 3% | **82%** |
| Slop control (generic AI blurb) | **100%** | 0% | 0% |
| SparkHub agent submission (Showcase B) | 34% | 8% | 58% |

## Run it

```bash
python3 generate_showcase_a.py   # builds the One-Apply packet + receipts into showcase_a/
python3 generate_showcase_b.py   # builds the SparkHub gate record + receipts into showcase_b/
python3 build_demo.py            # builds demo.html (single self-contained page)
python3 tests/test_receipt.py    # 7 end-to-end tests, DEMO MODE
python3 receipt.py any-document.txt --title "My document"   # receipt for anything
```

Open `demo.html` in a browser — that's the whole demo: both showcases, both receipts, the merge gate a human can flip live, and the 60-second demo script printed on the page.

To go live with Pangram: `pip install pangram-sdk`, set `PANGRAM_API_KEY`, re-run the generators. Receipts switch to live mode and say so.

## Sponsors

Tonight runs on four sponsors' tools, and each one is load-bearing somewhere in our stack:

- **Pangram** — the AI-content detection API inside every receipt this project produces (single `predict` for live scoring, Bulk API for corpus-scale scans). Every participant receives **$1,000 in Pangram credits**; Pangram also puts up a **$1,000 cash prize**.
- **Kino** — the code-first, agent-drivable video editor (Remotion timelines an agent and a human edit together, MCP access, auto-indexed footage). Our demo-film toolchain. Participants get **2 months of Kino Pro**; Kino's prize is **$1,000 cash + 1 year of Kino Pro** for the winning team.
- **Capy** — cloud coding-agent crews: threads on isolated machines that take tasks to pull requests and merge only on a human's say-so. In our architecture Capy supplies the parallel hands; SparkHub's gate stays the judge. Participants get **1 month of Capy Max ($200 value)**; Capy's prize is **$1,000 cash**.
- **Paper** — the design canvas that is real HTML/CSS, with an MCP server agents can read and write. This project's demo page follows Paper's design language: clean, inspectable, already code. **Paper Pro is free during the hackathon**; Paper's prize is **$1,000 cash + 1 year of Paper Pro + swag** for the winning team.

## The event

- **SF Non-Slop Hackathon | Pangram x Kino x Capy x Paper**, hosted by Pangram Labs, San Francisco, Tue Nov 24, 2026, 5:00–10:00 PM PT, in person.
- **Theme:** "What matters when you can generate anything? Can you explain your choices?" Build something intentional with AI — with Pangram's API, Kino, Capy, and Paper, plus any other tools.
- **Judges:** Lucas Igel (CEO of Kino), Leo Rodrigues, Clo Wang, Donald Jewkes, Olivia Zheng, Afra Wang.
- **Every participant receives:** $1,000 in Pangram credits · 2 months of Kino Pro · 1 month of Capy Max ($200 value) · Paper Pro free during the event · merch.

## Our work

Receipts, Not Vibes sits on top of things we already ship:

- **Founders One-Apply** — one application matched against 528 funding programmes from 483 providers, with structured eligibility gates so the tool refuses to recommend programmes you're ineligible for. https://builderspace.tech/one-apply.html
- **SparkHub** — live agent infrastructure: agents register with public profiles, publish and discover packages, and hand work to each other over the NANDA protocol, under human merge gates. https://sparkhub.agi.lease
- **Ask Humanity** — consent-first alignment research: twenty questions, consent provenance by design, answers belong to the people who give them. https://ask.fellowship.chat
- **Bayou to the Bay** — a complete multi-restaurant Louisiana food concierge: full menus, ordering flow, a parish-by-parish journey.
- **LoopForge** — a working consent-data loop with its test suite, built at the European Startup House hackathon, live on our own VPS. https://loopforge.agi.lease

## How the dual build works

```
                        ┌─────────────────────────────┐
   any document ───────▶│  receipt.py (the engine)    │
                        │  passages → scores → receipt │
                        └──────┬──────────────┬───────┘
                               │              │
                Showcase A     │              │     Showcase B
        One-Apply packet + ────┘              └──── SparkHub package →
        slop control, scored                        receipt attached →
                                                    HUMAN MERGE GATE (blocked
                                                    until a person decides)
```

The same renderer draws every receipt, so a funder reading a One-Apply packet and a maintainer reading a SparkHub submission see the same instrument. The receipt is a **disclosure, not a verdict of quality** — detector scores can be noisy on short or formulaic text, and false positives on human text are a known class-wide issue. We disclose; we don't accuse.

## Status — honest

- Built tonight, Nov 24, 2026, for this hackathon. Engine, both showcases, demo page, and tests are complete and running (7/7 tests pass in DEMO MODE — see `TEST_RESULTS.txt`).
- **Pangram live mode activates when the API key lands.** The participant credits ($1,000) are Pangram's; the account signup was in progress at build time, so tonight's receipts run in labelled DEMO MODE until the key is set. When it is, re-running the two generators re-scores everything against the real API and the receipts say "Pangram API (live)".
- The SparkHub gate demo simulates the pipeline stage locally; the live registry and its human merge gates are at sparkhub.agi.lease.
- Repo/wiki content lives in `wiki/` (Home, Sponsors, The-Event, Our-Work, Build-Log), ready to paste into a GitHub wiki.

## Layout

```
receipt.py               the engine (Pangram adapter + labelled demo fallback)
generate_showcase_a.py   One-Apply packet from the real dataset + its receipt
generate_showcase_b.py   SparkHub gate simulation + its receipt
build_demo.py            builds demo.html from the generated receipts
demo.html                the self-contained demo page
samples/slop_control.txt the generic AI blurb used as the control
showcase_a/              packet + receipts (JSON + HTML)
showcase_b/              gate record + submission receipts (JSON + HTML)
tests/test_receipt.py    end-to-end tests (plain python3 or pytest)
TEST_RESULTS.txt         recorded test + generation output
wiki/                    Home · Sponsors · The-Event · Our-Work · Build-Log
```
