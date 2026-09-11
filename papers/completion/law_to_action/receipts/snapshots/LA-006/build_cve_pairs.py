#!/usr/bin/python3.12
"""Build LA-006 CVE pairs and non-empirical controls from pinned row evidence.

Packet preparation only. Independent human security review is not performed
and must not be reported as obtained. Dataset-derived vulnerable/fixed roles
are not independently reviewed expected polarity. Untrusted source is never
executed. Fabricated fixture CVE identifiers and mocked source records are
excluded from empirical sample counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
BENCHMARK = ROOT / "papers/completion/law_to_action/benchmark"
CASES = BENCHMARK / "cases"
ANNOT = BENCHMARK / "annotations"
SOURCES = BENCHMARK / "manifests/sources.json"
SPLITS = BENCHMARK / "manifests/splits.json"
EVIDENCE_DEFAULT = Path(__file__).resolve().parent / "row_evidence.json"
PAIR_SCHEMA = "law-to-action-cve-pair/v1"
CONTROL_SCHEMA = "law-to-action-cve-control/v1"
PREPARER_ID = "la006-packet-preparer-implementation-worker"
PREPARER_ROLE = (
    "autonomous_annotation_packet_preparer_not_independent_security_reviewer"
)
VOCAB = "security.cvefixes/v1"
LANGUAGE_MAP = {
    "C": "c",
    "C++": "cpp",
    "Go": "go",
    "JavaScript": "javascript",
    "PHP": "php",
    "Python": "python",
    "Ruby": "ruby",
    "TypeScript": "typescript",
}
CWE_MAP = {
    "CWE-22": {
        "action": "construct_path_from_untrusted_input",
        "preconditions": ["attacker_controls_path", "missing_canonicalization"],
        "effects": ["read_outside_allowed_root"],
        "mitigations": ["canonicalize_and_confine"],
        "scope": "filesystem",
        "confidence": "packet_preparer_cwe_table",
    },
    "CWE-59": {
        "action": "construct_path_from_untrusted_input",
        "preconditions": ["attacker_controls_path", "missing_canonicalization"],
        "effects": ["write_outside_allowed_root"],
        "mitigations": ["canonicalize_and_confine"],
        "scope": "filesystem",
        "confidence": "packet_preparer_cwe_table",
    },
    "CWE-79": {
        "action": "render_untrusted_output",
        "preconditions": ["missing_output_encoding", "untrusted_input_reaches_sink"],
        "effects": ["cross_site_scripting"],
        "mitigations": ["encode_output"],
        "scope": "web",
        "confidence": "packet_preparer_cwe_table",
    },
    "CWE-835": {
        "action": "parse_untrusted_input",
        "preconditions": ["missing_input_validation"],
        "effects": ["denial_of_service"],
        "mitigations": ["apply_resource_limits"],
        "scope": "resource",
        "confidence": "packet_preparer_uncertain",
    },
    "CWE-863": {
        "action": "perform_privileged_operation",
        "preconditions": ["missing_authorization"],
        "effects": ["authorization_bypass"],
        "mitigations": ["enforce_authorization"],
        "scope": "authorization",
        "confidence": "packet_preparer_uncertain",
    },
    "CWE-918": {
        "action": "follow_untrusted_redirect",
        "preconditions": ["untrusted_input_reaches_sink"],
        "effects": ["server_side_request_forgery"],
        "mitigations": ["restrict_network_destinations"],
        "scope": "network",
        "confidence": "packet_preparer_cwe_table",
    },
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        for row in rows
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def provenance(prepared_at: str) -> dict:
    return {
        "packet_preparer": {
            "annotator_id": PREPARER_ID,
            "independence": "same implementation worker that prepared all packets; not an independent second annotator",
            "is_independent_security_review": False,
            "prepared_at": prepared_at,
            "role": PREPARER_ROLE,
        },
        "independent_human_security_review": {
            "dependency": "Competent independent human security reviewer with access to the pinned first CVEfixes shard, these packets, and the quoted spans.",
            "generated_labels_are_not_expert_review": True,
            "is_expert_security_review": False,
            "is_independent_security_review": False,
            "reviewed_at": None,
            "reviewer_credentials": None,
            "reviewer_id": None,
            "status": "not_obtained",
        },
        "second_independent_annotator": {
            "note": "No second human annotator was available. Dual-annotator agreement is not computed.",
            "status": "not_obtained",
        },
    }


def adjudication() -> dict:
    return {
        "agreement": "not_applicable_no_independent_reviewer",
        "claims_narrowed": True,
        "disagreement_records": [],
        "evaluation_admission": "blocked_until_independent_human_security_review",
        "final_adjudication": None,
        "status": "unresolved_missing_expert_review",
        "visible_unresolved": True,
    }


def polarity(dataset_role: str, *, evidence_gap: bool) -> dict:
    return {
        "authority_of_label": "dataset_derived_candidate_not_independently_reviewed",
        "dataset_derived": dataset_role,
        "evidence_gap": evidence_gap,
        "expected": "unknown",
        "expert_certified": False,
        "independently_reviewed": False,
        "label_set": ["vulnerable_positive", "fixed_negative", "unknown"],
        "reason": (
            "CVEfixes assigns vulnerable/fixed methodological roles. Independent "
            "review of expected polarity was not obtained, so evaluation polarity "
            "remains unknown rather than a forced gold label."
        ),
    }


def limitations() -> list[str]:
    return [
        "Packet-preparer field extraction is not independent human security review.",
        "Dataset-derived vulnerable/fixed roles are not independently reviewed expected polarity.",
        "Untrusted CVE source was not executed; there is no sandbox reproduction of native sinks.",
        "A fix for one scoped restriction is not universal security.",
        "CVE or CWE identifiers are classifications, not policies or execution authority.",
        "Transfer onto the qualified export_json sandbox handler is unsupported without an explicit supported behavior model.",
        "Evaluation admission remains blocked until competent independent review and adjudication.",
        "Twelve repository families from one shard are not the full CVEfixes release.",
    ]


def language_term(raw: str | None) -> dict:
    mapped = LANGUAGE_MAP.get(raw or "")
    if mapped is None:
        return {
            "canonical": None,
            "source_language": raw,
            "status": "unknown",
            "reason": "Source language is absent or outside the CVEfixes v1 language registry.",
        }
    return {
        "canonical": f"{VOCAB}/language/{mapped}",
        "name": mapped,
        "source_language": raw,
        "status": "source_attested",
    }


def restriction_candidate(row: dict) -> dict:
    cwe = row.get("cwe_id")
    mapped = CWE_MAP.get(cwe) if isinstance(cwe, str) else None
    language = language_term(row.get("language"))
    body_gap = not row["vulnerable"]["present"] and not row["fixed"]["present"]
    if mapped is None or body_gap or cwe in {"CWE-264"}:
        return {
            "authoritative": False,
            "cve_ids": [row["cve_id"]],
            "cwe_ids": [cwe] if cwe else [],
            "grants_execution_authority": False,
            "language": language,
            "mapping_status": "unknown",
            "reason": (
                "No exact scoped deny candidate is admitted. Missing code bodies, "
                "an unmapped or overly generic CWE, or absent independent review "
                "leave the restriction unknown rather than generalized."
            ),
            "status": "unknown",
            "wildcard": False,
        }
    return {
        "action": f"{VOCAB}/action/{mapped['action']}",
        "authoritative": False,
        "confidence": mapped["confidence"],
        "cve_ids": [row["cve_id"]],
        "cwe_ids": [cwe],
        "effects": [f"{VOCAB}/effect/{name}" for name in mapped["effects"]],
        "grants_execution_authority": False,
        "language": language,
        "mapping_status": "packet_preparer_non_authoritative_candidate",
        "mitigations": [f"{VOCAB}/mitigation/{name}" for name in mapped["mitigations"]],
        "note": "A mitigation that removes one unsafe data-flow does not imply universal safety.",
        "preconditions": [
            f"{VOCAB}/precondition/{name}" for name in mapped["preconditions"]
        ],
        "scope": f"{VOCAB}/scope/{mapped['scope']}",
        "status": "observed_candidate",
        "wildcard": False,
    }


def side(row: dict, *, role: str, case_id: str) -> dict:
    blob = row[role]
    quote = blob.get("quote")
    evidence_gap = not blob["present"]
    spans = []
    if quote:
        spans.append(
            {
                "char_end": quote["char_end"],
                "char_start": quote["char_start"],
                "quoted_sha256": quote["quoted_sha256"],
                "quoted_text": quote["quoted_text"],
                "role": f"{role}_code_span",
                "unique_in_body": quote["unique_in_body"],
            }
        )
    if row.get("commit_message"):
        message = row["commit_message"]
        spans.append(
            {
                "quoted_sha256": sha256_text(message),
                "quoted_text": message,
                "role": "commit_message_not_code_body",
            }
        )
    return {
        "body_present": blob["present"],
        "body_sha256": blob["sha256"],
        "body_utf8_bytes": blob["utf8_bytes"],
        "case_id": case_id,
        "executed": False,
        "polarity": polarity(
            "vulnerable_positive" if role == "vulnerable" else "fixed_negative",
            evidence_gap=evidence_gap,
        ),
        "role": role,
        "source_spans": spans,
    }


def pair_record(item: dict, artifact: dict, prepared_at: str) -> dict:
    row = item["row"]
    held_out = item["split"] != "development"
    vulnerable_id, fixed_id = item["planned_case_ids"]
    restriction = restriction_candidate(row)
    return {
        "adjudication": adjudication(),
        "claim_limitations": limitations(),
        "empirical_sample": True,
        "enters_empirical_sample_count": True,
        "fixture": False,
        "fixture_cve": False,
        "held_out": held_out,
        "intent_code_effect_mapping": {
            "code_effect": {
                "native_sink": restriction.get("effects") or "unknown",
                "qualified_sandbox_handler": "export_json",
                "status": "unsupported_transfer",
            },
            "correlation": "unknown",
            "declared_intent": "apply the non-authoritative scoped restriction candidate if and only if an exact supported mapping exists",
            "reason": (
                "No supported behavior model maps this CVE's native sink onto the "
                "qualified export_json sandbox handler. Incomplete mappings remain unknown."
            ),
        },
        "lineage_family_id": item["lineage_family_id"],
        "mocked_source_record": False,
        "mutation_classes": {
            "fixed": "fixed_negative_control",
            "vulnerable": "source_faithful_vulnerable_positive",
        },
        "pair_id": item["lineage_family_id"] + ":pair",
        "planned_case_ids": item["planned_case_ids"],
        "provenance": provenance(prepared_at),
        "restriction_candidate": restriction,
        "schema": PAIR_SCHEMA,
        "sides": {
            "fixed": side(row, role="fixed", case_id=fixed_id),
            "vulnerable": side(row, role="vulnerable", case_id=vulnerable_id),
        },
        "source": {
            "artifact_id": artifact["artifact_id"],
            "cve_id": row["cve_id"],
            "cwe_id": row["cwe_id"],
            "cwe_name": row["cwe_name"],
            "file_paths": row["file_paths"],
            "file_row_number": row["file_row_number"],
            "fix_commit": row["fix_commit"],
            "language": row["language"],
            "lineage_family_id": item["lineage_family_id"],
            "normalized_source_sha256": row["normalized_source_sha256"],
            "redistribution": "quoted spans and hashes only; parquet and source bodies remain retrieval_only",
            "repo_url": row["repo_url"],
            "repository": row["repository"],
            "revision": artifact["revision"],
            "shard_sha256": artifact["sha256"],
            "source_id": item["source_id"],
            "source_record_sha256": row["source_record_sha256"],
            "source_uri": artifact["source_uri"],
        },
        "source_id": item["source_id"],
        "split": item["split"],
        "supported_behavior_evidence": {
            "kind": "source_locator_body_hashes_and_unique_quotes_not_executed",
            "runnable_sandbox_reproduction": "not_run_untrusted_source_not_executed",
            "vulnerable_body_present": row["vulnerable"]["present"],
            "fixed_body_present": row["fixed"]["present"],
            "reason": (
                "Exact repository revision, shard SHA-256, file_row_number, CVE/CWE "
                "identifiers, and body hashes are retained. Native vulnerable behavior "
                "was not reproduced in the sandbox because CVEfixes rows are untrusted "
                "input and must not be executed by ingestion."
            ),
        },
        "universal_security_claimed": False,
    }


def control_base(item: dict, prepared_at: str, control_class: str, suffix: str) -> dict:
    return {
        "adjudication": adjudication(),
        "claim_limitations": limitations(),
        "control_class": control_class,
        "control_id": item["lineage_family_id"] + ":" + suffix,
        "empirical_sample": False,
        "enters_empirical_sample_count": False,
        "fixture_cve": False,
        "held_out": item["split"] != "development",
        "lineage_family_id": item["lineage_family_id"],
        "mocked_source_record": False,
        "parent_pair_id": item["lineage_family_id"] + ":pair",
        "parent_source_id": item["source_id"],
        "provenance": provenance(prepared_at),
        "schema": CONTROL_SCHEMA,
        "split": item["split"],
        "universal_security_claimed": False,
    }


def build_controls(item: dict, distractor: dict, prepared_at: str) -> list[dict]:
    row = item["row"]
    restriction = restriction_candidate(row)
    distractor_row = distractor["row"]
    records = []

    similarity = control_base(item, prepared_at, "misleading_cve_similarity", "misleading-similarity")
    similarity.update(
        {
            "distractor": {
                "cve_id": distractor_row["cve_id"],
                "cwe_id": distractor_row["cwe_id"],
                "file_row_number": distractor_row["file_row_number"],
                "fix_commit": distractor_row["fix_commit"],
                "relation": distractor["relation"],
                "repository": distractor_row["repository"],
                "source_record_sha256": distractor_row["source_record_sha256"],
                "vulnerable_body_sha256": distractor_row["vulnerable"]["sha256"],
                "vulnerable_quote": distractor_row["vulnerable"]["quote"],
            },
            "expected_polarity": "unknown",
            "expected_status": "unknown",
            "fixture": False,
            "reason": (
                "A real unselected source row is lexically or taxonomically available as "
                "a distractor. Retrieval similarity or a nearby CVE identifier is not "
                "transfer of the parent restriction. Expected polarity remains unknown."
            ),
            "source_kind": "real_unselected_source_row",
        }
    )
    records.append(similarity)

    fixed_negative = control_base(item, prepared_at, "fixed_negative_control", "fixed-negative")
    fixed_negative.update(
        {
            "expected_polarity": "unknown",
            "expected_status": "unknown",
            "fixture": False,
            "fixed_case_id": item["planned_case_ids"][1],
            "fixed_body_present": row["fixed"]["present"],
            "fixed_body_sha256": row["fixed"]["sha256"],
            "reason": (
                "Fixed code is a negative control for this particular restriction "
                "candidate only. It does not certify that all other vulnerabilities "
                "are absent. Independent polarity review was not obtained."
            ),
            "source_kind": "real_selected_fixed_side",
        }
    )
    records.append(fixed_negative)

    broadened = control_base(item, prepared_at, "broadened_effects", "broadened-effects")
    broadened.update(
        {
            "broadened_candidate": {
                "action": restriction.get("action", "security.cvefixes/v1/action/any"),
                "effects": ["security.cvefixes/v1/effect/any", "*"],
                "scope": "generalized",
                "wildcard": True,
            },
            "expected_polarity": "unknown",
            "expected_status": "rejected",
            "fixture": False,
            "reason": (
                "Wildcard, catch-all, or generalized effect/scope broadening is rejected "
                "by the CVEfixes adapter and vocabulary contracts. Broadening is not "
                "admitted as a supported transfer of the parent pair."
            ),
            "source_kind": "synthetic_policy_mutation_on_real_parent",
        }
    )
    records.append(broadened)

    unknown_scope = control_base(item, prepared_at, "unknown_scope", "unknown-scope")
    unknown_scope.update(
        {
            "expected_polarity": "unknown",
            "expected_status": "unknown",
            "fixture": False,
            "reason": (
                "Scope is incomplete: language, native sink, or exact resource bounds "
                "are not independently reviewed. Incomplete mappings remain unknown "
                "rather than silently allowed or denied."
            ),
            "source_kind": "synthetic_policy_mutation_on_real_parent",
        }
    )
    records.append(unknown_scope)

    wildcard = control_base(item, prepared_at, "wildcard_scope", "wildcard")
    wildcard.update(
        {
            "expected_polarity": "unknown",
            "expected_status": "rejected",
            "fixture": False,
            "reason": (
                "Wildcard scope values such as '*', 'any', or glob/regex generalization "
                "are rejected. They cannot be adapted into a CVEfixes Security IR "
                "policy without explicit reviewed_pattern provenance, which was not obtained."
            ),
            "rejected_payload": {"scope": "*", "action": "any", "effects": ["everything"]},
            "source_kind": "synthetic_policy_mutation_on_real_parent",
        }
    )
    records.append(wildcard)

    authority = control_base(item, prepared_at, "self_granted_authority", "self-granted-authority")
    authority.update(
        {
            "expected_polarity": "unknown",
            "expected_status": "rejected",
            "fixture": False,
            "reason": (
                "A candidate, review binding, or derived record cannot grant execution "
                "authority or mark itself authoritative. Self-granted authority remains "
                "rejected."
            ),
            "rejected_payload": {
                "authoritative": True,
                "grants_execution_authority": True,
                "authority": "self",
            },
            "source_kind": "synthetic_policy_mutation_on_real_parent",
        }
    )
    records.append(authority)

    transfer = control_base(item, prepared_at, "unsupported_transfer", "unsupported-transfer")
    transfer.update(
        {
            "expected_polarity": "unknown",
            "expected_status": "unknown",
            "fixture": False,
            "reason": (
                "Transfer of this CVE restriction onto a proposed tool, generated patch, "
                "or the qualified export_json handler requires an explicit mapping, a "
                "supported behavior model, applicable scope, and a checked rule. Those "
                "are absent, so the transfer remains unknown."
            ),
            "target": {
                "handler": "export_json",
                "operation": "export_json",
                "path": "exports/result.json",
            },
            "source_kind": "synthetic_policy_mutation_on_real_parent",
        }
    )
    records.append(transfer)
    return records


def write_review(pairs: list[dict], controls: list[dict], path: Path) -> None:
    split_rows = []
    for pair in pairs:
        source = pair["source"]
        split_rows.append(
            "| `{cve}` | `{repo}` | {split} | {held} | {vbody} | {fbody} | {cwe} |".format(
                cve=source["cve_id"],
                repo=source["repository"],
                split=pair["split"],
                held="yes" if pair["held_out"] else "no",
                vbody="present" if pair["sides"]["vulnerable"]["body_present"] else "absent",
                fbody="present" if pair["sides"]["fixed"]["body_present"] else "absent",
                cwe=source["cwe_id"] or "none",
            )
        )
    classes = sorted({row["control_class"] for row in controls})
    text = f"""# LA-006 CVE pair and control review

**Review status: unresolved.** Independent human security review was not
obtained. Packet-preparer labels are not expert review. Expected polarity
remains `unknown`. Claims are narrowed. Evaluation admission is blocked.

## What was completed

Autonomous packet preparation for the twelve frozen CVE source families and
twenty-four reserved case identities from LA-004. Every pair in
`cve_pairs.jsonl` has exact repository revisions, source-row locators, CVE/CWE
lineage, body hashes when present, unique quoted spans when a unique window
exists, and non-authoritative scoped restriction candidates. Fixed code is a
negative control for that particular restriction only.

Unrelated but lexically or taxonomically similar real unselected rows,
broadened effects, fixed negatives, unknown scope, wildcards, self-granted
authority, and unsupported transfer are in `cve_controls.jsonl`. Those controls
do not enter empirical sample counts.

## What was not completed

Competent independent human security review did not occur. There is no second
human annotator, no disagreement table against an expert, and no final
adjudication of expected polarity. Untrusted source was not executed in the
sandbox; untrusted CVEfixes rows remain inert data. Native vulnerable behavior
is therefore not a measured reproduction.

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
| Independent expert reviews | 0 | not obtained |

Hermetic fixture identifiers such as `CVE-2026-0042` from the default CVE e2e
suite are not empirical source-derived cases and are not included.

## Cohort

| CVE | Repository | Split | Held-out | Vulnerable body | Fixed body | CWE |
| --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(split_rows)}

Twelve planned pair identities and twenty-four planned case IDs from
`benchmark/manifests/splits.json` are present. No family was split across
development/calibration/final. No parquet body or upstream source tree is
vendored; spans are quotes and hashes from the pinned first shard.

Several real rows have absent vulnerable and/or fixed bodies in the pinned
shard. Those absences are recorded as evidence gaps. Missing bodies were not
fabricated.

## Packet preparation method

1. Retrieve the pinned first CVEfixes shard at revision
   `d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2` and verify SHA-256
   `2e25e84e85e1560d41acacbfc7eb359349f5417bc9bf31318cdf0c4aafccb7d1`.
2. Re-read the twelve LA-004 selected `file_row_number` values and verify
   source-record hashes, CVE identifiers, repositories, and fix commits.
3. Hash vulnerable and fixed bodies when present; quote a unique window; never
   execute the text.
4. Assign reserved case-0 to the vulnerable side and case-1 to the fixed side.
5. Propose non-authoritative restriction candidates from a closed CWE table
   only when a mapped CWE and inspectable body exist; otherwise unknown.
6. Attach real unselected distractor rows and synthetic policy mutations as
   controls with `empirical_sample=false`.
7. Set every independently reviewed expected polarity to `unknown`.
8. Record packet-preparer provenance and
   `independent_human_security_review: not_obtained`.

The preparer identifier is `{PREPARER_ID}`. That identity is not an independent
reviewer and does not grant policy or execution authority.

## Independent review attempt

No competent independent human security reviewer was available in this
implementation environment. No expert roster or reviewer credential was
supplied. The worker did not invent a reviewer name, did not treat this
language-model session as expert review, and did not dual-run the same model as
a fake second annotator.

**Dependency still required:** a competent independent human security reviewer
with access to the pinned shard, `cve_pairs.jsonl`, `cve_controls.jsonl`, and
this report, producing per-pair agree/disagree/unknown/amend records and a
named adjudication of residual disagreements.

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
| Independently reviewed expected polarity | unknown | All 24 empirical cases |
| Evaluation admission | blocked | Until independent review |

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
- A fix for one restriction is not universal security.
- Twelve families from one shard are not worldwide vulnerability coverage.
- The structural validator is provenance checking, not scientific peer review.
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", default=str(EVIDENCE_DEFAULT))
    parser.add_argument("--pairs-out", default=str(CASES / "cve_pairs.jsonl"))
    parser.add_argument("--controls-out", default=str(CASES / "cve_controls.jsonl"))
    parser.add_argument("--review-out", default=str(ANNOT / "cve_review.md"))
    args = parser.parse_args()
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    if evidence.get("schema") != "law-to-action-cve-row-evidence/v1":
        raise SystemExit("unexpected evidence schema")
    if len(evidence["selected_rows"]) != 12:
        raise SystemExit("evidence must contain 12 selected rows")
    source_by_id = {
        row["source_id"]: row
        for row in sources["source_records"]
        if row["population"] == "cve"
    }
    split_by_id = {
        row["source_id"]: row for row in splits["assignments"] if row["population"] == "cve"
    }
    prepared_at = datetime.now(timezone.utc).isoformat()
    pairs = []
    controls = []
    for item in evidence["selected_rows"]:
        source = source_by_id[item["source_id"]]
        assignment = split_by_id[item["source_id"]]
        if item["lineage_family_id"] != source["lineage_family_id"]:
            raise SystemExit("evidence family mismatch")
        if item["planned_case_ids"] != assignment["planned_case_ids"]:
            raise SystemExit("planned case identity mismatch")
        pairs.append(pair_record(item, evidence["artifact"], prepared_at))
        controls.extend(
            build_controls(
                item,
                evidence["distractors"][item["source_id"]],
                prepared_at,
            )
        )
    dump_jsonl(Path(args.pairs_out), pairs)
    dump_jsonl(Path(args.controls_out), controls)
    write_review(pairs, controls, Path(args.review_out))
    print(
        json.dumps(
            {
                "status": "built",
                "pairs": len(pairs),
                "controls": len(controls),
                "empirical_cases": 24,
                "fixture_cves_in_empirical_counts": 0,
                "mocked_source_records_in_empirical_counts": 0,
                "independent_human_security_review": "not_obtained",
                "expected_polarity": "unknown",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
