# Operator historical development service

This is the executable host service used by the recovered NS026 client. It admits an exact, operator-selected **development** source, prompt, arm and HTTP profile. It does not grant pilot/final access, consume a native supervisor claim, manufacture a Grok quota event, or replace NS004. The authoring route remains Grok primary with independently verified quota-only Codex gpt-5.6-terra HIGH fallback. This scientific development transport is a separately frozen amendment.

The actual flow is **ID-only request → one HTTP proposal → sealed candidate → explicit AI operator source review → separate cold score → signed response**. The model has no filesystem tools, terminal, Docker socket, scorer payload, private registry or keys. The host sends only the bound, complete public JSON context. It never truncates an oversized request or selects a replacement unit based on the result. Both HTTP and scorer run sequentially with one CPU, 2 GiB and 32 processes. HTTP permits one POST, no retries, at most 180 seconds; the independent cold score has a hard 120-second outer limit and a shared 115-second test budget. Operator review wait is a distinct unmeasured interval, not zero elapsed time.

**Trust limit:** ordinary pytest imports candidate Python into its interpreter. Container isolation does not prove adversarial observation integrity inside that interpreter. The current development gate requires the host operator to read the exact candidate diff before scoring. This is AI operator review of one candidate, not a human annotation, a general anti-tamper proof, or final experiment admission. No adversarial demonstration was executed. See [SCORER_TRUST_LIMITS.md](../SCORER_TRUST_LIMITS.md).

## Installation and private inputs

`source_manifest.json` hashes the durable source copies in this directory. Restore its `files` into an operator-owned checkout at `papers/completion/runtime_bootstrap/unblock_20260912/`, preserving the three directories `gateway_v2`, `gateway_historical`, and `historical_adapter`. Do not execute these archived copies in place: the shared utility derives the campaign checkout root from that installation layout. The operator checkout must also contain the pinned campaign environment script and native runtime source; each fresh grant binds and rechecks their identities.

This installation must preserve matching source bytes. A relocated installation or changed runtime requires fresh source/profile qualification and a fresh grant; existing consumed grants never migrate implicitly. Runtime requirements are Python 3, OpenSSL Ed25519 support, the exact Docker daemon/image from the profile, the previously qualified scorer dependencies, and host-only API authentication. The client does not receive credentials or Docker authority.

Keep the registry, upstream archives, scorer payloads, private logs, signing key, grant directory and runtime queue outside Git and outside authoring mounts. The private registry's dependencies are checked by `lookup_unit` before source export. Its 16 units retain the existing 4-development/4-pilot/8-final split; only development lookup is executable here. Source archives and private oracle custody must be provisioned by the operator from the retained NS005 commitments, not from a worker-supplied path. `source_manifest.json` records the private registry digest without distributing the registry or payloads.

The shared `gateway_v2/host_gateway.py` is retained only for signing, exact file access, source binding and environment utilities. Its older public CLI canary is not the historical HTTP route. Do not use its CLI to dispatch this experiment.

## Host commands

Run from the matching operator checkout. `SERVICE`, `REGISTRY`, `PREFLIGHT`, `GRANT`, `QUEUE`, `NATIVE` and `AMENDMENT` below are operator-owned exact paths; `GRANT_SHA`, `REGISTRY_SHA`, `AMENDMENT_SHA` and `REVIEW_SHA` are independently computed SHA-256 values. Choose fresh preflight/grant/queue directories. No command accepts worker-selected shell arguments or alternate test code.

```sh
python3 "$SERVICE" preflight --private "$PREFLIGHT" \
  --registry "$REGISTRY" --registry-sha256 "$REGISTRY_SHA" \
  --unit ns-hist-01-xmltodict
```

Freeze `ns-historical-development-provider-amendment/v1` **before the call**, using the complete preflight `profile` and `request_binding`, exact source manifest/prompt hashes, scope `development_only`, the selected unit and arm `A`, provider/model `grok`/`grok-4.6`, expected served aliases `["grok-4.6"]`, fallback false, maximum one call, and transport `operator_host_fixed_https_json_edits/v1`. Reasoning effort and temperature are omitted; the provider default is not asserted. The API system fingerprint is recorded without treating it as an immutable model revision. Preserve original NS004.

```sh
python3 "$SERVICE" prepare --private "$GRANT" --queue "$QUEUE" \
  --repo "$NATIVE" --registry "$REGISTRY" --registry-sha256 "$REGISTRY_SHA" \
  --unit ns-hist-01-xmltodict --amendment "$AMENDMENT" \
  --amendment-sha256 "$AMENDMENT_SHA"
```

Prepare returns the exact grant and offer hashes without invoking the provider. Publish only `offer.json` at the task's declared `qualification/production_provider/host_handoff/<grant>/` path and install its exact reviewed entry in `experiments/production_profile.json` under `host_handoff.grants`. The entry binds task/unit, arm, cache, repetition, record kind, queue/evidence relative paths, offer/grant/amendment/manifest/source hashes and full profile. Public verification material is explicitly typed SPKI-DER base64 inside offer JSON; no PEM/DER key file belongs in the paper tree.

The client submits the exact offered ID-only `request.json`. The host then runs:

```sh
python3 "$SERVICE" execute --private "$GRANT" --grant-sha256 "$GRANT_SHA"
python3 "$SERVICE" review-template --private "$GRANT" --grant-sha256 "$GRANT_SHA"
```

`execute` consumes the one model grant and returns `awaiting_operator_candidate_review`; it does **not** score. Preserve the signed `proposal.json`. The operator reads the exact small diff between private `proposal`/`sealed` and the bound preimage, and records a fresh private `operator_review.json` from the template. Set `approved:true` only after that review, with an actual UTC `reviewed_at`, an explicit bounded `review_statement`, and every emitted binding unchanged. The review must identify `ai_operator`, not human annotation, and retain the specific-candidate trust limitation. It is not a queue message the worker may approve.

```sh
python3 "$SERVICE" score-reviewed --private "$GRANT" \
  --grant-sha256 "$GRANT_SHA" --review-sha256 "$REVIEW_SHA"
```

This consumes a distinct one-score reservation, rechecks the sealed inventory and every review/source binding, invokes no provider, then emits signed `response.json`. A failed test remains a failed outcome. Pipeline availability and correctness are different claims.

## Client execution and resumption

```sh
python3 papers/completion/neurosymbolic_supervision/experiments/run_comparison.py one-task \
  --repo "$PAPER_REPO" --ledger "$LOCAL_LEDGER" \
  --task-id ns-hist-01-xmltodict --arm A --cache local_cold --repetition 0 \
  --path production --record-kind development --out "$ATTEMPT"
```

Here `--path production --record-kind development` selects the real, grant-bound historical **development** implementation. It does not authorize the final population. While the operator has not supplied a signed final response, the command returns pending (exit 75), publishes no terminal scientific ledger outcome and makes no API call. Resume the identical command/ledger/schedule after the response arrives. A pending file is not a no-run measurement or a finished trial.

Before retiring the queue, retain exact `offer.json` and signed `response.json` bytes under `qualification/production_provider/host_receipts/<grant>/` and bind `evidence_relative` in the profile. These public metadata files are sufficient for durable signature verification. The private candidate/scorer logs remain in operator custody.

```sh
python3 papers/completion/neurosymbolic_supervision/experiments/score_runs.py \
  --attempt "$ATTEMPT" --out "$RESCORED"
```

For a host attempt, rescore revalidates the durable signature, grant, schedule, source and candidate hashes. It reads no hidden oracle and invokes neither provider nor scorer again. Local client CPU/RSS/wait counters are not remote aggregate measurements; absent remote metrics remain null/unavailable. Imported operator grant consumption is reported separately from the local runner ledger.

## Interruption and later experiments

A consumed reservation without complete signed evidence is **uncertain**. Do not delete markers or rerun it. If HTTP creation/termination is unproven, use the retained exact container name/CID and cleanup evidence for operator reconciliation; do not score. If interrupted after score reservation, preserve pending proposal, review, score logs and reservation; no automatic second scoring run. Completed same-grant requests return retained evidence without another effect.

NS011 may implement and qualify additional development arms against this host interface, but each exact unit/arm/profile needs its own reviewed grant. The current first grant demonstrates only A/local_cold for one frozen development unit, not A–D parity, warm reuse, paired statistics, corpus completion, or total cost measurement. Never mix models or changed context policies within a paired block.

NS016 must freeze any population/profile amendment and pilot/final schedule **before** outcomes, address or explicitly bound scorer observation integrity and confidentiality, qualify all scientific arm/cache budgets and effect accounting, and obtain a new reviewed host registry/admission implementation. This service and adapter intentionally reject the twelve locked pilot/final units; merely editing a profile JSON or choosing `--record-kind final` does not unlock them. NS016 needs code/qualification work on the host service and registry gate, not an environment switch. The operator must then install and service that newly reviewed version. Original NS004 and all failed/consumed grant history remain retained.
