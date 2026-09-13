# NS-025 author-review handoff

This is an independent readiness audit of the already frozen anonymous
workshop package. It is a **ready-for-author-review** technical package.
It does not submit, upload, or publish anything, and it does not invent
author-owned attestations.

The operator asked this worker to read
`/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/ns024_final_artifact_handoff_v1.md`
(declared SHA256 `c9917e47d6a8b54fbd5dcaba4eb94bb13fb60b017d3462569726918bccaa2304`).
That private path is **not present in this worktree**. The in-repo NS-024
adopted PDF and ZIP match the hashes named in the task instruction, and
those bytes are the audited product.

## Decision

| Question | Answer |
|---|---|
| Is the technical anonymous package complete for author review? | **Yes**, with the measured limits below. |
| Are author-owned attestations complete? | **No.** See the outstanding list. |
| Was a portal action performed? | **No.** |
| May an automated process submit or publish? | **No.** |
| Is outside human review required by this track? | **No.** Human semantic fidelity remains unmeasured. |

## Exact files

| File | Bytes | SHA256 |
|---|---:|---|
| `papers/completion/neurosymbolic_supervision/release/paper.pdf` | 252576 | `0fb82abbec94c3858b6c9e63fcd456b16a5ad4aa2f294c4b52d08a8592c59862` |
| `papers/completion/neurosymbolic_supervision/release/supplement.zip` | 2280657 | `48cee756e4e1bcdcf4d541b6c8721f21cba0800e990e1159a64f3eeb888a0b07` |
| `papers/completion/neurosymbolic_supervision/release/reproduce.sh` | 1549 | `0ea4f3a6874008f10de37e63d3bbfa87351c653bea5036bb20dfb1ee8a0a58c9` |
| `papers/completion/neurosymbolic_supervision/release/manifest.json` | 5830 | `cd673ac98f1a058caf934174a93364e8199a438306ec38217bae0f6f885116c2` |
| `papers/completion/neurosymbolic_supervision/release/README.md` | 4113 | `b0f1c14dff71ab06858412dcb68ea781c5c89a094e47c2ca0752ffca9757a452` |
| `papers/completion/neurosymbolic_supervision/manuscript/paper.pdf` (NS-022, 12 pages) | 216541 | `907f0a24b775d22cbff1a35e958c2f121cbb4784756b2943dcee4eb5ae3e14ab` |
| `papers/completion/neurosymbolic_supervision/manuscript/main.tex` (NS-022) | — | `d10683b13e4fb0c5566e3b71fb7941fb2a95f1be5e1a50aa38957fe3092bf8ab` |
| `papers/completion/neurosymbolic_supervision/manuscript/checklist.tex` | 28079 | `48859ff3d74dd0fabfbd77a1579b5d51d2d226a5564fab9b81f27aa3c4b531b1` |
| `papers/completion/neurosymbolic_supervision/manuscript/neurips_2026_vericode.sty` | 13757 | `2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11` |

Release-directory checksums are also in `checksums.sha256`.

NS-024 compiled PDF layout, confirmed by sealed `pdfinfo` / `pdftotext -layout`
on this worker:

- main text pages **1–6** (within the declared 4–9 bound)
- references **7**
- technical appendices **8–12**
- LLM disclosure **13**
- official 16-item checklist **14–20**

NS-022 `manuscript/paper.pdf` remains the 12-page scientific manuscript
without disclosure/checklist. NS-025 did not overwrite NS-022 or NS-019
generated figure `8ea081bc`.

## Reproducibility commands

Sealed validation PATH is exactly
`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`. Interpreter
`/usr/bin/python3.12` (`Python 3.12.3`). No `pdflatex` is on that PATH.

Fresh numerical regeneration from the frozen ZIP (no provider, scorer,
hidden test, or signature replay):

```sh
PYTHON=/usr/bin/python3.12 /bin/sh \
  papers/completion/neurosymbolic_supervision/release/reproduce.sh \
  /absolute/new-extract-dir /absolute/new-output-dir
```

This worker's independent after-extraction run succeeded in 0.571 s.
The three unpooled children (`final32`, `prior`, `boundary`) passed.
`final32/numerical/summary.json` SHA256
`ae46fd4e9eb98004620d3533e59bee084c33c76b95829c469d196a034701a215`
matches the NS-024 recorded summary. Combined reproduction reports
`new_scientific_or_native_calls=0` and
`signature_authentication_performed=false`.

Ordinary NS-025 verification:

```sh
python3 scripts/paper_supervisors.py verify-task \
  --paper neurosymbolic_supervision --task NS-025
```

## Frozen claims (measured vs unavailable)

Governing freeze: canonical
`ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d`,
file SHA256
`7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a`.
This audit does not change the experiment after outcomes.

Measured, traced to `analysis/results.json`
(`6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e`),
regenerated `table17.tex` / PDF totals, and the reproduced final32 summary:

- eight independent families, 32 fixed cells, nested repetitions 104729 and 130363
- original 192-order/filter lineage with 160 withdrawn factor cells and eight unrecruited families
- useful completions A 5/16, B 4/16, mean B−A −0.0625
- conditional descriptive quality interval [−0.1875, 0.0], non-degenerate
- outcomes: full_cold_pass 9, hidden_acceptance_failed 7, known_proposal_failure 2, proposal_child_deadline 14
- API usage missing_or_invalid_count 16; `settled_charge=false`; missing costs are not zero

Unavailable, unmeasured, or withdrawn — not completed benchmarks and not
zero-filled:

- C/D routing, warm caches, reuse, publication-comparison efficacy, original 16-family inferential objectives
- human semantic fidelity, expert agreement, human time
- exact served Grok 4.6 revision/weights
- settled provider charges
- machine-checked formal arguments (NS-023: sketches remain unmachine-checked)
- original private-signature authentication and hidden-test rescoring

## Predecessor receipts

NS-001 through NS-024 each have a complete `paper-task-evidence/v1` receipt
whose snapshot artifacts still hash. Live files later owned by NS-022/NS-024
(and some runner/qualification paths owned after NS-001/NS-006/NS-010/NS-011)
are not treated as the predecessor outcome; the snapshots are. NS-023 noted
NS-011 as absent at its 2026-09-12 review; NS-011 is now complete.

## Placeholder, anonymity, template, checklist

Scientific/result/benchmark/checklist placeholder scan of the NS-024 PDF,
NS-022 PDF, snapshot `.tex` sources, and answered checklist: **no hits**.
Exempted only the official style-generated anonymous block:

```
Anonymous Author(s)
Affiliation
Address
email
```

PDF Author is `Anonymous Authors`. Workshop footer and review line numbers
are present. Fonts are embedded Type 1; no Type 3. Shared workshop.tex
`c1c74133`, research style `2944ec0d`, and unanswered official checklist
`780ba13c` match NS-001. Per-paper checklist answers
Yes/Yes/No/No/No/Yes/Yes/No/N/A/Yes/N/A/No/Yes/N/A/N/A/Yes with 16
justifications and no `answerTODO`/`justificationTODO` fields.

Supplement: 468 entries, no `/home/barberb` or gmail identity. Four executed
sources retain anonymized `/anonymous-runtime/operator-root/lift_coding/...`
correlation strings. That is not de-identification.

## Live deadline note

Root/operator CFP note (not independently fetched by this worker):

- deadline **2026-09-14T12:00:00Z**
- main pages 4–9, PDF 50 MB, anonymous ZIP 100 MB
- unchanged official template; author proofread and LLM disclosure required
- root claimed all three abstracts registered
- declared private file SHA256
  `0f7294cf7e1381104fb443a4a1c78acf58dfc06a3f73738752ad8534bbdeb1b3`
  was **not** present at the declared lift_coding path in this worktree

Measured package vs those declared bounds: 6 main pages, PDF 252576 bytes,
ZIP 2280657 bytes. A local date or this receipt is not proof that the portal
is open.

## Outstanding author-owned input

1. Author proofread of the final anonymous PDF/ZIP.
2. NeurIPS Code of Ethics review (checklist Q9 is N/A because that review is not in the preparation record).
3. Complete asset/provider terms confirmation (checklist Q12 is No).
4. Exact served Grok 4.6 revision/weights.
5. Whether any authoring task actually invoked configured `gpt-5.6-terra`.
6. Settled provider charges.
7. Human semantic fidelity, expert agreement, and human time.
8. Any IRB/consent/human-subject facts (no such study is reported).
9. Explicit authorization to submit or publish.

## What this completion is not

It is not OpenReview submission, camera-ready upload, publication, outside
peer review, or a claim that the task queue being done implies scientific
closure of withdrawn arms. Completion here is the independent readiness
record and the frozen evidence ledger.
