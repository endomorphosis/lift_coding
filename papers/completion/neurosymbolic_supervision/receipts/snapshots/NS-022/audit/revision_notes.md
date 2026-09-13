# NS-022 revision notes

This completion adopts the accepted 12-page manuscript already present in
`papers/completion/neurosymbolic_supervision/writing_inputs/ns022_complete_manuscript_v1/`
(manifest SHA256 `1ee539aa44992c6f4aaae6b475921525380faecb15fe3e61b6aeae892da543af`).
It does not rerun models, scorers, contexts, proofs, or experiments, and it
does not create an outside-reviewer or publication gate. Official checklist
and integrated 20-page release work remain NS-024.

## Interrupted authoring history

The previous live `manuscript/main.tex` was the NS-001 PDF reconstruction
(SHA256 `46a14011d3ec69cf2b399d310b830901a59c4d50bb4834142103c5f171a70585`,
114696 bytes). That reconstruction still contained the abstract
`[RESULTS: insert ...]` placeholder and deferred table typesetting to this
task. Its snapshot under `receipts/snapshots/NS-001/` is unchanged. This
completion replaces only the live entrypoint and adds `manuscript/paper.pdf`.
It does not rewrite the NS-001 reconstruction snapshot.

## Allowlisted 21-file adoption

The accepted source tree has 22 files. One precise copy exception applies:

- Copy the other 21 allowlisted `source/` paths.
- Do **not** copy `source/generated/figures/family_useful.pdf`
  (SHA256 `001ddc3496915e7c21a52567551b36711a3dd4740ff12a0b4ae2402e56b96a06`,
  16554 bytes). That file is the retained original Matplotlib input. It has a
  historical Type3 font. Accepted `main.tex` does not reference it.

Live `manuscript/` writes authorized by this task are only `main.tex` and
`paper.pdf`. The remaining allowlisted sources are retained under
`receipts/snapshots/NS-022/manuscript/` with the same relative names. The
font42 layout PDF is archived as canonical base64 text
(`source_evidence/layout_family_useful.pdf.b64`) with a distinct digest; no
extra raw layout snapshot is created.

## NS-019 figure ownership

Live `manuscript/generated/figures/family_useful.pdf` remains the current
NS-019-owned handwritten ASCII rendering:

- SHA256 `8ea081bca5d5e309cc5659628b7ceea5e053089b3adfd1d5ae11a7f5c163e4a5`
- 5019 bytes
- family/arm coordinates and labels match actual results
- it is **not** the published Figure 1 and is **not** the original analyzer PDF

The published Figure 1 is the independent Type42 layout derivative
`layout/family_useful.pdf`, SHA256
`d70be87412a97285b440aef5de8b05c6fe575d3cbaf00b3abe34eae707146443`,
embedded CID TrueType DejaVuSans, no Type3. Accepted `main.tex` already
includes that path. The current SVG, Table 17, ablations, statistical report,
and cost report remain the NS-019 prepared products. NS-020 generated
`table18.tex` remains SHA256
`3fa332e34627a5825f6065623ac39bd3f0a5041627375d167e3fd397f33e2495`.
Those generated scientific outputs and the NS-019/NS-020 receipts were not
replaced.

## Historical root preparation versus this worker

Root assembled and visually reviewed the accepted 12-page PDF
`907f0a24b775d22cbff1a35e958c2f121cbb4784756b2943dcee4eb5ae3e14ab`
(216541 bytes; main 1–6, references 7, formal appendix 8–10, figure 11,
boundary/withdrawn tables 12). That historical compile used
`/home/barberb/.local/bin/pdflatex` in a private authoring tree. The local
`evidence/*.json` files retain those original absolute paths as historical
hash commitments, not files this worker had to rediscover.

This worker:

- verified the checkout writing-input bytes against `manifest.json`
- adopted that accepted PDF as live `manuscript/paper.pdf` and as the
  distinct task-owned snapshot `receipts/snapshots/NS-022/manuscript/paper.pdf`
- copied the accepted entrypoint as live `manuscript/main.tex`
- performed a **new** current-source compile with shell escape disabled using
  the worker TinyTeX binary
  `/home/barberb/.local/share/vericodegen-texlive/.TinyTeX/bin/aarch64-linux/pdflatex`
  in writable `/tmp` scratch after an initial absolute-`/tmp` BibTeX
  `openout_any=p` refusal
- recorded that worker compile separately from the historical root command

The worker PDF has 12 pages, 216541 bytes, identical `pdftotext` payload to
the accepted PDF, Type1 plus CID TrueType, and no Type3. Its SHA256
`2eb0e6dc18e6b21770e81f06ef77bb8544dfea47d1ea6bc8ea81262a18204e52` differs
from `907f0a24` (PDF identifiers/timestamps). The deliverable remains the
accepted historical product `907f0a24`. The worker PDF is not substituted
and is not stored as an extra raw layout/manuscript snapshot.

Sealed validation PATH `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
has `python3.12`, `pdffonts`, `pdfinfo`, and `pdftotext`, and does **not**
have `pdflatex`. Ordinary verification therefore inspects the adopted PDF
and accepted sources; it does not claim a sealed-PATH LaTeX rebuild.

The declared checkpoint directory was not writable (parent state mount is
read-only). Worker scratch used `/tmp/ipfs-accelerate-ns022-worker-relative-d6c2cdaa0536`.

## Scientific content preserved

Abstract, results, and conclusion keep the frozen 32-cell A/B local-cold
descriptive outcome: useful 9/32 (A 5/16, B 4/16); mean family B-minus-A
`-0.0625`; descriptive 95% percentile interval `[-0.1875, 0]`; 14 child
deadlines; 16 scoring invocations / 15 completed cold validations; API usage
16/32; settlement unavailable for all 32. Nested repetitions 104729/130363
remain design positions, not served API seeds. Original 192-cell lineage,
160 withdrawn factor cells, eight unrecruited families, the developmental
pilot, constructed controls, 1/26 false-reuse case, interrupted lease,
unknown charges, and unmeasured human semantic fidelity remain explicit.
C/D routing, warm caches, reuse, publication-comparison efficacy, and
original sixteen-family inferential objectives stay withdrawn. Conditional
formal arguments from NS-023 are retained verbatim in the appendix.

No TBD, TO BE FILLED, RESULTS placeholder, unsupported success assertion, or
unresolved internal artifact label remains in the scientific text. Table 18
`NS-NNN` identifiers are defined in the caption as internal qualification
records. Supplemental breadth (historical boundaries, withdrawn comparisons,
unmachine-checked formal record) is labeled as not evaluated final-repair
implementation.

NS-024 still owns the official 16-question checklist, anonymity/disclosure
package, and integrated release PDF.
