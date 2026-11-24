#!/usr/bin/env python3
"""
Tests for the Receipts, Not Vibes engine — DEMO MODE end-to-end.

Runs with plain python3 (no dependencies) or under pytest:
    python3 tests/test_receipt.py
    python3 -m pytest tests/test_receipt.py

Asserts, in DEMO MODE (no PANGRAM_API_KEY in the test environment):
  1. A receipt is produced for the generated One-Apply packet and for the
     slop-control sample, end to end.
  2. Every receipt produced without a Pangram key carries the DEMO MODE
     label, in JSON and in the rendered HTML — nothing fake is ever
     presented as a real Pangram result.
  3. Passage fractions sum to 1.0 and carry window-level segments.
  4. The summary separates human-authored facts from AI-drafted prose and
     the two buckets partition the passages.
  5. The slop control scores strictly more AI than the real packet
     (the demo's core claim).
  6. The Showcase B gate record is BLOCKED at the human merge gate with
     a receipt attached.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

# Tests must exercise DEMO MODE regardless of the caller's environment.
os.environ.pop("PANGRAM_API_KEY", None)

from receipt import build_receipt, render_receipt_html, DEMO_LABEL  # noqa: E402


def _load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def _ensure_generated():
    for script in ("generate_showcase_a.py", "generate_showcase_b.py"):
        out = os.path.join(ROOT, "showcase_a", "one_apply_packet.txt")
        if not os.path.exists(out):
            subprocess.run([sys.executable, os.path.join(ROOT, script)],
                           check=True, capture_output=True)


def test_receipts_produced_for_both_samples():
    _ensure_generated()
    packet = _load(os.path.join("showcase_a", "one_apply_packet.txt"))
    slop = _load(os.path.join("samples", "slop_control.txt"))
    for text in (packet, slop):
        r = build_receipt(text, "test")
        assert r["passages"], "receipt must contain passages"
        assert r["summary"]["passage_count"] == len(r["passages"])
        assert r["summary"]["total_words"] > 100


def test_demo_mode_labelled_everywhere():
    _ensure_generated()
    packet = _load(os.path.join("showcase_a", "one_apply_packet.txt"))
    r = build_receipt(packet, "test")
    assert r["mode"] == "demo"
    assert r["mode_label"] == DEMO_LABEL
    html = render_receipt_html(r)
    assert DEMO_LABEL in html, "rendered HTML must carry the DEMO MODE label"
    blob = json.dumps(r)
    assert "DEMO MODE" in blob


def test_fractions_sum_and_segments_present():
    slop = _load(os.path.join("samples", "slop_control.txt"))
    r = build_receipt(slop, "test")
    for p in r["passages"]:
        total = p["fraction_ai"] + p["fraction_ai_assisted"] + p["fraction_human"]
        assert abs(total - 1.0) < 0.01, f"passage fractions sum to {total}"
        assert p["segments"], "each passage must carry window segments"
        for seg in p["segments"]:
            assert 0.0 <= float(seg["ai_assistance_score"]) <= 1.0
            assert "is_humanized" in seg and "humanizer_score" in seg
        assert p["verdict"] in ("human-authored", "ai-assisted", "ai-generated", "mixed")


def test_summary_buckets_partition_passages():
    packet = _load(os.path.join("showcase_a", "one_apply_packet.txt"))
    r = build_receipt(packet, "test")
    s = r["summary"]
    human = set(s["human_authored_facts"]["passage_indices"])
    ai = set(s["ai_drafted_prose"]["passage_indices"])
    assert not (human & ai), "buckets must not overlap"
    assert human | ai <= {p["index"] for p in r["passages"]}
    assert 0.0 <= s["human_authored_facts"]["word_share"] <= 1.0
    assert 0.0 <= s["ai_drafted_prose"]["word_share"] <= 1.0


def test_slop_scores_worse_than_real_packet():
    _ensure_generated()
    packet = _load(os.path.join("showcase_a", "one_apply_packet.txt"))
    slop = _load(os.path.join("samples", "slop_control.txt"))
    rp = build_receipt(packet, "packet")
    rs = build_receipt(slop, "slop")
    assert rs["summary"]["overall_fraction_ai"] > rp["summary"]["overall_fraction_ai"], (
        f"slop ai={rs['summary']['overall_fraction_ai']} must exceed "
        f"packet ai={rp['summary']['overall_fraction_ai']}")
    assert rp["summary"]["overall_fraction_human"] > rs["summary"]["overall_fraction_human"]


def test_showcase_b_gate_blocked_with_receipt():
    _ensure_generated()
    with open(os.path.join(ROOT, "showcase_b", "gate_record.json"), encoding="utf-8") as fh:
        gate = json.load(fh)
    stages = {s["stage"]: s for s in gate["stages"]}
    gate_stage = next(s for s in gate["stages"] if "merge gate" in s["stage"])
    assert gate_stage["state"].startswith("BLOCKED")
    receipt_stage = next(s for s in gate["stages"] if "receipt" in s["stage"].lower())
    assert receipt_stage["state"] == "done"
    assert receipt_stage["receipt_mode_label"] == DEMO_LABEL


def test_export_rule_present():
    slop = _load(os.path.join("samples", "slop_control.txt"))
    r = build_receipt(slop, "test")
    assert "may not be exported without this receipt" in r["export_rule"]
    assert "may not be exported without this receipt" in render_receipt_html(r)


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed")
    sys.exit(1 if failed else 0)
