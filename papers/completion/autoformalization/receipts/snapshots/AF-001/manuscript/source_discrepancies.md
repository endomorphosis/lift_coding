# Autoformalization source recovery audit

This is a staged reconstruction, not recovered author LaTeX or a completed paper. It changes no original PDF, shared template, lane worktree, runtime database, or scientific result.

**Original:** `papers/autoformalization_training_methods_revised-1.pdf`,27 pages. SHA256: `15a19fbfb7bc700c0827a8e48711422283f7703810689d3834a346826fbe5943`.

The existing layout extraction is preserved byte-for-byte in `original-layout.txt`; individual raw PDF pages are in `pages/page-XX.txt`. Every original numbered line1–859 is mapped with its page, text and recovered source path in `recovery-map.json`.

## Recovery status

- `main.tex` and `pages/page-XX.tex` provide editable prose. Original word-break hyphens and explicit line breaks are retained; no automatic spelling or semantic correction is asserted. The title, abstract environment, numbered section labels and anonymous author shell are reconstructed.
- All15 numbered equations have editable LaTeX in `equations/`. Equations2–5 and15 were checked against rendered original pages4 and22. The other equations are text-based transcriptions pending full visual/formal review. Inline subscripts, superscripts and accents are not reliably represented by PDF text extraction;12 source lines are mechanically flagged, but that list is not exhaustive.
- All13 tables have editable layout fragments in `blocks/`; original text, row values and column spacing are preserved without claiming fully recovered semantic cell boundaries. Tables2 and9 span multiple pages and remain multiple source fragments. Retype these as proper table environments before publication.
- Figure1 has editable boxes/arrows in `figure-01.tex`; its five-box information-flow structure and wording were compared with original page4.
- All10 visible bibliography entries are preserved in `bibliography/` and rendered literally on recovered page10. `references.bib` uses placeholder entry types with the full rendered reference in `note`, rather than inventing structured metadata. Convert to verified publication metadata and citation commands before submission. Existing bracket citations and artifact S01–S40 references remain literal text.
- The research style and user template/checklist are copied unchanged; SHA256 comparisons are recorded. The competition style is not used. Default research-style anonymous mode is used. The new official checklist is available in `inputs/checklist.tex`, but this recovery copy deliberately retains the original historical placeholder on original p27. It does not claim checklist completion.

## Missing historical material

The user-supplied Overleaf project https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0 was previously inaccessible to unauthenticated retrieval; project membership and contents remain unverified. This recovery does not claim an Overleaf download. A local search of papers found the user templates, but no manuscript-specific original LaTeX or BibTeX. A bounded filename search of papers, scripts, external/ipfs_accelerate and external/ipfs_datasets found no reference_semantics.py, reference_results.json, autoformalization source/archive, or audit-ledger match; this is not a claim of an exhaustive private archive search. The root evaluation/ directory was absent.

Original AppendixD(pp14–15) and AppendixG(pp16–17) describe a standalone reference suite and earlier LaTeX/research work. Those are preserved historical manuscript statements, not newly verified execution. The private source-audit ledger, exact inspected revisions, reference script/results, model checkpoints and empirical logs have not been recovered. Recreate missing reference code as a separately versioned artifact with independent expected outcomes; never backdate it as the original suite.

## Preservation checks and remaining work

Two pdflatex passes succeeded with shell escape disabled. `build/main.pdf` has31 review-copy pages; the extra notices and retained line breaks mean this is not a workshop page-limit check. Logs record164 underfull boxes, no overfull horizontal boxes, and no missing-character warnings. A successful build does not establish source fidelity or scientific correctness.

Re-extracting the compiled PDF found all15 equation numbers,13 table captions and10 numbered references. It retains exactly44 `[TBD]` cells,2 `[TODO]` markers and1 `[To complete:]` marker. These are preservation checks, not filled evaluations. `build/coverage-check.json` and `build/build.json` retain the counts, commands and output hashes.

Before using this for final manuscript work: audit inline math against the original PDF; replace layout fragments with verified cell tables; join line-break hyphenation by reviewed edits; convert bibliography metadata/citations; supply truthful official checklist answers; repair claims against real evidence; then check the actual main-text page count. This source work does not block independent dataset/protocol/harness tasks. No task-completion receipt was created.

## Section mapping

| Original section | Title | Original page/line | Recovered source |
|---|---|---|---|
| 1 | Introduction | p1, line22 | `pages/page-01.tex` |
| 2 | Representations and training examples | p2, line51 | `pages/page-02.tex` |
| 2.1 | What is shared, and what is learned? | p2, line52 | `pages/page-02.tex` |
| 2.2 | How examples and supervisory targets are constructed | p2, line68 | `pages/page-02.tex` |
| 3 | Compilers, decompilers, and reconstruction loops | p3, line88 | `pages/page-03.tex` |
| 3.1 | The deterministic source-to-symbolic path | p3, line89 | `pages/page-03.tex` |
| 3.2 | Two different meanings of reconstruction | p3, line103 | `pages/page-03.tex` |
| 3.3 | Constrained candidates and transfer beyond the legal teacher | p3, line116 | `pages/page-03.tex` |
| 4 | Adaptive multi-view learning | p3, line127 | `pages/page-03.tex` |
| 4.1 | Shared parameter state versus per-example memory | p3, line128 | `pages/page-03.tex` |
| 4.2 | Actual gradient objectives | p4, line140 | `pages/page-04.tex` |
| 4.3 | Guarded optimization rather than an unrestricted fit | p5, line156 | `pages/page-05.tex` |
| 4.4 | Proof-aware auxiliary supervision | p5, line169 | `pages/page-05.tex` |
| 4.5 | How learning improves deterministic formalization | p5, line180 | `pages/page-05.tex` |
| 5 | Retrieval, tacticians, and proof reconstruction | p5, line194 | `pages/page-05.tex` |
| 5.1 | Three retrieval signals, not three truth criteria | p5, line195 | `pages/page-05.tex` |
| 5.2 | The Tactician plans; the Hammer searches and reconstructs | p6, line208 | `pages/page-06.tex` |
| 5.3 | Leanstral proposals and verified training feedback | p6, line227 | `pages/page-06.tex` |
| 6 | How different IRs are used together | p6, line240 | `pages/page-06.tex` |
| 6.1 | Semantics are indexed by a profile | p6, line241 | `pages/page-06.tex` |
| 6.2 | Loss-aware translation | p7, line271 | `pages/page-07.tex` |
| 6.3 | A conditional proof-transfer rule | p7, line287 | `pages/page-07.tex` |
| 7 | Worked example: learned guidance and cross-view reasoning | p8, line300 | `pages/page-08.tex` |
| 8 | Evidence and evaluation plan | p8, line332 | `pages/page-08.tex` |
| 9 | Related work, limitations, and conclusion | p9, line356 | `pages/page-09.tex` |
| A | Anonymous implementation map and claim status | p11, line405 | `pages/page-11.tex` |
| B | Preservation contract and proof-transfer argument | p13, line417 | `pages/page-13.tex` |
| C | Modal semantics and adversarial minimal pairs | p14, line454 | `pages/page-14.tex` |
| D | Executable reference semantics | p14, line460 | `pages/page-14.tex` |
| E | Pipeline manifest, evaluation protocol, and result fields | p15, line478 | `pages/page-15.tex` |
| F | Source-grounded query procedure | p16, line505 | `pages/page-16.tex` |
| G | Completion, LLM disclosure, and artifact separation | p16, line527 | `pages/page-16.tex` |
| H | Learning-system anatomy and terminology | p17, line545 | `pages/page-17.tex` |
| I | Dataset construction and supervision provenance | p18, line561 | `pages/page-18.tex` |
| J | Exact losses, updates, and validation control | p18, line580 | `pages/page-18.tex` |
| J.1 | The packed differentiable step | p18, line581 | `pages/page-18.tex` |
| J.2 | The outer model-selection step | p19, line597 | `pages/page-19.tex` |
| J.3 | Proof-feedback heads and objective isolation | p19, line610 | `pages/page-19.tex` |
| K | Constrained decoding and learned-to-symbolic promotion | p19, line621 | `pages/page-19.tex` |
| K.1 | Grammar controls the candidate language | p19, line622 | `pages/page-19.tex` |
| K.2 | Feature export is not source copying | p20, line633 | `pages/page-20.tex` |
| K.3 | Program synthesis changes the algorithm, not just the weights | p20, line646 | `pages/page-20.tex` |
| L | Using IRs together: a concrete explanatory trace | p20, line657 | `pages/page-20.tex` |
| M | Training experiments and paper-completion fields | p21, line671 | `pages/page-21.tex` |
| N | Retrieval substrates and premise formation | p22, line683 | `pages/page-22.tex` |
| N.1 | BM25 in sample construction and corpus lookup | p22, line689 | `pages/page-22.tex` |
| N.2 | Vector indexing is separate from representation learning | p22, line704 | `pages/page-22.tex` |
| N.3 | Graphs connect evidence without silently adding axioms | p22, line718 | `pages/page-22.tex` |
| O | Tactician, Hammer, and Leanstral: distinct computational roles | p23, line734 | `pages/page-23.tex` |
| O.1 | Planning is deterministic until explicitly guided | p23, line735 | `pages/page-23.tex` |
| O.2 | The supported-fragment Hammer workflow | p23, line745 | `pages/page-23.tex` |
| O.3 | What the optional premise selector actually learns | p24, line761 | `pages/page-24.tex` |
| O.4 | Leanstral does not train itself by generating a draft | p24, line772 | `pages/page-24.tex` |
| P | Putting the representations and update loops together | p24, line789 | `pages/page-24.tex` |
| P.1 | Legal, Intent, and Security IR composition | p25, line821 | `pages/page-25.tex` |
| Q | Additional retrieval and proof-assistance evaluation | p26, line837 | `pages/page-26.tex` |

## Equations

| Equation | Original page | Recovered LaTeX |
|---|---|---|
| (1) | 3 | `equations/equation-01.tex` |
| (2) | 4 | `equations/equation-02.tex` |
| (3) | 4 | `equations/equation-03.tex` |
| (4) | 4 | `equations/equation-04.tex` |
| (5) | 4 | `equations/equation-05.tex` |
| (6) | 7 | `equations/equation-06.tex` |
| (7) | 7 | `equations/equation-07.tex` |
| (8) | 7 | `equations/equation-08.tex` |
| (9) | 8 | `equations/equation-09.tex` |
| (10) | 8 | `equations/equation-10.tex` |
| (11) | 8 | `equations/equation-11.tex` |
| (12) | 18 | `equations/equation-12.tex` |
| (13) | 19 | `equations/equation-13.tex` |
| (14) | 19 | `equations/equation-14.tex` |
| (15) | 22 | `equations/equation-15.tex` |

## Tables

| Table | Original pages | Editable raw fragments |
|---|---|---|
| 1 | 9 | `blocks/block-011.txt` |
| 2 | 11, 12, 13 | `blocks/block-012.txt`, `blocks/block-013.txt`, `blocks/block-014.txt` |
| 3 | 14 | `blocks/block-015.txt` |
| 4 | 15 | `blocks/block-016.txt` |
| 5 | 15 | `blocks/block-017.txt` |
| 6 | 16 | `blocks/block-018.txt` |
| 7 | 17 | `blocks/block-019.txt` |
| 8 | 18 | `blocks/block-020.txt` |
| 9 | 20, 21 | `blocks/block-024.txt`, `blocks/block-025.txt` |
| 10 | 21 | `blocks/block-026.txt` |
| 11 | 21 | `blocks/block-027.txt` |
| 12 | 23 | `blocks/block-029.txt` |
| 13 | 26 | `blocks/block-030.txt` |

## References

| Original citation | Original page | Exact visible text |
|---|---|---|
| [1] | 10 | `bibliography/reference-01.txt` |
| [2] | 10 | `bibliography/reference-02.txt` |
| [3] | 10 | `bibliography/reference-03.txt` |
| [4] | 10 | `bibliography/reference-04.txt` |
| [5] | 10 | `bibliography/reference-05.txt` |
| [6] | 10 | `bibliography/reference-06.txt` |
| [7] | 10 | `bibliography/reference-07.txt` |
| [8] | 10 | `bibliography/reference-08.txt` |
| [9] | 10 | `bibliography/reference-09.txt` |
| [10] | 10 | `bibliography/reference-10.txt` |
