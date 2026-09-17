#!/usr/bin/python3.12
"""Validate LA-017 paired ablation outputs against retained snapshot evidence."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
SNAP = Path(__file__).resolve().parent
SEED = 104729
MECHANISMS = (
    "source_provenance",
    "hard_applicability",
    "intent_code_correlation",
    "proof_jobs",
    "current_root_binding",
    "capability_verification",
    "consumption",
)
TERMINAL = {
    "success",
    "denial",
    "abstention",
    "execution_failure",
    "timeout",
    "infrastructure_invalid",
    "not_started",
}
REQUIRED_SUMMARY_PHRASES = (
    "masked",
    "not manufactured into benefit",
    "Interacting checks",
    "not enabled in live services",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    live = LIVE / "results" / "ablations"
    snap_out = SNAP / "outputs" / "results" / "ablations"
    spec = load_json(LIVE / "benchmark" / "ablations.json")
    snap_spec = SNAP / "outputs" / "benchmark" / "ablations.json"
    require(spec["schema"] == "law-to-action-ablations/v1", "ablations.json schema mismatch")
    require(spec["task"] == "LA-017", "ablations.json task mismatch")
    require([row["id"] for row in spec["mechanisms"]] == list(MECHANISMS), "seven mechanisms missing or reordered")
    require(spec["live_service_policy"].find("never") >= 0, "live-service prohibition missing")
    require(snap_spec.is_file(), "snapshot copy of ablations.json missing")
    require(LIVE.joinpath("benchmark/ablations.json").read_bytes() == snap_spec.read_bytes(), "live/snapshot ablations.json mismatch")

    for name in ("raw.jsonl", "summary.json"):
        live_path = live / name
        snap_path = snap_out / name
        require(live_path.is_file(), f"missing live output {live_path}")
        require(snap_path.is_file(), f"missing snapshot output {snap_path}")
        require(live_path.read_bytes() == snap_path.read_bytes(), f"live/snapshot mismatch: {name}")

    records = load_jsonl(live / "raw.jsonl")
    summary = load_json(live / "summary.json")
    require(len(records) == 28, f"raw.jsonl must contain 28 paired cells, found {len(records)}")
    require(summary["task"] == "LA-017", "summary task mismatch")
    require(summary["schema"] == "law-to-action-ablation-summary/v1", "summary schema mismatch")
    require(summary["scheduled"] == 28, "summary scheduled is not 28")
    require(summary["ablated_configurations_enabled_in_live_services"] is False, "ablated configs marked live")
    require(summary["absence_of_change_manufactured_into_benefit"] is False, "no-change was manufactured into benefit")
    require(summary["safety_uses_effect_counters_not_decision_labels_alone"] is True, "safety must use effect counters")
    require(summary["independent_human_gold"] is False, "human gold was claimed")
    require(summary["sandbox_only"] is True, "sandbox_only missing")
    require(summary["mechanisms_with_scoped_omission"] == [], "unexpected scoped omission")
    require(summary["mechanisms_with_paired_experiment"] == list(MECHANISMS), "paired experiment list drifted")
    require(len(summary["implementation_revision"]) == 64, "implementation revision is not sha256")
    narrative = summary.get("attribution_narrative") or ""
    for phrase in REQUIRED_SUMMARY_PHRASES:
        require(phrase in narrative, f"summary narrative missing phrase: {phrase}")

    expected_ids = {
        f"{SEED}:{mechanism}:{config_id}:{polarity}"
        for mechanism in MECHANISMS
        for config_id in ("full", "ablated")
        for polarity in ("positive", "negative")
    }
    got_ids = {row["attempt_id"] for row in records}
    require(got_ids == expected_ids, f"raw log does not cover the paired matrix: {sorted(expected_ids - got_ids)[:8]}")
    require(len(got_ids) == 28, "attempt IDs are not unique")

    by_mechanism = {row["id"]: row for row in spec["mechanisms"]}
    identities = {}
    for row in records:
        require(row["mechanism_id"] in MECHANISMS, f"unknown mechanism {row['mechanism_id']}")
        require(row["config_id"] in {"full", "ablated"}, f"invalid config {row['config_id']}")
        require(row["polarity"] in {"positive", "negative"}, f"invalid polarity {row['polarity']}")
        require(row["terminal_outcome"] in TERMINAL, f"invalid terminal {row['terminal_outcome']}")
        require(row["oracle_label"] in {"allowed", "forbidden"}, "oracle_label must be allowed or forbidden")
        require(row["sandbox"] is True, "executed cell lost sandbox flag")
        require(row["deployment_scope"] == "sandbox_experiment_only", "deployment scope drifted")
        require(row["independent_human_gold"] is False, "row claimed human gold")
        require(type(row["observed_effect_count"]) is int, "effect count is not an integer")
        require("configuration_difference" in row, "configuration difference missing")
        require(row["configuration_difference"]["one_factor"] is (row["config_id"] == "ablated"), "one-factor flag incorrect")
        require("would_deny" in row and "applied_deny" in row, "guard attribution fields missing")
        require(row["implementation_revision"] == summary["implementation_revision"], "per-row revision drifted")
        if row["config_id"] == "ablated":
            require(row["live_service"] is False, "ablated configuration marked live")
            require(row["enabled_mechanisms"][row["mechanism_id"]] is False, "ablated mechanism still enabled")
            require(row["configuration_difference"]["changed_mechanisms"] == [row["mechanism_id"]], "ablation was not one-factor")
        else:
            require(all(row["enabled_mechanisms"][key] is True for key in MECHANISMS), "full config missing a mechanism")
        if row["polarity"] == "positive":
            require(row["oracle_label"] == "allowed", "positive control is not allowed")
        else:
            require(row["oracle_label"] == "forbidden", "negative control is not forbidden")
        if row["terminal_outcome"] == "denial":
            require(row["observed_effect_count"] == 0, "denial recoded over a positive effect counter")
        spec_row = by_mechanism[row["mechanism_id"]]
        expected_case = spec_row["positive_case_id"] if row["polarity"] == "positive" else spec_row["negative_case_id"]
        require(row["case_id"] == expected_case, f"{row['attempt_id']} used unplanned case {row['case_id']}")
        identities.setdefault((row["mechanism_id"], row["polarity"]), set()).add(row["identity_digest"])

    require(all(len(values) == 1 for values in identities.values()), "candidate identity changed across full/ablated")

    for mechanism_id, block in summary["by_mechanism"].items():
        require(mechanism_id in MECHANISMS, f"summary has unknown mechanism {mechanism_id}")
        require(block["status"] == "paired_experiment", f"{mechanism_id} is not a paired experiment")
        require(block["scoped_omission"] is False, f"{mechanism_id} was omitted")
        require(block["live_service_enabled"] is False, f"{mechanism_id} ablation marked live")
        require("configuration_difference" in block, f"{mechanism_id} lost configuration difference")
        require("attribution" in block, f"{mechanism_id} lost attribution")
        attr = block["attribution"]
        require(attr["absence_of_change_manufactured_into_benefit"] is False, f"{mechanism_id} manufactured benefit")
        require(attr["kind"] != "benefit", f"{mechanism_id} labeled a no-change as benefit")
        if attr["forbidden_effect_delta"] == 0:
            require("not" in attr["text"] and "benefit" in attr["text"], f"{mechanism_id} no-change text missing caution")
            if attr["remaining_guards"]:
                require(attr["kind"] == "masked_by_interacting_checks", f"{mechanism_id} remaining guards not called interacting")
        full_neg = next(
            row
            for row in records
            if row["mechanism_id"] == mechanism_id and row["config_id"] == "full" and row["polarity"] == "negative"
        )
        ablated_neg = next(
            row
            for row in records
            if row["mechanism_id"] == mechanism_id and row["config_id"] == "ablated" and row["polarity"] == "negative"
        )
        require(attr["full_forbidden_effect"] == bool(full_neg["observed_forbidden_effect"]), f"{mechanism_id} full fx mismatch")
        require(attr["ablated_forbidden_effect"] == bool(ablated_neg["observed_forbidden_effect"]), f"{mechanism_id} ablated fx mismatch")
        require(
            block["full_negative"]["observed_effect_count"] == full_neg["observed_effect_count"],
            f"{mechanism_id} full effect counter mismatch",
        )
        require(
            block["ablated_negative"]["observed_effect_count"] == ablated_neg["observed_effect_count"],
            f"{mechanism_id} ablated effect counter mismatch",
        )

    require(summary["counts"]["effect_sum"] == sum(row["observed_effect_count"] for row in records), "effect_sum mismatch")
    require(
        summary["counts"]["observed_forbidden_effects"] == sum(1 for row in records if row["observed_forbidden_effect"]),
        "forbidden-effect count mismatch",
    )
    require(
        summary["counts"]["false_rejections"] == sum(1 for row in records if row["false_rejection"]),
        "false-rejection count mismatch",
    )
    for name, payload in summary["metrics"].items():
        require(set(payload) >= {"numerator", "denominator", "value", "undefined"}, f"{name} lacks rate fields")
        if payload["denominator"] == 0:
            require(payload["undefined"] is True, f"{name} n=0 was not marked undefined")
            require(payload["value"] is None, f"{name} n=0 was given a numeric value")
        else:
            require(payload["undefined"] is False, f"{name} marked undefined with a denominator")
            expected = payload["numerator"] / payload["denominator"]
            require(abs(payload["value"] - expected) < 1e-12, f"{name} value does not match numerator/denominator")

    print(
        json.dumps(
            {
                "ok": True,
                "records": len(records),
                "mechanisms": list(MECHANISMS),
                "implementation_revision": summary["implementation_revision"],
                "effect_sum": summary["counts"]["effect_sum"],
                "observed_forbidden_effects": summary["counts"]["observed_forbidden_effects"],
                "false_rejections": summary["counts"]["false_rejections"],
                "attribution_kinds": sorted({row["kind"] for row in summary["attributions"]}),
                "load_bearing": [
                    row["mechanism_id"] for row in summary["attributions"] if row["kind"] == "load_bearing"
                ],
                "masked": [
                    row["mechanism_id"] for row in summary["attributions"] if "masked" in row["kind"]
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
