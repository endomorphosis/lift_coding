---
name: lra-kernel
description: LRA NCA kernel — cache tiers L0–L3, CID put/get, negative TTL, single-flight, context budget. Use for caching, in-flight lake keys, or CALL ptr://skill/port_{cache_put,cache_get,negative_ttl,singleflight,context_budget}. Cache hits never admit Lean.
---

Canonical skill: `~/lift_coding/JevOps/skills/jevops-kernel/SKILL.md`.
Module: `jevops.kernel`. PYTHONPATH must include JevOps.

LRA `harness/nca_kernel.py` is a shim. L2 CAS dir is `evidence/canaries/nca-cas`. Lake remains the Lean oracle.
