# T2 historical receipts and T4 original-receipt supplement

This supplement inspected 22 original files (3,600,308 bytes), producing 13 trial projections and 19 bound invocation/session projections. All 15 hash or structural joins and 21 arithmetic checks passed. These are retained-record checks, not independent experiment authentication. Original reports and the earlier audit were preserved; no model, solver, training, build, hidden-grader or supervisor-state operation ran.

| Trial | Profile | Reward | Reported native usage complete | Complete native total | Known retained counter subtotal |
|---|---|---:|---|---:|---:|
| fix-code-vulnerability__PtEnAhJ | native-codex | 1.0 | None | unknown | 177371 |
| fix-code-vulnerability__LpmwPSj | full | 0.0 | None | unknown | None |
| fix-code-vulnerability__eho8DzW | full | 0.0 | True | 21293 | 21293 |
| fix-code-vulnerability__79SoPKN | no-index | 0.0 | True | 292265 | 292265 |
| fix-code-vulnerability__nrCRphy | full | 0.0 | False | unknown | 265932 |
| fix-code-vulnerability__4Dfzugh | no-index | 0.0 | True | 288445 | 288445 |
| fix-code-vulnerability__DqsoZ7E | full | 1.0 | True | 308102 | 308102 |
| fix-code-vulnerability__2xXoTsQ | no-index | 1.0 | True | 317735 | 317735 |
| fix-code-vulnerability__jzhr9xA | full | 1.0 | True | 22040 | 22040 |
| fix-code-vulnerability__xRfZaYk | no-index | 0.0 | True | 439027 | 439027 |
| largest-eigenval__beFUuMt | no-index | 1.0 | True | 358492 | 358492 |
| largest-eigenval__8vAYxJm | native-codex | 1.0 | True | 113883 | 113883 |
| fix-code-vulnerability__z4cVfSR | full | 1.0 | True | 22749 | 22749 |

The ten named earlier security receipts all match the hashes in the original retained inventory. Their old trial IDs, failures, runtime revisions and counters remain distinct. The shared native control was not added again. Native trial `fix-code-vulnerability__PtEnAhJ` retains a known 177,371-token observation but no explicit session-completion marker; its complete total remains unknown. The interrupted full trial `__nrCRphy` likewise retains its reported subtotal without becoming a complete total.

Both T4 originals are recovered: `largest-eigenval__beFUuMt` (358,492 reported native tokens) and `largest-eigenval__8vAYxJm` (113,883). Their original receipt hashes match the earlier pair/three-arm reporting bindings; the native binding was independently corroborated by the root workstream in `audit/t4_native_report_join.json`. Their rewards remain 1.0. Complete reported native usage does not repair the recorded missing auxiliary usage or establish a complete bill.

For indexed T2 `fix-code-vulnerability__z4cVfSR`, the original outer receipt binds the Harbor result bytes, the standalone supervisor result equals the embedded result, and the separately retained reward file agrees at 1.0. The original verifier CTRF records **6 tests, 6 passed**; the original-repository CTRF separately records **367 tests, 367 passed**. These are separate scopes with overlap unestablished, so no combined test count is asserted. No names, bodies or reference patches were exported. Admission declares one internal validation, but declaration is not execution evidence.

Final accepted-root custody remains incomplete. The post-publication projection retains a semantic-root commitment, world-snapshot commitment and completion-receipt CID, and reports that the accepted source tree includes declared outputs. Yet its completion projection has empty attempt, claim and validation-run IDs and fencing token 0; goal-contract evaluation and live freshness are false. The earlier observation still says `pending_native_stop`. These facts cannot be promoted into a recovered final owner publication or executed internal-validation receipt.

The indexed trial artifact manifest reports an empty exported artifacts directory. A bounded filename inventory found 46 files within four levels and no owner journal or Lean axiom-output export. Container-local lifecycle/profile locations and sealed native/kernel store references are recorded as recovery leads. This is an exact custody gap in the inspected export, not proof the original events never happened or no other archive survives.

The pinned wrapper contains expected `#print axioms` strings and the retained kernel replay receipt reports success. Actual original Lean subprocess stdout is **not recovered**. The wrapper captures that stdout, checks expected lines, then emits its own JSON receipt; the wrapper stdout CID is therefore not automatically a commitment to raw Lean axiom output. None of those expected lines appears in the retained top-level supervisor stdout. No proof was rerun.

Old gap 10 is closed at the named-original-receipt level; old gap 11 is closed at the original-receipt/hash-join level. Gap 9 is partial: independent finite verifier summaries are now recovered, but final owner publication/internal validation remain unresolved. Gaps 12–14 retain their domain-specific limits; T1 archive or Intent weight verification elsewhere cannot establish T3/T4 Source384 weight bytes, complete X1 usage or learned source semantics. Related gaps 18/23 remain partial for the local T2 proof and unresolved for original axiom stdout/general correspondence.

Reproduce the bounded projection checks without overwriting this supplement:

```bash
python artifacts/paper-supervision-evidence-closeout-v2-supplement-20261015-02/workstreams/t2_recover.py --verify
```

The script reads only the explicitly named artifacts through the bounded reader and compares generated outputs. It does not import runtime packages, traverse databases, execute proof commands or reprocess raw provider transcripts.
