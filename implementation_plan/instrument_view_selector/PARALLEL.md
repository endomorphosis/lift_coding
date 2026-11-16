# Parallel waves

A wave starts when every task it depends on is `completed`. Inside a wave, tasks run together only when their write scopes do not share a path.

| Wave | Tasks | Wait for | What runs together |
| --- | --- | --- | --- |
| A | IVS-001, IVS-003 | nothing | Site selector files and the SwissKnife package. Different repositories. |
| B | IVS-002 | IVS-001 | ResultItem marker. May run beside IVS-003, because it does not edit SwissKnife. |
| C | IVS-004 | IVS-001, IVS-002, IVS-003 | One read-only proof. Writes only its evidence file. |

The supervisor launches at most two live workers. It asks `llm_router` once per launch wave. It does not rank providers a second time.
