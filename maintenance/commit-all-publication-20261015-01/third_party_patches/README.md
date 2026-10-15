# Preserved third-party working-tree edits

This archive preserves 176 changed-file observations across seven working-tree
variants from five third-party origins. These are saved local edits, not approved
upstream contributions, benchmark evidence, or changes applied to the active
dependencies. No third-party repository, working tree, index, branch, or remote
was modified.

`manifest.json` records exact source paths, base commits, origins, tracked and
advertised upstream heads, changed-file hashes, patch hashes, and original
license provenance. Seven full-index Git patches preserve 175 file edits. The
two additional MCP SDK variants have different bases and patches; they are
preserved separately rather than counted as independent implementations.

The Python changes are formatting-oriented: 37 files have identical parsed ASTs
and one differs only in its docstring. This static observation is not behavioral
qualification. Some MCP documentation edits alter MkDocs snippet delimiters;
those changes are archived as unapproved and should not be applied as a claimed
documentation fix. The current vendor copies and their upstream repositories
remain untouched.

The Lighthouse `tests/test_get_api_key.py` file contains an existing private-key-
shaped literal in its base revision. That literal is **not** exported. Instead,
`lighthouse-python-sdk-test-get-api-key.byte-edits.json` records exact base/result
hashes and offset/delete/insert operations containing only the changed bytes.
Applying those operations in reverse offset order to the independently obtained,
hash-verified original reconstructs the retained file exactly. No replacement key
is fabricated and the ordinary Lighthouse patch deliberately omits this file.

Original license texts are copied unchanged. The IPFS documentation README's
license section is preserved verbatim with its source hash; its descriptive
license wording and linked Creative Commons URL differ, and this archive does
not resolve that discrepancy. Original copyright attribution remains with the
upstream owners. These patches are not relicensed under the parent repository's
license.

Run the bounded, provider-free integrity check from the parent repository:

```sh
python artifacts/commit-all-publication-20261015-01/third_party_patches/verify.py
```

It hashes the archived outputs, verifies exact retained input/result hashes,
checks patch applicability against temporary Git indexes, and reconstructs the
content-omitting recipe in memory. It does not import vendor packages or run
tests, services, models, builds, or network operations. The source repositories
and exact base objects must still be available locally.

`preserve.py` documents the generation process and refuses to overwrite existing
artifacts. To regenerate, place a copy in a new empty output directory before
running it; it performs read-only remote-head queries as well as local reads.
The earlier vendor fingerprint inventory records duplicate copies separately.
Files absent from a fresh remote object store were not fetched solely to prove
upstream equivalence; stale tracked refs are explicitly recorded.
