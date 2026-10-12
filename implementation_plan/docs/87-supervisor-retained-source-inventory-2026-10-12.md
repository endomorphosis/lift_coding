# Retained committed source and cold byte replay

The new host API retains complete committed Git source in the caller's existing
datasets `ImmutableCAS`, then reconstructs exact historical bytes after the
original checkout and Git objects are unavailable. This supplies the source
custody foundation for the
[repository-wide compact-view plan](85-supervisor-reversible-codebase-views-2026-10-12.md).
It returns data records rather than creating a filesystem checkout or granting
current-source, semantic, proof, execution or completion authority.

The [implementation and guide](https://github.com/endomorphosis/ipfs_accelerate_py/blob/2eda41dfebb0a92a88c069362c7c03c82fb7145e/docs/agent_supervisor/repository_source_inventory.md)
are published at accelerator `2eda41dfebb0a92a88c069362c7c03c82fb7145e`.
This parent integration preserves parallel LegalIR storage-recovery work and
datasets pin `c18390b350c7ab40f5bd342578204a03dc34fe05`, also used for qualification.
Its native content/CAS/acquisition/parser files match the preceding `c1b1f65` pin.

## Implemented boundary

`SourceInventoryRequest` binds independent task/repository, full commit/tree
and complete population identities. Typed hard-bounded limits govern file and
per-path bytes, metadata, native frame references and predicted export work.
Capture requires clean exact committed scope and the supplied CAS outside source.
It creates no competing content store, DuckDB owner, model or locator factory.

Native datasets complete preflight/chunk acquisition retains all committed paths,
raw path identities, Git modes and verified content. The existing native closed
manifest parser validates paged references, schemas, order, population, counts,
mode/type and contiguous chunks. Cold replay independently reads every retained
chunk, recomputes its raw CID, the whole source CID and Git blob hash.

Capture checks native frame/rehash work from metadata before initial content
reads. It retains verified frames and native manifest blocks, replays them,
rechecks source and publishes the inventory root last. It then replays the
actually stored root/content and rechecks source/store/input bindings before
returning. Request/limit bodies and physical CAS/configuration identity remain
checked around callbacks; duplicate page refs and total records are bounded
before metadata expansion. Failed capture may leave immutable artifacts, but
returns no successful reference. There is no atomic mutation lease or rollback.

Regular, executable, binary, non-UTF-8 and empty files retain exact committed
bytes. Symlinks retain target bytes without following targets or creating links.
Gitlinks retain exact child commit references with explicit missing-child-content
status. Duplicate blobs share stored content while every path remains present;
per-path materialization totals are separately bounded. Git executable mode
does not imply arbitrary POSIX metadata preservation. Git committed bytes are
distinct from checkout filter/newline transformations, dirty overlays and history.

Bounded host metadata pages include source/mode/object identities and Gitlink
frontiers, without source bodies. They are historical data rather than a Quack
operation or qualified coding-model expansion tool. Operational reuse needs
separately admitted current source/owner checks. Native frame export still
rehashes each whole blob per frame; no random-access/export-speed claim is made.

## Qualification and remaining work

[Retained qualification](https://github.com/endomorphosis/ipfs_accelerate_py/tree/2eda41dfebb0a92a88c069362c7c03c82fb7145e/docs/agent_supervisor/evidence/repository-source-inventory-20261012)
contains **54 distinct passing tests**: 28 new integration controls and 26 existing
reconstruction regressions, with normal AST sealing, isolated process state and
no skips. A fresh process loads exact bytes after deleting the authored original
repository, with source/Git producers and new-owner creation prohibited after
explicit store admission. Actual Git SHA-1/SHA-256, CRLF/LF, Unicode/binary/empty
bytes, modes, opaque names/links, corruption, independent pins, callback drift,
rehashed metadata attacks and early work bounds are covered.

The initial evidence collector's verbose node format was corrected before tests
ran. A subsequent EOF lint correction preserved the test AST including positions;
the same 28 cases passed again against final source. Both original and final
evidence remain, without counting repeated cases twice. Runtime source stayed
unchanged. Exact local documentation workflow steps, changed-guide links and
staged diff checks passed; hosted CI is a separate status.
The exact-commit [GitHub documentation job](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38205964432)
executed no steps: its failure annotation reports that the account is locked
due to a billing issue. No hosted CI pass is claimed.

Next implement compact source views with complete retained byte mappings, then
qualify exact current-owner source/capsule access through the coding interface.
Keep original-source edits first; mapped compact edits and mid-coding candidate
refresh remain separate qualifications. Rebuild and qualify the runtime archive
before worker deployment. Measure complete input and total native planning,
coding, expansion and repair tokens only after those interfaces are qualified.
This phase establishes no token savings or new Terminal Bench reward.

Existing LegalIR, SecurityIR, CodebaseIR and IntentIR inventories/embeddings and
8D/384D/768D checkpoints remain intact. No inference, training, model download,
Hugging Face upload, provider/prover call or full benchmark was performed.
