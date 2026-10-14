# 127: Signed source replay after working-set preflight, 2026-10-14

A valid capsule-page reply could be followed by source drift after instruction
`@5` had already been marked current. The router now reloads the pinned public
instruction after working-set RPC, world checks and descriptor-context entry,
then confirms actual CWD still equals the allocated worktree before setting
provider-attempt fields. The [published fix](https://github.com/endomorphosis/ipfs_accelerate_py/blob/cb104896f55a28352feb8cd35c4b9991144c933a/ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py)
and [qualification record](https://github.com/endomorphosis/ipfs_accelerate_py/blob/cb104896f55a28352feb8cd35c4b9991144c933a/docs/agent_supervisor/evidence/router-signed-scope-closing-20261014/README.md) retain the complete signed
profile, compiled selection, source hashes/modes and both checkout baselines.
Legacy instruction routes retain their existing behavior.

The unchanged published parent `b184d30229b3b8f23a390ca24580962d44620536`
reproduced omitted-source drift reaching one capturing provider after a valid
page. Its one deliberate failed test is an independent control, not an extra
passing case or a demonstrated deployed exploit. The new positive combined
path restores exact native capsule bytes and original semantic transport.
Fifteen post-page drift cases and two descriptor-entry cases refuse before
provider dispatch, including omitted originals in both checkouts, artifact
bytes/permissions, executable modes, HEAD changes and CWD. Dispatch remains
false and `router_calls=0` on refusal.

The [final merged qualification](https://github.com/endomorphosis/ipfs_accelerate_py/blob/cb104896f55a28352feb8cd35c4b9991144c933a/docs/agent_supervisor/evidence/router-signed-scope-closing-20261014/qualification-02/commands.json)
passed **145 distinct tests across eight full suites**, including 18 new cases,
with zero failures, errors or skips. All **268 listed bindings** stayed unchanged:
217 accelerator and 51 datasets files. Elapsed time was 587.803 seconds, which
measures authored-test execution rather than production latency. The earlier
145-test pass remains separate; counts are not aggregated. The concurrent world
replay contribution `9763f00bc176073729b432783b312e77e6c3e704` is preserved,
with its three world modules added to the inventory. Incoming replay suites
outside this eight-suite roster are not counted.

The [documentation receipt](https://github.com/endomorphosis/ipfs_accelerate_py/blob/cb104896f55a28352feb8cd35c4b9991144c933a/docs/agent_supervisor/evidence/router-signed-scope-closing-20261014/documentation-checks-02.json) passed
all four exact local workflow blocks and checked 101 relative links and nine
anchors. The [sealed child manifest](https://github.com/endomorphosis/ipfs_accelerate_py/blob/cb104896f55a28352feb8cd35c4b9991144c933a/docs/agent_supervisor/evidence/router-signed-scope-closing-20261014/manifest.json) preserves
both qualifications, the unpatched control, raw outputs, source snapshots and
final documents. Listed bindings do not attest a complete import/toolchain
closure. The [proof-context guide](https://github.com/endomorphosis/ipfs_accelerate_py/blob/cb104896f55a28352feb8cd35c4b9991144c933a/docs/agent_supervisor/repository_proof_context.md)
and [improvement plan](https://github.com/endomorphosis/ipfs_accelerate_py/blob/cb104896f55a28352feb8cd35c4b9991144c933a/docs/agent_supervisor/reversible_codebase_views_plan.md)
now distinguish this closed host regression from remaining deployed handoffs.

Parent publication starts at `67778aeb76dcac7ae19671643255c5b871b2e879`.
Only the accelerator pin advances to `cb104896f55a28352feb8cd35c4b9991144c933a`. Datasets
`b1fd77597867ad31f1687edc8bff090caf3d3b7d` and kit
`40c98c71b95be750509ffdb21e7e5494d91b4e79` remain pinned. Actual datasets
execution used `a0f60d42f836571a0023515e92dfb0e5724f0d79`; all 51 listed
objects match the retained parent pin. The [compatibility record](../../artifacts/router-signed-scope-closing-publication-20261014/fresh-main-compatibility.json),
[parent checks](../../artifacts/router-signed-scope-closing-publication-20261014/parent-checks.json)
and [parent manifest](../../artifacts/router-signed-scope-closing-publication-20261014/manifest.json)
retain exact Git/source/document custody without rerunning tests.

Git, signatures, complete signed inventories, native owners, compiled capsules,
linked allocation and capsule paging are real. Combined regression cases author
same-process endpoint routing and UID metadata. The existing dispatch suite also
uses a registered inert Python socket client with authored UID admission.
Provider replies and usage figures are authored. No external provider, decoder
trainer, embedding encoder, solver, native proof kernel, Docker run, target
program or official task verifier is invoked by this qualification. No proof,
execution, completion, omission or token-saving authority is established.
Sequential checks provide no filesystem writer lease.

The [exact CI observation](../../artifacts/router-signed-scope-closing-publication-20261014/child-ci-observation.json)
records [run 38559235187](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38559235187)
for `cb104896f55a28352feb8cd35c4b9991144c933a`. GitHub concluded failure because of an account billing lock;
no hosted steps executed. The four documentation blocks passed locally.

Next qualify native task/claim/allocation and permission joins with the deployed
consumer. Preserve each IR family's schema/version, decoder-task and
8D/384D/768D inventory/checkpoint lineage. Existing trained weights and embedding
assets remain unchanged. Actual encoder conditioning, fresh semantic/text
reconstruction and per-family ModelManager registration still gate teacher
promotion and distillation; the parallel LegalIR findings remain separate.
Whole-session token trials must include planning, coding, retrieval, expansion,
edits, verification, retries and failures at matched official task success.
