"""Equal-update support/action residual comparison; frozen class readout.

The two arms have different capacities. Authored targets supervise TRAIN only;
the fresh final and both exposed retention panels are joined after durable
selection and source-only predictions. No legal or proof admission runs.
"""
from contextlib import ExitStack
from hashlib import sha256
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import time
from unittest.mock import patch

import torch
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_span_decoder as span
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_trigger_readout as parent_head
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_support_action as head
from ipfs_datasets_py.logic.deontic.utils import deontic_parser

SCORER = Path('/home/barberb/lift_coding/artifacts/legal-trigger-readout-20261007-01/run_trigger_experiment.py')
SCORER_SHA = '8db24c4c0e39ebb106a72031fa53aa9f153fed94f1ddaf1b58ba7ef9ad093f00'


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def mkdir_durable(path):
    missing, current = [], path
    while not current.exists():
        missing.append(current)
        current = current.parent
    path.mkdir(parents=True, exist_ok=True)
    for created in reversed(missing):
        sync_directory(created.parent)


def write(path, value):
    mkdir_durable(path.parent)
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)
    return pin(path)


def load(reference):
    assert pin(reference['path']) == reference, 'input artifact differs'
    return json.loads(Path(reference['path']).read_text())


def denied(*args, **kwargs):
    raise AssertionError('inference reached a TRAIN label, optimizer, or semantic parser')


def frozen_signature(result):
    raw = result['raw_prediction']
    assert raw is not None
    return dict(modality_logits=result['modality_logits'], modality=raw['modality'],
        presence=raw['presence'], nonaction_token_spans={
            facet: raw['token_spans'][facet] for facet in span.FACETS if facet != 'action'})


def initial_core(result):
    return {key: result[key] for key in ('status', 'prediction', 'proposal', 'blockers',
        'raw_prediction', 'modality_logits', 'support_probability', 'support_threshold')}


def collect(model, inputs, path, *, parent=False):
    records = []
    with ExitStack() as stack:
        for owner, names in ((head, ('train_support_action_step', 'SupportActionExample')),
            (parent_head, ('train_trigger_readout_step', 'TriggerReadoutExample')),
            (span, ('_labels', 'train_scope_span_step', 'ScopeSpanExample')),
            (deontic_parser, ('extract_normative_elements', 'analyze_normative_sentence', 'classify_modal'))):
            for name in names:
                stack.enter_context(patch.object(owner, name, denied))
        for name in ('_action_labels', '_labels'):
            if hasattr(head, name):
                stack.enter_context(patch.object(head, name, denied))
        for row in inputs:
            assert set(row) == {'id', 'source_group', 'template', 'condition_attachment', 'source_text', 'source_sha256'}
            assert sha256(row['source_text'].encode()).hexdigest() == row['source_sha256']
            owner = parent_head if parent else head
            predictor = owner.predict_trigger_readout if parent else owner.predict_support_action
            result = predictor(model, row['source_text'], row['condition_attachment'],
                expected_source_sha256=row['source_sha256'])
            assert result['model_executed'] and result['formal_output'] is None
            assert not any(result[key] for key in ('source_semantics_verified', 'proof_ready',
                'proof_authority', 'qualified', 'accepted', 'formalized', 'target_access'))
            if result['proposal']:
                assert not any(result['proposal']['masks'].values())
            logits = result['modality_logits']
            assert len(logits) == 3 and all(type(v) is float and math.isfinite(v) for v in logits)
            records.append(dict(id=row['id'], source_group=row['source_group'],
                source_sha256=row['source_sha256'], class_logits=logits, prediction=result))
    reference = write(path, dict(schema='support-action-source-only-panel/v1', rows=records,
        references_accessed_by_inference=False))
    return records, reference


def assert_frozen_panels(left, right):
    assert len(left) == len(right)
    for a, b in zip(left, right, strict=True):
        assert a['id'] == b['id']
        assert frozen_signature(a['prediction']) == frozen_signature(b['prediction']), a['id']
    return len(left)


def score_components(base_score, records, references, inputs):
    out = base_score(records, references, inputs)
    refs, sources = ({row['id']: row for row in values} for values in (references, inputs))
    counts = dict(true_positive=0, false_negative=0, false_positive=0, true_negative=0)
    support_ce, ceiling = [], []
    for template in out['positive_templates'].values():
        template['raw_action_exact'] = 0
    for row in records:
        ref, source, result = refs[row['id']], sources[row['id']], row['prediction']
        probability = result['support_probability']
        assert type(probability) is float and math.isfinite(probability) and 0 <= probability <= 1
        assert result['support_threshold'] == .5
        positive = probability >= .5
        key = ('true_positive' if positive else 'false_negative') if ref['supported'] else ('false_positive' if positive else 'true_negative')
        counts[key] += 1
        clipped = max(1e-12, min(1 - 1e-12, probability))
        support_ce.append(-math.log(clipped) if ref['supported'] else -math.log1p(-clipped))
        if not ref['supported']:
            continue
        gold, raw, tokens = ref['prediction'], result['raw_prediction'], span.tokenize_source(source['source_text'])
        exact_spans = {}
        for facet in span.FACETS:
            if facet in span.OPTIONAL and not raw['presence'][facet]:
                predicted = None
            else:
                left, right = raw['token_spans'][facet]
                predicted = [tokens[left].start, tokens[right].end] if 0 <= left <= right < len(tokens) else 'invalid'
            exact_spans[facet] = predicted == gold['spans'][facet]
        out['positive_templates'][source['template']]['raw_action_exact'] += int(exact_spans['action'])
        if raw['modality'] == gold['modality'] and all(exact_spans[facet] for facet in span.FACETS if facet != 'action'):
            ceiling.append(row['id'])
    out.update(raw_support_confusion=counts,
        raw_support_accuracy=(counts['true_positive'] + counts['true_negative']) / len(records),
        support_probability_BCE=sum(support_ce) / len(support_ce), support_BCE_probability_clip=[1e-12, 1 - 1e-12],
        fixed_class_nonaction_whole_ceiling_count=len(ceiling), fixed_class_nonaction_whole_ceiling_ids=ceiling)
    return out


def transitions(baseline, candidate, references):
    refs = {r['id']: r for r in references}
    out = {key: [] for key in ('whole_retained', 'whole_lost', 'whole_gained',
        'negative_emission_retained', 'negative_emission_removed', 'negative_emission_new')}
    for a, b in zip(baseline, candidate, strict=True):
        assert a['id'] == b['id']
        ref = refs[a['id']]
        if ref['supported']:
            exact = lambda row: row['prediction']['status'] == 'predicted' and row['prediction']['prediction'] == ref['prediction']
            before, after = exact(a), exact(b)
            if before and after:
                out['whole_retained'].append(a['id'])
            elif before:
                out['whole_lost'].append(a['id'])
            elif after:
                out['whole_gained'].append(a['id'])
        else:
            before, after = (row['prediction']['status'] == 'predicted' for row in (a, b))
            if before and after:
                out['negative_emission_retained'].append(a['id'])
            elif before:
                out['negative_emission_removed'].append(a['id'])
            elif after:
                out['negative_emission_new'].append(a['id'])
    return {'counts': {key: len(ids) for key, ids in out.items()}, 'case_ids': out}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    assert not torch.cuda.is_initialized() and torch.get_default_device().type == 'cpu'
    plan = json.loads(args.plan.read_text())
    assert plan['runner'] == pin(Path(__file__)) and plan['producer_pins'] == head.producer_pins()
    assert plan['arms'] == ['linear', 'mlp'] and plan['updates_per_arm'] == 240
    assert plan['batch_size'] == 16 and plan['seed'] == 24604
    assert set(plan['retention']) == {'earlier_scope', 'earlier_trigger'}
    assert pin(SCORER)['sha256'] == SCORER_SHA and plan['scorer'] == pin(SCORER)
    spec = importlib.util.spec_from_file_location('_support_action_pinned_score_owner', SCORER)
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    score = lambda records, references, inputs: score_components(scorer.score, records, references, inputs)
    assert plan['selection_policy'] == pin(Path(__file__).with_name('selection_policy.py'))
    policy_spec = importlib.util.spec_from_file_location('_support_action_selection_policy', plan['selection_policy']['path'])
    policy = importlib.util.module_from_spec(policy_spec)
    policy_spec.loader.exec_module(policy)
    output = args.output.resolve()
    assert not output.exists()
    mkdir_durable(output)
    train_inputs, train_refs = (load(plan[key]['train']) for key in ('inputs', 'references'))
    sources, refs = ({r['id']: r for r in values} for values in (train_inputs, train_refs))
    assert len(sources) == len(refs) == 1024 and set(sources) == set(refs)
    examples = {key: head.SupportActionExample(sources[key]['source_text'], ref['supported'],
        ref['prediction']['spans']['action'] if ref['supported'] else None) for key, ref in refs.items()}
    assert pin(plan['builder']['path']) == plan['builder']
    spec = importlib.util.spec_from_file_location('_support_action_schedule', plan['builder']['path'])
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    schedule = builder.training_batches(train_inputs, train_refs, seed=24604, updates=240)
    assert sha256(canonical(schedule)).hexdigest() == plan['schedule_canonical_sha256']
    assert len(schedule) == 240 and all(len(batch) == 16 and sum(refs[key]['supported'] for key in batch) == 8 for batch in schedule)
    write(output/'training-schedule.json', schedule)
    selection_inputs, selection_refs = load(plan['inputs']['selection']), load(plan['references']['selection'])
    for reference in [plan['references']['final'], *[c['references'] for c in plan['retention'].values()]]:
        assert pin(reference['path']) == reference  # Hash/read only, never JSON-parse before the barrier.
    assert pin(plan['parent_checkpoint']['path']) == plan['parent_checkpoint']
    parent_raw = Path(plan['parent_checkpoint']['path']).read_bytes()
    parent_json = json.loads(parent_raw)
    parent, parent_optimizer, parent_steps = parent_head.restore_trigger_readout_checkpoint(parent_json)
    assert parent_steps == 240 and parent.config.mode == 'predicted_trigger'
    models = {kind: head.FrozenSupportAction(parent_raw,
        expected_parent_sha256=plan['parent_checkpoint']['sha256'],
        config=head.SupportActionConfig(seed=24604, head_kind=kind, hidden=32)) for kind in plan['arms']}
    first_inputs = [sources[key] for key in schedule[0]]
    parent_initial, parent_initial_ref = collect(parent, first_inputs, output/'initial-parent-predictions.json', parent=True)
    initial = {}
    for kind, model in models.items():
        records, record_ref = collect(model, first_inputs, output/f'initial-{kind}-predictions.json')
        assert_frozen_panels(records, parent_initial)
        assert all(initial_core(a['prediction']) == initial_core(b['prediction'])
            for a, b in zip(records, parent_initial, strict=True))
        initial[kind] = record_ref
    counts = {kind: dict(total=sum(p.numel() for p in model.parameters()),
        trainable=sum(p.numel() for p in model.parameters() if p.requires_grad)) for kind, model in models.items()}
    assert counts['linear']['trainable'] == 195 and counts['mlp']['trainable'] == 6339
    write(output/'initialization.json', dict(parameter_counts=counts, capacity_matched=False,
        data_and_update_budget_matched=True, initial_parent_full_core_and_logits_parity=16,
        parent=parent_initial_ref, candidates=initial, parent_steps=parent_steps,
        new_Adam_fresh=True, parent_Adam_continued=False))
    parent_selection, parent_selection_ref = collect(parent, selection_inputs,
        output/'parent-selection-predictions.json', parent=True)
    baseline_selection = score(parent_selection, selection_refs, selection_inputs)
    assert policy.eligible(baseline_selection, baseline_selection)
    write(output/'selection-baseline-floors.json', dict(summary=baseline_selection,
        eligibility_rule=plan['selection_eligibility'], selection_policy=pin(plan['selection_policy']['path'])))
    parent_train, parent_train_ref = collect(parent, train_inputs,
        output/'parent-TRAIN-predictions.json', parent=True)
    arms = {}
    frozen_selection_rows = frozen_train_rows = 0
    for kind, model in models.items():
        directory = output/kind
        optimizer = head.make_support_action_optimizer(model, learning_rate=.003, weight_decay=0)
        chosen, candidates, losses = None, [], []
        for step in range(241):
            if step in (0, 120, 240):
                checkpoint = write(directory/f'checkpoint-{step}.json',
                    head.save_support_action_checkpoint(model, optimizer, steps=step, action_steps=step))
                records, record_ref = collect(model, selection_inputs, directory/f'selection-predictions-{step}.json')
                frozen_selection_rows += assert_frozen_panels(records, parent_selection)
                summary = score(records, selection_refs, selection_inputs)
                candidate = dict(completed_updates=step, summary=summary, checkpoint=checkpoint, predictions=record_ref)
                if step == 0:
                    assert summary == baseline_selection
                candidate['eligible'] = policy.eligible(summary, baseline_selection)
                candidates.append(candidate)
                chosen = policy.select(candidates, baseline_selection)
            if step == 240:
                break
            update = head.train_support_action_step(model, optimizer, [examples[key] for key in schedule[step]], gradient_clip=5)
            assert update['optimizer_step_executed'] is True and update['action_optimizer_step_executed'] is True
            assert update['supported_examples'] == 8 and update['unsupported_examples'] == 8
            assert update['encoded_examples'] == 16
            losses.append(dict(update=step + 1, **update))
        train_panel, train_panel_ref = collect(model, train_inputs, directory/'last-TRAIN-predictions.json')
        frozen_train_rows += assert_frozen_panels(train_panel, parent_train)
        write(directory/'losses.json', losses)
        write(directory/'selected.json', chosen)
        arms[kind] = dict(selected=chosen, selection_candidates=candidates, completed_support_updates=240,
            completed_action_updates=240, training_input_records=3840, encoded_optimizer_source_presentations=3840,
            positive_action_presentations=1920, negative_support_presentations=1920, negative_records_ignored=0,
            last_TRAIN=score(train_panel, train_refs, train_inputs), last_TRAIN_predictions=train_panel_ref)
    barrier = write(output/'both-selected-before-final-and-retention.json', dict(
        schema='support-action-final-reference-barrier/v1', arms=arms, references_parsed=False,
        actual_optimizer_calls=480, support_head_updates=480, action_head_updates=480,
        head_updates_share_the_same_optimizer_calls=True, runner=pin(Path(__file__)), plan=pin(args.plan)))
    cohorts = {'fresh_final': dict(inputs=plan['inputs']['final'], references=plan['references']['final']), **plan['retention']}
    panels, panel_refs = {}, {}
    for kind, arm in arms.items():
        checkpoint = load(arm['selected']['checkpoint'])
        model, optimizer, steps, action_steps = head.restore_support_action_checkpoint(checkpoint)
        assert head.save_support_action_checkpoint(model, optimizer, steps=steps, action_steps=action_steps) == checkpoint
        for name, cohort in cohorts.items():
            inputs = load(cohort['inputs'])
            panels[(kind, name)], panel_refs[(kind, name)] = collect(model, inputs, output/kind/f'{name}-predictions.json')
        assert head.save_support_action_checkpoint(model, optimizer, steps=steps, action_steps=action_steps) == checkpoint
        arm['strict_model_full_Adam_resume_exact'] = True
    for name, cohort in cohorts.items():
        panels[('parent', name)], panel_refs[('parent', name)] = collect(parent, load(cohort['inputs']),
            output/f'parent-{name}-predictions.json', parent=True)
        for kind in plan['arms']:
            assert_frozen_panels(panels[(kind, name)], panels[('parent', name)])
    predictions_barrier = write(output/'all-final-and-retention-predictions-before-reference-joins.json', dict(
        schema='support-action-output-barrier/v1', panels={f'{kind}/{name}': ref for (kind, name), ref in panel_refs.items()},
        evaluation_references_parsed=False))
    scores, paired = {}, {}
    for name, cohort in cohorts.items():
        inputs, references = load(cohort['inputs']), load(cohort['references'])
        scores[name] = {kind: score(panels[(kind, name)], references, inputs) for kind in ['parent', *plan['arms']]}
        paired[name] = {kind: transitions(panels[('parent', name)], panels[(kind, name)], references) for kind in plan['arms']}
        for kind in ['parent', *plan['arms']]:
            if kind != 'parent':
                arms[kind][name] = scores[name][kind]
        if name != 'fresh_final':
            archived = load(cohort['archived_parent_predictions'])['rows']
            assert len(archived) == len(panels[('parent', name)])
            assert all(a['id'] == b['id'] and a['prediction'] == b['prediction']
                for a, b in zip(archived, panels[('parent', name)], strict=True))
    assert parent_head.save_trigger_readout_checkpoint(parent, parent_optimizer, steps=parent_steps) == parent_json
    result = dict(schema='support-action-training-results/v1', status='completed', arms=arms,
        scores=scores, paired_transitions=paired, actual_optimizer_updates=480,
        support_head_updates=480, action_head_updates=480, head_updates_share_the_same_optimizer_calls=True,
        training_input_records=7680, encoded_optimizer_source_presentations=7680,
        positive_action_presentations=3840, negative_support_presentations=3840, negative_records_ignored=0,
        frozen_class_and_nonaction_selection_rows=frozen_selection_rows,
        frozen_class_and_nonaction_TRAIN_rows=frozen_train_rows,
        frozen_class_and_nonaction_postfit_rows=768, parent_full_model_and_Adam_unchanged=True,
        capacity_matched=False, data_and_update_budget_matched=True, source_only=True, latent_conditioned=False,
        class_readout_trained=False, caller_attachment_learned=False, legal_gold=False, semantic_admission=False,
        Lake_executed=False, existing_weights_changed=False, final_references_used_for_training_or_selection=False,
        retention_references_used_for_training_or_selection=False, fresh_final_now_exposed=True,
        plan=pin(args.plan), runner=pin(Path(__file__)), scorer=pin(SCORER), producer_pins=head.producer_pins(),
        selection_barrier=barrier, predictions_barrier=predictions_barrier,
        device='cpu', threads=2, cuda_initialized=torch.cuda.is_initialized(), wall_seconds=time.monotonic() - started)
    reference = write(output/'training-results.json', result)
    write(output/'summary.json', dict(schema='support-action-pilot-completion/v1', status='completed',
        training_results=reference, actual_optimizer_updates=480, scores=scores,
        paired_transition_counts={name: {kind: value['counts'] for kind, value in cohort.items()} for name, cohort in paired.items()},
        proof_ready=False, source_semantics_verified=False, model_defaults_changed=False))
    print(json.dumps(dict(status='completed', updates=480, scores=scores,
        paired_transition_counts={name: {kind: value['counts'] for kind, value in cohort.items()} for name, cohort in paired.items()})))


if __name__ == '__main__':
    main()
