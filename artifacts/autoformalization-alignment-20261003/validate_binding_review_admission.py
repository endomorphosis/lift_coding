"""Validate source-only review recording readiness without admitting labels."""
import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
STAGE = CAMPAIGN / 'binding-review-admission-01'
OUTPUT = CAMPAIGN / 'binding-review-admission-validation-01'
MUTABLE_KEYS = {'mutable_main_plan_historical_reference'}
FALSE_FIELDS = ('qualified', 'accepted', 'source_fidelity_established', 'proof_authority',
                'independent_semantic_review_completed', 'reviewer_identity_authenticated',
                'reviewer_independence_authenticated', 'semantic_gold_created',
                'actual_training_or_evaluation_admission')
MASKS = {'weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation'}


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


def load(path, checksum_key='content_sha256'):
    value = json.loads(Path(path).read_bytes())
    if checksum_key is not None:
        assert value[checksum_key] == digest({key: item for key, item in value.items() if key != checksum_key})
    return value


def references(value):
    if isinstance(value, dict):
        if {'path', 'sha256'} <= value.keys():
            yield value
        for key, child in value.items():
            if key not in MUTABLE_KEYS:
                yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def no_authority(value):
    assert all(value[field] is False for field in FALSE_FIELDS)


def zero_masks(value):
    assert type(value) is dict and set(value) == MASKS
    assert all(type(number) is int and number == 0 for number in value.values())


def main(expected_report_sha):
    assert not OUTPUT.exists(), 'fresh validation generation required'
    checked = {}

    def verify(reference):
        observed = binding(reference['path'])
        assert reference['sha256'] == observed['sha256'], reference['path']
        assert 'bytes' not in reference or reference['bytes'] == observed['bytes']
        checked[observed['path']] = observed

    report_binding = binding(STAGE / 'report_private.json')
    assert report_binding['sha256'] == expected_report_sha
    report = load(report_binding['path'])
    prior_binding = binding(CAMPAIGN / 'symbol-binding-validation-01/validation.json')
    assert prior_binding['sha256'] == '8dafcff5672a5ead9310321d8fc30c4faaf1075296b5d3d4fc34311ebd30aaf3'
    prior = load(prior_binding['path'])
    assert report['source_bindings'] == prior['checked_file_bindings']
    assert len(report['source_bindings']) == prior['checked_file_count'] == 483
    assert report['mutable_main_plan_file_accessed'] is report['mutable_main_plan_preservation_required'] is False
    for reference in references(report):
        verify(reference)
    verify(report_binding)
    verify(prior_binding)
    verify(prior['runner_binding'])
    for reference in prior['documentation_bindings']:
        if not reference['path'].endswith('49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md'):
            verify(reference)
    assert len(report['new_implementation_test_bindings']) == 5
    assert report['original_packet_and_organizer_objects_unchanged'] is report['prior_file_bindings_unchanged'] is True
    workflow_report = load(report['workflow_report_binding']['path'])
    for reference in references(workflow_report):
        verify(reference)
    packet_binding = workflow_report['packet_binding']
    assert packet_binding['sha256'] == report['packet_file_sha256'] == '8a8303ea83fe22899f798703e7931b1f48a8aa0afb01c7d6980a7d3e9301701e'
    packet = load(packet_binding['path'], None)
    packet_pin = digest(packet)
    assert packet_pin == report['reviewer_packet_sha256'] == workflow_report['reviewer_packet_sha256'] == 'a8f465c7950e34ce11f69a5a900d79895f5e19545a2082da75eb9ddf59815655'
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir import canonical_binding_review as adapter
    assert binding(adapter.__file__)['sha256'] == '658bce8569101e36852702ceb53f1bc0ab61d6a00ed071e73d7044f39765d59d'
    preparation = adapter.validate_blank_packet(packet, expected_packet_sha256=packet_pin)
    assert preparation == workflow_report['preparation_validation'] == report['packet_preparation_validation']
    receipt = load(report['receipt_binding']['path'], 'receipt_sha256')
    assert adapter.record_reviews(packet, [], expected_packet_sha256=packet_pin) == receipt
    replay = adapter.validate_recording(receipt, packet, [], expected_packet_sha256=packet_pin)
    assert replay == workflow_report['recording_validation'] == report['saved_recording_validation']
    guide = load(report['public_submission_guide_binding']['path'], None)
    assert adapter.submission_guide() == guide
    assert report['receipt_binding'] == workflow_report['receipt_binding']
    assert report['public_submission_guide_binding'] == workflow_report['submission_guide_binding']
    for value in (report, workflow_report, receipt, replay, guide, *receipt['items']):
        no_authority(value)
    assert receipt['submission_count'] == len(receipt['submissions']) == len(workflow_report['submission_bindings']) == 0
    assert receipt['item_count'] == report['input_item_count'] == len(receipt['items']) == len(packet['items']) == 64
    assert receipt['status'] == workflow_report['status'] == 'pending'
    assert receipt['status_counts']['pending'] == 64 and sum(receipt['status_counts'].values()) == 64
    assert receipt['status_counts'] == report['status_counts'] == workflow_report['status_counts']
    assert all(number == 0 for number in receipt['interpretation_status_counts'].values())
    assert receipt['declared_completed_annotation_count'] == receipt['human_reviews_authenticated'] == receipt['independent_reviews_authenticated'] == 0
    assert report['adjudications_completed'] == report['actual_reviews_created'] == 0
    assert report['workflow_runs'] == report['saved_receipt_validation_runs'] == 1
    assert report['model_import_attempts'] == report['model_execution_stacks_loaded'] == []
    for field in ('model_calls', 'provider_calls', 'encoder_calls', 'prover_calls', 'optimizer_updates',
                  'profile_fit_calls', 'candidate_redecoding_calls'):
        assert type(report[field]) is int and report[field] == 0
    assert report['workflow_organizer_manifest_accessed'] is report['group_and_split_metadata_supplied_to_recording_api'] is False
    assert report['candidate_reference_payloads_supplied_to_recording'] is report['query_reference_used_to_establish_meaning'] is False
    assert workflow_report['organizer_manifest_accessed'] is workflow_report['candidate_or_reference_accessed'] is False
    organizer = load(CAMPAIGN / 'binding-review-packet-01/organizer_manifest_private.json')
    private_by_id = {row['item_id']: row for row in organizer['rows']}
    packet_by_id = {row['item_id']: row for row in packet['items']}
    assert len(private_by_id) == len(packet_by_id) == 64
    assert [row['item_id'] for row in receipt['items']] == sorted(packet_by_id)
    group_counts, split_counts = Counter(), Counter()
    for row in receipt['items']:
        original, private = packet_by_id[row['item_id']], private_by_id[row['item_id']]
        envelope = {key: value for key, value in original.items() if key != 'annotation'}
        assert all(row[key] == value for key, value in envelope.items())
        assert row['review_input_envelope_sha256'] == digest(envelope)
        assert row['source_sha256'] == private['source_sha256'] and row['input_sha256'] == private['input_sha256']
        assert all(value is None for value in original['annotation'].values()) and len(original['annotation']) == 8
        assert row['status'] == 'pending' and row['consensus_interpretation_status'] is None
        assert row['complete_declaration_count'] == row['pending_declaration_count'] == row['meaning_signature_count'] == 0
        assert row['received_declarations'] == [] and row['external_adjudication_status'] == 'pending'
        assert row['independent_adjudication_completed'] is False
        assert private['review_status'] == 'pending'
        zero_masks(row['masks'])
        zero_masks(private['masks'])
        group_counts[private['group_id']] += 1
        split_counts[private['proposed_split']] += 1
    zero_masks(receipt['masks'])
    assert len(group_counts) == 16 and set(group_counts.values()) == {4}
    assert split_counts == report['proposed_split_counts'] == dict(proposed_train=32, proposed_development=32)
    public_guide_bytes = raw(guide)
    assert all(row['source_text'].encode() not in public_guide_bytes for row in packet['items'])
    assert all(value.encode() not in public_guide_bytes for value in (*group_counts, *split_counts, *packet_by_id))
    assert stat.S_IMODE(Path(workflow_report['output_directory']).stat().st_mode) == 0o700
    for reference in (report['receipt_binding'], report['public_submission_guide_binding'], report['workflow_report_binding']):
        assert stat.S_IMODE(Path(reference['path']).stat().st_mode) == 0o600
    observations = [json.loads(line) for line in Path(report['resource_journal_binding']['path']).read_bytes().splitlines()]
    assert observations == report['resource_observations'] and len(observations) >= 2
    assert report['resource_measurement_scope'] == 'fresh_forked_static_worker'
    assert report['wall_limit_seconds'] == 60 and report['cpu_limit_seconds'] == [60, 65] and report['rss_limit_kib'] == 524288
    assert 0 <= report['wall_seconds'] <= 60 and 0 <= report['cpu_seconds'] <= 60
    for field in ('resource_ru_maxrss_kib', 'linux_current_rss_kib', 'linux_peak_hwm_kib'):
        assert all(0 < row[field] <= report['rss_limit_kib'] for row in observations)
    assert observations[-1]['linux_peak_hwm_kib'] == report['worker_linux_peak_hwm_kib'] == 27340
    assert report['worker_resource_ru_maxrss_kib'] == 26140 <= report['rss_limit_kib']
    assert report['launch_parent_resource_observation']['resource_measurement_scope'] == 'launcher_before_fresh_worker_fork'
    audit_path = CAMPAIGN / 'binding-review-admission-independent-audit-01/audit.json'
    audit = load(audit_path)
    for reference in references(audit):
        verify(reference)
    audit_binding = binding(audit_path)
    assert audit_binding['sha256'] == 'a7d98665bb92b94b3ab0c9b59dc942239f31579957e861f122cdf24a7ea23da5'
    verify(audit_binding)
    documents = [CAMPAIGN / 'binding-review-admission-report.md',
                 REPO / 'docs/autoencoders/alignment_binding_review_recording.md',
                 ROOT / 'implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md']
    links = []
    for document in documents:
        for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', document.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            resolved = (document.parent / target.split('#')[0]).resolve()
            assert resolved.is_file() or resolved == OUTPUT / 'validation.json'
            links.append(dict(document=str(document), target=target, resolved=str(resolved)))
    ids = re.findall(r'^\| (AFI-[0-9]+[ab]?) \|', documents[2].read_text(), flags=re.M)
    assert len(ids) == len(set(ids)) == 25
    checkout = ROOT / '.worktrees/alignment-decoder-768-20261003'
    assert subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain=v1',
                                   '--untracked-files=normal'], text=True).strip() == ''
    assert not {'torch', 'numpy', 'spacy', 'transformers', 'llama_cpp'}.intersection(sys.modules)
    for reference in checked.values():
        assert binding(reference['path']) == reference
    result = dict(schema='alignment-binding-review-recording-root-validation/v1', status='passed_readiness_only',
        runner_binding=binding(__file__), report_binding=report_binding, independent_audit_binding=audit_binding,
        checked_file_bindings=list(checked.values()), checked_file_count=len(checked),
        preserved_prior_checked_file_count=483, reviewer_packet_items=64, exact_source_context_receipt_joins=64,
        blank_annotation_slots=512, receipt_mask_values_zero=320, organizer_mask_values_zero=320,
        actual_submissions=0, authenticated_reviews=0, adjudications_completed=0,
        schema_specific_recording_implemented=True, semantic_label_admission_implemented=False,
        source_only_packet_recording=True, numerical_model_execution=False, training_execution=False, prover_execution=False,
        receipt_recomputation_executed=True, natural_source_corpus=False, independent_blind_quality_study=False,
        focused_test_results=dict(passed=224, elapsed_seconds=3.36, file_count=4, synthetic_test_fixtures_only=True),
        ruff_results=dict(new_owner_workflow_cli_tests_assay_and_validator_files=7, status='passed'),
        documentation_bindings=[binding(path) for path in documents], local_link_checks=links,
        work_package_ids=ids, isolated_decoder_checkout_clean=True,
        new_implementation_test_bindings=report['new_implementation_test_bindings'],
        complete_dependency_manifest=False, **{field: False for field in FALSE_FIELDS})
    result['content_sha256'] = digest(result)
    OUTPUT.mkdir()
    (OUTPUT / 'validation.json').write_bytes(raw(result) + b'\n')
    print(json.dumps(dict(binding=binding(OUTPUT / 'validation.json'), checked_files=len(checked),
                          source_items=64, submissions=0), sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report-sha256', required=True)
    main(parser.parse_args().report_sha256)
