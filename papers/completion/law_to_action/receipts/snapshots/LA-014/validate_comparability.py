#!/usr/bin/python3.12
"""Validate LA-014 matched-arm outputs against retained snapshot evidence."""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
SNAP = Path(__file__).resolve().parent

POLICY_KEYS = (
    "unguarded_sandbox_dispatch",
    "inert_policy_text",
    "inert_retrieval_context",
    "lightweight_declared_policy",
    "real_ucan_verifier",
    "supervisor_enforce",
    "checked_sat_obligations",
    "durable_consumption",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    live_arms = LIVE / "benchmark" / "arms.json"
    live_baselines = LIVE / "benchmark" / "baselines.py"
    live_report = LIVE / "benchmark" / "comparability_report.md"
    snap_arms = SNAP / "outputs" / "benchmark" / "arms.json"
    snap_baselines = SNAP / "outputs" / "benchmark" / "baselines.py"
    snap_report = SNAP / "outputs" / "benchmark" / "comparability_report.md"
    records_path = SNAP / "traces" / "records.json"
    for path in (live_arms, live_baselines, live_report, snap_arms, snap_baselines, snap_report, records_path):
        if not path.is_file():
            raise SystemExit(f"missing {path}")
    if live_arms.read_bytes() != snap_arms.read_bytes():
        raise SystemExit("arms.json live/snapshot mismatch")
    if live_baselines.read_bytes() != snap_baselines.read_bytes():
        raise SystemExit("baselines.py live/snapshot mismatch")
    if live_report.read_bytes() != snap_report.read_bytes():
        raise SystemExit("comparability_report.md live/snapshot mismatch")

    arms = load_json(live_arms)
    payload = load_json(records_path)
    report = live_report.read_text(encoding="utf-8")
    env = payload["environment"]
    comparison = payload["comparison"]

    assert arms["schema"] == "law-to-action-matched-arms/v1"
    assert arms["task"] == "LA-014"
    assert arms["empirical_benchmark_result"] is False
    assert arms["admitted_split"] == "development"
    assert arms["held_out_tuning"] is False
    assert tuple(arms["policy_component_keys"]) == POLICY_KEYS
    assert [arm["id"] for arm in arms["arms"]] == ["A0", "A1", "A2", "A3", "A4"]
    for arm in arms["arms"]:
        extra = set(arm) - {
            "id",
            "name",
            "conventional_arm_label",
            "contrast_role",
            "interpretation",
            "required_qualifications",
            "when_unavailable",
            "policy_components",
        }
        assert not extra, extra
        assert tuple(arm["policy_components"]) == POLICY_KEYS
    a0, a1, a2, a3, a4 = (arm["policy_components"] for arm in arms["arms"])
    assert a0["unguarded_sandbox_dispatch"] and not a0["inert_policy_text"] and not a0["inert_retrieval_context"]
    assert a1["unguarded_sandbox_dispatch"] and a1["inert_policy_text"] and not a1["inert_retrieval_context"]
    assert a2["unguarded_sandbox_dispatch"] and a2["inert_policy_text"] and a2["inert_retrieval_context"]
    assert a3["lightweight_declared_policy"] and a3["real_ucan_verifier"] and not a3["unguarded_sandbox_dispatch"]
    assert a3["supervisor_enforce"] is False and a3["durable_consumption"] is False
    assert a4["supervisor_enforce"] and a4["checked_sat_obligations"] and a4["durable_consumption"]
    assert a4["real_ucan_verifier"] and a4["lightweight_declared_policy"]
    assert a1 != a2
    assert env["path"] == os.environ.get("PATH")
    assert env["python_executable"] == "/usr/bin/python3.12" or Path(sys.executable).name.startswith("python3")
    assert env["HAVE_CRYPTO_ED25519"] is True
    assert payload["empirical_benchmark_result"] is False
    assert payload["task"] == "LA-014"
    assert comparison["identical_candidate_identity"] is True
    assert comparison["a0_a1_a2_operational_equivalence"] is True
    assert comparison["prompt_only_distinct_from_retrieval_prompt"] is True
    assert comparison["unguarded_remains_sandboxed"] is True
    assert comparison["a3_a4_differ_from_unguarded_on_forbidden"] is True
    assert comparison["held_out_used"] is False
    assert comparison["no_failures"] is True
    assert payload["replay"]["identity_stable"] is True
    records = payload["records"]
    assert len(records) == 60
    by_arm: dict[str, list] = defaultdict(list)
    identities: dict[str, set[str]] = defaultdict(set)
    for row in records:
        assert row["split"] == "development"
        assert row["empirical_benchmark_result"] is False
        assert row["sandbox"] is True
        by_arm[row["arm_id"]].append(row)
        identities[row["candidate_id"]].add(json.dumps(row["identity"], sort_keys=True))
    assert set(by_arm) == {"A0", "A1", "A2", "A3", "A4"}
    assert all(len(group) == 12 for group in by_arm.values())
    assert all(len(values) == 1 for values in identities.values())
    for arm_id in ("A0", "A1", "A2"):
        assert all(row["decision"] == "allow" and row["observed_effect_count"] == 1 for row in by_arm[arm_id])
        assert all(row["mechanism"].get("arbitrary_generated_source_execution") is False for row in by_arm[arm_id])
    assert all(row["mechanism"].get("crypto") == "real-ed25519" for row in by_arm["A3"])
    assert all(row["mechanism"].get("verifier_kind") == "real-ucan-verifier" for row in by_arm["A3"])
    allowed_a3 = [row for row in by_arm["A3"] if row["candidate_id"].endswith(":case-0")]
    forbidden_a3 = [row for row in by_arm["A3"] if row["candidate_id"].endswith(":case-1")]
    assert len(allowed_a3) == 6 and all(row["decision"] == "allow" and row["observed_effect_count"] == 1 for row in allowed_a3)
    assert len(forbidden_a3) == 6 and all(row["decision"] == "deny" and row["observed_effect_count"] == 0 for row in forbidden_a3)
    assert all(row["mechanism"].get("enforce_mode") == "enforce" for row in by_arm["A4"])
    assert all(row["mechanism"].get("in_memory_store") is False for row in by_arm["A4"])
    assert all(row["mechanism"].get("store_kind") == "duckdb-file-typed-quack-owner" for row in by_arm["A4"])
    assert all(row["mechanism"].get("obligation", {}).get("authority_kind") == "satisfiability" for row in by_arm["A4"])
    allowed_a4 = [row for row in by_arm["A4"] if row["candidate_id"].endswith(":case-0")]
    forbidden_a4 = [row for row in by_arm["A4"] if row["candidate_id"].endswith(":case-1")]
    assert all(row["decision"] == "allow" and row["observed_effect_count"] == 1 for row in allowed_a4)
    assert all(row["decision"] == "deny" and row["observed_effect_count"] == 0 for row in forbidden_a4)
    a1_meta = by_arm["A1"][0]["metadata"]
    a2_meta = by_arm["A2"][0]["metadata"]
    assert "policy_text" in a1_meta and "retrieval" not in a1_meta
    assert "policy_text" in a2_meta and "retrieval" in a2_meta
    assert a2_meta["retrieval"]["includes_final_sibling"] is False
    assert a2_meta["retrieval"]["includes_acceptance_oracle"] is False
    assert a2_meta["retrieval"]["split"] == "development"
    assert "prompt-only" in report and "retrieval+prompt" in report
    assert "sandboxed" in report.lower()
    assert "differ only by" in report.lower() or "differ only by `policy_components`" in report
    assert "held-out" in report.lower() or "held-out" in report
    print(json.dumps({
        "ok": True,
        "attempts": len(records),
        "shared_fingerprint": comparison["shared_fingerprint"],
        "empirical_benchmark_result": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"validate_comparability: assertion failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
