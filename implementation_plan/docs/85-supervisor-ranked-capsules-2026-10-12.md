# Ranked capsule lifecycle and real-task instruction census — 2026-10-12

The corrected full-supervisor instruction census completed on `largest-eigenval`.
Reversible instruction deduplication reduced complete coding input from
**65,222 to 64,254 bytes: 968 bytes (1.484%)**. It consumed the configured
Source384 checkpoint and planned through `llm_router`, then stopped before
coding. This establishes smaller input, not total provider-token savings or an
official Terminal Bench score.

## Measured result and controls

| Observation | Result |
| --- | --- |
| Complete rendered input | 65,222 → 64,254 bytes; exact restoration checked |
| Successful census planning | 23,824 input + 1,491 output = **25,315 native tokens** |
| Reasoning usage | 116 tokens, already included in output |
| Successful attempt elapsed time | 683.07 seconds including setup and cleanup |
| Source384 inference | 13.81 seconds, nested within initial context preparation |
| All three retained attempts | **50,500 known planning tokens** in two observed sessions; **1,839.67 seconds** |
| Coding calls / official verifier | 0 / not run |
| Reported cost / tokens per official pass | Unknown / unavailable |

The treatment was `common-bindings-instruction@1`, using lexical capsules and
semantic transport v1. The qualified Codex fallback used GPT-6.1 Sol/high through
`llm_router`; Intent autoencoding was explicitly disabled. This was not a native
Codex-harness comparison or a ranked-capsule performance experiment. The
byte-derived proxy fell from 16,306 to 16,064; it is not a provider token count.

Both failed attempts remain in the accounting. The first stopped before
planning and has no native usage ledger; the second completed 25,185 planning
tokens before JSON framing failed. Missing usage stays unknown. All owned
containers were removed and observed absent twice. Independent bounded review
checked arithmetic, identities, controls and cleanup without reading private
provider or owner-database bodies.

An earlier authored-plan census of the same public task measured 57,423 to
56,452 bytes (1.69%) with no provider calls. Its different plan/input scope must
not be conflated with the fresh live result.

## Integrated behavior and repairs

The benchmark CLI now carries `--capsule-selection verified-retrieval-symbol-rank@1`
through frozen controls, initial indexing, planning and admitted context.
Ranked profiles require an independently signed program/support source
partition. No-index and unpartitioned legacy profiles refuse the option before
indexing or planning. Default lexical behavior retains its existing receipts.

After source publication, the supervisor verifies predecessor ranking against
retained native evidence and refreshes pinned retrieval before selecting
successor capsules. Cold reload checks lineage and selection bindings. Missing
or stale retrieval refuses safely. Previously prepared experimental ranked
contexts need rebuilding; ranking does not authorize proof or omit required
facts. The lexical rebuilder still refuses changed vocabulary; learned rebuilds
require their separately pinned policy and assets.

Two runtime repairs were needed to close the live census:

- Sealed prompt capture reuses the existing Linux libc fallback when standalone
  CPython lacks `memfd` bindings. Anonymous descriptors, required seals, exact
  bytes and failure cleanup remain enforced.
- Logic-tree diagnostics go to stderr, preserving strict JSON stdout. A distinct
  Security Source384 compatibility profile permits only the exact reviewed
  diagnostic hash transition, optionally alongside the existing unrelated UI
  pin transition. All other implementation pins and checkpoint content remain
  exact. No checkpoint was modified, trained or uploaded.

Old/new inference matched exactly for the compared inputs except compatibility
metadata. The separately qualified public eigen.py sample still returns an
unsupported source contract. This is not evidence of whole-program proof
coverage. The archived runtime's projected-vector difference was at most
1.11e-16 across interpreters, with other native output fields unchanged.

## Qualification and publication

Initial ranking/benchmark qualification passed 401 distinct host cases and
16 repeated lifecycle cases in Docker. Portable capture passed 55 cases under
both native Python and the actual standalone CPython 3.12.12, plus a Docker
kernel-seal check. JSON/compatibility qualification passed 67 datasets and
18 supervisor cases, with another 18-case archived CLI check.

The larger Harbor run passed 325 cases and exposed one stale assertion expecting
11 dependencies after the required twelfth was added. The corrected exact-source
and tamper suite passed 98/98; the failed receipt remains retained. Publication
preserves concurrent proof-inventory work. Its merged metadata closure contains
41 paths, and **73 scoped postmerge checks passed**, including actual Lean/Z3
cold restart and existing bridge behavior, with unchanged sources.

The successful live archive SHA-256 is
`a70740cd83a848ca0193b315b7e2a0ed2f72f9e5770e3b15fcf00989d986b1f6`,
with 27,467 verified ordinary members and datasets commit
`c1b1f65f254f5f3ee8f307cdddf923c62450f78e`. Its receipt remains bound to that
frozen source; it is not relabeled as a run of later merged code.

The refreshed archive04 verifies 27,468 members and all 41 metadata dependencies.
Its SHA-256 is
`1f2637d14981e2c3659c2bff7ad66d7509a17b942aead36067a75abf83142150`.
Source packaging is qualified; its deployment and full coding trials have not
run. Three schema-accepted full-arm recipes separate instruction deduplication
and ranked capsules from a lexical/legacy full baseline. They retain admitted
Intent defaults, with actual status unmeasured until execution, rather than the
census's explicit Intent disable. Native Codex/no-index commands are declared
only; no-index currently requires a different reply/setup-cache contract, so
that broader comparison cannot isolate indexing alone.

## Remaining measurement boundary

Run instruction deduplication and ranked capsules as separate full-run
experiments. Hold task inputs, provider/model, planning, reply contract and
resources fixed; retain failures and measure complete native tokens per
official verifier pass. Input-byte reductions alone do not establish savings.

Unavailable ranked refresh preserves a verified embedding observation on its
exception, but the runtime catch still exports only type/phase. Detailed failed
embedding usage remains a reporting gap; safe refusal is preserved.


Published implementation pins: ipfs_accelerate_py
`ffc6643826e546e5a0b3436b766b22f39f243b71`, ipfs_datasets_py
`c1b1f65f254f5f3ee8f307cdddf923c62450f78e`; ipfs_kit remains
`8ac00bb1974b1378e12091d546d8425af34049e0`.
The [detailed evidence and qualification matrix](https://github.com/endomorphosis/ipfs_accelerate_py/blob/ffc6643826e546e5a0b3436b766b22f39f243b71/docs/agent_supervisor/evidence/terminal-ranked-successor-20261012/README.md)
retains failed attempts, exact source inventories, test receipts and prepared
comparison recipes.

Local documentation gates and all 46 relative evidence links passed.
GitHub's [documentation-gates job](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38201578713/job/114655942687)
and the selected [datasets check](https://github.com/endomorphosis/ipfs_datasets_py/actions/runs/38201102071)
could not start because the account is locked for billing. No remote CI pass is
claimed; the validation above is local and source-bound.
