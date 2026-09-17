# LA-006 CVE pair and control review

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
| Control records | 84 | `enters_empirical_sample_count` is false |
| Independent expert reviews | 0 | not obtained |

Hermetic fixture identifiers such as `CVE-2026-0042` from the default CVE e2e
suite are not empirical source-derived cases and are not included.

## Cohort

| CVE | Repository | Split | Held-out | Vulnerable body | Fixed body | CWE |
| --- | --- | --- | --- | --- | --- | --- |
| `CVE-2024-24746` | `github.com/apache/mynewt-nimble` | calibration | yes | present | present | CWE-835 |
| `CVE-2020-7763` | `github.com/pofider/phantom-html-to-pdf` | final | yes | present | present | CWE-22 |
| `CVE-2023-51665` | `github.com/advplyr/audiobookshelf` | final | yes | present | present | CWE-918 |
| `CVE-2021-4265` | `github.com/siwapp/siwapp-ror` | development | no | present | present | CWE-79 |
| `CVE-2017-16876` | `github.com/lepture/mistune` | final | yes | present | present | CWE-79 |
| `CVE-2022-21159` | `github.com/mz-automation/libiec61850` | development | no | absent | present | CWE-835 |
| `CVE-2019-25087` | `github.com/ramseyk/httpserver` | final | yes | present | present | CWE-22 |
| `CVE-2014-2829` | `github.com/esl/mongooseim` | calibration | yes | absent | absent | CWE-264 |
| `CVE-2020-15084` | `github.com/auth0/express-jwt` | final | yes | absent | absent | CWE-863 |
| `CVE-2016-7149` | `github.com/b2evolution/b2evolution` | final | yes | present | present | CWE-79 |
| `CVE-2020-24654` | `github.com/kde/ark` | calibration | yes | present | present | CWE-59 |
| `CVE-2015-10092` | `github.com/wp-plugins/qtranslate-slug` | final | yes | absent | present | CWE-79 |

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

The preparer identifier is `la006-packet-preparer-implementation-worker`. That identity is not an independent
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
| Packet-preparer pair records | 12 | All twelve reserved families |
| Packet-preparer control records | 84 | Not empirical samples |
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
