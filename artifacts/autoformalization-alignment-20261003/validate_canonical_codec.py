"""Validate byte preparation, weak-label separation and document bindings."""

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
OUTPUT = CAMPAIGN / 'canonical-codec-validation-01'
REPORT_SHA = 'd6f38de71b9027486fb693f94a029129acd0dd53b7109837b3c3fcfdc4425c59'
MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation')


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


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

    report_path = CAMPAIGN / 'canonical-codec-01/report.json'
    report_binding = bind(report_path)
    assert report_binding['sha256'] == REPORT_SHA
    report = load(report_path, sealed=True)
    plan = load(report['plan_binding']['path'], sealed=True)
    baselines = load(report['existing_codec_baselines_binding']['path'], sealed=True)
    for value in (report, plan, baselines):
        for reference in references(value):
            verify(reference)
    verify(report_binding)
    prior = load(CAMPAIGN / 'preflight-decoder-validation-01/validation.json', sealed=True)
    assert len(report['source_bindings']) == prior['checked_file_count'] == 311
    verify(prior['runner_binding'])
    for reference in prior['documentation_bindings']:
        if Path(reference['path']).name == 'preflight-decoder-report.md':
            verify(reference)
    inputs = load(report['target_free_inputs_binding']['path'], sealed=True)
    outcomes = load(report['all_request_outcomes_binding']['path'], sealed=True)
    train = load(report['train_weak_supervision_binding']['path'], sealed=True)
    dev = load(report['development_transport_binding']['path'], sealed=True)
    construction = load(CAMPAIGN / 'grounding-01/constructed_receipts.json', sealed=True)
    source_inputs = load(CAMPAIGN / 'richer-embedding-01/embedding_inputs.json')
    source_by_id = {row['id']: row for row in source_inputs['rows']}
    ground_by_id = {row['id']: row['grounding'] for row in construction['rows']}
    input_by_id = {row['id']: row for row in inputs['rows']}
    outcome_by_id = {row['id']: row for row in outcomes['rows']}
    assert len(source_by_id) == len(input_by_id) == len(outcome_by_id) == 34
    assert set(source_by_id) == set(input_by_id) == set(outcome_by_id) == set(ground_by_id)
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir import canonical_byte_codec as codec
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_formula_codec as typed
    lane_joins = 0
    for name, reference in inputs['lane_bindings'].items():
        verify(reference)
        lane = load(reference['path'])
        for receipt in lane['receipts']:
            row = input_by_id[receipt['id']]
            source = source_by_id[receipt['id']]
            observed = row['embeddings'][name]
            assert set(row) == {'id', 'input_sha256', 'source_sha256', 'source_text', 'context_text',
                                'context_sha256', 'requires_context_resolution', 'context_applied', 'embeddings'}
            assert row['source_text'] == source['source_text']
            assert row['input_sha256'] == receipt['input_sha256'] == source['input_sha256']
            assert row['source_sha256'] == receipt['source_sha256'] == source['source_sha256']
            assert row['context_sha256'] == hashlib.sha256(row['context_text'].encode()).hexdigest()
            assert observed['embedding'] == receipt['embedding']
            assert digest(observed['embedding']) == observed['embedding_sha256'] == receipt['embedding_sha256']
            assert observed['dimension'] == lane['dimension']
            assert observed['profile_id'] == lane['backend_evidence']['profile_id']
            assert observed['token_input_sha256'] == receipt['token_input_sha256']
            assert observed['context_applied'] is row['context_applied'] is False
            lane_joins += 1
    assert lane_joins == 102
    assert inputs['contains_canonical_ir'] is inputs['contains_target_token_ids'] is False
    assert Counter(row['grounding_outcome'] for row in outcomes['rows']) == dict(
        grounded_candidate=22, source_blocked=10, proposal_unavailable=2)
    for row in outcomes['rows']:
        assert set(row['masks']) == set(MASKS)
        expected = int(row['split'] == 'train' and row['grounding_outcome'] == 'grounded_candidate')
        assert row['masks'] == {field: expected if field == 'weak_decoder_fit' else 0 for field in MASKS}
        assert row['review_status'] == 'pending' and row['negative_gold_sequence_created'] is False
    assert len(train['rows']) == train['row_count'] == 16
    assert len(dev['rows']) == dev['constructed_candidate_count'] == 6
    assert dev['positive_denominator'] == 8 and dev['unavailable_positive_count'] == 2
    train_ids = {row['id'] for row in train['rows']}
    dev_ids = {row['id'] for row in dev['rows']}
    assert train_ids.isdisjoint(dev_ids)
    assert {row['group_id'] for row in train['rows']}.isdisjoint({row['group_id'] for row in dev['rows']})
    train_examples, anchors, partition_counts = [], 0, {}
    for partition, payload in (('train', train), ('validation', dev)):
        lengths = []
        for row in payload['rows']:
            source = input_by_id[row['id']]['source_text']
            ground = ground_by_id[row['id']]
            assert row['proposal']['canonical_ir'] == ground['canonical_ir']
            assert row['proposal']['anchors'] == ground['anchors']
            assert row['proposal_sha256'] == digest(row['proposal'])
            assert row['byte_token_ids_sha256'] == digest(row['byte_token_ids'])
            assert codec.encode_proposal(row['proposal'], source, output_cap=4096) == row['byte_token_ids']
            assert codec.decode_proposal(row['byte_token_ids'], source, output_cap=4096) == row['proposal']
            assert codec.inspect_encoding(row['proposal'], source, output_cap=4096) == row['inspection']
            assert codec.inspect_encoding(row['proposal'], source, output_cap=512) == row['same_numeric_512_ceiling_new_byte_unit_inspection']
            assert row['inspection']['outcome'] == 'encoding_admitted'
            assert row['same_numeric_512_ceiling_new_byte_unit_inspection']['outcome'] == 'encoding_unavailable'
            assert row['masks'] == {field: int(partition == 'train' and field == 'weak_decoder_fit') for field in MASKS}
            if partition == 'train':
                assert row['next_token_loss_mask'] == [1] * (len(row['byte_token_ids']) - 1)
                train_examples.append(dict(id=row['id'], source_text=source, canonical_ir=row['proposal']['canonical_ir']))
            anchors += len(row['proposal']['anchors'])
            lengths.append(len(row['byte_token_ids']))
        partition_counts[partition] = dict(rows=len(lengths), minimum=min(lengths), maximum=max(lengths))
        saved = report['capacity_by_partition'][partition]
        assert saved['rows'] == len(lengths)
        assert (saved['min_byte_tokens_including_BOS_EOS'], saved['max_byte_tokens_including_BOS_EOS']) == (min(lengths), max(lengths))
    assert anchors == 172
    group_weights = Counter()
    for row in train['rows']:
        group_weights[row['group_id']] += row['group_loss_weight']
    assert len(group_weights) == 4 and all(value == 1.0 for value in group_weights.values())
    fitted = typed.fit_codec(train_examples)
    assert fitted == load(baselines['train_refitted_codec_binding']['path'])
    assert digest(fitted) == baselines['train_refitted_codec_sha256']
    retained = load(baselines['retained_checkpoint_binding']['path'])
    for name, vocabulary in (('train_refitted_no_neural_checkpoint', fitted),
                             ('retained_checkpoint_unmodified_codec', retained['codec'])):
        saved = baselines[name]
        for row in saved['rows']:
            source = input_by_id[row['id']]['source_text']
            candidate = ground_by_id[row['id']]['canonical_ir']
            for field, function, argument in (('source', typed.encode_source, source),
                                               ('target', typed.encode_target, candidate)):
                try:
                    ids = function(vocabulary, argument)
                except typed.CodecError:
                    assert row[field + '_compatible'] is False
                else:
                    assert row[field + '_compatible'] is True and row[field + '_token_count'] == len(ids)
        assert saved['source_compatible_count'] == saved['target_compatible_count'] == (22 if name.startswith('train') else 0)
    assert report['calls']['models'] == report['calls']['encoders'] == report['calls']['provers'] == report['calls']['neural_training'] == 0
    assert report['blocked_model_import_attempts'] == report['independent_reviews_completed'] == 0
    assert not {'torch', 'transformers', 'numpy', 'spacy', 'llama_cpp'}.intersection(sys.modules)
    documents = [CAMPAIGN / 'canonical-codec-report.md',
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
    assert subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain=v1',
                                   '--untracked-files=normal'], text=True).strip() == ''
    for reference in checked.values():
        assert bind(reference['path']) == reference
    result = dict(schema='alignment-canonical-byte-stage-validation/v1', status='passed_unqualified',
        runner_binding=bind(__file__), report_binding=report_binding,
        checked_file_bindings=list(checked.values()), checked_file_count=len(checked),
        preserved_prior_checked_file_count=311, target_free_vector_joins=102,
        full_proposal_roundtrips=22, exact_source_anchors=172, partition_token_counts=partition_counts,
        weak_training_rows=16, all_request_rows=34, fidelity_reference_rows=0,
        new_implementation_test_bindings=[bind(REPO / relative) for relative in (
            'ipfs_datasets_py/logic/legal_ir/canonical_byte_codec.py',
            'tests/unit/logic/legal_ir/test_canonical_byte_codec.py')],
        focused_test_results=dict(passed=474, elapsed_seconds=4.03),
        ruff_results=dict(codec_test_and_preparation_files=3, status='passed'),
        independent_readonly_review=dict(codec_boundary_checks=1295, full_proposal_roundtrips=22,
            artifact_masks_splits_input_joins_and_static_baselines='passed', model_execution=False),
        documentation_bindings=[bind(path) for path in documents], local_link_checks=links,
        work_package_ids=ids, isolated_decoder_checkout_clean=True,
        model_execution=False, neural_training_execution=False, proof_execution=False,
        complete_dependency_manifest=False, qualified=False, proof_authority=False,
        independent_semantic_review_completed=False, source_fidelity_established=False)
    result['content_sha256'] = digest(result)
    OUTPUT.mkdir()
    path = OUTPUT / 'validation.json'
    with path.open('xb') as stream:
        stream.write(raw(result) + b'\n')
    assert all(Path(link['resolved']).is_file() for link in links)
    print(json.dumps(dict(validation=bind(path), checked_files=len(checked), local_links=len(links)), indent=2))


if __name__ == '__main__':
    main()
