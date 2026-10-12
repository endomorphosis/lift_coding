# Compact source retrieval in the coding worker — 2026-10-12

The isolated supervisor coding worker can now request compact source views and
expand their exact originals through the existing `llm_router` session. This
connects the reversible source codec to the worker's tools. The earlier prompt
metadata experiments alone did not qualify that interaction.

The optional `--source-view-profile` is frozen during full-arm benchmark
preparation and propagated through the container launcher and router. Profiles
are `disabled` (default), `identity@1`, `python-whitespace@1`, and
`python-comments@1`. The identity profile provides a control through the same
channel. Unsupported transformations retain exact source bytes. The runtime
archive binds the reader, semantic producers, codec, launcher and accounting.

The reader reuses the verified semantic source manifest and the existing
owner/worker broker lifecycle. It is independent of numerical task contexts.
Pages carry source and representation hashes, with bounded, single-use
continuations. The owner checks canonical and allocated files before and after
reads and refuses stale or foreign requests. Original source remains the editing
and execution representation. This semantic adapter is separate from the native
Quack owner's typed `source.get` API.

The default CLI validates the whole protocol envelope and displays only the
source content, representation pins and paging information. Restoration maps and
unrequested original bytes stay owner-side. The router includes the added tool
guidance in complete rendered-input accounting; the collector joins private
session measurements to the task and router receipt after cleanup. Missing or
incomplete measurements remain unavailable.

Validation on the published implementation:

| Check | Result |
| --- | ---: |
| Integrated regression tests | 1,059 passed; zero failures, errors or skips |
| Production source unchanged during regression run | Yes |
| Docker review checks | 23 passed |
| Public source files reconstructed in both representations | 2/2 |
| Primary pages | 6 |
| Foreign/stale/invalid-request refusals | 10 |
| Model/provider calls | 0 |

The Docker qualification used the generated owner launcher, real UID 1000/1001
boundary, router, CLI and socket with a root-owned authored provider fixture.
The container had networking disabled, five CPUs, 12 GiB memory and a 128-process
limit. Cleanup removed the endpoint and container. It was not a full live
supervisor START or official Terminal Bench verifier run.

The compact source transform saved only 35 bytes across the two public files;
the second file retained its original representation because of unsupported
f-strings. First-page default tool output shrank from 2,497 to 938 JSON bytes for
one file and from 4,096 to 2,523 bytes for the other, mainly by omitting repeated
transport fields. These are byte measurements, not native provider tokens.
Required source still remains in the initial prompt, so no whole-session token
advantage is established.

Current limits are 64 admitted files, 1 MiB total source, 64 session connections
and 524,288 response bytes, with an 8,192-byte maximum JSON response. Edits make
the old session stale. Automatic refresh, general capsule expansion, translating
compact edits into original patches, and a controlled live token comparison
remain unfinished. The next comparison should hold harness controls fixed and
compare `identity@1` with `python-whitespace@1`, including planning, cold indexing,
tool outputs, expansions, repairs and official task verification.

The accelerator implementation and reviewed evidence are published at
`21457b554254b48b51930fa1a5d39cd563fe1bef`:

- [Worker source-view guide](https://github.com/endomorphosis/ipfs_accelerate_py/blob/21457b554254b48b51930fa1a5d39cd563fe1bef/docs/agent_supervisor/worker_source_views.md)
- [Qualification and source-bound manifest](https://github.com/endomorphosis/ipfs_accelerate_py/tree/21457b554254b48b51930fa1a5d39cd563fe1bef/docs/agent_supervisor/evidence/source-view-worker-20261012)

Datasets remains pinned to `f47161b757190380e9898aff155067c1ad609217` and kit to
`8ac00bb1974b1378e12091d546d8425af34049e0`.

Local documentation and changed-file link checks passed. The hosted
[documentation job](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38285970906/job/114934310735)
did not start because GitHub reported an account billing lock. The
[CI observation](../../artifacts/source-view-worker-publication-20261012/hosted-ci.json)
retains that exact-commit infrastructure result separately from local validation.
