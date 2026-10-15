The final T4 experiment completed on September 14, 2026, using the unchanged qualified collector and all three finalized T3 checkpoint exports. It executed guidance off, on, and rollback for each of 1,913 held-out native C candidates and each of three training seeds.

- All 5,739 source–seed pairs consumed the learned obligation prior and changed the check order.
- All 34,434 required structural check calls actually executed, with no execution errors.
- All 5,739 pairs preserved their check outcomes and restored the baseline order after rollback.
- All candidates passed the two structural checks. Of these, 5,679 source–seed pairs were nonempty, corresponding to 1,893 distinct sources. Twenty distinct sources produced valid empty representations and do not count toward nonempty coverage.
- The collector used 50.294 wall seconds, 50.689 process-CPU seconds, and 1,831,612,416 bytes of peak resident memory.

The full emitted-head audit found one identical complete head vector across all sources and seven fixed contexts within each seed. The vector is also identical across all three seeds. The obligation prior assigns 0.593398469592 to provenance preservation and 0.406601530408 to modal well-formedness. This is a learned global prior, not source-specific prediction or calibrated confidence in semantic fidelity or proof truth.

Both checks execute in every condition. The final population contains no failing checks, so this experiment supplies no estimate of earlier failure discovery. Fixed off/on/rollback order also precludes a speedup interpretation. The result demonstrates actual learned-state consumption, unchanged structural acceptance, and reliable rollback. Independent legal-semantic fidelity, native proof success, and the historical proposed canonical-field mutation adapter remain outside this experiment.

`final_join/summary.json`, all three `paired_seed*.jsonl` files, and `head_distribution_audit.json` retain the measured observations. `completion.json` records successful collection, head auditing, anonymous export, and portable verification. `portable_reproduction.json` confirms exact reproduction of every per-seed and pooled count and timing summary from the unchanged observation receipts. The standalone anonymous component is `../supplement_staging/guidance/`; its reproduction requires only the Python standard library and performs no fresh model calls or native check calls.
