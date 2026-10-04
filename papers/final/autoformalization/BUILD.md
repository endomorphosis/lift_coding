# Build and evidence

This directory contains the completed empirical revision of the autoformalization paper. The upload pair is `paper.pdf` and `supplement.zip`. The manuscript uses the unmodified official workshop style.

From this directory, with Python 3, pdfLaTeX, BibTeX, and Poppler installed, run:

```sh
python build_paper.py
```

The script compiles `editable/manuscript/main.tex`, resolves citations, and checks the main-page limit, placeholder absence, PDF size, and anonymous metadata. Output is `editable/build/main.pdf`; the delivered `paper.pdf` is preserved until an author explicitly adopts a rebuild. Typesetting bytes can vary with installed TeX versions.

Extract `supplement.zip` separately and run its `python reproduce.py` command using Python 3.12 and NumPy 1.26.4. This regenerates metrics and tables from actual observations. Add `--proofs` with Lean 4.33.1 on PATH to recheck the 12 admitted generated proofs. Full model weights and the complete external runtime are not included.

The validated manuscript has 9 main pages. Its empirical populations are 1,913 units per native compiler arm, 100 direct-model units, three learned seeds on all 1,913 units, 5,739 learned check-order source/seed pairs, and 64 constructed proof goals. Independent legal-semantic accuracy remains unmeasured. The historical status-filled paper is preserved under the empirical revision directory, not as the current handoff.

`provenance/` and editable sources are local author support and can contain private host paths. Upload only the PDF and anonymous ZIP. No submission or author acknowledgment was performed.
