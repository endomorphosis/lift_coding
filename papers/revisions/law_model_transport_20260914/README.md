# Restricted per-job model transport

The current transport passed 27 controls in an actual container using the native worker's pinned image, bridge network, user identity, read-only root and capability restrictions. The container reached an owned host loopback **tiny HTTP fixture** through a read-only Unix socket mount. The final run retained 11 logical exchanges and 29 HTTP phase requests; all fixture processes and its container were removed. No model, provider CLI, scientific candidate or native board operation was invoked.

The authoritative test is [qualification_v4/qualification.json](qualification_v4/qualification.json), with exact tested source bytes in `qualification_v4/code/`. Run the read-only verification from any directory:

```sh
python3 -B papers/revisions/law_model_transport_20260914/verify_transport.py
```

The verifier checks retained raw bytes, request and response hashes, phase accounting, original seeds, token-count bindings, terminal receipts and actual container configuration. It neither launches resources nor repeats requests. The recorded verification is `verification_v1.json`.

## Interface

A trusted host owner starts and supervises the warm model separately. Prepare one fresh private job directory with `transport.prepare(directory, owner, max_requests=N, max_tokens=1024)`, then run `transport.py serve --job DIRECTORY` in a foreground process supervised by that owner. `prepare` does not launch a model. Use a short absolute job path because Linux Unix socket paths must fit 108 bytes.

Project only `DIRECTORY/client` read-only into the worker at `/model-job`. Project a **code-only snapshot** at `/transport` and a separate writable output directory at `/output`. Do not mount the transport revision or host job directory: they contain host authority and unrelated retained jobs. The native provider's per-job projection hook remains an explicit integration task; global Docker or provider settings were not changed.

```python
from client import exchange, post_json

body = {
    'model': 'leanstral_local',
    'messages': [{'role': 'user', 'content': 'A bounded task prompt'}],
    'temperature': 0,
    'seed': 104729,
    'max_tokens': 1024,
    'stream': False,
}
response, receipt = exchange('/model-job', body, '/output/attempt-01',
                             budget_seconds=60, request_id='0123456789abcdef0123456789abcdef')
# Alternatively, the qualified-loop adapter returns parsed chat JSON on success:
# result = post_json('/model-job', body, '/output', 'attempt-02', remaining_seconds)
```

Each exchange ID and output directory must be fresh. Failed and uncertain exchanges are retained and must be reconciled before any successor dispatch. There is no automatic retry. `client.close_job('/model-job')` requests authenticated gateway shutdown; the host must observe its terminal receipt and perform model cleanup. The gateway never stops or replaces its separately owned model.

The body admits exactly `model`, `messages`, `temperature`, `seed`, `max_tokens`, and `stream`. The model must match the owner alias, temperature must be numeric zero, stream false, and the seed one of **104729, 104759, 104761**. Messages have only plain-text role/content fields. Real-model jobs require an output ceiling of **1024**, with per-call output requests from 1 to 1024 and input counts from 1 to **2048**.

The host performs an atomic three-phase exchange over fixed loopback routes:

1. `/apply-template` receives the exact messages with `add_generation_prompt=true`.
2. `/tokenize` receives the returned template bytes with `add_special=true` and `parse_special=true`.
3. After checking the actual count, live worker, remaining deadline and owner identity, `/v1/chat/completions` receives the original request body.

The host records a generation reservation before generation dispatch. It retains template bytes and actual token IDs, requires returned `usage.prompt_tokens` to equal the preflight count, and bounds reported completion tokens. The worker independently verifies the returned message/template/token hashes and input-count equality. Input overflow is a retained preflight rejection without generation. This interface must still be qualified against the actual model's template and tokenizer semantics.

## Ownership and bounds

The private job capability includes a random job ID and token, Unix peer UID checking, mode-0700 directories and a mode-0600 socket. The gateway pins the owner's boot ID, PID, process start time, command hash and actual loopback listening socket inode. It allows only `127.0.0.1` at one declared high port, rechecks ownership during each phase, disables environment proxies and redirects, and accepts no worker-specified URL or route.

For `scope=real_model`, the owner record must declare **10000 total wall seconds and 360 startup seconds**, a finite monotonic deadline within that total, the exact model identity, and a hash-bound owner qualification report. The report schema is `law-warm-model-owner-qualification/v1`, with `status=PASS`, matching `model_identity`, `wall_seconds=10000`, `startup_seconds=360`, and `cleanup_qualified=true`. This is owner/resource qualification; it is not a claim of model performance. The tiny fixture uses the separate explicit `tiny_non_model_fixture` scope.

Each logical exchange has one deadline of at most 60 seconds shared across all three phases. Each HTTP child is separately owned, receives parent-death SIGKILL, and is killed and reaped on deadline, disconnect or owner change. An unproven child cleanup stops subsequent dispatch. Cleanup has a separately recorded allowance of up to two seconds. Client connect, send and read operations recompute the remaining deadline. The host owner must still qualify whether the real service stops generation compute on disconnect; tiny-fixture socket cancellation alone does not prove that.

Request frames are bounded to 256 KiB, template and tokenize responses to 256 KiB each, generation responses to 4 MiB, and the combined encoded response to 7 MiB. Oversize receipts retain only the bound plus one byte. The finite logical request allowance includes preflight failures. The gateway is serial, expires with the owner deadline, and removes its socket on shutdown. One owner should create one job gateway for this workload; this implementation does not provide a global registry across independently prepared jobs.

## Retained development history and remaining gates

| Run | Outcome | Tiny HTTP requests |
| --- | --- | ---: |
| v1 | Failed cancellation observation; retained with reconciliation | 6 |
| v2 | Chat-only interface passed | 7 |
| v3 | Atomic preflight interface passed | 26 |
| v4 | Atomic preflight and all response-size controls passed | 29 |

All **68** historical requests were to the tiny fixture; model and provider calls were zero. The first failure is preserved at `qualification_v1/failure_reconciliation.json`; its cancel occurred before an upstream connection, so that run did not prove upstream cancellation. Later runs explicitly observed it. No historical logs were rewritten.

The actual container test adds one CPU and 512 MiB limits for the tiny fixture worker. These are stricter test limits, not assertions about the native `cpu-medium` label: the audited native worker has no explicit Docker CPU or memory cap. It has no GPU/device request or model-cache mount, and container loopback cannot reach host loopback. Full boundary evidence remains in `papers/completion/runtime_bootstrap/post_empirical_20260914/LA032_worker_model_boundary_audit.json`.

Actual model interface/usage/template equality, warm-model lifecycle and compute cancellation, native per-job mount integration, and finite scientific-loop scheduling remain separate gates. This transport evidence does not complete LA-032 or the 900-cell study. The separately prepared eight-request qualification worker under `law_model_qualification_20260914/` has an offline frozen plan; only its host owner may launch the actual model workload.
