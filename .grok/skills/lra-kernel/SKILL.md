---
name: lra-kernel
description: LRA NCA kernel — cache tiers L0–L3, CID put/get, negative TTL, single-flight, context budget. Use for caching, in-flight lake keys, or CALL ptr://skill/port_{cache_put,cache_get,negative_ttl,singleflight,context_budget}. Cache hits never admit Lean.
---

# NCA kernel

`harness/nca_kernel.py`. Supervisor-inspired, lake still the only Lean oracle.

| Tier | Store |
| --- | --- |
| L0 | neural tape / DT window |
| L1 | `nca.kernel.l1` process dict |
| L2 | `evidence/canaries/nca-cas/` files |
| L3 | optional JSON-LD DuckDB (never control.duckdb) |

- Put/get by `sha256:` CID. `theorem_ok` is stripped.
- L1 eviction: **ARC** (default) or **LRU**. CALL `port_cache_arc` / `port_cache_lru`. ARC uses T1 recency, T2 frequency, B1/B2 ghosts, integer `p`.
- Negative cache expires after N ticks (default 32).
- Single-flight: second begin on the same key returns `in_flight`.
- Context budget: `keep_k` on the tape.

Never docker0. Jev does not write Lean.
