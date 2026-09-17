# Lean Refactor Arena warm-up runbook

**Protocol:** `LRA/v1`. **Loop:** v1. **Hardware label:** `hardware_class=spark_gb10`.
**Control plane:** `harness/run_warmup.py` plus `tools/verify_lra_batch.py`.
**This runbook is not official Track 2** and is not a scored Arena ranking.

The operator command below runs the frozen **15** warm-up problems on Spark.
**Completing** the campaign requires `verify_lra_batch --require-complete` to
print `status=PASS` and exit 0. Incomplete is not success. **Do not** write
Arena scores into the manuscript.

Identities frozen for this run live in
[`../evidence/run_freeze.json`](../evidence/run_freeze.json). Freeze before
run. Do not add `lean_refactor_arena` to `scripts/paper_supervisors.py`
`PAPERS`. LRAH-* IDs in this file are documentation, not a second scheduler.

## Claim boundary

Allowed after a verifier PASS:

- Per-problem filesystem receipts under the receipts directory.
- `hardware_class=spark_gb10` on every receipt.
- Local keep-best composites recorded as `local_proxy_*` only.
- Honest incomplete / retained failures.

Forbidden by this runbook:

- Writing `arena_score`, `arena_score_tokens`, `arena_score_elab`,
  `official_score`, `token_savings`, or Track 1 / Track 2 rankings into
  `manuscript/main.tex`, `manuscript/warmup_table.tex`, or
  `manuscript/main.pdf`.
- Treating Spark NVFP4 wall-clock as the official 4×A100 80 GB / 48 h envelope.
- Declaring the warm-up complete without `verify_lra_batch --require-complete`
  `PASS`.
- Taking owner `LOCK_EX` on `gpu-0.lock` or starting a second `llama-server`.
- Citing unpublished SHA `3fe4e64d` as the Leanstral identity.

## Frozen identity (see `evidence/run_freeze.json`)

| Item | Value |
| --- | --- |
| Warm-up JSONL | `data/benchmark_data_warmup.jsonl` |
| SHA-256 | `6209680cf00cde0765b77b24834cd72c64dd585b2f7e3f2a58209980ab59a804` |
| Bytes / problems | 113826 / 15 |
| Weight | `Frosty40/Leanstral-1.5-119B-A6B-GGUF-NVFP4` revision `abcc5ce2528c6375148d41dac6dce20f06c339f4` |
| CID | `bafkreicgnd6su3jhmtpckbejqurdb2lchdvvydluswdg5m5zy3cpvroh3i` |
| NVFP4 size | 67135119264 bytes (~62.52 GiB) |
| SM80 derivative SHA | `null` until LRA-024; NVFP4-on-Spark is `spark_gb10` only |
| Generator | `leanstral_local` / `Leanstral`, temperature 0.0 |
| Prompt | `harness/lra_prompt.txt` |
| Gates / hammers / TypeSafe | `off` / `off` / `off` |
| Policy JSON | absent (`open_policy_v1.json` is after v1 distill) |
| Completing process | `tools/verify_lra_batch.py --require-complete` |

## Prerequisites

1. Working directory is the repository root.
2. Canonical interpreter: `/usr/bin/python3.12`.
3. Pin `IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART=0` so `llm_router` does not spawn a
   second `llama-server`.
4. Probe `http://172.17.0.1:8080/health`. If healthy, loop v1 **must** call
   Leanstral as an HTTP client. Skip generate **only** if docker0 is down
   (keep the reference proof). Never `LOCK_EX`.
5. Tag-pinned elan at
   `{ELAN_HOME}/toolchains/leanprover--lean4---<tag>/bin/{lean,lake}`.
   PATH `lean` is not a fallback. Missing tags are a capability gap.
6. Olean caches for listed `(url, commit, tag)` jobs and the three Putnam
   Mathlib+Aesop lake projects. `--network deny` fails closed if a cache is
   missing.
7. Copy `freeze_binding` from `evidence/run_freeze.json` into the receipts
   directory before verifying (the verifier also accepts a missing binding;
   a mismatched `warmup_sha256` fails closed).

```text
export IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART=0
export LRA_HARDWARE=spark_gb10
export LRA_TYPESAFE=off
export LRA_GENERATOR=leanstral
export LRA_NETWORK=deny
/usr/bin/python3.12 papers/completion/lean_refactor_arena/harness/run_warmup.py --probe-health
/usr/bin/python3.12 papers/completion/lean_refactor_arena/harness/run_warmup.py --plan
/usr/bin/python3.12 papers/completion/lean_refactor_arena/tools/verify_lra_batch.py --schedule
```

`--plan` must report `n_problems=15` and `hardware_class=spark_gb10`.
`--schedule` must list the same 15 frozen names.

## Operator command (15 problems, Spark, hardware_class=spark_gb10)

This is the operator command. It runs all 15 frozen warm-up problems through
loop v1 (splice → retrieve → optional generate → lexical admit → lake compile
→ keep-best) and writes local filesystem receipts. `run_warmup.py` hard-codes
`HARDWARE_CLASS = "spark_gb10"`.

```bash
IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART=0 \
LRA_HARDWARE=spark_gb10 \
LRA_TYPESAFE=off \
LRA_GENERATOR=leanstral \
/usr/bin/python3.12 papers/completion/lean_refactor_arena/harness/run_warmup.py \
  --run \
  --receipts-dir papers/completion/lean_refactor_arena/submissions/warmup \
  --network deny
```

Do not pass `--limit`. Do not pass `--synthetic-compile` for an operator run.
Do not start `llama-server`. Serialize generations in-process.

Receipts directory layout (created by `run_warmup.py`):

```text
papers/completion/lean_refactor_arena/submissions/warmup/
  freeze_binding.json          # copy from evidence/run_freeze.json freeze_binding
  <problem>/
    problem.json               # hardware_class=spark_gb10; arena_score=null
    candidate.lean
    admission.json
    result.json
    <lean-tag>.json            # one compile record per listed version_info tag
```

Optional freeze-binding copy (fail-closed if SHA drifts):

```bash
/usr/bin/python3.12 -c "import json,pathlib; p=pathlib.Path('papers/completion/lean_refactor_arena/evidence/run_freeze.json'); b=json.loads(p.read_text())['freeze_binding']; d=pathlib.Path('papers/completion/lean_refactor_arena/submissions/warmup'); d.mkdir(parents=True, exist_ok=True); (d/'freeze_binding.json').write_text(json.dumps(b, indent=2, sort_keys=True)+'\n')"
```

## Completing requires verify_lra_batch --require-complete PASS

`verify_lra_batch.py --require-complete` is the **only** process allowed to
declare the warm-up run complete. `--require-complete` enables every gate:
digest, statement-bind, all listed tags, no `sorryAx`, one receipt per
scheduled problem. Exit 0 with `status=PASS` and `complete=true`. Any other
status is not completion.

```bash
/usr/bin/python3.12 papers/completion/lean_refactor_arena/tools/verify_lra_batch.py \
  --receipts-dir papers/completion/lean_refactor_arena/submissions/warmup \
  --require-complete
```

Equivalent explicit gates (same ALL_GATES set):

```bash
/usr/bin/python3.12 papers/completion/lean_refactor_arena/tools/verify_lra_batch.py \
  --receipts-dir papers/completion/lean_refactor_arena/submissions/warmup \
  --require-complete \
  --require-digest \
  --require-statement-bind \
  --require-all-tags \
  --require-no-sorry
```

A compact synthetic fixture (`--self-check`) is for landing the verifier, not
an operator Spark run. Operator completion is the receipts-dir command above.

Fail closed (exit 2, `status=FAIL`):

- missing receipt for any of the 15
- JSONL or `freeze_binding` digest mismatch
- candidate does not prefix-bind `header+statement`
- missing compile record for a listed `version_info` tag
- `sorryAx` / missing axiom report
- non-null `arena_score` / `score` on a receipt
- duplicate receipt for the same name

Do not import law_to_action `verify_batch.py`.

## Does not write Arena scores into the manuscript

This runbook **does not** edit `manuscript/main.tex`,
`manuscript/warmup_table.tex`, or `manuscript/main.pdf`.

- `arena_score_*` stay JSON `null` on loop payloads, problem receipts, the
  freeze file, and verifier output.
- Local numbers, if any, are `local_proxy_*`. They are not Arena rankings.
- `warmup_table.tex` remains the imported-reference characterization
  (source, short name, lines, tokens, toolchain count). It has no score
  column.
- PR-14 may fill Approach / Models / Budget from receipts **after** this
  verifier PASSes. Until then the manuscript keeps the harness unrun and
  does not invent leaderboard ranks.

## LRAH documentation IDs (not a scheduler)

| ID | Work | v1 operator run |
| --- | --- | --- |
| LRAH-001 | Digest-gated JSONL loader + prefix splice | used |
| LRAH-002 | Cached clone + elan + olean bake + Putnam lake | used |
| LRAH-003 | Lexical `admit_lean_proof_text` | used |
| LRAH-004 | Multi-tag lake compile worker | used |
| LRAH-005 | Lake-native tactic try | **off** 30 Sep path |
| LRAH-006 | TypeSafe wrapper | **off** (`LRA_TYPESAFE=off`) |
| LRAH-007 | fail-closed `generate_text` docker0 client | used |
| LRAH-008 | `run_warmup.py` loop + receipt writer | **this command** |
| LRAH-009 | Warm-up 15, fail-closed verifier | **this completing command** |
| LRAH-010 | Official Track 2 runner | gated 15 Oct; not this runbook |
| LRAH-011 | Optional Track 1 ledger | after v1; not this runbook |

## Feature flags for this run

```text
LRA_TYPESAFE=off
LRA_GENERATOR=leanstral
LRA_HARDWARE=spark_gb10
LRA_MAX_CANDIDATES=8
LRA_MEASUREMENT_MAX_HEARTBEATS=400000
IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART=0
```

Official Track 2, if it ever runs, filters to `hardware_class=a100_80gb_x4`
**and** a new SM80 GGUF SHA in `evidence/run_freeze.json`. That SHA does not
exist in this freeze. Spark NVFP4 is `hardware_class=spark_gb10` only.

## Capability gaps (do not weaken the command)

- Sealed validation `HOME` (`ipfs-accelerate-validation-home-*`) has no
  operator `~/.elan`. Missing tag-pinned lake/lean is a recorded gap, not
  PATH usability.
- The local NVFP4 GGUF may be absent on a given host. Loop v1 still requires
  docker0 `/health` before generate; it does not fetch weights.
- `scripts/run_leanstral_ephemeral.py` may be absent. The common path is
  HTTP client of a live owner, not exec-owner.
- Putnam Mathlib/Aesop revisions are the Lean tags. JSONL git commits are
  `jsonl_version_pin` only. If organizers later publish SHAs, replace pins
  in `evidence/run_freeze.json` and rebake.
