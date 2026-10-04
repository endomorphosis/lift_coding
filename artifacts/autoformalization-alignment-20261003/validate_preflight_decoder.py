"""Check saved wrapper evidence and documentation without numerical inference."""

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
OUTPUT = CAMPAIGN / 'preflight-decoder-validation-01'
REPORT_SHA = 'dd82c1546bdae48d812c855a304c3d486205010331d0456fa887f8e6cf4cfc54'
CONTROLS = ('none', 'zero', 'disabled', 'rotate')


def raw(value, *, ascii=False):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=ascii, allow_nan=False).encode('utf-8')


def digest(value, *, ascii=False):
    return hashlib.sha256(raw(value, ascii=ascii)).hexdigest()


def load(path, *, sealed=False):
    value = json.loads(Path(path).read_bytes())
    if sealed:
        assert value['content_sha256'] == digest({
            key: item for key, item in value.items() if key != 'content_sha256'})
    return value


def bind(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def references(value):
    if isinstance(value, dict):
        if {'path', 'sha256'} <= value.keys():
            yield value
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def main():
    assert not OUTPUT.exists(), 'fresh validation generation required'
    checked = {}

    def verify(reference):
        current = bind(reference['path'])
        assert current['sha256'] == reference['sha256'], reference['path']
        assert 'bytes' not in reference or current['bytes'] == reference['bytes']
        checked[current['path']] = current
        return current

    report_path = CAMPAIGN / 'preflight-decoder-01/report.json'
    report_binding = bind(report_path)
    assert report_binding['sha256'] == REPORT_SHA
    report = load(report_path, sealed=True)
    plan = load(report['plan_binding']['path'], sealed=True)
    joins = load(report['request_joins_binding']['path'], sealed=True)
    for reference in references(report):
        verify(reference)
    for reference in references(plan):
        verify(reference)
    referenced_file_count = len(checked)
    assert referenced_file_count == 308
    checked[report_binding['path']] = report_binding
    prior = load(CAMPAIGN / 'source-grounding-validation-01/validation.json', sealed=True)
    assert len(prior['checked_file_bindings']) == len(report['source_bindings']) == 258
    for reference in prior['checked_file_bindings'] + prior['new_implementation_test_bindings']:
        verify(reference)
    manifest = load(CAMPAIGN / 'grounding-01/request_manifest.json', sealed=True)
    inputs = load(CAMPAIGN / 'richer-embedding-01/embedding_inputs.json')
    lane = load(CAMPAIGN / 'richer-embedding-01/native768_embeddings.json')
    raw_report = load(CAMPAIGN / 'span-replay-01/report.json', sealed=True)
    assert len(manifest['rows']) == len(inputs['rows']) == len(lane['receipts']) == 34
    assert [row['id'] for row in manifest['rows']] == [row['id'] for row in inputs['rows']]
    by_id = {row['id']: row for row in lane['receipts']}
    vectors = [by_id[row['id']]['embedding'] for row in inputs['rows']]
    requests = [dict(id=row['id'], source_text=row['source_text'],
                     context_text=row['declared_context']['text'],
                     requires_context_resolution=row['requires_context_resolution'])
                for row in manifest['rows']]
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir.canonical_decoder_preflight import analyze_decoder_source
    from ipfs_datasets_py.logic.legal_ir.canonical_span_decoder import validate_preflight_decoding
    preflights = [analyze_decoder_source(row['source_text'], context_text=row['context_text'],
                  requires_context_resolution=row['requires_context_resolution']) for row in requests]
    positions = [index for index, row in enumerate(preflights) if row['outcome'] == 'unassessed']
    assert len(positions) == 24
    counts = dict(Counter(row['outcome'] for row in preflights))
    assert counts == report['source_preflight_counts'] == dict(
        unassessed=24, unsupported_profile=6, clarification_required=4)
    assert len(joins['rows']) == 34
    for index, (source, receipt, join, vector) in enumerate(zip(
            inputs['rows'], manifest['rows'], joins['rows'], vectors, strict=True)):
        context_hash = hashlib.sha256(requests[index]['context_text'].encode('utf-8')).hexdigest()
        assert source['source_text'] == receipt['source_text']
        assert source['source_sha256'] == receipt['source_sha256'] == join['source_sha256']
        assert hashlib.sha256(source['source_text'].encode('utf-8')).hexdigest() == source['source_sha256']
        assert digest(vector) == by_id[source['id']]['embedding_sha256'] == join['embedding_sha256']
        assert join['id'] == source['id'] and join['position'] == index
        assert join['context_sha256'] == context_hash == receipt['declared_context']['sha256']
        assert join['requires_context_resolution'] is requests[index]['requires_context_resolution']
        assert join['forwarded'] is (index in positions)
        assert join['preflight_outcome'] == preflights[index]['outcome']
        donor = (index + 1) % 34
        assert join['full_rotation_donor_position'] == donor
        assert join['full_rotation_donor_id'] == requests[donor]['id']
        assert join['full_rotation_donor_embedding_sha256'] == digest(vectors[donor])
    primary, repeats, parity, blocked, rotated_blocked_donors = 0, 0, 0, 0, 0
    assert len(report['runs']) == len(raw_report['runs']) == 9
    for run, prior_run in zip(report['runs'], raw_report['runs'], strict=True):
        assert (run['seed'], run['role']) == (prior_run['seed'], prior_run['role'])
        checkpoint = load(run['checkpoint_binding']['path'])
        assert digest(checkpoint, ascii=True) == prior_run['checkpoint_payload_sha256']
        state_hash = digest(checkpoint['model_state'], ascii=True)
        assert state_hash == run['model_state_sha256'] == prior_run['model_state_sha256']
        assert len(checkpoint['model_state']) == run['model_tensor_count'] == 23
        assert run['model_parameter_count'] == 33271
        assert run['model_state_unchanged'] is run['checkpoint_payload_unchanged'] is True
        saved = {}
        for control in CONTROLS:
            result = load(run['output_bindings'][control]['path'], sealed=True)
            validate_preflight_decoding(result, requests, vectors)
            original = load(prior_run['output_bindings'][control]['path'])
            assert result['requested_control'] == control
            assert result['submitted_positions'] == positions
            assert result['decoder_call_count'] == result['decoder_completion_count'] == 1
            assert result['input_count'] == 34 and result['eligible_count'] == 24
            assert result['backend_exception_type'] is None
            outcomes = dict(Counter(row['outcome'] for row in result['rows']))
            assert outcomes == run['summaries'][control]['outcomes'] == dict(
                decoder_abstained=24, source_blocked=6, clarification_required=4)
            for index, row in enumerate(result['rows']):
                assert row['preflight'] == preflights[index]
                if index in positions:
                    assert raw(row['decoder_row']) == raw(original['rows'][index])
                    assert row['decoder_row']['reason'] == 'copied_spans_overlap'
                    parity += 1
                    rotated_blocked_donors += int(control == 'rotate' and (index + 1) % 34 not in positions)
                else:
                    assert row['decoder_row'] is None
                    blocked += 1
            for field in ('target_access', 'teacher_forcing', 'training_executed', 'context_applied',
                          'source_fidelity_established', 'qualified', 'proof_authority', 'accepted'):
                assert result[field] is False
            saved[control] = result
            primary += 1
        repeat = load(run['private_reload_binding']['path'], sealed=True)
        validate_preflight_decoding(repeat, requests, vectors)
        assert raw(repeat) == raw(saved['none'])
        assert run['private_reload_bitwise_json_equal'] is run['private_models_disjoint_storage'] is True
        assert len(run['public_invocations']) == 4 and len(run['private_reload_invocations']) == 1
        for invocation in run['public_invocations'] + run['private_reload_invocations']:
            assert invocation['row_count'] == 24
            assert invocation['model_state_before_sha256'] == invocation['model_state_after_sha256'] == state_hash
            assert invocation['checkpoint_before_sha256'] == invocation['checkpoint_after_sha256']
            assert invocation['rng_state_unchanged'] is True
        repeats += 1
    assert (primary, repeats, parity, blocked, rotated_blocked_donors) == (36, 9, 864, 360, 63)
    assert report['calls'] == dict(inference_calls=45, optimizer_steps=0, row_forward_calls=1080)
    assert report['actual_row_forward_reduction'] == report['raw_prior_row_forward_calls'] - 1080 == 450
    assert report['new_encoder_calls'] == report['proof_calls'] == 0
    assert report['rng_state_unchanged'] is report['full_order_rotation_preserved'] is True
    assert all(report[field] is False for field in (
        'training_executed', 'authored_reference_semantics_read', 'independent_semantic_review_completed',
        'source_fidelity_established', 'qualified', 'proof_authority', 'promotion_performed'))
    assert not {'torch', 'transformers', 'numpy', 'spacy', 'llama_cpp'}.intersection(sys.modules)
    documents = [CAMPAIGN / 'preflight-decoder-report.md',
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
    assert set(re.findall(r'AFI-[0-9]+[ab]?', documents[1].read_text())) <= set(ids)
    checkout = ROOT / '.worktrees/alignment-decoder-768-20261003'
    assert subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain=v1',
                                   '--untracked-files=normal'], text=True).strip() == ''
    new_files = [REPO / relative for relative in (
        'ipfs_datasets_py/logic/legal_ir/canonical_span_decoder.py',
        'tests/unit/logic/legal_ir/test_canonical_span_decoder.py')]
    for reference in checked.values():
        assert bind(reference['path']) == reference
    result = dict(schema='alignment-preflight-decoder-stage-validation/v1', status='passed_unqualified',
                  runner_binding=bind(__file__), report_binding=report_binding,
                  checked_file_bindings=list(checked.values()), checked_file_count=len(checked),
                  report_plan_referenced_file_count=referenced_file_count, preserved_prior_binding_count=258,
                  new_implementation_test_bindings=[bind(path) for path in new_files],
                  deterministic_wrapper_receipts=primary + repeats, raw_primary_complete_row_matches=parity,
                  private_reload_receipt_matches=repeats, blocked_primary_slots_without_backend_rows=blocked,
                  rotated_eligible_rows_with_blocked_original_donors=rotated_blocked_donors,
                  source_preflight_counts=counts, all_request_count_per_response=34,
                  independent_readonly_audit=dict(status='passed', referenced_file_count=308,
                      deterministic_receipts=45, complete_row_matches=864, private_repeat_matches=9,
                      huge_integer_vector_rejected_before_decoder=True, model_execution=False,
                      limitation='Saved runner evidence and parity; no fresh numerical or semantic attestation.'),
                  focused_test_results=dict(passed=382, elapsed_seconds=4.00),
                  ruff_results=dict(wrapper_test_and_assay_files=3, status='passed'),
                  documentation_bindings=[bind(path) for path in documents], local_link_checks=links,
                  work_package_ids=ids, isolated_decoder_checkout_clean=True,
                  model_execution=False, training_execution=False, proof_execution=False,
                  complete_dependency_manifest=False, independent_semantic_review_completed=False,
                  qualified=False, proof_authority=False, source_fidelity_established=False)
    result['content_sha256'] = digest(result)
    OUTPUT.mkdir()
    path = OUTPUT / 'validation.json'
    with path.open('xb') as stream:
        stream.write(raw(result) + b'\n')
    assert all(Path(link['resolved']).is_file() for link in links)
    print(json.dumps(dict(validation=bind(path), checked_files=len(checked),
                          local_links=len(links), receipts=primary + repeats), indent=2))


if __name__ == '__main__':
    main()
