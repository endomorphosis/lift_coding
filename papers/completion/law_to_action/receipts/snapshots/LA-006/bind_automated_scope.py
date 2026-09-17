#!/usr/bin/python3.12
"""Bind frozen LA-026 CVE envelopes to compact machine-checkable contracts.

The pair/control JSONL envelopes stay byte-identical to LA-026. Polarity
contracts are written as a compact catalog. This compiler is distinct from the
CVEfixes adapter under evaluation. It does not execute untrusted source, invent
reviewers, or treat dataset-derived roles as evaluation polarity.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/law_to_action"
BENCHMARK = PAPER / "benchmark"
CASES = BENCHMARK / "cases"
ANNOT = BENCHMARK / "annotations"
SNAP = Path(__file__).resolve().parent
LA026 = PAPER / "receipts/snapshots/LA-026/outputs/benchmark/cases"
HIST = SNAP / "original_failed_blocked_attempt_20260911"
LIVE_PAIRS = CASES / "cve_pairs.jsonl"
LIVE_CONTROLS = CASES / "cve_controls.jsonl"
LIVE_REVIEW = ANNOT / "cve_review.md"
SNAP_OUT = SNAP / "outputs/benchmark"
CONTRACTS = SNAP / "polarity_contracts.jsonl"
PRODUCER_ID = "la-006-scoped-behavior-contract-compiler"
PRODUCER_KIND = "machine_contract_expectation_compiler"
PRODUCER_VERSION = "la-006-automated-scope/v1"
EVALUATED_ADAPTER = "ipfs_datasets_py.logic.security_ir.cvefixes.adapter"
FORBIDDEN_FIXTURE_CVES = {"CVE-2026-0042"}
REQUIRED_CONTROLS = {
    "misleading_cve_similarity",
    "fixed_negative_control",
    "broadened_effects",
    "unknown_scope",
    "wildcard_scope",
    "self_granted_authority",
    "unsupported_transfer",
}
REJECTED_CONTROLS = {"wildcard_scope", "self_granted_authority", "broadened_effects"}
DENOM_PAIR = (
    "Source-difference observation at pinned revisions does not establish "
    "evaluation polarity, exploitability, allow/deny, or independent human agreement."
)
DENOM = {
    "wildcard_scope": "Wildcard scope is rejected by the scoped vocabulary contract; it is not evaluation polarity.",
    "self_granted_authority": "Self-granted authority is rejected; it is not evaluation polarity or execution authority.",
    "broadened_effects": "Catch-all effects are generalization, not a scoped deny candidate or evaluation polarity.",
    "unsupported_transfer": "No supported mapping onto export_json exists; transfer remains unknown and is not empirical success.",
    "unknown_scope": "Incomplete scope is not recoded as allow or deny.",
    "misleading_cve_similarity": "A real unselected distractor is not transfer of the parent restriction; polarity remains unknown.",
    "fixed_negative_control": "Dataset-derived fixed-side role is not independently reviewed polarity and is not universal security.",
}


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def producer() -> dict:
    return {
        "distinct_from_evaluated_adapter": True,
        "evaluated_adapter": EVALUATED_ADAPTER,
        "generated_labels_are": "explicitly identified machine-contract expectations, never human/expert gold",
        "id": PRODUCER_ID,
        "kind": PRODUCER_KIND,
        "not_cvefixes_adapter_output": True,
        "not_expert_security_review": True,
        "not_human_gold": True,
        "not_independent_review": True,
        "version": PRODUCER_VERSION,
    }


def wildcard_tokens(value) -> list[str]:
    blob = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return [token for token in ("*", "any", "everything", "generalized") if token in blob or token in blob.casefold()]


def retain_envelopes() -> dict[str, str]:
    hashes = {}
    for name in ("cve_pairs.jsonl", "cve_controls.jsonl"):
        live = CASES / name
        origin = LA026 / name
        if not live.is_file() or not origin.is_file():
            raise SystemExit(f"missing envelope {name}")
        live_sha = sha256_file(live)
        origin_sha = sha256_file(origin)
        if live_sha != origin_sha:
            raise SystemExit(f"{name} drifted from LA-026 ({live_sha} != {origin_sha})")
        snap = SNAP_OUT / "cases" / name
        hist = HIST / "outputs/benchmark/cases" / name
        if snap.is_file() and sha256_file(snap) != live_sha:
            hist.parent.mkdir(parents=True, exist_ok=True)
            if not hist.is_file():
                shutil.copyfile(snap, hist)
        elif not hist.is_file() and snap.is_file():
            hist.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(snap, hist)
        snap.parent.mkdir(parents=True, exist_ok=True)
        if not snap.is_file() or sha256_file(snap) != live_sha:
            shutil.copyfile(live, snap)
        hashes[name] = live_sha
        hashes[f"la026/{name}"] = origin_sha
        if hist.is_file():
            hashes[f"original/{name}"] = sha256_file(hist)
    return hashes


def pair_observation(pair: dict) -> dict:
    iso = pair["supported_behavior_evidence"]["isolated_reproduction"]
    return {
        "effect_observed": iso["effect_observed"],
        "executed_untrusted_source": iso["executed_untrusted_source"],
        "fixed_files_recovered": iso["fixed_files_recovered"],
        "fixed_revision": iso["fixed_revision"],
        "fixed_tree_sha256": iso["fixed_tree_sha256"],
        "kind": iso["kind"],
        "native_sink_observed": iso["native_sink_observed"],
        "observer": iso["observer"],
        "recovery_failures": pair["supported_behavior_evidence"].get("recovery_failures") or [],
        "reproduction_record": str(
            Path("papers/completion/law_to_action/benchmark/cve_reproduction/pairs") / f"{pair['source']['cve_id']}.json"
        ),
        "runnable_sandbox_reproduction": iso["runnable_sandbox_reproduction"],
        "source": "LA-026 isolated_reproduction",
        "source_difference_observed": iso["status"] == "source_difference_observed_at_pinned_revisions",
        "status": iso["status"],
        "vulnerable_files_recovered": iso["vulnerable_files_recovered"],
        "vulnerable_revision": iso["vulnerable_revision"],
        "vulnerable_tree_sha256": iso["vulnerable_tree_sha256"],
    }


def control_observation(row: dict, parent: dict) -> tuple[dict, str, bool]:
    cls = row["control_class"]
    status = row["expected_status"]
    if cls == "wildcard_scope":
        payload = row.get("rejected_payload") or {}
        tokens = wildcard_tokens(payload)
        obs = {"contains_wildcard": bool(tokens), "wildcard_tokens_observed": tokens}
        return obs, "wildcard_scope_rejected", bool(tokens) and status == "rejected"
    if cls == "self_granted_authority":
        payload = row.get("rejected_payload") or {}
        obs = {
            "authoritative": payload.get("authoritative"),
            "grants_execution_authority": payload.get("grants_execution_authority"),
            "self_grant_observed": payload.get("grants_execution_authority") is True,
        }
        return obs, "self_granted_authority_rejected", obs["self_grant_observed"] and status == "rejected"
    if cls == "broadened_effects":
        payload = row.get("broadened_candidate") or {}
        tokens = wildcard_tokens(payload)
        obs = {
            "contains_wildcard": bool(tokens) or payload.get("wildcard") is True,
            "wildcard_flag": payload.get("wildcard"),
            "wildcard_tokens_observed": tokens,
        }
        return obs, "broadened_effects_rejected", obs["contains_wildcard"] and status == "rejected"
    if cls == "unsupported_transfer":
        mapping = parent.get("intent_code_effect_mapping") or {}
        obs = {
            "parent_mapping_status": (mapping.get("code_effect") or {}).get("status"),
            "target_handler": (row.get("target") or {}).get("handler"),
            "transfer_supported": False,
        }
        ok = status == "unknown" and obs["parent_mapping_status"] == "unsupported_transfer"
        return obs, "unsupported_transfer_unknown", ok
    if cls == "unknown_scope":
        restriction = parent.get("restriction_candidate") or {}
        obs = {
            "complete_scoped_deny_candidate": False,
            "parent_restriction_authoritative": restriction.get("authoritative"),
            "parent_restriction_wildcard": restriction.get("wildcard"),
            "reason_recorded": bool(row.get("reason")),
        }
        return obs, "unknown_scope_retained_unknown", status == "unknown"
    if cls == "misleading_cve_similarity":
        distractor = row.get("distractor") or {}
        parent_cve = parent["source"]["cve_id"]
        obs = {
            "distractor_cve_id": distractor.get("cve_id"),
            "distractor_is_empirical_parent": distractor.get("cve_id") == parent_cve,
            "parent_cve_id": parent_cve,
            "relation": distractor.get("relation"),
        }
        ok = status == "unknown" and bool(obs["distractor_cve_id"]) and not obs["distractor_is_empirical_parent"]
        return obs, "misleading_similarity_is_not_transfer", ok
    if cls == "fixed_negative_control":
        fixed = parent["sides"]["fixed"]
        obs = {
            "fixed_body_sha256": row.get("fixed_body_sha256"),
            "fixed_case_id": row.get("fixed_case_id"),
            "matches_parent_fixed_body": row.get("fixed_body_sha256") == fixed.get("body_sha256"),
            "matches_parent_fixed_case": row.get("fixed_case_id") == fixed.get("case_id"),
            "universal_security_claimed": False,
        }
        ok = status == "unknown" and obs["matches_parent_fixed_body"] and obs["matches_parent_fixed_case"]
        return obs, "fixed_side_is_not_universal_security", ok
    raise SystemExit(f"unrecognized control class {cls}")


def contract(checked: str, observation: dict, subject_id: str, *, polarity_supported: bool, status_supported: bool | None, denom: str) -> dict:
    body = {
        "authority": "explicitly_identified_machine_contract_expectation",
        "checked_property": checked,
        "expectation_kind": "machine_contract",
        "frozen_before_evaluated_predictions": True,
        "id": f"{subject_id}:scoped-behavior-contract",
        "kind": "scoped_machine_checkable_behavior_contract",
        "observation": observation,
        "polarity_supported_by_contract": polarity_supported,
        "producer": producer(),
        "unsupported_metric_denominator": {"excluded": True, "reason": denom},
    }
    if status_supported is not None:
        body["status_supported_by_contract"] = status_supported
    return body


def polarity_result(subject_kind: str, subject_id: str, contract_body: dict, extra: dict) -> dict:
    row = {
        "behavior_contract": contract_body,
        "empirical_success_credit": False,
        "expected": "unknown",
        "expert_certified": False,
        "independent_human_gold": False,
        "independently_reviewed": False,
        "schema": "law-to-action-cve-polarity-result/v1",
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "universal_security_claimed": False,
    }
    row.update(extra)
    return row


def write_review(pairs: list[dict], summary: dict) -> None:
    rows = []
    for pair in pairs:
        source = pair["source"]
        iso = pair["supported_behavior_evidence"]["isolated_reproduction"]
        failures = pair["supported_behavior_evidence"].get("recovery_failures") or []
        rows.append(
            "| `{cve}` | `{repo}` | {split} | {held} | `{parent}` | `{fix}` | {vfiles}/{listed} | {ffiles}/{listed} | {fail} | {cwe} |".format(
                cve=source["cve_id"],
                repo=source["repository"],
                split=pair["split"],
                held="yes" if pair["held_out"] else "no",
                parent=iso["vulnerable_revision"][:12],
                fix=iso["fixed_revision"][:12],
                vfiles=iso["vulnerable_files_recovered"],
                ffiles=iso["fixed_files_recovered"],
                listed=iso["files_listed"],
                fail=len(failures),
                cwe=source["cwe_id"],
            )
        )
    text = f"""# LA-006 source-supported CVE pair evidence under the automated scope

**Review status: automated-scope complete; human gold uncollected.** Independent
human security review was not obtained and is not required for this amended
scope. Packet-preparer, source-recovery, and machine-contract-compiler labels
are not expert review. Expected polarity remains `unknown`. No independent-human
or universal-security claim is made.

## Original LA-006 failed/blocked attempt (retained history)

The original 2026-09-11 contract required independently reviewed expected
polarity. Independent human security review was not obtained. Evaluation
admission remained blocked. That attempt is retained and is not human gold.

| Field | Value |
| --- | --- |
| History directory | `papers/completion/law_to_action/receipts/snapshots/LA-006/original_failed_blocked_attempt_20260911/` |
| Original receipt | `original_receipt.json` |
| Original criteria | `original_criteria.json` |
| Failure kind | `blocked_missing_independent_human_security_review` |
| Original evaluation admission | `blocked_until_independent_human_security_review` |
| Independently reviewed polarity | not obtained; expected polarity unknown |

Original criteria:

1. Each pair has runnable sandbox reproduction or precisely defined supported behavior evidence and independently reviewed expected polarity.
2. No fabricated fixture CVE or mocked source record enters empirical sample counts.
3. Wildcards, self-granted authority and unsupported transfer remain rejected/unknown with reasons.

The original pair/control envelopes from that blocked attempt remain under
`original_failed_blocked_attempt_20260911/outputs/`. Live pair/control files
are the frozen LA-026 envelopes and are not rewritten.

## Amended automated scope

LA-027/v1 removes the outside-reviewer prerequisite for manuscript generation.
This task reuses the frozen LA-026 source-supported behavior evidence and binds
every reported polarity result to a scoped machine-checkable behavior contract
and an actual observation. Contracts are the compact catalog
`receipts/snapshots/LA-006/polarity_contracts.jsonl`, produced by
`{PRODUCER_ID}` (`{PRODUCER_KIND}`), distinct from
`{EVALUATED_ADAPTER}`. Dataset-derived roles, compiler output, and model
judgment are not evaluation polarity.

## Empirical sample counts

| Population | Count | Notes |
| --- | ---: | --- |
| Frozen CVE families | 12 | LA-004 repository families |
| Empirical pairs | 12 | one vulnerable/fixed pair per family |
| Empirical cases | 24 | reserved case-0 and case-1 identities |
| Fabricated fixture CVE identifiers in empirical counts | 0 | none |
| Mocked source records in empirical counts | 0 | none |
| Fabricated reviewers | 0 | none |
| Control records | 84 | `enters_empirical_sample_count` is false |
| Real unselected or fixed-side controls | 24 | excluded, not empirical samples |
| Synthetic policy-mutation controls | 60 | excluded, not empirical samples |
| Synthetic controls in empirical sample counts | 0 | none |
| Independent expert reviews | 0 | not obtained; not required for this scope |
| Empirical success credits for unsupported transfer | 0 | none |
| Empirical success credits for self-granted authority | 0 | none |
| Polarity results with expected ≠ unknown | 0 | unknown remains unknown |

Hermetic fixture identifiers such as `CVE-2026-0042` from the default CVE e2e
suite are not empirical source-derived cases and are not included.

## Frozen identities and LA-026 behavior evidence

| CVE | Repository | Split | Held-out | Parent | Fix | Vuln files | Fixed files | Failures | CWE |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(rows)}

Twelve planned pair identities and twenty-four planned case IDs from
`benchmark/manifests/splits.json` are present. No family was split across
development/calibration/final. LA-026 recovered both sides of all twelve pairs
with zero failed recovery attempts; the empty failure log is retained. Native
sinks were not executed.

## Polarity contracts and observations

Every reported polarity result binds a scoped machine-checkable behavior
contract and an actual observation.

- Empirical pair sides: the contract is source-difference-at-pinned-revisions.
  The observation is the LA-026 isolated reproduction (recovered file hashes,
  first-parent vulnerable revision, fix commit, source-text difference). That
  observation does **not** support evaluation polarity. Expected polarity is
  `unknown` and is excluded only from the unsupported polarity metric
  denominator, with the recorded reason above.
- Control `expected_status` values `rejected` or `unknown` bind structural
  payload observations (wildcard tokens, self-grant flags, missing transfer
  mapping, real distractor identity, fixed-side hash). They are not allow/deny
  security polarity and receive no empirical success credit.

No Cohen's kappa is computed. No independent-human agreement is claimed.

## Wildcards, self-granted authority, and unsupported transfer

These remain rejected or unknown with reasons. They are control records, not
empirical CVE samples, and receive no empirical success credit.

| Control class | Expected status | Expected polarity | Reason |
| --- | --- | --- | --- |
| `wildcard_scope` | rejected | unknown | `*`, `any`, glob/regex, and generalized scope fail the scoped vocabulary contract |
| `self_granted_authority` | rejected | unknown | Candidates and reviews cannot grant execution authority |
| `unsupported_transfer` | unknown | unknown | No supported mapping onto export_json or another proposed tool |
| `broadened_effects` | rejected | unknown | Catch-all effects are generalization, not a scoped deny candidate |
| `unknown_scope` | unknown | unknown | Incomplete scope is not recoded as allow or deny |
| `misleading_cve_similarity` | unknown | unknown | Real unrelated or same-repo unselected code is not transfer |
| `fixed_negative_control` | unknown | unknown | Dataset-derived negative role is not evaluation polarity or universal security |

## Claim limits

- Dataset-derived polarity is a methodological role, not evaluation polarity.
- Quoted spans ground locator fidelity; they do not certify exploitability.
- Isolated source-difference observation is not native exploit execution.
- Untrusted CVE and upstream source remains untrusted and was not executed.
- A fix for one restriction is not universal security.
- Twelve families from one shard are not worldwide vulnerability coverage.
- The structural validator is provenance checking, not scientific peer review.
- Machine-contract expectations are not independent human gold.
- The original failed/blocked LA-006 attempt and original criteria are retained.
- Independent human security review remains uncollected and is not claimed.

## Binder summary

| Measure | Value |
| --- | ---: |
| Pairs bound | {summary['pairs']} |
| Empirical cases bound | {summary['empirical_cases']} |
| Controls bound | {summary['controls']} |
| Polarity results with bound contracts | {summary['polarity_results_bound']} |
| Expected polarity unknown | {summary['expected_polarity_unknown']} |
| Recovery failures | {summary['recovery_failures']} |
| Empirical success credits granted | {summary['empirical_success_credits']} |
"""
    LIVE_REVIEW.parent.mkdir(parents=True, exist_ok=True)
    LIVE_REVIEW.write_text(text, encoding="utf-8")
    review_snap = SNAP_OUT / "annotations/cve_review.md"
    review_snap.parent.mkdir(parents=True, exist_ok=True)
    review_snap.write_text(text, encoding="utf-8")


def main() -> int:
    hashes = retain_envelopes()
    pairs = load_jsonl(LIVE_PAIRS)
    controls = load_jsonl(LIVE_CONTROLS)
    if len(pairs) != 12 or len(controls) != 84:
        raise SystemExit(f"frozen counts changed: {len(pairs)} pairs, {len(controls)} controls")
    machine_cases = {
        row["case_id"]: row
        for row in load_json(ANNOT / "automated_reference_manifest.json")["cases"]
        if row.get("population") == "cve"
    }
    if len(machine_cases) != 24:
        raise SystemExit(f"expected 24 LA-027 CVE machine cases, found {len(machine_cases)}")
    results = []
    for pair in pairs:
        cve_id = pair["source"]["cve_id"]
        if cve_id in FORBIDDEN_FIXTURE_CVES:
            raise SystemExit(f"fixture CVE {cve_id} entered empirical counts")
        observation = pair_observation(pair)
        if observation["source_difference_observed"] is not True:
            raise SystemExit(f"{cve_id} missing LA-026 source-difference observation")
        for role in ("vulnerable", "fixed"):
            side = pair["sides"][role]
            case_id = side["case_id"]
            machine = machine_cases[case_id]
            if machine.get("policy_polarity") != "unknown":
                raise SystemExit(f"{case_id} LA-027 policy polarity is not unknown")
            if side.get("polarity", {}).get("expected") != "unknown":
                raise SystemExit(f"{case_id} envelope polarity is not unknown")
            body = contract(
                "source_difference_at_pinned_revisions",
                observation,
                case_id,
                polarity_supported=False,
                status_supported=None,
                denom=DENOM_PAIR,
            )
            body["la026_task"] = "LA-026"
            body["la027_checked_property"] = machine["checked_property"]
            body["la027_policy_polarity"] = machine["policy_polarity"]
            body["role"] = role
            results.append(
                polarity_result(
                    "pair_side",
                    case_id,
                    body,
                    {
                        "cve_id": cve_id,
                        "dataset_derived": side["polarity"]["dataset_derived"],
                        "envelope_path": "papers/completion/law_to_action/benchmark/cases/cve_pairs.jsonl",
                        "pair_id": pair["pair_id"],
                        "role": role,
                        "source_id": pair["source_id"],
                    },
                )
            )
    parents = {row["source_id"]: row for row in pairs}
    for row in controls:
        cls = row["control_class"]
        if cls not in REQUIRED_CONTROLS:
            raise SystemExit(f"{row['control_id']} unknown class")
        expected_status = "rejected" if cls in REJECTED_CONTROLS else "unknown"
        if row.get("expected_status") != expected_status:
            raise SystemExit(f"{row['control_id']} status {row.get('expected_status')!r}")
        if row.get("expected_polarity") != "unknown":
            raise SystemExit(f"{row['control_id']} forced expected polarity")
        parent = parents[row["parent_source_id"]]
        observation, checked, status_supported = control_observation(row, parent)
        if not status_supported:
            raise SystemExit(f"{row['control_id']} observation does not support recorded status")
        body = contract(
            checked,
            observation,
            row["control_id"],
            polarity_supported=False,
            status_supported=True,
            denom=DENOM[cls],
        )
        body["control_class"] = cls
        results.append(
            polarity_result(
                "control",
                row["control_id"],
                body,
                {
                    "control_class": cls,
                    "envelope_path": "papers/completion/law_to_action/benchmark/cases/cve_controls.jsonl",
                    "expected_status": expected_status,
                    "parent_source_id": row["parent_source_id"],
                },
            )
        )
    if len(results) != 108:
        raise SystemExit(f"expected 108 polarity results, found {len(results)}")
    dump_jsonl(CONTRACTS, results)
    summary = {
        "controls": 84,
        "empirical_cases": 24,
        "empirical_success_credits": 0,
        "envelope_sha256": hashes,
        "expected_polarity_unknown": 108,
        "la026_controls_sha256": hashes["la026/cve_controls.jsonl"],
        "la026_pairs_sha256": hashes["la026/cve_pairs.jsonl"],
        "original_failed_history": str(HIST.relative_to(ROOT)),
        "pairs": 12,
        "polarity_catalog": str(CONTRACTS.relative_to(ROOT)),
        "polarity_results_bound": 108,
        "producer": producer(),
        "recovery_failures": 0,
        "schema": "law-to-action-la006-automated-scope-bind/v1",
    }
    write_review(pairs, summary)
    dump_json(SNAP / "bind_summary.json", summary)
    dump_json(
        HIST / "original_outputs_manifest.json",
        {
            "live_envelopes_are_la026": True,
            "note": "Original blocked envelopes are retained under original_failed_blocked_attempt_20260911/outputs/. Live pair/control files remain the frozen LA-026 bytes.",
            "original_controls_sha256": hashes.get("original/cve_controls.jsonl"),
            "original_pairs_sha256": hashes.get("original/cve_pairs.jsonl"),
            "schema": "law-to-action-la006-original-outputs/v1",
            "task_id": "LA-006",
        },
    )
    dump_json(
        SNAP / "review_status.json",
        {
            "adjudication_status": "automated_scope_complete_human_gold_uncollected",
            "agreement": "not_applicable_no_independent_reviewer",
            "amendment": "LA-027/v1",
            "claims_narrowed": True,
            "control_records": 84,
            "dataset_derived_roles_recorded": True,
            "disagreement_records": 0,
            "empirical_cases": 24,
            "empirical_pairs": 12,
            "empirical_success_credits": 0,
            "evaluation_admission": "automated_scope_source_supported_evidence_complete_polarity_unknown",
            "expected_polarity": "unknown",
            "fabricated_reviewers": 0,
            "final_adjudication": None,
            "fixture_cves_in_empirical_counts": 0,
            "forced_permission_or_denial": False,
            "generated_labels_are_expert_review": False,
            "independent_human_security_review": "not_obtained",
            "limitation": "This status object is automated-scope provenance. It is not independent expert review.",
            "mocked_source_records_in_empirical_counts": 0,
            "original_failed_history_retained": True,
            "packet_preparation": "complete",
            "polarity_catalog": str(CONTRACTS.relative_to(ROOT)),
            "required_control_classes_present": sorted(REQUIRED_CONTROLS),
            "sandbox_reproduction": "not_run_untrusted_source_not_executed",
            "schema": "law-to-action-cve-review-status/v2",
            "task_id": "LA-006",
            "untrusted_source_executed": False,
            "visible_unresolved": True,
        },
    )
    json.dump(
        {
            "controls": 84,
            "empirical_cases": 24,
            "empirical_success_credits": 0,
            "expected_polarity_unknown": 108,
            "original_failed_history_retained": True,
            "pairs": 12,
            "polarity_results_bound": 108,
            "status": "bound",
        },
        sys.stdout,
        indent=2,
        sort_keys=True,
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
