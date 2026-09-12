#!/usr/bin/env python3
"""Provenance-preserving evaluation and result accounting for AF-007.

The harness records parse/elaboration, independent source-facet fidelity,
ambiguity, source maps, forward/cycle/final reconstruction, consistency,
proof/false-transfer, costs, identities, and every execution status.  It
accepts normalized paper roundtrip fields without importing project packages
or invoking models, compilers, or native checkers. Conversion from the named
native benchmark report formats remains unqualified.

Every eligible source remains in coverage denominators.  Invalid, no-run, and
fixture records cannot occupy measured table rows.  Tables regenerate
deterministically from raw records or compact population recipes, with
artifact hashes and denominator checks.  Unrun and unavailable arms are not
zero-score successes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "autoformalization-evaluation-result/v1"
RECIPE_SCHEMA = "autoformalization-population-recipe/v1"
TABLE_SCHEMA = "autoformalization-evaluation-tables/v1"
METRICS_SCHEMA = "autoformalization-metrics/v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

RESULT_KINDS = (
    "native_checked_proof",
    "solver_local_result",
    "countermodel",
    "bounded_observation",
    "failure",
    "no_run",
)
EXECUTION_STATUSES = (
    "measured",
    "partial",
    "unavailable",
    "unsupported",
    "abstained",
    "timeout",
    "invalid",
    "failure",
    "no_run",
)
COVERAGE_STATUSES = EXECUTION_STATUSES
ATTEMPTED_STATUSES = frozenset({
    "measured", "partial", "unsupported", "abstained", "timeout", "invalid", "failure",
})
UNATTEMPTED_STATUSES = frozenset({"no_run", "unavailable"})
SPLITS = ("train", "selection", "fixed_canary", "final_test", "constructed_control")
CHECKER_CLASSES = ("native", "solver_local", "none")
PHASE_STATUSES = (
    "success", "failure", "unmeasured", "unavailable", "unsupported",
    "abstained", "timeout", "invalid", "no_run",
)
KIND_STATUS = {
    "native_checked_proof": frozenset({"measured", "partial"}),
    "solver_local_result": frozenset({"measured", "partial"}),
    "countermodel": frozenset({"measured", "partial"}),
    "bounded_observation": frozenset({"measured", "partial"}),
    "failure": frozenset({
        "failure", "timeout", "unsupported", "abstained", "invalid", "partial",
    }),
    "no_run": frozenset({"no_run", "unavailable"}),
}
KIND_CHECKER = {
    "native_checked_proof": "native",
    "solver_local_result": "solver_local",
}
RECORD_KEYS = (
    "schema", "record_id", "source_id", "source_family_time_group", "split",
    "experiment_arm", "eligible", "fixture", "constructed_control",
    "execution_status", "result_kind", "parse", "elaboration", "source_facets",
    "source_maps", "reconstruction", "consistency", "proof", "identities",
    "cost", "artifacts",
)
OPTIONAL_RECORD_KEYS = ("notes",)
HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = PAPER_ROOT.parents[2]


class AccountingError(ValueError):
    """Raised when a record, recipe, or table contract is violated."""


def canonical_dumps(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except ValueError as exc:
        raise AccountingError("canonical JSON requires finite numeric values") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_path() -> Path:
    return HERE / "result_schema.json"


def metrics_path() -> Path:
    return PAPER_ROOT / "config" / "metrics.json"


def load_schema_contract(path: Path | None = None) -> dict[str, Any]:
    data = load_json(path or schema_path())
    kinds = tuple(data.get("result_kinds") or ())
    statuses = tuple(data.get("execution_statuses") or ())
    if kinds != RESULT_KINDS:
        raise AccountingError("result_schema.json result_kinds drifted from the harness")
    if statuses != EXECUTION_STATUSES:
        raise AccountingError("result_schema.json execution_statuses drifted from the harness")
    blocked = set(data.get("blocked_from_measured_table_rows") or ())
    if blocked != {"invalid", "no_run", "fixture"}:
        raise AccountingError("result_schema.json admission blocklist drifted")
    return data


def load_metrics_contract(path: Path | None = None) -> dict[str, Any]:
    data = load_json(path or metrics_path())
    if data.get("schema") != METRICS_SCHEMA:
        raise AccountingError("metrics.json has an unexpected schema")
    if tuple(data.get("result_kinds") or ()) != RESULT_KINDS:
        raise AccountingError("metrics.json result_kinds drifted from the harness")
    ids = [item["id"] for item in data.get("metrics") or [] if isinstance(item, dict)]
    if len(ids) != len(set(ids)) or not ids:
        raise AccountingError("metrics.json must declare unique metric identifiers")
    return data


def _expect(cond: bool, message: str) -> None:
    if not cond:
        raise AccountingError(message)


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _phase(value: Any, label: str) -> None:
    _expect(isinstance(value, dict), f"{label} must be an object")
    status = value.get("status")
    _expect(status in PHASE_STATUSES, f"{label}.status is not a permitted phase status")
    if "score" in value:
        score = value["score"]
        _expect(score is None or isinstance(score, (int, float)) and not isinstance(score, bool)
                and math.isfinite(score), f"{label}.score must be finite or null")


def empty_phase(status: str = "no_run") -> dict[str, Any]:
    return {"status": status, "score": None}


def artifact_digest_for_record(payload: Mapping[str, Any]) -> str:
    body = {key: payload[key] for key in payload if key != "artifacts"}
    return sha256_obj(body)


def make_record(
    *,
    source_id: str,
    experiment_arm: str,
    execution_status: str,
    result_kind: str,
    split: str = "final_test",
    source_family_time_group: str = "G0",
    eligible: bool = True,
    fixture: bool = False,
    constructed_control: bool = False,
    parse: dict[str, Any] | None = None,
    elaboration: dict[str, Any] | None = None,
    independent_gold_present: bool = False,
    all_facet_match: bool | None = None,
    ambiguity_status: str = "no_run",
    source_maps: dict[str, Any] | None = None,
    forward: dict[str, Any] | None = None,
    cycle: dict[str, Any] | None = None,
    final: dict[str, Any] | None = None,
    consistency: dict[str, Any] | None = None,
    useful: bool = False,
    false_transfer: bool = False,
    checker_class: str = "none",
    receipt_sha256: str | None = None,
    model: str | None = None,
    tool: str | None = None,
    checker: str | None = None,
    compiler: str | None = None,
    elapsed_seconds: float | None = None,
    cpu_seconds: float | None = None,
    notes: str | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "record_id": record_id or f"{experiment_arm}:{source_id}",
        "source_id": source_id,
        "source_family_time_group": source_family_time_group,
        "split": split,
        "experiment_arm": experiment_arm,
        "eligible": eligible,
        "fixture": fixture,
        "constructed_control": constructed_control,
        "execution_status": execution_status,
        "result_kind": result_kind,
        "parse": parse or empty_phase(),
        "elaboration": elaboration or empty_phase(),
        "source_facets": {
            "independent_gold_present": independent_gold_present,
            "all_facet_match": all_facet_match,
            "ambiguity": {"status": ambiguity_status, "labels": []},
            "status": "success" if all_facet_match is True else (
                "unmeasured" if execution_status in ATTEMPTED_STATUSES else "no_run"
            ),
        },
        "source_maps": source_maps or empty_phase(),
        "reconstruction": {
            "forward": forward or empty_phase(),
            "cycle": cycle or empty_phase(),
            "final": final or empty_phase(),
        },
        "consistency": consistency or empty_phase(),
        "proof": {
            "useful": useful,
            "false_transfer": false_transfer,
            "checker_class": checker_class,
            "receipt_sha256": receipt_sha256,
            "theorem": None,
            "fragment": None,
        },
        "identities": {
            "experiment_arm": experiment_arm,
            "model": model,
            "tool": tool,
            "checker": checker,
            "compiler": compiler,
        },
        "cost": {
            "elapsed_seconds": elapsed_seconds,
            "cpu_seconds": cpu_seconds,
            "gpu_seconds": None,
            "provider_units": None,
            "memory_gib": None,
            "human_review_seconds": None,
        },
    }
    if notes is not None:
        record["notes"] = notes
    record["artifacts"] = {"raw_sha256": artifact_digest_for_record(record), "command_log_sha256": None}
    return record


def validate_record(record: Mapping[str, Any]) -> None:
    _expect(isinstance(record, Mapping), "record must be an object")
    extra = set(record) - set(RECORD_KEYS) - set(OPTIONAL_RECORD_KEYS)
    missing = set(RECORD_KEYS) - set(record)
    _expect(not extra, f"record has unexpected keys: {sorted(extra)}")
    _expect(not missing, f"record is missing keys: {sorted(missing)}")
    _expect(record.get("schema") == SCHEMA, "record schema mismatch")
    for key in ("record_id", "source_id", "source_family_time_group", "experiment_arm"):
        _expect(isinstance(record[key], str) and record[key], f"{key} must be a nonempty string")
    _expect(record["split"] in SPLITS, "split is not permitted")
    for flag in ("eligible", "fixture", "constructed_control"):
        _expect(type(record[flag]) is bool, f"{flag} must be a boolean")
    status = record["execution_status"]
    kind = record["result_kind"]
    _expect(status in EXECUTION_STATUSES, "execution_status is not permitted")
    _expect(kind in RESULT_KINDS, "result_kind is not permitted")
    _expect(status in KIND_STATUS[kind], f"result_kind {kind} is incompatible with execution_status {status}")
    _phase(record["parse"], "parse")
    _phase(record["elaboration"], "elaboration")
    _phase(record["source_maps"], "source_maps")
    _phase(record["consistency"], "consistency")
    facets = record["source_facets"]
    _expect(isinstance(facets, dict), "source_facets must be an object")
    _expect(type(facets.get("independent_gold_present")) is bool, "independent_gold_present must be boolean")
    match = facets.get("all_facet_match")
    _expect(match is None or type(match) is bool, "all_facet_match must be boolean or null")
    amb = facets.get("ambiguity")
    _expect(isinstance(amb, dict) and isinstance(amb.get("status"), str), "ambiguity.status is required")
    recon = record["reconstruction"]
    _expect(isinstance(recon, dict) and set(recon) == {"forward", "cycle", "final"},
            "reconstruction must contain exactly forward, cycle, and final")
    for name in ("forward", "cycle", "final"):
        _phase(recon[name], f"reconstruction.{name}")
    proof = record["proof"]
    _expect(isinstance(proof, dict), "proof must be an object")
    _expect(type(proof.get("useful")) is bool and type(proof.get("false_transfer")) is bool,
            "proof.useful and proof.false_transfer must be booleans")
    checker_class = proof.get("checker_class")
    _expect(checker_class in CHECKER_CLASSES, "proof.checker_class is not permitted")
    receipt = proof.get("receipt_sha256")
    _expect(receipt is None or _is_sha(receipt), "proof.receipt_sha256 must be sha256 or null")
    expected_class = KIND_CHECKER.get(kind)
    if expected_class:
        _expect(checker_class == expected_class, f"{kind} requires checker_class={expected_class}")
    if kind == "native_checked_proof":
        _expect(_is_sha(receipt), "native_checked_proof requires proof.receipt_sha256")
        _expect(isinstance(record["identities"].get("checker"), str) and record["identities"]["checker"],
                "native_checked_proof requires identities.checker")
    if kind != "native_checked_proof":
        _expect(not (proof.get("useful") and checker_class == "native" and status == "measured" and kind == "solver_local_result"),
                "solver-local results cannot be labeled native useful proofs")
    identities = record["identities"]
    _expect(isinstance(identities, dict), "identities must be an object")
    _expect(identities.get("experiment_arm") == record["experiment_arm"],
            "identities.experiment_arm must match experiment_arm")
    for key in ("model", "tool", "checker", "compiler"):
        value = identities.get(key)
        _expect(value is None or (isinstance(value, str) and value), f"identities.{key} must be a string or null")
    cost = record["cost"]
    _expect(isinstance(cost, dict), "cost must be an object")
    for key in ("elapsed_seconds", "cpu_seconds", "gpu_seconds", "provider_units",
                "memory_gib", "human_review_seconds"):
        _expect(key in cost, f"cost.{key} is required")
        value = cost[key]
        _expect(value is None or isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and value >= 0,
                f"cost.{key} must be a finite nonnegative number or null")
    artifacts = record["artifacts"]
    _expect(isinstance(artifacts, dict) and _is_sha(artifacts.get("raw_sha256")),
            "artifacts.raw_sha256 must be a sha256 digest")
    log_hash = artifacts.get("command_log_sha256")
    _expect(log_hash is None or _is_sha(log_hash), "artifacts.command_log_sha256 must be sha256 or null")
    expected = artifact_digest_for_record(record)
    _expect(artifacts["raw_sha256"] == expected, "artifacts.raw_sha256 does not match the canonical record body")
    _expect("admission" not in record, "raw records must not self-assert admission")


def admission_decision(record: Mapping[str, Any]) -> dict[str, Any]:
    validate_record(record)
    reasons: list[str] = []
    if not record["eligible"]:
        reasons.append("ineligible")
    if record["fixture"]:
        reasons.append("fixture")
    if record["execution_status"] == "invalid":
        reasons.append("invalid")
    if record["execution_status"] == "no_run" or record["result_kind"] == "no_run":
        reasons.append("no_run")
    if record["execution_status"] != "measured":
        reasons.append(f"execution_status={record['execution_status']}")
    if record["result_kind"] in {"failure", "no_run"}:
        reasons.append(f"result_kind={record['result_kind']}")
    if record["constructed_control"] and record["split"] != "constructed_control":
        reasons.append("constructed_control_outside_control_split")
    admitted = not reasons
    return {
        "measured_table_row": admitted,
        "reasons": tuple(reasons),
        "result_kind": record["result_kind"],
        "execution_status": record["execution_status"],
    }


def adapt_semantic_logic_roundtrip(
    case: Mapping[str, Any],
    *,
    experiment_arm: str,
    fixture: bool,
    source_id: str | None = None,
) -> dict[str, Any]:
    """Map this paper's normalized roundtrip fields into a result record.

    Forward, cycle, and final scores stay distinct.  Pilot fixtures remain
    fixtures and cannot enter natural measured tables. This is not a parser
    for native bench_semantic_logic_roundtrip reports; that integration still
    requires an explicit, validated field conversion.
    """
    case_id = str(source_id or case.get("case_id") or case.get("id") or "roundtrip-case")
    scores = case.get("scores") if isinstance(case.get("scores"), Mapping) else case
    def _score_phase(key: str) -> dict[str, Any]:
        raw = scores.get(key) if isinstance(scores, Mapping) else None
        if isinstance(raw, Mapping):
            status = str(raw.get("status") or ("success" if raw.get("ok") else "unmeasured"))
            score = raw.get("score")
        elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
            status, score = "success", float(raw)
        else:
            status, score = ("no_run", None) if fixture or not case else ("unmeasured", None)
        if status not in PHASE_STATUSES:
            status = "unmeasured"
        return {"status": status, "score": score}
    parse_ok = case.get("parse_ok")
    parse = {"status": "success" if parse_ok is True else ("failure" if parse_ok is False else "unmeasured"),
             "score": None}
    kind = "bounded_observation" if not fixture and parse_ok is True else ("failure" if parse_ok is False else "no_run")
    status = "measured" if kind == "bounded_observation" else ("failure" if kind == "failure" else "no_run")
    if fixture:
        kind, status = "no_run", "no_run"
    return make_record(
        source_id=case_id,
        experiment_arm=experiment_arm,
        execution_status=status,
        result_kind=kind,
        split="constructed_control" if fixture else str(case.get("split") or "final_test"),
        eligible=not fixture,
        fixture=fixture,
        constructed_control=fixture,
        parse=parse,
        forward=_score_phase("forward"),
        cycle=_score_phase("cycle"),
        final=_score_phase("final"),
        consistency=_score_phase("cycle"),
        tool="bench_semantic_logic_roundtrip",
        notes="normalized paper roundtrip input; native report conversion remains unqualified; not a native checker receipt",
    )


def adapt_semantic_roundtrip_compositions(
    case: Mapping[str, Any],
    *,
    experiment_arm: str,
    fixture: bool,
) -> dict[str, Any]:
    """Map normalized paper bridge fields, not a native composition report.

    A retained false transfer stays an attempted failure. This mapping does
    not validate the observation or manufacture independent evidence.
    """
    case_id = str(case.get("case_id") or case.get("id") or "composition-case")
    transfer = case["bridge_transfer"] if "bridge_transfer" in case else case.get("transfer")
    false_transfer = transfer is False
    consistency_ok = case.get("composition_consistency")
    if fixture:
        kind, status = "no_run", "no_run"
    elif transfer is True:
        kind, status = "solver_local_result", "measured"
    elif transfer is False:
        kind, status = "failure", "failure"
    else:
        kind, status = "no_run", "no_run"
    return make_record(
        source_id=case_id,
        experiment_arm=experiment_arm,
        execution_status=status,
        result_kind=kind,
        eligible=not fixture,
        fixture=fixture,
        constructed_control=fixture,
        consistency={"status": "success" if consistency_ok is True else (
            "failure" if consistency_ok is False else "no_run"), "score": None},
        false_transfer=false_transfer,
        checker_class="solver_local" if kind == "solver_local_result" else "none",
        tool="bench_semantic_roundtrip_compositions",
        notes="normalized paper bridge fields; native report conversion remains unqualified; solver-local transfer is not native checked proof",
    )


def _metric_ids(metrics: Mapping[str, Any]) -> list[str]:
    return [item["id"] for item in metrics["metrics"]]


def _ratio(numerator: int | None, denominator: int, status: str) -> dict[str, Any]:
    value: float | None
    if numerator is None or denominator <= 0 or status in {"unrun", "unavailable"}:
        value = None
    else:
        value = numerator / denominator
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "status": status,
    }


def _outcome_status(status_counts: Mapping[str, int]) -> str:
    attempted = sum(status_counts.get(name, 0) for name in ATTEMPTED_STATUSES)
    if attempted:
        return "measured"
    if status_counts.get("unavailable", 0) and not status_counts.get("no_run", 0):
        return "unavailable"
    return "unrun"


def _count_records(records: Sequence[Mapping[str, Any]]) -> Counter:
    counts: Counter = Counter()
    for record in records:
        if record["eligible"] and not record["fixture"]:
            counts[record["execution_status"]] += 1
    return counts


def account_arm(
    *,
    experiment_arm: str,
    eligible_count: int,
    records: Sequence[Mapping[str, Any]],
    default_status: str,
    default_kind: str,
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    _expect(eligible_count >= 0, "eligible_count must be nonnegative")
    _expect(default_status in EXECUTION_STATUSES, "default execution status is not permitted")
    _expect(default_kind in RESULT_KINDS, "default result kind is not permitted")
    eligible_records = []
    ineligible = 0
    fixtures = 0
    seen_ids: set[str] = set()
    for record in records:
        validate_record(record)
        _expect(record["experiment_arm"] == experiment_arm,
                f"record {record['record_id']} has the wrong experiment arm")
        if record["fixture"]:
            fixtures += 1
            admission_decision(record)
            _expect(not admission_decision(record)["measured_table_row"],
                    "fixture record was admitted as a measured table row")
            continue
        if not record["eligible"]:
            ineligible += 1
            continue
        _expect(record["source_id"] not in seen_ids, f"duplicate eligible source_id {record['source_id']}")
        seen_ids.add(record["source_id"])
        eligible_records.append(record)
    _expect(len(eligible_records) <= eligible_count,
            f"arm {experiment_arm} has more eligible records than the eligible count")
    remainder = eligible_count - len(eligible_records)
    status_counts: Counter = Counter({name: 0 for name in COVERAGE_STATUSES})
    kind_counts: Counter = Counter({name: 0 for name in RESULT_KINDS})
    for record in eligible_records:
        status_counts[record["execution_status"]] += 1
        kind_counts[record["result_kind"]] += 1
    status_counts[default_status] += remainder
    kind_counts[default_kind] += remainder
    _expect(sum(status_counts.values()) == eligible_count,
            f"arm {experiment_arm} coverage statuses do not sum to the eligible denominator")
    _expect(sum(kind_counts.values()) == eligible_count,
            f"arm {experiment_arm} result kinds do not sum to the eligible denominator")

    admitted: list[dict[str, Any]] = []
    rejected = Counter()
    for record in eligible_records:
        decision = admission_decision(record)
        if decision["measured_table_row"]:
            admitted.append(dict(record))
        else:
            for reason in decision["reasons"]:
                rejected[reason] += 1
    rejected["remainder_" + default_status] += remainder
    if default_status != "measured" or default_kind in {"no_run", "failure"}:
        pass
    else:
        raise AccountingError("compact remainder cannot default to an admitted measured row")

    outcome_status = _outcome_status(status_counts)
    adjudicated = [record for record in admitted
                   if record["source_facets"]["independent_gold_present"]
                   and type(record["source_facets"]["all_facet_match"]) is bool]
    native_success = sum(
        1 for record in admitted
        if record["result_kind"] == "native_checked_proof"
        and record["proof"]["useful"]
        and record["proof"]["checker_class"] == "native"
        and _is_sha(record["proof"]["receipt_sha256"])
    )
    metric_values: dict[str, Any] = {}
    for spec in metrics["metrics"]:
        metric_id = spec["id"]
        kind = spec["kind"]
        if metric_id == "coverage":
            metric_values[metric_id] = _ratio(status_counts["measured"], eligible_count, "accounted")
        elif metric_id == "parse_success":
            n = sum(1 for record in admitted if record["parse"]["status"] == "success")
            metric_values[metric_id] = _ratio(n if outcome_status == "measured" else None,
                                              eligible_count, outcome_status)
        elif metric_id == "elaboration_success":
            n = sum(1 for record in admitted if record["elaboration"]["status"] == "success")
            metric_values[metric_id] = _ratio(n if outcome_status == "measured" else None,
                                              eligible_count, outcome_status)
        elif metric_id == "all_facet_source_fidelity":
            n = sum(1 for record in adjudicated
                    if record["source_facets"]["all_facet_match"] is True)
            complete = eligible_count > 0 and len(adjudicated) == eligible_count
            if complete:
                status = "measured"
            elif outcome_status in {"unrun", "unavailable"}:
                status = outcome_status
            elif not any(record["source_facets"]["independent_gold_present"] for record in admitted):
                status = "unmeasured_pending_independent_gold"
            else:
                status = "unmeasured_pending_population_adjudication"
            metric_values[metric_id] = {
                **_ratio(n if complete else None, eligible_count, status),
                "adjudication_coverage": _ratio(len(adjudicated), eligible_count, "accounted"),
                "missing_adjudicated_units": eligible_count - len(adjudicated),
                "verified_success_lower_bound": {
                    **_ratio(n, eligible_count, "lower_bound"),
                    "not_a_primary_estimate": True,
                },
            }
        elif metric_id == "source_map_validity":
            n = sum(1 for record in admitted if record["source_maps"]["status"] == "success")
            metric_values[metric_id] = _ratio(n if outcome_status == "measured" else None,
                                              eligible_count, outcome_status)
        elif metric_id == "forward_reconstruction":
            n = sum(1 for record in admitted if record["reconstruction"]["forward"]["status"] == "success")
            metric_values[metric_id] = _ratio(n if outcome_status == "measured" else None,
                                              eligible_count, outcome_status)
        elif metric_id == "cycle_reconstruction":
            n = sum(1 for record in admitted if record["reconstruction"]["cycle"]["status"] == "success")
            metric_values[metric_id] = _ratio(n if outcome_status == "measured" else None,
                                              eligible_count, outcome_status)
        elif metric_id == "final_reconstruction":
            n = sum(1 for record in admitted if record["reconstruction"]["final"]["status"] == "success")
            metric_values[metric_id] = _ratio(n if outcome_status == "measured" else None,
                                              eligible_count, outcome_status)
        elif metric_id == "consistency":
            n = sum(1 for record in admitted if record["consistency"]["status"] == "success")
            metric_values[metric_id] = _ratio(n if outcome_status == "measured" else None,
                                              eligible_count, outcome_status)
        elif metric_id == "native_checked_useful_proof_coverage":
            metric_values[metric_id] = _ratio(
                native_success if outcome_status == "measured" else None,
                eligible_count, outcome_status,
            )
        elif metric_id == "solver_local_rate":
            metric_values[metric_id] = _ratio(kind_counts["solver_local_result"], eligible_count, "accounted")
        elif metric_id == "countermodel_rate":
            metric_values[metric_id] = _ratio(kind_counts["countermodel"], eligible_count, "accounted")
        elif metric_id == "bounded_observation_rate":
            metric_values[metric_id] = _ratio(kind_counts["bounded_observation"], eligible_count, "accounted")
        elif metric_id == "false_transfer_rate":
            # Observed failures belong in this error metric without being
            # admitted into success tables. Invalid and unrun rows do not.
            n = sum(1 for record in eligible_records
                    if record["execution_status"] in {"measured", "partial", "failure"}
                    and record["proof"]["false_transfer"])
            metric_values[metric_id] = _ratio(n if outcome_status == "measured" else None,
                                              eligible_count, outcome_status)
        elif metric_id.endswith("_rate") or metric_id in {
            "abstention_rate", "unsupported_rate", "unavailable_rate", "timeout_rate",
            "no_run_rate", "failure_rate", "invalid_rate",
        }:
            status_name = {
                "abstention_rate": "abstained",
                "unsupported_rate": "unsupported",
                "unavailable_rate": "unavailable",
                "timeout_rate": "timeout",
                "no_run_rate": "no_run",
                "failure_rate": "failure",
                "invalid_rate": "invalid",
            }[metric_id]
            metric_values[metric_id] = _ratio(status_counts[status_name], eligible_count, "accounted")
        elif metric_id == "total_cost":
            elapsed = [
                record["cost"]["elapsed_seconds"]
                for record in eligible_records
                if record["cost"]["elapsed_seconds"] is not None
            ]
            status = "measured" if elapsed else ("unrun" if outcome_status == "unrun" else "unmeasured")
            total = sum(elapsed) if elapsed else None
            metric_values[metric_id] = {
                "numerator": total,
                "denominator": eligible_count,
                "value": total,
                "status": status,
                "retained_cost_records": len(elapsed),
            }
        else:
            raise AccountingError(f"unhandled metric {metric_id}")
        _ = kind

    native_from_solver = sum(
        1 for record in eligible_records
        if record["result_kind"] == "solver_local_result" and record["proof"]["checker_class"] == "native"
    )
    _expect(native_from_solver == 0, "solver-local records cannot carry native checker class")

    return {
        "experiment_arm": experiment_arm,
        "eligible": eligible_count,
        "explicit_records": len(eligible_records),
        "remainder": remainder,
        "coverage_statuses": {name: int(status_counts[name]) for name in COVERAGE_STATUSES},
        "result_kinds": {name: int(kind_counts[name]) for name in RESULT_KINDS},
        "admitted_measured_rows": len(admitted),
        "rejected_from_measured_table": dict(sorted(rejected.items())),
        "ineligible_records": ineligible,
        "fixture_records": fixtures,
        "metrics": metric_values,
        "admitted_record_ids": sorted(record["record_id"] for record in admitted),
    }


def denominator_check(arm: Mapping[str, Any]) -> dict[str, Any]:
    eligible = arm["eligible"]
    status_sum = sum(arm["coverage_statuses"].values())
    kind_sum = sum(arm["result_kinds"].values())
    dropped = eligible - status_sum
    problems = []
    if status_sum != eligible:
        problems.append("coverage statuses do not exhaust the eligible denominator")
    if kind_sum != eligible:
        problems.append("result kinds do not exhaust the eligible denominator")
    if arm["explicit_records"] + arm["remainder"] != eligible:
        problems.append("explicit records plus remainder do not equal the eligible count")
    if arm["admitted_measured_rows"] > arm["coverage_statuses"].get("measured", 0):
        problems.append("admitted measured rows exceed measured execution statuses")
    return {
        "eligible": eligible,
        "coverage_status_sum": status_sum,
        "result_kind_sum": kind_sum,
        "dropped_eligible": dropped,
        "pass": not problems,
        "problems": problems,
    }


def regenerate_tables(
    recipe: Mapping[str, Any],
    *,
    metrics: Mapping[str, Any] | None = None,
    schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = metrics or load_metrics_contract()
    schema = schema or load_schema_contract()
    _expect(recipe.get("schema") == RECIPE_SCHEMA, "population recipe schema mismatch")
    basis = recipe["eligible_basis"]
    _expect(isinstance(basis, Mapping) and type(basis.get("count")) is int and basis["count"] >= 0,
            "eligible_basis.count must be a nonnegative integer")
    _expect(basis.get("split") in SPLITS, "eligible_basis.split must name a permitted split")
    natural_basis = basis.get("field") == "natural_source_units"
    _expect(not natural_basis or basis["split"] != "constructed_control",
            "natural_source_units cannot use the constructed_control split")
    arms = list(recipe["arms"])
    _expect(arms == sorted(set(arms), key=arms.index), "recipe arms must be unique and stable")
    default_status = recipe["default_execution_status"]
    default_kind = recipe["default_result_kind"]
    eligible_ids = recipe.get("eligible_source_ids")
    if eligible_ids is not None:
        _expect(isinstance(eligible_ids, list) and all(isinstance(item, str) and item for item in eligible_ids),
                "eligible_source_ids must be a list of nonempty strings")
        _expect(len(eligible_ids) == len(set(eligible_ids)) == basis["count"],
                "eligible_source_ids must be unique and match eligible_basis.count")
    grouped: dict[str, list[dict[str, Any]]] = {arm: [] for arm in arms}
    for record in recipe.get("records") or []:
        validate_record(record)
        arm = record["experiment_arm"]
        _expect(arm in grouped, f"record arm {arm} is not in the recipe")
        grouped[arm].append(record)
        if record["eligible"] and not record["fixture"]:
            _expect(record["split"] == basis["split"],
                    f"source_id {record['source_id']} belongs to a different split")
            _expect(not natural_basis or not record["constructed_control"],
                    "constructed control cannot enter a natural source population")
            if eligible_ids is not None:
                _expect(record["source_id"] in eligible_ids,
                        f"source_id {record['source_id']} is outside the frozen eligible set")
    tables = {}
    checks = {}
    for arm in arms:
        accounted = account_arm(
            experiment_arm=arm,
            eligible_count=basis["count"],
            records=grouped[arm],
            default_status=default_status,
            default_kind=default_kind,
            metrics=metrics,
        )
        check = denominator_check(accounted)
        if not check["pass"]:
            raise AccountingError(f"denominator check failed for arm {arm}: {check['problems']}")
        tables[arm] = accounted
        checks[arm] = check
    envelope = {
        "schema": TABLE_SCHEMA,
        "generated_from": {
            "recipe_sha256": sha256_obj({key: recipe[key] for key in recipe if key != "records"}),
            "records_sha256": sha256_obj(recipe.get("records") or []),
            "metrics_sha256": sha256_obj(metrics),
            "schema_sha256": sha256_obj(schema),
            "eligible_basis_sha256": sha256_obj(basis),
        },
        "eligible_basis": dict(basis),
        "default_execution_status": default_status,
        "default_result_kind": default_kind,
        "denominator_checks": checks,
        "arms": tables,
        "claim_limits": [
            "This accounting does not execute models, compilers, or native checkers.",
            "Unrun and unavailable conditions are not measured zeros.",
            "Solver-local results, countermodels, and bounded observations are not native checked proofs.",
            "Fixture and invalid records cannot occupy measured table rows.",
        ],
    }
    envelope["tables_sha256"] = sha256_obj({key: envelope[key] for key in envelope if key != "tables_sha256"})
    return envelope


def frozen_unrun_recipe(root: Path | None = None) -> dict[str, Any]:
    root = root or REPO_ROOT
    paper = root / "papers/completion/autoformalization"
    plan = load_json(paper / "config/experiment_plan.json")
    splits = load_json(paper / "data/splits.json")
    corpus = load_json(paper / "data/corpus_manifest.json")
    _expect(plan.get("schema") == "autoformalization-experiment-plan/v1", "unexpected experiment plan schema")
    arms = [item["id"] for item in plan["conditions"]]
    _expect(arms == ["A", "B", "C", "D", "E", "T0", "T1", "T2", "T3", "T4", "T5"],
            "frozen experiment arms drifted")
    count = splits["counts"]["final_test"]["natural_source_units"]
    _expect(type(count) is int and count == 1913, "frozen final-test natural source units drifted")
    _expect(corpus["inventories"]["legal_policy"]["unique_normalized_source_units"] == 2035,
            "corpus unique source units drifted")
    _expect(corpus["inventories"]["synthetic_fixture"]["admission"] == "excluded_synthetic_fixture",
            "synthetic fixtures must remain excluded from natural denominators")
    _expect(corpus["inventories"]["coding_requirements_and_implementation"]["natural_admitted"] == 0, "coding admitted drifted")
    _expect(corpus["inventories"]["trace_material"]["natural_admitted"] == 0, "trace admitted drifted")
    return {
        "schema": RECIPE_SCHEMA,
        "eligible_basis": {
            "split": "final_test",
            "field": "natural_source_units",
            "count": count,
            "manifest_path": "papers/completion/autoformalization/data/splits.json",
            "manifest_sha256": sha256_file(paper / "data/splits.json"),
            "corpus_manifest_sha256": sha256_file(paper / "data/corpus_manifest.json"),
            "experiment_plan_sha256": sha256_file(paper / "config/experiment_plan.json"),
            "private_final_ids_disclosed": bool(corpus.get("private_final_ids_disclosed")),
        },
        "arms": arms,
        "default_execution_status": "no_run",
        "default_result_kind": "no_run",
        "records": [],
        "excluded_populations": {
            "synthetic_fixture": corpus["inventories"]["synthetic_fixture"]["admission"],
            "coding_natural_admitted": 0,
            "trace_natural_admitted": 0,
        },
        "notes": "Compact unrun recipe over frozen eligible counts. Individual final-test identities remain undisclosed.",
    }


def assert_tables_deterministic(recipe: Mapping[str, Any], tables: Mapping[str, Any]) -> None:
    again = regenerate_tables(recipe)
    _expect(canonical_dumps(tables) == canonical_dumps(again), "table regeneration is not deterministic")
    _expect(tables["tables_sha256"] == again["tables_sha256"], "table digest is not stable")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_dumps(value) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    account = sub.add_parser("account", help="Regenerate tables from a compact recipe")
    account.add_argument("--recipe", type=Path)
    account.add_argument("--output", type=Path)
    unrun = sub.add_parser("materialize-unrun", help="Account the frozen AF-002/AF-004 unrun population")
    unrun.add_argument("--root", type=Path, default=REPO_ROOT)
    unrun.add_argument("--output", type=Path)
    check = sub.add_parser("check-schema", help="Load and pin schema/metrics contracts")
    check.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    if args.command == "check-schema":
        schema = load_schema_contract()
        metrics = load_metrics_contract()
        report = {
            "schema": SCHEMA,
            "result_kinds": list(RESULT_KINDS),
            "execution_statuses": list(EXECUTION_STATUSES),
            "metrics": _metric_ids(metrics),
            "schema_sha256": sha256_obj(schema),
            "metrics_sha256": sha256_obj(metrics),
        }
        print(canonical_dumps(report))
        return 0
    if args.command == "materialize-unrun":
        recipe = frozen_unrun_recipe(Path(args.root).resolve())
        tables = regenerate_tables(recipe)
        assert_tables_deterministic(recipe, tables)
        if args.output:
            _write_json(Path(args.output), tables)
        print(canonical_dumps({
            "schema": tables["schema"],
            "tables_sha256": tables["tables_sha256"],
            "eligible": tables["eligible_basis"]["count"],
            "arms": {
                arm: {
                    "eligible": body["eligible"],
                    "admitted_measured_rows": body["admitted_measured_rows"],
                    "no_run": body["coverage_statuses"]["no_run"],
                    "native_checked_useful_proof_coverage": body["metrics"]["native_checked_useful_proof_coverage"],
                }
                for arm, body in tables["arms"].items()
            },
            "denominator_checks_pass": all(item["pass"] for item in tables["denominator_checks"].values()),
        }))
        return 0
    if not args.recipe:
        raise AccountingError("account requires --recipe")
    recipe = load_json(Path(args.recipe))
    tables = regenerate_tables(recipe)
    assert_tables_deterministic(recipe, tables)
    if args.output:
        _write_json(Path(args.output), tables)
    print(canonical_dumps({
        "tables_sha256": tables["tables_sha256"],
        "denominator_checks_pass": all(item["pass"] for item in tables["denominator_checks"].values()),
    }))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AccountingError as exc:
        print(f"run_benchmark: {exc}", flush=True)
        raise SystemExit(1)
