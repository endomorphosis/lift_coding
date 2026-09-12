# LA-006 source-supported CVE pair evidence under the automated scope

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
`la-006-scoped-behavior-contract-compiler` (`machine_contract_expectation_compiler`), distinct from
`ipfs_datasets_py.logic.security_ir.cvefixes.adapter`. Dataset-derived roles, compiler output, and model
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
| Pairs bound | 12 |
| Empirical cases bound | 24 |
| Controls bound | 84 |
| Polarity results with bound contracts | 108 |
| Expected polarity unknown | 108 |
| Recovery failures | 0 |
| Empirical success credits granted | 0 |
