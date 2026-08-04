# Proof-backed test reuse readiness audit — 2026-08-03

> **Superseded for board/closeout status.** See
> [`46-proof-backed-test-reuse-readiness-audit-2026-08-04.md`](./46-proof-backed-test-reuse-readiness-audit-2026-08-04.md)
> for the closed **66/66** board, live capability gap, and report-only closeout
> diagnosis. Architecture and dependency sections below remain historical
> context for the pre-close wave.

## Executive status

- Audited integration revision: `6d61e86594ec70b0ff60a37308fe11ef16f17f95`
- Accelerator revision: `003036ec9fea5e27493f9b42792296498711e82f`
- Datasets revision: `1894e9dca7dced0690893d468e40751a14f0b15b`
- Kit revision: `2f2fd78505fe7528bb406dbed1123abbb729ce80`
- Board progress: 62 of 66 implementation tasks complete (93.94%). No task is
  blocked. The claimable wave is exactly `PTR-153` and `PTR-154`; `PTR-155`
  joins them and `PTR-149` remains the final operator handoff.
- Objective authority: 0 of 12 goals are authoritatively complete. This is
  intentional: implementation status cannot substitute for a reviewed v4 key
  ceremony and genuine positive cold-to-warm proof-reuse evidence.
- Supervisor status after supported two-pass recovery and restart: healthy,
  globally progressable, zero blocked tasks, and all three lane processes alive.
  `PTR-153` is actively implementing through Grok `grok-4.5`.

The 93.94% figure measures reviewed implementation contracts, not production
skip authority. Positive v4 publication stays deliberately disabled until the
remaining security and evidence joins close.

## Implemented architecture

1. Test identity is derived without a test-file registry. Pytest collection,
   canonical AST/static facts, parameters, fixtures, hooks, repository state,
   policy inputs, and the completed runtime dependency trace contribute to a
   canonical execution identity.
2. Canonical artifacts use multiformats/multihash CIDs with retained canonical
   bytes. Locator indexes are hints and never proof authority.
3. Package entry points and narrow repository loaders compose the plugin for
   individual tests and normal suite runs. Package `__init__` exposes only a
   lazy proof-reuse facade; it does not eagerly import datasets, NLTK, native
   backends, cache transports, or supervisor internals.
4. Cache, endpoint, IPFS, Groth16, NLTK-data, and optional-provider failures are
   typed `RUN`/`DEFERRED` outcomes. They do not fail collection and cannot turn
   an unverified pass into a skip.
5. Serial and xdist publication share one controller transaction. Workers have
   no direct candidate-write path, and the sole `put_candidate` call is behind
   exact controller verification.
6. PTR-152 is a reviewed denial boundary. Forged injected bindings, fake
   authoritative verifier objects, structural certificate claims, attached
   worker certificates, mutable snapshot substitutions, oversized inputs, and
   untyped/double store acknowledgements cannot authorize a candidate.

## Dependency and setup contract

The final wheel metadata contains these ordinary Python requirements:

| Distribution | Constraint | Purpose |
| --- | --- | --- |
| `nltk` | `>=3.8.1,<4` | admitted AST/text capabilities |
| `jsonschema` | `>=4,<5` | bounded certificate/schema validation |
| `multiformats` | `>=0.3,<1` | CID and multihash construction |
| `pymultihash` | `>=0.8.2` | compatible multihash support |

`requirements.txt`, `setup.py` install requirements, dynamic pyproject
dependencies, the `proof-reuse` extra, and wheel metadata are tested for
parity. `pymultihash` is a core requirement, so `pip install '.[proof-reuse]'`
includes it even though the scoped extra does not duplicate that line.

Two explicit post-install provisioning surfaces delegate to the same bounded
lazy installer:

```bash
ipfs-accelerate-proof-reuse-provision
python setup.py proof_reuse_provision
```

Normal wheel/sdist construction, `pip install`, `setup.py` import, package
import, and pytest collection remain side-effect free. NLTK itself is installed
through ordinary setup metadata. Its corpora are downloaded only for an
allowlisted first-use request with both package/proof consent and
`IPFS_TEST_PROOF_REUSE_NLTK_DOWNLOAD=1`.

Groth16 is a Cargo-native capability, not a package that can truthfully be
listed as `groth16` on PyPI. With general consent plus
`IPFS_TEST_PROOF_REUSE_GROTH16_BUILD=1`, the explicit setup/console provisioner
may build the exact digest-pinned, locked source into a private cache. It never
runs trusted setup and never creates production proving or verifying keys.
Absent Cargo, network, source, binary, endpoint, cache, or keys produces a typed
non-blocking result.

The private datasets verifier is a closed 57-file Git-blob snapshot:

- snapshot SHA-256: `789339696dc10fb37dc0fd4fddd21b24af50b669479c194095f37dc904eab343`
- snapshot bytes: 873,708
- reviewed native binary SHA-256:
  `d883348d24a6dc6c0ab25745b3dab7a759e1566799ddaaf90429f21a0e469055`
- reviewed capability SHA-256:
  `7625046099fc44760dd858af3f976bd37341ff1ca327fad30e0654ee8ad6109f`
- reviewed release-manifest SHA-256:
  `033990805b50b7229c394809b3c549eda88f705b9358826313d79da0714fea33`
- locked source identity:
  `sha256:93dbdcb273114f6ec578f8f80bea185ac57f67f0b86daa6f0ff1d2575903691c`

## Provider and supervisor policy

Both implementation and semantic merge resolution use the same sealed chain:

- primary: Grok `grok-4.5`;
- fallback: Codex `gpt-5.6-terra`, medium reasoning;
- sole fallback trigger: typed `grok_quota_exhausted`;
- authentication, launch, timeout, transport, malformed output, generic
  nonzero, and task failures propagate without invoking Codex.

The live PTR-153 command records that exact provider wrapper and currently uses
the Grok primary. The three-lane supervisor is healthy and reports no blocked
tasks or unhealthy lanes. PTR-153 and PTR-154 are dependency-independent and
have disjoint predicted files, but both modify the accelerator submodule. The
supervisor's intentional repository-level resource lease therefore serializes
their provider dispatch to prevent divergent gitlink mutation; the idle lane's
`resource_claim_deferred` state does not consume an attempt or mark either task
blocked. Cross-submodule waves still execute concurrently. File-granular
same-submodule dispatch would require a separately reviewed scheduler/merge
safety capability and must not be enabled by bypassing this lease.

## Validation evidence

| Scope | Result |
| --- | --- |
| Board validator | valid; 66 tasks, 62 complete, 2 ready, 0 conflicts |
| Outer supervisor suite | 28 passed |
| Provider fallback and merge resolver | 35 passed |
| Accelerator integrated proof-reuse/security population | 193 passed |
| Independent PTR-152 security population | 140 passed |
| Accelerator xdist population | 26 passed |
| Datasets bootstrap/zero-config/shim | 40 passed |
| Kit bootstrap/zero-config/shim | 29 passed |
| Datasets native release Python checks | 3 passed |
| Datasets Groth16 Cargo tests | 19 passed |
| Final archive wheel and sdist | built successfully |
| Twine artifact validation | wheel and sdist passed |

The installed-wheel cold-import audit also blocked process and network APIs
while all consent flags were enabled; imports attempted no install/download,
created no proof cache/provisioning directory, and started no daemon.

## Remaining dependency-ordered work

1. `PTR-153` must retain complete bounded public proof/certificate material and
   make actual prove/verify execution immutable or FD-bound. It must revalidate
   exact key bytes at use time, overwrite the approved artifacts root, and use a
   strict child environment excluding loader/interpreter injection.
2. `PTR-154` must retain/reconstruct the bounded controller-owned receipt,
   candidate, policy, statement, circuit, key, issuer, epoch, and backend context
   through serial and xdist paths without granting publication authority.
3. `PTR-155` must join those branches through the exact datasets
   `verify_test_execution_certificate_v2` result, expected candidate-context
   CID, reviewed module/source provenance, and the sole typed atomic candidate
   write. Only then may the positive gate be considered for enablement.
4. `PTR-149` must run genuine three-repository cold/warm subprocesses, observe
   a standard pytest skip only after local v4 verification, measure positive
   time/body-execution savings, prove zero false skips under mutation/forced
   rerun populations, and perform the operator-reviewed objective closeout.

## External activation inputs still required

- Operator-approved v4 proving/verifying-key locations and exact SHA-256 values,
  plus the reviewed ceremony/provenance receipt authority. The hardcoded
  production v4 manifest allowlist is intentionally empty until this exists.
- Supported platform policy: reviewed prebuilt native releases versus required
  local Cargo builds for each platform.
- Cache retention, revocation, issuer epoch, and production key-rotation policy.
- Whether each allowlisted NLTK dataset is required by an admitted consumer;
  unused corpora should remain absent.
- Rollout population, target savings threshold, forced-rerun sampling cadence,
  and acceptable proof/cache latency budget.

These inputs gate production skip authority, not test execution or supervisor
health. Until supplied, tests continue normally and report the exact reason a
certificate/cache could not be reused.
