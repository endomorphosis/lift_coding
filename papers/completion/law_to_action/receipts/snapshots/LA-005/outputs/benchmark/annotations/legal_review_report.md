# LA-005 legal review report

**Review status: unresolved.** Independent human legal expert review was not
obtained. Packet-preparer labels are not expert review. Applicability remains
`unknown`. Claims are narrowed. Evaluation admission is blocked.

## What was completed

Autonomous packet preparation for the six frozen legal source families and
twelve reserved case identities from LA-004. Every record in `legal.jsonl` has
source spans, annotator/review provenance, and applicability assumptions.
Omitted-exception, wrong-date/jurisdiction, unsupported-construct, and
no-applicable-record cases are present. Ambiguous and unsupported cases use
explicit `unknown` labels rather than permission or denial.

## What was not completed

Competent independent human legal review did not occur. There is no second
human annotator, no disagreement table against an expert, and no final
adjudication of allow/deny. The reviewer-access dependency remains open.

This is the outcome the task requires when reviewer access is missing: document
agreement/disagreement as inapplicable, leave adjudication unresolved, and
narrow claims. It is not a substitute for that review.

## Cohort

| Family | Section | Split | Held-out | case-0 | case-1 |
| --- | --- | --- | --- | --- | --- |
| legal-health-information | 42 U.S.C. § 1320d-6 | development | no | source_faithful | omitted_legal_exception |
| legal-computer-access | 18 U.S.C. § 1030 | development | no | source_faithful | wrong_date_or_jurisdiction |
| legal-childrens-privacy | 15 U.S.C. § 6502 | calibration | yes | source_faithful | unsupported_construct |
| legal-federal-records-privacy | 5 U.S.C. § 552a | final | yes | source_faithful | no_applicable_record |
| legal-access-control-circumvention | 17 U.S.C. § 1201 | final | yes | source_faithful | omitted_legal_exception |
| legal-telecom-confidentiality | 47 U.S.C. § 222 | final | yes | source_faithful | wrong_date_or_jurisdiction |

Twelve planned case IDs from `benchmark/manifests/splits.json` are present.
No family was split across development/calibration/final. No source body PDF
was added to paper outputs; spans are quotes from `pdftotext -raw` of the
pinned bytes.

## Packet preparation method

1. Retrieve the six GovInfo URIs frozen by LA-004 and verify document SHA-256
   and byte size.
2. Extract text with `pdftotext -raw` and verify the LA-004 text and
   normalized SHA-256 values.
3. Quote unique normalized substrings for operative clauses, exceptions,
   definitions, cross-references, authority, and effective-interval language.
4. Copy actor/action/object/modality words from those quotes into atom fields.
5. Assign synthetic request scenarios for the reserved case identities,
   including the required mutation classes.
6. Set every applicability label to `unknown`.
7. Record packet-preparer provenance and `independent_human_legal_review:
   not_obtained`.

The preparer identifier is `la005-packet-preparer-implementation-worker`. That
identity is not a licensed attorney and is not an independent reviewer.

## Independent review attempt

No competent independent human legal reviewer was available in this
implementation environment. No bar license, expert roster, or reviewer
credential was supplied. The worker did not invent a reviewer name, did not
treat this language-model session as expert review, and did not dual-run the
same model as a fake second annotator.

**Dependency still required:** a competent independent human legal reviewer
with access to the six pinned USCODE-2024 PDFs, `legal.jsonl`, and
`legal_guidelines.md`, producing per-case agree/disagree/unknown/amend records
and a named adjudication of residual disagreements.

## Agreement, disagreement, and adjudication

| Measure | Value | Notes |
| --- | ---: | --- |
| Packet-preparer records | 12 | All twelve reserved cases |
| Independent expert reviews | 0 | Not obtained |
| Dual-annotator pairs | 0 | Second human annotator not obtained |
| Observed agreements | not applicable | No independent reviewer |
| Observed disagreements | none recorded | Absence of a reviewer is not agreement |
| Final adjudicated allow labels | 0 | Not adjudicated |
| Final adjudicated deny labels | 0 | Not adjudicated |
| Explicit unknown labels | 12 | Mandatory while review is missing |
| Unresolved cases | 12 | Visible; not silently closed |

Adjudication status on every record is
`unresolved_missing_expert_review`. `final_adjudication` is null.
`evaluation_admission` is `blocked_until_independent_human_legal_review`.

There is no Cohen's kappa, percent agreement, or expert-acceptance rate to
report. Computing those statistics from a single worker would fabricate
independence.

## Held-out provenance

Calibration and final records (eight cases) each include:

- one or more source spans with quoted text and offsets;
- packet-preparer annotator provenance with `is_expert_legal_review: false`;
- independent-review provenance `not_obtained`;
- applicability assumptions;
- `unknown` applicability.

Those eight held-out labels are therefore source-grounded packets with
documented missing review, not expert gold.

## Unknown labels instead of forced permission or denial

Every applicability label is `unknown`. Forced permission or denial is false
on every record.

This is required for:

- omitted-exception probes, where retaining an exception span is not an allow;
- wrong-date/jurisdiction probes, where a non-applicable source is not an allow;
- no-applicable-record probes, where a private-actor request unmatched to
  5 U.S.C. § 552a is not a deny of all law and not a permission;
- unsupported constructs, including COPPA's incorporation of Commission
  regulations and DMCA Librarian class rulemaking, which cannot disappear
  into a seven-field success.

## Claim limitations (narrowed)

The following claims are **not** made:

- That a held-out expert legal gold set exists.
- That allow/deny oracles are ready for LA-009 source-to-IR scoring of
  applicability.
- That exceptions, cross-references, dates, jurisdiction, or authority have
  been expert-validated.
- That case law (including CFAA constructions) or FTC/HIPAA regulations were
  applied.
- That worldwide legal coverage follows from six U.S. Code sections.

The following claims **are** made, and only these:

- Twelve reserved case identities have annotation packets.
- Quoted spans occur uniquely in the pinned normalized section text.
- Review provenance records missing expert review instead of hiding it.
- Unknown labels are explicit.
- Independent review is an unmet dependency that keeps evaluation closed.

## Follow-up

A bounded follow-up remains: obtain the independent human legal review named
above, store disagreement/adjudication records, and only then consider
evaluation admission. Until that follow-up exists, LA-009 must treat
applicability as unknown and must not score invented expert judgments.
