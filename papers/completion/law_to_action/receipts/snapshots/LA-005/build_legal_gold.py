#!/usr/bin/python3.12
"""Build the LA-005 legal annotation packets from pinned GovInfo section text.

This script extracts exact source spans from pdftotext -raw output of the
six frozen USCODE-2024 PDFs. It does not perform, and must not be reported
as, independent human legal expert review. Applicability labels are unknown.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
BENCHMARK = ROOT / "papers/completion/law_to_action/benchmark"
ANNOTATIONS = BENCHMARK / "annotations"
SCHEMA = "law-to-action-legal-annotation/v1"
TEXT_BASIS = "pdftotext -raw UTF-8; whitespace collapsed with re.sub(r'\\s+', ' ', text)"
PREPARER_ID = "la005-packet-preparer-implementation-worker"
PREPARER_ROLE = "autonomous_annotation_packet_preparer_not_licensed_attorney_not_expert_review"

REQUIRED_MUTATIONS = {
    "omitted_legal_exception",
    "wrong_date_or_jurisdiction",
    "unsupported_construct",
    "no_applicable_record",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def require_span(normal: str, quoted: str, span_id: str, role: str) -> dict:
    start = normal.find(quoted)
    if start < 0:
        raise SystemExit(f"quoted span not found for {span_id}: {quoted[:80]!r}")
    if normal.count(quoted) != 1:
        raise SystemExit(f"quoted span is not unique for {span_id}: {quoted[:80]!r}")
    end = start + len(quoted)
    return {
        "span_id": span_id,
        "role": role,
        "quoted_text": quoted,
        "normalized_char_start": start,
        "normalized_char_end": end,
        "quoted_sha256": sha256_text(quoted),
        "encoding": "utf-8",
        "text_basis": TEXT_BASIS,
    }


def field(value, status, span_ids, note=None):
    payload = {
        "value": value,
        "status": status,
        "span_ids": list(span_ids),
    }
    if note:
        payload["note"] = note
    return payload


def provenance(prepared_at: str) -> dict:
    return {
        "packet_preparer": {
            "annotator_id": PREPARER_ID,
            "role": PREPARER_ROLE,
            "is_expert_legal_review": False,
            "is_licensed_attorney": False,
            "independence": "same implementation worker that prepared all packets; not an independent second annotator",
            "prepared_at": prepared_at,
        },
        "independent_human_legal_review": {
            "status": "not_obtained",
            "reviewer_id": None,
            "reviewer_credentials": None,
            "reviewed_at": None,
            "is_expert_legal_review": False,
            "dependency": "Competent independent human legal reviewer with access to the six pinned USCODE-2024 section PDFs, these packets, and the annotation guidelines.",
            "generated_labels_are_not_expert_review": True,
        },
        "second_independent_annotator": {
            "status": "not_obtained",
            "note": "No second human annotator was available. Dual-annotator agreement is not computed.",
        },
    }


def adjudication() -> dict:
    return {
        "status": "unresolved_missing_expert_review",
        "agreement": "not_applicable_no_independent_reviewer",
        "disagreement_records": [],
        "final_adjudication": None,
        "claims_narrowed": True,
        "evaluation_admission": "blocked_until_independent_human_legal_review",
        "visible_unresolved": True,
    }


def applicability(reason: str, assumptions: list[str], scope_match: str) -> dict:
    return {
        "label": "unknown",
        "label_set": ["allow", "deny", "unknown"],
        "reason": reason,
        "scope_match": scope_match,
        "forced_permission_or_denial": False,
        "assumptions": assumptions,
        "authority_of_label": "packet_preparer_unknown_pending_expert_review",
        "expert_certified": False,
    }


def record(base: dict) -> dict:
    required = [
        "schema",
        "annotation_id",
        "case_id",
        "split",
        "held_out",
        "source",
        "mutation_class",
        "request_scenario",
        "atoms",
        "source_spans",
        "applicability",
        "unsupported_constructs",
        "provenance",
        "adjudication",
        "claim_limitations",
        "gold_use",
    ]
    missing = [key for key in required if key not in base]
    if missing:
        raise SystemExit(f"incomplete record {base.get('case_id')}: {missing}")
    atoms = base["atoms"]
    for name in (
        "modality",
        "actor",
        "action",
        "object",
        "conditions",
        "exceptions",
        "effective_interval",
        "jurisdiction",
        "authority",
        "definitions",
        "cross_references",
    ):
        if name not in atoms:
            raise SystemExit(f"{base['case_id']} missing atom {name}")
    if not base["source_spans"]:
        raise SystemExit(f"{base['case_id']} has no source spans")
    if base["applicability"]["label"] not in {"allow", "deny", "unknown"}:
        raise SystemExit(f"{base['case_id']} invalid applicability label")
    return base


def source_block(family: dict, artifact: dict, prepared_from: str) -> dict:
    locator = family["source_locator"]
    return {
        "source_id": family["source_id"],
        "lineage_family_id": family["lineage_family_id"],
        "artifact_id": family["artifact_id"],
        "section": locator["section"],
        "edition": locator["edition"],
        "document_sha256": locator["document_sha256"],
        "normalized_source_sha256": family["normalized_source_sha256"],
        "source_uri": artifact["source_uri"],
        "revision": artifact["revision"],
        "text_extraction": TEXT_BASIS,
        "prepared_from_cache_file": prepared_from,
        "redistribution": "quoted spans only; full PDF bodies remain retrieval_only",
    }


def common_limitations() -> list[str]:
    return [
        "Packet-preparer field extraction is not independent human legal expert review.",
        "No licensed attorney reviewed these labels.",
        "Judicial gloss, later amendments, implementing regulations, and unquoted neighboring sections are not treated as controlling gold.",
        "Applicability is unknown; these records are not an allow/deny oracle for scored enforcement.",
        "Evaluation admission remains blocked until competent independent human legal review and adjudication.",
    ]


def build_cases(normals: dict[str, str], families: dict[str, dict], artifacts: dict[str, dict], prepared_at: str) -> list[dict]:
    cases = []

    def add(**kwargs):
        cases.append(record(kwargs))

    # 42 USC 1320d-6 development family
    fam = families["legal-health-information"]
    art = artifacts["legal-health-information"]
    n = normals["legal-health-information"]
    s_off = require_span(
        n,
        "A person who knowingly and in violation of this part— (1) uses or causes to be used a unique health identifier; (2) obtains individually identifiable health information relating to an individual; or (3) discloses individually identifiable health information to another person, shall be punished as provided in subsection (b).",
        "h1-offense",
        "operative_clause",
    )
    s_authz = require_span(
        n,
        "the individual ob- tained or disclosed such information without au- thorization",
        "h1-authorization",
        "condition_and_exception_boundary",
    )
    s_covered = require_span(
        n,
        "if the information is main- tained by a covered entity (as defined in the HIPAA privacy regulation described in section 1320d–9(b)(3) of this title)",
        "h1-covered-entity",
        "condition",
    )
    s_eff = require_span(
        n,
        "Amendment by Pub. L. 111–5 effective 12 months after Feb. 17, 2009, see section 13423 of Pub. L. 111–5, set out as an Effective Date note under section 17931 of this title.",
        "h1-effective",
        "effective_interval",
    )
    s_xref = require_span(
        n,
        "HIPAA privacy regulation described in section 1320d–9(b)(3) of this title) and the individual ob- tained or disclosed such information without au- thorization",
        "h1-xref",
        "cross_reference",
    )
    health_source = source_block(fam, art, "legal-health-information.txt")
    health_atoms_base = {
        "modality": field("prohibition", "source_attested", ["h1-offense"], "Offense text imposes punishment for listed acts; packet preparer does not certify a deontic encoding."),
        "actor": field("a person", "source_attested", ["h1-offense"]),
        "action": field("uses or causes to be used a unique health identifier; obtains or discloses individually identifiable health information", "source_attested", ["h1-offense"]),
        "object": field("unique health identifier; individually identifiable health information relating to an individual", "source_attested", ["h1-offense"]),
        "conditions": field(
            "knowingly and in violation of this part; information maintained by a covered entity as defined by cross-referenced HIPAA privacy regulation",
            "source_attested",
            ["h1-offense", "h1-covered-entity", "h1-authorization"],
        ),
        "exceptions": field(
            "without authorization is part of the obtaining/disclosure construct; no separate statutory exception clause is quoted for this offense",
            "unknown",
            ["h1-authorization"],
            "Whether 'without authorization' functions as an exception, an element, or both is a legal-interpretation question reserved as unknown.",
        ),
        "effective_interval": field("2009 amendment effective 12 months after Feb. 17, 2009", "source_attested", ["h1-effective"]),
        "jurisdiction": field("United States; Title 42 public-health statutory offense", "source_attested", ["h1-offense"], "No extra-territorial statement is quoted in the selected spans."),
        "authority": field("42 U.S.C. § 1320d-6, USCODE-2024 edition", "source_attested", ["h1-offense"]),
        "definitions": [
            field(
                "covered entity as defined in the HIPAA privacy regulation described in section 1320d-9(b)(3)",
                "unsupported",
                ["h1-covered-entity", "h1-xref"],
                "Definition is incorporated by cross-reference to another section and to a regulation not in this source family.",
            )
        ],
        "cross_references": [
            field("42 U.S.C. § 1320d-9(b)(3); HIPAA privacy regulation", "source_attested", ["h1-xref"])
        ],
    }
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-health-information:case-0",
        case_id=fam["planned_case_ids"][0],
        split=fam["split"],
        held_out=fam["split"] != "development",
        source=health_source,
        mutation_class="source_faithful",
        request_scenario={
            "scenario_id": "h1-faithful-disclosure",
            "synthetic": True,
            "actor": "hospital workforce member",
            "action": "disclose individually identifiable health information of a patient to an unaffiliated person",
            "object": "patient laboratory result stored by a HIPAA covered entity",
            "jurisdiction": "United States",
            "clock": "2024-06-01T00:00:00+00:00",
            "authorization_fact": "no authorization from the individual is stipulated",
            "facts": "Synthetic request aligned to the quoted offense text. Alignment is not an expert applicability judgment.",
        },
        atoms=health_atoms_base,
        source_spans=[s_off, s_authz, s_covered, s_eff, s_xref],
        applicability=applicability(
            "Source-attested offense text is present, but legal applicability of these synthetic facts is unknown without independent expert review.",
            [
                "Facts are synthetic.",
                "Covered-entity status depends on a regulation and section not fully quoted here.",
                "No expert determination of mens rea, authorization, or preemption is made.",
            ],
            "in_scope_candidate",
        ),
        unsupported_constructs=[
            "HIPAA privacy regulation definition of covered entity is outside this section PDF.",
            "Interaction with 42 U.S.C. § 1320d-7 state-law effect is not annotated as a rule.",
        ],
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-health-information:case-1",
        case_id=fam["planned_case_ids"][1],
        split=fam["split"],
        held_out=fam["split"] != "development",
        source=health_source,
        mutation_class="omitted_legal_exception",
        request_scenario={
            "scenario_id": "h1-omitted-authorization-boundary",
            "synthetic": True,
            "actor": "hospital workforce member",
            "action": "disclose individually identifiable health information",
            "object": "patient record maintained by a covered entity",
            "jurisdiction": "United States",
            "clock": "2024-06-01T00:00:00+00:00",
            "authorization_fact": "individual authorization is stipulated as present",
            "facts": "Probe case: a compiler that drops the 'without authorization' language would treat an authorized disclosure like the base offense. Gold retains the authorization span. Applicability of the authorized facts remains unknown.",
        },
        atoms={
            **health_atoms_base,
            "exceptions": field(
                "authorization boundary quoted in source must be retained; omitting it is an exception/element loss",
                "source_attested",
                ["h1-authorization"],
                "Packet preparer records the span. Whether authorization is a true exception or a negative element is unknown.",
            ),
        },
        source_spans=[s_off, s_authz, s_covered, s_eff, s_xref],
        applicability=applicability(
            "Omitted-authorization probe. Gold does not convert authorized facts into permission or denial.",
            [
                "The exception/element span must remain in the gold atom even if a compiler drops it.",
                "Presence of stipulated authorization is a synthetic fact, not a HIPAA authorization-form review.",
                "Unknown is required; do not force allow.",
            ],
            "exception_may_apply",
        ),
        unsupported_constructs=[
            "What counts as valid individual authorization under the HIPAA privacy rule is not in this section.",
        ],
        omitted_exception_probe={
            "retained_span_id": "h1-authorization",
            "compiler_fault_under_test": "drop without-authorization language from the seven-field projection",
            "gold_requires_span_retention": True,
            "gold_does_not_force_permission": True,
        },
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )

    # 18 USC 1030 development family
    fam = families["legal-computer-access"]
    art = artifacts["legal-computer-access"]
    n = normals["legal-computer-access"]
    s_who = require_span(n, "§ 1030. Fraud and related activity in connection with computers (a) Whoever—", "c1-heading", "authority")
    s_acc = require_span(
        n,
        "intentionally accesses a computer with- out authorization or exceeds authorized ac- cess, and thereby obtains—",
        "c1-access",
        "operative_clause",
    )
    s_exc = require_span(
        n,
        "unless the object of the fraud and the thing obtained consists only of the use of the computer and the value of such use is not more than $5,000 in any 1-year period",
        "c1-value-exception",
        "exception",
    )
    s_le = require_span(
        n,
        "(f) This section does not prohibit any lawfully authorized investigative, protective, or intel- ligence activity of a law enforcement agency of the United States, a State, or a political sub- division of a State, or of an intelligence agency of the United States.",
        "c1-le-exception",
        "exception",
    )
    s_eaa = require_span(
        n,
        "the term ‘‘exceeds authorized access’’ means to access a computer with authoriza- tion and to use such access to obtain or alter information in the computer that the accesser is not entitled so to obtain or alter",
        "c1-def-eaa",
        "definition",
    )
    s_pc = require_span(
        n,
        "the term ‘‘protected computer’’ means a computer—",
        "c1-def-pc",
        "definition",
    )
    computer_source = source_block(fam, art, "legal-computer-access.txt")
    computer_atoms = {
        "modality": field("prohibition", "source_attested", ["c1-access"], "Whoever clause plus listed conduct; not an expert deontic encoding."),
        "actor": field("whoever", "source_attested", ["c1-heading", "c1-access"]),
        "action": field("intentionally accesses a computer without authorization or exceeds authorized access and thereby obtains listed information", "source_attested", ["c1-access"]),
        "object": field("computer; information from a protected computer or listed records", "source_attested", ["c1-access", "c1-def-pc"]),
        "conditions": field("intentional access; obtaining information described in (a)(2)", "source_attested", ["c1-access"]),
        "exceptions": field(
            "subsection (f) lawfully authorized investigative/protective/intelligence activity; (a)(4) use-value cap is a separate exception on a different paragraph",
            "source_attested",
            ["c1-le-exception", "c1-value-exception"],
        ),
        "effective_interval": field("USCODE-2024 edition text; no separate original-enactment clock is quoted as the sole operative date for (a)(2)", "unknown", ["c1-heading"]),
        "jurisdiction": field("United States criminal code; protected-computer definition includes certain foreign computers used in a manner that affects U.S. interstate or foreign commerce", "source_attested", ["c1-def-pc"]),
        "authority": field("18 U.S.C. § 1030, USCODE-2024 edition", "source_attested", ["c1-heading"]),
        "definitions": [
            field("exceeds authorized access", "source_attested", ["c1-def-eaa"]),
            field("protected computer", "source_attested", ["c1-def-pc"]),
        ],
        "cross_references": [
            field("Fair Credit Reporting Act (15 U.S.C. 1681 et seq.) appears in (a)(2)(A) and is not expanded here", "unsupported", ["c1-access"]),
        ],
    }
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-computer-access:case-0",
        case_id=fam["planned_case_ids"][0],
        split=fam["split"],
        held_out=fam["split"] != "development",
        source=computer_source,
        mutation_class="source_faithful",
        request_scenario={
            "scenario_id": "c1-faithful-unauthorized-access",
            "synthetic": True,
            "actor": "unauthenticated remote user",
            "action": "intentionally access a computer and obtain information",
            "object": "files on a U.S. interstate e-commerce server",
            "jurisdiction": "United States",
            "clock": "2024-06-01T00:00:00+00:00",
            "authorization_fact": "no authorization stipulated",
            "facts": "Synthetic access request. Judicial interpretations of 'exceeds authorized access' are not applied.",
        },
        atoms=computer_atoms,
        source_spans=[s_who, s_acc, s_exc, s_le, s_eaa, s_pc],
        applicability=applicability(
            "Quoted access prohibition is present. Whether these synthetic facts constitute a violation is unknown without expert review, including unresolved construction of authorization.",
            [
                "No case-law overlay (including Van Buren) is treated as gold.",
                "Protected-computer status is not independently verified from facts.",
                "Unknown is required.",
            ],
            "in_scope_candidate",
        ),
        unsupported_constructs=[
            "Case-law narrowing of exceeds-authorized-access is outside the statute PDF.",
            "Cross-referenced consumer-reporting definitions are not expanded.",
        ],
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations() + ["Statutory text is annotated; judicial construction is unknown."],
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-computer-access:case-1",
        case_id=fam["planned_case_ids"][1],
        split=fam["split"],
        held_out=fam["split"] != "development",
        source=computer_source,
        mutation_class="wrong_date_or_jurisdiction",
        request_scenario={
            "scenario_id": "c1-wrong-jurisdiction-clock",
            "synthetic": True,
            "actor": "foreign system administrator acting only on a wholly foreign computer with no stipulated U.S. commerce effect",
            "action": "access own employer computer",
            "object": "local files",
            "jurisdiction": "a non-U.S. jurisdiction with no stipulated U.S. nexus",
            "clock": "1970-01-01T00:00:00+00:00",
            "authorization_fact": "employer authorization stipulated",
            "facts": "Request clock and jurisdiction are outside the quoted USCODE-2024 computer-fraud setting. Gold must not treat the mismatch as permission to act, nor as a U.S. denial.",
        },
        atoms=computer_atoms,
        source_spans=[s_who, s_acc, s_exc, s_le, s_eaa, s_pc],
        applicability=applicability(
            "Wrong date/jurisdiction probe. The pinned U.S. section is not shown to apply; that is not a permission label.",
            [
                "A source that does not apply is unknown/not-applicable, never allow.",
                "Absence of a matching U.S. record is not a global finding that no law applies.",
                "Clock 1970-01-01 is synthetic and predates the quoted offense family.",
            ],
            "out_of_scope_or_unmatched",
        ),
        unsupported_constructs=["Extra-territorial reach and historical versioning beyond USCODE-2024 are unsupported."],
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )

    # 15 USC 6502 calibration family
    fam = families["legal-childrens-privacy"]
    art = artifacts["legal-childrens-privacy"]
    n = normals["legal-childrens-privacy"]
    s_unlaw = require_span(
        n,
        "It is unlawful for an operator of a website or online service directed to children, or any op- erator that has actual knowledge that it is collecting personal information from a child, to collect personal information from a child in a manner that violates the regulations pre- scribed under subsection (b).",
        "k1-unlawful",
        "operative_clause",
    )
    s_vpc = require_span(
        n,
        "to obtain verifiable parental consent for the collection, use, or disclosure of per- sonal information from children",
        "k1-vpc-req",
        "condition",
    )
    s_vpcdef = require_span(
        n,
        "The term ‘‘verifiable parental consent’’ means any reasonable effort (taking into con- sideration available technology), including a request for authorization for future collection, use, and disclosure described in the notice, to ensure that a parent of a child receives notice of the operator’s personal information collec- tion, use, and disclosure practices, and author- izes the collection, use, and disclosure, as ap- plicable, of personal information",
        "k1-vpc-def",
        "definition",
    )
    s_parent = require_span(n, "The term ‘‘parent’’ includes a legal guard- ian.", "k1-parent", "definition")
    s_pi = require_span(
        n,
        "The term ‘‘personal information’’ means in- dividually identifiable information about an individual collected online, including—",
        "k1-pi",
        "definition",
    )
    s_reg = require_span(
        n,
        "Not later than 1 year after October 21, 1998, the Commission shall promulgate under sec- tion 553 of title 5 regulations that—",
        "k1-reg-clock",
        "effective_interval",
    )
    s_disc = require_span(
        n,
        "Notwithstanding paragraph (1), neither an operator of such a website or online service nor the operator’s agent shall be held to be liable under any Federal or State law for any disclosure made in good faith and following reasonable procedures in responding to a re- Page 2245 TITLE 15—COMMERCE AND TRADE § 6502 quest for disclosure of personal information under subsection (b)(1)(B)(iii) to the parent of a child.",
        "k1-parent-disclosure",
        "exception",
    )
    kids_source = source_block(fam, art, "legal-childrens-privacy.txt")
    kids_atoms = {
        "modality": field("prohibition", "source_attested", ["k1-unlawful"]),
        "actor": field("operator of a website or online service directed to children, or operator with actual knowledge it is collecting personal information from a child", "source_attested", ["k1-unlawful"]),
        "action": field("collect personal information from a child in a manner that violates regulations prescribed under subsection (b)", "source_attested", ["k1-unlawful"]),
        "object": field("personal information from a child", "source_attested", ["k1-unlawful", "k1-pi"]),
        "conditions": field("directed to children or actual knowledge; collection that violates subsection (b) regulations including verifiable parental consent", "source_attested", ["k1-unlawful", "k1-vpc-req"]),
        "exceptions": field("good-faith parent disclosure response under (a)(2)", "source_attested", ["k1-parent-disclosure"]),
        "effective_interval": field("Commission regulation duty not later than 1 year after October 21, 1998", "source_attested", ["k1-reg-clock"]),
        "jurisdiction": field("United States; Title 15 commerce statute", "source_attested", ["k1-unlawful"]),
        "authority": field("15 U.S.C. § 6502, USCODE-2024 edition", "source_attested", ["k1-unlawful"]),
        "definitions": [
            field("verifiable parental consent", "source_attested", ["k1-vpc-def"]),
            field("parent includes legal guardian", "source_attested", ["k1-parent"]),
            field("personal information", "source_attested", ["k1-pi"]),
            field("child", "unknown", [], "The term is used in § 6502; the definition lives in § 6501 and is not a unique complete definition span in this family PDF."),
            field("operator", "unknown", [], "Operator is used operatively; its definition is not uniquely present as a complete quoted definition in this family PDF."),
        ],
        "cross_references": [
            field("regulations prescribed under subsection (b); 5 U.S.C. § 553", "source_attested", ["k1-unlawful", "k1-reg-clock"]),
        ],
    }
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-childrens-privacy:case-0",
        case_id=fam["planned_case_ids"][0],
        split=fam["split"],
        held_out=True,
        source=kids_source,
        mutation_class="source_faithful",
        request_scenario={
            "scenario_id": "k1-faithful-collection",
            "synthetic": True,
            "actor": "operator of a website directed to children",
            "action": "collect personal information from a child without stipulated parental consent",
            "object": "name and online contact information",
            "jurisdiction": "United States",
            "clock": "2024-06-01T00:00:00+00:00",
            "facts": "Synthetic COPPA-shaped request. Age, directed-to-children status, and consent validity are not expert-determined.",
        },
        atoms=kids_atoms,
        source_spans=[s_unlaw, s_vpc, s_vpcdef, s_parent, s_pi, s_reg, s_disc],
        applicability=applicability(
            "Operative collection prohibition is quoted. Applicability of synthetic child-directed collection facts is unknown.",
            [
                "Child is not fully defined inside this section PDF.",
                "Subsection (b) regulations are not the PDF body.",
                "Unknown is required.",
            ],
            "in_scope_candidate",
        ),
        unsupported_constructs=[
            "FTC COPPA rule text is incorporated by reference and is not this source family.",
            "Definition of child/operator from 15 U.S.C. § 6501 is not a complete unique span here.",
        ],
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-childrens-privacy:case-1",
        case_id=fam["planned_case_ids"][1],
        split=fam["split"],
        held_out=True,
        source=kids_source,
        mutation_class="unsupported_construct",
        request_scenario={
            "scenario_id": "k1-unsupported-incorporated-regulations",
            "synthetic": True,
            "actor": "operator",
            "action": "collect personal information in a manner whose lawfulness depends on the full subsection (b) regulation set",
            "object": "personal information from a child",
            "jurisdiction": "United States",
            "clock": "2024-06-01T00:00:00+00:00",
            "facts": "The seven-field compiler cannot faithfully encode 'in a manner that violates the regulations prescribed under subsection (b)' without the regulation corpus. Gold marks that construct unsupported and applicability unknown.",
        },
        atoms=kids_atoms,
        source_spans=[s_unlaw, s_vpc, s_vpcdef, s_parent, s_pi, s_reg, s_disc],
        applicability=applicability(
            "Unsupported incorporation-by-reference construct. Do not force permission or denial from a partial seven-field projection.",
            [
                "Unrepresented regulation corpus cannot disappear into a successful allow or deny.",
                "Unknown is mandatory for uses that require the missing regulations.",
            ],
            "unsupported",
        ),
        unsupported_constructs=[
            "Incorporation of Commission regulations under subsection (b).",
            "Open-ended 'any reasonable effort' technology-dependent consent standard.",
            "Missing unique definition spans for child and operator in this family PDF.",
        ],
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )

    # 5 USC 552a final family
    fam = families["legal-federal-records-privacy"]
    art = artifacts["legal-federal-records-privacy"]
    n = normals["legal-federal-records-privacy"]
    s_head = require_span(n, "§ 552a. Records maintained on individuals", "p1-heading", "authority")
    s_disc = require_span(
        n,
        "No agency shall disclose any record which is contained in a system of records by any means of communica- tion to any person, or to another agency, except pursuant to a written request by, or with the prior written consent of, the individual to whom the record pertains, unless disclosure of the record would be—",
        "p1-disclose",
        "operative_clause",
    )
    s_agency = require_span(
        n,
        "the term ‘‘agency’’ means agency as de- fined in section 552(e) 1 of this title",
        "p1-agency",
        "definition",
    )
    s_ind = require_span(
        n,
        "the term ‘‘individual’’ means a citizen of the United States or an alien lawfully admit- ted for permanent residence",
        "p1-individual",
        "definition",
    )
    s_rec = require_span(
        n,
        "the term ‘‘record’’ means any item, col- lection, or grouping of information about an individual that is maintained by an agency, including, but not limited to, his education, fi- nancial transactions, medical history, and criminal or employment history and that con- tains his name, or the identifying number, symbol, or other identifying particular as- signed to the individual, such as a finger or voice print or a photograph",
        "p1-record",
        "definition",
    )
    s_sor = require_span(
        n,
        "the term ‘‘system of records’’ means a group of any records under the control of any agency from which information is retrieved by the name of the individual or by some identi- fying number, symbol, or other identifying particular assigned to the individual",
        "p1-sor",
        "definition",
    )
    s_ru = require_span(
        n,
        "the term ‘‘routine use’’ means, with re- spect to the disclosure of a record, the use of such record for a purpose which is compatible with the purpose for which it was collected",
        "p1-routine",
        "definition",
    )
    privacy_source = source_block(fam, art, "legal-federal-records-privacy.txt")
    privacy_atoms = {
        "modality": field("prohibition", "source_attested", ["p1-disclose"]),
        "actor": field("agency", "source_attested", ["p1-disclose", "p1-agency"]),
        "action": field("disclose any record contained in a system of records by any means of communication to any person or to another agency", "source_attested", ["p1-disclose"]),
        "object": field("record contained in a system of records", "source_attested", ["p1-disclose", "p1-record", "p1-sor"]),
        "conditions": field("record is in a system of records; disclosure is to a person or another agency", "source_attested", ["p1-disclose"]),
        "exceptions": field(
            "written request or prior written consent of the individual; plus the numbered unless-disclosure-would-be conditions beginning after the quoted colon",
            "source_attested",
            ["p1-disclose", "p1-routine"],
            "The full numbered exception list is longer than a seven-field slot; remaining numbered conditions are unrepresented material.",
        ),
        "effective_interval": field("USCODE-2024 edition of 5 U.S.C. § 552a", "source_attested", ["p1-heading"]),
        "jurisdiction": field("United States; agency as defined via 5 U.S.C. § 552(e)", "source_attested", ["p1-agency"]),
        "authority": field("5 U.S.C. § 552a, USCODE-2024 edition", "source_attested", ["p1-heading"]),
        "definitions": [
            field("agency", "source_attested", ["p1-agency"]),
            field("individual", "source_attested", ["p1-individual"]),
            field("record", "source_attested", ["p1-record"]),
            field("system of records", "source_attested", ["p1-sor"]),
            field("routine use", "source_attested", ["p1-routine"]),
        ],
        "cross_references": [
            field("section 552(e) of this title for agency; section 552 of this title appears among disclosure conditions", "source_attested", ["p1-agency", "p1-disclose"]),
        ],
    }
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-federal-records-privacy:case-0",
        case_id=fam["planned_case_ids"][0],
        split=fam["split"],
        held_out=True,
        source=privacy_source,
        mutation_class="source_faithful",
        request_scenario={
            "scenario_id": "p1-faithful-agency-disclosure",
            "synthetic": True,
            "actor": "federal agency records officer",
            "action": "disclose a record from a system of records to an unaffiliated person",
            "object": "named individual's medical-history record",
            "jurisdiction": "United States",
            "clock": "2024-06-01T00:00:00+00:00",
            "authorization_fact": "no written request or prior written consent stipulated",
            "facts": "Synthetic agency-disclosure request. Whether any numbered unless-condition applies is unknown.",
        },
        atoms=privacy_atoms,
        source_spans=[s_head, s_disc, s_agency, s_ind, s_rec, s_sor, s_ru],
        applicability=applicability(
            "Disclosure prohibition is quoted. Applicability of the synthetic agency disclosure, including numbered exceptions, is unknown.",
            [
                "Numbered exception list is longer than the retained quote.",
                "Agency status depends on a cross-referenced definition.",
                "Unknown is required.",
            ],
            "in_scope_candidate",
        ),
        unsupported_constructs=[
            "Full twelve-plus disclosure exceptions cannot be losslessly stored in a seven-field tuple.",
            "Agency definition incorporates 5 U.S.C. § 552(e).",
        ],
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-federal-records-privacy:case-1",
        case_id=fam["planned_case_ids"][1],
        split=fam["split"],
        held_out=True,
        source=privacy_source,
        mutation_class="no_applicable_record",
        request_scenario={
            "scenario_id": "p1-no-applicable-record",
            "synthetic": True,
            "actor": "private coffee-shop loyalty program",
            "action": "email a marketing offer to a customer",
            "object": "store-local purchase history that is not an agency system of records",
            "jurisdiction": "a U.S. city, private actor",
            "clock": "2024-06-01T00:00:00+00:00",
            "facts": "The pinned 5 U.S.C. § 552a family does not supply an applicable agency system-of-records disclosure rule for this private-actor request. Gold is unknown/no-applicable-record, not a denial of the email and not a permission under other unquoted laws.",
        },
        atoms=privacy_atoms,
        source_spans=[s_head, s_disc, s_agency, s_ind, s_rec, s_sor, s_ru],
        applicability=applicability(
            "No applicable record in this frozen family for the private-actor request. That is not a forced deny and not a forced allow.",
            [
                "Actor is not an agency as defined in the quoted spans.",
                "Other privacy statutes are outside this source family and remain unknown.",
                "Unknown is mandatory.",
            ],
            "out_of_scope_or_unmatched",
        ),
        unsupported_constructs=["Any non-552a privacy regime is outside this family."],
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )

    # 17 USC 1201 final family
    fam = families["legal-access-control-circumvention"]
    art = artifacts["legal-access-control-circumvention"]
    n = normals["legal-access-control-circumvention"]
    s_circ = require_span(
        n,
        "No person shall circumvent a technological measure that effectively controls access to a work protected under this title.",
        "d1-prohibit",
        "operative_clause",
    )
    s_eff = require_span(
        n,
        "The prohibition contained in the preceding sentence shall take effect at the end of the 2-year period beginning on the date of the enactment of this chapter.",
        "d1-effective",
        "effective_interval",
    )
    s_class = require_span(
        n,
        "The prohibition contained in subparagraph (A) shall not apply to persons who are users of a copyrighted work which is in a particular class of works, if such persons are, or are likely to be in the succeeding 3-year period, adversely affected by virtue of such prohibition in their ability to make noninfringing uses of that par- ticular class of works under this title, as deter- mined under subparagraph (C).",
        "d1-class-exception",
        "exception",
    )
    s_lib = require_span(
        n,
        "During the 2-year period described in sub- paragraph (A), and during each succeeding 3- year period, the Librarian of Congress, upon the recommendation of the Register of Copyrights, who shall consult with the Assistant Secretary for Communications and Information of the De- partment of Commerce and report and comment on his or her views in making such recommenda- tion, shall make the determination in a rule- making proceeding for purposes of subparagraph (B) of whether persons who are users of a copy- righted work are, or are likely to be in the suc- ceeding 3-year period, adversely affected by the prohibition under subparagraph (A) in their abil- ity to make noninfringing uses under this title of a particular class of copyrighted works.",
        "d1-rulemaking",
        "unsupported_construct",
    )
    s_npl = require_span(
        n,
        "A nonprofit library, archives, or educational insti- tution which gains access to a commercially ex- ploited copyrighted work solely in order to make a good faith determination of whether to acquire a copy of that work for the sole purpose of engaging in conduct permitted under this title shall not be in violation of subsection (a)(1)(A).",
        "d1-npl",
        "exception",
    )
    s_cdef = require_span(
        n,
        "to ‘‘circumvent a technological meas- ure’’ means to descramble a scrambled work, to decrypt an encrypted work, or otherwise to avoid, bypass, remove, deactivate, or impair a technological measure, without the authority of the copyright owner",
        "d1-circ-def",
        "definition",
    )
    dmca_source = source_block(fam, art, "legal-access-control-circumvention.txt")
    dmca_atoms = {
        "modality": field("prohibition", "source_attested", ["d1-prohibit"]),
        "actor": field("no person / any person", "source_attested", ["d1-prohibit"]),
        "action": field("circumvent a technological measure that effectively controls access to a work protected under this title", "source_attested", ["d1-prohibit", "d1-circ-def"]),
        "object": field("technological measure controlling access to a work protected under title 17", "source_attested", ["d1-prohibit"]),
        "conditions": field("measure effectively controls access; work protected under this title", "source_attested", ["d1-prohibit"]),
        "exceptions": field(
            "Librarian class exemptions under (a)(1)(B)-(C); nonprofit library/archives/educational good-faith acquisition check under (d)",
            "source_attested",
            ["d1-class-exception", "d1-npl", "d1-rulemaking"],
        ),
        "effective_interval": field("access-control prohibition takes effect at the end of the 2-year period beginning on the date of enactment of this chapter", "source_attested", ["d1-effective"]),
        "jurisdiction": field("United States; Title 17", "source_attested", ["d1-prohibit"]),
        "authority": field("17 U.S.C. § 1201, USCODE-2024 edition", "source_attested", ["d1-prohibit"]),
        "definitions": [
            field("circumvent a technological measure", "source_attested", ["d1-circ-def"]),
        ],
        "cross_references": [
            field("section 1030 of title 18 is referenced in the security-testing subsection and is a different family", "unsupported", ["d1-rulemaking"]),
        ],
    }
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-access-control-circumvention:case-0",
        case_id=fam["planned_case_ids"][0],
        split=fam["split"],
        held_out=True,
        source=dmca_source,
        mutation_class="source_faithful",
        request_scenario={
            "scenario_id": "d1-faithful-circumvention",
            "synthetic": True,
            "actor": "person",
            "action": "decrypt an encrypted copyrighted work without stipulated copyright-owner authority",
            "object": "access-control measure on a protected work",
            "jurisdiction": "United States",
            "clock": "2024-06-01T00:00:00+00:00",
            "facts": "Synthetic circumvention request after the quoted 2-year delayed-effectiveness window. Class exemptions are not evaluated.",
        },
        atoms=dmca_atoms,
        source_spans=[s_circ, s_eff, s_class, s_lib, s_npl, s_cdef],
        applicability=applicability(
            "Circumvention prohibition is quoted. Applicability, including class exemptions and fair-use interaction, is unknown.",
            [
                "Delayed-effectiveness clause is retained.",
                "Librarian class lists are not in this PDF body as current 37 C.F.R. text.",
                "Unknown is required.",
            ],
            "in_scope_candidate",
        ),
        unsupported_constructs=[
            "Triennial Librarian of Congress class rulemaking cannot be reduced to a static seven-field tuple.",
        ],
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-access-control-circumvention:case-1",
        case_id=fam["planned_case_ids"][1],
        split=fam["split"],
        held_out=True,
        source=dmca_source,
        mutation_class="omitted_legal_exception",
        request_scenario={
            "scenario_id": "d1-omitted-library-exception",
            "synthetic": True,
            "actor": "nonprofit library",
            "action": "gain access solely to make a good faith determination whether to acquire a copy for conduct permitted under title 17",
            "object": "commercially exploited copyrighted work protected by an access-control measure",
            "jurisdiction": "United States",
            "clock": "2024-06-01T00:00:00+00:00",
            "facts": "Probe: dropping the (d) nonprofit library exception from IR would mis-score this request. Gold retains the exception span. Applicability of the good-faith acquisition facts remains unknown.",
        },
        atoms=dmca_atoms,
        source_spans=[s_circ, s_eff, s_class, s_lib, s_npl, s_cdef],
        applicability=applicability(
            "Omitted-exception probe for the nonprofit library/archives/educational acquisition check. Do not force permission merely because an exception span exists, and do not force denial if the compiler dropped it.",
            [
                "Exception span d1-npl must be retained.",
                "Good-faith and sole-purpose facts are synthetic and unreviewed.",
                "Unknown is required.",
            ],
            "exception_may_apply",
        ),
        unsupported_constructs=["Good-faith determination is not a seven-field primitive."],
        omitted_exception_probe={
            "retained_span_id": "d1-npl",
            "compiler_fault_under_test": "drop subsection (d) nonprofit library exception",
            "gold_requires_span_retention": True,
            "gold_does_not_force_permission": True,
        },
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )

    # 47 USC 222 final family
    fam = families["legal-telecom-confidentiality"]
    art = artifacts["legal-telecom-confidentiality"]
    n = normals["legal-telecom-confidentiality"]
    s_duty = require_span(
        n,
        "Every telecommunications carrier has a duty to protect the confidentiality of proprietary in- formation of, and relating to, other tele- communication carriers, equipment manufac- turers, and customers, including telecommuni- cation carriers reselling telecommunications services provided by a telecommunications car- rier.",
        "t1-duty",
        "operative_clause",
    )
    s_cpni = require_span(
        n,
        "Except as required by law or with the ap- proval of the customer, a telecommunications carrier that receives or obtains customer pro- prietary network information by virtue of its provision of a telecommunications service shall only use, disclose, or permit access to in- dividually identifiable customer proprietary network information in its provision of (A) the telecommunications service from which such information is derived, or (B) services nec- essary to, or used in, the provision of such telecommunications service, including the publishing of directories.",
        "t1-cpni",
        "operative_clause",
    )
    s_ex = require_span(
        n,
        "(d) Exceptions Nothing in this section prohibits a tele- communications carrier from using, disclosing, or permitting access to customer proprietary network information obtained from its cus- tomers, either directly or indirectly through its agents—",
        "t1-exceptions",
        "exception",
    )
    s_emerg = require_span(
        n,
        "to a public safety answering point, emergency medical service provider or emer- gency dispatch provider, public safety, fire service, or law enforcement official, or hos- pital emergency or trauma care facility, in order to respond to the user’s call for emer- gency services",
        "t1-emergency",
        "exception",
    )
    s_def = require_span(
        n,
        "The term ‘‘customer proprietary network in- formation’’ means—",
        "t1-cpni-def",
        "definition",
    )
    s_added = require_span(
        n,
        "as added Pub. L. 104–104, title VII, § 702, Feb. 8, 1996, 110 Stat. 148",
        "t1-added",
        "effective_interval",
    )
    telecom_source = source_block(fam, art, "legal-telecom-confidentiality.txt")
    telecom_atoms = {
        "modality": field("obligation and prohibition", "source_attested", ["t1-duty", "t1-cpni"], "Duty to protect plus use/disclose restriction; dual modality is retained rather than collapsed."),
        "actor": field("telecommunications carrier", "source_attested", ["t1-duty", "t1-cpni"]),
        "action": field("use, disclose, or permit access to individually identifiable customer proprietary network information; duty to protect confidentiality of proprietary information", "source_attested", ["t1-duty", "t1-cpni"]),
        "object": field("customer proprietary network information; proprietary information of carriers, manufacturers, and customers", "source_attested", ["t1-duty", "t1-cpni", "t1-cpni-def"]),
        "conditions": field("information obtained by virtue of provision of a telecommunications service; individually identifiable CPNI", "source_attested", ["t1-cpni"]),
        "exceptions": field(
            "required by law; customer approval; subsection (d) including emergency public-safety disclosures",
            "source_attested",
            ["t1-cpni", "t1-exceptions", "t1-emergency"],
        ),
        "effective_interval": field("section added Feb. 8, 1996 by Pub. L. 104-104; USCODE-2024 text", "source_attested", ["t1-added"]),
        "jurisdiction": field("United States; Communications Act Title 47", "source_attested", ["t1-duty"]),
        "authority": field("47 U.S.C. § 222, USCODE-2024 edition", "source_attested", ["t1-duty"]),
        "definitions": [
            field("customer proprietary network information", "source_attested", ["t1-cpni-def"]),
        ],
        "cross_references": [
            field("section 332(d) of this title and section 615b of this title appear in the emergency-location exception", "source_attested", ["t1-emergency"]),
        ],
    }
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-telecom-confidentiality:case-0",
        case_id=fam["planned_case_ids"][0],
        split=fam["split"],
        held_out=True,
        source=telecom_source,
        mutation_class="source_faithful",
        request_scenario={
            "scenario_id": "t1-faithful-cpni-disclosure",
            "synthetic": True,
            "actor": "telecommunications carrier",
            "action": "disclose individually identifiable CPNI to an unaffiliated marketer",
            "object": "customer call-detail and location information",
            "jurisdiction": "United States",
            "clock": "2024-06-01T00:00:00+00:00",
            "authorization_fact": "no customer approval stipulated; not an emergency dispatch",
            "facts": "Synthetic CPNI disclosure request. Carrier status and CPNI classification are not expert-determined.",
        },
        atoms=telecom_atoms,
        source_spans=[s_duty, s_cpni, s_ex, s_emerg, s_def, s_added],
        applicability=applicability(
            "CPNI use/disclosure restriction is quoted. Applicability of the synthetic marketing disclosure is unknown.",
            [
                "Customer approval and required-by-law exceptions are not stipulated as satisfied.",
                "Dual obligation/prohibition modality is retained.",
                "Unknown is required.",
            ],
            "in_scope_candidate",
        ),
        unsupported_constructs=["Full CPNI definition including negative subscriber-list carve-out exceeds a single object field."],
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )
    add(
        schema=SCHEMA,
        annotation_id="la005:legal-telecom-confidentiality:case-1",
        case_id=fam["planned_case_ids"][1],
        split=fam["split"],
        held_out=True,
        source=telecom_source,
        mutation_class="wrong_date_or_jurisdiction",
        request_scenario={
            "scenario_id": "t1-wrong-date-jurisdiction",
            "synthetic": True,
            "actor": "non-U.S. postal operator with no stipulated telecommunications-carrier status",
            "action": "share a paper mailing list",
            "object": "postal addresses",
            "jurisdiction": "a non-U.S. jurisdiction",
            "clock": "1990-01-01T00:00:00+00:00",
            "facts": "Request predates the quoted Feb. 8, 1996 addition of § 222 and is outside telecommunications-carrier CPNI facts. Gold is unknown, not permission and not a U.S. denial.",
        },
        atoms=telecom_atoms,
        source_spans=[s_duty, s_cpni, s_ex, s_emerg, s_def, s_added],
        applicability=applicability(
            "Wrong date/jurisdiction probe against the pinned 47 U.S.C. § 222 family. Non-application of this source is not an allow label.",
            [
                "Clock 1990-01-01 predates the quoted addition date.",
                "Actor is not a quoted telecommunications carrier.",
                "Unknown is mandatory.",
            ],
            "out_of_scope_or_unmatched",
        ),
        unsupported_constructs=["Historical Communications Act versions before Pub. L. 104-104 are not this source family."],
        provenance=provenance(prepared_at),
        adjudication=adjudication(),
        claim_limitations=common_limitations(),
        gold_use="atom_and_span_fidelity_only_until_expert_review",
    )
    return cases


def index_families(sources: dict, splits: dict) -> tuple[dict, dict]:
    artifacts = {row["artifact_id"]: row for row in sources["source_artifacts"]}
    split_by_source = {row["source_id"]: row for row in splits["assignments"] if row["population"] == "legal"}
    families = {}
    for row in sources["source_records"]:
        if row["population"] != "legal":
            continue
        assignment = split_by_source[row["source_id"]]
        families[row["artifact_id"]] = {
            **row,
            "split": assignment["split"],
            "planned_case_ids": assignment["planned_case_ids"],
        }
    if len(families) != 6:
        raise SystemExit(f"expected 6 legal families, found {len(families)}")
    return families, artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-dir", required=True, help="Directory of pdftotext -raw UTF-8 .txt files named after artifact ids")
    parser.add_argument("--output", default=str(ANNOTATIONS / "legal.jsonl"))
    args = parser.parse_args()
    text_dir = Path(args.text_dir)
    sources = load_json(BENCHMARK / "manifests/sources.json")
    splits = load_json(BENCHMARK / "manifests/splits.json")
    families, artifacts = index_families(sources, splits)
    normals = {}
    for artifact_id, family in families.items():
        path = text_dir / f"{artifact_id}.txt"
        text = path.read_text(encoding="utf-8")
        if sha256_text(text) != {
            "legal-computer-access": "d7ad445ec2100cd5e4efb62cd4815fd4dd7b2c209f00d457a419afc2a8e07940",
            "legal-federal-records-privacy": "794a0b190d59127f6db11cfbf5f9a29a44248850d6986e5687e33b7e77579912",
            "legal-childrens-privacy": "d7166e4aff6f7fbcfec383501dbd19a819955fafc537fffae5023a6eaaaed2c8",
            "legal-access-control-circumvention": "2abf13af7a1cc2e0c485a818b328ad05441591c0709bcbc3c8bb859249184364",
            "legal-health-information": "7ea0ca5d9050d31079e9d36f61a53fa426f5bc08afc28ef79136655dc14c2321",
            "legal-telecom-confidentiality": "066e898e4612983b2f1b64495acc8e5e75adace96c19345e8a778b468b62e4cb",
        }[artifact_id]:
            raise SystemExit(f"text hash mismatch for {artifact_id}")
        normal = normalize(text)
        if sha256_text(normal) != family["normalized_source_sha256"]:
            raise SystemExit(f"normalized hash mismatch for {artifact_id}")
        normals[artifact_id] = normal
    prepared_at = datetime.now(timezone.utc).isoformat()
    cases = build_cases(normals, families, artifacts, prepared_at)
    planned = [case_id for family in families.values() for case_id in family["planned_case_ids"]]
    got = [row["case_id"] for row in cases]
    if sorted(got) != sorted(planned):
        raise SystemExit(f"case id mismatch: {got} vs {planned}")
    mutations = {row["mutation_class"] for row in cases}
    if not REQUIRED_MUTATIONS <= mutations:
        raise SystemExit(f"missing mutation classes: {REQUIRED_MUTATIONS - mutations}")
    if any(row["applicability"]["label"] != "unknown" for row in cases):
        raise SystemExit("applicability must remain unknown without expert review")
    if any(row["provenance"]["independent_human_legal_review"]["status"] != "not_obtained" for row in cases):
        raise SystemExit("must not claim independent human legal review")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in cases), encoding="utf-8")
    print(json.dumps({"wrote": str(output), "cases": len(cases), "prepared_at": prepared_at}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
