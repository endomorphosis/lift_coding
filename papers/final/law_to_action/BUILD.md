The editable tree contains the exact ten allowlisted manuscript/build members from the final anonymous ZIP. Its large nested evidence archive is not separately expanded. Alternatively, from `editable/`, `sh build_pdf.sh /tmp/law-final-pdf-rebuild` uses an unused absolute output directory and an installed `latexmk`; the direct sequence below explicitly disables shell escape. The source README distinguishes the admitted fixed-action matrix from the separately executed generated-code 900-cell study.

Run from `editable/manuscript/` with a compatible installed TeX distribution and a fresh `../build` directory:

```sh
mkdir ../build
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=../build main.tex
bibtex ../build/main
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=../build main.tex
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=../build main.tex
```

These commands build only the copied manuscript; the handoff executor has not run them. Retain your actual toolchain, command logs and new PDF hash. Date and identifier metadata may differ, so byte-identical reconstruction is not asserted. Preserve the accepted `paper.pdf` and inspect page boundaries, fonts, citations and text after editing. No benchmark or model calls are necessary for a paper build.
