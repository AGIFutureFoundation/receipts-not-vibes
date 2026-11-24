#!/usr/bin/env python3
"""
generate_showcase_b.py — SHOWCASE B (SparkHub merge gate).

Simulates one pass through SparkHub's publishing pipeline: an agent submits
a package; the pipeline runs the provenance engine over the package
description; the package stops at the HUMAN MERGE GATE with its receipt
attached. No merge can happen inside this demo — the gate record's state is
"BLOCKED — awaiting human decision", which is the product working as
designed. (The live demo page lets a human flip the decision in-page so
judges can see both outcomes; the recorded pipeline state stays blocked
until a human acts.)

Writes showcase_b/gate_record.json, the submission text, and its receipt
(JSON + HTML, rendered by the same receipt.py renderer as Showcase A).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from receipt import build_receipt, render_receipt_html  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

SUBMISSION = {
    "package_name": "one-apply-gate-reasons",
    "version": "0.2.0",
    "submitted_by_agent": "capy-thread-7 (Capy crew, SparkHub-registered agent)",
    "submitted_at": "2026-11-24T18:12:00Z",
    "change_summary": "Adds plain-language gate-reason strings for 12 programme records in the One-Apply dataset.",
    "description": (
        "This package supercharges the One-Apply experience with dynamic, human-readable explanations "
        "for every eligibility decision. When a programme is held back, founders no longer see a bare "
        "\"held\" label: they see the exact gate that fired and what would change the verdict.\n\n"
        "In this release, twelve programme records gain hand-checked reason strings, including the "
        "determination-letter gate, the referral gate, and the formation gate. Each string was written "
        "against the provider's own published criteria, and each names the missing input rather than "
        "guessing at it. Tests: 14 assertions over the shared gate function, all passing locally.\n\n"
        "Leveraging our seamless pipeline, this cutting-edge enhancement empowers founders to unlock "
        "clarity and elevate their application journey to the next level."
    ),
}


def main():
    outdir = os.path.join(HERE, "showcase_b")
    os.makedirs(outdir, exist_ok=True)

    sub_path = os.path.join(outdir, "agent_submission.txt")
    with open(sub_path, "w", encoding="utf-8") as fh:
        fh.write(SUBMISSION["description"] + "\n")

    receipt = build_receipt(
        SUBMISSION["description"],
        f"SparkHub package description — {SUBMISSION['package_name']} v{SUBMISSION['version']}",
        source=f"Agent submission by {SUBMISSION['submitted_by_agent']}")
    with open(os.path.join(outdir, "agent_submission.receipt.json"), "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(outdir, "agent_submission.receipt.html"), "w", encoding="utf-8") as fh:
        fh.write(render_receipt_html(receipt))

    gate = {
        "pipeline": "SparkHub publishing pipeline (demo simulation of the live gate at sparkhub.agi.lease)",
        "package": SUBMISSION["package_name"],
        "version": SUBMISSION["version"],
        "submitted_by_agent": SUBMISSION["submitted_by_agent"],
        "submitted_at": SUBMISSION["submitted_at"],
        "change_summary": SUBMISSION["change_summary"],
        "stages": [
            {"stage": "1 · Agent submits package", "state": "done"},
            {"stage": "2 · Provenance receipt generated and attached", "state": "done",
             "receipt_mode": receipt["mode"], "receipt_mode_label": receipt["mode_label"],
             "overall_fraction_ai": receipt["summary"]["overall_fraction_ai"],
             "overall_fraction_ai_assisted": receipt["summary"]["overall_fraction_ai_assisted"],
             "overall_fraction_human": receipt["summary"]["overall_fraction_human"]},
            {"stage": "3 · Human merge gate", "state": "BLOCKED — awaiting human decision",
             "note": "No agent can merge its own work. A named human reviews the diff and this "
                     "receipt, then approves or rejects with a reason. This record stays blocked "
                     "until that happens — in the live demo, the human decides on the demo page."},
            {"stage": "4 · Publish to SparkHub registry", "state": "not reached"},
        ],
        "export_rule": receipt["export_rule"],
    }
    with open(os.path.join(outdir, "gate_record.json"), "w", encoding="utf-8") as fh:
        json.dump(gate, fh, indent=2, ensure_ascii=False)

    s = receipt["summary"]
    print(f"showcase B receipt: mode={receipt['mode']} ai={s['overall_fraction_ai']} "
          f"assisted={s['overall_fraction_ai_assisted']} human={s['overall_fraction_human']}")
    print("gate state: BLOCKED — awaiting human decision (by design)")
    print("wrote showcase_b/: agent_submission.txt, receipts (JSON + HTML), gate_record.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
