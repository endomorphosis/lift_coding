"""Capture bounded static planning facts without launching any model or service."""
import hashlib
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
OUTPUT = CAMPAIGN / 'alignment-next-experiments-readiness-02'
GIB = 1024**3
MODEL = Path('/home/barberb/.cache/ipfs_accelerate_py/llama_cpp/models/cid-v1/bafkreicgnd6su3jhmtpckbejqurdb2lchdvvydluswdg5m5zy3cpvroh3i/Leanstral-1.5-119B-A6B-NVFP4.gguf')


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def binding(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    assert not OUTPUT.exists(), 'fresh snapshot required'
    observed_utc = datetime.now(UTC).isoformat()
    info = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, rest = line.split(':', 1)
        if key in {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'}:
            count, unit = rest.split()
            assert unit == 'kB'
            info[key + '_bytes'] = int(count) * 1024
    gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free',
                          '--format=csv,noheader,nounits'], capture_output=True, text=True,
                         timeout=5, check=False)
    model_info = MODEL.stat()
    memory_limit, reserve = 90 * GIB, 12 * GIB
    estimate = model_info.st_size * 1.10 + min(4 * GIB, memory_limit * 0.1)
    admitted_by_formula = estimate <= memory_limit and estimate + reserve <= info['MemAvailable_bytes']
    path = CAMPAIGN / 'canonical-codec-01/train_weak_supervision.json'
    train_document = json.loads(path.read_bytes())
    assert train_document['content_sha256'] == digest({k: v for k, v in train_document.items() if k != 'content_sha256'})
    rows = train_document['rows']
    canonical_ids = [digest(row['proposal']['canonical_ir']) for row in rows]
    masks = Counter(tuple(sorted(row['masks'].items())) for row in rows)
    expected_masks = dict(weak_decoder_fit=1, strong_semantic_fit=0, contrastive_supervision=0,
                          proof_supervision=0, fidelity_evaluation=0)
    assert len(rows) == len(set(canonical_ids)) == 16 and len(masks) == 1
    assert all(row['masks'] == expected_masks for row in rows)
    group_counts = Counter(row['group_id'] for row in rows)
    assert len(group_counts) == 4 and set(group_counts.values()) == {4}
    source_paths = [ROOT / 'scripts/run_leanstral_ephemeral.py',
                    ROOT / 'scripts/benchmark_leanstral_embeddings.py', ROOT / 'JevOps/jevops/leanstral.py',
                    REPO / 'ipfs_datasets_py/logic/formalization/autoencoder/alignment_projection.py',
                    REPO / 'ipfs_datasets_py/logic/autoformal/legal_review_admission.py',
                    REPO / 'ipfs_datasets_py/logic/legal_ir/canonical_binding_review.py']
    record = dict(schema='alignment-next-experiments-static-readiness/v1', observed_utc=observed_utc,
        runner_binding=binding(__file__), source_bindings=[binding(p) for p in source_paths],
        training_manifest_binding=binding(path), training_rows=16, distinct_canonical_targets=16,
        source_groups=4, variants_per_group=4, original_training_masks=expected_masks,
        original_contrastive_masks_enabled=0, existing_group_ids_are_equivalence_labels=False,
        new_weak_contrastive_policy_required_before_diagnostic_fit=True,
        memory_observation=info, gpu_query=dict(exit_code=gpu.returncode, stdout=gpu.stdout.strip(),
            stderr=gpu.stderr.strip(), numeric_gpu_memory_availability_established=False),
        model_stat=dict(model_path=str(MODEL), resolved_model_path=str(MODEL.resolve()),
            bytes=model_info.st_size, modified_ns=model_info.st_mtime_ns, full_model_hash_verified=False),
        common_runner_resource_formula=dict(memory_limit_bytes=memory_limit, reserve_bytes=reserve,
            estimated_model_and_headroom_bytes=int(estimate),
            estimated_model_headroom_and_reserve_bytes=int(estimate + reserve),
            admitted_by_formula=admitted_by_formula,
            result='fits_formula_at_snapshot' if admitted_by_formula else 'would_reject_at_snapshot',
            scope='evaluation_of_existing_common_runner_formula_not_an_executed_embedding_preflight',
            runner_preflight_invoked=False),
        service_queries_or_mutations_executed=False, model_loaded=False, embeddings_generated=0,
        projection_fit_executed=False, optimizer_updates=0, prover_calls=0,
        authenticated_reviews_created=0, labels_admitted=0, masks_changed=False,
        qualified=False, accepted=False, source_fidelity_established=False, proof_authority=False)
    record['content_sha256'] = digest(record)
    OUTPUT.mkdir()
    (OUTPUT / 'snapshot.json').write_bytes(raw(record) + b'\n')
    print(json.dumps(dict(binding=binding(OUTPUT / 'snapshot.json'), memory_available_gib=info['MemAvailable_bytes']/GIB,
                          estimated_required_gib=(estimate+reserve)/GIB, admission_formula_result=record['common_runner_resource_formula']['result'],
                          distinct_train_targets=16, original_contrastive_masks_enabled=0), sort_keys=True))


if __name__ == '__main__':
    main()
