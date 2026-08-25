# Proof-Carrying Context Engine v0.1 independently reviewed qualification

## Decision

The highest level supported by the immutable evidence at canonical admission baseline `b8cadc3fb3f492cc2f27276e750ecb488bea541d` is **`research_demo`**. Release, internal pilot, external supervised pilot, production candidate, and production use are **NO-GO**. Internal development may proceed only with restrictions appropriate to unqualified research code.

PCCE-081 source candidate `c1b3a46f863594a5d513b2162c08860b8115ea08` passed independent review, its reviewed receipt is bound, and the live task is completed at revision 3 with CID `baguqeerafrcsh2er4rissdyxq5ikb34kqbvrmb3a6drtys7k3tdlhbualp6q`. PCCE-082 candidate commit `11f5e995348f442bfe568c75d569ded9b8ca3a3d` (tree `502e26584c5569f8e6f56e30f1bb6b2509e2a483`) passed independent review without fixes; this sealing update records that disposition and requires no recomposition. Supervisor admission and live PCCE-082 database completion are not claimed. Completed predecessor or task authority cannot raise the level: installation, benchmark, security, current-head CI, longitudinal self-hosting, and the release candidate all retain explicit NO-GO decisions without waivers.

## Deterministic policy result

The policy selects the highest level whose criteria and all lower-level criteria have immutable support. Missing evidence cannot pass, an explicit NO-GO cannot be waived by task completion, and configured or locally tested controls receive no external execution credit.

`internal_alpha` is ineligible because:

1. PCCE-056 has zero qualified clean-install profiles and records `decision=NO-GO` and `release_qualified=false`.
2. The PCCE-081 bundle is present and deterministically reconstructed, but records `status=NO-GO`, `release_qualified=false`, and `promotable=false` with seven blockers.
3. PCCE-068 records an unavailable-evidence NO-GO, not a measured threshold failure or passage; `provider_call_count=0` and unobserved cost/quality fields remain unavailable rather than zero.
4. PCCE-076 records security NO-GO with nine critical and one high release blocker open.
5. PCCE-080 proves a nine-job local workflow contract only. External run, ruleset, job-log, and dependency/license authority is absent, so CI and release qualification remain false.

`internal_pilot` is additionally blocked because frozen benchmark thresholds have not passed and PCCE-079 contains one same-session epoch, zero benchmark/provider attempts, and no genuinely time-separated longitudinal evidence. Higher levels have no eligible lower-level basis or explicit external/production policy passage.

The only evidence-honest selection is the restrictive `research_demo` fallback. It conveys no positive installation, benchmark, security, CI, self-hosting, release, pilot, or production claim.

## Evidence identities

| Evidence | Disposition | SHA-256 | Raw CIDv1 |
| --- | --- | --- | --- |
| `installation/qualification.json` | explicit NO-GO | `378f733b31feee32c39552c775d8e774f0cee9381920c00f14649dcfdafb1ef7` | `bafkreibxr5ztwmp65yzmhfksy525rz3u6dhosoazedaa6fdetxh5v6y664` |
| `benchmark/thresholds.json` | frozen policy; no execution credit | `61b8efd5b4a8794b973e917324f491c10e7dbde4415e05b0515aa704e11a256b` | `bafkreidbxdx5lnfipffzopuromspjeobbz633zcblyc3auk2u4cocgrfnm` |
| `benchmark/metrics.json` | 84 unavailable route observations | `09c50c845ac1c2038bb6be3a879855a913ec2d9ed6644d3f126e32a5e2086664` | `bafkreiajyugiiwwbyibyxnv6hkdzqvnjcpwc3hwwmrgt6etogks6ecdgmq` |
| `benchmark/qualification.json` | explicit unavailable-evidence NO-GO | `13dcaf260fcbbed9dd72b53954e6bdfd12db27a423ee96343d18afca8bf1c077` | `bafkreiat3sxsmd6lx3m524vvhfkonpp5clnspjbd52ldipiyv7fix4oao4` |
| `security/findings.json` | ten open high-or-critical blockers | `09eb93e942efc040bd43b12246c9d241a4227a2c2d514e65db66b8669c67b40f` | `bafkreiaj5oj6sqxpybal2q5rejdmtusbuqrhulbnkfhglw3gxbtjyz5ub4` |
| `security/qualification.json` | explicit NO-GO | `94034723fddfa547266c794961c3c88d005f1d097c6e2524ccfbedd49a7dc8f4` | `bafkreieuandsh7o7uvdsm3dzjfq4hsenabpr2cl4nyssjth35xkju7oi6q` |
| `benchmark/self_hosting/manifest.json` | generic runtime evidence only | `c08d56ff2daa957f768769d8ac94761d1916f4e5d2b64ef2fe986b769f30489b` | `bafkreigarvlp6lnksv7xnb3j3cwji5q5delpjzoswzhpf7uynn3j6mcitm` |
| `benchmark/self_hosting/qualification.json` | explicit NO-GO / not qualified | `6c5ffee3b265d013e6069f394106e950825d0bfedc3c0278bfb98522ae97fc8f` | `bafkreidml77ohmtf2aj6mbu7hfaqn2kqqjoqx7w4hqbhrp5zqurk5f74r4` |
| `ci/required_jobs.json` | local contract passed; external authority NO-GO | `eacb6d323c9350a233a83f5344ff1f5972b22775365d011d3f80445c516fd553` | `bafkreihkznwtepetkcrdhkb7kncp6h2zokzco5jwluar2p4airofc36vkm` |
| `release/v0.1-rc1/release_manifest.json` | deterministic unpromotable NO-GO bundle | `f0002a16bc97d8b49a15b7097ea1e63f2edbaf4c3a75275faa89026e4f3ed385` | `bafkreihqaavbnpex3c2jufnxbf7kdzr7f3n26tb2outv7kujajxe6pwtqu` |
| `receipts/PCCE-081.json` | independently reviewed; live task completed revision 3 | `928ebfd90e2bc66fd0c9e12fe92394e3682cffd1e83c488b0743a2b91cf1676e` | `bafkreiesr275sdrlyzx5bspbf7ushfhdnawp7upihreiwb2duk4rz4lhny` |

The PCCE-068 receipt uses a structured software-contract CID for its artifact identity. This report separately records raw file CIDs and does not conflate those identity kinds.

## Release-candidate interpretation

The independently reviewed PCCE-081 bundle has all 64 predecessor receipts, exact bindings for the five gate qualifications, two identical deterministic manifest builds, and a passed bounded secret/hidden-body scan. Those facts support bundle integrity only. Its seven retained blockers include installation NO-GO, one unavailable package archive, unavailable package signatures, and explicit self-hosting, benchmark, security, and CI NO-GO decisions. Its delegated `qualification_level` remains `null` with owner `PCCE-082`; this task assigns `research_demo` in a separate projection and does not alter immutable rc1 bytes.

## Restrictions and limitations

- Do not treat task completion, local tests, the benchmark simulated-success structural zero, or generic runtime lifecycle success as qualification.
- Do not infer cost zero, quality zero, provider execution, current-head CI passage, dependency/license passage, security passage, signatures, hidden evaluation, or longitudinal stability.
- Do not use this evidence for an internal pilot, external use, release promotion, or production.
- `research_demo` permits only bounded research/development examination under controls chosen outside this artifact.
- The PCCE-082 evidence task is complete and its exact three-path candidate passed independent review without fixes. The sealed candidate is not provisional and requires no recomposition; PCCE-082 nevertheless remains live `todo` at revision 1, and neither supervisor admission nor database mutation is claimed.

## Rollback and supersession

Retain this projection for its exact evidence cut. New immutable evidence produces a new projection identity; it never relabels these bytes or raises the qualification level automatically.
