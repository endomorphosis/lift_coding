# Law to Action — revised manuscript, 14 September 2026

Start with `paper.pdf`: 7 main pages and 23 pages in total.

- `manuscript/main.tex`: editable entry point.
- `latex_sources.zip`: portable LaTeX sources, official style, bibliography, citation audit, and build script.
- `supplement.zip`: matching anonymous supplement with unchanged scientific evidence.
- `review/citation_audit.md`: verification and corrections for all 40 references.
- `REVISION_NOTES.md`: restored ideas, presentation changes, and validation scope.
- `review/validation.json` and `checksums.sha256`: build and artifact integrity records.

Upload the files inside `manuscript/` to Overleaf and select `main.tex`. For a local build with pdflatex and BibTeX installed, run from this directory:

```sh
./build_pdf.sh /tmp/law-synthesis-build
```

Choose an output directory that does not exist. The script installs nothing; the output is `main.pdf`. The supplied workshop style stays in anonymous mode. `related_work.bib` is the single selected bibliography.

This revision combines the original architecture with the existing results; future extensions remain explicitly unmeasured. The previous handoffs remain unchanged. No external upload or submission has been performed.
