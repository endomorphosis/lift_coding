"""Correct shared-validator provenance in retained LA009 records, without rerun."""
import sys
sys.dont_write_bytecode = True
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
PAPER = HERE.parents[3]
ROOT = PAPER.parents[2]
ORIGINAL = HERE.parent / 'outputs/results/source_ir'
CURRENT = PAPER / 'results/source_ir'
EXPECTED = {
    'raw.jsonl': 'b420d59a9bb918c50e42f4b99cfd7973bbb502b646030c8b9fd2c8c8445b708a',
    'metrics.json': '1caa2ab02c253415d64f459b44d6c75ed1bccba99312726ef91bf16d693e939c',
    'failure_review.md': 'b38e8034bb65a6a86d2ceb7daccb024c0eeb5415083236e11932072edaf1699f',
}
RECEIPT_SHA = '1410f502978a1e55f46071fe80e0e67d88fff79f4e770c6e127b19517721e7f8'
OLD_METRIC = 'skill_normalizer_independent_decoder_agreement'
NEW_METRIC = 'skill_normalizer_shared_schema_conformance'
OLD_BOOL = 'normalizer_and_independent_decoder_agree'
NEW_BOOL = 'normalizer_and_shared_schema_conformant'
NOTE = ('The normalizer already invokes these same Intent IR decoder/schema functions. '
        'This repeats shared-validator conformance; it is not independent agreement or semantic accuracy.')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()


def write_fresh(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())


def shared_checker(value):
    value = copy.deepcopy(value)
    assert value['checker']['distinct_from_evaluated_adapter'] is True
    value['checker']['distinct_from_evaluated_adapter'] = False
    value['checker']['shares_validation_code_with_evaluated_adapter'] = True
    value['checker']['observation_scope'] = 'repeated_shared_validator_conformance'
    return value


def transform_rows(rows):
    assert len(rows) == len({row['case_id'] for row in rows}) == 60
    updated = copy.deepcopy(rows)
    changed = 0
    for before, after in zip(rows, updated):
        if before['population'] != 'skill' or before['status'] != 'prediction':
            assert before == after
            continue
        consistency = after['compiler_checker']['implementation_consistency']
        assert consistency['shared_producer_dependence'] is False and consistency[OLD_BOOL] is True
        consistency[NEW_BOOL] = consistency.pop(OLD_BOOL)
        consistency['shared_producer_dependence'] = True
        consistency['note'] = NOTE
        after['parse_schema_validity'] = shared_checker(before['parse_schema_validity'])
        checker = after['compiler_checker'].pop('independent_schema_checker')
        assert checker == before['parse_schema_validity']
        after['compiler_checker']['shared_schema_checker'] = shared_checker(checker)
        changed += 1
    assert changed == 18
    return updated


def numeric_summary(rows):
    return {'records': len(rows),
            'predictions': sum(r['status'] == 'prediction' for r in rows),
            'failed': sum(r['status'] == 'failed' for r in rows),
            'unsupported': sum(r['status'] == 'unsupported' for r in rows),
            'span_linked': sum(r['source_span_linkage']['linked'] is True for r in rows),
            'schema_valid': sum(r['parse_schema_validity']['valid'] is True for r in rows),
            'contract_satisfied': sum(r['machine_contract_outcome']['satisfied'] is True for r in rows)}


def science_projection(row):
    # Remove only the provenance slots actually reclassified. Every prediction,
    # case identity, source span, failure, expectation and metric input remains.
    row = copy.deepcopy(row)
    if row['population'] == 'skill' and row['status'] == 'prediction':
        row['parse_schema_validity'].pop('checker')
        checkers = row['compiler_checker']
        checkers.pop('independent_schema_checker', None)
        checkers.pop('shared_schema_checker', None)
        consistency = checkers['implementation_consistency']
        for key in [OLD_BOOL, NEW_BOOL, 'shared_producer_dependence', 'note']:
            consistency.pop(key, None)
    return row


def main():
    start = time.monotonic(); started = dt.datetime.now(dt.timezone.utc).isoformat()
    for name, digest in EXPECTED.items():
        assert sha(ORIGINAL / name) == sha(CURRENT / name) == digest
    receipt_path = PAPER / 'receipts/LA-009.json'
    assert sha(receipt_path) == RECEIPT_SHA
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    old_artifacts = dict(receipt['artifacts'])
    assert all(sha(ROOT / path) == digest for path, digest in old_artifacts.items())
    rows = [json.loads(line) for line in (ORIGINAL / 'raw.jsonl').read_text().splitlines() if line.strip()]
    transformed = transform_rows(rows)
    assert [science_projection(r) for r in rows] == [science_projection(r) for r in transformed]
    assert numeric_summary(rows) == numeric_summary(transformed) == {
        'records': 60, 'predictions': 50, 'failed': 4, 'unsupported': 6,
        'span_linked': 60, 'schema_valid': 50, 'contract_satisfied': 60}
    controls = []
    for label, altered in [('missing_case', rows[:-1]), ('duplicate_case', rows[:-1] + rows[:1])]:
        try:
            transform_rows(altered)
        except AssertionError:
            controls.append(label)
        else:
            raise AssertionError('changed population admitted')
    changed_input = copy.deepcopy(rows)
    next(r for r in changed_input if r['population'] == 'skill' and r['status'] == 'prediction')['compiler_checker']['implementation_consistency']['shared_producer_dependence'] = True
    try:
        transform_rows(changed_input)
    except AssertionError:
        controls.append('already_changed_provenance')
    else:
        raise AssertionError('non-original provenance admitted')
    forged = copy.deepcopy(transformed); forged[0]['status'] = 'failed'
    assert [science_projection(r) for r in rows] != [science_projection(r) for r in forged]
    controls.append('changed_outcome_detected')

    raw = ''.join(json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n' for row in transformed).encode()
    metrics = json.loads((ORIGINAL / 'metrics.json').read_bytes())
    old_metrics = copy.deepcopy(metrics)
    comparison = metrics['metrics']['compiler_checker_consistency'].pop(OLD_METRIC)
    assert comparison['numerator'] == comparison['denominator'] == 18 and comparison['shared_producer_dependence'] is False
    comparison['shared_producer_dependence'] = True
    comparison['shared_checker'] = comparison.pop('independent_checker')
    comparison['note'] = NOTE
    metrics['metrics']['compiler_checker_consistency'][NEW_METRIC] = comparison
    metrics['metrics']['parse_schema_validity']['property'] = 'adapter_or_schema_conformance'
    metrics['raw_sha256'] = hashlib.sha256(raw).hexdigest()
    metrics['provenance_correction'] = {
        'kind': 'shared_validator_classification', 'measurement_reexecuted': False,
        'original_raw_sha256': EXPECTED['raw.jsonl'], 'original_metrics_sha256': EXPECTED['metrics.json'],
        'source': str(Path(__file__).relative_to(ROOT)), 'source_sha256': sha(Path(__file__)), 'scope': NOTE}
    assert metrics['case_accounting'] == old_metrics['case_accounting']
    assert metrics['by_population'] == old_metrics['by_population'] and metrics['by_split'] == old_metrics['by_split']
    review = (ORIGINAL / 'failure_review.md').read_text()
    sentence = '- Skill decoder/schema checks are independent of the SkillCenter normalizer.'
    assert review.count(sentence) == 1
    review = review.replace(sentence, '- Skill decoder/schema conformance reuses the same validators already called by the SkillCenter normalizer; shared-producer dependence is present.')
    review += '\n## Shared-validator provenance correction\n\n' + NOTE + '\nThe original measurements, all60 cases, four failures and six unsupported cases are unchanged. No adapter or checker was rerun. Original snapshots and receipt remain retained.\n'
    rendered = {'raw.jsonl': raw, 'metrics.json': json_bytes(metrics), 'failure_review.md': review.encode()}
    write_fresh(HERE / 'original_receipt.json', receipt_bytes)
    for name, data in rendered.items():
        write_fresh(HERE / 'outputs/results/source_ir' / name, data)
        (CURRENT / name).write_bytes(data)
    guide = ('# LA009 shared-validator correction\n\n' + NOTE + '\n\n'
             'Use `skill_normalizer_shared_schema_conformance` and shared-producer dependence=true. '
             'The retained18/18 describes repeated structural conformance, never independent agreement. '
             'All60 cases and50 predictions/4 failures/6 unsupported observations remain unchanged.\n\n'
             'The original LA009 snapshot files remain byte-identical; `original_receipt.json` binds them. '
             'Reproduction is the original recorded measurement followed by this metadata-only reducer. '
             'No new native adapter, validator, model, benchmark or final-data execution occurred. '
             'Downstream tables and manuscript prose must use the corrected metric name and dependence label.\n')
    write_fresh(HERE / 'DOWNSTREAM_GUIDANCE.md', guide.encode())
    result = {'schema': 'la009-shared-provenance-correction/v1', 'success': True,
              'started_at': started, 'completed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'wall_seconds': time.monotonic() - start, 'source_sha256': sha(Path(__file__)),
              'original_receipt_sha256': RECEIPT_SHA, 'original_output_sha256': EXPECTED,
              'corrected_output_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in rendered.items()},
              'exact_scientific_projection_preserved': True, 'numeric_summary': numeric_summary(transformed),
              'changed_provenance_records': 18, 'negative_controls_passed': controls,
              'original10_artifacts_unchanged': all(sha(ROOT / path) == digest for path, digest in old_artifacts.items()),
              'native_adapter_checker_model_or_scientific_runs': 0}
    assert result['original10_artifacts_unchanged']
    write_fresh(HERE / 'qualification.json', json_bytes(result))
    receipt['original_completed_at'] = receipt['completed_at']
    receipt['completed_at'] = result['completed_at']
    receipt['completion_mode'] += ' Subsequent metadata-only correction labels the skill18/18 result as shared-validator conformance and preserves all original measurements.'
    old_sentence = 'Skill decoder/schema checks are independent of the SkillCenter normalizer.'
    assert old_sentence in receipt['criteria'][1]['explanation']
    receipt['criteria'][1]['explanation'] = receipt['criteria'][1]['explanation'].replace(old_sentence, NOTE)
    original_prefix = str((HERE.parent / 'outputs').relative_to(ROOT))
    corrected_prefix = str((HERE / 'outputs').relative_to(ROOT))
    for criterion in receipt['criteria']:
        criterion['evidence'] = [path.replace(original_prefix, corrected_prefix) for path in criterion['evidence']]
    receipt['criteria'][1]['evidence'] += [str((HERE / 'qualification.json').relative_to(ROOT)), str((HERE / 'DOWNSTREAM_GUIDANCE.md').relative_to(ROOT))]
    receipt['outputs'] = {str((CURRENT / name).relative_to(ROOT)): str((HERE / 'outputs/results/source_ir' / name).relative_to(ROOT)) for name in rendered}
    receipt['source_versions']['shared_skill_checker'] = receipt['source_versions'].pop('independent_skill_checker')
    receipt['source_versions']['raw_sha256_before_provenance_correction'] = receipt['source_versions']['raw_sha256']
    receipt['source_versions']['raw_sha256'] = metrics['raw_sha256']
    receipt['source_versions']['shared_skill_validator_dependence'] = True
    receipt['limitations'].append(NOTE)
    receipt['provenance_correction'] = {
        'original_receipt': str((HERE / 'original_receipt.json').relative_to(ROOT)),
        'original_receipt_sha256': RECEIPT_SHA, 'qualification': str((HERE / 'qualification.json').relative_to(ROOT)),
        'original_measurement_outcomes_unchanged': True, 'native_task_completion_history_unchanged': True}
    receipt['commands'].append({'argv': ['/usr/bin/python3.12', '-B', str(Path(__file__).relative_to(ROOT))],
                                'cwd': '.', 'exit_code': 0, 'started_at': started, 'completed_at': result['completed_at'],
                                'scope': 'retained_metadata_only_no_adapter_or_checker_rerun',
                                'log': str((HERE / 'qualification.json').relative_to(ROOT)),
                                'script_artifact': str(Path(__file__).relative_to(ROOT)),
                                'result': str((HERE / 'qualification.json').relative_to(ROOT))})
    for path in HERE.rglob('*'):
        if path.is_file():
            receipt['artifacts'][str(path.relative_to(ROOT))] = sha(path)
    receipt_path.write_bytes(json_bytes(receipt))
    print(json.dumps({'success': True, 'original_artifacts': len(old_artifacts), 'current_artifacts': len(receipt['artifacts']),
                      'qualification': str(HERE / 'qualification.json'), 'numeric_summary': result['numeric_summary']}))


if __name__ == '__main__':
    main()
