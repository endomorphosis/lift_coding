# Autoformalization incompleteness audit

Audit date: 14 September 2026. This audit reads retained records and source code. It does not run training, inference, native checkers, or final-test evaluation, and it does not alter historical taskboards, receipts, checkpoints, or final handoffs.

## Finding

The final paper accurately discloses substantial unfinished evaluation, but the taskboard's completed status does not mean the original empirical objective was achieved. The primary final-test comparison was never run. Supporting development experiments and training did run, and those should be preserved and built upon.

This is not an accidentally stale PDF export. SHA-256 checks performed during this audit found that `papers/final/autoformalization/paper.pdf` and `supplement.zip` are byte-identical to the corresponding active worktree submission files:

| File | SHA-256 |
| --- | --- |
| `paper.pdf` | `18f21b7c212c9ba70e5fea229bf871df46af173d090ec8ee31cf14b67588ce16` |
| `supplement.zip` | `6b6940f1edf655c3fec544f48eee12793c7884499fdaf0dd2763e9a03adfcd2c` |

The active implementation and evidence tree is `.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/`. The top-level `papers/completion/autoformalization/` retains an earlier projection and does not contain the later 29-task implementation and result set. The final editable source is the later corrected compiler input, as documented in [BUILD.md](/home/barberb/lift_coding/papers/final/autoformalization/BUILD.md:1).

## How completion diverged from the requested work

The original AF-025 acceptance condition required completion of the empirical objective only when the required evidence existed; narrowed alternatives and pending choices had to remain explicit. See the original [taskboard acceptance condition](/home/barberb/lift_coding/papers/completion/autoformalization/paper.todo.md:938) and [individual criterion](/home/barberb/lift_coding/papers/completion/autoformalization/paper.todo.md:949). The original protocol also said budget exhaustion remains partial/unrun and cannot become full-goal completion: [protocol](/home/barberb/lift_coding/papers/completion/autoformalization/protocol.md:28).

AF-028 subsequently interpreted the user's statement that no outside reviewers were available as a decision to prepare a manuscript limited to retained automated evidence. That interpretation appears explicitly in the [scope amendment](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/config/structural_evidence_scope.json:6). The amended AF-025 criterion then became: “The manuscript objective is complete when every retained automated empirical claim has real reproducible evidence and omitted/unmeasured human-dependent claims are explicit.” See [AF-025 receipt](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/AF-025.json:125).

All 29 AF-001–AF-029 receipt files currently have `status: complete`. In particular, AF-016 was completed with all 20 primary pipeline cells still unrun, unmeasured, or unavailable: [completion scope](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/AF-016.json:165).

**Assessment:** the user was clarifying manuscript preparation and outside review, not abandoning automated evaluations. Absence of independent source-fidelity labels limits that particular metric; it does not prevent running compilers, structural checks, reconstruction diagnostics, exact-goal native checkers, or bounded proof-assistance experiments. Treating honest status reporting as completion of the broader empirical work was the central scope error. The current request explicitly resumes that unfinished engineering and evaluation work. Preserve the historical scope amendment as history and track recovery separately.

## Real experiments and their limits

| Work | Retained observations | Interpretation |
| --- | --- | --- |
| AF-029 native T0–T3 training | Seeds 104729, 130363, 155921; 69 training and 15 selection units with pinned MiniLM vectors. Each T2 seed accepted one epoch and applied all five packed update families. Each T3 seed applied 256 feedback updates. | Actual training occurred. It is development training, not the locked final test. T3 labels describe compiler-structural contracts. |
| AF-013 guidance export and canaries | Three checkpoints, 38 fixed canaries each, 114 diagnostics total. All three promotions returned `no_candidate`. | Export/load identity is demonstrated; applied learned guidance is not. T4 and Arm E remain unavailable. |
| AF-016 pipeline development | 75 selection records: A unavailable 15; B measured 11 and abstained 4; C measured 15; D unsupported 15; E unavailable 15. Six additional constructed-control records give 81 records overall. | Some structural pipeline evaluation ran. It did not measure final-distribution native proof coverage or source-semantic fidelity. |
| AF-027 runtime qualification | One real Grok-to-Lean development call, independent Lean success/failure controls, and Z3 checking; A–D development routes were exercised. | This established a usable runtime boundary. It was deliberately not a primary benchmark result. |
| Other supporting diagnostics | Twelve reconstructed finite semantic checks; 17 bridge records of mixed statuses; 72 constructed planning observations; retrieval and premise-selection proxies; proof-policy controls. | Finite/constructed/proxy evidence, not natural held-out performance. Record counts are not all successful proof counts. |

Training identities, seeds, update counts and teacher counts are in [actual execution: T2/T3](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evidence/final_correction/actual_execution.json:150) and [teacher population](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evidence/final_correction/actual_execution.json:200). The 114 canaries and promotion reasons are in [actual execution: AF-013](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evidence/final_correction/actual_execution.json:45). Selection counts are explicit in [AF-016 empirical execution](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/AF-016.json:57); its identity checks cover all 81 records at [line 91](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/AF-016.json:91). AF-027 documents real development mechanisms at [line 157](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/AF-027.json:157). Finite semantic scope is described in [reference provenance](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evidence/reference_provenance.json:80).

The original training/checker boundary failed after training because the checker ran out of memory. A separate retained-byte checker later passed; this does not turn the original container failure into a success. The corrected final handoff explains both outcomes at [line 9](/home/barberb/lift_coding/papers/final/autoformalization/provenance/author_handoff.md:9). The amended profile was CPU-only, two CPUs and a 64 GiB memory envelope, with 13,926.773996 seconds of exclusive training-stage wall time. See [costs](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evidence/final_correction/actual_execution.json:67) and [resource profile](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evidence/final_correction/actual_execution.json:132). Earlier failures and unknown interrupted usage remain historical costs; they should not be discarded or needlessly repeated.

## Missing or invalid efficacy measurements

The 1,913-unit final population was not evaluated. All 20 A–E result cells and the 24 T0–T5 table cells remain inventories or explicit missingness, not completed primary measurements. See [pipeline table](/home/barberb/lift_coding/papers/final/autoformalization/editable/results/table6_pipeline.tex:14), [training table](/home/barberb/lift_coding/papers/final/autoformalization/editable/results/table11_training.tex:13), and [final handoff](/home/barberb/lift_coding/papers/final/autoformalization/provenance/author_handoff.md:13). The natural held-out assistance comparisons are also unrun/unavailable: [assistance table](/home/barberb/lift_coding/papers/final/autoformalization/editable/results/table13_assistance.tex:13).

Independent human source-fidelity and agreement were not measured. No new human-review requirement should block independent automated engineering work; simply do not relabel automated metrics as those unmeasured human judgments.

T2's perfect cosine and zero MSE are **target-assisted**: the evaluated route can return the target embedding supplied to it. Family cross-entropy was unchanged from T0. Consequently these observations do not demonstrate learned source-withheld reconstruction or generalization, even though real parameters changed. See [metric limitation](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evidence/final_correction/actual_execution.json:119). A corrected evaluation must explicitly withhold the target vector and sample memory from the prediction path, and record any resulting failure or regression.

All three guidance promotions failed because of `proof_receipts_missing`, `missing_view_family_weights`, `no_canonical_contracts_resolved`, and `no_guidance_records_met_promotion_threshold`: [promotion gates](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evidence/final_correction/actual_execution.json:48). These are real integration gaps. Merely locating or loading a checkpoint cannot fill T4/E.

The final reproduction runs regenerated tables and verified retained-input hashes. They explicitly did not rerun training, checkpoints, native solvers, canaries, model calls, or final-test experiments: [reproduction exclusions](/home/barberb/lift_coding/papers/final/autoformalization/provenance/final_reproduction.json:14). Successful reproduction of missingness tables is not completion of the absent evaluations.

## Runtime isolation caused avoidable unavailability

AF-016 records `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`, a private HOME and no host toolchain: [environment record](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/AF-016.json:102). Arm A was not dispatched because `env -i` removed its model credential: [AF-016 limitation](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/AF-016.json:158).

Earlier AF-027 had already qualified worker-visible Lean 4.33.1 and Z3 4.15.4 using the research runtime, and documented how the default sealed PATH differed from the operator validation PATH: [qualified runtime](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/AF-027.json:182). It explicitly instructed later work to expose the research runtime in the worker boundary or use `IPFS_ACCELERATE_AGENT_VALIDATION_PATH`: [runtime advice](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/AF-027.json:296).

The corresponding historical executables were under `/home/barberb/.local/share/vericodegen-research-runtime/bin/`, with Python packages under the sibling `python/` directory. Their current availability should be freshly checked without launching a model. “Absent on sealed PATH” is not evidence that the host lacks these tools.

AF-027 also documented missing `multiformats`: native `TypedDeonticCanonicalCompiler` and `IntentFormalizationCompiler` imports failed, and B/C used stdlib replicas. See [dependency limitation](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/AF-027.json:291). The adapter implementations remain explicit about replicas at [B](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evaluation/pipeline_arms.py:920) and [C](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evaluation/pipeline_arms.py:958). Reusing them does not by itself establish native compiler evaluation.

## Fixed constructed assistance goals and native checker entry point

The pre-existing five-goal assistance pool is `ASSIST_GOALS` in [AF-018 measure_assistance.py](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/snapshots/AF-018/measure_assistance.py:312). These are constructed inputs, independent of the locked final-test corpus.

| Goal ID | Existing statement | Interpretation for a recovered run |
| --- | --- | --- |
| `h.fol_identity` | `forall x. P(x) -> P(x)` | Ordinary first-order identity. Pin the concrete Lean type/predicate binders. |
| `h.fol_protected_write` | `(Protected /\ ~Approved) -> ~Write` | **Not valid for arbitrary propositions without a behavioral premise.** Preserve it as a nonproof/countermodel control, or explicitly version a different theorem with a declared premise. Do not silently add an assumption to claim the original goal passed. |
| `h.fol_add_zero` | `forall a. add(a, zero) = a` with sort Nat | Pin `Nat.add` and `0` if that is the intended Lean interpretation. The first-order term names alone do not define arbitrary `add`/`zero`. |
| `h.unsupported_dependent` | `forall {α : Type} (x : α), x = x` | Unsupported by the frozen first-order Hammer translator; directly expressible in Lean. |
| `h.unsupported_higher_order` | `forall (p : (Nat -> Nat) -> Prop), p id -> p id` | Unsupported by the frozen first-order Hammer translator; directly expressible in Lean. |

The two `supported: false` flags describe the Hammer translation fragment. They must not be interpreted as Lean kernel limitations. The protected-write counterexample is immediate: Protected=true, Approved=false, Write=true. This interpretation follows the fixed formula and does not require opening any natural source record.

The old AF-018 script explicitly says it does not call a model and does not execute the native reconstruction path: [script contract](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/snapshots/AF-018/measure_assistance.py:2). Its `main` writes historical result paths, so **do not run that script in place** to recover the experiment. Read or copy its literal constructed inputs into a new versioned bounded evaluation instead. The old `model_call_authorized: false` field records that historical invocation; the user's present request authorizes temporary Leanstral recovery, subject to the requested resource/time bounds.

Callable native checking is available as:

```python
# Module directory:
# .worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evaluation
from pipeline_arms import lean_check_text

receipt = lean_check_text(fixed_theorem_and_generated_proof, purpose="recovery_fixed_goal_check")
```

[lean_check_text](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evaluation/pipeline_arms.py:853) creates a temporary Lean file and calls [run_native_checker](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evaluation/pipeline_arms.py:757), which uses a 30-second subprocess timeout and records source/binary hashes, exit status and output. `_which_or_absolute` at [line 516](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evaluation/pipeline_arms.py:516) checks PATH and the known research-runtime directory. Module import is separate from any call to `qualify_runtime.py`; the latter's qualification command includes a model call and should not be run as a mere availability probe.

The native checker wrapper alone does **not** reject `sorry`, axioms or changes to the theorem. A recovered harness must hold the goal and allowed premises fixed, admit only a proof body, reject unapproved executable/meta commands and proof escapes, and inspect the theorem's axiom dependencies. AF-018's historical lexical check at [line 819](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/snapshots/AF-018/measure_assistance.py:819) is useful as a first check but is not a complete proof-admission mechanism. This is necessary to make a kernel-acceptance metric meaningful, rather than an additional human-review gate.

## Recovery order

1. Requalify installed checker and Python paths; repair missing native compiler imports and record the exact versions actually executed.
2. Run the existing constructed proof-assistance goals in a new bounded experiment, with Leanstral started only for inference and stopped on success, failure or timeout. Preserve expected negative and translation-unsupported outcomes.
3. Locate and inspect the already trained autoencoder checkpoints via their existing custody manifests. Repair target-withheld evaluation before repeating multi-hour training.
4. Add useful automated development/selection metrics and exact-goal checks without requiring outside reviewers. Keep source-semantic fidelity claims limited to evidence actually available.
5. Repair learned-guidance exports/consumer integration on non-final data before granting T4/E credit.
6. Freeze the corrected models, metrics, supported fragments and budget before a sealed final-test run. A small constructed recovery run remains a development result and does not fill 1,913-unit population cells.

The ~325 KB supplement contains compact summaries and references rather than multi-gigabyte checkpoint payloads. Their custody is linked from [native adoption handoff](/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/evidence/native_training/adoption_handoff.json:1) into `papers/completion/runtime_bootstrap/unblock_20260912/af029_recovery/`. Checkpoint absence from the final folder does not imply training never happened.

Historical taskboards, receipts and final files were left unchanged. This report is an audit and recovery guide, not a claim that the missing experiments have now run.
