# LA-005 legal annotation guidelines

These guidelines bind the frozen six-family legal cohort from LA-004. They
govern packet preparation, source-span recording, unknown labels, and review
provenance. They do not authorize scored evaluation admission.

## Status of this gold set

This file describes how the packets in `legal.jsonl` were prepared and how they
must be read.

- Packet preparation is an autonomous implementation-worker task.
- Independent human legal expert review was **not obtained**.
- Generated or worker-prepared labels are not expert review.
- Applicability labels are **unknown**. Permission and denial are not assigned.
- Agreement, disagreement, and final adjudication are unresolved.
- Claims are narrowed to source-span fidelity of quoted statutory text.
- These records are not an expert applicability oracle for LA-009 or LA-015.

A later competent independent human legal review may change labels. Until that
review and documented adjudication exist, evaluation admission remains blocked.

## Source freeze

Use only the six official GovInfo USCODE-2024 section PDFs reserved by LA-004.

| Artifact | Section | Document SHA-256 |
| --- | --- | --- |
| legal-computer-access | 18 U.S.C. § 1030 | `b403c8ea9d052478c35cdcdaa5361ba6ff09d3ca89b129e1bc031c870367ac76` |
| legal-federal-records-privacy | 5 U.S.C. § 552a | `9a090bb5da1dd4bc151d2fc7651e659c3d56d23fad3932eaedd3f083638ab24a` |
| legal-childrens-privacy | 15 U.S.C. § 6502 | `39eede5f2f8dffb893574526f158e1c1bb16a3cd2047a6634d770e132b11348b` |
| legal-access-control-circumvention | 17 U.S.C. § 1201 | `0878ee4ab36ad6fbfcbbc1fb6749ef5242f57a30f21e8119c84498edb05f1aa1` |
| legal-health-information | 42 U.S.C. § 1320d-6 | `32bd2e92ac9ad9897e286c93b9373bdc88ad28f976215a2ff859ad029c0fefa0` |
| legal-telecom-confidentiality | 47 U.S.C. § 222 | `4cc72f64f8f4a6b99809b2da804e90ba00d796f5e91e93d20b35751d21c1072e` |

Each entire section PDF is one lineage family. Adjacent-page context in a PDF
is context only; it is not a second family and not a substitute for a missing
definition in another section. Case IDs are the two planned child identities
already reserved in `benchmark/manifests/splits.json`. Do not mint replacement
IDs after seeing outcomes.

Text basis for span offsets: `pdftotext -raw` UTF-8, then collapse whitespace
with `re.sub(r'\s+', ' ', text)`. Offsets are into that normalized string.
Quoted text must be an exact unique substring of the normalized source.

Do not vendor full PDF bodies in paper outputs. Quote the spans needed to
ground a label.

## What every record must contain

Every label, including every held-out label, must carry:

1. source spans: exact quoted text, normalized character offsets, SHA-256 of
   the quote, and a role (`operative_clause`, `exception`, `definition`,
   `cross_reference`, `effective_interval`, `condition`, `authority`, or
   `unsupported_construct`).
2. **Annotator and review provenance.** Packet-preparer identity and role;
   independent-reviewer identity or an explicit `not_obtained` status. Never
   fill reviewer identity with the packet preparer.
3. **Applicability assumptions.** The synthetic request facts, clock,
   jurisdiction, and the interpretive limits of the quote.

Required atom fields, matching the paper's rich bridge and seven-field
compiler: `modality`, `actor`, `action`, `object`, `conditions`, `exceptions`,
`effective_interval`, `jurisdiction`, `authority`, `definitions`, and
`cross_references`. A field that cannot be supported by a span is `unknown` or
`unsupported`, not invented.

## Unknown policy (mandatory)

Allowed applicability labels are `allow`, `deny`, and `unknown`.

Use `unknown` when any of the following is true:

- Independent human legal expert review is missing.
- The construct is unsupported in the seven-field grammar.
- The request has no applicable record in this frozen family.
- Date or jurisdiction is outside the quoted source.
- An exception or element may apply and has not been adjudicated.
- Judicial gloss, implementing regulations, or unquoted neighboring sections
  would be required.
- Ambiguity remains after reading the quoted spans.

Never silently recode unknown as permission or denial. A source that does not
apply is not an allow. Absence of a matching family record is not a global
finding that no law applies, and it is not a scored deny of the request.

`scope_match` may record `in_scope_candidate`, `out_of_scope_or_unmatched`,
`exception_may_apply`, or `unsupported`. That field is not an allow/deny
oracle.

## Mutation cases

Each family has two reserved cases. The gold set must include all of:

- `omitted_legal_exception`
- `wrong_date_or_jurisdiction`
- `unsupported_construct`
- `no_applicable_record`

plus source-faithful atom packets.

For omitted-exception probes, retain the exception or authorization-boundary
span in gold even if a compiler would drop it. Do not convert the probe into
allow. For wrong-date/jurisdiction and no-applicable-record probes, keep
applicability unknown. For unsupported constructs, retain the unrepresented
material explicitly so it cannot disappear into a successful compilation.

## Annotator versus expert review

| Role | Who | What they may do | What they may not do |
| --- | --- | --- | --- |
| Packet preparer | Implementation worker | Quote spans, copy actor/action/object words, flag unsupported material, assign unknown | Claim attorney status, apply case law, certify allow/deny, impersonate a second annotator |
| Independent human legal reviewer | Licensed or otherwise competent human reviewer, independent of packet preparation | Accept, reject, or adjudicate labels; record disagreement | Be invented by a supervisor or language model |
| Adjudicator | Named after disagreement | Record a final reviewed label or keep unknown | Silently overwrite unknown with allow or deny |

If the independent reviewer is missing, record `status: not_obtained`, keep
adjudication `unresolved_missing_expert_review`, and narrow claims. Do not
compute a fake agreement rate.

## Held-out handling

Calibration and final family labels are held-out. Development packets use the
same schema so they cannot later be relabeled as expert gold by omission.
Development examples must not leak into held-out scoring. Unknowns are
retained in every split.

## What this gold set may be used for

Until independent review lands:

- Span and atom-presence checks against quoted text.
- Tests that a compiler reports unsupported constructs instead of dropping them.
- Documentation that expert applicability review is an unmet dependency.

It may not be used as:

- An expert allow/deny oracle.
- Evidence that legal source-to-IR fidelity has been measured (that is LA-009).
- A substitute for human legal advice.

## Reviewer packet (for the unmet dependency)

A future reviewer should receive, for each case: the pinned PDF, this
guideline, the JSONL record, the quoted spans highlighted in the normalized
text, the synthetic request, and a form with fields `agree`, `disagree`,
`unknown`, `amended_label`, and `rationale`. Disagreement with the packet
preparer is expected and must be kept. Final adjudication is a separate named
step.
