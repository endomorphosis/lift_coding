The convenient editable tree contains all 24 decoded sources from the accepted final build. The immutable `editable/carrier/` retains 22 text sources, two base64 PDF carriers, the source manifest and helper. From that carrier directory, `python3 -B build_from_snapshot.py --manifest-sha256 89bffcb1545d491945dba5604dc11ea3fa0a0a9745d2b3ef44b0fd85a1aa0973 --verify-only` validates them; optional `--output /tmp/unused-ns-build` materializes and compiles only into a fresh system temporary directory. The compiled plot is `layout/family_useful.pdf`, with embedded supported fonts; the original generated plot is retained separately. The copy has not changed NS019/NS022-owned files.

Run from `editable/manuscript/` with a compatible installed TeX distribution and a fresh `../build` directory:

```sh
mkdir ../build
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=../build main.tex
bibtex ../build/main
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=../build main.tex
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=../build main.tex
```

These commands build only the copied manuscript; the handoff executor has not run them. Retain your actual toolchain, command logs and new PDF hash. Date and identifier metadata may differ, so byte-identical reconstruction is not asserted. Preserve the accepted `paper.pdf` and inspect page boundaries, fonts, citations and text after editing. No benchmark or model calls are necessary for a paper build.
