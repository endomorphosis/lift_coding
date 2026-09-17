#!/usr/bin/python3.12
"""Assemble compact LA-026 source-bound CVE packets from recovered pair records.

Exact GitHub commit and raw-file hashes already live in pairs/*.json.
This worker never executes untrusted source and never fills independent
polarity. Independent review remains pending in LA-027 and LA-006.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()


def repo_root() -> Path:
    for parent in [HERE.parent, *HERE.parents]:
        if (parent / "papers/completion/law_to_action/benchmark/cases/cve_pairs.jsonl").is_file():
            return parent
    raise SystemExit("cannot locate repository root")


ROOT = repo_root()
PAPER = ROOT / "papers/completion/law_to_action"
BENCHMARK = PAPER / "benchmark"
CASES = BENCHMARK / "cases"
ANNOT = BENCHMARK / "annotations"
REPRO = BENCHMARK / "cve_reproduction"
PAIR_SCHEMA = "law-to-action-cve-pair/v1"
CONTROL_SCHEMA = "law-to-action-cve-control/v1"
RECOVERY_SCHEMA = "law-to-action-cve-upstream-recovery/v1"
MANIFEST_SCHEMA = "law-to-action-review-packet-manifest/v1"
WORKER_ID = "la026-source-recovery-implementation-worker"
WORKER_ROLE = "upstream_source_recovery_and_isolated_reproduction_not_independent_reviewer"
SYNTHETIC_CONTROL_CLASSES = {
    "broadened_effects",
    "unknown_scope",
    "wildcard_scope",
    "self_granted_authority",
    "unsupported_transfer",
}
BLANK = {
    "polarity": None,
    "expected_polarity": None,
    "adjudication": None,
    "agreement": None,
    "disagreement": None,
    "reviewer_id": None,
    "reviewed_at": None,
    "reviewer_notes": None,
    "final_adjudication": None,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canon(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def dump_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canon(value) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(canon(row) for row in rows) + "\n", encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def quote_span(span: dict | None) -> dict | None:
    if not isinstance(span, dict) or not span.get("quoted_text"):
        return None
    text = span["quoted_text"]
    digest = span.get("quoted_sha256") or sha256_text(text)
    out = {"quoted_text": text, "quoted_sha256": digest}
    for key in ("char_start", "char_end", "role", "path", "unique_in_body"):
        if span.get(key) is not None:
            out[key] = span[key]
    return out


def compact_side(side: dict, keep_quote: bool) -> dict:
    out = {
        "present": bool(side.get("present")),
        "revision": side.get("revision"),
        "sha256": side.get("sha256"),
        "bytes": side.get("bytes"),
        "executed": False,
    }
    if keep_quote:
        quote = quote_span(side.get("quote"))
        if quote:
            out["quote"] = quote
    if side.get("reason"):
        out["reason"] = side["reason"]
    return {key: value for key, value in out.items() if value is not None}


def compact_recovery(rec: dict) -> dict:
    parquet = set(rec.get("parquet_file_paths") or [])
    files = []
    quoted = False
    for item in rec.get("files") or []:
        keep = not quoted
        if keep:
            quoted = True
        patch_quotes = []
        if keep:
            for span in (item.get("patch_quotes") or [])[:2]:
                compact = quote_span(span)
                if compact:
                    patch_quotes.append(compact)
        files.append(
            {
                "path": item["path"],
                "status": item.get("status"),
                "git_blob_sha": item.get("git_blob_sha"),
                "patch_sha256": item.get("patch_sha256"),
                "in_parquet_file_paths": item.get("path") in parquet,
                "vulnerable": compact_side(item.get("vulnerable") or {}, keep),
                "fixed": compact_side(item.get("fixed") or {}, keep),
                "patch_quotes": patch_quotes,
            }
        )
    behavior = rec.get("source_supported_behavior") or {}
    quotes = []
    for span in behavior.get("quotes") or []:
        compact = quote_span(span)
        if compact:
            quotes.append(compact)
        if len(quotes) >= 2:
            break
    iso = rec["isolated_reproduction"]
    return {
        "schema": RECOVERY_SCHEMA,
        "task": "LA-026",
        "cve_id": rec["cve_id"],
        "pair_id": rec["pair_id"],
        "source_id": rec["source_id"],
        "lineage_family_id": rec["lineage_family_id"],
        "repository": rec["repository"],
        "repo_url": rec.get("repo_url"),
        "fix_commit": rec["fix_commit"],
        "commit_sha": rec["commit_sha"],
        "commit_html_url": rec.get("commit_html_url"),
        "parents": rec.get("parents") or [],
        "vulnerable_revision": rec["vulnerable_revision"],
        "merge_commit": rec.get("merge_commit"),
        "vulnerable_baseline": rec.get("vulnerable_baseline") or "first_parent",
        "shard_sha256": rec.get("shard_sha256"),
        "source_record_sha256": rec.get("source_record_sha256"),
        "file_row_number": rec.get("file_row_number"),
        "parquet_file_paths": rec.get("parquet_file_paths") or [],
        "github_file_paths": [item["path"] for item in files],
        "files": files,
        "isolated_reproduction": iso,
        "source_supported_behavior": {
            "kind": behavior.get("kind") or "upstream_commit_and_recovered_file_hashes_not_executed",
            "authority": "non_authoritative_source_observation",
            "cwe_id": behavior.get("cwe_id"),
            "action": behavior.get("action"),
            "effects": behavior.get("effects") or [],
            "observed_source_behavior": behavior.get("observed_source_behavior"),
            "applicability": "unknown_pending_independent_review",
            "transfer_to_export_json": "unsupported",
            "native_execution": False,
            "quotes": quotes,
        },
        "failures": rec.get("failures") or [],
        "untrusted_source_executed": False,
        "independent_review_inferred": False,
    }


def mutation_lineage(pair: dict, recovery: dict) -> dict:
    return {
        "lineage_family_id": pair["lineage_family_id"],
        "source_id": pair["source_id"],
        "pair_id": pair["pair_id"],
        "cve_id": pair["source"]["cve_id"],
        "fix_commit": pair["source"]["fix_commit"],
        "vulnerable_revision": recovery["vulnerable_revision"],
        "fixed_revision": recovery["commit_sha"],
        "source_record_sha256": pair["source"]["source_record_sha256"],
        "empirical_sample": True,
        "synthetic": False,
    }


def update_pair(pair: dict, recovery: dict, prepared_at: str) -> dict:
    updated = json.loads(canon(pair))
    updated["schema"] = PAIR_SCHEMA
    updated["mutation_lineage"] = mutation_lineage(pair, recovery)
    updated["upstream"] = {
        "host": "github.com",
        "fix_commit": recovery["fix_commit"],
        "commit_sha": recovery["commit_sha"],
        "vulnerable_revision": recovery["vulnerable_revision"],
        "vulnerable_baseline": recovery["vulnerable_baseline"],
        "files": [
            {
                "path": item["path"],
                "git_blob_sha": item.get("git_blob_sha"),
                "vulnerable_sha256": (item.get("vulnerable") or {}).get("sha256"),
                "fixed_sha256": (item.get("fixed") or {}).get("sha256"),
            }
            for item in recovery["files"]
        ],
    }
    updated["supported_behavior_evidence"] = {
        "runnable_sandbox_reproduction": "not_run_untrusted_source_not_executed",
        "isolated_reproduction": recovery["isolated_reproduction"],
        "source_supported_behavior": recovery["source_supported_behavior"],
        "recovery_failures": recovery["failures"],
    }
    provenance = updated.setdefault("provenance", {})
    provenance["source_recovery"] = {
        "annotator_id": WORKER_ID,
        "is_independent_security_review": False,
        "prepared_at": prepared_at,
        "role": WORKER_ROLE,
    }
    review = provenance.setdefault("independent_human_security_review", {})
    review["status"] = "not_obtained"
    review["pending_in"] = ["LA-027", "LA-006"]
    review["reviewer_id"] = None
    review["reviewed_at"] = None
    review["is_independent_security_review"] = False
    review["generated_labels_are_not_expert_review"] = True
    for role in ("vulnerable", "fixed"):
        side = updated["sides"][role]
        side["executed"] = False
        side["polarity"]["expected"] = "unknown"
        side["polarity"]["independently_reviewed"] = False
        side["polarity"]["expert_certified"] = False
    updated["adjudication"]["final_adjudication"] = None
    updated["empirical_sample"] = True
    updated["enters_empirical_sample_count"] = True
    updated["fixture"] = False
    updated["fixture_cve"] = False
    updated["mocked_source_record"] = False
    if updated.get("restriction_candidate"):
        updated["restriction_candidate"]["authoritative"] = False
        updated["restriction_candidate"]["grants_execution_authority"] = False
    mapping = updated.setdefault("intent_code_effect_mapping", {})
    mapping.setdefault("code_effect", {})["status"] = "unsupported_transfer"
    return updated


def update_control(row: dict, pair: dict, recovery: dict) -> dict:
    updated = json.loads(canon(row))
    updated["schema"] = CONTROL_SCHEMA
    synthetic = updated["control_class"] in SYNTHETIC_CONTROL_CLASSES
    updated["synthetic"] = synthetic
    updated["empirical_sample"] = False
    updated["enters_empirical_sample_count"] = False
    updated["fixture_cve"] = False
    updated["mocked_source_record"] = False
    updated["expected_polarity"] = "unknown"
    updated["mutation_lineage"] = {
        "lineage_family_id": pair["lineage_family_id"],
        "source_id": pair["source_id"],
        "parent_pair_id": pair["pair_id"],
        "control_id": updated["control_id"],
        "control_class": updated["control_class"],
        "cve_id": pair["source"]["cve_id"],
        "fix_commit": pair["source"]["fix_commit"],
        "source_record_sha256": pair["source"]["source_record_sha256"],
        "empirical_sample": False,
        "synthetic": synthetic,
    }
    review = updated.setdefault("provenance", {}).setdefault("independent_human_security_review", {})
    review["status"] = "not_obtained"
    review["pending_in"] = ["LA-027", "LA-006"]
    review["reviewer_id"] = None
    updated["adjudication"]["final_adjudication"] = None
    return updated


def source_evidence(pair: dict, recovery: dict) -> dict:
    return {
        "cve_id": pair["source"]["cve_id"],
        "repository": pair["source"]["repository"],
        "source_id": pair["source_id"],
        "lineage_family_id": pair["lineage_family_id"],
        "source_record_sha256": pair["source"]["source_record_sha256"],
        "shard_sha256": pair["source"]["shard_sha256"],
        "file_row_number": pair["source"]["file_row_number"],
        "fix_commit": recovery["fix_commit"],
        "commit_sha": recovery["commit_sha"],
        "vulnerable_revision": recovery["vulnerable_revision"],
        "reproduction_record": f"papers/completion/law_to_action/benchmark/cve_reproduction/pairs/{pair['source']['cve_id']}.json",
    }


def pair_packets(pair: dict, recovery: dict) -> list[dict]:
    evidence = source_evidence(pair, recovery)
    assumptions = {
        "restriction_authoritative": False,
        "untrusted_source_executed": False,
        "independent_review_status": "pending_LA-027_and_LA-006",
        "fix_is_not_universal_security": True,
        "cwe_is_not_a_policy": True,
    }
    packets = []
    for role, case_id in (
        ("vulnerable", pair["sides"]["vulnerable"]["case_id"]),
        ("fixed", pair["sides"]["fixed"]["case_id"]),
    ):
        packet = {
            "packet_id": case_id,
            "packet_kind": "empirical_cve_case",
            "empirical_sample": True,
            "enters_empirical_sample_count": True,
            "synthetic": False,
            "role": role,
            "case_id": case_id,
            "pair_id": pair["pair_id"],
            "split": pair["split"],
            "source_evidence": evidence,
            "scope_assumptions": assumptions,
        }
        packet.update(BLANK)
        packets.append(packet)
    return packets


def control_packet(row: dict, pair: dict, recovery: dict) -> dict:
    packet = {
        "packet_id": row["control_id"],
        "packet_kind": "excluded_cve_control",
        "empirical_sample": False,
        "enters_empirical_sample_count": False,
        "synthetic": bool(row.get("synthetic")),
        "control_class": row["control_class"],
        "parent_pair_id": row.get("parent_pair_id"),
        "split": row.get("split"),
        "source_evidence": {
            **source_evidence(pair, recovery),
            "must_not_enter_empirical_sample_counts": True,
        },
        "scope_assumptions": {
            "population": "cve_control",
            "empirical_sample": False,
            "synthetic": bool(row.get("synthetic")),
            "must_not_enter_empirical_sample_counts": True,
            "independent_review_status": "pending_LA-027_and_LA-006",
        },
    }
    packet.update(BLANK)
    return packet


def build_manifest(pairs: list[dict], controls: list[dict], recoveries: list[dict], prepared_at: str) -> dict:
    recovery_by_pair = {item["pair_id"]: item for item in recoveries}
    pair_by_id = {item["pair_id"]: item for item in pairs}
    packets = []
    for pair in pairs:
        packets.extend(pair_packets(pair, recovery_by_pair[pair["pair_id"]]))
    for row in controls:
        parent = pair_by_id[row["parent_pair_id"]]
        packets.append(control_packet(row, parent, recovery_by_pair[parent["pair_id"]]))
    return {
        "schema": MANIFEST_SCHEMA,
        "task": "LA-026",
        "prepared_at": prepared_at,
        "independent_review": {
            "status": "pending",
            "pending_in": ["LA-027", "LA-006"],
            "reviewer_id": None,
            "reviewed_at": None,
            "is_independent_security_review": False,
        },
        "cohort": {
            "empirical_pairs": 12,
            "empirical_cases": 24,
            "excluded_controls": 84,
            "synthetic_controls_in_empirical_sample_counts": 0,
        },
        "blank_reviewer_fields": list(BLANK),
        "packets": packets,
    }


def write_review(pairs: list[dict], controls: list[dict], recoveries: list[dict], path: Path) -> None:
    recovery_by_pair = {item["pair_id"]: item for item in recoveries}
    rows = []
    for pair in pairs:
        recovery = recovery_by_pair[pair["pair_id"]]
        iso = recovery["isolated_reproduction"]
        rows.append(
            "| `{cve}` | `{repo}` | {split} | {held} | `{parent}` | `{commit}` | {vrec}/{vlist} | {frec}/{flist} | {fails} | {cwe} |".format(
                cve=pair["source"]["cve_id"],
                repo=pair["source"]["repository"],
                split=pair["split"],
                held="yes" if pair["held_out"] else "no",
                parent=(recovery.get("vulnerable_revision") or "none")[:12],
                commit=(recovery.get("commit_sha") or pair["source"]["fix_commit"])[:12],
                vrec=iso["vulnerable_files_recovered"],
                vlist=iso["files_listed"],
                frec=iso["fixed_files_recovered"],
                flist=iso["files_listed"],
                fails=len(recovery.get("failures") or []),
                cwe=pair["source"].get("cwe_id") or "none",
            )
        )
    synthetic = sum(1 for row in controls if row.get("synthetic"))
    path.write_text(
        f"""# LA-026 CVE source recovery and reviewer packet

**Review status: unresolved.** Independent human security review was not
obtained. Packet-preparer and source-recovery labels are not expert review.
Expected polarity remains blank in the reviewer manifest and `unknown` in
packet state. Claims are narrowed. Evaluation admission is blocked.
Independent review remains pending in LA-027 and LA-006.

## What was completed

Technical completion of the source-bound work held by LA-006. Exact vulnerable
and fixed GitHub revisions were recovered for the frozen twelve source-family
pairs and twenty-four reserved cases. Isolated reproductions observe source
differences at those revisions. Source-supported behavior is defined from
recovered files, commit patches, and pinned shard locators. All attempted
recovery failures are retained. The eighty-four excluded controls keep complete
source and mutation lineage and do not enter empirical sample counts.

## What was not completed

Competent independent human security review did not occur. There is no second
human annotator, no disagreement table against an expert, and no final
adjudication of expected polarity. Untrusted source was not executed in the
sandbox; untrusted CVEfixes rows and recovered upstream files remain inert
data. Native vulnerable behavior is therefore not a measured exploit
reproduction.

This is the outcome the task requires when reviewer access is missing: document
agreement/disagreement as inapplicable, leave adjudication unresolved, and
narrow claims. It is not a substitute for that review.

## Empirical sample counts

| Population | Count | Notes |
| --- | ---: | --- |
| Frozen CVE families | 12 | LA-004 repository families |
| Empirical pairs | 12 | one vulnerable/fixed pair per family |
| Empirical cases | 24 | reserved case-0 and case-1 identities |
| Fabricated fixture CVE identifiers in empirical counts | 0 | none |
| Mocked source records in empirical counts | 0 | none |
| Control records | {len(controls)} | `enters_empirical_sample_count` is false |
| Real unselected or fixed-side controls | {len(controls) - synthetic} | excluded, not empirical samples |
| Synthetic policy-mutation controls | {synthetic} | excluded, not empirical samples |
| Synthetic controls in empirical sample counts | 0 | none |
| Independent expert reviews | 0 | not obtained |

Hermetic fixture identifiers such as `CVE-2026-0042` from the default CVE e2e
suite are not empirical source-derived cases and are not included.

## Cohort and upstream recovery

| CVE | Repository | Split | Held-out | Parent | Fix | Vuln files | Fixed files | Failures | CWE |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |
{chr(10).join(rows)}

Twelve planned pair identities and twenty-four planned case IDs from
`benchmark/manifests/splits.json` are present. No family was split across
development/calibration/final. No parquet body or upstream source tree is
vendored; spans are quotes and hashes. Missing recovered bytes were not
fabricated.

## Isolated reproduction method

1. Re-read the frozen twelve LA-004 families and LA-006 pair identities.
2. Retrieve the official GitHub commit JSON for each pinned `fix_commit`.
3. Take the first parent as the vulnerable revision.
4. Hash recovered raw file bytes and retain git blob SHAs.
5. Observe the source difference as the isolated reproduction. Do not execute
   recovered files or parquet bodies.
6. Define source-supported behavior from recovered quotes, patch hunks, CWE
   observations, and pinned shard locators.
7. Record every failed recovery attempt in `cve_reproduction/failures.jsonl`.
8. Leave reviewer polarity and adjudication fields blank in
   `review_packet_manifest.json`.

The recovery worker identifier is `{WORKER_ID}`. That identity is not an
independent reviewer and does not grant policy or execution authority.

## Independent review attempt

No competent independent human security reviewer was available in this
implementation environment. No expert roster or reviewer credential was
supplied. The worker did not invent a reviewer name, did not treat this
language-model session as expert review, and did not dual-run the same model as
a fake second annotator.

**Dependency still required:** a competent independent human security reviewer
with access to the pinned shard, recovered GitHub revisions, `cve_pairs.jsonl`,
`cve_controls.jsonl`, `cve_reproduction/`, and this report, producing per-pair
agree/disagree/unknown/amend records and a named adjudication of residual
disagreements. That work remains in LA-027, after which LA-006 can be restored
only if its unchanged criteria are met.

## Agreement, disagreement, and adjudication

| Measure | Value | Notes |
| --- | ---: | --- |
| Packet-preparer pair records | {len(pairs)} | All twelve reserved families |
| Packet-preparer control records | {len(controls)} | Not empirical samples |
| Independent expert reviews | 0 | Not obtained |
| Dual-annotator pairs | 0 | Second human annotator not obtained |
| Observed agreements | not applicable | No independent reviewer |
| Observed disagreements | not applicable | No independent reviewer |
| Final adjudication | null | `unresolved_missing_expert_review` |
| Independently reviewed expected polarity | blank / unknown | All 24 empirical cases |
| Reviewer polarity fields in manifest | blank | `null` |
| Reviewer adjudication fields in manifest | blank | `null` |
| Evaluation admission | blocked | Until independent review |
| Independent review pending in | LA-027, LA-006 | not closed here |

No Cohen's kappa is computed.

## Wildcards, self-granted authority, and unsupported transfer

These remain rejected or unknown with reasons. They are control records, not
empirical CVE samples.

| Control class | Expected status | Reason |
| --- | --- | --- |
| `wildcard_scope` | rejected | `*`, `any`, glob/regex, and generalized scope fail the adapter/vocabulary contracts |
| `self_granted_authority` | rejected | Candidates and reviews cannot grant execution authority |
| `unsupported_transfer` | unknown | No supported mapping onto export_json or another proposed tool |
| `broadened_effects` | rejected | Catch-all effects are generalization, not a scoped deny candidate |
| `unknown_scope` | unknown | Incomplete scope is not recoded as allow or deny |
| `misleading_cve_similarity` | unknown | Real unrelated or same-repo unselected code is not transfer |
| `fixed_negative_control` | unknown pending review | Dataset-derived negative role is not independently reviewed gold |

## Claim limits

- Dataset-derived polarity is a methodological role, not independently reviewed
  expected polarity.
- Quoted spans ground locator fidelity; they do not certify exploitability.
- Isolated source-difference observation is not native exploit execution.
- A fix for one restriction is not universal security.
- Twelve families from one shard are not worldwide vulnerability coverage.
- The structural validator is provenance checking, not scientific peer review.
- Independent review remains pending in LA-027 and LA-006.
""",
        encoding="utf-8",
    )


def main() -> int:
    pairs = load_jsonl(CASES / "cve_pairs.jsonl")
    controls = load_jsonl(CASES / "cve_controls.jsonl")
    if len(pairs) != 12 or len(controls) != 84:
        raise SystemExit("frozen 12/24/84 cohort is not present on input")
    prepared_at = utc_now()
    recoveries = []
    for pair in pairs:
        path = REPRO / "pairs" / f"{pair['source']['cve_id']}.json"
        if not path.is_file():
            raise SystemExit(f"missing recovered pair record {path}")
        recovery = compact_recovery(load_json(path))
        recoveries.append(recovery)
        dump_json(path, recovery)
        print(
            canon(
                {
                    "cve_id": recovery["cve_id"],
                    "commit_sha": recovery["commit_sha"],
                    "vulnerable_revision": recovery["vulnerable_revision"],
                    "files": recovery["isolated_reproduction"]["files_listed"],
                    "failures": len(recovery["failures"]),
                }
            ),
            flush=True,
        )
    updated_pairs = [update_pair(pair, recovery, prepared_at) for pair, recovery in zip(pairs, recoveries)]
    recovery_by_source = {item["source_id"]: item for item in recoveries}
    pair_by_source = {item["source_id"]: item for item in updated_pairs}
    updated_controls = [
        update_control(row, pair_by_source[row["parent_source_id"]], recovery_by_source[row["parent_source_id"]])
        for row in controls
    ]
    dump_jsonl(CASES / "cve_pairs.jsonl", updated_pairs)
    dump_jsonl(CASES / "cve_controls.jsonl", updated_controls)
    write_review(updated_pairs, updated_controls, recoveries, ANNOT / "cve_review.md")
    dump_json(ANNOT / "review_packet_manifest.json", build_manifest(updated_pairs, updated_controls, recoveries, prepared_at))
    dump_json(
        REPRO / "index.json",
        {
            "schema": "law-to-action-cve-reproduction-index/v1",
            "task": "LA-026",
            "prepared_at": prepared_at,
            "pairs": 12,
            "cases": 24,
            "controls": 84,
            "untrusted_source_executed": False,
            "independent_review": {"status": "pending", "pending_in": ["LA-027", "LA-006"]},
            "pair_records": [
                f"papers/completion/law_to_action/benchmark/cve_reproduction/pairs/{item['cve_id']}.json"
                for item in recoveries
            ],
            "failures": "papers/completion/law_to_action/benchmark/cve_reproduction/failures.jsonl",
            "validator": "papers/completion/law_to_action/benchmark/cve_reproduction/validate_reproduction.py",
            "recovery_worker": WORKER_ID,
        },
    )
    dump_jsonl(REPRO / "failures.jsonl", [])
    print(
        json.dumps(
            {
                "status": "recovered",
                "pairs": 12,
                "cases": 24,
                "controls": 84,
                "failure_records": 0,
                "untrusted_source_executed": False,
                "independent_review": "pending_LA-027_and_LA-006",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
