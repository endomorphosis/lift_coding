The manuscript is an editable reconstruction of the supplied PDF. Source
recovery and explicit baseline reconciliation are complete for NS-001; the
scientific paper, typesetting, and submission review remain unfinished.

From this directory:

```bash
/home/barberb/.local/bin/vericodegen-latexmk \
  -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex
python3 check_reconstruction.py
```

The absolute wrapper uses the installed user-local TeX Live 2026 toolchain and
works with a restricted worker PATH. Its installation provenance is retained
under `papers/completion/runtime_bootstrap/`. The successful build's command,
log, source/PDF hashes, and audit output are retained in NS-001's immutable
receipt snapshots. The build uses the unchanged research workshop style
`neurips_2026_vericode.sty`, with the official anonymous author block; it does
not use the competition or generic NeurIPS styles.

`main.tex` contains the complete editable body, abstract, numbered bibliography,
and appendices. It is self-contained apart from standard packages and the
copied official style. Six numbered equations are native LaTeX. All 18 tables
retain the exact extracted column text in preformatted blocks, with full
caption/table transcriptions and explicit typography follow-ups in
`../audit/reconstruction_discrepancies.json`. The 34 original `[TBD]` cells and
other results/disclosure/checklist placeholders remain unchanged.

`references.bib` preserves all 12 literal entries in note fields; it is a
recovery asset, not a claim that structured metadata has been verified. The
numeric bibliography in `main.tex` preserves the original labels. The
`abstract.tex`, `transcription.tex`, and `references.tex` helpers retain the
earlier modular transcription for review; the build does not depend on them.
`checklist.tex` is an unchanged, unanswered official input. The original
draft's obsolete placeholder checklist is retained and explicitly reconciled
in the audit, pending replacement under NS-024.

The audit checks the 778 original numbered text lines, every extracted table
line, references, equation tags, placeholder/numeric anchors, and unchanged
baseline/style/checklist bytes. It establishes recovery coverage and artifact
integrity, not mathematical correctness, measured research results, or complete
visual equivalence. Remaining inline script placement, line-wrap hyphens,
table typesetting, bibliographic verification, and final checklist/disclosure
work are assigned to NS-021 through NS-025 as detailed in the audit.
