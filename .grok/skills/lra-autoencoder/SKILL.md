---
name: lra-autoencoder
description: VAE-style text→Lean round-trip for LRA. Use when teaching an autoencoder, scoring variations with TypeSafe Jev vs previous batch rounds, or CALL ptr://skill/port_autoencoder / port_vae. Jev replaces CE/cosine as the loss. Lake admits Lean. Never writes Lean.
---

# LRA VAE autoencoder

`harness/nca_autoencoder.py`. CALL `ptr://skill/port_autoencoder` or `port_vae`.

- Encode unstructured text to milles `mu`/`logvar`. Sample several VAE latents. Decode to Lean sketches (codebook of lake-ok snippets when taught).
- **Loss is Jev**, not CE/cosine. Jev Choice/Score/Noul ranks the current variation against previous rounds in `nca.autoencoder.batch`.
- `ipfs_datasets_py` `cosine_similarity` / `cosine_loss` are **diagnostics** (`gold: false`), matching the autoformalization protocol.
- Among Jev-ok variants, keep the **shortest** lake-valid Lean. Jev never writes Lean. Never docker0. Not Arena scores.
