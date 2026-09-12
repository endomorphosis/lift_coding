# NS-005 population provenance

Frozen as a task/oracle registry before final A–D outcomes. This document is
not a live repair result, promotion decision, or SWE-bench score.

## Freeze identity

- Protocol: `ns-core-v1`
- Freeze kind: `task_population_before_final_outcomes`
- Builder start (UTC): 2026-09-12T00:17:15.565981+00:00
- Ranking key: `sha256(UTF8(ns-core-v1|family_id))`
- Replacement after freeze: **forbidden**
- Favorable-case selection: **forbidden**

## What was recruited

The live comparison population is genuine historical Python repairs from
public upstream repositories on an a-priori roster. The roster excluded the
twelve SWE-bench families, CVE-identified commits, and Lean/autoformalization
material. Each live family contributes **one** pre-fix issue/fix.

Eligibility (applied uniformly, before looking at model success):

1. OSI-licensed public history.
2. Non-merge commit since 2018-01-01 whose subject documents a fix/bug.
3. Python-only repair surface; native/C/Rust/Go files excluded.
4. Serialized patch ≤ 16 KiB (the preregistered admitted-patch bound).
5. Accompanying test change.
6. Independent hidden FAIL_TO_PASS tests fail on the exact pre-fix snapshot
   and pass on the privately held reference fix.
7. Compile failure, missing dependency, or empty suite is not eligibility.

Development families use the earliest eligible commit; pilot families use the
median-dated eligible commit; final families use the latest eligible commit
(temporal holdout within family). Families are then ordered by SHA-256 rank.

## Actual live population

- Preregistered target: 24 families (4 development / 4 pilot / 16 final)
- Actual live families: 16
- Shortfall vs target: 8
- NS-016 amendment required: true

Development families:

- `upstream:martinblech/xmltodict`
- `upstream:pyparsing/pyparsing`
- `upstream:oauthlib/oauthlib`
- `upstream:pallets/click`

Pilot families:

- `upstream:rthalley/dnspython`
- `upstream:bottlepy/bottle`
- `upstream:kjd/idna`
- `upstream:scrapy/protego`

Final families (also learning holdouts):

- `upstream:sdispater/tomlkit`
- `upstream:pypa/installer`
- `upstream:tornadoweb/tornado`
- `upstream:more-itertools/more-itertools`
- `upstream:jawah/charset_normalizer`
- `upstream:pytest-dev/iniconfig`
- `upstream:pypa/wheel`
- `upstream:pallets/jinja`

Licenses for live families:

- `upstream:martinblech/xmltodict`: MIT
- `upstream:pyparsing/pyparsing`: MIT
- `upstream:oauthlib/oauthlib`: BSD
- `upstream:pallets/click`: BSD
- `upstream:rthalley/dnspython`: ISC
- `upstream:bottlepy/bottle`: MIT
- `upstream:kjd/idna`: BSD-3-Clause
- `upstream:scrapy/protego`: BSD
- `upstream:sdispater/tomlkit`: MIT
- `upstream:pypa/installer`: MIT
- `upstream:tornadoweb/tornado`: Apache-2.0
- `upstream:more-itertools/more-itertools`: MIT
- `upstream:jawah/charset_normalizer`: MIT
- `upstream:pytest-dev/iniconfig`: MIT
- `upstream:pypa/wheel`: MIT
- `upstream:pallets/jinja`: BSD

## Hidden oracles

Target patches and FAIL_TO_PASS **payloads** are not stored in this tree.
Each live task pins an independent oracle by SHA-256 (`reference_patch_sha256`,
`hidden_test_sha256`, `fail_to_pass_sha256`) plus a reconstruction recipe
(`git diff <pre_fix_commit> <fix_commit>` and `git show <fix_commit>:<path>`).
Compact `oracle.json` records live under
`papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-005/scorer_only/oracles/`
and must not be mounted into proposal context. `tasks.jsonl` contains issue
text and compact pre-fix recipes, not reference patches. NS-006 must keep
the hidden store unmounted in the proposal sandbox.

## Qualification overlays

- Table 18 retained boundaries: provider, translation, fixture lifecycle,
  restart publication. Native theorem/circuit and world/procedure remain
  narrowed by NS-014/NS-015 and have no core paired oracles.
- Planned Table 18 count if 16 final families: 128 (16 × 4 × 2).
- Actual Table 18 paired cases: 64.
- Retained Table 12 mutation categories each have a valid and invalid case on
  independently generated `nsq_fixture_v1` (not the old 40 fixtures).
- Actual Table 12 paired cases: 58.

## Forty semantic fixtures

The existing `semantic-state-benchmark-corpus-v1` / 40 `sch-bench-*` tasks
remain **preliminary/qualification only**. They are listed in `tasks.jsonl`
as `role=preliminary_fixture_only` and are not live historical repairs.

## Related-paper corpora

- Autoformalization: Lean/source-fidelity/proof-transfer; no shared instance IDs.
- Law to action: CVE/legal/skill; CVE commits excluded.
- SWE-bench/SWT-Bench: twelve families excluded from the roster so this
  protocol is not a silent SWE-bench subset.

## Unused eligible families

Unused eligible families remain frozen and must not replace a verified live
family after this freeze:

- none

## Exclusions

Every scanned roster member that did not enter the live set has a reason in
`audit/leakage_audit.json`. Verification failures were **not** backfilled from
unused families.

## Limits

- Compact snapshot **recipes** pin the admitted repair surface (commit +
  per-file SHA-256/byte length). Source bytes are not dumped in-tree.
  NS-006 materializes the pinned `pre_fix_commit` for execution.
- Builder execution of hidden tests used CPython 3.12 and pytest on archived
  commits. That is oracle applicability, not an A–D result.
- Shared-org clustering is disclosed; it is not silently treated as 24
  unconditionally independent population units.
