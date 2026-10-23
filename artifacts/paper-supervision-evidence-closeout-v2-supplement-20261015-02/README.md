# Proof-Carrying Neurosymbolic Supervision: evidence supplement

This is a continuation of the bounded local evidence audit for **Proof-Carrying Neurosymbolic Supervision: State, Reasoning, and Evidence Reuse**. It adds original artifact recovery and deterministic verification to the [frozen prior audit](../paper-supervision-evidence-closeout-v2-audit-20261015-01/README.md). The earlier audit and original reports remain unchanged. No benchmark, model, training, solver, test, grader, build, production-service or supervisor-state execution was started. No upload or push occurred.

The selected working paper remains increment-016, with the previously recorded exact title, abstract and 37-page PDF hash. Identity with the unavailable supplied PDF is still unresolved. This supplement neither changes the paper's supervision framing nor turns source/receipt recovery into evidence of a complete five-IR deployment.

## What was recovered

| Evidence | New result | Limit |
|---|---|---|
| Final T1 runtime archive | Its 1,349,592,874 bytes match the original SHA256; all **27,911** declared regular files, totaling 4,113,131,392 uncompressed bytes, match size/hash commitments. All 34 selected source/overlay pin checks match. | No extraction, code execution or import replay. Actual live loaded-module origins and executed Git forest remain unestablished. |
| Intent development backend | Its 2,243,486 bytes match the retained checkpoint descriptor. | Byte identity does not establish 384D architecture, semantic qualification or Terminal-Bench consumption. The previously reported 75/75 authored versus 0/3 weak-public holdouts remain unchanged. |
| Earlier T1 attempts | All seven earlier original receipts match their retained commitments; together with the final pair, all nine original outer receipts are recovered. | Three failed attempts still lack usage. Their pre-driver diagnostics do not turn unknown usage into zero. |
| Retrieval candidate | Original identity recovered as `fix-code-vulnerability__VkepsZo`, bound to the same two sessions and **548,438** tokens. | Identity repair only: no extra trial or token charge. Exact query-reference delivery remains unverified. |
| Frontier lead | The 18 hits belong to a zero-provider-call, authored qualification fixture. The production-quota probe chose full transport because frontier representation was larger. | This does not show live retrieval efficacy. Seven security-test failures are identified, but complete measured-path reachability is unresolved. |
| T2/T4 originals | Ten older T2 originals and both previously unread T4 originals are hash-joined. | No historical reward or total is changed; incomplete usage remains incomplete. |
| T2 validation | Original verifier **6/6** and separate repository suite **367/367** recovered. | These are separate scopes, not 373 established distinct tests. Final owner publication, executed internal validation custody and actual Lean axiom stdout remain missing. |
| Requests cohorts | All **23** original provider-call receipts recovered; cohort totals remain **108,981** and **243,255**. | Calls are not inferred conversation sessions. Both cohorts still complete zero trajectories; transport authenticity and settlement remain unverified. |
| Compositional/procedure evidence | Original records identify cvc5 1.3.3, Z3 4.15.4, 242 scoped import entries, both archive-consumption summaries and 136 distinct TEST procedure invocations. | The import recorder excludes dependencies outside its source root. Internal gate/dispatch counts are not repair trials; archive proofs do not prove execution truth. |
| Historical reuse analysis | Three exact Git versions recovered. NS-011 preserves **1/26** false reuse; later NS-027 removes reuse and enforces full cold validation. | The old selected 0/25 subset does not erase the adverse case. NS-027's 0/16 with zero admitted reuse is not a positive-reuse reliability estimate. |

The consolidated view preserves **85 existing mixed-unit rows**, including 39 Terminal-Bench rows: 38 identified invoked trials and one uninvoked slot. No experiments were added. The 82 usage observation rows comprise 49 actual session IDs, 31 call/invocation IDs and two unbound report observations. Newly recovered identities belong to existing trials. There is no combined project token total.

The bounded pass read 78 filesystem evidence files (13,018,171 bytes), six historical Git blobs (418,785 bytes), and the two named large assets. Archive hashing read the same compressed runtime a second time to verify member contents. The compressed/asset streaming total is 2,701,429,234 bytes; regular member hashing processed 4,113,131,392 bytes without extraction. Limits and operations are recorded in `authorization.json` and `audit/`.

## Files to review

- [Consolidated remaining evidence](consolidated/remaining_evidence.md): **5 closed, 11 partially closed, 3 unresolved and 8 unchanged** prior gaps. Closure applies to the named evidence field, not complete authenticity or formal correctness.
- `consolidated/runs.jsonl`, `sessions.jsonl`, `results.csv`, `identity_updates.json`: evidence overlays preserving old counters, rewards and schema-specific completeness assertions. The old frontier completeness assertion remains visible alongside the original envelope's missing strict field.
- `consolidated/encoder_deployment_ledger.jsonl` and `cross_ir_trace.jsonl`: checkpoint byte verification and identity updates, with no new semantic-stage qualification.
- [T1 report](workstreams/t1_report.md), [T2/T4 report](workstreams/t2_report.md), [historical report](workstreams/historical_report.md): original-record findings and limitations.
- `runtime_source_forest.json`, `private/runtime_source_files.jsonl`, `audit/runtime_member_verification.json`: complete declared archive file commitments and fresh verification.
- `workstreams/git_reuse_recovery.json`: exact historical commits, adverse counts, later removal and retained source commitments.
- `workstreams/git_population_leads.json`: an earlier file named “pilot” contains 76 developmental rows; a final plan lists 192 units with dispatch disabled. Neither is substituted for the selected manuscript's 24/32 cohorts.
- [Reviewer matrix delta](reviewer_matrix_delta.md) and [proposed sentence changes](proposed_manuscript/changes.md): evidence-supported edits, with an **unapplied** patch against the prior proposed addendum. Original manuscripts remain unchanged.
- `consolidated/checks.json`, `audit/independent_review.md`, `audit/final_consolidation_review.md`, `audit/integrity_report.json`: arithmetic, identity, review and integrity results.

Current/report commits, immutable archive files, actual loaded sources and historical action authority remain distinct. This pass does not fix the full cross-IR trace, unsupported decoder grammar or repository-training qualification. A loaded global checkpoint, codebase indexing, adaptation and independently qualified inference are still separate events. Historical benchmark rewards remain observed rewards even when the learned path is unqualified.

## Reproduction

Use Python's standard library from this directory. Projection outputs must go to a new directory; scripts refuse overwrites. None of these commands runs a model, prover, grader or benchmark.

```bash
python assemble_supplement.py --output /tmp/paper-closeout-supplement-replay-01
python workstreams/t1_recover_supplement.py --output-dir "$PWD/replay-t1"
python workstreams/t2_recover.py --verify
python verify_supplement.py --output /tmp/paper-closeout-supplement-integrity-01.json
```

The first command reproduces the consolidated projections and 139 assembly checks from saved audit projections. The T1 command re-reads its bounded original inputs. T2's verification mode checks its declared original file bindings and saved arithmetic. Historical recovery has 141 source-specific checks, preserved with the 23 call receipts in `workstreams/historical_*`. Hash equality verifies retained bytes, not provider or experimental authenticity.

The large-asset scripts and scoped Git recovery scripts are retained as exact inspection code. They use exclusive outputs rooted beside the scripts. To repeat them, create a new private directory, copy `authorization.json`, `audit_io.py`, the relevant scripts and their declared prerequisite metadata, then run in that new directory. `verify_large_assets.py` verifies two named asset hashes; `verify_runtime_members.py` streams the retained tar against its manifest, with byte/header/time caps; `project_runtime_forest.py` joins the selected freeze. No archive link is followed. Large assets are not re-read by the ordinary integrity command; it verifies the saved audit receipt binding and current file existence/size, with that limitation explicit.

The prior experiment proposals remain [unapproved](../paper-supervision-evidence-closeout-v2-audit-20261015-01/next_experiments.yaml). New behavioral claims, training, model runs, solver execution or a clean paper build would require separate approval under the handoff. No production restart or threshold change is implied by continuation of this evidence pass.

## Remaining decisions and custody

The original revision-package identity and H1/D1–D6/R1/R2 label mapping still need author resolution. The selected retained PDF still has 10 main-text pages; the nine-page limit and official workshop style are not newly qualified. The full multi-IR action trace, final T2 owner custody, actual Lean axiom output, exact 32/24 cell ledgers and complete pipeline usage remain open with precise recovery routes or proposed remedies.

This directory is private author material, not an anonymous release. It contains source paths, commits, task IDs, timestamps and stable hashes. No original signature is transferred to changed derivatives. API-reported per-request charges, where retained, remain separate from account settlement; no pricing-derived dollar total is inferred. Existing licenses and notices are retained in the original artifacts; this supplement exports commitments and bounded observations rather than source bodies, credentials, hidden tests or raw model transcripts.

The original disk-capacity request remains unresolved because the prior geometry inspection found no usable unallocated capacity. No disk, filesystem, reserve or admission setting was changed during this supplement.
