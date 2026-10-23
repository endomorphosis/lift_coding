# Law to Action — editorial revision, 14 September 2026

Start with `paper.pdf`. The revised manuscript has 5 main pages and 21 pages total.

- `manuscript/main.tex`: editable entry point; upload the manuscript directory to Overleaf and choose main.tex.
- `latex_sources.zip`: portable source package, official style, bibliography, and build script.
- `supplement.zip`: matching anonymous supplement with the revised manuscript and unchanged scientific artifacts.
- `EDITORIAL_NOTES.md`: changes and validation scope.
- `review/validation.json`: machine-readable integrity and build checks.

With an installed TeX distribution, from this directory:

```sh
./build_pdf.sh /tmp/law-editorial-build
```

Choose an output directory that does not exist. The script requires pdflatex and BibTeX and installs nothing. The output is main.pdf. The supplied workshop style remains in anonymous mode. Only related_work.bib is loaded; references.bib is retained for provenance and has duplicate inherited keys.

The prior final handoff remains unchanged. This revision is a separate editorial candidate; it has not been submitted or uploaded to Overleaf.
