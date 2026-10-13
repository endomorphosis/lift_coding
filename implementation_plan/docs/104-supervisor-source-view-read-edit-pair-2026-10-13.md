# Matched source-view read/edit comparison — 2026-10-13

Accelerator `85b21ded006fa9850ab49ee9f33bd320457a79a5` adds a strict trace
comparator and qualifies an exact/compact read/edit pair in Docker. Both arms
produced identical source changes and restored the workspace. Compact views
reduced one-pass prepared-prompt plus CLI exposure by **133 bytes (0.17%)**.

| UTF-8 bytes captured once | Exact | Compact |
| --- | ---: | ---: |
| Prepared router prompt | 53,933 | 53,940 |
| Default CLI stdout | 25,429 | 25,289 |
| CLI stderr | 0 | 0 |
| Combined exposure | **79,362** | **79,229** |

The experiment uses `identity@1` and `python-comments@1` with the same public
`largest-eigenval` inputs, prescribed `idx` to `i` edit, 11 logical operations and
12 CLI calls. Optional catalog navigation costs 12,151 CLI bytes in each arm;
the filenames were already known. Both exact expansions and stale-read refusals
are charged. Native transport JSON is a separate ledger and increased by 64 bytes.

- [Implementation and interpretation](https://github.com/endomorphosis/ipfs_accelerate_py/blob/85b21ded006fa9850ab49ee9f33bd320457a79a5/docs/agent_supervisor/source_view_read_edit_pair.md)
- [Qualified scripts, controls, independent replay and tests](https://github.com/endomorphosis/ipfs_accelerate_py/blob/85b21ded006fa9850ab49ee9f33bd320457a79a5/docs/agent_supervisor/evidence/source-view-read-edit-pair-20261013/README.md)
- [Previous indexed reading plan](103-supervisor-context-reading-plan-2026-10-13.md)

The existing router, generated owner/worker launchers, broker and default CLI
ran with an explicitly authored generation hook, separate owner/worker UIDs and
network access disabled. Two fresh sessions reused one frozen native preflight;
their order was fixed. Static indexing, capsule/world construction and Doctor
diagnostics ran. Checkpoint inference, proof discharge, automatic repair, full
supervisor START and official task verification did not run. The authored rename
is not a benchmark solution. Provider tokens and official reward are unmeasured.

This comparison establishes the read/edit measurement mechanism, not an advantage
for the full indexed IR system. The
[subsequent prompt census](107-supervisor-metadata-projection-pair-2026-10-13.md)
established that this fixture already deferred both program bodies and retained
three harness support files inline. Prioritize
task-relevant source selection, small capsules and actual context substitution,
then compare repeated native model sessions with all-attempt usage and official
success. Model-facing compact-edit submission also remains open; these workers
edited expanded originals. Historical host-mapper evidence is linked by source
and postimage hashes without claiming another mapped application or numerical run.

Validation: **97 distinct tests passed**, including 41 comparator tests and the
existing source/candidate observation checks. All four local documentation gates
and additional links/anchors passed. The evidence manifest covers 44 artifacts.
Raw prompts, full source-bearing CLI traces, private stores and signing material
remain local; public scripts retain qualification-machine paths. The
[exact-commit hosted CI observation](../../artifacts/source-view-read-edit-pair-publication-20261013/hosted-ci.json)
records an account billing lock: the documentation job obtained no runner and
executed no steps. Local checks passed; hosted checks did not execute.

This parent publication updates only the accelerator pin and this report plus
[publication checks](../../artifacts/source-view-read-edit-pair-publication-20261013/parent-checks.json).
Datasets remains `b95938c2a816075466f8dc84f339cf622414030d` and kit remains
`8ac00bb1974b1378e12091d546d8425af34049e0`. Qualification itself used the retained
datasets checkout `f47161b757190380e9898aff155067c1ad609217`; it does not claim
execution against every change in the newer parent datasets pin.
