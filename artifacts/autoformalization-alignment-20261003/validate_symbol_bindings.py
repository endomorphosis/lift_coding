"""Verify static alias filtering and unadmitted authored review envelopes."""

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
STAGE = CAMPAIGN / 'symbol-binding-recovery-02'
PACKET = CAMPAIGN / 'binding-review-packet-01'
OUTPUT = CAMPAIGN / 'symbol-binding-validation-01'
MUTABLE_PLAN_KEYS = {'mutable_main_plan_prior_reference', 'mutable_main_plan_observed_before_binding'}
FALSE = ('accepted', 'qualified', 'proof_authority', 'source_fidelity_established',
         'independent_semantic_review_completed')


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def binding(path):
    path = Path(path).resolve()
    checksum, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            checksum.update(chunk)
            size += len(chunk)
    return dict(path=str(path), bytes=size, sha256=checksum.hexdigest())


def load(path, *, sealed=True):
    value = json.loads(Path(path).read_bytes())
    if sealed:
        assert value['content_sha256'] == digest({key: item for key, item in value.items()
                                                 if key != 'content_sha256'})
    return value


def references(value):
    if isinstance(value, dict):
        if {'path', 'sha256'} <= value.keys():
            yield value
        for key, child in value.items():
            if key not in MUTABLE_PLAN_KEYS:
                yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def all_false(value):
    assert all(value[field] is False for field in FALSE if field in value)


def key_paths(value, name, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + '/' + key
            if key == name:
                yield child_path
            yield from key_paths(child, name, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from key_paths(child, name, path + '/' + str(index))


def main(expected_sha):
    assert not OUTPUT.exists(), 'fresh validation generation required'
    checked = {}

    def verify(reference):
        observed = binding(reference['path'])
        assert observed['sha256'] == reference['sha256'], reference['path']
        assert 'bytes' not in reference or observed['bytes'] == reference['bytes']
        checked[observed['path']] = observed

    report_binding = binding(STAGE / 'report.json')
    assert report_binding['sha256'] == expected_sha
    report = load(report_binding['path'])
    prior = load(CAMPAIGN / 'typed-anchor-decoder-validation-01/validation.json')
    assert report['source_bindings'] == prior['checked_file_bindings']
    assert len(report['source_bindings']) == prior['checked_file_count'] == 444
    assert report['mutable_main_plan_preservation_required'] is False
    for reference in references(report):
        verify(reference)
    verify(report_binding)
    profile = load(report['profile_binding']['path'])
    requests = load(CAMPAIGN / 'typed-anchor-decoder-recovery-01/inference_requests.json')['rows']
    outcomes = load(CAMPAIGN / 'canonical-codec-01/all_request_outcomes.json')['rows']
    train = load(CAMPAIGN / 'canonical-codec-01/train_weak_supervision.json')['rows']
    requests_by_id, metadata_by_id = ({row['id']: row for row in rows} for rows in (requests, outcomes))
    examples = [{'id': row['id'], 'source_text': requests_by_id[row['id']]['source_text'],
                 'proposal': row['proposal']} for row in train]
    assert len(examples) == 16 and len({metadata_by_id[row['id']]['group_id'] for row in examples}) == 4
    assert all(metadata_by_id[row['id']]['split'] == 'train' for row in examples)
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir import canonical_symbol_bindings as gate
    assert binding(gate.__file__)['sha256'] == '7a46a2488ee37621bdebc6d4521e3eb8160c7eaeaf66ffb2b59cff016c7c8a7a'
    assert gate.fit_profile(examples) == profile
    pin = profile['content_sha256']
    assert pin == report['profile_content_sha256'] == 'b2f897a33ca3e7c43b2879db4abb651653dedab587bc6f94364a6bd80bb06324'
    assert gate.validate_profile(profile, expected_profile_sha256=pin) == profile
    assert (profile['training_pair_count'], profile['training_anchor_count'],
            profile['alias_entry_count'], profile['ambiguous_alias_count']) == (16, 124, 20, 0)
    assert profile['training_manifest_sha256'] == digest(examples)
    primary, repeats, primary_by_role = [], [], {}
    recomputations = 0
    for spec in report['assessment_records']:
        record = load(spec['assessment_binding']['path'])
        original = load(spec['original_generation_binding']['path'])
        all_false(record)
        assert len(record['rows']) == len(original['rows']) == len(requests) == 34
        for row, original_row, request in zip(record['rows'], original['rows'], requests, strict=True):
            position = row['position']
            assert row['id'] == original_row['id'] == request['id'] and request == requests[position]
            assert row['source_sha256'] == hashlib.sha256(request['source_text'].encode()).hexdigest()
            assert row['context_sha256'] == hashlib.sha256(request['context_text'].encode()).hexdigest()
            assert row['request_sha256'] == digest(request)
            assert row['original_generation_row_sha256'] == digest(original_row)
            assert row['original_generation_outcome'] == original_row['outcome']
            assert row['candidate_unchanged'] is True and row['canonical_ir_repaired'] is False
            assert row['query_reference_accessed'] is False
            metadata = metadata_by_id[row['id']]
            assert all(row[field] == metadata[field] for field in ('split', 'group_id', 'row_kind', 'review_status'))
            assert row['review_status'] == 'pending'
            all_false(row)
            proposal = original_row.get('proposal')
            if proposal is None:
                assert row['binding_outcome'] == 'binding_unavailable' and row['assessment'] is None
                assert row['candidate_proposal_sha256'] is row['output_proposal'] is None
                assert row['binding_unavailable_reason'] is not None and row['candidate_output_withheld'] is False
            else:
                assessment = gate.assess_bindings(request['source_text'], proposal, profile,
                                                 expected_profile_sha256=pin)
                assert assessment == row['assessment']
                assert gate.validate_bindings(assessment, request['source_text'], proposal, profile,
                                              expected_profile_sha256=pin) == assessment
                assert row['candidate_proposal_sha256'] == digest(proposal)
                assert row['binding_outcome'] == assessment['outcome'] and row['binding_unavailable_reason'] is None
                withheld = assessment['outcome'] == 'binding_inconsistent'
                assert row['candidate_output_withheld'] is withheld
                assert row['output_proposal'] == (None if withheld else proposal)
                all_false(assessment)
                recomputations += 1
        role = (spec['seed'], spec['role'])
        if spec['is_private_repeat']:
            assert record['rows'] == primary_by_role[role]['rows']
            assert record['counts'] == primary_by_role[role]['counts']
            assert spec['private_repeat_exact_row_json_equal_primary'] is True
            repeats.extend(record['rows'])
        else:
            primary_by_role[role] = record
            primary.extend(record['rows'])
        assert spec['counts'] == record['counts']
        assert Counter(row['binding_outcome'] for row in record['rows']) == record['counts']['binding_outcome_counts']
    assert len(primary) == 408 and len(repeats) == 102 and recomputations == 98
    for rows, counts, expected in ((primary, report['primary_counts'], (48, 1, 359)),
                                   (repeats, report['private_repeat_counts'], (48, 1, 53))):
        assert counts['row_count'] == len(rows)
        assert Counter(row['binding_outcome'] for row in rows) == dict(zip(
            ('binding_consistent', 'binding_inconsistent', 'binding_unavailable'), expected, strict=True))
        assert counts['original_full_proposal_count'] == 49 and counts['candidate_output_withheld_count'] == 1
        assert counts['candidate_output_available_count'] == 48
    contradictions = [row for row in primary if row['binding_outcome'] == 'binding_inconsistent']
    assert len(contradictions) == 1
    leaves = [leaf for leaf in contradictions[0]['assessment']['leaves'] if leaf['outcome'] == 'known_alias_mismatch']
    assert {(leaf['facet'], leaf['claimed_symbol'], tuple(leaf['recognized_symbols'])) for leaf in leaves} == {
        ('action', 'notify', ('retain',)), ('object', 'applicant', ('filing',))}
    assert report['query_reference_accessed'] is report['development_weak_proposal_accessed'] is False
    assert report['development_reference_ir_accessed'] is report['weak_gold_comparison_performed'] is False
    assert report['model_import_attempts'] == report['model_execution_stacks_loaded'] == []
    assert report['accepted_output_rows'] == report['qualified_output_rows'] == report['independently_reviewed_fidelity_rows'] == 0
    assert report['observed_calls'] == dict(candidate_redecoding=0, encoder=0, model=0,
        optimizer_updates=0, primary_assessments=49, private_repeat_assessments=49,
        profile_fitting=0, prover=0, saved_assessment_validation_recomputations=98)
    assert report['original_completed_profile_fit_calls'] == 1 and report['recovery_profile_fit_calls'] == 0
    assert report['profile_frozen_before_candidate_body_access'] is True
    assert report['resource_measurement_scope'] == 'fresh_forked_static_worker'
    assert report['max_rss_kib'] == 512 * 1024 and report['max_seconds'] == 60
    assert report['cpu_limit_seconds'] == [60, 65]
    assert 0 <= report['wall_seconds'] <= 60 and 0 <= report['cpu_seconds'] <= 60
    observations = [json.loads(line) for line in Path(report['resource_journal_binding']['path']).read_bytes().splitlines()]
    assert observations == report['resource_observations'] and len(observations) == 111
    assert observations[0]['label'] == 'initial_resource_baseline'
    assert observations[-1]['label'] == 'final_resource_observation'
    for field in ('resource_ru_maxrss_kib', 'linux_current_rss_kib', 'linux_peak_hwm_kib'):
        assert all(0 < observation[field] <= report['max_rss_kib'] for observation in observations)
    assert max(row['resource_ru_maxrss_kib'] for row in observations) == report['peak_rss_kib'] == 30260
    assert observations[-1]['linux_current_rss_kib'] == report['linux_current_rss_kib_at_final_observation'] == 30760
    assert max(row['linux_peak_hwm_kib'] for row in observations) == report['linux_peak_hwm_kib_at_final_observation'] == 30760
    assert report['launch_parent_resource_observation']['resource_measurement_scope'] == 'launcher_before_fresh_worker_fork'
    failed = report['failed_attempt']
    assert failed['profile_fit_calls'] == 1 and failed['observed_failed_peak_rss_kib'] is None
    assert failed['failure_cause'] == 'unknown' and failed['candidate_body_reads'] == failed['gate_assessment_calls'] == 0
    stopped = report['failed_recovery_attempt']
    stopped_journal = [json.loads(line) for line in Path(
        report['interrupted_recovery_stage_bindings'][0]['path']).read_bytes().splitlines()]
    assert stopped_journal == [stopped['resource_observation']]
    assert stopped['profile_fit_calls'] == stopped['candidate_body_reads'] == stopped['gate_assessment_calls'] == 0
    assert stopped['underlying_cause'] == 'not_independently_established'
    assert stopped['resource_observation']['resource_ru_maxrss_kib'] == 1719700 > report['max_rss_kib']
    assert stopped['resource_observation']['linux_current_rss_kib'] == stopped['resource_observation']['linux_peak_hwm_kib'] == 18736
    scope_path = STAGE / 'provenance_scope_addendum.json'
    assert binding(scope_path)['sha256'] == '3173403dd858dec8788b611e67e190f4e99ed8164e2a466a48e66dc299fddf4b'
    scope = load(scope_path)
    for reference in references(scope):
        verify(reference)
    scope_binding = binding(scope_path)
    verify(scope_binding)
    assert scope['report_binding'] == report_binding and scope['profile_content_sha256'] == pin
    historical_paths = list(key_paths(prior, 'weak_reference_rule'))
    assert historical_paths == scope['historical_weak_reference_field_paths'] == [
        '/exact_span_wrong_symbol_weak_counterexamples/0/weak_reference_rule']
    assert scope['historical_weak_reference_value_count'] == 1
    assert scope['historical_weak_reference_values_present_in_parsed_json'] is True
    assert scope['profile_frozen_before_prior_validation_json_parsing'] is True
    for field in ('algorithmic_query_reference_use', 'historical_weak_reference_values_supplied_to_profile_fitting',
                  'historical_weak_reference_values_supplied_to_assess_bindings',
                  'historical_weak_reference_values_consumed_by_withholding_policy', 'independent_blind_quality_study',
                  'independent_fidelity_evaluation_performed', 'frozen_report_or_runner_modified', 'gate_decisions_modified'):
        assert scope[field] is False
    assert scope['additional_gate_assessment_calls'] == scope['additional_profile_fit_calls'] == 0
    all_false(scope)
    all_false(report)
    packet_binding = binding(PACKET / 'report.json')
    assert packet_binding['sha256'] == '9c6bd0ee725f052da98a0b3f31fc83c9c361a869ced9c088a32fc3b259d82ce1'
    packet = load(packet_binding['path'])
    for reference in references(packet):
        verify(reference)
    verify(packet_binding)
    packet_plan = load(packet['plan_binding']['path'])
    public = load(packet['reviewer_payload_binding']['path'], sealed=False)
    private = load(packet['organizer_manifest_binding']['path'])
    manifest = load(packet['reviewer_manifest_binding']['path'])
    spec = importlib.util.spec_from_file_location('frozen_review_preparer', packet['runner_binding']['path'])
    authoring = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(authoring)
    public_by_id = {row['item_id']: row for row in public['items']}
    assert len(public_by_id) == len(public['items']) == len(private['rows']) == 64
    assert len({row['source_sha256'] for row in public['items']}) == 64
    assert manifest['candidate_reference_blind'] is manifest['split_and_group_blind'] is True
    assert packet['natural_source_corpus'] is packet['actual_training_or_evaluation_admission'] is False
    assert packet['semantic_gold_created'] is packet['existing_review_admission_adapter_compatible'] is False
    group_counts, split_counts = Counter(), Counter()
    for row in private['rows']:
        _, actor_index, pair_index = row['group_id'].rsplit(':', 2)
        actor_index, pair_index = int(actor_index), int(pair_index)
        actor = authoring.ACTORS[actor_index]
        action, object_text = authoring.ACTION_OBJECT_PAIRS[pair_index]
        expected_source = authoring.TEMPLATES[row['variant_index']].format(actor=actor, action=action, object=object_text)
        expected_split = 'proposed_train' if (actor_index - pair_index) % 4 in (0, 1) else 'proposed_development'
        assert row['proposed_split'] == expected_split and row['review_status'] == 'pending'
        assert all(value == 0 for value in row['masks'].values())
        item = public_by_id[row['item_id']]
        assert set(item) == {'item_id', 'source_text', 'source_sha256', 'input_sha256', 'context', 'annotation'}
        assert item['source_text'] == expected_source
        assert item['source_sha256'] == row['source_sha256'] == hashlib.sha256(expected_source.encode()).hexdigest()
        assert item['context'] == dict(role='none_required', text='', bindings={}, sha256=hashlib.sha256(b'').hexdigest())
        assert item['input_sha256'] == row['input_sha256'] == digest(dict(source_text=expected_source, context=item['context']))
        expected_id = 'binding-review-item-' + hashlib.sha256(
            b'authored-binding-review-v1\0' + bytes.fromhex(item['input_sha256'])).hexdigest()[:24]
        assert item['item_id'] == expected_id and set(item['annotation']) == set(authoring.ANNOTATION_FIELDS)
        assert all(value is None for value in item['annotation'].values())
        group_counts[row['group_id']] += 1
        split_counts[row['proposed_split']] += 1
    assert len(group_counts) == 16 and set(group_counts.values()) == {4}
    assert split_counts == packet['proposed_split_counts'] == packet_plan['proposed_split_counts'] == dict(
        proposed_train=32, proposed_development=32)
    old_source_hashes = {hashlib.sha256(row['source_text'].encode()).hexdigest() for row in requests}
    assert old_source_hashes.isdisjoint({row['source_sha256'] for row in public['items']})
    audit_path = CAMPAIGN / 'symbol-binding-independent-audit-01/audit.json'
    audit = load(audit_path)
    for reference in references(audit):
        verify(reference)
    audit_binding = binding(audit_path)
    assert audit_binding['sha256'] == '88fe2f7de08334242af24fc258bdda6feb4167a83901241f2b12fc960928c47f'
    verify(audit_binding)
    audit_scope_path = audit_path.with_name('provenance_scope_audit_addendum.json')
    audit_scope_binding = binding(audit_scope_path)
    assert audit_scope_binding['sha256'] == 'c22547fa51e8d6a9cb0548e37cfe5a54f63fe7450563e6cd671706cd5f2d6ff7'
    audit_scope = load(audit_scope_path)
    for reference in references(audit_scope):
        verify(reference)
    verify(audit_scope_binding)
    assert audit_scope['frozen_original_audit_binding'] == audit_binding
    assert audit_scope['assay_provenance_scope_addendum_binding'] == scope_binding
    assert audit_scope['historical_metadata_weak_reference_paths'] == historical_paths
    assert audit_scope['historical_metadata_weak_reference_value_count'] == 1
    assert audit_scope['query_reference_comparisons'] == 0 and audit_scope['algorithmic_query_reference_use'] is False
    assert audit_scope['metadata_deserialization_occurred'] is True
    assert audit_scope['original_assessment_counts_and_filters_unchanged'] is True
    all_false(audit_scope)
    documents = [CAMPAIGN / 'symbol-binding-report.md',
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
    assert not {'torch', 'numpy', 'spacy', 'transformers', 'llama_cpp'}.intersection(sys.modules)
    for reference in checked.values():
        assert binding(reference['path']) == reference
    result = dict(schema='alignment-static-bindings-and-review-packet-validation/v1', status='passed_unqualified',
        runner_binding=binding(__file__), report_binding=report_binding, review_packet_report_binding=packet_binding,
        checked_file_bindings=list(checked.values()), checked_file_count=len(checked),
        preserved_prior_checked_file_count=444, original_candidate_receipt_slots=510,
        primary_candidate_count=49, primary_consistent_candidates=48, primary_contradictions_withheld=1,
        private_repeat_comparisons=3, binding_assessment_recomputations=98, profile_aliases=20,
        profile_training_anchor_observations=124, authored_review_items=64, authored_source_groups=16,
        new_reviews_completed=0, all_new_fit_and_evaluation_masks_zero=True,
        independent_readonly_audit_binding=audit_binding,
        provenance_scope_addendum_binding=scope_binding, independent_provenance_audit_addendum_binding=audit_scope_binding,
        historical_weak_reference_metadata_deserialized=True, historical_weak_reference_metadata_value_count=1,
        algorithmic_query_reference_use=False, independent_blind_quality_study=False,
        worker_resource_observations=111, worker_resource_ru_maxrss_kib=30260, worker_linux_peak_hwm_kib=30760,
        worker_rss_limit_kib=524288, failed_attempts_preserved=2,
        new_implementation_test_bindings=[binding(REPO / relative) for relative in (
            'ipfs_datasets_py/logic/legal_ir/canonical_symbol_bindings.py',
            'tests/unit/logic/legal_ir/test_canonical_symbol_bindings.py')],
        focused_test_results=dict(passed=613, elapsed_seconds=6.03,
            cpu_environment=dict(CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'),
            initial_unisolated_attempt=dict(passed=599, setup_errors=14, reason='CUDA allocation failure in CPU fixture optimizer health check')),
        ruff_results=dict(implementation_test_assay_recovery_review_preparer_and_validator_files=7, status='passed'),
        documentation_bindings=[binding(path) for path in documents], local_link_checks=links,
        work_package_ids=ids, isolated_decoder_checkout_clean=True, model_execution=False,
        neural_training_execution=False, prover_execution=False,
        alias_profile_reaggregation_executed=True, validation_scope='saved_static_receipts_not_numeric_generation_or_semantic_review',
        complete_dependency_manifest=False, **{field: False for field in FALSE})
    result['content_sha256'] = digest(result)
    OUTPUT.mkdir()
    (OUTPUT / 'validation.json').write_bytes(raw(result) + b'\n')
    print(json.dumps(dict(binding=binding(OUTPUT / 'validation.json'), checked_files=len(checked),
                          checked_receipt_rows=510, review_items=64), sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report-sha256', required=True)
    main(parser.parse_args().report_sha256)
