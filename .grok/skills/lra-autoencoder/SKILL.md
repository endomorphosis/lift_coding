---
name: lra-autoencoder
description: VAE-style text→Lean IR→text round-trip for LRA. Use when teaching an autoencoder, scoring variations with TypeSafe Jev vs previous batch rounds, or CALL ptr://skill/port_autoencoder / port_vae / port_lean_ir. Jev replaces CE/cosine as the loss. Lake admits Lean. Never writes Lean.
---

Canonical skill: `~/lift_coding/JevOps/skills/jevops-autoencoder/SKILL.md`.
Module: `jevops.autoencoder`. PYTHONPATH must include JevOps.

LRA `harness/nca_autoencoder.py` is a shim.
