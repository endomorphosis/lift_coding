"""Read-only saved-artifact checks; does not replay or authenticate neural predictions."""

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
STAGE = CAMPAIGN / 'typed-anchor-decoder-recovery-01'
OUTPUT = CAMPAIGN / 'typed-anchor-decoder-validation-01'
AUTHORITY = ('qualified', 'source_fidelity_established', 'proof_authority', 'accepted',
             'independent_semantic_review_completed')


def raw(value, *, ascii=False):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=ascii,
                      allow_nan=False).encode('utf-8')


def digest(value, *, ascii=False):
    return hashlib.sha256(raw(value, ascii=ascii)).hexdigest()


def bind(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def load(path, *, sealed=False, ascii=False):
    value = json.loads(Path(path).read_bytes())
    if sealed:
        assert value['content_sha256'] == digest({key: item for key, item in value.items()
                                                 if key != 'content_sha256'}, ascii=ascii)
    return value


def references(value):
    if isinstance(value, dict):
        if {'path', 'sha256'} <= value.keys():
            yield value
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def false_authority(value):
    for field in AUTHORITY:
        if field in value:
            assert value[field] is False, field


def coordinates(anchors):
    return [{key: anchor[key] for key in ('field_path', 'start', 'end')} for anchor in anchors]


def main(expected_sha):
    assert not OUTPUT.exists(), 'fresh validation generation required'
    checked = {}

    def verify(reference):
        observed = bind(reference['path'])
        assert observed['sha256'] == reference['sha256'], reference['path']
        assert 'bytes' not in reference or observed['bytes'] == reference['bytes']
        checked[observed['path']] = observed

    report_binding = bind(STAGE / 'report.json')
    assert report_binding['sha256'] == expected_sha
    report = load(report_binding['path'], sealed=True)
    plan = load(report['plan_binding']['path'], sealed=True)
    diagnostics = load(report['posthoc_weak_diagnostics_binding']['path'], sealed=True)
    for payload in (report, plan):
        for reference in references(payload):
            verify(reference)
    verify(report_binding)
    prior = load(CAMPAIGN / 'canonical-codec-validation-01/validation.json', sealed=True)
    audit_binding = bind(CAMPAIGN / 'typed-anchor-independent-audit-01/audit.json')
    assert audit_binding['sha256'] == '2cc77242ef964cdc28ec4cfdfa9fdf4a8d386d1a35e343093f2591d96e6737e2'
    audit = load(audit_binding['path'], sealed=True)
    assert audit['status'] == 'passed' and audit['checked_unique_file_count'] == 440
    assert audit['audit_model_execution'] is audit['audit_training_execution'] is False
    for reference in references(audit):
        verify(reference)
    verify(audit_binding)
    assert report['source_bindings'] == prior['checked_file_bindings']
    assert len(report['source_bindings']) == prior['checked_file_count'] == 336
    assert report['extra_prior_bindings'] == prior['new_implementation_test_bindings']
    verify(prior['runner_binding'])
    for reference in prior['documentation_bindings']:
        if Path(reference['path']).name == 'canonical-codec-report.md':
            verify(reference)
    requests = load(report['inference_requests_binding']['path'], sealed=True)['rows']
    inputs = load(CAMPAIGN / 'canonical-codec-01/target_free_inputs.json', sealed=True)['rows']
    assert requests == [{field: row[field] for field in ('id', 'source_text', 'context_text',
                                                        'requires_context_resolution')} for row in inputs]
    assert len(requests) == len({row['id'] for row in requests}) == 34
    train = load(CAMPAIGN / 'canonical-codec-01/train_weak_supervision.json', sealed=True)
    dev = load(CAMPAIGN / 'canonical-codec-01/development_transport_diagnostics.json', sealed=True)
    outcomes = load(CAMPAIGN / 'canonical-codec-01/all_request_outcomes.json', sealed=True)
    by_id = {row['id']: row for row in outcomes['rows']}
    request_by_id = {row['id']: row for row in requests}
    weak = {row['id']: row['proposal'] for row in train['rows'] + dev['rows']}
    assert len(train['rows']) == 16 and len(dev['rows']) == 6 and dev['positive_denominator'] == 8
    assert {row['group_id'] for row in train['rows']}.isdisjoint({row['group_id'] for row in dev['rows']})
    groups = Counter(row['group_id'] for row in train['rows'])
    assert len(groups) == 4 and set(groups.values()) == {4}
    for row in outcomes['rows']:
        assert row['review_status'] == 'pending'
        assert row['masks'] == {field: int(field == 'weak_decoder_fit' and row['split'] == 'train')
                               for field in row['masks']}
    typed_examples = [{'id': row['id'], 'source_text': request_by_id[row['id']]['source_text'],
                       'canonical_ir': row['proposal']['canonical_ir']} for row in train['rows']]
    anchor_examples = [{'id': row['id'], 'source_text': request_by_id[row['id']]['source_text'],
                        'proposal': row['proposal']} for row in train['rows']]
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir import canonical_byte_codec as byte
    from ipfs_datasets_py.logic.legal_ir import canonical_decoder_preflight as preflight
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_formula_codec as typed
    fitted_codec = typed.fit_codec(typed_examples)
    expected_positions = []
    for position, request in enumerate(requests):
        warning = preflight.analyze_decoder_source(request['source_text'], context_text=request['context_text'],
            requires_context_resolution=request['requires_context_resolution'])
        if warning['outcome'] == 'unassessed':
            try:
                typed.encode_source(fitted_codec, request['source_text'])
            except typed.CodecError:
                continue
            expected_positions.append(position)
    assert len(expected_positions) == 22
    generation_rows = proposals = proposal_anchors = checkpoints = 0
    observed_diagnostics = []
    development_facet_mismatches, span_counterexamples = {}, []
    assert [run['seed'] for run in report['runs']] == [1729, 1730, 1731]
    assert plan['source_fit_calls'] == 0 and plan['recovery_anchor_seed'] == 1731
    assert report['training_plan_complete'] is True
    assert report['optimizer_steps'] == {'source': 0, 'anchors': 200, 'outside_fit': 0}
    assert report['completed_checkpoint_lineage_optimizer_steps'] == 1200
    assert report['partial_stage_durable_optimizer_steps'] == {'source': 600, 'anchors': 400}
    assert report['interrupted_unsaved_optimizer_step_bounds'] == {'minimum': 0, 'maximum': 200}
    assert report['total_optimizer_update_bounds_including_canary'] == {'minimum': 1210, 'maximum': 1410}
    assert report['tuning_rows'] == report['independent_reviews_completed'] == 0
    assert report['new_encoder_calls'] == report['prover_calls'] == 0
    assert report['external_embedding_conditioning'] is report['prepared_group_loss_weights_consumed'] is False
    assert report['development_used_for_fit_or_selection'] is report['checkpoint_promoted'] is False
    assert report['rng_state_unchanged'] is report['actual_numeric_generation_executed'] is True
    for run in report['runs']:
        seed = run['seed']
        states = {role: load(run[role + '_checkpoint_binding']['path'])
                  for role in ('source_initial', 'source_final', 'anchor_initial', 'anchor_final')}
        checkpoints += len(states)
        for role, state in states.items():
            assert state['config']['seed'] == seed and state['training_pair_count'] == 16
            assert state['config']['device'] == 'cpu' and state['config']['dtype'] == 'float32'
            assert state['progress'] == ({'epochs_completed': 0, 'row_cursor': 0, 'optimizer_steps': 0}
                                         if role.endswith('initial') else
                                         {'epochs_completed': 100, 'row_cursor': 0, 'optimizer_steps': 200})
            assert all(type(value) in (int, float) and math.isfinite(value) for tensor in state['model_state'].values()
                       for value in flatten(tensor))
            if role.startswith('source'):
                assert state['training_manifest_sha256'] == digest(typed_examples, ascii=True)
                assert state['codec'] == fitted_codec and state['tuning_pair_count'] == 0
                assert len(state['model_state']) == 12
            else:
                assert state['training_manifest_sha256'] == digest(anchor_examples, ascii=True)
                assert state['training_anchor_count'] == 124 and len(state['model_state']) == 8
                assert state['source_checkpoint_sha256'] == digest(states['source_final'], ascii=True)
                for name, tensor in state['model_state'].items():
                    expected = ([64, 32] if name.endswith('query.weight') else [64]
                                if name.endswith('query.bias') else [1, 64]
                                if name.endswith('source.weight') else [1])
                    assert shape(tensor) == expected
                moments = state['optimizer_state']['parameters']
                assert set(moments) == (set(state['model_state']) if role.endswith('final') else set())
                for name, moments_for_tensor in moments.items():
                    assert moments_for_tensor['step'] == 200
                    for field in ('exp_avg', 'exp_avg_sq'):
                        assert shape(moments_for_tensor[field]) == shape(state['model_state'][name])
                        assert all(type(value) in (int, float) and math.isfinite(value)
                                   and (field != 'exp_avg_sq' or value >= 0)
                                   for value in flatten(moments_for_tensor[field]))
            if role.endswith('final'):
                assert state['model_state'] != states[role.replace('final', 'initial')]['model_state']
        assert states['source_final']['parent_checkpoint_sha256'] == digest(states['source_initial'], ascii=True)
        assert states['anchor_final']['parent_anchor_checkpoint_sha256'] == digest(states['anchor_initial'], ascii=True)
        source_final = load(run['source_generation_bindings']['source_final']['path'], sealed=True)
        roles = {**run['source_generation_bindings'], **run['pipeline_generation_bindings']}
        for role, reference in roles.items():
            pipeline = role.startswith('source_final_anchor')
            result = load(reference['path'], sealed=True, ascii=pipeline)
            false_authority(result)
            assert len(result['rows']) == 34 and result['target_access'] is False
            assert result['submitted_positions'] == expected_positions
            assert result['teacher_forcing'] is result['training_executed'] is False
            backend = result['parent_backend'] if pipeline else result['backend_result']
            expected_source = states['source_final' if pipeline or role == 'source_final' else 'source_initial']
            assert backend['checkpoint_sha256'] == digest(expected_source, ascii=True)
            if pipeline:
                assert result['parent_backend'] == source_final['backend_result']
                assert result['outcome_counts'] == {key: sum(row['outcome'] == key for row in result['rows'])
                                                   for key in result['outcome_counts']}
            for position, (row, request) in enumerate(zip(result['rows'], requests, strict=True)):
                assert row['id'] == request['id'] and row['position'] == position
                assert row['source_sha256'] == hashlib.sha256(request['source_text'].encode()).hexdigest()
                assert row['context_sha256'] == hashlib.sha256(request['context_text'].encode()).hexdigest()
                assert row['preflight'] == preflight.analyze_decoder_source(request['source_text'],
                    context_text=request['context_text'], requires_context_resolution=request['requires_context_resolution'])
                false_authority(row)
                parent = row.get('parent_row') if pipeline else row.get('decoder_row')
                if position in expected_positions:
                    assert parent == backend['rows'][expected_positions.index(position)]
                else:
                    assert parent is None and row.get('proposal') is None
                    expected_outcome = ('clarification_required' if row['preflight']['outcome'] == 'clarification_required'
                                        else 'source_blocked' if row['preflight']['outcome'] != 'unassessed'
                                        else 'source_encoding_unavailable')
                    assert row['outcome'] == expected_outcome
                if parent:
                    assert parent['source_sha256'] == row['source_sha256']
                    assert all(parent[field] is False for field in ('target_access', 'teacher_forcing',
                        'training_executed', 'qualified', 'proof_authority', 'semantic_correctness_verified',
                        'family_syntax_checked'))
                if parent and parent['status'] == 'decoded':
                    assert typed.decode_target(fitted_codec, parent['generated_token_ids']) == parent['canonical_ir']
                proposal = row.get('proposal')
                if proposal is not None:
                    assert byte.validate_proposal(proposal, request['source_text']) == proposal
                    assert proposal['canonical_ir'] == parent['canonical_ir']
                    assert byte.decode_proposal(byte.encode_proposal(proposal, request['source_text']),
                                                request['source_text']) == proposal
                    proposals += 1
                    proposal_anchors += len(proposal['anchors'])
                generation_rows += 1
            partition_counts = {}
            for split, denominator in (('train', 16), ('validation', 8)):
                selected = [row for row in result['rows'] if by_id[row['id']]['split'] == split
                            and by_id[row['id']]['row_kind'] == 'positive']
                assert len(selected) == denominator
                count = Counter()
                facet_mismatches = Counter()
                for row in selected:
                    if row['id'] not in weak:
                        continue
                    count['compared'] += 1
                    reference_proposal = weak[row['id']]
                    candidate = row.get('proposal')
                    parent = row.get('parent_row') if pipeline else row.get('decoder_row')
                    canonical = candidate['canonical_ir'] if candidate else parent.get('canonical_ir') if parent else None
                    count['canonical'] += canonical == reference_proposal['canonical_ir']
                    count['full'] += candidate is not None and candidate == reference_proposal
                    count['anchors'] += candidate is not None and candidate['anchors'] == reference_proposal['anchors']
                    count['coordinates'] += candidate is not None and coordinates(candidate['anchors']) == coordinates(reference_proposal['anchors'])
                    if split == 'validation' and role == 'source_final_anchor_final' and canonical is not None:
                        reference_rule, predicted_rule = reference_proposal['canonical_ir']['rules'][0], canonical['rules'][0]
                        differing = [field for field in reference_rule if reference_rule[field] != predicted_rule[field]]
                        facet_mismatches.update(differing)
                        if candidate is not None and coordinates(candidate['anchors']) == coordinates(reference_proposal['anchors']) and differing:
                            span_counterexamples.append(dict(seed=seed, id=row['id'], source_sha256=row['source_sha256'],
                                differing_weak_canonical_facets=differing, generated_rule=predicted_rule,
                                weak_reference_rule=reference_rule, independent_semantic_review_completed=False))
                if split == 'validation' and role == 'source_final_anchor_final':
                    development_facet_mismatches[str(seed)] = dict(facet_mismatches)
                partition_counts[split] = dict(positive_denominator=denominator, weak_reference_available=count['compared'],
                    weak_canonical_exact_count=count['canonical'], weak_full_proposal_exact_count=count['full'],
                    weak_complete_anchor_exact_count=count['anchors'], weak_span_coordinate_exact_count=count['coordinates'],
                    independent_fidelity_value=None, reference_role='parser_derived_weak_diagnostic_not_independent_gold')
            observed_diagnostics.append(dict(seed=seed, role=role, row_count=34,
                all_row_outcomes=dict(Counter(row['outcome'] for row in result['rows'])),
                partition_diagnostics=partition_counts, **{field: False for field in AUTHORITY}))
        final = load(run['pipeline_generation_bindings']['source_final_anchor_final']['path'], sealed=True, ascii=True)
        repeated = load(run['private_reload_binding']['path'], sealed=True, ascii=True)
        assert raw(final) == raw(repeated)
        generation_rows += len(repeated['rows'])
        assert run['private_reload_state_checks'] == run['pipeline_state_checks']['source_final_anchor_final']
        assert run['private_models_disjoint_storage'] is run['private_reload_bitwise_json_equal'] is True
        for role, checks in run['pipeline_state_checks'].items():
            head = states['anchor_initial' if role.endswith('initial') else 'anchor_final']
            result = load(run['pipeline_generation_bindings'][role]['path'], sealed=True, ascii=True)
            assert checks['source_model_state_before_sha256'] == checks['source_model_state_after_sha256'] == digest(states['source_final']['model_state'], ascii=True)
            assert checks['anchor_model_state_before_sha256'] == checks['anchor_model_state_after_sha256'] == digest(head['model_state'], ascii=True)
            assert checks['source_checkpoint_before_sha256'] == checks['source_checkpoint_after_sha256'] == digest(states['source_final'], ascii=True)
            assert checks['anchor_checkpoint_before_sha256'] == checks['anchor_checkpoint_after_sha256'] == digest(head, ascii=True)
            assert checks['rng_state_unchanged'] is checks['actual_numeric_generation_executed'] is True
            assert checks['observed_generation_encoder_forwards']
            assert len(checks['observed_parent_batches']) == result['parent_invocation_count']
            assert len(checks['observed_generation_encoder_forwards']) == result['parent_submitted_row_count']
            assert len(checks['observed_anchor_numeric_forwards']) == result['anchor_invocation_count']
            assert len(checks['observed_anchor_feature_encoder_forwards']) == result['anchor_invocation_count']
    assert generation_rows == 510 and checkpoints == 12
    assert {(row['seed'], row['role']): row for row in diagnostics['rows']} == {
        (row['seed'], row['role']): row for row in observed_diagnostics}
    documents = [CAMPAIGN / 'typed-anchor-decoder-report.md',
                 ROOT / 'implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md']
    links = []
    for document in documents:
        for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', document.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            resolved = (document.parent / target.split('#')[0]).resolve()
            assert resolved.is_file() or resolved == OUTPUT / 'validation.json'
            links.append(dict(document=str(document), target=target, resolved=str(resolved)))
    ids = re.findall(r'^\| (AFI-[0-9]+[ab]?) \|', documents[1].read_text(), flags=re.M)
    assert len(ids) == len(set(ids)) == 25
    checkout = ROOT / '.worktrees/alignment-decoder-768-20261003'
    checkout_commit = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    checkout_branch = subprocess.check_output(['git', '-C', str(checkout), 'branch', '--show-current'], text=True).strip()
    assert checkout_commit == '64bc5734dc82db72e955f2e809b770127e9b6cfc'
    assert checkout_branch == 'codex/alignment-decoder-768-20261003'
    restored_bindings = [reference for reference in report['source_bindings']
                         if Path(reference['path']).is_relative_to(checkout)]
    assert len(restored_bindings) == 16
    for reference in restored_bindings:
        relative = Path(reference['path']).relative_to(checkout)
        committed = subprocess.check_output(['git', '-C', str(REPO), 'show', f'{checkout_commit}:{relative}'])
        assert hashlib.sha256(committed).hexdigest() == reference['sha256'] and len(committed) == reference['bytes']
    assert subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain=v1',
                                   '--untracked-files=normal'], text=True).strip() == ''
    assert not {'torch', 'numpy', 'transformers', 'spacy', 'llama_cpp'}.intersection(sys.modules)
    for reference in checked.values():
        assert bind(reference['path']) == reference
    result = dict(schema='alignment-typed-anchor-saved-stage-validation/v1', status='passed_unqualified',
        runner_binding=bind(__file__), report_binding=report_binding,
        checked_file_bindings=list(checked.values()), checked_file_count=len(checked),
        preserved_prior_checked_file_count=336, generation_receipt_rows=510, primary_proposals_validated=proposals,
        primary_proposal_anchors_validated=proposal_anchors, neural_checkpoints=12,
        independently_reviewed_fidelity_rows=0, completed_checkpoint_lineage_optimizer_steps=1200,
        recovery_optimizer_steps=200, interrupted_unsaved_optimizer_step_bounds=dict(minimum=0, maximum=200),
        total_optimizer_update_bounds_including_canary=dict(minimum=1210, maximum=1410),
        development_weak_facet_mismatch_counts=development_facet_mismatches,
        exact_span_wrong_symbol_weak_counterexamples=span_counterexamples,
        disposable_timing_canary_optimizer_steps=10, private_reload_comparisons=3,
        new_implementation_test_bindings=[bind(REPO / relative) for relative in (
            'ipfs_datasets_py/logic/legal_ir/canonical_typed_anchors.py',
            'tests/unit/logic/legal_ir/test_canonical_typed_anchors.py')],
        focused_test_results=dict(passed=537, elapsed_seconds=9.49),
        ruff_results=dict(implementation_test_and_experiment_runner_files=5, status='passed'),
        independent_readonly_audit_binding=audit_binding,
        documentation_bindings=[bind(path) for path in documents], local_link_checks=links,
        work_package_ids=ids, isolated_decoder_checkout_clean=True,
        isolated_decoder_checkout_restoration=dict(observed_missing_utc='2026-10-04T02:29:15Z',
            restored_from_existing_local_branch=True, commit=checkout_commit, branch=checkout_branch,
            verified_source_bindings=restored_bindings, verified_source_file_count=16,
            persistent_git_worktree_lock=True, disappearance_cause_established=False),
        validation_execution_scope='saved_receipts_not_independent_numeric_replay_or_semantic_review',
        model_execution=False, neural_training_execution=False, proof_execution=False,
        complete_dependency_manifest=False, **{field: False for field in AUTHORITY})
    result['content_sha256'] = digest(result)
    OUTPUT.mkdir()
    (OUTPUT / 'validation.json').write_bytes(raw(result) + b'\n')
    print(json.dumps(dict(binding=bind(OUTPUT / 'validation.json'), checked_file_count=len(checked),
                          rows=generation_rows, primary_proposals_validated=proposals), sort_keys=True))


def flatten(value):
    if isinstance(value, list):
        for item in value:
            yield from flatten(item)
    else:
        yield value


def shape(value):
    if not isinstance(value, list):
        return []
    dimensions = shape(value[0]) if value else []
    assert all(shape(item) == dimensions for item in value)
    return [len(value), *dimensions]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report-sha256', required=True)
    main(parser.parse_args().report_sha256)
