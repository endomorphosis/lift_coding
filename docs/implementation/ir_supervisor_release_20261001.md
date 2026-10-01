# IR autoencoder and supervisor publication, 2026-10-01

The reviewed shared-IR and supervisor work is published through the pinned
`external/ipfs_datasets` and `external/ipfs_accelerate` submodules. The datasets
submodule tracks `main` for explicit future remote updates. Unrelated active
workspace edits, runtime databases/caches, and rejected weights are excluded.

Datasets release: `f4e28be225455add0f29259fa6ecf238d23c6316`.
It contains shared training and inference, expanded formal-logic projections,
semantic chunking, source qualification, immutable checkpoint catalogs, and
supervisor consumer documentation. Validation: 3,442 passed, 87 explicit optional
fixture/parser skips; 25 Hub tests passed after the publication pin update.

Five experimental structured 384D heads are available in the Publicus Intent,
Security, UI/UX and Legal model repositories, including an additional Security
source-style diagnostic profile. The original trained Legal head is also packaged
under a new source-compatible release; its weights, optimizer, original binding,
and core remain unchanged. All 32 training and 8 tuning inputs were checked before
that repair. All new releases passed cold-download hashes and offline inference
replay; all four canonical domain loaders were replayed through the actual catalog.

The [checkpoint release catalog](https://github.com/endomorphosis/ipfs_datasets_py/blob/f4e28be225455add0f29259fa6ecf238d23c6316/docs/autoencoders/experimental_structured_checkpoints.md)
records immutable Hub revisions, checksums, validation scope and the supervisor
configuration. The new structured profiles remain explicit opt-ins. Their reported
reconstruction and Lake checks concern authored bounded programs, not new
Terminal-Bench task scores or proofs of security correctness. The regressing UI
augmentation and Security legacy-repair head are excluded.

Supervisor release: `bdeffd9548810813cc4dd61b722c6f744095b49b`.
Validation: 654 passed, including all 127 dependency preflight cases. Eight existing
validation-scheduler tests fail identically on untouched upstream commit
`5306d49957bba7444a31639584e26378f3e3fb19`; these are not claimed fixed or passing.
The [supervisor validation receipt](https://github.com/endomorphosis/ipfs_accelerate_py/blob/bdeffd9548810813cc4dd61b722c6f744095b49b/docs/agent_supervisor/releases/20261001-ir-publication.json)
records their names, baseline comparison and test receipt hashes.

Publication used isolated worktrees based on current origin/main and normal
fast-forward pushes. Active original checkouts and concurrent work remain intact.
