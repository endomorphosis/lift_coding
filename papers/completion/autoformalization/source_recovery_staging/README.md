# Autoformalization reconstruction staging

Open `build/main.pdf` for the review copy and `source_discrepancies.md` for limitations and the complete section/equation/table/reference mapping. `main.tex` compiles with the byte-identical local research style.

This is partial reconstruction, not completed AF-001 evidence or a submission-ready manuscript. Original empirical placeholders are unchanged.

Build from this directory:

```sh
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
```

`reconstruct.py` deterministically regenerates the recovered per-page source and mappings from `../extracted.txt`; it overwrites those generated files. Copy material into the actual manuscript directory before making reviewed source edits, or update the generator deliberately. It does not mutate runtime databases, tasks, or worktrees.
