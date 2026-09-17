# Autoformalization paper completion review

Reviewed 2026-09-11. Paper: **Compiler-Guided Autoformalization with Adaptive Multi-View Representations**, `papers/autoformalization_training_methods_revised-1.pdf`. The PDF has 27 pages: main text pp. 1–9, references p. 10, appendices pp. 11–26, and a checklist placeholder p. 27. Page numbers below are PDF pages; printed line numbers identify finer evidence. Extracted text is retained in `extracted.txt`. No research experiments or native proofs were executed in this review.

The draft carefully distinguishes mechanisms from measured results, but is not empirically complete. Its main research question—whether shared learned representations and checked feedback improve independently judged source fidelity and useful proof coverage on unseen material—has no reported answer. Twelve finite semantic illustrations cannot fill that gap. The plan in `tasks.json` contains 25 bounded tasks for the autoformalization supervisor; it preserves the two experiment matrices the manuscript promises and the distinction between experimental failure and unfinished work.

## Exact missing fields and evidence inventory

| Location | Missing or incomplete item | Required completion |
| --- | --- | --- |
| Abstract p. 1, lines 18–21; introduction p. 2, lines 48–50 | Explicitly no new training or end-to-end performance; fidelity, retrieval benefit, native proof coverage, and total cost unmeasured | Execute frozen experiments and rewrite the evidence summary using actual results. |
| §2.2 p. 2, lines 69–87; App. I p. 18, Table 8 | Training counts, corpus, teacher/vector producer, label provenance, parameter state, partitions, execution configuration, proof-feedback population, promotion consumer all unspecified | Freeze dataset/annotation and experiment manifests, including mock versus real vector provenance and parser-assisted features. |
| §4.3 p. 5, lines 164–168 | Repeated validation selection; fallback to training examples when validation absent | Disjoint training, model-selection, fixed-canary, and untouched final-test groups, with source-family/temporal grouping. |
| §8 p. 9, lines 347–349 | Explicit `[To complete: ...]` field | Checkpoint/configuration identities, training/split counts, teacher-vector provenance, enabled heads, held-out fidelity, independent proof-transfer results. |
| App. A pp. 11–13, Tables 2 and continuation; lines 405–416 | S01–S40 map is only anonymous role descriptions; private audit ledger/frozen implementation not supplied; integration status to fill | Exact commit/blob/path/range map, import paths and runtime route identities, plus anonymous supplement. |
| App. D pp. 14–15, Table 4 | Claims twelve executed reference checks and 26/64 strong-until disagreements; cites `evaluation/reference_semantics.py` and expected-output JSON | Recover referenced files and rerun independently from supplied source; manuscript-specific sources are still absent; research template/style/checklist are now available in `papers`. If unavailable, reconstruct with explicit new provenance and distinguish historical from current evidence. |
| App. E pp. 15–16, Tables 5–6 | **20 `[TBD]` cells**: arms A–E × sources/covered, fidelity/uncertainty, correct transfers, cost/latency | Matched direct-model, deterministic, multiview, checked-bridge, and learned-advice runs with full denominators. |
| App. G pp. 16–17, lines 533–544 | LLM disclosure, author verification, anonymous implementation, and official checklist unfinished | Record actual material model uses and dates; obtain author review; package and check artifacts. |
| App. M p. 21, Tables 10–11 | **24 `[TBD]` cells**: T0–T5 × source/split counts, held-out fidelity, proof/route benefit, total cost | Deterministic, sample-memory, shared-only, proof-head, promoted-guidance, and code-repair ablations. |
| App. Q p. 26, Table 13 | Six proposed comparisons with no results | Retrieval modalities, premise selectors, guided planning, Hammer/Leanstral, proof heads, and actual promoted-guidance activation. |
| Checklist p. 27, lines 851–859 | **Two `[TODO]` paragraphs**; entire questionnaire absent | Use the now-supplied local `papers/checklist.tex` copy and complete against evidence; author review and frozen anonymous artifact remain required. |

Literal inventory: 44 `[TBD]` cells, one bracketed `[To complete: ...]` span, and two `[TODO]` paragraphs. Other occurrences of “TODO” describe supervisor mechanisms, not manuscript placeholders.

## Scientific review and required experiments

### 1. Establish a measurable contribution

The central hypothesis should be source-facet fidelity and useful checked proof coverage per total cost, not embedding similarity alone. The main text mixes engineered architecture, a feature-based multi-head learner, a conditional semantic transfer proposition, and numerous optional integrations. A primary claim and prespecified comparisons will help reviewers identify what is being established. The current main text already occupies the workshop's maximum nine pages, so replacing the evaluation plan with results requires compression of descriptive material, not smaller fonts.

Tables 5 and 10 answer different questions. A–E vary the source-to-proof pipeline, whereas T0–T5 vary learning and transfer. They must share a dataset and budget policy when appropriate, but need an explicit crosswalk rather than being silently merged. T1 must report seen-source reconstruction separately from unseen-source inference: enabling memory alone does not define a fair generalization condition. T2 versus T0 measures the shared learner; T3 versus T2 measures isolated trusted proof feedback; T4 versus T3 measures guidance actually loaded by the compiler/realizer; T5 must specify its fixed starting arm and the exact executable patch.

### 2. Prevent teacher self-consistency from becoming semantic gold

The default `build_us_code_sample` vector is `mock:stable-sha256`; the spaCy codec has a separate hashed-feature route. Family and view targets are derived from compiler/adapters (§2.2, App. I). Low loss against these targets establishes teacher distillation, not correct source interpretation. Training/evaluation must retain producer IDs and label lineage. Real semantic-vector claims require a real pinned encoder; otherwise explicitly evaluate feature hashing and keep mock embeddings as fixture controls.

Build independently annotated source facts, modality/negation, actors/recipients, quantifier order, conditions/exceptions, temporal anchors/windows, ambiguity, source spans, and admissible alternative readings. Keep test labels unavailable to candidate generation. Related sections, paraphrases, synthetic variants, derivatives, and all views of a source must remain in one group. Training, hyperparameter selection, fixed-canary admission, and final test must have different roles. Human annotation/adjudication that has not happened is an open dependency, not something an autonomous worker may assert completed.

### 3. Separate reconstruction and leakage paths

Equations 1–5 and App. H correctly distinguish numerical vector reconstruction from source-withheld symbolic/text cycles. Evaluate forward fidelity (gold → first IR), cycle consistency (first IR → second IR), and end-to-end fidelity (gold → second IR) separately. Add the twelve semantic distinctions in Table 3 and training probes in App. M: modal flips, scope movement, conditional direction, quantifier order, actor exchange, time-anchor changes, incomplete logs, and mismatched tenant identities.

App. E lines 493–494 prohibits source and gold access during source-withheld realization. Block text, source maps, locators, parser caches, retrieval recovery, sample IDs, and reference/gold fallback. Report parser-assisted features and their cost; do not describe an arm as raw-text prediction when it receives the target IR. The constrained decoder's 143-token/16-beam/64-step constants are configuration claims, not trained decoding quality (App. K).

### 4. Verify actual learning, promotion, and repair

The packed path uses SGD-style updates, masks, FP32 reduction, clipping, and optional BF16; App. J specifies total-sample normalization for masked cross-entropy. Run focused CPU correctness/parity checks and record whether parameters actually changed. A forward-only no-op, fixture test, or skipped CUDA test is not successful training. Multiple independent seeds and document-grouped uncertainty should accompany real training comparisons; commit/checkpoint IDs and final selected hyperparameters are required.

Proof heads are isolated from primary representations (§4.4, App. J.3). Evaluate both predictive calibration/abstention and downstream route value; retain eligible verifier version, duplicate/holdout exclusion, and protected-parameter fingerprints. T4 requires source-free export, paired fixed canaries, active-consumer load receipt, and rollback identity. The canonical profile explicitly disables learned guidance (§3.1), so training another module does not demonstrate changed canonical behavior. T5 needs the actual introspection → task → patch → validator → activation chain (App. K.3), preferably on development-discovered defects with final-test access blocked.

### 5. Ground proof transfer in executable coding examples

Proposition 1 (App. B) is a conditional paper argument, not a theorem that every implementation translator satisfies. Verify the supported fragment, premise preservation, goal reflection, related-model existence, and premise consistency for the evaluated bridges. The legacy TDFOL converter that erases modalities (§6.2) is a negative control; do not count a resulting solver success as a valid modal proof.

Execute the protected-write/audit example (§7), including safe and unsafe code, complete and incomplete audit windows, identity mismatch, and corrupted bridge assumptions. Bind the source-code extraction/refinement relation; a model of `Write = not Protected or Approved` is not verification of arbitrary code containing an approval keyword. Native proof coverage requires actual checker receipts with theorem statement, toolchain, fragment, and premises. Keep solver-local SAT/UNSAT, native reconstruction, counterexample, unsupported, timeout, unavailable, and abstention separate.

### 6. Isolate retrieval, planning, and assistance

Table 13 needs a matched corpus/query/budget protocol. Lexical, vector, graph, and any declared fusion route must retrieve real independent relevance labels and report accepted-premise yield. The thin-client vector option is declared but not dispatched (§5.1, App. N.2): choose an actual verified FAISS entry point or implement and test that route before claiming it.

The existing premise benchmark uses shared imports as relevance proxy, and its supplied selector weights are hand-authored (App. O.3). Report those facts; use actual dependency/usefulness labels before claiming proof-premise recall or a trained selector. Compare the same admitted sources and route budgets for deterministic/guided Tactician. Compare Hammer and Leanstral on the same goals and native checker; record candidate generation, reconstruction, accepted proofs, unsupported/timeout cases, and all failed-attempt costs. Preserve the paper's distinction between proposal generation and base-model fine-tuning.

### 7. Transfer and economics must match the retained claims

Legal/Security/Intent adapter compatibility is not statistical cross-domain transfer (§3.3, App. P). Use separate natural-document/code/trace strata and reviewed identity/time bridges. Compare legal-trained shared parameters with appropriate deterministic or domain-specific baselines if claiming transfer. Media claims need a measured extraction route; the present submission can keep media as a limitation without building an unrelated OCR/ASR benchmark.

Measure target construction, annotation, compilation, feature extraction, indexing, update/selection, validation, model calls, solver failures, native reconstruction, review, and repair. Report cold/warm cache status, local/provider resource costs, latency distribution, hardware, precision, and phase totals. CUDA speedup requires measured matched CPU/CUDA runs; absence of hardware remains unavailable, not a zero-time result.

## Claims and editing risks

The draft is unusually explicit about its evidence limits. Its main problem is missing validation rather than concealed quantitative claims. Preserve those distinctions while editing:

- Abstract “parameters are optimized” and “stable learned guidance reaches enabled consumers” can read as executed behavior; condition these on actual T2/T4 receipts or label them implementation capabilities.
- “Source-audited” and “one frozen snapshot” need the exact inspected revision and S01–S40 ledger; the present checkout may differ from the manuscript's private snapshot.
- Table 4's historical reference-check outcomes need their missing source/results; reproducing a newly written script is new evidence, not recovery of a historical run.
- Constructor/route availability is distinct from supported semantic fragments and live checker coverage.
- A CID binds encoding, not interpretation, training provenance, or proof authority.
- Quantitative cells must be generated from retained raw results. Report zero only for a measured zero; unavailable/no-run and an omitted claim require explicit status.
- Related work p. 10 has only ten references and very little comparison with current verified-coding/autoformalization systems. Verify each citation from primary sources and situate the final measured contribution using the workshop's topic; do not pad citations to unrelated theorem tasks.

## Confirmed code reuse and boundaries

Inspected checkout: monorepo HEAD `8601408d6406681a14a9488d31d1cd9a16164649`; `external/ipfs_datasets` HEAD `ac82107e246b30e35a2bbdcf75e01370d22350c6`. These are review-time identities, not the unknown manuscript-audit snapshot or a claim of a clean tree. Freeze overlays/imported paths in AF-003. The root-level `ipfs_datasets_py` is only a small partial tree; use and pin the external checkout deliberately.

| Existing path | Reuse and caveat |
| --- | --- |
| `external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_samples.py` | Dataset record, normalization, parser/frame target construction; `stable_mock_embedding` line 20 and `build_us_code_sample` line 88 make mock defaults explicit. |
| `.../modal_autoencoder.py` | Shared learner, encode/decode, proof heads, generalized training. `train_generalizable_projection` line 6922 uses `validation_list or sample_list` at line 6972: caller must enforce independent selection data. |
| `.../modal_autoencoder_cuda.py` | Packed objective/update and CPU reference; `apply_packed_projection_update` line 1165 and CPU entry line 1468. |
| `.../spacy_modal_codec.py` | Actual encoder/compiler/decoder/codec classes and feature hashing. |
| `external/ipfs_datasets/benchmarks/bench_semantic_logic_roundtrip.py` | Existing source-withheld harness separates forward, cycle, and final fidelity; pilot fixtures alone are not natural held-out evaluation. |
| `external/ipfs_datasets/benchmarks/bench_semantic_roundtrip_compositions.py` | Composition benchmark entry point to audit and adapt for supported bridges. |
| `external/ipfs_datasets/benchmarks/bench_modal_autoencoder_cycle.py` | Consumes real daemon summaries for cost evidence. **Its `--dry-run` synthesizes metrics and invokes no trainer/model/prover; dry-run output is never empirical evidence.** |
| `external/ipfs_datasets/benchmarks/bench_itp_hammer.py` | Hammer benchmark entry point; runtime availability and native checks still need preflight. |
| `external/ipfs_datasets/benchmarks/bench_itp_hammer_premise_selection.py` | Explicit import-overlap proxy, deterministic/gated selector, fallback check. Do not relabel proxy recall as true proof dependencies. |
| `external/ipfs_datasets/ipfs_datasets_py/logic/integration/reasoning/legal_ir_learned_guidance.py` | Promotion mechanism to audit for T4 and actual consumer wiring. |
| `external/ipfs_datasets/ipfs_datasets_py/logic/tactician/planner.py` | Bounded planner; execution and native results are separate. |
| `external/ipfs_datasets/ipfs_datasets_py/logic/TDFOL/tdfol_converter.py` | Legacy translation negative controls. |
| `external/ipfs_datasets/ipfs_datasets_py/vector_stores/faiss_store.py` | Actual vector-store candidate; preflight real dependencies/index backend. |
| `external/ipfs_datasets/tests/unit/optimizers/logic_theorem_optimizer/` | Focused CUDA, memory, proof-head, checkpoint, transaction, codec and feature-transfer tests; no passing execution inferred from existence. |
| `external/ipfs_datasets/docs/implementation/runbooks/leanstral_legal_ir_rollout.md` | Existing source-free feedback/promotion workflow and shared model-service ownership; modes and historical guides are not current experiment results. |

The initial search found no matching manuscript `.tex`, checklist, or `reference_semantics.py`. The user subsequently supplied the local research template/style and `papers/checklist.tex`; a fresh `papers/` source inventory still found no manuscript-specific LaTeX/BibTeX or reference-semantics source. The user supplied [an Overleaf source project](https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0) during review. Its contents and which PDF(s) it corresponds to are not yet verified; no source download is claimed. Recover authorized editable files there if access permits, without blocking independent protocol/code work on login or missing files. Rebuild from PDF only after recording what could not be recovered, with equations and bibliography checked against the PDF.

## Workshop and supervisor completion contract

The coordinator verified the [2026 research CFP](https://vericodegen.github.io/cfp.html): 4–9 main-text pages excluding references/appendices, the official 2026 workshop research template, double-blind text and linked artifacts, material LLM-method disclosure, PDF at most 50 MB, and supplemental ZIP at most 100 MB. Tentative deadlines are abstract September 11 AoE and paper September 13 AoE, 2026; confirm live CFP before submission. This PDF is only 312,201 bytes, but it is already at nine main-text pages and has a missing questionnaire. The last page must be replaced by a completed per-paper copy of the now-available `papers/checklist.tex`.

Run AF-001, AF-002, and AF-003 first. Data/annotation and harness work can then proceed independently before the learning and bridge/proof branches join in analysis. Store each experiment's output under this paper's own run directory. Use isolated worktrees for implementation changes shared with the other two paper supervisors, and shared model/GPU scheduling rather than overlapping unlimited jobs. Historical outputs and the other papers' measurements must not silently become this paper's results.

The supervisor should finish with a reviewable manuscript, raw evidence, regenerable tables, frozen implementation, completed questionnaire, and explicit remaining author-dependent items. It must not fabricate annotations, experiments, author sign-off, or publication/submission. If the deadline prevents the prespecified experiment package, prepare a concrete narrowed methods-only alternative with honest unmeasured claims for author decision; do not mark the full empirical goal completed merely by deleting the TBD cells.

## Local research-template update (2026-09-11)

The user supplied the formatting sources during this review. Use `papers/neurips_2026_vericode_workshop.tex`, `papers/neurips_2026_vericode.sty`, and a per-paper copy of `papers/checklist.tex`. A fresh inventory found only template/checklist `.tex` files and style files under `papers/`; the three editable manuscript bodies and their `.bib` sources remain absent. Template availability resolves the missing questionnaire source, while manuscript recovery/reconstruction and actual checklist answers remain tasks. Overleaf project contents/access are still unverified.

The research shell loads `\usepackage{neurips_2026_vericode}` with no options (line 10). Keep this anonymous submission default: it prints the workshop footer, hides the `ack` environment, and adds review line numbers. Do not use the supplied competition files, `sglblindworkshop`, `nonanonymous`, `final`, `preprint`, or the generic `neurips_2026.sty`. Preserve the user's originals and the style bytes; keep editable manuscript/checklist copies under this paper's directory and record input checksums.

The style itself intentionally renders **Anonymous Author(s), Affiliation, Address, email** (style lines 343–350). These strings are legitimate anonymous-template output, not missing author data. Do not patch the style to remove them or fail the scientific-placeholder scan solely because they appear. Remove actual unresolved result/disclosure/checklist fields and identifying author metadata/links.

The local checklist contains **16 questions**. Include the completed per-paper copy after the references and optional appendices, as the research shell does at line 461. Delete only its `BEGIN INSTRUCTIONS`/`END INSTRUCTIONS` block, retain the section heading, subsection headings, questions and guidelines, and replace every `\answerTODO{}` and `\justificationTODO{}` with an actual `\answerYes{}`, `\answerNo{}`, or `\answerNA{}` plus a 1–2 sentence justification. Answers must describe real evidence; unresolved author facts cannot be invented. The checklist does not count toward the main-text limit. Its LLM question concerns important/original/non-standard core-method uses; writing/editing/formatting alone does not require declaration under that question.

Two template quirks need no style modification. The shell comment says `\workshoptitle{}` is required but contains no call; the style defines/stores it while its research footer uses the fixed workshop notice. A reconstruction may set `\workshoptitle{NeurIPS 2026 Workshop on AI for Verifiable Coding}` to match the comment, and should inspect the resulting footer. Some instructional prose still calls the generic `neurips_2026.sty` the only style; the research shell's actual package load and workshop-specific research style are the relevant inputs. Main results supporting central claims must fit in the 4–9-page main text, even though appendices/checklist are excluded from that count.

