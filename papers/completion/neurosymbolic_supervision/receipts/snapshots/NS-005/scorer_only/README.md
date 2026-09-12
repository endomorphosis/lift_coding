# Scorer-only hidden oracle store

This directory is the independent scorer principal store for NS-005.

Proposal generation, arm A–D context packing, and any training/synthesis
process must not mount, search, or copy these files. NS-006 must enforce
that isolation.

Contained material:

- `oracles/*/oracle.json` — scorer identifiers, FAIL_TO_PASS node ids, and
  SHA-256 pins for the privately held reference patch and hidden tests.
  Payload bytes are reconstructed from the pinned `pre_fix_commit` /
  `fix_commit` and are **not** stored in this tree.
- `qualification_fixture/` — compact independently generated
  `nsq_fixture_v1` sources used by Table 12 mutation recipes.

`tasks.jsonl` may name oracle IDs and content hashes but must not embed
patch or hidden-test payloads.
