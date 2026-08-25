# Proof-Carrying Context Engine v0.1 qualification

## Decision

The evidence-supported level for the immutable repository cut at commit `43457c396be7a9116152e4414dadc4625eff2c2e` is **`research_demo`**. Release, internal-pilot, external-supervised-pilot, and production use are **NO-GO**. Internal development may proceed only with restrictions appropriate to unqualified research code.

This is a fail-closed upper bound. It is not a positive claim about quality, security, cost, context reduction, current-head CI, clean installation, longitudinal stability, or production fitness.

## Deterministic decision

The policy evaluates levels from highest to lowest and selects the first level whose criteria and every lower-level criterion have immutable supporting evidence. Missing evidence is unavailable, explicit NO-GO evidence remains NO-GO, and task or component completion supplies no gate credit.

At this evidence cut:

- Installation is an observed NO-GO. `installation/qualification.json` records `completion_disposition=completed-with-explicit-no-go`, `decision=NO-GO`, and `release_qualified=false`.
- Benchmark thresholds are frozen before execution, but no benchmark qualification exists. Frozen policy is not execution evidence.
- The threat model records `current_qualification=no_go`; the terminal PCCE-076 security qualification is unavailable.
- Required current-head CI evidence is unavailable.
- PCCE-045 implemented a bounded self-hosting harness with no qualification authority. PCCE-079 longitudinal qualification evidence is unavailable.
- The required PCCE-081 release-candidate manifest and receipt are unavailable at this evidence cut.

Those facts make `internal_alpha` ineligible. The only evidence-honest level is the restrictive `research_demo` fallback.

## Evidence identities

| Evidence | Disposition | SHA-256 | Raw CIDv1 |
| --- | --- | --- | --- |
| `installation/qualification.json` | observed NO-GO | `378f733b31feee32c39552c775d8e774f0cee9381920c00f14649dcfdafb1ef7` | `bafkreibxr5ztwmp65yzmhfksy525rz3u6dhosoazedaa6fdetxh5v6y664` |
| `benchmark/thresholds.json` | policy only; no results | `61b8efd5b4a8794b973e917324f491c10e7dbde4415e05b0515aa704e11a256b` | `bafkreidbxdx5lnfipffzopuromspjeobbz633zcblyc3auk2u4cocgrfnm` |
| `security/threat_model.json` | observed NO-GO | `505d63a745c6c6ee463712272fd5a932f4f56dda51c8f96e5261e16ac93105ff` | `bafkreicqlvr2orogy3xemnyse4x5lkjs6t2w3wsrzd4w4utb4fvmsmif74` |
| `receipts/PCCE-045.json` | harness implementation only | `640a904ca8837f59d98b5ff71915dd141bd143bf8d52d391abd4f5fe2dcaae7b` | `bafkreidebkiezkedp5m5tc2764mrlxiudpiuhp4nkljzdk6u6x7c3svopm` |

The machine-readable decision records missing benchmark, security, CI, self-hosting, and release inputs with `present=false`. It does not assign placeholder identities to unavailable bytes.

## Next-level blockers

`internal_alpha` remains blocked by all of the following:

1. No qualified clean installation; the immutable installation gate is NO-GO.
2. No present and verified PCCE-081 release-candidate manifest at this cut.
3. No benchmark qualification showing quality, context, route, cost, and zero-tolerance outcomes.
4. No terminal security qualification clearing release-blocking critical/high findings.
5. No required current-head CI qualification.

`internal_pilot` additionally requires passage of the frozen benchmark thresholds and longitudinal self-hosting checks. `external_supervised_pilot` additionally requires explicit external-supervision policy evidence. `production_candidate` additionally requires explicit production policy passage. None is present.

## Restrictions and limitations

- Do not treat board completion as qualification evidence.
- Do not use this cut for internal pilot, external use, release promotion, or production.
- Do not infer provider execution, CI passage, hidden-scorer validity, security passage, package signatures, or longitudinal passage from implemented code or configured tests.
- `research_demo` permits only bounded research/development examination under controls chosen outside this artifact.
- PCCE-081 is a required predecessor. Before admission against a later composed head, bind its exact release artifacts and all intervening benchmark, security, CI, and self-hosting evidence, update the repository cut and hashes, and re-run the same fail-closed policy.

## Rollback and supersession

Retain this immutable projection for its declared evidence cut. New immutable evidence produces a new projection identity; it never relabels these bytes or raises the level automatically.
