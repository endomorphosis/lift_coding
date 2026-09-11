This is an editable PDF-derived staging reconstruction, not recovered original
LaTeX and not a completed paper. It preserves the draft's missing results.

From this directory, build with the installed toolchain:

```bash
/home/barberb/.local/bin/vericodegen-latexmk \
  -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

The absolute wrapper works even when a worker's PATH is restricted. It uses
the user-local TeX Live 2026 installation recorded in
`papers/completion/runtime_bootstrap/tex_installation_provenance.json`.
The measured build produced `main.pdf`, 24 pages, with no fatal errors or
overfull-box warnings. Underfull-box warnings and layout reconciliation remain.
The baseline has 28 pages; the changed count is not a claim of submission
readiness or verified formatting compliance.

`main.tex` uses an unchanged copy of the user-supplied research workshop style
and its anonymous author block. `abstract.tex` and `transcription.tex` contain
editable manuscript text; the latter labels each source page and original
numbered prose line. Six numbered equations use native LaTeX. Tables preserve
the extracted columns as editable preformatted text and still need proper
typesetting. `references.tex` preserves the original numbered reference list.
`references.bib` retains each literal entry in a note field; it is a recovery
asset, not a fully parsed bibliography, and is not used by this conservative
build. `checklist.tex` is an unchanged, unanswered copy of the official input;
the original draft's placeholder checklist remains in the transcription.

`python3 reconstruct.py` regenerates the staging source and recovery inventory
from the repository's original extracted text and local workshop inputs. It
overwrites generated `.tex`/`.bib` files, so do not run it after manual editorial
changes without preserving those changes first. It never updates task state.

The audits under `audit/` distinguish transcription coverage from visual and
scientific verification. All 34 `[TBD]` cells, the abstract results placeholder,
the final-results placeholder, disclosure blanks, and checklist TODOs remain.
No task-completion receipt is present.
