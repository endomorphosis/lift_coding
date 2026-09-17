#!/usr/bin/python3.12
"""Validate LA-011 mediation outputs against sealed-environment facts."""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
SNAP = Path(__file__).resolve().parent

PAPER_ROUTES = {
    "supervisor_pre_invocation_enforce",
    "supervisor_pre_invocation_off",
    "supervisor_pre_invocation_audit",
    "supervisor_pre_invocation_shadow",
    "execution_permit",
    "ucan_gated_mcp_authorization_gate",
    "profile_d_lightweight_dispatcher",
    "direct_bounded_export_handler",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    live_inventory = LIVE / "benchmark" / "route_inventory.json"
    live_raw = LIVE / "results" / "mediation" / "raw.jsonl"
    live_qual = LIVE / "results" / "mediation" / "qualification.md"
    live_patch = LIVE / "patches" / "mediation_changes.md"
    snap_inventory = SNAP / "outputs" / "benchmark" / "route_inventory.json"
    snap_raw = SNAP / "outputs" / "results" / "mediation" / "raw.jsonl"
    snap_qual = SNAP / "outputs" / "results" / "mediation" / "qualification.md"
    snap_patch = SNAP / "outputs" / "patches" / "mediation_changes.md"
    for path in (
        live_inventory,
        live_raw,
        live_qual,
        live_patch,
        snap_inventory,
        snap_raw,
        snap_qual,
        snap_patch,
    ):
        if not path.is_file():
            raise SystemExit(f"missing {path}")
    if live_inventory.read_bytes() != snap_inventory.read_bytes():
        raise SystemExit("route_inventory.json live/snapshot mismatch")
    if live_raw.read_bytes() != snap_raw.read_bytes():
        raise SystemExit("raw.jsonl live/snapshot mismatch")
    if live_qual.read_bytes() != snap_qual.read_bytes():
        raise SystemExit("qualification.md live/snapshot mismatch")
    if live_patch.read_bytes() != snap_patch.read_bytes():
        raise SystemExit("mediation_changes.md live/snapshot mismatch")

    inventory = load_json(live_inventory)
    jobs = load_jsonl(live_raw)
    text = live_qual.read_text(encoding="utf-8")
    patch = live_patch.read_text(encoding="utf-8")
    summary = load_json(SNAP / "probe" / "summary.json")
    env = load_json(SNAP / "probe" / "sealed-environment.json")
    widening = load_json(SNAP / "probe" / "tenant-widening.json")

    assert inventory["schema"] == "law-to-action-route-inventory/v1"
    assert inventory["task"] == "LA-011"
    assert inventory["empirical_benchmark_result"] is False
    assert inventory["authoritative_environment"]["python"] == "/usr/bin/python3.12"
    assert inventory["authoritative_environment"]["path"] == os.environ.get("PATH")
    assert inventory["authoritative_environment"]["HAVE_CRYPTO_ED25519"] is True
    assert inventory["selected_safety_claim"]["route_id"] == "supervisor_pre_invocation_enforce"
    assert inventory["selected_safety_claim"]["includes_unprotected_routes"] is False
    assert inventory["selected_safety_claim"]["includes_fixture_verifiers"] is False
    assert inventory["selected_safety_claim"]["mode"] == "enforce"

    route_ids = {row["id"] for row in inventory["routes"]}
    missing = PAPER_ROUTES - route_ids
    assert not missing, f"paper routes missing from inventory: {missing}"

    by_route: dict[str, list[dict]] = defaultdict(list)
    for job in jobs:
        by_route[job["route_id"]].append(job)
        assert job["empirical_benchmark_result"] is False

    required_kinds = {"allow", "deny", "unknown", "context_mutation"}
    for route_id in PAPER_ROUTES:
        kinds = {job["case_kind"] for job in by_route[route_id]}
        missing_kinds = required_kinds - kinds
        assert not missing_kinds, f"{route_id} missing kinds {missing_kinds}"
        assert by_route[route_id], f"no jobs for {route_id}"

    selected = [job for job in jobs if job["in_safety_claim"]]
    assert selected
    assert all(job["route_id"] == "supervisor_pre_invocation_enforce" for job in selected)
    assert all(job["passed"] for job in selected), [
        job["job_id"] for job in selected if not job["passed"]
    ]
    assert any(job["case_kind"] == "allow" and job["observed_effect_count"] == 1 for job in selected)
    assert all(
        job["observed_effect_count"] == 0
        for job in selected
        if job["case_kind"] in {"deny", "unknown", "context_mutation"}
        or job["expected_effect_count"] == 0
    )

    real = [job for job in jobs if job["crypto"] == "real-ed25519"]
    assert len(real) >= 8, len(real)
    assert all(job["verifier_kind"] == "real-ucan-verifier" for job in real)
    assert any(job["mutation"] == "wrong-audience" for job in real)
    assert any("tenant-a-versus-tenant-ab" in job["mutation"] for job in real)
    assert any(job["mutation"] == "expired-token" for job in real)
    assert any(job["mutation"] == "revoked-token" for job in real)
    assert any("forged" in job["mutation"] for job in real)
    assert any(job["mutation"] == "replay" for job in real)

    fixtures = [job for job in jobs if job["crypto"] == "fixture-verifier" or "fixture" in job["verifier_kind"]]
    assert fixtures
    assert all(job["in_safety_claim"] is False for job in fixtures)
    assert any("fixture" in job["job_id"] or job["crypto"] == "fixture-verifier" for job in jobs)

    unprotected = [
        job
        for job in jobs
        if job["route_id"]
        in {
            "supervisor_pre_invocation_off",
            "supervisor_pre_invocation_audit",
            "supervisor_pre_invocation_shadow",
            "direct_bounded_export_handler",
            "profile_d_lightweight_dispatcher",
        }
    ]
    assert unprotected
    assert all(job["in_safety_claim"] is False for job in unprotected)
    assert any(
        job["route_id"] == "direct_bounded_export_handler" and job["observed_effect_count"] == 1
        for job in jobs
    )
    assert any(
        job["route_id"] == "supervisor_pre_invocation_off" and job["observed_effect_count"] == 1
        for job in jobs
    )

    assert widening["tenant-a/* covers tenant-a/x"] is True
    assert widening["tenant-a/* covers tenant-ab"] is False
    assert widening["tenant-a/* covers tenant-ab/x"] is False

    assert env["HAVE_CRYPTO_ED25519"] is True
    assert env["canonical_profile_d_available"] is False
    assert env["multiformats"] is False
    assert "cryptography" in env["cryptography_version"] or env["cryptography_version"]

    assert "ENFORCE" in text or "enforce" in text
    assert "Ed25519" in text or "ed25519" in text.lower()
    assert "fixture" in text.lower()
    assert "not a scored" in text.lower() or "not** a scored" in text.lower() or "not a scored A3" in text
    assert "tenant-ab" in text or "tenant-a versus tenant-ab" in text
    assert "None applied" in patch or "not**" in patch or "were **not**" in patch
    assert "Boundary regressions" in patch or "boundary regression" in patch.lower()

    claim_route = next(row for row in inventory["routes"] if row["id"] == "supervisor_pre_invocation_enforce")
    assert claim_route["in_safety_claim"] is True
    for row in inventory["routes"]:
        if row["id"] != "supervisor_pre_invocation_enforce":
            assert row["in_safety_claim"] is False, row["id"]

    print("LA-011 mediation validation: PASS")
    print(
        f"jobs={len(jobs)} selected={len(selected)} real_ucan={len(real)} "
        f"fixtures={len(fixtures)} failed={summary.get('failed')}"
    )
    print("selected ENFORCE claim excludes unprotected routes; real Ed25519 executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
