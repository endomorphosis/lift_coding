# Author review packet (AF-025)

This packet is an autonomous evidence handoff for the compiler-guided
autoformalization manuscript. Independent reproduction here means a separate
clean sealed-PATH execution environment; it does not require an outside person.
It does **not** record author sign-off, OpenReview upload, workshop submission,
or publication.

## Environment and commands

- Interpreter: `/usr/bin/python3.12` (`Python 3.12.3`)
- `PATH`: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- HOME prefix: `ipfs-accelerate-validation-home-`
- Standard library only for table regeneration and receipt inspection.
- LaTeX compilation is **not** empirical validation and was not used as such.
- Paper-tree `evaluation/analyze_results.py --check` was not executed because it
  rewrites undeclared result files; the declared feasible command is the
  anonymous ZIP regenerator.

Documented ZIP commands actually run:

```
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin HOME=<ipfs-accelerate-validation-home-*> \
/usr/bin/python3.12 -S regenerate_tables.py --check
/usr/bin/python3.12 -S verify_retained_inputs.py
```

Exact argv, timestamps, and exit codes are in
`papers/completion/autoformalization/evidence/final_reproduction.json`.

## Expected versus actual tables

| File | Expected SHA-256 | ZIP regeneration | Paper tree | Match |
| --- | --- | --- | --- | --- |
| `table6_pipeline.tex` | `a2ebba34895da30b383954e93ec582d2738a212d15de7b329fecf5a4d0c7aa49` | `a2ebba34895da30b383954e93ec582d2738a212d15de7b329fecf5a4d0c7aa49` | `a2ebba34895da30b383954e93ec582d2738a212d15de7b329fecf5a4d0c7aa49` | yes |
| `table11_training.tex` | `dcb2582f2c091a48b3c26bb1b1698e1287d70d77cc2c3824b4f1f822bd2d6e74` | `dcb2582f2c091a48b3c26bb1b1698e1287d70d77cc2c3824b4f1f822bd2d6e74` | `dcb2582f2c091a48b3c26bb1b1698e1287d70d77cc2c3824b4f1f822bd2d6e74` | yes |
| `table13_assistance.tex` | `655dfb58c0c1a960b636dbe35292ee243fbcb197fad1108f8a047742e2f62d3f` | `655dfb58c0c1a960b636dbe35292ee243fbcb197fad1108f8a047742e2f62d3f` | `655dfb58c0c1a960b636dbe35292ee243fbcb197fad1108f8a047742e2f62d3f` | yes |
| `summary.json` | `62e63725fe02f4ac9f9c5a3b397d0b2d9f9d7a1e25fc87e9eb7fdc21cb01cc72` | `62e63725fe02f4ac9f9c5a3b397d0b2d9f9d7a1e25fc87e9eb7fdc21cb01cc72` | `62e63725fe02f4ac9f9c5a3b397d0b2d9f9d7a1e25fc87e9eb7fdc21cb01cc72` | yes |

Unrun and unavailable cells remain labeled; they are not measured zeros.
Table 6 statuses: `{'unrun': 10, 'unmeasured': 5, 'unavailable': 5}`.
Table 11 statuses: `{'measured_inventory': 6, 'unmeasured': 6, 'unrun': 10, 'unavailable': 2}`.
Table 13 statuses: `{'constructed_automatic_labels_only': 1, 'constructed_hand_authored_weights': 1, 'constructed_replay': 1, 'unavailable': 3}`.

## Unavailable checks

| Tool | Sealed PATH resolution | Status |
| --- | --- | --- |
| `lean` | `not found` | unavailable |
| `lake` | `not found` | unavailable |
| `elan` | `not found` | unavailable |
| `z3` | `not found` | unavailable |
| `cvc5` | `not found` | unavailable |
| `vampire` | `not found` | unavailable |
| `eprover` | `not found` | unavailable |
| `coqc` | `not found` | unavailable |
| `isabelle` | `not found` | unavailable |

Sealed-PATH native useful-proof cells stay unavailable, not 0/1913 soundness.
AF-027 development Lean/Z3 receipts used operator-local binaries that are not on
this PATH; they do not receive Table 6 credit and were not replayed.
pdflatex/latexmk are also absent from sealed PATH; format evidence is the frozen
AF-024 PDF/log inspection, not a new compilation.

## Finished automated work

- Anonymous supplement, S01-S40 map, and table regenerators (AF-023).
- Official style/checklist/disclosure/PDF anonymity checks (AF-024).
- Claim ledger with 27 mapped claims (AF-022).
- Regenerable Tables 6/11/13 from frozen `summary.json` (AF-021).
- Finite constructed checks (12/12 match) and Q1/Q2 translation receipts (AF-006/AF-015).
- Sealed-PATH native-checker unavailability receipts (AF-018) and development
  Lean success/failure plus Z3 unsat sentinels (AF-027), explicitly non-Table-6.
- Structural-evidence scope: human fidelity unmeasured; teacher/prover not source gold (AF-028).

Retained automated claim IDs with hash-bound sources:
`ABS-SCOPE`, `ABS-T2`, `ABS-T1`, `ABS-FINITE`, `AE-VS-T`, `T1-MEMORY`, `T2-SHARED`, `AF029-NOT-TABLE11`, `NO-INVENTED-CHECKPOINT`, `PROP1`, `AF006-TWELVE`, `AF015-Q1`, `AF027-DEV`, `COST`.

## Measured failures and negative results

- Shared-parameter T2 accepted 0 sealed-PATH epochs (`update_counts=[0]`); H-T2 is unsupported.
- T1 train-versus-selection teacher cosine is a sample-memory diagnostic, not generalization;
  `claim_admissible_for_paper_primary=false`.
- AF-029 packed-CPU MiniLM updates remain `claim_admissible=false` and do not fill Table 11 held-out cells.
- C7 retrieval/planning/assistance utility is inconclusive on natural held-out cells.
- Sorry/admit/unapproved-axiom Lean fixtures are policy-rejected before any kernel claim.
- AF-027 `False:=trivial` is an explicit development type error, not a Table 6 success.

## Deliberately unrun or unavailable conditions

- Locked 1913-unit final-test A--E coverage, cost, and native useful-proof cells.
- Held-out independent source-semantic fidelity (no gold; teacher cosine is not this cell).
- T3 eligible native labels, T4 consumer load, and Arm E promotion (`e_locked`).
- Related-work systems (LeanDojo, DSP/miniF2F, Sledgehammer, Baldur, CompCert, seL4, Dafny) not executed.
- Independent 100-unit human review sample remains blank (`gold_records_with_values=0`).

Omitted/unmeasured claim IDs:
`ABS-HUMAN:unmeasured`, `ABS-FINALTEST:unrun`, `ABS-T345E:unavailable`, `C1:unrun`, `C2:unrun`, `C3:unrun`, `C4:unrun`, `C5:unrun`, `C6:unrun`, `C7:inconclusive`, `ARM-E-LOCKED:unavailable`, `RW-NOT-RUN:method_description`, `CONC:unrun`.

The AF-028 reporting scope does not convert those unrun training or human-dependent
cells into measured success. Unfinished required training is still recorded as
unrun/unavailable/unsupported.

## Human-dependent claims

Independent human agreement and source-semantic fidelity are **unmeasured, not
collected**. They are not replaced by prover success, teacher agreement, reconstruction
scores, or optional author comments. Outside reviewers and optional author feedback
are not manuscript-completion prerequisites. Optional author feedback was not supplied
and is acceptable in its absence.

## Remaining author-only items (cannot be invented)

1. Camera-ready names, affiliations, postal addresses, and emails for a non-anonymous `final` build.
2. Author verification of equations, examples, bibliography, checklist, and LLM disclosure.
3. Any additional model/provider/date/prompt/code/annotation assistance not already logged.
4. Camera-ready funding acknowledgements.
5. Actual OpenReview/workshop upload and licensing. This packet does not perform them.
6. Overleaf project membership remains unverified (historical HTTP 403).
7. Coding-shard license-risk rows stay unadmitted.
8. Optional independent annotation of the blank 100-unit sample.
9. Any license statement on the anonymous supplement beyond the hash-bound package.

## Deadlines

The reviewed CFP record (checked 2026-09-11 against
https://vericodegen.github.io/cfp.html) lists tentative AoE dates: abstract 2026-09-11
and paper 2026-09-13. Those dates are tentative. Authors must recheck the live CFP
and OpenReview before any external action. This packet performs no abstract upload,
paper upload, or author approval.

## Submission files and checksum identities

- Manuscript PDF: `papers/completion/autoformalization/submission/paper.pdf` SHA-256 `516f5bf2bc169bd7510b4421d1c6e5c02848a03e6df5b1170977e2a03558e147` (270925 bytes)
- Manuscript source: `papers/completion/autoformalization/manuscript/main.tex` SHA-256 `0912df8c2e702f1d0db369e72f5e92fc4ac0ddc926efc6dde0b187255e842656` (30946 bytes)
- Anonymous supplement: `papers/completion/autoformalization/submission/supplement.zip` SHA-256 `7437e6670058cd3e4cd417610fff4a8b0aef8fa4b2196554d4de302275b22fd1` (312081 bytes)
- Claim audit: `papers/completion/autoformalization/evidence/final_claim_audit.json` SHA-256 `796a507cf4cbfe0fcc246c534c02ddcd636c769b8cde87280161d12317db05e6` (19018 bytes)
- Results summary: `papers/completion/autoformalization/results/summary.json` SHA-256 `62e63725fe02f4ac9f9c5a3b397d0b2d9f9d7a1e25fc87e9eb7fdc21cb01cc72` (84488 bytes)
- Reproduction result: `papers/completion/autoformalization/evidence/final_reproduction.json` SHA-256 `8c4453adb04eedf031a9f4f5bd98d7b909aa79eb87c24ddcc2b45ea603930b3d` (43622 bytes)
- Checksum ledger: `papers/completion/autoformalization/submission/checksums.json`
  SHA-256 `b8bf91df8cbc4a9cf5a6b57f591f465f18d714e40d8b07e82099a12f60d02a32`

Official templates remain unmodified:
- `papers/neurips_2026_vericode_workshop.tex` `c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250`
- `papers/neurips_2026_vericode.sty` `2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11`
- `papers/checklist.tex` `780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6`

Checklist: 16 official questions with Yes/No/N/A answers
`Yes,Yes,Yes,Yes,Yes,Yes,No,Yes,Yes,Yes,NA,Yes,Yes,NA,NA,Yes`; statistical significance is No;
instruction block removed; Affiliation/Address/email is style-generated anonymous text.
Workshop footer and review line numbers are retained.

Analysis identity: `392407da2432633405e512e2e0b17e960ed89c2a3552f4a09959e73125fc4c43`. Scope policy: `AF-028/structural-evidence-scope/v1`
(SHA-256 `6373506c21a276388ef3ebf582d48d01a7aa5cc114ca414c0ca07a23f4f8ceea`).

## What this packet does not claim

- Authors did not approve the manuscript in this task.
- The paper was not submitted or published by this task.
- Independent human fidelity was not measured.
- Native useful-proof coverage on 1913 units was not obtained.
- Scope narrowing does not complete C1--C6 or hide T2/T4/E/AF-029 training status.

