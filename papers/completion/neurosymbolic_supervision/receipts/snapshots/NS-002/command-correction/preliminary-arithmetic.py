import json, statistics
from pathlib import Path
semantic=json.loads(Path('external/ipfs_accelerate/docs/benchmarks/semantic_compression_harness_results.json').read_text())
sealer=json.loads(Path('external/ipfs_accelerate/artifacts/agent_supervisor/incremental_proof_sealer/summary.json').read_text())
rows=semantic['results']
print(json.dumps({'semantic_task_count': len(rows),'median_reduction_percent': statistics.median(sorted(row['reduction_ratio'] for row in rows))*100,'model_receipt_emitted_count': sum(row['model_receipt_emitted'] for row in rows),'production_eligible_true_count': sum(row['production_eligible'] for row in rows),'production_root_advanced_count': sum(row['production_root_advanced'] for row in rows),'sealer_transition_count': sealer['transition_count'],'average_reuse_rate_percent': sealer['average_reuse_rate']['value_percent'],'average_compute_reduction_percent': sealer['average_compute_reduction']['value_percent'],'measured_prover_cpu_rows': sealer['metric_summary']['prover_cpu_seconds']['measured_rows'],'measured_prover_gpu_rows': sealer['metric_summary']['prover_gpu_seconds']['measured_rows']}, sort_keys=True))
