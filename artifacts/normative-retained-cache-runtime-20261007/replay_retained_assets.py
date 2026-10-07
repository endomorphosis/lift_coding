"""Generate from reused exposed-v3 cache; compare archived exact output parity separately."""
import argparse
from contextlib import ExitStack
import datetime
import hashlib
import importlib
import importlib.abc
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/barberb/lift_coding')
DATASETS = ROOT / '.worktrees/normative-cache-input-datasets-20261007'
PACKAGE = 'ipfs_datasets_py.logic.formalization.autoencoder.'
sys.path.insert(0, str(DATASETS))


def pin(path):
    p = Path(path).resolve(strict=True)
    data = p.read_bytes()
    return {'path': str(p), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    return pin(path)


def fail(*args, **kwargs):
    raise AssertionError('No optimizer, fitting or evaluation action during generation')


class ForbiddenImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'duckdb', 'ducklake', 'sentence_transformers',
                'transformers', 'huggingface_hub', 'ipfs_accelerate_py'}:
            raise AssertionError('No encoder/database/Hub/manager imports: ' + fullname)
        if 'modal_latent_formula' in fullname or (fullname.startswith(PACKAGE) and 'training' in fullname):
            raise AssertionError('No historical training owner imports: ' + fullname)


def audit(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo'}:
        raise AssertionError('No network during generation')
    if event == 'open' and isinstance(args[0], (str, bytes)):
        name = str(args[0])
        if 'training-rows.json' in name or 'training.json' in name or 'source-inventory.json' in name:
            raise AssertionError('No training/reference bank reads during generation')
        if 'fresh-source-only-candidates.json' in name or 'semantic-ir-evaluation.json' in name or 'selected-predictions.json' in name:
            raise AssertionError('No prior predictions/evaluations during generation')


def generate():
    sys.meta_path.insert(0, ForbiddenImports())
    sys.addaudithook(audit)
    from ipfs_datasets_py.logic.formalization.autoencoder import normative_cached_legal_ir_runtime as runtime
    assert 'torch' not in sys.modules
    preflight_path = HERE / 'preflight/retained-assets-preflight.json'
    preflight = json.loads(preflight_path.read_text())
    assert preflight['completed'] and len(preflight['selected_states']) == 4
    review_path = HERE / 'independent-review.json'
    review = json.loads(review_path.read_text())
    assert review['approved'] is True and review['findings'] == []
    for source_pin in review['source_file_pins']:
        assert pin(source_pin['path']) == source_pin
    prepared, originals = [], {}
    for record in preflight['selected_states']:
        options_pin = record['options_pin']
        assert pin(options_pin['path']) == options_pin
        options = json.loads(Path(options_pin['path']).read_text())
        plan = runtime.prepare_normative_cached_legal_ir_runtime(**options)
        assert plan['model_manager_selector'] == record['model_manager_selector']
        assert plan['model_tensor_sha256'] == record['model_tensor_sha256']
        for value in [options[name] for name in ('checkpoint_pin', 'preprocessing_pin',
                'donor_checkpoint_pin', 'source_cache_pin', 'source_plan_pin', 'production_pin')]:
            assert pin(value['path']) == value
            originals[value['path']] = value
        for value in plan['historical_evidence_receipts'].values():
            assert pin(value['path']) == value
            originals[value['path']] = value
        prepared.append((record, options))
    assert 'torch' not in sys.modules
    import torch
    torch.set_num_threads(1)
    generation_dir = HERE / 'generation'
    generation_dir.mkdir(exist_ok=True)
    results = []
    start = time.monotonic()
    with ExitStack() as stack:
        stack.enter_context(patch.object(torch.optim.Optimizer, '__init__', fail))
        for name in runtime.contextual.SOURCE_OWNER_NAMES:
            if name.startswith('contextual_'):
                continue
            owner = importlib.import_module(PACKAGE + name)
            for method in ('fit_source_normalization', 'fit_source_count_prior', 'run_trial',
                    '_evaluate', 'unique_training_clauses', 'prepare_source_contexts', 'validate_training_contexts'):
                if hasattr(owner, method):
                    stack.enter_context(patch.object(owner, method, fail))
        for record, options in prepared:
            before_rng = torch.get_rng_state().clone()
            started = time.monotonic()
            handle = runtime.open_normative_cached_legal_ir_autoencoder(**options)
            report = handle.infer_cached()
            candidate = report['raw_candidate_report']
            assert candidate['completed'] and candidate['row_count'] == 48
            assert candidate['model_tensor_sha256'] == record['model_tensor_sha256']
            assert candidate['weights_unchanged'] and candidate['source_inputs_unchanged']
            assert candidate['ambient_rng_preserved'] and torch.equal(before_rng, torch.get_rng_state())
            assert not any(report['authority'].values())
            key = f"{record['dimension']}-{record['arm']}"
            candidate_pin = save(generation_dir / (key + '-candidate-report.json'), report)
            results.append(dict(dimension=record['dimension'], arm=record['arm'],
                candidate_pin=candidate_pin, model_tensor_sha256=candidate['model_tensor_sha256'],
                row_count=48, eos_reached=sum(p['eos_reached'] for p in candidate['predictions']),
                elapsed_seconds=time.monotonic() - started))
            del handle
    assert all(pin(p['path']) == p for p in originals.values())
    for source_pin in review['source_file_pins']:
        assert pin(source_pin['path']) == source_pin
    result = dict(schema='normative-retained-source-cache-replay/v1', completed=True,
        observed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        script_pin=pin(__file__), independent_review_pin=pin(review_path), preflight_pin=pin(preflight_path),
        lanes=results, original_input_pins=list(originals.values()), original_bytes_unchanged=True,
        model_tensor_and_rng_unchanged=True, total_elapsed_seconds=time.monotonic() - start,
        source_only_generation=True, original_targets_opened=False, previous_candidates_opened=False,
        encoder_executed=False, fitting_or_optimizer_executed=False, network_or_database_executed=False,
        runtime_admitted=False, teacher_qualified=False, proof_authority=False,
        legal_prose_reconstruction_measured=False, fresh_holdout=False,
        reused_original_embeddings=True, cached_cohort='exposed_v3_fresh_modality', encoder_execution_attested=False)
    receipt = save(generation_dir / 'generation-result.json', result)
    print(json.dumps({'completed': True, 'receipt': receipt, 'lanes': results}))


def compare():
    assert 'torch' not in sys.modules
    generation = json.loads((HERE / 'generation/generation-result.json').read_text())
    assert generation['completed'] and len(generation['lanes']) == 4
    results = []
    for lane in generation['lanes']:
        assert pin(lane['candidate_pin']['path']) == lane['candidate_pin']
        report = json.loads(Path(lane['candidate_pin']['path']).read_text())
        previous_path = ROOT / ("external/ipfs_datasets/workspace/test-logs/decoder-normative-wording-retention-20261006/"
            f"retention-r1/results/{lane['dimension']}-{lane['arm']}/selected-predictions.json")
        previous = json.loads(previous_path.read_text())
        predictions = report['raw_candidate_report']['predictions']
        archived = previous['predictions']
        assert previous['model_tensor_sha256'] == report['raw_candidate_report']['model_tensor_sha256']
        assert previous['distribution'] == 'previously_exposed_authored_modality_holdout_v3'
        assert [p['id'] for p in predictions] == [p['id'] for p in archived]
        parity = sum(all(p.get(k) == q.get(k) for k in ('token_ids', 'eos_reached', 'generation_status'))
                     for p, q in zip(predictions, archived))
        results.append(dict(dimension=lane['dimension'], arm=lane['arm'], rows=48,
            archived_same_state_prediction_pin=pin(previous_path), candidate_pin=lane['candidate_pin'],
            exact_token_status_EOS_archived_parity=parity, mismatches=48-parity))
    receipt = save(HERE / 'archived-output-parity.json', dict(
        schema='normative-retained-cache-archived-output-parity/v1', completed=True,
        script_pin=pin(__file__), lanes=results, separate_comparison_process=True,
        references_or_gold_scored=False, model_or_encoder_executed=False,
        fresh_semantic_reconstruction_quality_measured=False,
        runtime_admitted=False, teacher_qualified=False, proof_authority=False))
    print(json.dumps({'receipt': receipt, 'lanes': results}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['generate', 'compare'])
    mode = parser.parse_args().mode
    generate() if mode == 'generate' else compare()
