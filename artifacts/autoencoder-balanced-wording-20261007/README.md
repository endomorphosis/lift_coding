# Balanced source-wording continuation

This experiment tests whether a broader authored wording bank improves the 384D Legal decoder beyond another continuation on its existing bank. The parent reconstructs the original and existing normative TRAIN paragraphs exactly, yet makes errors on previously exposed development wording. The comparison changes the source auxiliary bank while matching original rule identities, template slots, update counts and inherited losses. It does not establish convergence or new legal-semantic qualification.

The completed comparison is documented in [RESULTS.md](RESULTS.md). Existing-bank continuation reached 33/48 exact exposed development paragraphs; balanced replacement reached 19/48 and regressed retained wording to 33/48. The latter is rejected. Preparation for a bounded two-bank replay follows separately; it is not a completed replay fit.

## Run map

- `predeclared-comparison-protocol.json`: fixed parent, losses, draw budgets, selection, endpoint and panel requirements.
- `candidates/source-results-freeze.json`: exact reviewed source/result bindings, including the 90 rejected drafts. Candidate review checks authored fixture alignment; all natural-law, training-admission and proof flags remain false.
- `review/candidate-pair-independent-review-draft-r3.json`: independent audit of all 180 pairs, 48 packed paragraphs and source exclusions.
- `runtime/experiment-source`: private experiment adapters and entry scripts. Importing these helpers starts no training. Use the owned run guardian after actual phase readiness; do not invoke the numerical entry script directly.
- `guardian`: phase budgets, local asset inspection and independent mechanical readiness. A passed phase review is not a semantic admission.
- Actual phase outputs belong under `external/ipfs_datasets/workspace/test-logs/decoder-balanced-wording-20261007`, in fresh attempt directories with resource, source and execution receipts.

## What stays controlled

Both arms start from the same E selected 384D weights, with fresh optimizer and scheduler state. The published parent does not provide an Adam-state resume. The six source strata draw the same original rule and template slot in both arms for all 170 steps. Source text IDs and hashes remain authentic; this new schedule is not a replay of E's old source-hash schedule. The original decoder training stream, existing source losses, 384D original auxiliary and original source-fidelity selection are retained. Both wording auxiliary weights are 0.05.

The new 180 clauses reuse 90 known TRAIN meanings and contain obligations, permissions and prohibitions. They use explicit deontic infinitives and possessive gerunds. Literal source novelty and operational exclusion do not make their meanings a fresh holdout. The 48 packed paragraphs have the same target token sequences and rule order as E; only their source wording and source bindings differ.

Native preparation reads only the 48 source rows and the local asset profile. It produces 216 source/paragraph embeddings using verified gte-small384 assets, batch four, CPU float32 and the existing 512-token ceiling. No weights are downloaded. Before fitting, the same parent is measured on both complete clause banks and on actual new-bank greedy generations. If the new bank is already classified correctly, any change is reported as confidence or coverage evidence rather than classification repair.

## Retention and interpretation

Preserve all nine inherited postfit panels at both selected and last-attempt endpoints. Computed results may be shared between endpoints only after exact tensor-hash equality; reports must distinguish computed and logical denominators. Separately report original TRAIN, normative TRAIN, balanced TRAIN and exposed-v3 paragraphs, including all seven formal facets, omissions, extra rules, ordering, EOS and full32 source/recurrent/combined readouts. Exposed-v3 and sealed60 labels are never optimizer inputs or checkpoint selectors.

The current 32-token normative codec covers empty conditions, exceptions and temporal qualifiers in this authored lane. It does not demonstrate nonempty qualifier coverage. Native logic-family and Lean gates remain independent. Only an actual `lake build <Lib>` is a Lean admit. These runs do not execute Lake, grant `roundtrip_ok`, promote checkpoints or formalize the Constitution. The 8D linguistic teacher, 768D and 4096D lineages and archived restart12 checkpoint remain preserved.

Timing is CPU-only feature/reconstruction timing: workers one, bridge names empty, external provers false and metric disk cache disabled. New source embeddings are actual local forwards; OS page-cache warmth is uncontrolled. No bridge-on legal-IR speed claim can be inferred from these runs.

The inherited original384 paragraph/context vectors are caller-byte authenticated and lack a saved encoder-producer receipt. The existing normative384 bank and this new384 bank have separate actual local-producer evidence. Preserving the original numerical stream does not upgrade its provenance or establish a verified whole-corpus semantic representation.

The executed inherited initializer logs tree-pin imports from its explicitly frozen historical numerical tree. The reconstruction callback validates `legal_formula_codec._rule` schema; this is not a current-workspace compiler run. These measurements cannot establish canonical-tree legal-IR success or speed. Any compiler-facing admission must separately use the workspace compiler/decompiler/parser at `external/ipfs_datasets`, with `require_workspace_logic_tree()` and the unchanged actual Lake gate.
