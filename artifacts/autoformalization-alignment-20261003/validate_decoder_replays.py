"""Read-only arithmetic and binding checks for the bounded decoder replay stage."""
from collections import Counter
import ast
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path('/home/barberb/lift_coding')
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
OUTPUT = CAMPAIGN / 'decoder-replay-01'
CHECKOUT = ROOT / '.worktrees/alignment-decoder-768-20261003'
PLAN = ROOT / 'implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md'


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def bind(path):
    path = Path(path)
    value = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(value), sha256=hashlib.sha256(value).hexdigest())


def references(value):
    if isinstance(value, dict):
        if {'path', 'sha256'} <= value.keys():
            yield value
        for nested in value.values():
            yield from references(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from references(nested)


def shape_and_values(value):
    if not isinstance(value, list):
        assert type(value) in (int, float) and math.isfinite(value)
        return [], [value]
    assert value
    children = [shape_and_values(item) for item in value]
    assert all(shape == children[0][0] for shape, _ in children)
    return [len(value)] + children[0][0], [item for _, items in children for item in items]


def binary_tensor_digest(state):
    result = hashlib.sha256()
    scalar_ints = []
    elements = 0
    for name, value in sorted(state.items()):
        shape, values = shape_and_values(value)
        integral = type(value) is int
        dtype = 'torch.int64' if integral else 'torch.float32'
        if integral:
            scalar_ints.append(name)
        result.update(raw([name, dtype, shape]))
        result.update(struct.pack('<' + ('q' if integral else 'f') * len(values), *values))
        elements += len(values)
    assert scalar_ints == ['head_initialization_seed', 'ordered_clause_recurrent_version']
    assert elements == 191308
    return result.hexdigest()


def generation(row):
    return {key: row[key] for key in ('status', 'reason', 'canonical_ir')}


def control_comparison(left, right):
    changed, greatest = [], 0.
    for index, (a, b) in enumerate(zip(left['rows'], right['rows'], strict=True)):
        if generation(a) != generation(b):
            changed.append(index)
        x, y = (item['span_diagnostics']['modality_logits'] for item in (a, b))
        assert len(x) == len(y) == 3 and all(math.isfinite(v) for v in x + y)
        greatest = max(greatest, *(abs(u - v) for u, v in zip(x, y, strict=True)))
    return dict(generation_changed_count=len(changed), generation_changed_row_positions=changed,
                modality_logit_comparison_rows=len(left['rows']), max_abs_modality_logit_difference=greatest)


def main():
    assert not OUTPUT.exists(), 'fresh validation generation required'
    span_path = CAMPAIGN / 'span-replay-01/report.json'
    sidecar_path = CAMPAIGN / 'sidecar-replay-01/report.json'
    span, sidecar = load(span_path), load(sidecar_path)
    discovery = load(CAMPAIGN / 'decoder-discovery-01/inventory.json')
    for report in (span, sidecar, discovery):
        assert report['content_sha256'] == digest({k: v for k, v in report.items() if k != 'content_sha256'})
    checked = {}
    for reference in references([span, sidecar, discovery['preserved_prior_bindings']]):
        current = bind(reference['path'])
        assert current['sha256'] == reference['sha256'], reference['path']
        assert 'bytes' not in reference or reference['bytes'] == current['bytes']
        if current['path'] in checked:
            assert current == checked[current['path']]
        checked[current['path']] = current
    inputs = load(CAMPAIGN / 'richer-embedding-01/embedding_inputs.json')
    lane = load(CAMPAIGN / 'richer-embedding-01/native768_embeddings.json')
    for payload in (inputs, lane):
        assert payload['payload_sha256'] == digest({k: v for k, v in payload.items() if k != 'payload_sha256'})
    receipts = {row['id']: row for row in lane['receipts']}
    assert len(inputs['rows']) == len(receipts) == 34
    vectors = [receipts[row['id']]['embedding'] for row in inputs['rows']]
    for row, vector in zip(inputs['rows'], vectors, strict=True):
        assert hashlib.sha256(row['source_text'].encode()).hexdigest() == row['source_sha256']
        assert row['source_sha256'] == receipts[row['id']]['source_sha256']
        assert digest(vector) == receipts[row['id']]['embedding_sha256']
        assert len(vector) == 768 and all(math.isfinite(value) for value in vector)
    assert len({row['source_text'] for row in inputs['rows']}) == 33
    positions = [index for index, row in enumerate(inputs['rows']) if row['context_role'] == 'explicit_assumptions']
    assert positions == span['context_pair_positions'] and len(positions) == 2
    assert vectors[positions[0]] == vectors[positions[1]]
    span_counts = []
    for run in span['runs']:
        checkpoint = load(run['checkpoint_binding']['path'])
        assert digest(checkpoint) == run['checkpoint_payload_sha256']
        assert digest(checkpoint['model_state']) == run['model_state_sha256']
        assert checkpoint['context_contract']['representation_id'] == lane['backend_evidence']['profile_id']
        assert checkpoint['progress']['optimizer_steps'] == run['recorded_optimizer_steps']
        if run['role'] == 'constructed_initial_control':
            assert digest(checkpoint['model_state']) == checkpoint['initial_model_state_sha256']
            assert checkpoint['optimizer_state']['parameters'] == {}
        outputs = {control: load(pin['path']) for control, pin in run['output_bindings'].items()}
        assert load(run['private_reload_binding']['path']) == outputs['none']
        assert outputs['none']['rows'][positions[0]] == outputs['none']['rows'][positions[1]]
        for control, result in outputs.items():
            assert len(result['rows']) == 34 and result['model_state_unchanged'] is True
            assert all(result[key] is False for key in ('target_access', 'teacher_forcing', 'training_executed'))
            assert result['decoded_count'] == sum(row['status'] == 'decoded' for row in result['rows'])
            assert run['summaries'][control]['decoded_count'] == result['decoded_count']
            assert run['summaries'][control]['abstention_reasons'] == dict(Counter(
                row['reason'] for row in result['rows'] if row['status'] != 'decoded'))
            for index, row in enumerate(result['rows']):
                effective = [0.] * 768 if control == 'zero' else vectors[(index + 1) % 34] if control == 'rotate' else vectors[index]
                assert row['latent_sha256'] == digest(effective)
                assert row['source_sha256'] == inputs['rows'][index]['source_sha256']
                assert row['latent_input_enabled'] is (control != 'disabled')
            if control != 'none':
                assert run['control_comparisons'][control] == control_comparison(outputs['none'], result)
        span_counts.append(dict(seed=run['seed'], role=run['role'],
                               decoded_count=outputs['none']['decoded_count']))
    assert len(span['runs']) == 9 and span['calls'] == dict(optimizer_steps=0, inference_calls=45, row_forward_calls=1530)
    scope = load(span['reference_scope_binding']['path'])
    assert sum(row['literal_reference_compatible'] for row in scope['rows']) == 0
    assert all(row['literal_exact_rate'] is None and row['literal_exact_count'] == 0 for row in scope['scores'])
    assert span['rng_state_unchanged'] is True and span['literal_compatible_reference_count'] == 0
    panel = load(CAMPAIGN / 'richer-01/panel.json')
    panel_by_input = {row['input_sha256']: row for row in panel['rows']}
    assert len(panel_by_input) == 34
    decoded_diagnostics = []
    for row, prediction in zip(inputs['rows'], load(CAMPAIGN / 'span-replay-01/seed1729-selected400-none.json')['rows'], strict=True):
        if prediction['status'] == 'decoded':
            reference = panel_by_input[row['input_sha256']]
            assert reference['row_kind'] in ('unsupported', 'ambiguous')
            decoded_diagnostics.append(dict(panel_id=reference['id'], row_kind=reference['row_kind'],
                                            predicted_ir=prediction['canonical_ir']))
    sidecar_counts, state_values, normalization = [], {}, {}
    for role, restoration in sidecar['restorations'].items():
        state = load(restoration['state']['path'])
        state_values[role] = state
        assert len(state['model_state']) == 32 and digest(state['model_state']) == state['weights_sha256']
        assert binary_tensor_digest(state['model_state']) == state['tensor_sha256'] == restoration['tensor_sha256']
        assert restoration['parameter_count'] == 189736
        normalization[role] = {key: digest(value) for key, value in {
            'input_transform': state['input_transform'], 'paragraph_normalization': state['architecture']['normalization'],
            'clause_normalization': state['architecture']['clause_normalization'], 'count_prior': state['architecture']['count_prior']}.items()}
        forward = load(sidecar['artifacts'][role + '-forward']['path'])
        assert len(forward['rows']) == 34 and forward['explicit_prefix'] == 'one_BOS_token_only'
        assert forward['original_input_transform_retained'] is True
        for source, observation in zip(inputs['rows'], forward['rows'], strict=True):
            assert source['id'] == observation['id']
            assert source['source_sha256'] == observation['source_sha256']
            assert observation['embedding_sha256'] == receipts[source['id']]['embedding_sha256']
            assert len(observation['bos_next_logits']) == 32
            assert all(math.isfinite(value) for value in observation['bos_next_logits'])
        generation_result = load(sidecar['artifacts'][role + '-generation']['path'])
        assert generation_result['completed_rows'] == len(generation_result['predictions']) == 34
        assert generation_result['output_limit'] == 512
        json_count = 0
        vocab = state['codec']['target_vocabulary']
        for source, prediction in zip(inputs['rows'], generation_result['predictions'], strict=True):
            assert source['id'] == prediction['id'] and prediction['generation_status'] == 'eos'
            assert 0 < len(prediction['token_ids']) <= 512
            assert ''.join(vocab[token] for token in prediction['token_ids']) == prediction['token_text']
            try:
                parsed = json.loads(prediction['token_text'])
            except ValueError:
                assert prediction['json_parse_valid'] is False
            else:
                assert prediction['json_parse_valid'] is True and parsed == prediction['parsed_json']
                json_count += 1
                assert role == 'last-attempt' and len(parsed['rules']) == 1
                assert all(parsed['rules'][0][key] == [] for key in ('conditions', 'exceptions', 'temporal'))
        assert json_count == sidecar['generation'][role]['json_parse_valid_rows']
        sidecar_counts.append(dict(role=role, rows=34, json_parse_valid=json_count,
                                  distinct_outputs=len({row['token_text'] for row in generation_result['predictions']}),
                                  max_content_tokens=max(len(row['token_ids']) for row in generation_result['predictions'])))
    assert state_values['initial']['model_state'] == state_values['selected']['model_state']
    assert normalization['initial'] == normalization['selected'] == normalization['last-attempt']
    assert load(sidecar['artifacts']['initial-forward']['path'])['rows'] == load(sidecar['artifacts']['selected-forward']['path'])['rows']
    assert sidecar['numerical']['actual_bos_forward_calls'] == 16 and sidecar['numerical']['greedy_batch_calls'] == 15
    assert all(value is False for value in sidecar['support']['named_diagnostic_symbol_representability'].values())
    for report in (span, sidecar):
        assert report['qualified'] is False and report['proof_authority'] is False
        assert report['source_fidelity_established'] is False and report['training_executed'] is False
    head = subprocess.check_output(['git', '-C', str(CHECKOUT), 'rev-parse', 'HEAD'], text=True).strip()
    assert head == '64bc5734dc82db72e955f2e809b770127e9b6cfc'
    assert subprocess.check_output(['git', '-C', str(CHECKOUT), 'status', '--porcelain=v1', '--untracked-files=normal'], text=True).strip() == ''
    documentation = [PLAN, CAMPAIGN / 'decoder-replay-report.md']
    links = []
    for document in documentation:
        for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', document.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            resolved = (document.parent / target.split('#')[0]).resolve()
            assert resolved.is_file() or resolved == OUTPUT / 'validation.json', str(resolved)
            links.append(dict(document=str(document), target=target, resolved=str(resolved)))
    work_ids = re.findall(r'^\| (AFI-[0-9]+[ab]?) \|', PLAN.read_text(), flags=re.M)
    assert len(work_ids) == len(set(work_ids)) == 25
    assert set(re.findall(r'AFI-[0-9]+[ab]?', PLAN.read_text())) <= set(work_ids)
    runner_syntax = []
    for runner in ('replay_source_span.py', 'replay_formula_sidecar.py', 'validate_decoder_replays.py'):
        path = CAMPAIGN / runner
        ast.parse(path.read_text(), filename=str(path))
        runner_syntax.append(bind(path))
    result = dict(schema='alignment-retained-decoder-replay-validation/v1', status='passed_unqualified',
                  runner_binding=bind(__file__), span_report_binding=bind(span_path), sidecar_report_binding=bind(sidecar_path),
                  predecessor_validation_bindings=[bind(CAMPAIGN / 'decoder-discovery-01/validation.json'),
                                                   bind(CAMPAIGN / 'plan-synthesis-01/validation.json')],
                  preserved_prior_bindings=discovery['preserved_prior_bindings'], checked_file_bindings=list(checked.values()),
                  span_state_counts=span_counts, span_primary_state_rows=306, span_total_row_forwards=1530,
                  span_private_reload_count=9, span_literal_accuracy_available=False,
                  span_trained_seed1729_decoded_diagnostics=decoded_diagnostics,
                  sidecar_state_counts=sidecar_counts, sidecar_saved_BOS_observations=102,
                  sidecar_BOS_batch_calls=16, sidecar_ABA_extra_observations=8, sidecar_greedy_outputs=102,
                  sidecar_greedy_batch_calls=15, sidecar_binary_digest_recomputed_stdlib=True,
                  sidecar_state_tensor_count=32, sidecar_parameter_tensor_count=25, sidecar_buffer_tensor_count=7,
                  sidecar_parameter_count=189736, sidecar_stored_elements=191308,
                  sidecar_preserved_normalization_digests=normalization,
                  source_checkout=dict(path=str(CHECKOUT), commit=head, clean=True),
                  documentation_bindings=[bind(path) for path in documentation], local_link_checks=links,
                  work_package_ids=work_ids, runner_syntax=runner_syntax,
                  prior_evidence_preserved=True, protocol_preserved=True, complete_dependency_manifest=False,
                  model_executed_by_validation=False, new_unit_tests_executed=False,
                  lint_pass_claimed=False, independent_semantic_review_completed=False,
                  validation_scope='artifact_hashes_source_joins_control_arithmetic_state_bytes_generation_counts_documentation',
                  qualified=False, proof_authority=False, source_fidelity_established=False)
    result['content_sha256'] = digest(result)
    OUTPUT.mkdir()
    path = OUTPUT / 'validation.json'
    with path.open('xb') as stream:
        stream.write(raw(result) + b'\n')
    assert all(Path(item['resolved']).is_file() for item in links)
    print(json.dumps(dict(validation=bind(path), checked_file_count=len(checked), local_link_count=len(links)), indent=2))


if __name__ == '__main__':
    main()
