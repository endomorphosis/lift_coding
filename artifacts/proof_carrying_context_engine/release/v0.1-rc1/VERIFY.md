# PCCE v0.1-rc1 verification

This directory is an immutable, unpromoted **NO-GO** evidence bundle. It is
not a signed release and does not claim a provider run, a CI run, benchmark
qualification, security qualification, or package publication.

From the outer repository root, run:

```sh
python external/ipfs_accelerate/scripts/proof_context/build_release_candidate.py --check artifacts/proof_carrying_context_engine/release/v0.1-rc1
python -m json.tool artifacts/proof_carrying_context_engine/release/v0.1-rc1/release_manifest.json
python -m json.tool artifacts/proof_carrying_context_engine/release/v0.1-rc1/qualification.json
```

The first command reconstructs every byte from the frozen Git evidence cut,
checks all transitive SHA-256/raw-CID bindings, and repeats the secret/hidden
body scan. A different evidence population requires `v0.1-rc2`; rc1 must not
be overwritten.
