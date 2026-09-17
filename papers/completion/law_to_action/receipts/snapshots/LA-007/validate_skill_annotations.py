#!/usr/bin/python3.12
"""Validate LA-007 skill annotations, adversarial controls, and guidelines.

This checker is structural provenance validation. It does not perform
independent human intent review, does not execute untrusted Markdown, and must
not be reported as empirical evaluation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/law_to_action"
SKILLS = PAPER / "benchmark/annotations/skills.jsonl"
ADVERSARIAL = PAPER / "benchmark/cases/skill_adversarial.jsonl"
GUIDELINES = PAPER / "benchmark/annotations/skill_guidelines.md"
SOURCES = PAPER / "benchmark/manifests/sources.json"
SPLITS = PAPER / "benchmark/manifests/splits.json"
EVIDENCE = Path(__file__).resolve().parent / "row_evidence.json"
SKILL_SCHEMA = "law-to-action-skill-annotation/v1"
ADV_SCHEMA = "law-to-action-skill-adversarial/v1"
NODE_FIELDS = (
    "goals",
    "preconditions",
    "postconditions",
    "guards",
    "effects",
    "verification_steps",
    "assumptions",
    "failures",
    "invariants",
)
CONTROL_KINDS = {
    "next",
    "on_success",
    "on_failure",
    "retry",
    "parallel",
    "join",
}
REQUIRED_MUTATIONS = {
    "malicious_markdown",
    "skill_claims_authorization",
    "command_execution_bait",
}
BUNDLE_SHA256 = "8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4"


def fail(message: str) -> None:
    raise SystemExit("LA-007 validation failed: " + message)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"{path} line {index}: {exc}")
        if not isinstance(row, dict):
            fail(f"{path} line {index} is not an object")
        rows.append(row)
    return rows


def require_text(path: Path, needles: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        fail(f"{path} is empty")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        fail(f"{path} missing required language: {missing}")


def check_span(span: dict, label: str, seen: set[str]) -> None:
    for key in (
        "span_id",
        "role",
        "quoted_text",
        "normalized_char_start",
        "normalized_char_end",
        "quoted_sha256",
    ):
        if key not in span:
            fail(f"{label} span missing {key}")
    quote = span["quoted_text"]
    if not isinstance(quote, str) or len(quote) < 20:
        fail(f"{label} span quote too short")
    if sha256_text(quote) != span["quoted_sha256"]:
        fail(f"{label} span {span['span_id']} quoted_sha256 mismatch")
    start, end = span["normalized_char_start"], span["normalized_char_end"]
    if type(start) is not int or type(end) is not int or end - start != len(quote) or start < 0:
        fail(f"{label} span {span['span_id']} offsets do not match quoted text")
    if span["span_id"] in seen:
        fail(f"{label} duplicate span_id {span['span_id']}")
    seen.add(span["span_id"])


def check_review(row: dict, label: str) -> None:
    provenance = row.get("provenance")
    if not isinstance(provenance, dict):
        fail(f"{label} missing provenance")
    preparer = provenance.get("packet_preparer")
    review = provenance.get("independent_human_intent_review")
    if not isinstance(preparer, dict) or not preparer.get("annotator_id"):
        fail(f"{label} missing annotator provenance")
    if preparer.get("is_independent_intent_review") is not False:
        fail(f"{label} packet preparer is represented as independent review")
    if not isinstance(review, dict) or review.get("status") != "not_obtained":
        fail(f"{label} independent review status must be not_obtained")
    if review.get("reviewer_id") not in {None, ""}:
        fail(f"{label} invented independent reviewer identity")
    if review.get("generated_labels_are_not_expert_review") is not True:
        fail(f"{label} does not record that generated labels are not expert review")
    adjudication = row.get("adjudication")
    if not isinstance(adjudication, dict):
        fail(f"{label} missing adjudication")
    if adjudication.get("status") != "unresolved_missing_expert_review":
        fail(f"{label} adjudication is not visibly unresolved")
    if adjudication.get("final_adjudication") is not None:
        fail(f"{label} final adjudication claimed without expert review")
    if adjudication.get("evaluation_admission") != "blocked_until_independent_human_intent_review":
        fail(f"{label} evaluation admission is not blocked")
    reference = row.get("independent_reference")
    if not isinstance(reference, dict):
        fail(f"{label} missing independent_reference")
    if reference.get("created_before_evaluated_predictions") is not True:
        fail(f"{label} does not record independent annotations before predictions")
    if reference.get("evaluated_predictions_viewed") is not False:
        fail(f"{label} claims evaluated predictions were viewed")
    if reference.get("prediction_files_inspected") != []:
        fail(f"{label} inspected prediction files")
    learned = row.get("learned_components")
    if not isinstance(learned, dict):
        fail(f"{label} missing learned_components")
    if learned.get("trained_normalizer_present") is not False or learned.get("trained_encoder_present") is not False:
        fail(f"{label} claims a trained learned component")
    if learned.get("model_revision") is not None:
        fail(f"{label} invents a model revision")
    ingestion = row.get("ingestion")
    if not isinstance(ingestion, dict):
        fail(f"{label} missing ingestion block")
    if ingestion.get("executed_source_markdown_commands") is not False:
        fail(f"{label} claims Markdown commands were executed")
    if ingestion.get("subprocess_invoked_on_skill_md") is not False:
        fail(f"{label} claims a subprocess on skill_md")


def check_original(row: dict, planned: dict, evidence_by_source: dict, artifact: dict) -> None:
    case_id = row.get("case_id")
    if case_id not in planned:
        fail(f"unexpected original case_id {case_id!r}")
    assignment = planned[case_id]
    if assignment["slot"] != 0:
        fail(f"{case_id} is not the reserved original case-0 identity")
    if row.get("schema") != SKILL_SCHEMA:
        fail(f"{case_id} has wrong schema")
    if row.get("split") != assignment["split"]:
        fail(f"{case_id} split mismatch")
    if row.get("held_out") is not (assignment["split"] != "development"):
        fail(f"{case_id} held_out flag incorrect")
    if row.get("synthetic") is not False or row.get("empirical_sample") is not True:
        fail(f"{case_id} original is not marked empirical original")
    identity = row.get("identity")
    if not isinstance(identity, dict) or identity.get("kind") != "original_skill":
        fail(f"{case_id} identity.kind is not original_skill")
    if identity.get("mutation_id") is not None:
        fail(f"{case_id} original carries a mutation_id")
    if identity.get("source_id") != assignment["source_id"]:
        fail(f"{case_id} source_id mismatch")
    if identity.get("lineage_family_id") != assignment["lineage_family_id"]:
        fail(f"{case_id} family mismatch")
    source = row.get("source")
    if not isinstance(source, dict):
        fail(f"{case_id} missing source")
    if source.get("bundle_sha256") != artifact["sha256"] or artifact["sha256"] != BUNDLE_SHA256:
        fail(f"{case_id} bundle hash mismatch")
    evidence = evidence_by_source[assignment["source_id"]]
    if source.get("skill_id") != evidence["source_locator"]["skill_id"]:
        fail(f"{case_id} skill_id mismatch")
    if source.get("content_sha256") != evidence["content_sha256"]:
        fail(f"{case_id} content hash mismatch")
    if row.get("paired_mutation_case_id") != assignment["sibling"]:
        fail(f"{case_id} paired mutation case is not the reserved case-1")
    spans = row.get("source_spans")
    if not isinstance(spans, list) or not spans:
        fail(f"{case_id} missing source spans")
    span_ids: set[str] = set()
    roles = set()
    for span in spans:
        if not isinstance(span, dict):
            fail(f"{case_id} span is not an object")
        check_span(span, case_id, span_ids)
        roles.add(span["role"])
    for required in ("goal", "precondition", "postcondition", "guard", "effect", "verification", "action"):
        if required not in roles:
            fail(f"{case_id} missing {required} span")
    nodes = row.get("nodes")
    if not isinstance(nodes, dict):
        fail(f"{case_id} missing nodes")
    for name in NODE_FIELDS:
        items = nodes.get(name)
        if not isinstance(items, list) or not items:
            fail(f"{case_id} missing node field {name}")
        for item in items:
            if not isinstance(item, dict) or item.get("grounding") not in {"grounded", "inferred"}:
                fail(f"{case_id} node {name} missing grounding")
            if item["grounding"] == "grounded":
                if not item.get("span_ids") or set(item["span_ids"]) - span_ids:
                    fail(f"{case_id} grounded {name} lacks valid spans")
            elif item.get("span_ids"):
                fail(f"{case_id} inferred {name} must not claim spans")
    actions = row.get("actions")
    if not isinstance(actions, list) or not actions:
        fail(f"{case_id} missing actions")
    edges = row.get("control_edges")
    if not isinstance(edges, list):
        fail(f"{case_id} missing control edges")
    kinds = {edge.get("kind") for edge in edges if isinstance(edge, dict)}
    if kinds != CONTROL_KINDS:
        fail(f"{case_id} control-edge kinds {sorted(kinds)} != {sorted(CONTROL_KINDS)}")
    authority = row.get("textual_authority")
    if not isinstance(authority, dict):
        fail(f"{case_id} missing textual_authority")
    if authority.get("source_word_permitted_is_capability") is not False:
        fail(f"{case_id} treats source permitted as a capability")
    if authority.get("false_textual_authority_expected") != "rejected":
        fail(f"{case_id} does not expect rejection of false textual authority")
    if authority.get("grants_execution_authority") is not False:
        fail(f"{case_id} grants execution authority from skill text")
    check_review(row, case_id)
    if row.get("gold_use") != "intent_span_and_control_fidelity_only_until_independent_review":
        fail(f"{case_id} gold_use overclaims expert labels")
    if row.get("fixture") is not False or row.get("mocked_source_record") is not False:
        fail(f"{case_id} marks a fixture or mocked source record")


def check_adversarial(row: dict, planned: dict, originals: dict, evidence_by_source: dict) -> None:
    case_id = row.get("case_id")
    if row.get("schema") != ADV_SCHEMA:
        fail(f"{case_id} has wrong schema")
    if row.get("synthetic") is not True:
        fail(f"{case_id} mutation is not marked synthetic")
    identity = row.get("identity")
    if not isinstance(identity, dict) or identity.get("kind") != "synthetic_mutation":
        fail(f"{case_id} identity.kind is not synthetic_mutation")
    mutation_id = identity.get("mutation_id")
    if not isinstance(mutation_id, str) or not mutation_id.startswith("mutation:"):
        fail(f"{case_id} mutation_id is missing")
    parent = identity.get("parent_source_id")
    if parent not in evidence_by_source:
        fail(f"{case_id} parent_source_id is not a frozen skill family")
    original_skill = evidence_by_source[parent]["source_locator"]["skill_id"]
    if mutation_id == original_skill or mutation_id == parent:
        fail(f"{case_id} mutation identity collapsed onto the original skill")
    if identity.get("original_skill_id_reused") is not False:
        fail(f"{case_id} reuses original skill identity")
    if identity.get("lineage_family_id") != evidence_by_source[parent]["lineage_family_id"]:
        fail(f"{case_id} mutation left its parent lineage")
    if row.get("original_and_mutation_distinguishable") is not True:
        fail(f"{case_id} does not declare distinguishable identities")
    if identity.get("original_content_sha256") != evidence_by_source[parent]["content_sha256"]:
        fail(f"{case_id} original content hash mismatch")
    overlay = row.get("mutation_overlay")
    if not isinstance(overlay, dict) or overlay.get("synthetic") is not True:
        fail(f"{case_id} missing synthetic overlay")
    if sha256_text(overlay["quoted_text"]) != overlay["quoted_sha256"]:
        fail(f"{case_id} overlay hash mismatch")
    if overlay["quoted_sha256"] == evidence_by_source[parent]["content_sha256"]:
        fail(f"{case_id} overlay hash equals original content hash")
    if row.get("expected_status") != "rejected":
        fail(f"{case_id} false textual authority is not rejected")
    rejection = row.get("expected_rejection")
    if not isinstance(rejection, dict):
        fail(f"{case_id} missing expected_rejection")
    if rejection.get("false_textual_authority") is not True:
        fail(f"{case_id} does not mark false textual authority")
    if rejection.get("grants_execution_authority") is not False:
        fail(f"{case_id} grants execution authority")
    if rejection.get("ingestion_executes_markdown") is not False:
        fail(f"{case_id} allows Markdown execution")
    if row.get("mutation_class") not in REQUIRED_MUTATIONS:
        fail(f"{case_id} unknown mutation_class {row.get('mutation_class')!r}")
    if case_id in planned:
        assignment = planned[case_id]
        if assignment["slot"] != 1:
            fail(f"{case_id} reserved original identity used as a mutation")
        if row.get("empirical_sample") is not True or row.get("enters_empirical_sample_count") is not True:
            fail(f"{case_id} reserved mutation is not counted as the planned case")
        if assignment["source_id"] != parent:
            fail(f"{case_id} mutation parent is not the reserved family")
        if identity.get("parent_case_id") != assignment["sibling"]:
            fail(f"{case_id} parent_case_id is not case-0")
        original = originals[assignment["sibling"]]
        if original["identity"]["skill_id"] == mutation_id:
            fail(f"{case_id} mutation_id equals original skill_id")
    else:
        if not str(case_id).startswith("synthetic:"):
            fail(f"{case_id} extra mutation is not a synthetic identity")
        if row.get("empirical_sample") is not False or row.get("enters_empirical_sample_count") is not False:
            fail(f"{case_id} extra mutation entered empirical counts")
        if evidence_by_source[parent]["lineage_family_id"] not in str(case_id):
            fail(f"{case_id} synthetic id lost parent family")
    if row.get("split") != evidence_by_source[parent]["split"]:
        fail(f"{case_id} mutation split drifted from parent")
    check_review(row, str(case_id))
    if row.get("fixture") is not False or row.get("mocked_source_record") is not False:
        fail(f"{case_id} marks a fixture or mocked source record")


def main() -> int:
    if not SKILLS.is_file() or not ADVERSARIAL.is_file() or not GUIDELINES.is_file():
        fail("annotation deliverables are missing")
    if not EVIDENCE.is_file():
        fail("row evidence is missing")
    sources = load_json(SOURCES)
    splits = load_json(SPLITS)
    evidence = load_json(EVIDENCE)
    artifact = next(row for row in sources["source_artifacts"] if row["artifact_id"] == "skill-security-bundle")
    if artifact["sha256"] != BUNDLE_SHA256:
        fail("frozen SkillCenter artifact hash drifted")
    if evidence.get("bundle", {}).get("markdown_executed") is not False:
        fail("evidence claims Markdown execution")
    if evidence.get("bundle", {}).get("sha256") != BUNDLE_SHA256:
        fail("evidence bundle hash mismatch")
    evidence_by_source = {row["source_id"]: row for row in evidence["records"]}
    planned: dict[str, dict] = {}
    for assignment in splits["assignments"]:
        if assignment["population"] != "skill":
            continue
        source = next(row for row in sources["source_records"] if row["source_id"] == assignment["source_id"])
        case0, case1 = assignment["planned_case_ids"]
        planned[case0] = {
            "source_id": assignment["source_id"],
            "lineage_family_id": assignment["lineage_family_id"],
            "split": assignment["split"],
            "slot": 0,
            "sibling": case1,
            "skill_id": source["source_locator"]["skill_id"],
        }
        planned[case1] = {
            "source_id": assignment["source_id"],
            "lineage_family_id": assignment["lineage_family_id"],
            "split": assignment["split"],
            "slot": 1,
            "sibling": case0,
            "skill_id": source["source_locator"]["skill_id"],
        }
    if len(planned) != 24:
        fail(f"expected 24 reserved skill cases, found {len(planned)}")
    originals = load_jsonl(SKILLS)
    if len(originals) != 12:
        fail(f"expected 12 original skill annotations, found {len(originals)}")
    seen_originals = []
    held_out = 0
    original_by_case = {}
    for row in originals:
        case_id = row.get("case_id")
        if case_id in seen_originals:
            fail(f"duplicate original case_id {case_id}")
        seen_originals.append(case_id)
        check_original(row, planned, evidence_by_source, artifact)
        original_by_case[case_id] = row
        if row.get("held_out"):
            held_out += 1
    missing_originals = sorted(case_id for case_id, item in planned.items() if item["slot"] == 0 and case_id not in original_by_case)
    if missing_originals:
        fail(f"missing reserved original case ids: {missing_originals}")
    if held_out != 10:
        fail(f"expected 10 held-out original records, found {held_out}")
    mutations = load_jsonl(ADVERSARIAL)
    if len(mutations) != 36:
        fail(f"expected 36 adversarial records, found {len(mutations)}")
    seen_mutations = []
    seen_mutation_ids = []
    classes = set()
    empirical_mutations = 0
    extra = 0
    for row in mutations:
        case_id = row.get("case_id")
        if case_id in seen_mutations or case_id in original_by_case:
            fail(f"duplicate or colliding case_id {case_id}")
        seen_mutations.append(case_id)
        mutation_id = row.get("identity", {}).get("mutation_id")
        if mutation_id in seen_mutation_ids:
            fail(f"duplicate mutation_id {mutation_id}")
        seen_mutation_ids.append(mutation_id)
        check_adversarial(row, planned, original_by_case, evidence_by_source)
        classes.add(row.get("mutation_class"))
        if row.get("enters_empirical_sample_count"):
            empirical_mutations += 1
        else:
            extra += 1
    missing_mutations = sorted(case_id for case_id, item in planned.items() if item["slot"] == 1 and case_id not in seen_mutations)
    if missing_mutations:
        fail(f"missing reserved mutation case ids: {missing_mutations}")
    if classes != REQUIRED_MUTATIONS:
        fail(f"missing mutation classes: {sorted(REQUIRED_MUTATIONS - classes)}")
    if empirical_mutations != 12 or extra != 24:
        fail(f"empirical mutations {empirical_mutations}, extra {extra}")
    overlap = set(seen_mutation_ids) & {
        row["source_locator"]["skill_id"] for row in evidence["records"]
    }
    if overlap:
        fail(f"mutation ids collided with original skill ids: {sorted(overlap)}")
    require_text(
        GUIDELINES,
        [
            "Independent human intent review was **not obtained**",
            "not expert review",
            "before viewing",
            "evaluated predictions",
            "Ingestion never executes source Markdown",
            "False textual authority",
            "source assertion, not a capability",
            "malicious_markdown",
            "skill_claims_authorization",
            "command_execution_bait",
            "original_skill",
            "synthetic_mutation",
            "evaluation admission remains blocked",
            "no trained SkillCenter normalizer",
            "Independent reference annotations were created",
            "grounded",
            "inferred",
        ],
    )
    extract_source = Path(__file__).with_name("extract_skill_evidence.py").read_text(encoding="utf-8")
    for needle in (
        "enable_load_extension(False)",
        "PRAGMA query_only = ON",
        "mode=ro&immutable=1",
        "never executed",
    ):
        if needle not in extract_source:
            fail(f"extract script missing safety language: {needle}")
    print(
        json.dumps(
            {
                "status": "pass",
                "originals": len(originals),
                "adversarial": len(mutations),
                "reserved_cases": 24,
                "empirical_mutations": empirical_mutations,
                "extra_synthetic_controls": extra,
                "held_out_originals": held_out,
                "independent_review": "not_obtained",
                "markdown_executed": False,
                "limitation": "Structural provenance validation only. Not independent scientific or intent review.",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
