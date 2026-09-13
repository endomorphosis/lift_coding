#!/usr/bin/env python3
"""Validate NS-011 published cold-oracle reuse artifacts.

Re-checks structural invariants and performs a live smoke of independent
cold pytest execution, identity-from-files reuse lookup, mutation
invalidation, skip-not-agreement, and false-reuse accounting.
Does not claim a live A–D experiment or a Groth16 pytest proof.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile


SNAP = Path(__file__).resolve().parent
ROOT = SNAP.parents[5]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP_QUAL = SNAP / "qualification"
RUNNER = SNAP / "run_cold_oracle_qualification.py"
ACC_ROOT = ROOT / "external/ipfs_accelerate"
DS_ROOT = ROOT / "external/ipfs_datasets"

CRITERIA = (
    "Cold execution and reuse are independently recorded for every scored case; skipped/unavailable oracle cases cannot count as safe agreement.",
    "Each required mutation has an expected invalidation/fallback decision and a genuine unchanged positive reuse witness.",
    "False-reuse rate includes all attempted reuse cases and reports exact counts/uncertainty, including observed failures.",
    "Any discovered unsound reuse blocks the affected profile until fixed/requalified or explicitly excluded from the paper claim.",
)

REQUIRED_MUTATION_KINDS = (
    "fixture_definition",
    "fixture_instance",
    "finalizer",
    "plugin",
    "hook",
    "config",
    "policy",
    "key",
    "runtime",
    "external_snapshot",
    "test_removal",
    "stale_cache",
    "incomplete_trace",
    "changed_external_effect",
    "unchanged_positive",
)

PAPER_CLAIM_PROFILE = "identity-from-files"
STALE_KEY_PROFILE = "stale-key-caller"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"NS-011 validation failed: {message}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def live_smoke() -> None:
    sys.path.insert(0, str(SNAP))
    import run_cold_oracle_qualification as runner

    for path in (str(ACC_ROOT), str(DS_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)

    capability = runner.prepare_imports()
    api = capability.pop("api")
    python = "/usr/bin/python3.12"
    work = Path(tempfile.mkdtemp(prefix="ns011-smoke-"))
    suite = work / "suite"
    runner.materialize(suite, runner.RECIPE)
    cold = runner.cold_run(
        suite=suite,
        node_id=runner.NODE_DOUBLE,
        work=work / "cold-pass",
        python=python,
    )
    if cold["cold_outcome"] != "pass" or cold["skipped_or_unavailable"]:
        fail(f"live smoke: baseline cold did not pass ({cold})")

    admission = runner.admit_baseline(api, suite, runner.NODE_DOUBLE)
    hit = runner.lookup_reuse(
        api,
        locator=admission["locator"],
        key=admission["key"],
        candidates=(admission["candidate"],),
    )
    if enum_action(hit) != "SKIP" or enum_reason(hit) != "proof_cache_hit":
        fail("live smoke: unchanged eligible reuse did not hit")

    mutated_files = runner.apply_files(
        runner.RECIPE,
        {"conftest.py": runner.RECIPE["conftest.py"].replace("yield 21\n", "yield 20\n")},
    )
    mutated = work / "mutated"
    runner.materialize(mutated, mutated_files)
    bound = runner.bind_identity(api, mutated, node_id=runner.NODE_DOUBLE)
    key = runner._execution_key(api, admission["locator"], bound)
    miss = runner.lookup_reuse(
        api,
        locator=admission["locator"],
        key=key,
        candidates=(admission["candidate"],),
    )
    if enum_action(miss) != "RUN":
        fail("live smoke: fixture mutation reused")
    if enum_reason(miss) != "execution_key_mismatch":
        fail(f"live smoke: unexpected mutation reason {enum_reason(miss)}")
    cold_fail = runner.cold_run(
        suite=mutated,
        node_id=runner.NODE_DOUBLE,
        work=work / "cold-fail",
        python=python,
    )
    if cold_fail["cold_outcome"] != "fail":
        fail(f"live smoke: mutated fixture did not fail cold ({cold_fail})")
    scoring = runner.score_pair(
        expected_reuse_action="RUN",
        reuse_action=enum_action(miss),
        cold=cold_fail,
        expected_cold_outcome="fail",
    )
    if scoring["false_reuse"] or not scoring["counts_as_safe_agreement"]:
        fail("live smoke: honest mutation path was not correct invalidation")

    skip_cold = runner.cold_run(
        suite=suite,
        node_id=runner.NODE_SKIP,
        work=work / "cold-skip",
        python=python,
    )
    if skip_cold["oracle_status"] != "skipped" or skip_cold["counts_as_safe_agreement_eligible"]:
        fail("live smoke: pytest skip was treated as an eligible oracle")
    skip_score = runner.score_pair(
        expected_reuse_action="RUN",
        reuse_action="RUN",
        cold=skip_cold,
        expected_cold_outcome="skip",
    )
    if skip_score["counts_as_safe_agreement"]:
        fail("live smoke: skipped oracle counted as safe agreement")

    stale = runner.lookup_reuse(
        api,
        locator=admission["locator"],
        key=admission["key"],
        candidates=(admission["candidate"],),
    )
    if enum_action(stale) != "SKIP":
        fail("live smoke: stale key did not hit; attack row would be vacuous")
    stale_score = runner.score_pair(
        expected_reuse_action="RUN",
        reuse_action=enum_action(stale),
        cold=cold_fail,
        expected_cold_outcome="fail",
    )
    if not stale_score["unsound_reuse"]:
        fail("live smoke: stale-key plus failing cold was not unsound reuse")


def enum_action(lookup) -> str:
    return str(getattr(lookup.decision.action, "value", lookup.decision.action))


def enum_reason(lookup) -> str:
    return str(getattr(lookup.decision.reason_code, "value", lookup.decision.reason_code))


def main() -> None:
    cold_path = QUAL / "cold_oracle_results.jsonl"
    mutation_path = QUAL / "reuse_mutation_results.jsonl"
    analysis_path = QUAL / "reuse_analysis.json"
    for path in (cold_path, mutation_path, analysis_path, RUNNER):
        if not path.is_file():
            fail(f"missing {path}")
    if digest(cold_path) != digest(SNAP_QUAL / "cold_oracle_results.jsonl"):
        fail("qualification cold results drifted from snapshot")
    if digest(mutation_path) != digest(SNAP_QUAL / "reuse_mutation_results.jsonl"):
        fail("qualification mutation results drifted from snapshot")
    if digest(analysis_path) != digest(SNAP_QUAL / "reuse_analysis.json"):
        fail("qualification analysis drifted from snapshot")

    cold_rows = load_jsonl(cold_path)
    mutation_rows = load_jsonl(mutation_path)
    analysis = load_json(analysis_path)

    if analysis.get("schema") != "neurosymbolic-supervision/reuse-analysis@1":
        fail("unexpected analysis schema")
    if analysis.get("task_id") != "NS-011":
        fail("analysis task_id mismatch")
    if not cold_rows or not mutation_rows:
        fail("empty result files")
    if len(cold_rows) != len(mutation_rows):
        fail("cold and mutation row counts differ")
    cold_ids = [row.get("case_id") for row in cold_rows]
    mutation_ids = [row.get("case_id") for row in mutation_rows]
    if cold_ids != mutation_ids:
        fail("cold and mutation case_id order/identity differ")
    if len(set(cold_ids)) != len(cold_ids):
        fail("duplicate case_id")

    for row in cold_rows:
        if row.get("schema") != "neurosymbolic-supervision/cold-oracle-result@1":
            fail(f"{row.get('case_id')} has unexpected cold schema")
        if not row.get("independent_of_reuse_lookup"):
            fail(f"{row.get('case_id')} cold is not independent")
        if "oracle_status" not in row or "cold_outcome" not in row:
            fail(f"{row.get('case_id')} missing cold fields")
        if row.get("oracle_status") in {"skipped", "unavailable"}:
            if not row.get("skipped_or_unavailable"):
                fail(f"{row.get('case_id')} skip/unavailable not flagged")
            if row.get("counts_as_safe_agreement_eligible"):
                fail(f"{row.get('case_id')} unavailable oracle marked agreement-eligible")
        if row.get("status") != "pass" and row.get("profile") == PAPER_CLAIM_PROFILE:
            fail(f"{row.get('case_id')} paper-claim cold status is not pass")

    for row in mutation_rows:
        if row.get("schema") != "neurosymbolic-supervision/reuse-mutation-result@1":
            fail(f"{row.get('case_id')} has unexpected mutation schema")
        if not row.get("reuse_recorded_before_cold"):
            fail(f"{row.get('case_id')} reuse was not recorded before cold")
        if not row.get("oracle_unavailable_to_reuse_lookup"):
            fail(f"{row.get('case_id')} oracle was available to reuse lookup")
        if row.get("status") != "pass" and row.get("profile") == PAPER_CLAIM_PROFILE:
            fail(f"{row.get('case_id')} paper-claim mutation status is not pass")
        if row.get("oracle_skip_or_unavailable") and row.get("counts_as_safe_agreement"):
            fail(f"{row.get('case_id')} skip/unavailable counted as safe agreement")

    independence = analysis.get("independence") or {}
    if not independence.get("reuse_recorded_before_cold_for_every_case"):
        fail("analysis did not record reuse independently for every case")
    if not independence.get("cold_independent_of_reuse_lookup"):
        fail("analysis did not record cold independently")
    if not independence.get("skipped_or_unavailable_cannot_count_as_safe_agreement"):
        fail("analysis allows skipped/unavailable agreement")
    if not independence.get("oracle_unavailable_to_candidate_generation"):
        fail("analysis does not keep the oracle unavailable to candidate generation")

    kinds = set(analysis.get("observed_mutation_kinds") or ())
    missing = [kind for kind in REQUIRED_MUTATION_KINDS if kind not in kinds]
    if missing:
        fail(f"missing required mutation kinds: {missing}")
    if analysis.get("missing_required_mutation_kinds"):
        fail("analysis still lists missing mutation kinds")
    witnesses = analysis.get("genuine_unchanged_positive_reuse_witnesses") or []
    if len(witnesses) < 1:
        fail("no genuine unchanged positive reuse witness")
    true_reuse = [
        row
        for row in mutation_rows
        if row.get("scoring_class") == "true_reuse"
        and row.get("reuse_action") == "SKIP"
        and row.get("profile") == PAPER_CLAIM_PROFILE
    ]
    if not true_reuse:
        fail("no paper-claim true reuse SKIP witness")
    cold_by_id = {row["case_id"]: row for row in cold_rows}
    for row in true_reuse:
        cold = cold_by_id[row["case_id"]]
        if cold.get("cold_outcome") != "pass" or cold.get("skipped_or_unavailable"):
            fail(f"{row['case_id']} true reuse lacks a passing independent cold oracle")

    required_invalidations = [
        row
        for row in mutation_rows
        if row.get("mutation_kind") in REQUIRED_MUTATION_KINDS
        and row.get("mutation_kind") != "unchanged_positive"
        and row.get("profile") == PAPER_CLAIM_PROFILE
        and row.get("expected_reuse_action") == "RUN"
    ]
    if not required_invalidations:
        fail("no paper-claim mutation invalidation rows")
    for row in required_invalidations:
        if row.get("reuse_action") != "RUN":
            fail(f"{row['case_id']} mutation did not fall back/invalidate")

    paper = analysis.get("paper_claim") or {}
    false_reuse = paper.get("false_reuse") or {}
    if false_reuse.get("denominator") != len(
        [row for row in mutation_rows if row.get("profile") == PAPER_CLAIM_PROFILE]
    ):
        fail("paper-claim false-reuse denominator is not all attempted paper-claim cases")
    if false_reuse.get("events") != 0:
        fail("paper-claim profile has observed false reuse")
    if not isinstance(false_reuse.get("observed_failures"), list):
        fail("false-reuse observed_failures missing")
    interval = false_reuse.get("clopper_pearson_95") or {}
    if interval.get("lower") != 0.0 or not isinstance(interval.get("upper"), float):
        fail("paper-claim false-reuse interval is not exact 0/N Clopper-Pearson")
    if false_reuse.get("exact_counts") != f"0/{false_reuse.get('denominator')}":
        fail("false-reuse exact counts mismatch")
    all_attempted = (analysis.get("all_attempted_reuse_cases") or {}).get("false_reuse") or {}
    if all_attempted.get("denominator") != len(mutation_rows):
        fail("all-attempted false-reuse denominator is not every reuse case")
    if not isinstance(all_attempted.get("observed_failures"), list):
        fail("all-attempted observed failures missing")
    if all_attempted.get("events") != len(all_attempted.get("observed_failures") or ()):
        fail("all-attempted event count != listed failures")

    if paper.get("blocked"):
        fail("paper-claim profile is blocked")
    excluded = (analysis.get("excluded_profiles") or {}).get(STALE_KEY_PROFILE) or {}
    if not excluded.get("blocked"):
        fail("stale-key-caller unsound reuse was not blocked")
    if "excluded from the paper reuse claim" not in str(excluded.get("exclusion", "")).lower():
        fail("stale-key-caller was not explicitly excluded from the paper claim")
    if analysis.get("paper_claim_profile") != PAPER_CLAIM_PROFILE:
        fail("paper claim profile mismatch")

    live_smoke()
    print("NS-011 cold-oracle validation: OK")
    print(f"cases={len(mutation_rows)} paper_false_reuse={false_reuse.get('exact_counts')}")
    print(f"true_reuse_witnesses={len(true_reuse)}")


if __name__ == "__main__":
    main()
