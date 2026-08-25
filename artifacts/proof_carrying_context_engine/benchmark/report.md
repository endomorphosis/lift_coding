# PCCE-068 benchmark qualification report

Decision: **NO-GO** for benchmark qualification and release qualification.

This is a completed deterministic evidence projection over the immutable PCCE-067 population at outer commit `caefdd51db180e43885ef3bf51e0794ac6b00e45` (tree `6512c396bbf2c086d69e91b5fa5df4df280337a6`). It is not a measured benchmark failure: all four primary gates are unavailable because no provider/model execution or required outcome measurement exists.

Independent review, outer composition admission, and task completion remain pending. This candidate does not mutate the board, Quack/DuckDB, the canonical branch, raw results, thresholds, or predecessor receipts.

## Population

All 84 terminal PCCE-067 records were retained and admitted by the shipped schema and population validators. Each of 21 frozen tasks has one record for each configuration A-D.

| Repository class | Tasks | Rows | Rows per configuration | C/D routine-localized tasks |
| --- | ---: | ---: | ---: | ---: |
| Typed structured | 6 | 24 | 6 | 4 |
| Dynamic/plugins | 7 | 28 | 7 | 4 |
| Mature Python | 8 | 32 | 8 | 6 |
| Total | 21 | 84 | 21 | 14 |

Every row has `terminal_status=unavailable`, `eligible_task_count=1`, `provider_call_count=0`, and `route_unavailable_count=1`. No row was dropped. The A/D paired population has 21 task clusters and no unmatched cluster.

## Metrics and missingness

The frozen catalog contains 78 metrics. Across 6,552 raw metric slots, 294 control/classification slots are observed and 6,258 are explicitly null with bound missingness reasons.

| Configuration | Rows | Raw observed slots | Raw null slots | Eligible | Unavailable routes | Provider calls | Routine-localized | Observed total cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A | 21 | 63 | 1,575 | 21 | 21 | 0 | not applicable | unavailable (`null`) |
| B | 21 | 63 | 1,575 | 21 | 21 | 0 | not applicable | unavailable (`null`) |
| C | 21 | 84 | 1,554 | 21 | 21 | 0 | 14 | unavailable (`null`) |
| D | 21 | 84 | 1,554 | 21 | 21 | 0 | 14 | unavailable (`null`) |

Context/token, patch-quality, latency, test, proof-reuse, assurance, provider/model, and monetary-cost observations are unavailable. Zero provider calls is an observed control fact; it does not make unknown monetary cost equal to zero.

The shipped scorer derives `correct_accepted_patch_rate_bp=0` from the preregistered rule that eligible terminal failures or abstentions score zero. That value is a scoring penalty, not an observed live-quality measurement, and it cannot qualify the evidence.

`metrics.json` publishes every catalog definition, every A-D aggregate value and missingness disposition, all per-class aggregate values, the complete 84-row terminal ledger, confidence inputs, and deterministic aggregate/comparison CIDs.

## Primary thresholds

| Gate | Frozen requirement | Projection | Evidence status | Decision |
| --- | --- | --- | --- | --- |
| Context reduction | A vs D, minimum 5,000 bp | estimate and bound unavailable | context denominator missing | `unavailable-no-go` |
| Accepted-patch noninferiority | D-A lower bound at least -500 bp | scorer projection 0 bp; 95% lower bound 0 bp | descriptive non-live; raw quality unavailable | `unavailable-no-go` |
| Total cost reduction | A vs D, minimum 3,000 bp | estimate and bound unavailable | paired observed-live cost missing | `unavailable-no-go` |
| Routine frontier escalation | D upper bound at most 2,500 bp | estimate and bound unavailable | frontier numerator missing for 14 routine tasks | `unavailable-no-go` |

The accepted-patch bootstrap drew 10,000 deterministic paired-task replicates, but its evidence class is ineligible because it contains no observed live quality. The other three confidence projections have no defined estimate. Confidence computation never upgrades missing evidence.

## Zero-tolerance checks

| Check | Required | Observed | Decision |
| --- | ---: | --- | --- |
| Simulated success accepted | 0 | structurally derived 0 from 84 non-simulated rows | `pass` |
| Critical regression accepted | 0 | unavailable across 84 applicable rows | `unavailable-no-go` |
| Stale capsule accepted | 0 | unavailable across 42 C/D rows | `unavailable-no-go` |
| Stale proof accepted | 0 | unavailable across 42 C/D rows | `unavailable-no-go` |
| Controlled selected-test false negative | 0 | unavailable across 42 C/D rows | `unavailable-no-go` |
| Critical mutant accepted | 0 | unavailable across 21 D rows | `unavailable-no-go` |
| Negative-review autonomous accept | 0 | unavailable across 21 D rows | `unavailable-no-go` |

The sole pass is structural and narrow: non-simulated provenance proves that simulated success was not accepted. It says nothing about provider quality, cost, correctness, security, or release readiness. The remaining six checks are unavailable, not measured passes or measured failures.

## Decision and blockers

There are no measured threshold failures and no waivers. Qualification is nevertheless `NO-GO` because four primary gates and six zero-tolerance checks lack qualifying evidence. Neither benchmark nor release qualification can be inferred from population completeness alone.

No provider permit, provider/model dispatch, model revision/output, patch proposal, hidden evaluator execution, test result, proof, assurance result, latency, or observed monetary cost is present. A future permitted run must publish a separately identified raw population; it must not rewrite these unavailable records.

## Evidence identities

- Raw population: SHA-256 `2973a0c9468ca14dda509578c1da7a1d649b48df13c9292592f34a7872a66c2a`, raw CID `bafkreibjooqmsrumufg5uuevpda5u6q5msnurxytzeuslextjj4hfjtmfi`.
- Run manifest: structured CID `baguqeeraem6tjti2y3bjbsdyyr2klsdkfxhvo6xywfmbw2zmgils244jjd4q`.
- PCCE-067 execution receipt: structured CID `baguqeeracruwjey3ittkczloj74nxtamwnbme22tiptck3ftb4c647h7olwq`.
- PCCE-067 task receipt: SHA-256 `363d4ffd662873bf80aa8bbd704bbdf44304df35b844532220da462ae732d8c1`, structured CID `baguqeerabhtpvxxanndurequvfpbgpc3rxmnnrer4idjf6sjm3f45jpeuqxa`.
- Frozen threshold set: structured CID `baguqeeraqbhgjlvhrdrwfashgtvwsb5e4k3fac5mg75j6f4p4gvxbaz75b6q`.
- Deterministic aggregate set: `baguqeerapfe3u56yaqccjp3ogvexdb7sqefw4sl2zilf4t6eu5ucuqwjeqpa`.
- Deterministic comparison report: `baguqeerauzrslzgeyq6cxn2k5rsluxhjjpynbcuuptapfhxg7fml7sjwafzq`.
- PCCE-068 metrics: SHA-256 `09c50c845ac1c2038bb6be3a879855a913ec2d9ed6644d3f126e32a5e2086664`, raw CID `bafkreiajyugiiwwbyibyxnv6hkdzqvnjcpwc3hwwmrgt6etogks6ecdgmq`, structured CID `baguqeerasfa2mtggtcmtqsfguoyzckjsjmryzzji7fq2vcuirqmnjxzgoava`.
- PCCE-068 qualification: SHA-256 `13dcaf260fcbbed9dd72b53954e6bdfd12db27a423ee96343d18afca8bf1c077`, raw CID `bafkreiat3sxsmd6lx3m524vvhfkonpp5clnspjbd52ldipiyv7fix4oao4`, structured CID `baguqeeraxdcsravklkrwuqftkaf3nuqvqnrnnj6ypwydsnntxv4l45veuxca`.

## Validation state

The exact shipped metrics suite passed 124 tests. Both JSON projections passed strict parsing and `json.tool`; all source/output hashes and CIDs are subject to final independent recomputation. Independent review is pending and is not claimed by this report.
