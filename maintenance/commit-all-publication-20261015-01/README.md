# Commit-all publication — 2026-10-15

This publication follows the author's explicit request to commit and push the remaining local work, including submodules. It is separate from the frozen paper evidence audit; it does not change historical benchmark rewards, token totals, source pins, or evidence qualifications.

## Published source and repository pins

- `ipfs_accelerate_py`: `846a53dba17d711954a2f5f1a7268f7ad527217d` — 55 distinct source, test and documentation changes. Eight other selected local files already matched upstream.
- `ipfs_datasets_py`: `f9b69c7aadf099fb73f90c2853b72f8427f3ec63` — nine distinct source, test and documentation changes. Existing newer capacity diagnostics were preserved.
- MCP++, Kit, SwissKnife, Hallucinate and JevOps had no additional unpublished first-party source after comparison with current upstream and previously published snapshots. Their newer existing parent pins are preserved.
- The two Meta Wearables gitlinks advance to their already-published, clean local `main` commits. No changes were pushed to the Facebook upstream repositories.

The parent adds 1,299 reviewed authored source/reproducibility/manuscript files and 27 additional planning, discovery and supervisor-script files. Their exact original paths and hashes are recorded in `publication.json`. Eight conflicting local paper files are retained under `retained-local/`; these are **inactive local alternatives**. Current published driver and validation implementations remain active. See `retained_local_publication_review.json` for the scope difference; archival preservation does not qualify the alternatives for scientific execution.

## Nested vendor preservation

Distinct third-party changes are preserved as patches and, where necessary to omit sensitive unchanged content, base-hash-bound byte-edit recipes. See `third_party_patches/` and `extra_vendor_patches/` for base commits, origin URLs, exact result commitments, attribution and reconstruction checks. These archives preserve local edits; they are not approvals to apply the patches. Some edits are formatting changes and some affect documentation directives. No third-party upstream repository was modified.

The bounded nested inspection visited 72 initialized repositories under Hallucinate, through depth five. All 30 dirty first-party nested repositories matched non-gitlink source snapshots already ancestral to canonical published history. Multiple copies of the same vendor edit were deduplicated by exact content, while distinct variants remain separate.

## Validation and retained local state

Publication checks cover exact source/copy/staged blob identity, Python and shell syntax, structured-data parsing, sensitive-content screening, patch reconstruction and remote commit availability. They do not establish application behavior, formal correctness, checkpoint qualification, end-to-end integration or successful CI. No model, training, benchmark, theorem-prover, build or production-service execution was started for this publication.

The parent source review parsed 1,208 Python files and checked nine shell scripts. Additional plan/script and retained-local checks are recorded separately. Accelerate recorded 61 Python syntax checks and 34 isolated standard-library policy checks; Datasets checked four Python files. Whitespace diagnostics in original archival source are recorded without rewriting the preserved bytes.

The old live checkouts and indexes remain intact. They may still appear dirty against older local HEADs even when their source bytes are already published. The parent publication was prepared in an isolated checkout based on fresh `origin/main`, preserving concurrent published work. No force push, reset, clean or destructive checkout was used.

Generated databases, runtime archives, model weights, caches, downloaded dependency copies, raw model/SDK logs, lock files and process state remain local. The initial metadata inventory included approximately 116 GB of untracked material; that is not the Git payload. The exact reviewed source selection and 55 frozen/generated/dependency-copy exclusions are recorded here. This publication does not promise availability of every original runtime or dataset dependency.
