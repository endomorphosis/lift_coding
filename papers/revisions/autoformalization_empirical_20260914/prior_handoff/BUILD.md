The editable tree contains the exact corrected compiler input from `evidence/final_correction/build/`, including disclosure, checklist and anonymous metadata, plus three `../results/` tables. It does not use the stale recovery main or earlier build guide. The original host-specific `build_pdf.py` is provenance, not a portable command: it targets original worktree outputs and must not be run from this copy. The retained actual build used `SOURCE_DATE_EPOCH=1767225600`; set that variable for the commands below if reproducing its date convention.

Run from `editable/manuscript/` with a compatible installed TeX distribution and a fresh `../build` directory:

```sh
mkdir ../build
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=../build main.tex
bibtex ../build/main
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=../build main.tex
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=../build main.tex
```

These commands build only the copied manuscript; the handoff executor has not run them. Retain your actual toolchain, command logs and new PDF hash. Date and identifier metadata may differ, so byte-identical reconstruction is not asserted. Preserve the accepted `paper.pdf` and inspect page boundaries, fonts, citations and text after editing. No benchmark or model calls are necessary for a paper build.
