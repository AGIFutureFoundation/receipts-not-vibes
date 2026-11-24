#!/usr/bin/env python3
"""
generate_showcase_a.py — SHOWCASE A (One-Apply).

Generates a real One-Apply application packet from the live dataset
(~/workspace/fundraising/one-apply-fix/one-apply-data-v3.json) for the
AGI Future Foundation profile, using the same packet layout as the
one-apply page's packetText() function, plus the applicant's project
narrative passage. Then runs the receipt engine over the packet and over
the slop-control sample, writing JSON + HTML receipts to showcase_a/.

The packet's facts are the Foundation's verified facts (CA Secretary of
State record B20260196664; credits ledger as published on the One-Apply
page). The narrative passage is labelled in the packet itself as drafted
prose — which is exactly what the receipt then measures and discloses.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from receipt import build_receipt, render_receipt_html  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.expanduser("~/workspace/fundraising/one-apply-fix/one-apply-data-v3.json")
PROGRAMME_ID = "transformative-ai-fund-ea-funds"  # Transformative AI Fund — submitted by the Foundation 2026-11-23

PROFILE = {
    "org_name": "AGI Future Foundation",
    "entity_type": "California nonprofit public benefit corporation (SOS entity B20260196664, filed 04/24/2026; federal 501(c)(3) determination pending — not claimed)",
    "stage": "Early — programmes live, first grants in review",
    "country": "United States",
    "website": "https://www.agifuturefoundation.org",
    "sector": ("Consent-first alignment research (Ask Humanity: twenty questions, consent provenance by "
               "design), agent infrastructure (SparkHub: NANDA-protocol registry with human merge gates), "
               "and Founders One-Apply, a matcher over 528 funding programmes from 483 providers."),
}

LANE_LABELS = {"email": "EMAIL-ROUTE", "portal": "FOUNDER-PORTAL", "input": "NEEDS-INPUT"}

NARRATIVE = (
    "PROJECT NARRATIVE (drafted prose — disclosed as such on the attached receipt): "
    "Advanced AI systems will be built by whoever shows up early with working infrastructure. "
    "We are building the consent layer first: Ask Humanity collects answers to twenty alignment "
    "questions only with explicit, revocable consent, and every answer stays the property of the "
    "person who gave it. SparkHub lets agents register, publish packages, and hand work to each "
    "other, but nothing merges without a human decision. One-Apply exists because small teams "
    "waste their scarcest resource — time — on applications they were never eligible for; its "
    "matcher checks structured eligibility gates before it recommends anything. The Transformative "
    "AI Fund grant would fund the secure Ask Humanity database, the receipt tooling you are "
    "reading now, and a public dataset release with consent provenance intact."
)


def packet_text(profile, rec):
    """Same layout as packetText() in one-apply-v3.html."""
    pb = rec.get("playbook") or {}
    fields = "; ".join(pb.get("required_fields") or []) or "Packet fields not in dataset — apply on the provider's site."
    lines = [
        "PROGRAMME: " + rec["programme"] + " (" + rec["provider"] + ")",
        "OFFER: " + (rec.get("offer") or ""),
        "APPLY AT: " + (rec.get("terms_url") or rec.get("url") or ""),
        "APPLICANT: " + profile["org_name"],
        "ENTITY: " + profile["entity_type"] + " · STAGE: " + profile["stage"] + " · COUNTRY: " + profile["country"],
        "WEBSITE: " + profile["website"],
        "WHAT WE ARE BUILDING: " + profile["sector"],
        "PROVIDER ASKS FOR: " + fields,
        "REVIEW CLOCK: " + (rec.get("review_clock") or "No review timeframe published."),
        "SEND LANE: " + LANE_LABELS.get(rec.get("apply_lane") or "portal", "FOUNDER-PORTAL"),
    ]
    if rec.get("apply_lane") == "portal":
        lines.append("PORTAL: " + (rec.get("terms_url") or rec.get("url") or "(no public URL published)"))
        lines.append("ACCOUNT NEEDED: " + (rec.get("lane_account") or "Your own account with the provider"))
    lines.append("YOUR STEP: " + (rec.get("founder_step") or ""))
    lines.append("")
    lines.append("ESTATE FACTS (verified, human-supplied): $77,425.98 in non-cash programme support "
                 "secured to date (PostHog $50,000, Algolia $10,000, Sentry $5,000, Cartesia approx. "
                 "$7,200, Murf $1,510, Exa $1,000, others itemised on the One-Apply page); 93 applications "
                 "submitted through the pipeline; $0 cash raised. Principal address: 995 Market St, "
                 "San Francisco, CA 94103. President/CEO: Mike Rice (full-time). Co-founder and lead "
                 "developer: Russel Vacanti.")
    lines.append("")
    lines.append(NARRATIVE)
    return "\n".join(lines)


def main():
    with open(DATASET, encoding="utf-8") as fh:
        data = json.load(fh)
    rec = next(p for p in data["programmes"] if p["id"] == PROGRAMME_ID)

    outdir = os.path.join(HERE, "showcase_a")
    os.makedirs(outdir, exist_ok=True)

    packet = packet_text(PROFILE, rec)
    packet_path = os.path.join(outdir, "one_apply_packet.txt")
    with open(packet_path, "w", encoding="utf-8") as fh:
        fh.write(packet + "\n")

    receipt = build_receipt(packet, f"One-Apply packet — {rec['programme']} ({rec['provider']})",
                            source="Generated from one-apply-data-v3.json, programme id " + PROGRAMME_ID)
    with open(os.path.join(outdir, "one_apply_packet.receipt.json"), "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(outdir, "one_apply_packet.receipt.html"), "w", encoding="utf-8") as fh:
        fh.write(render_receipt_html(receipt))

    with open(os.path.join(HERE, "samples", "slop_control.txt"), encoding="utf-8") as fh:
        slop = fh.read()
    slop_receipt = build_receipt(slop, "Slop control — a generic AI grant blurb (written for this demo)",
                                 source="samples/slop_control.txt")
    with open(os.path.join(outdir, "slop_control.receipt.json"), "w", encoding="utf-8") as fh:
        json.dump(slop_receipt, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(outdir, "slop_control.receipt.html"), "w", encoding="utf-8") as fh:
        fh.write(render_receipt_html(slop_receipt))

    for name, r in (("packet", receipt), ("slop control", slop_receipt)):
        s = r["summary"]
        print(f"{name}: mode={r['mode']} ai={s['overall_fraction_ai']} "
              f"assisted={s['overall_fraction_ai_assisted']} human={s['overall_fraction_human']} "
              f"passages={s['passage_count']}")
    print("wrote showcase_a/: one_apply_packet.txt + receipts (JSON + HTML) for packet and slop control")
    return 0


if __name__ == "__main__":
    sys.exit(main())
