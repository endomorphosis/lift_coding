"""Matched warm starts; both selections durable before fresh final references."""
from collections import Counter
from contextlib import ExitStack
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import time
from unittest.mock import patch

import torch
from ipfs_datasets_py.logic.formalization.autoencoder import legal_grouped_span_decoder_v2 as head
from ipfs_datasets_py.logic.deontic.utils import deontic_parser
from ipfs_datasets_py.logic.deontic import decoder as legacy

OUT = Path(__file__).resolve().parent
OLD = OUT.parent / 'legal-grouped-head-v2-20261006'
spec = importlib.util.spec_from_file_location('original_grouped_measurement', OLD / 'run_v2_training_corrected.py')
measurement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measurement)


def pin(path):
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return pin(path)


def load(ref):
    path = Path(ref['path'])
    assert pin(path) == ref
    return json.loads(path.read_text())


def reject(*args, **kwargs):
    raise AssertionError('Inference accessed training targets, parser, or a legacy fallback')


def evaluate(model, rows, split):
    with ExitStack() as stack:
        for module, names in ((head, ('_labels', 'GroupedSpanTarget', 'GroupedSpanExample', 'train_grouped_span_step')),
                (deontic_parser, ('extract_normative_elements', 'analyze_normative_sentence', 'classify_modal')),
                (legacy, ('decode_legal_norm_ir',))):
            for name in names:
                stack.enter_context(patch.object(module, name, reject))
        return measurement.evaluate(model, rows, split=split)


def score(summary, additional_updates):
    return (summary['mixed_exact_count'], -summary['negative_emitted_request_count'],
            summary['positive_exact_count'], -additional_updates)


torch.set_num_threads(2)
torch.use_deterministic_algorithms(True)
assert not torch.cuda.is_initialized()
plan_path = OUT / 'experiment-plan.json'
plan = json.loads(plan_path.read_text())
runner_pin = pin(Path(__file__))
producer_pins = head.producer_pins()
parent_path = Path(plan['parent_checkpoint']['path'])
assert pin(parent_path)['sha256'] == plan['parent_checkpoint']['sha256']
parent = json.loads(parent_path.read_text())
train = load(plan['training_corpus'])
selection = load(plan['selection_reference'])['rows']
assert plan['sealed_final_reference']['sha256'] == pin(Path(plan['sealed_final_reference']['path']))['sha256']
# Hashing the sealed bytes is an integrity observation, not parsing references.
positive = [row for row in train['original_rows'] if row['supported']]
negative = [row for row in train['original_rows'] if not row['supported']]
targeted = train['targeted_negatives']
assert len(positive) == len(negative) == 1280 and len(targeted) == 2560
for rows in (positive, negative, targeted):
    assert all(row['split'] == 'train' for row in rows)
    assert all(set(row['input']) == {'source_text', 'modal_scope'} for row in rows)
selection_sources = {r['input']['source_text'] for r in selection}
assert selection_sources.isdisjoint({r['input']['source_text'] for r in positive + negative + targeted})
rng = random.Random(plan['batch_order_seed'])
positive_order = list(range(len(positive)))
negative_order = list(range(len(negative)))
targeted_order = list(range(len(targeted)))
rng.shuffle(positive_order)
rng.shuffle(negative_order)
rng.shuffle(targeted_order)
schedule = []
for update in range(plan['updates_per_arm']):
    schedule.append({'positive': [positive_order[(update * 8 + j) % len(positive)] for j in range(8)],
                     'negative': [negative_order[(update * 8 + j) % len(negative)] for j in range(8)],
                     'targeted': [targeted_order[(update * 4 + j) % len(targeted)] for j in range(4)]})
schedule_ref = write(OUT / 'training-schedule.json', {'seed': plan['batch_order_seed'], 'schedule': schedule})
results = {}
started = time.monotonic()
for arm in plan['arms']:
    directory = OUT / 'runs' / arm
    assert not directory.exists()
    model, optimizer, steps = head.restore_grouped_span_checkpoint(parent)
    assert steps == 480 and head.save_grouped_span_checkpoint(model, optimizer, steps=steps) == parent
    optimizer.param_groups[0]['lr'] = plan['learning_rate']
    summaries, losses = [], []
    selected = None
    presentations = Counter()
    for update in range(plan['updates_per_arm'] + 1):
        if update in plan['selection_updates']:
            measured = evaluate(model, selection, split='fresh_selection')
            summary = measured['mixed_summary']
            evaluation_ref = write(directory / ('selection-' + str(update) + '.json'), measured)
            checkpoint = head.save_grouped_span_checkpoint(model, optimizer, steps=480 + update)
            checkpoint_ref = write(directory / ('checkpoint-' + str(update) + '.json'), checkpoint)
            # Restore now, before considering this checkpoint for selection.
            restored, restored_optimizer, restored_steps = head.restore_grouped_span_checkpoint(checkpoint)
            assert head.save_grouped_span_checkpoint(restored, restored_optimizer, steps=restored_steps) == checkpoint
            candidate = {'additional_updates': update, 'optimizer_steps': 480 + update,
                         'summary': summary, 'checkpoint': checkpoint_ref, 'evaluation': evaluation_ref}
            summaries.append(candidate)
            if selected is None or score(summary, update) > score(selected['summary'], selected['additional_updates']):
                selected = candidate
            print(json.dumps({'arm': arm, 'update': update, 'selection': summary,
                              'elapsed_seconds': round(time.monotonic() - started, 2)}), flush=True)
        if update == plan['updates_per_arm']:
            break
        item = schedule[update]
        rows = [positive[i] for i in item['positive']]
        if arm == 'original_negatives':
            rows += [negative[i] for i in item['negative']]
        else:
            rows += [negative[i] for i in item['negative'][:4]] + [targeted[i] for i in item['targeted']]
        for row in rows:
            presentations['positive' if row['supported'] else row['negative_category']] += 1
        examples = [measurement.example(row) for row in rows]
        losses.append(head.train_grouped_span_step(model, optimizer, examples))
        assert head.producer_pins() == producer_pins
        if (update + 1) % 50 == 0:
            print(json.dumps({'arm': arm, 'completed_updates': update + 1,
                              'last_loss': losses[-1]['loss']}), flush=True)
    assert sum(presentations.values()) == 3200 and presentations['positive'] == 1600
    results[arm] = {'selected': selected, 'selection_checkpoints': summaries,
                   'completed_updates': 200, 'row_presentations': dict(presentations),
                   'optimizer_parent_steps': 480, 'schedule': schedule_ref}
    write(directory / 'losses.json', {'losses': losses})
    write(directory / 'selected.json', results[arm])

barrier = write(OUT / 'both-selections-durable-before-final.json', {
    'schema': 'matched-boundary-final-reference-barrier/v1', 'runner': runner_pin,
    'plan': pin(plan_path), 'producer_pins': producer_pins, 'selections': results,
    'final_reference': plan['sealed_final_reference'], 'final_reference_parsed': False,
    'legal_gold': False, 'threshold': 0.5})
final_rows = load(plan['sealed_final_reference'])['rows']
assert len(final_rows) == 128
assert {r['input']['source_text'] for r in final_rows}.isdisjoint(selection_sources)
assert {r['input']['source_text'] for r in final_rows}.isdisjoint({r['input']['source_text'] for r in positive + negative + targeted})
parent_model, _, _ = head.restore_grouped_span_checkpoint(parent)
measured_parent = evaluate(parent_model, final_rows, 'fresh_final_parent_comparison')
write(OUT / 'parent-fresh-final.json', measured_parent)
for arm in plan['arms']:
    chosen = load(results[arm]['selected']['checkpoint'])
    model, optimizer, steps = head.restore_grouped_span_checkpoint(chosen)
    measured = evaluate(model, final_rows, 'fresh_final_once_after_both_selections')
    measured['selection_barrier'] = barrier
    measured['selected_checkpoint'] = results[arm]['selected']['checkpoint']
    measured['fresh_final_used_for_selection_or_fitting'] = False
    measured['paired_parent_summary'] = measured_parent['mixed_summary']
    write(OUT / 'runs' / arm / 'fresh-final.json', measured)
    assert head.save_grouped_span_checkpoint(model, optimizer, steps=steps) == chosen
    results[arm]['fresh_final'] = measured['mixed_summary']
    results[arm]['negative_categories'] = measured['negative_categories']
    results[arm]['fresh_final_source_spans'] = {k: v for k, v in measured['source_span_fidelity'].items() if k != 'cases'}
    print(json.dumps({'arm': arm, 'fresh_final': measured['mixed_summary']}), flush=True)
assert pin(parent_path)['sha256'] == plan['parent_checkpoint']['sha256']
assert head.producer_pins() == producer_pins and pin(Path(__file__)) == runner_pin
assert not torch.cuda.is_initialized()
write(OUT / 'training-results.json', {'schema': 'matched-grouped-boundary-continuation-results/v1',
    'status': 'completed', 'plan': pin(plan_path), 'runner': runner_pin, 'producer_pins': producer_pins,
    'barrier': barrier, 'arms': results, 'parent_fresh_final': measured_parent['mixed_summary'],
    'actual_optimizer_updates': 400, 'additional_row_presentations': 6400,
    'fresh_final_reference_used_for_tuning': False, 'support_threshold': 0.5,
    'architecture_or_decoder_changed': False, 'latent_conditioned': False,
    'legal_gold': False, 'source_semantics_verified': False, 'proof_ready': False,
    'existing_default_weights_changed': False, 'wall_seconds': time.monotonic() - started,
    'device': 'cpu', 'threads': 2, 'cuda_initialized': False})
print(json.dumps({'status': 'completed', 'results': str(OUT / 'training-results.json')}), flush=True)
