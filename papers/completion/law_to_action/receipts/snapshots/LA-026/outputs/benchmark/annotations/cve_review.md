# LA-026 CVE source recovery and reviewer packet

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
| Control records | 84 | `enters_empirical_sample_count` is false |
| Real unselected or fixed-side controls | 24 | excluded, not empirical samples |
| Synthetic policy-mutation controls | 60 | excluded, not empirical samples |
| Synthetic controls in empirical sample counts | 0 | none |
| Independent expert reviews | 0 | not obtained |

Hermetic fixture identifiers such as `CVE-2026-0042` from the default CVE e2e
suite are not empirical source-derived cases and are not included.

## Cohort and upstream recovery

| CVE | Repository | Split | Held-out | Parent | Fix | Vuln files | Fixed files | Failures | CWE |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| `CVE-2024-24746` | `github.com/apache/mynewt-nimble` | calibration | yes | `4080f942f185` | `d42a0ebe6632` | 1/1 | 1/1 | 0 | CWE-835 |
| `CVE-2020-7763` | `github.com/pofider/phantom-html-to-pdf` | final | yes | `c1c4d4df05f3` | `b5d2da2639a4` | 2/2 | 2/2 | 0 | CWE-22 |
| `CVE-2023-51665` | `github.com/advplyr/audiobookshelf` | final | yes | `433671424815` | `728496010cbf` | 1/1 | 1/1 | 0 | CWE-918 |
| `CVE-2021-4265` | `github.com/siwapp/siwapp-ror` | development | no | `7e56c6a82ff0` | `924d16008cfc` | 22/22 | 22/22 | 0 | CWE-79 |
| `CVE-2017-16876` | `github.com/lepture/mistune` | final | yes | `7f7f106a717e` | `5f06d724bc05` | 1/1 | 1/1 | 0 | CWE-79 |
| `CVE-2022-21159` | `github.com/mz-automation/libiec61850` | development | no | `96e93c4be32e` | `cfa94cbf1030` | 1/1 | 1/1 | 0 | CWE-835 |
| `CVE-2019-25087` | `github.com/ramseyk/httpserver` | final | yes | `6eeb84a28f09` | `1a0de56e4daf` | 3/3 | 3/3 | 0 | CWE-22 |
| `CVE-2014-2829` | `github.com/esl/mongooseim` | calibration | yes | `3ed283f6c5d0` | `586d96cc12ef` | 11/11 | 11/11 | 0 | CWE-264 |
| `CVE-2020-15084` | `github.com/auth0/express-jwt` | final | yes | `e9ed6d240d94` | `7ecab5f8f0ca` | 6/6 | 6/6 | 0 | CWE-863 |
| `CVE-2016-7149` | `github.com/b2evolution/b2evolution` | final | yes | `50daa5e658f3` | `9a4ab85439d1` | 2/2 | 2/2 | 0 | CWE-79 |
| `CVE-2020-24654` | `github.com/kde/ark` | calibration | yes | `ddd3641eecce` | `8bf8c5ef07b0` | 1/1 | 1/1 | 0 | CWE-59 |
| `CVE-2015-10092` | `github.com/wp-plugins/qtranslate-slug` | final | yes | `4751e91e83c0` | `74b3932696f9` | 3/3 | 3/3 | 0 | CWE-79 |

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

The recovery worker identifier is `la026-source-recovery-implementation-worker`. That identity is not an
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
| Packet-preparer pair records | 12 | All twelve reserved families |
| Packet-preparer control records | 84 | Not empirical samples |
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
