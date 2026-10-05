---
license: agpl-3.0
tags:
- autoencoder
- reconstruction
- experimental
---

# Source-vector reconstruction autoencoders: nine completed experimental fits

These nine new models reconstruct frozen native source vectors. They are
separate from the old spaCy categorical heads, the retained 384D residual/formula
model, and the 768D-conditioned span decoder. No text encoder backbone or
text-to-formal decoder is included.

| Lane | Native input/output | Hidden width | Complete latent width |
| --- | ---: | ---: | ---: |
| legacy8 | 8 | 16 | 4 |
| native384 | 384 | 128 | 32 |
| native768 | 768 | 128 | 64 |

Every lane has seeds 1729, 1730 and 1731. Each encoder has two linear layers
with an intermediate tanh; the decoder reverses the widths with tanh. There
is no skip connection or sample memory. Normalize native coordinates using
the saved TRAIN coordinate mean/global centered RMS, encode, decode, then
reverse normalization. The complete latents are 4D, 32D and 64D respectively.

The inputs are frozen spaCy8 linguistic features, mean-pooled/L2 GTE-small384,
and CLS-pooled/L2 GTE-multilingual768 with pinned producer revisions. No text
backbone fine-tuning or new backbone inference occurred in these fits. The
original producer normalization and the AE's TRAIN transform are distinct.

Each model completed 200 selected-lineage Adam updates at .003, batch8,
CPU float32/one thread and gradient clipping5. Selected step200 was fixed
before fitting. The cohort is the same historical16 TRAIN sources/four groups;
no DEV/query scoring, formal labels or semantic relations were used. Across
nine arms there are 1,800 selected updates and 27 separately counted scratch
Adam-resume comparison updates, 1,827 actual updates. The selected200 master
was preserved. Exact private reload outputs, resumed parameters/Adam moments,
finite values and CPU RNG preservation are recorded in the selected reports.

## Load and check

Keep each checkpoint triplet together. Externally select the manifest SHA256
and run `python -I -B verify_reconstruction_release.py --directory .
--expected-manifest-sha256 SELECTED_SHA256`. The stdlib checker verifies exact
files, seals, F32 tensor shapes, finite values, saved Adam steps/moments and
canonical serialized-value digests. It creates no model and performs no
numerical forward/optimizer call. Compact summaries bind the original reports;
latent/reconstruction row tables and data banks are excluded.

The exact included `train_reconstruction.py::load_checkpoint(torch,
checkpoint_file_binding, selected_config)` is the numerical load route.
Its original selected workers used Torch2.13.0+cu130 and safetensors0.7.0 while
explicitly computing on CPU. Select the checkpoint JSON file SHA independently
and the exact config from the manifest, preserving the triplet's local filenames.
The loader verifies implementation SHA, tensors, Adam and normalization; it
does not reopen the historical bank. A numerical download/restore smoke was
not executed by the publication preparer.

```python
# First verify/load the exact manifest-pinned helper source bytes.
model, adam, checkpoint = helper.load_checkpoint(torch, selected_file_binding, selected_config)
with torch.inference_mode():
    mean = torch.tensor(checkpoint['normalization']['mean'], dtype=torch.float32)
    rms = checkpoint['normalization']['rms']
    latent = model['encoder']((native_vectors - mean) / rms)
    reconstructed = model['decoder'](latent) * rms + mean
```

TRAIN reconstruction error is an engineering measure. Raw identity MSE is0
without compression. Error reduction against an untrained network establishes
no held-out reconstruction, retrieval quality, text meaning, source fidelity,
prover truth or logic-family coverage. Different widths/capacities prevent
using cross-lane MSE as a semantic ranking. All five semantic/decoder masks
remain0; semantic/contrastive fit authority, qualification, fidelity and proof
authority remain false. Reconstruction-only training is explicitly authorized.
No human identity/independence or relation admission is authenticated here.

Authorial source/checkpoints use AGPL-3.0. Upstream embedding backbones retain
their licenses and are neither copied nor relicensed by this release.
