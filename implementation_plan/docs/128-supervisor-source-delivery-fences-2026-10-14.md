# 128: Native source-delivery closing checks, 2026-10-14

The source broker replayed selected originals through retained CAS while
holding SERVER. A caller's CAS callback could then enter native claim checks
in the wrong lock order. The broker now releases SERVER for both selected-source
delivery replays, completes task/allocation fencing afterward, and checks
protected endpoints before its detached closing section. That section preserves
the original owner, task, allocation and nomination, checks both complete source
populations, and checks the selected original bytes in both roots. It is shared
with the existing launch checks without changing their order.

The final accelerator publication is `e21d6e7b41f14f3994b0fd8556bfcd341d9e888c`. Its
[source-delivery guide](https://github.com/endomorphosis/ipfs_accelerate_py/blob/e21d6e7b41f14f3994b0fd8556bfcd341d9e888c/docs/agent_supervisor/source_lookup_worker.md#close-source-delivery-after-broker-replay)
and [sealed evidence](https://github.com/endomorphosis/ipfs_accelerate_py/blob/e21d6e7b41f14f3994b0fd8556bfcd341d9e888c/docs/agent_supervisor/evidence/source-worker-delivery-fences-20261014/README.md)
record the exact boundary. Refusal before the backend call incurs no source
RPC. Refusal after validating a native reply preserves the already incurred
response/wire bytes without returning a success. These checks grant no proof,
execution, completion, edit or omission authority and no filesystem writer lease.

The unmodified published base `09ad10bd0e6694db7b0570614ab289184a0713c5`
reproduced the lock-order error in one deliberately failing control, in 26.873
seconds, before attempting native reentry. The first full run stopped during
fixture setup because the temporary path exceeded the Unix socket pathname
bound. Its failed raw record and runner/source snapshots remain unchanged. A
shorter unique temporary root fixed the runner; runtime source and tests were
unchanged. The next run passed **166 distinct tests across eight full suites**,
including 22 new cases, with zero failures, errors or skips in 933.237 seconds.
The 273 listed source bindings and fixed execution HEADs/indexes stayed fixed.
Those elapsed seconds describe authored tests rather than production latency.

The first qualified leaf `7883e693c5d90fbaa445a444eaeebc90789d9db1` was
published as a branch; its main push encountered concurrent world-packet audit
progress `8f5fa23317bc9609ea8cf7febf2d01c7b821f552`. Merge
`f58aa231805f2546d4f5cf650ef0bf3900d25540` retains both contributions and both
plan updates. The broker and new tests are unchanged; four other listed
accelerator sources changed. Original qualification/documentation records and
the first manifest, README and release-checker snapshots remain historical. A
fresh full qualification and documentation receipt bind the merged source.
Counts from the control, failed run, earlier pass and incoming world-audit
suites are not aggregated.

The final full-run record is `qualification-03/commands.json`: all 166 distinct
tests, including 22 new cases, passed with zero failures, errors or skips in
899.151 seconds. All 273 listed bindings and fixed HEAD/index guards stayed
unchanged. Its `documentation-checks-02.json` receipt passed four exact local
workflow blocks, 105 relative links and 14 anchors. Both belong to the published
child evidence phase. The manifest binds their raw outputs, exact source snapshots
and final documents. Its dependency population is explicitly listed, not a
complete import/toolchain closure: 222 accelerator and 51 datasets files.
Original prior evidence Git modes/blob IDs and reversible source/edit codecs
remain preserved.

Parent integration begins with original main
`0bb1beb9330f4e6122f9c6debde9af0ffeb524c6`, which already retains the newly
merged LegalIR actor-ranking research. Concurrent parent
`177aee9394ec524be81dfe81f09a743620a551c4` advanced the accelerator pin to the
incoming world audit. Parent merge `2ce0b414079c4e85485d230fc147e72ee9b3206a`
preserves that progress before this publication. The final parent advances its
accelerator pin to the independently published child while retaining datasets
`4b50ae4aac65da9166bd3b24608f32ba7e9fb23d` and kit
`40c98c71b95be750509ffdb21e7e5494d91b4e79`. Those are the actual test checkout
pins. All 51 listed datasets objects also match the child's embedded
`904f885c180eb9dfcdef80199f708125428d3859` pin; this is no whole-repository
equivalence claim. The [parent checks](../../artifacts/router-source-delivery-fences-publication-20261014/parent-checks.json)
and [parent manifest](../../artifacts/router-source-delivery-fences-publication-20261014/manifest.json)
bind publication custody without repeating pytest or the documentation gates.

The 22 new cases are owner-side reads through genuine native task/claim/grant,
Portal/allocation/lifecycle, Git/CAS and typed source connections. They target
each broker-owned replay, use actual native reentry, and test selected/omitted
source drift, task changes, revoked daemon/proxy grants, released claims,
descriptor bytes and socket modes. They launch no child. Other selected suites
also launch and reap real inert same-owner children. Listener and deployment UID
metadata remain authored host seams. No separate worker UID, deployed model
child, target program, provider, encoder, decoder trainer, solver, Docker run or
official task result is qualified. Constructor and privileged native gateway
CAS transactions remain separate callback boundaries.

The [exact hosted-CI observation](../../artifacts/router-source-delivery-fences-publication-20261014/child-ci-observation.json)
records [run 38607477860](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38607477860)
for the published child. GitHub concluded failure because of the account billing
lock; no hosted steps executed. The four exact documentation blocks passed
locally. No workflow dispatch or rerun was requested.

Next close constructor/backend callback contracts, then implement the reviewed
sealed writable delegation and authenticated native daemon/wrapper/child birth
handoff. Preserve the original owner-controlled allocation witnesses, native
claim and source-generation joins; keep the parallel candidate-launcher broker
contract separate. Independently qualify the signed profile and compiled
instruction on the actual worker before measuring a deployed token trial.

Reuse the existing CodebaseIR, IntentIR, SecurityIR, LegalIR and UI/UXIR assets
with separate family, schema/version, decoder-task and 8D/384D/768D identities.
The [merged LegalIR actor-ranking findings](https://github.com/endomorphosis/lift_coding/blob/0bb1beb9330f4e6122f9c6debde9af0ffeb524c6/docs/autoencoders/actor_context_ranking_20261014.md)
retain trained-parent reuse and a published candidate checkpoint, but complete
training reconstruction remains 154/168 and fresh development/test exact IR
remains zero. Latent conditioning was disabled; the configured 384 dimensions
were placeholders. It is an archived comparison rather than an accepted
distillation teacher. Actual encoder conditioning, fresh semantic and legal-text
round trips and per-family ModelManager custody still gate promotion. Measure
whole-session planning, coding, retrieval, expansion, edits, verification,
retries and failures at matched official success before claiming token savings.
