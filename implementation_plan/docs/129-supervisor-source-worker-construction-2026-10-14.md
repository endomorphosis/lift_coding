# 129: Source worker construction custody, 2026-10-14

The source broker constructed its canonical reader and replayed its source
references while holding SERVER. Both operations invoke retained CAS, whose
caller callback can enter the native coordinator in the wrong lock order.
Construction now retains the original owner, gateway, source, connection, lock
and CAS witnesses before callbacks, copies admitted request/limits/paths/bounds,
then performs both canonical replays outside SERVER.

After replay, it completes native task/allocation/nomination fencing outside
SERVER and detached original custody, reference, complete-source and protected
boundary/parent checks before issuing a proxy grant. Its genuine typed client
opens outside SERVER. Mandatory exact-grant checks and the other closing checks
repeat before any public socket, descriptor or serving thread is published.
Existing launch/delivery checks reuse the detached custody helpers and retain
their order. There is no grant-free or partial-descriptor fallback.

Final accelerator publication: `bbcc1350141120b454a9d5e7648b48cf315047c9`. The
[channel guide](https://github.com/endomorphosis/ipfs_accelerate_py/blob/bbcc1350141120b454a9d5e7648b48cf315047c9/docs/agent_supervisor/source_lookup_worker.md#construct-the-source-session-before-publishing-endpoints)
and [sealed evidence](https://github.com/endomorphosis/ipfs_accelerate_py/blob/bbcc1350141120b454a9d5e7648b48cf315047c9/docs/agent_supervisor/evidence/source-worker-construction-20261014/README.md)
describe the implemented boundary. The [previous signed-instruction publication](127-supervisor-signed-scope-closing-2026-10-14.md)
and [source-delivery integration](128-supervisor-source-delivery-fences-2026-10-14.md)
remain preserved with their own original controls and qualification.

The unmodified base `e21d6e7b41f14f3994b0fd8556bfcd341d9e888c` reproduced
the constructor lock error in one deliberate failed control, with no setup error
or skip, in 24.167 seconds. The initial full attempt collected 194 cases but
stopped at the first new positive case because the implementation omitted the
`json` import used for frozen owner bytes. The failure occurred before a proxy
grant. Its raw record, logs, JUnit and source snapshots are retained. The exact
one-import correction and subsequent qualification have separate records.

The selected full qualification is `qualification-02/commands.json`: all 194
distinct cases passed across nine complete suites, including the 28 new cases,
in 1346.696 seconds, with zero failures, errors or skips. The authoritative raw record
retains collection, distinct JUnit identities, outcomes, elapsed time and
before/after source and fixed HEAD/index guards. No historical counts are added.
The documentation receipt is `documentation-checks.json`, with four exact local
workflow blocks passed, 111 relative links and 16 anchors checked. An initial
checker reference-order refusal and its reproduction are retained; reconstruction
now uses the runner's ROOT/datasets/kit order after JSON loading. The manifest preserves
all attempts, production/test/runner snapshots, reviews and final documents.

The listed dependency population is 275: 224 accelerator and 51 datasets files;
it is not a complete import/toolchain closure. Actual fixed datasets and kit
checkouts are `4b50ae4aac65da9166bd3b24608f32ba7e9fb23d` and
`40c98c71b95be750509ffdb21e7e5494d91b4e79`. Parent integration begins at
`53c06431d0ca7e57fdf74a67e21c6b61530f5042`, advancing only the accelerator
pin plus this phase's note/evidence. Prior parent objects, model findings,
dependency pins and child evidence Git modes/blob IDs are preserved. The
[parent checks](../../artifacts/source-worker-construction-publication-20261014/parent-checks.json)
and [parent manifest](../../artifacts/source-worker-construction-publication-20261014/manifest.json)
bind publication custody without rerunning tests or documentation gates.

Incoming accelerator main `c91c42512c6c0f25af2cef61b33d2f2b31ea6032`
changes only its embedded datasets pin to
`8fd82826e8ee935270457acfeee185054eb44aed`; the merge preserves that pin.
All 51 listed datasets sources match incoming Git bytes. Qualification still
uses the fixed `4b50ae` checkout and does not qualify the incoming native-engine
fixes or a complete dependency closure.

GitHub accepted the accelerator main push with its required-check bypass notice.
The [exact-commit hosted run](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38617505770)
for `bbcc1350141120b454a9d5e7648b48cf315047c9` failed before executing any
steps because of the reported billing lock. The [read-only CI observation](../../artifacts/source-worker-construction-publication-20261014/child-ci-observation.json)
retains run/job/check identities and annotations. Hosted gates did not pass;
the four passing blocks above are local evidence.

At each canonical load, the new cases reenter real native fences and test 12
mutations: selected/omitted originals in both roots, task body, daemon grant,
native claim, allocation lifecycle, genuine alternate source binding/store on
the same CAS, boundary bytes and parent mode. Pre-grant refusal leaves no proxy,
client, listener, descriptor or thread. Two additional cases mutate omitted
canonical source or revoke the newly issued proxy after the genuine client
opens. They require exact proxy revocation and transport closure before public
endpoints, preserving the original daemon grant and consumed reader/task/
allocation markers. Stable cases retain exact source references and source
bytes. Cleanup restores only temporary fixture changes and grants no rebind.

These 28 cases are owner-side checks using real Git/CAS, native claims/grants,
Portal allocation/lifecycle and typed connections, with authored listener and
deployment UID metadata. They launch no child or worker peer. Other selected
suites launch and reap real inert same-owner Python children. No separate worker
UID, provider/model, target program, encoder/trainer, solver, Docker or official
task result is qualified. Checks are sequential and provide no writer lease or
proof, execution, completion or token-saving authority.

Next qualify initial native binding and privileged `source.get` transaction
callbacks as separate boundaries. Preserve original owner/grant/task/source
witnesses, continuation reuse/expiry/bounds and incurred byte accounting while
closing after callbacks before reply publication. Then implement the reviewed
permission delegation and authenticated native daemon/wrapper/child handoff,
joining the signed profile and compiled instruction independently. Keep the
parallel candidate-launcher's worker broker contract separate.

Reuse existing CodebaseIR, IntentIR, SecurityIR, LegalIR and UI/UXIR assets with
independent family, schema/version, decoder-task and 8D/384D/768D identities.
Existing decoder weights and embeddings remain the starting assets; no new
training or model publication occurs in this phase. Actual encoder conditioning,
fresh semantic/legal-text reconstruction and per-family ModelManager custody
still gate teacher promotion and distillation. Include planning, coding,
retrieval, expansion, edits, verification, retries and failed attempts at matched
official success when measuring whole-session token use.
