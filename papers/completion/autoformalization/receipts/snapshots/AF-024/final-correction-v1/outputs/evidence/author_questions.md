# Author-dependent items remaining after AF-024

This packet separates facts already established by frozen logs from information
that only the authors can supply. It is not a scientific TBD list and is not a
claim of author sign-off or workshop submission.

## Known from logs (do not treat as unanswered science)

- The submission PDF is compiled from the local research style
  `papers/neurips_2026_vericode.sty` (SHA-256
  `2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11`) in its
  anonymous default mode. The style-generated block **Anonymous Author(s) /
  Affiliation / Address / email** is official template output, not missing
  author data.
- Arm A development used served **grok-4.6** on 2026-09-12 (prompt SHA-256
  `1d9b23b293a4d99932c23291242f90d2dad9d573c0c13e950beb3d7f2091fec8`). Codex
  `gpt-5.6-terra` was configured and not invoked.
- Grouping/teacher embeddings used
  `sentence-transformers/all-MiniLM-L6-v2` revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Historical AF-011 T0/T1 diagnostics
  used `mock:stable-sha256`; the actual AF-029 T0/T1/T2/T3 run used the pinned MiniLM vectors. Its three T2/T3 seeds completed, while target-assisted reconstruction does not establish source-free learning or fidelity.
- LLM plan nomination and Leanstral were not executed (zero model calls; no
  fine-tuning claim).
- Independent human source-facet labels were not collected
  (`gold_records_with_values=0`). Optional author feedback was not supplied
  and is not required for this task.
- Tables 6/11/13 retain unrun, unmeasured, and unavailable 1913-unit cells.
  Those are measured statuses, not author blanks.
- No public upload, OpenReview upload, or workshop submission was performed
  by AF-023 or AF-024.
- Shared user templates `papers/neurips_2026_vericode_workshop.tex`,
  `papers/neurips_2026_vericode.sty`, and `papers/checklist.tex` were not
  modified.

## Optional author input and future publication details (not manuscript gates)

1. **Camera-ready identity.** Real names, affiliations, postal addresses, and
   emails for the non-anonymous `final` build. The review PDF must keep the
   official anonymous block.
2. **Optional author verification of the manuscript.** Review equations, examples,
   bibliography, checklist answers, and the LLM disclosure against the
   authors' own knowledge. This packet does not assert that verification occurred.
3. **Additional model uses.** If authors used any other model, provider, date,
   prompt, code assistant, or annotation assistant that is not the logged
   grok-4.6 AF-027 call, the MiniLM revision above, or writing/formatting
   assistance already disclosed, record the served identity. Do not invent a
   version if the log is missing.
4. **Funding acknowledgements.** The anonymous style hides the `ack`
   environment. Camera-ready funding text is author-owned.
5. **Workshop submission.** All three abstracts are registered in the coordinating status record. This corrective build performs no paper upload and invents no author sign-off. The working paper deadline is 14 September 2026 noon UTC; final upload and licensing are separate publication actions.
6. **Overleaf source.** Project
   `https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0` returned HTTP
   403 during review; membership is unverified. Recover editable sources there
   if authorized.
7. **Coding-shard rights.** 4024 upstream `needs_review` license-risk rows are
   not admitted as natural data. Authors must decide any later admission; this
   task does not reclassify them as cleared.
8. **Optional independent annotation.** The 100-unit candidate-blind sample
   remains blank. Running it is optional for the supported automated-evidence
   manuscript and is not fabricated here.
9. **Asset license for release.** If authors want a specific license on the
   anonymous supplement beyond the documented hash-bound package, they must
   name it.

## Not author-blocking for AF-024

- Sealed-PATH absence of Lean/Z3/CVC5/Vampire/E/Coq/Isabelle.
- Unrun 1913-unit A--E/T0--T5 primary cells.
- Unactivated T4 and Arm E.
- Writing-only LLM assistance, already disclosed as non-core.
