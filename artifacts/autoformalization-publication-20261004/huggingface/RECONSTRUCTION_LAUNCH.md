# Frozen reconstruction launch after verified publication

Use the unchanged helper and run plan. Their exact file SHA-256 values are:

- `train_reconstruction.py`: `387c0335549374a98e1d5458d9746733fe385dd760584fdf059f6266c44873d3`
- `run-plan-02.json`: `b02b0b35a9f2d82abd5422643f9034bea30e1d83f0c21772aa0a609c234ead3b`

The original README's literal isolated Python command cannot discover the native user-site Torch installation. The new launcher inserts only `/home/barberb/.local/lib/python3.12/site-packages` with `sys.path.insert`; it does not invoke `.pth` files in that selected site. It verifies Torch 2.13.0 and safetensors 0.7.0 distribution locations and entrypoint hashes before invoking the frozen helper through `runpy`. It uses CPU and one thread. This is a trusted process with selected-entrypoint pins, not an OS sandbox or a complete transitive import-closure verifier. The helper rechecks its own source and fixed plan before any Torch import. The wrapper rechecks selected source bytes afterwards. No training was run to prepare these launch notes.

The metadata-only route performs no Torch/safetensors imports or fits:

```sh
/home/barberb/.local/bin/python -I -B /home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/huggingface/launch_reconstruction.py --metadata-only
```

Root first verifies the initial Hugging Face and GitHub publication receipts, then writes a separately selected gate with exactly four fields:

```json
{"schema":"reconstruction-publication-gate/v1","published_artifact_receipts_sha256":"ROOT_SELECTED_64_HEX_RECEIPT_SHA","training_release_authorized":true,"content_sha256":"CANONICAL_BODY_SHA"}
```

The gate self-checksum `content_sha256` is SHA-256 of `json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")`, excluding `content_sha256` and **without a trailing newline**. The external `--publication-gate-sha256` is instead SHA-256 of the complete gate file's exact bytes, including any newline or indentation. These identities must not be conflated. The helper accepts a lowercase 64-hex receipt digest but does not derive or authenticate its publication meaning. Root should define that field as the exact SHA-256 of its selected aggregate publication evidence file binding both the HF releases and verified Git publication. The gate records root's internal release decision under the user's existing authorization; it is not a semantic admission or human authentication receipt.

After selecting the actual gate path and its exact file digest, run one fresh subprocess for each Cartesian product of lanes `legacy8,native384,native768` and seeds `1729,1730,1731`. Root creates a fresh `training/run-01` parent first; each arm directory must be absent. Example for one arm:

```sh
/home/barberb/.local/bin/python -I -B /home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/huggingface/launch_reconstruction.py --lane native768 --seed 1729 --output-directory /home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/training/run-01/native768-seed1729 --publication-gate /ROOT_SELECTED_GATE.json --publication-gate-sha256 ROOT_SELECTED_EXACT_FILE_SHA
```

The parent must use `Popen(..., start_new_session=True)`, bounded stdout/stderr capture, a 120-second wall deadline **per arm**, and short polling intervals. On timeout or failure, kill the process group, wait for it, and save durable exit/resource evidence. Do not overwrite failed arm directories. The launcher itself provides no parent wall watcher. The unchanged helper applies CPU soft/hard limits 90/100 seconds, address-space 8 GiB and output-file 32 MiB before Torch import; its 60-second training deadline is cooperative. Its selected-200 states and three private scratch updates per arm total 1,800 selected-lineage + 27 scratch = 1,827 updates if all nine complete.

Successful arms must emit exact report bindings. Before second publication, verify nine distinct lane/seed reports, each selected-200 triplet, explicit 203 total updates, TRAIN rows 16, query/DEV rows zero, all five semantic masks zero, source/proof/qualification flags false, exact reload and Adam-resume assertions, finite numerical state, and unchanged helper/run-plan/input file pins. Preserve step0/100 and scratch states locally while publishing only the explicitly selected final triplets and truthful reports. No new fidelity, retrieval, proof or independently reviewed family-coverage result follows from reconstruction MSE.
