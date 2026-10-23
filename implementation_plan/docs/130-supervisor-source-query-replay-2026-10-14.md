# 130: Native source-query replay, 2026-10-14

The typed source gateway replayed retained CAS under SERVER, and the reader
published continuations before final gateway authorization. It now captures
original owner/connection/reader/store/grant and registry witnesses first,
releases SERVER for source-specific clocks and CAS replay, stages the response
privately, then closes native task/body, complete source, selected bytes and
actual grant before cursor publication.

A short-held private guard rejects overlapping or nested reads before waiting
for SERVER. A renewal completed before capture remains usable; replacing the
captured grant during replay refuses. The original connection must report
boolean false for transaction state before and after detachment. This read
starts no transaction and never rolls back one owned by another caller. Cursor
expiry pruning, one-use predecessor consumption and bounded successors commit
only after final checks; refusal leaves the predecessor intact. Request/response
schemas and validated source/envelope/wire accounting retain their contracts.

Final accelerator publication: `55c42dd740d75c3ba04d6991c90cf0aa0dccd8a9`. The
[channel guide](https://github.com/endomorphosis/ipfs_accelerate_py/blob/55c42dd740d75c3ba04d6991c90cf0aa0dccd8a9/docs/agent_supervisor/source_lookup_worker.md#detach-native-source-query-replay)
and [sealed evidence](https://github.com/endomorphosis/ipfs_accelerate_py/blob/55c42dd740d75c3ba04d6991c90cf0aa0dccd8a9/docs/agent_supervisor/evidence/source-query-replay-20261014/README.md)
describe the query boundary. The [previous constructor publication](129-supervisor-source-worker-construction-2026-10-14.md)
retains its independent control, snapshots and results.

The unpatched base `b37a248a74d2cbad55dec7b1289aa7cfb367d7e4` reproduced
the retained-CAS lock error in one failed control, with no errors or skips, in
25.289 seconds. It detects SERVER held before attempting genuine native
coordinator reentry, avoiding deadlock. Its one-case snapshot stays historical
as the new suite expands to 27 cases.

The first full attempt collected 250 cases but stopped at a fixture that tried
to reopen the live owner's database. Its seven passes, one failure, no errors/
skips and 164.568 seconds remain retained. The two replacement handles now use
separate private databases; production sources did not change for this fix.

The historical full record is `qualification-02/commands.json`: all 250 distinct
cases passed in 1343.765 seconds, with zero failures, errors or skips, across
11 complete suites: new query, existing current-source
lookup, and nine constructor, delivery, channel, launch, nomination and
allocation suites. Raw collection/JUnit, four changed-source snapshots and
source/HEAD/index guards remain authoritative. No historical or failed counts
are added to passing results. Documentation gates and link checks have their
own receipt; the manifest binds all retained phase files and final documents.

Historical qualification-02 used datasets `4b50ae`; its four documentation
blocks passed with 113 relative links and 17 anchors. Publication review found
a changed listed semantic-state API in incoming datasets. A fresh unpatched
control, `baseline-02`, reproduced the lock error on accelerator `f15c146`
and datasets `f4a823`, with one expected failure, no errors/skips and 23.141
seconds. Runtime Git objects were unchanged from base b37; exact fix bytes were
restored afterward. Selected fresh qualification is
`qualification-03/commands.json`: all 250 distinct cases passed in 1178.039
seconds, with zero failures/errors/skips. The separate upstream API record,
`dependency-01/commands.json`, passed all 45 distinct cases in 1.011 seconds,
with no failures/errors/skips; those counts are not added to the 250 cases.
Selected documentation receipt `documentation-checks-02.json` passed all four
exact local workflow blocks, checking 116 relative links and 17 anchors. The
original receipt, log, documents and checker remain sealed as historical inputs.

The listed inventory covers 277 files: 226 accelerator and 51 datasets sources,
without complete import/toolchain coverage. Selected datasets/kit execution
checkouts are `f4a823231ad52c9252504810a1b00ed4738346b6` and
`40c98c71b95be750509ffdb21e7e5494d91b4e79`. Base b37 advances only its
embedded datasets pin to `667033fc7040fedeb67c1d359f10ed44fa2e27b5`.
All 51 listed datasets blobs matched the historical `4b50ae` execution checkout. The incoming
LegalIR engine/publication fixes remain preserved; this query qualification does
not test those changes or rewrite earlier decoder findings.

Incoming accelerator `f15c146` advances its embedded datasets pin to `cd420d7301`.
Incoming parent `683fb27c336147ba634fcaa989f892c284035704` advances datasets to
`f4a823` and adds 15 joint-readout audit artifacts plus a note-58 update. Fifty
of 51 listed datasets sources match the historical checkout; the changed API
reads the live backend before its parsed-index cache. Fresh qualification is
required for that code. All 17 incoming parent paths remain preserved.

Parent integration preserves initial `30d14ca11300adbe35faaa836bbfefb9d1fd2af7`
and uses incoming `683fb27c336147ba634fcaa989f892c284035704` as its chosen base,
advancing only accelerator, this note and its publication artifacts. Prior
parent objects and datasets/kit pins remain preserved. The
[parent checks](../../artifacts/source-query-replay-publication-20261014/parent-checks.json)
and [parent manifest](../../artifacts/source-query-replay-publication-20261014/manifest.json)
bind publication custody without rerunning tests or documentation gates.

The published child also advances its embedded datasets pin to the tested
`f4a823` revision, preserving `cd420d7301` as an ancestor. GitHub accepted the
main push with its required-check bypass notice. The [exact-commit hosted run](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38633506180)
failed before executing any steps because of the reported billing lock. The
[read-only CI observation](../../artifacts/source-query-replay-publication-20261014/child-ci-observation.json)
retains matching run/job/check identities and annotations. Hosted gates did not
pass; the four passing blocks above are local evidence. The observer's initial
stale output path and correction are recorded in its own artifact.

The 27 new owner-side cases use actual Git/CAS, native DuckDB, Unix typed
owner/client transport and native task/allocation resources for callback
fencing. They test CAS drift, final authorization, source clocks, busy reads,
caller-owned transactions, renewal and cursor/private-state substitution. They
launch no child or worker peer. Other selected suites launch and reap inert
same-owner Python children. Host listener/deployment metadata remains authored;
these checks do not qualify a separate worker UID or deployed coding child.
No model/provider, target program, encoder/trainer, solver, Docker or official
benchmark result is supplied. Checks remain sequential, without writer lease or
proof, edit, execution, completion or whole-session token-saving authority.
Source-specific clock safety does not qualify every gateway/authentication
callback; standalone reader callers still provide connection serialization.

Next qualify initial reader binding, including both server/gateway locks,
the native task binder's outer SERVER hold, copied original inputs and native
task/allocation bind-once markers. The proposal retains each caller's exact
published reader rather than adopting a competing reader; it has no implemented
changes or executed tests. Preserve
permission delegation, authentic native daemon/wrapper/child provenance and
independently joined signed profiles/compiled instructions before deployed
trials. Keep candidate-launcher work distinct from native task/allocation
custody.

Reuse existing CodebaseIR, IntentIR, SecurityIR, LegalIR and UI/UXIR assets with
independent family, schema/version, decoder task and 8D/384D/768D identities.
Checkpoints and embeddings remain the starting assets. Actual encoder
conditioning, fresh semantic/legal-text reconstruction and native per-family
ModelManager custody gate teacher promotion and distillation. Measure complete
planning, coding, retrieval, expansion, edits, refresh, verification, retries and
failed attempts at matched official success before claiming token savings.

The preserved [parallel F17 audit](58-autoencoder-progress-integration-2026-10-06.md)
reports train complete IR 154/168 against a 155 threshold, two loss vetoes,
fresh dev/test 0/36 and inactive latent conditioning. It supplies no teacher
promotion or matched 8D/384D/768D comparison. Its separate Hugging Face readback
and source publication remain the research session's evidence, rather than
outcomes of this source-query qualification.
