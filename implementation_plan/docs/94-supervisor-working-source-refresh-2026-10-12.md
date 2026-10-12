# Working-source refresh in the coding worker — 2026-10-12

An edit previously made the compact source reader unavailable for the rest of a
coding session. The isolated worker can now request a separate working-candidate
snapshot with `worker_source_client.py --path <path> --view compact --working`.
The reader remains behind the existing opt-in source-view profile and
`llm_router` coding route.

An unpinned first-page working request captures the whole admitted working-source
population, rebuilds its compact views, and checks the bytes again before
delivery. Each changed snapshot gets a generation bound to the source hashes,
immutable baseline/codec identity, session and sequence. Exact-original expansion
and continuation require that generation; they never refresh implicitly.
Working-source checks invalidate old generations on observed edits, including
continuations for unchanged files. Observed edit/revert cycles do not revive
earlier cursors.

The canonical source admission and semantic metadata stay unchanged. Both raw
and compact CLI output label working bytes as candidates and retain
`baseline_evidence_applicable: false`. This source-view refresh does not rebuild
DuckLake formal indexes, discharge obligations, refresh capsules or publish
accepted source. Numerical and native source readers retain their own freshness
checks. Editing still operates on the original allocated files.

The offline Docker qualification passed in 34.14 seconds with actual owner
UID 1000 and worker UID 1001. The worker edited and restored `eigen.py`, expanded
the edited original exactly, and exercised three distinct generations. Its edit
invalidated a working continuation for unchanged `eval.py`. All 18 negative
checks passed, including stale generation/pins, canonical drift, foreign peers
and baseline reads after edits. The endpoint and container were removed.

The collector matched 39 requests, 20 successful pages, 68,977 response bytes
and 23,157 returned source bytes. The reviewed authored call order attributes
14 requests and seven successful pages to working-candidate reads; the remaining
25 requests and 13 pages used the baseline path. These include repeated reads
and refusals. They are not unique source coverage or provider tokens.

The Docker fixture used one authored router hook and zero real model/provider
calls. It qualifies source refresh through the real worker boundary, not full
live supervisor START or an official Terminal Bench score. Required source
remains in the prompt. Formal-index/capsule rebuilding, mapped compact editing
and measured end-to-end token savings remain unfinished.

Scope stays fixed at the admitted paths, at most 64 files and 1 MiB of source.
New unadmitted files are not scanned or served; deleted, unsafe or oversized
admitted files refuse. Candidate cache state is session-local. Sequential source
checks do not establish an atomic filesystem lease or detect unobserved changes.

The combined regression completed with 1,164 passing cases, one failure and no
skips. The failure occurred before Doctor dispatch because Elan's `stable` default
resolved to an uninstalled Lean 4.35.0 executable. The exact case passed with the
installed Lean 4.34.1 executable explicitly pinned, without source changes,
global toolchain changes or skipped proof checks. All 1,165 distinct cases have
a passing result across these two runs; the original failed run is retained.
Production hashes remained unchanged throughout both runs, and local
documentation checks passed.

The accelerator implementation is published at
`17a1e73fa725effd795aa06dd0fd7257c63345b5`:

- [Working-source guide](https://github.com/endomorphosis/ipfs_accelerate_py/blob/17a1e73fa725effd795aa06dd0fd7257c63345b5/docs/agent_supervisor/worker_source_views.md)
- [Docker and regression evidence](https://github.com/endomorphosis/ipfs_accelerate_py/tree/17a1e73fa725effd795aa06dd0fd7257c63345b5/docs/agent_supervisor/evidence/working-source-refresh-20261012)

The parent retains datasets at `f47161b757190380e9898aff155067c1ad609217` and kit
at `8ac00bb1974b1378e12091d546d8425af34049e0`.

The hosted documentation job did not start because GitHub reported an account
billing lock. The [exact-commit CI observation](../../artifacts/working-source-refresh-publication-20261012/hosted-ci.json)
retains that infrastructure failure separately from passing local documentation
checks and the two-run regression result.
