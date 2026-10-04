---
license: agpl-3.0
tags:
- autoencoder
- reconstruction
- formal-logic
- experimental
---

# Source-vector reconstruction autoencoders: prepared second release

Status: template only. The numerical runs and selected trained artifacts must be verified before this card is finalized or uploaded. Proposed destination: `Publicus/legal-ir-autoencoder`, new append-only prefix `releases/20261004-source-reconstruction-aes-v1`.

These new lineages reconstruct frozen native source vectors. They are separate from the retained spaCy categorical sparse heads, the 384D residual reconstruction/formula model, and the 768D-conditioned span decoder. No backbone weights or text-to-formal decoder are included.

| Lane | Native input/output width | Hidden width | Complete latent width | Seeds |
| --- | ---: | ---: | ---: | --- |
| legacy8 | 8 | 16 | 4 | 1729, 1730, 1731 |
| native384 | 384 | 128 | 32 | 1729, 1730, 1731 |
| native768 | 768 | 128 | 64 | 1729, 1730, 1731 |

Each encoder has two linear layers with an intermediate tanh; the decoder reverses the widths with an intermediate tanh. There is no skip connection or sample-memory table. Each model receives native-vector coordinates after a TRAIN-only coordinate mean and global centered RMS transform, distinct from the original producer's pooling and normalization. Decode in normalized coordinates, then reverse that saved transform to reconstruct the native vector.

The fixed objective is vector self-reconstruction MSE on the same ordered 16 historical TRAIN rows. The raw inputs retain their producer identities: spaCy linguistic 8D features, pinned mean-pooled L2-normalized GTE-small 384D embeddings, and pinned CLS-pooled L2-normalized GTE-multilingual 768D embeddings. The raw text encoder assets are obtained separately. The training helper validates exact producer, source, vector and TRAIN cohort pins; it reads no formal target bodies, DEV/query vectors, or human review packages.

The declared budget is 200 Adam updates per lane/seed, learning rate .003, batch size 8, CPU float32 with one thread and gradient clipping 5. The selected checkpoint is fixed at update 200. Nine arms therefore plan 1,800 selected-lineage updates plus 27 separately counted private resume checks: 1,827 total. Actual completed counts, resource observations and exact report bindings must replace this planned wording after the runs.

The helper saves updates 0, 100 and 200. It privately restores model and Adam at 100, checks exact selected-200 reload outputs, and compares a direct 200→201→202 continuation with a separate saved-201→202 continuation, including Adam moments. Those three extra updates per arm leave the selected-200 master unchanged. Checkpoints use safe tensor files with closed JSON metadata, exact tensor-file SHA-256, names, shapes, float32/CPU and finite-value checks. No pickle loader is used.

Publish the nine selected-200 triplets together with their actual training reports, exact helper, frozen run plan, authorial license, a bounded stdlib integrity checker, and manifest containing externally selected file pins. Keep each triplet's `checkpoint.json`, `model.safetensors` and `optimizer.safetensors` together. The checkpoint-local tensor filenames permit relocation. Original data-bank absolute paths in metadata describe historical provenance; the loader does not need to reopen those banks.

After downloading an exact pinned release revision, use the included helper and externally selected manifest config:

```python
# Load the exact manifest-pinned train_reconstruction.py using importlib.
# Its SHA must equal the helper SHA recorded in the selected checkpoint config.
import torch
model, adam, checkpoint = helper.load_checkpoint(
    torch, independently_selected_checkpoint_file_binding, selected_asset_config
)
with torch.inference_mode():
    x = torch.tensor(native_vectors, dtype=torch.float32)
    mean = torch.tensor(checkpoint["normalization"]["mean"], dtype=torch.float32)
    rms = checkpoint["normalization"]["rms"]
    latent = model["encoder"]((x - mean) / rms)
    reconstruction = model["decoder"](latent) * rms + mean
```

The exact selected config is required, including original native producer/pooling identity and TRAIN normalization. The loader compares that config against the checkpoint; it is not a semantic admission verifier. The original worker used Torch 2.13.0+cu130 and safetensors 0.7.0 while explicitly computing on CPU.

Raw identity reconstruction has MSE zero without compression; it is a control. Training-set error reduction against an untrained network does not establish held-out reconstruction, retrieval quality, text meaning, formalization fidelity, prover truth, or support for any logic family. Widths and capacities differ across lanes; their MSE values are not a semantic ranking of the source encoders. No DEV selection or evaluation is performed. All five semantic/decoder admission masks stay zero; qualification, source fidelity, proof authority and semantic/contrastive fit authorization stay false. Training is explicitly reconstruction-only.

No human reviewer identities or independence have been authenticated by these models. No genuine process-owned review registry or admitted TRAIN relation ledger is created. The 40-family independent semantic pilot and contrastive fitting remain separate pending work. Publication does not promote any trust or admission state.
