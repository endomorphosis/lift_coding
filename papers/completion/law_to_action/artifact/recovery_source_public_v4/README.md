# Portable LA-029 recovery evidence and analysis

This add-on reproduces the admitted fixed-action results from retained observations. It supplies the actual five-segment host-controller, continuation-driver, cell and reducer lineage that was absent from the original four-snapshot operator import. It is a separately labeled, path-normalized derivative. Original private source bytes, admissions, receipts and all failed attempts remain unchanged.

From a fresh copy of this directory, with Python 3.12 and its standard library:

```sh
python3 -I -B reproduce.py --output /tmp/la029-fresh-analysis
```

Choose an output directory that does not exist. The command reads `evidence.zip` without extracting or importing historical code, verifies every member against `portable_index.json`, checks the retained identity/resource/cost records, and recomputes the split analysis and all 45 paired family-bootstrap comparisons. It writes `verification.json` and `split_analysis.json`. It uses no Docker, network, provider, native store, solver, secret key or benchmark execution. This is the bounded analysis route for this add-on; it does not replace the broader paper artifact's setup instructions or assert a new scientific run.

The archive is 30,925,812 bytes, with 9,976 members expanding to 198,373,746 bytes. It includes all 9,933 inputs bound by the original complete reducer, plus source-lineage and completion evidence. `manifest.json` pins the archive, index and lineage. The included license files preserve the original repository and native-component license texts. Native runtime binaries and a prebuilt container image are not included.

## Observed study and accounting

The unchanged schedule contains 900 scientific cells: 60 cases from 30 lineage families, five arms and three seeds. The development/calibration/final split is 6/6/18 families. The final split contains 54 allowed and 54 forbidden attempts per arm. Five segments retain 902 host attempts:

| Historical segment | Host indices, inclusive | Scientific cells | Additional host startup |
| --- | --- | ---: | --- |
| Original controller | 0–459 | 460 | — |
| Leaf-exit continuation | 460–560 | 101 | — |
| Parent-exit continuation | 561–591 | 30 | 591, before scientific dispatch |
| Startup-591 recovery | 591–625 | 34 | 625, before scientific dispatch |
| Startup-625 recovery | 625–899 | 275 | — |

Indices 459 and 560 retain their original false host-admission flags and monitoring failures. Separate retained physical-boundary dispositions qualify the observed scientific executions. The failed startups at 591 and 625 remain infrastructure records with no scientific outcomes. Positive first-action/custody evidence preceded the single prospective startup recovery at each index. There were two container-startup retries and zero scientific retries.

Measured descendant-inclusive CPU is 1608.817478 seconds: 1608.698691 for scientific cells plus 0.118787 for the two failed startups, counted once. Historical diagnostic CPU that was not measured stays unknown. Cell and segment/controller clocks overlap and must not be added as independent elapsed costs. The recovered 591 and 625 slots used explicitly amended cumulative-active allowances; their combined active walls were 11.766051943 and 19.793533246 seconds. Operator/usage-interruption pauses are separate, not a claim that the original absolute 20-second interval continued uninterrupted.

The frozen physical profile was one CPU with singleton cpuset, 2 GiB memory and no swap, 16 PIDs, per-cell 20-second wall/CPU bounds and an 18,000-second study CPU stop. The reader checks retained resource observations; it does not establish fresh physical enforcement. The original runtime image commitment is `sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6`. Its original runtime-tree manifest is included as evidence, without pretending the original host paths or image are a publicly provisioned runtime.

## Original and portable identities

`portable_index.json` maps each included relative path to both its original SHA-256 and its portable SHA-256. Only fixed private workspace prefixes were replaced with neutral aliases (`recovery_history`, `repository`, `live_repository`, `<AUTHOR_HOME>`). Numeric values, outcomes, event identities, recorded commitments and scientific source logic were retained. Source AST comparison checked that the executable-source transformation changed only path-string constants. The private original-to-public path map is retained outside this artifact.

An original digest embedded inside a record still commits to the original bytes; it is not silently rewritten to claim that transformed bytes are identical. Use the index's `portable_sha256` for included bytes and `original_sha256` for the historical relationship. The index also retains whether a file is byte-identical or path-normalized. Reconstructed historical shared-ready bytes are explicitly labeled in their retained join record; they are not mislabeled as an original snapshot.

`source_lineage.json` joins each segment's actual controller and driver to its historical admission and result. The unchanged cell/mechanism snapshot and final reducer are included. These historical controllers, drivers, verifiers and approved/consumed records are archival references, **not runnable commands or new authority**. Do not execute them or replay their admissions. A new benchmark would need a separately prepared runtime, resource boundary, private store/key and run authorization. The original private signing key, live database, credentials and author companion are absent. Their historical digests or public identities are provenance, not substitutes for usable secret material.

## Claim limits

The labels are frozen modeled policies and independently observed sandbox handler effects. They do not establish real-world legal validity, source-semantic fidelity, compiler soundness, universal prevention, independent human agreement or model efficacy. Model calls were zero; human fidelity and agreement remain unmeasured. Compact rows do not contain full per-cell proof or capability payloads.

Original LA-015 logs and their rescue remain protocol-unadmitted diagnostics, LA-020 traces remain separate diagnostic replays, and LA-009's 18/18 skill-schema metric is shared-producer conformance. Original LA-016 closed-loop cells were not executed; any later study needs its own evidence and must not be inferred from these results. This package preserves the earlier histories and their cost limits without pooling them into the admitted rates.

## Public metadata derivative

This public archive derives from the retained original portable archive. Only two administrative source metadata members replace two private project URLs each with `PRIVATE_PROJECT_URL_REDACTED`. `public_derivation.json` and `portable_index.json` retain the original, prior portable, and new public commitments. All other indexed members are byte-identical, including every observed outcome and cost record. Original controller source commitments and private historical artifacts remain unchanged.
