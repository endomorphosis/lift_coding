"""Bounded deterministic source grounding and retained-decoder transport assay.

This development runner constructs all source proposals before reading the
authored reference panel. It never loads a learned model or selects a decoder.
"""
import hashlib
import json
import resource
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
OUTPUT = CAMPAIGN / 'grounding-01'
MAX_SECONDS = 120
MAX_RSS_KIB = 1024 * 1024
BLOCKED_STACKS = frozenset({
    'torch', 'tensorflow', 'jax', 'transformers', 'sentence_transformers',
    'spacy', 'sklearn', 'numpy', 'llama_cpp',
})
FALSE_FLAGS = {
    'qualified': False, 'proof_authority': False,
    'source_fidelity_established': False, 'independent_semantic_review_completed': False,
}


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def bind(path):
    path = Path(path)
    checksum = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            checksum.update(chunk)
            size += len(chunk)
    return {'path': str(path), 'bytes': size, 'sha256': checksum.hexdigest()}


def verify(ref):
    current = bind(ref['path'])
    assert current['sha256'] == ref['sha256'], ref['path']
    if 'bytes' in ref:
        assert current['bytes'] == ref['bytes'], ref['path']
    return current


def load(path):
    return json.loads(Path(path).read_bytes())


def verify_payload(value, key='content_sha256'):
    assert value[key] == digest({k: v for k, v in value.items() if k != key})


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    return bind(path)


def seal(value):
    return {**value, 'content_sha256': digest(value)}


def loaded_repository_sources():
    paths = set()
    for module in tuple(sys.modules.values()):
        raw = getattr(module, '__file__', None)
        if raw is None:
            continue
        path = Path(raw).resolve()
        if path.suffix == '.py' and path.is_relative_to(REPO):
            paths.add(path)
    return [bind(path) for path in sorted(paths)]


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (60, 65))

    def admission():
        assert time.monotonic() - started < MAX_SECONDS, 'wall budget exceeded'
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < MAX_RSS_KIB, 'RSS budget exceeded'

    class NoModelStacks:
        attempts = []

        def find_spec(self, fullname, path=None, target=None):
            if fullname.partition('.')[0] in BLOCKED_STACKS:
                self.attempts.append(fullname)
                raise ImportError(f'model/numerical stack forbidden in deterministic assay: {fullname}')
            return None

    guard = NoModelStacks()
    sys.meta_path.insert(0, guard)
    assert not BLOCKED_STACKS.intersection(sys.modules), 'worker must start without ML stacks'

    numerical_validation_path = CAMPAIGN / 'decoder-replay-01/validation.json'
    prior_validation_path = CAMPAIGN / 'decoder-replay-02/validation.json'
    prior = load(prior_validation_path)
    verify_payload(prior)
    assert prior['status'] == 'passed_unqualified' and prior['numerical_evidence_preserved'] is True
    verify(prior['numerical_validation_binding'])
    assert Path(prior['numerical_validation_binding']['path']) == numerical_validation_path
    numerical_validation = load(numerical_validation_path)
    verify_payload(numerical_validation)
    prior_bindings = numerical_validation['checked_file_bindings']
    assert len(prior_bindings) == 245
    preserved = [verify(ref) for ref in prior_bindings]

    input_paths = {
        'source_inputs': CAMPAIGN / 'richer-embedding-01/embedding_inputs.json',
        'declared_context_inputs': CAMPAIGN / 'context-02/context_inputs.json',
        'training_vocabulary_metadata': CAMPAIGN / 'parser-01/report.json',
        'prior_numerical_validation': numerical_validation_path,
        'prior_documentation_validation': prior_validation_path,
        'source_span_report': CAMPAIGN / 'span-replay-01/report.json',
        'sidecar_report': CAMPAIGN / 'sidecar-replay-01/report.json',
    }
    inputs = load(input_paths['source_inputs'])
    contexts = load(input_paths['declared_context_inputs'])
    vocabulary_metadata = load(input_paths['training_vocabulary_metadata'])
    verify_payload(inputs, 'payload_sha256')
    verify_payload(contexts, 'payload_sha256')
    verify_payload(vocabulary_metadata, 'report_sha256')
    assert inputs['input_recipe'] == 'exact_source_only'
    assert inputs['row_count'] == len(inputs['rows']) == 34
    assert inputs['all_context_unapplied'] is True
    assert contexts['original_row_count'] == 34 and contexts['row_count'] == len(contexts['rows']) == 68
    assert contexts['context_resolved'] is False and contexts['context_semantics_applied'] is False
    vocabulary = vocabulary_metadata['training_vocabulary']
    vocabulary_sha256 = vocabulary_metadata['training_vocabulary_sha256']
    assert digest(vocabulary) == vocabulary_sha256
    assert vocabulary_metadata['development_used_in_vocabulary_fit'] is False
    assert vocabulary_metadata['query_targets_used_in_construction'] is False
    assert set(vocabulary) == {'actors', 'actions', 'objects', 'qualifiers'}

    sidecar_report = load(input_paths['sidecar_report'])
    span_report = load(input_paths['source_span_report'])
    verify_payload(sidecar_report)
    verify_payload(span_report)
    selected_checkpoint_ref = sidecar_report['inputs']['selected']
    verify(selected_checkpoint_ref)
    # Read bounded saved state metadata only. No tensor is restored or executed.
    selected_checkpoint = load(selected_checkpoint_ref['path'])
    assert selected_checkpoint['dimension'] == 768
    codec_tokens = selected_checkpoint['codec']['target_vocabulary']
    assert codec_tokens[:3] == ['<pad>', '<bos>', '<eos>'] and len(codec_tokens) == 32
    del selected_checkpoint
    input_bindings = {key: bind(path) for key, path in input_paths.items()}
    input_bindings['retained_fixed_codec_selected_checkpoint'] = selected_checkpoint_ref

    declared = [row for row in contexts['rows'] if row['arm_id'] == 'declared_context']
    assert len(declared) == 34
    by_original_id = {row['original_input_sha256']: row for row in declared}
    assert len(by_original_id) == 34
    assert set(by_original_id) == {row['input_sha256'] for row in inputs['rows']}
    request_rows = []
    for row in inputs['rows']:
        assert set(row) == {'id', 'input_sha256', 'source_text', 'source_sha256',
                            'context_role', 'context_applied'}
        assert row['id'] == 'sha256:' + row['input_sha256']
        assert row['source_sha256'] == hashlib.sha256(row['source_text'].encode()).hexdigest()
        assert row['context_applied'] is False
        context_row = by_original_id[row['input_sha256']]
        assert context_row['source_text'] == row['source_text']
        assert context_row['source_sha256'] == row['source_sha256']
        assert context_row['context']['role'] == row['context_role']
        assert context_row['context_semantics_applied'] is False
        assert context_row['encoder_text_sha256'] == hashlib.sha256(context_row['encoder_text'].encode()).hexdigest()
        frame = json.loads(context_row['encoder_text'])
        assert frame['source'] == {'role': 'source', 'text': row['source_text']}
        context = context_row['context']
        assert set(context) == {'role', 'text', 'sha256', 'bindings'}
        assert context['sha256'] == hashlib.sha256(context['text'].encode()).hexdigest()
        assert frame['assumptions'] == {'role': 'declared_assumptions', 'text': context['text'],
                                         'bindings': context['bindings']}
        assert context['role'] in ('none_required', 'explicit_assumptions')
        requires_context = context['role'] == 'explicit_assumptions'
        assert context_row['context_forwarded'] is requires_context
        if not requires_context:
            assert context['text'] == '' and context['bindings'] == {}
        else:
            assert context['text'].strip() and context['bindings']
        request_rows.append({**row, 'declared_context': context,
                             'declared_context_transport_id': context_row['transport_id'],
                             'requires_context_resolution': requires_context,
                             'context_semantics_applied': False})
    assert sum(row['requires_context_resolution'] for row in request_rows) == 2

    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir.canonical_contracts import CompilerRequest
    from ipfs_datasets_py.logic.legal_ir.canonical_decoder_preflight import (
        analyze_decoder_source,
        validate_decoder_preflight,
    )
    from ipfs_datasets_py.logic.legal_ir.canonical_source_grounding import (
        DECODER_PROFILES,
        assess_decoder_transport,
        construct_grounded_source,
        validate_decoder_transport,
        validate_grounded_source,
    )
    mandatory_owner_paths = [
        REPO / 'ipfs_datasets_py/logic/legal_ir' / name
        for name in ('canonical_decoder_preflight.py', 'canonical_source_grounding.py',
                     'canonical_explicit_qualifiers.py', 'canonical_contracts.py',
                     'canonical_source_guards.py')
    ]
    owners = [bind(path) for path in mandatory_owner_paths]
    loaded_before = loaded_repository_sources()
    runner_binding = bind(__file__)
    admission()
    OUTPUT.mkdir(exist_ok=False)
    manifest = seal({
        'schema': 'alignment-source-grounding-request-manifest/v1',
        'input_bindings': input_bindings, 'rows': request_rows, 'row_count': 34,
        'source_construction_recipe': 'exact_source_and_declared_unresolved_context/v1',
        'vocabulary': vocabulary, 'vocabulary_sha256': vocabulary_sha256,
        'vocabulary_provenance': 'frozen_parser_01_TRAIN_supervised_atom_vocabulary',
        'vocabulary_fit_development_used': False,
        'grammar_design_used_exposed_development': vocabulary_metadata['development_used_to_design_grammar'],
        'decoder_profiles': list(DECODER_PROFILES),
        'fixed_codec_vocabulary': codec_tokens, 'fixed_codec_vocabulary_sha256': digest(codec_tokens),
        'fixed_codec_output_cap': 512, 'implementation_bindings': owners,
        'loaded_repository_sources_before': loaded_before, 'runner_binding': runner_binding,
        'prior_unchanged_checked_file_count': len(preserved),
        'targets_used_in_construction': False, 'authored_panel_semantics_read': False,
        'context_resolution_executed': False, 'complete_dependency_manifest': False, **FALSE_FLAGS,
    })
    manifest_binding = save(OUTPUT / 'request_manifest.json', manifest)

    receipts = []
    for row in request_rows:
        admission()
        preflight = analyze_decoder_source(
            row['source_text'], context_text=row['declared_context']['text'],
            requires_context_resolution=row['requires_context_resolution'])
        validate_decoder_preflight(preflight)
        grounding = construct_grounded_source(
            CompilerRequest(row['source_text'], row['id'], vocabulary),
            context_text=row['declared_context']['text'],
            requires_context_resolution=row['requires_context_resolution'])
        validate_grounded_source(grounding)
        assert grounding['preflight'] == preflight
        assert grounding['context_applied'] is False
        transports = []
        for profile in DECODER_PROFILES:
            tokens = codec_tokens if profile == DECODER_PROFILES[1] else None
            transport = assess_decoder_transport(grounding, decoder_profile=profile,
                                                 codec_tokens=tokens, output_cap=512)
            validate_decoder_transport(transport, grounding, codec_tokens=tokens)
            transports.append(transport)
        receipts.append({'id': row['id'], 'input_sha256': row['input_sha256'],
                         'source_sha256': row['source_sha256'],
                         'context_sha256': row['declared_context']['sha256'],
                         'preflight': preflight, 'grounding': grounding, 'transports': transports})
    construction_binding = save(OUTPUT / 'constructed_receipts.json', seal({
        'schema': 'alignment-source-grounding-construction/v1', 'rows': receipts, 'row_count': 34,
        'request_manifest_binding': manifest_binding, 'targets_used_in_construction': False,
        'authored_panel_semantics_read': False, 'learned_decoder_executed': False,
        'context_resolution_executed': False, **FALSE_FLAGS,
    }))
    # Source construction and all static transports are now complete and saved.
    construction_finished_seconds = time.monotonic() - started
    panel_path = CAMPAIGN / 'richer-01/panel.json'
    panel_binding = bind(panel_path)
    panel = load(panel_path)
    panel_by_input = {row['input_sha256']: row for row in panel['rows']}
    assert len(panel_by_input) == len(panel['rows']) == 34
    assert set(panel_by_input) == {row['input_sha256'] for row in request_rows}
    diagnostic_rows = []
    for row, receipt in zip(request_rows, receipts, strict=True):
        authored = panel_by_input[row['input_sha256']]
        assert authored['source_sha256'] == row['source_sha256']
        assert authored['source_text'] == row['source_text']
        assert authored['context'] == row['declared_context']
        grounded_ir = receipt['grounding']['canonical_ir']
        diagnostic_rows.append({
            'id': row['id'], 'input_sha256': row['input_sha256'],
            'authored_panel_id': authored['id'], 'authored_row_kind': authored['row_kind'],
            'authored_split': authored['split'], 'grounding_outcome': receipt['grounding']['outcome'],
            'preflight_outcome': receipt['preflight']['outcome'],
            'authored_target_sha256': authored['target_sha256'],
            'exact_authored_reference_agreement': None if grounded_ir is None or authored['target'] is None
            else grounded_ir == authored['target'],
            'review_status': authored['provenance']['review_status'],
            'reference_used_for_construction': False, 'independent_fidelity_score': False,
            **FALSE_FLAGS,
        })
    diagnostic_binding = save(OUTPUT / 'posthoc_authored_diagnostics.json', seal({
        'schema': 'alignment-source-grounding-posthoc-authored-diagnostics/v1',
        'panel_binding': panel_binding, 'rows': diagnostic_rows, 'row_count': 34,
        'construction_binding': construction_binding,
        'reference_access_after_all_source_construction_completed': True,
        'role': 'exposed_authored_unreviewed_development_diagnostic', **FALSE_FLAGS,
    }))

    overlays = []
    old_output_bindings = []
    for run in span_report['runs']:
        output_ref = run['output_bindings']['none']
        verify(output_ref)
        old_output_bindings.append(output_ref)
        previous = load(output_ref['path'])
        assert len(previous['rows']) == 34
        overlay_rows = []
        for row, receipt, old in zip(request_rows, receipts, previous['rows'], strict=True):
            assert old['source_sha256'] == row['source_sha256']
            blocked = receipt['preflight']['outcome'] != 'unassessed'
            overlay_rows.append({
                'id': row['id'], 'input_sha256': row['input_sha256'],
                'source_sha256': row['source_sha256'], 'previous_decoder_status': old['status'],
                'previous_decoder_reason': old['reason'],
                'preflight_outcome': receipt['preflight']['outcome'],
                'preflight_diagnostic_codes': [item['code'] for item in receipt['preflight']['diagnostics']],
                'associated_with_preflight_block': blocked,
                'previously_decoded_and_associated_with_preflight_block': old['status'] == 'decoded' and blocked,
                'acceptance_decision': None, 'generated_candidate_semantics_assessed': False,
            })
        overlays.append({
            'seed': run['seed'], 'checkpoint_role': run['role'], 'control': 'none',
            'old_output_binding': output_ref, 'rows': overlay_rows, 'row_count': 34,
            'previous_decoded_count': sum(row['previous_decoder_status'] == 'decoded' for row in overlay_rows),
            'previously_decoded_and_associated_with_preflight_block_count': sum(
                row['previously_decoded_and_associated_with_preflight_block'] for row in overlay_rows),
            'previously_decoded_and_unassessed_count': sum(
                row['previous_decoder_status'] == 'decoded' and not row['associated_with_preflight_block']
                for row in overlay_rows),
            'unassessed_rows_counted_as_accepted': 0,
        })
    assert len(overlays) == 9
    overlay_binding = save(OUTPUT / 'posthoc_source_span_overlay.json', seal({
        'schema': 'alignment-source-grounding-source-span-posthoc-overlay/v1',
        'rows_per_state': 34, 'states': overlays,
        'overlay_scope': 'associate_saved_source_only_outputs_with_new_source_context_warnings',
        'old_outputs_modified': False, 'decoder_reexecuted': False,
        'generated_candidate_semantics_assessed': False,
        'unassessed_rows_counted_as_accepted': 0, **FALSE_FLAGS,
    }))

    transport_summaries = {}
    for index, profile in enumerate(DECODER_PROFILES):
        transport_summaries[profile] = {
            'denominator': 34,
            'outcomes': dict(Counter(row['transports'][index]['outcome'] for row in receipts)),
            'issue_codes': dict(Counter(issue['code'] for row in receipts
                                        for issue in row['transports'][index]['issues'])),
            'static_source_proposal_transport_only': True,
            'learned_decoder_quality_assessed': False, 'candidate_acceptance_decisions': 0,
        }
    grounded = [row for row in receipts if row['grounding']['outcome'] == 'grounded_candidate']
    anchors = [anchor for row in grounded for anchor in row['grounding']['anchors']]
    for row in grounded:
        source = row['grounding']['request']['source_text']
        for anchor in row['grounding']['anchors']:
            assert source[anchor['start']:anchor['end']] == anchor['source_text']
    anchor_count_by_facet = dict(Counter(anchor['facet'] for anchor in anchors))
    posthoc_exact = sum(row['exact_authored_reference_agreement'] is True for row in diagnostic_rows)
    posthoc_comparable = sum(row['exact_authored_reference_agreement'] is not None for row in diagnostic_rows)
    review_counts = dict(Counter(row['review_status'] for row in diagnostic_rows))

    rechecked = [verify(ref) for ref in preserved]
    for ref in list(input_bindings.values()) + owners + loaded_before + old_output_bindings + [runner_binding, panel_binding]:
        verify(ref)
    loaded_after = loaded_repository_sources()
    for ref in loaded_after:
        if ref['path'] in {item['path'] for item in loaded_before}:
            assert ref in loaded_before
    assert not BLOCKED_STACKS.intersection(sys.modules), 'ML stack was loaded'
    admission()
    report = seal({
        'schema': 'alignment-source-grounding-development-report/v1',
        'status': 'completed_unqualified', 'row_count': 34,
        'source_input_recipe': 'exact_source_with_declared_context_retained_unresolved',
        'input_bindings': input_bindings, 'runner_binding': runner_binding,
        'request_manifest_binding': manifest_binding, 'construction_binding': construction_binding,
        'posthoc_authored_diagnostics_binding': diagnostic_binding,
        'posthoc_source_span_overlay_binding': overlay_binding,
        'implementation_bindings': owners, 'loaded_repository_sources': loaded_after,
        'complete_dependency_manifest': False,
        'dependency_binding_scope': 'five_owner_files_and_observed_imported_repository_python_sources',
        'prior_numerical_evidence_preserved': True,
        'prior_unchanged_checked_file_count': len(rechecked),
        'prior_checked_bindings': rechecked,
        'preflight_outcomes': dict(Counter(row['preflight']['outcome'] for row in receipts)),
        'source_warning_rows': sum(bool(row['preflight']['diagnostics']) for row in receipts),
        'source_warning_codes': dict(Counter(item['code'] for row in receipts
                                           for item in row['preflight']['diagnostics'])),
        'grounding_outcomes': dict(Counter(row['grounding']['outcome'] for row in receipts)),
        'grounded_candidate_count': len(grounded), 'source_anchor_count': len(anchors),
        'source_anchor_count_by_facet': anchor_count_by_facet,
        'anchor_coverage_verified_by_complete_grounding_validator': True,
        'transport_summaries': transport_summaries,
        'declared_context_rows': 2, 'context_retained': True, 'context_resolved': False,
        'context_semantics_applied': False,
        'vocabulary_sha256': vocabulary_sha256,
        'vocabulary_provenance': 'frozen_parser_01_TRAIN_supervised_atom_vocabulary',
        'grammar_design_used_exposed_development': vocabulary_metadata['development_used_to_design_grammar'],
        'targets_used_in_construction': False,
        'authored_reference_access_after_source_construction_finished': True,
        'authored_reference_exact_agreement_count': posthoc_exact,
        'authored_reference_comparable_candidate_count': posthoc_comparable,
        'authored_reference_all_row_denominator': 34,
        'authored_reference_role': 'posthoc_synthetic_unreviewed_development_diagnostic',
        'review_status_counts': review_counts,
        'source_span_overlay': [
            {key: value for key, value in row.items() if key not in ('rows', 'old_output_binding')}
            for row in overlays],
        'candidate_acceptance_decisions': 0, 'unassessed_rows_counted_as_accepted': 0,
        'calls': {'models': 0, 'encoders': 0, 'provers': 0, 'training': 0,
                  'primary_source_preflights': 34, 'primary_groundings': 34,
                  'primary_transport_assessments': 102,
                  'deterministic_validation_replays_excluded_from_primary_counts': True},
        'checkpoint_promoted': False, 'default_compiler_replaced': False,
        'original_validation_semantics_accessed': False, 'sealed_final_test_semantics_accessed': False,
        'prior_binding_hash_reads_performed': True,
        'model_stack_imports_blocked': sorted(BLOCKED_STACKS),
        'blocked_import_attempts': guard.attempts,
        'ruff_pass_claimed': False,
        'resources': {'wall_ceiling_seconds': MAX_SECONDS, 'cpu_soft_ceiling_seconds': 60,
                      'cpu_hard_ceiling_seconds': 65, 'rss_cooperative_ceiling_kib': MAX_RSS_KIB,
                      'rss_guard_is_hard_limit': False,
                      'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      'source_construction_finished_seconds': construction_finished_seconds,
                      'elapsed_seconds': time.monotonic() - started,
                      'python_executable': sys.executable},
        'limitations': [
            'Warnings cover bounded lexical patterns; unassessed does not mean supported or faithful.',
            'Controlled-English proposals use a TRAIN-supervised vocabulary and a development-designed grammar.',
            'Source anchors preserve exact spans alongside canonical symbols; they do not certify source meaning.',
            'Static proposal transport checks execute no learned decoder and supply no candidate acceptance.',
            'Supplied context is retained and blocked for clarification, never applied or resolved.',
            'Authored agreement is unreviewed posthoc development evidence; all semantic reviews remain pending.',
            'The source-span overlay annotates frozen saved outputs without reexecution or semantic assessment.',
        ], **FALSE_FLAGS,
    })
    report_binding = save(OUTPUT / 'report.json', report)
    print(json.dumps({'report_binding': report_binding, 'preflight_outcomes': report['preflight_outcomes'],
                      'grounding_outcomes': report['grounding_outcomes'],
                      'transport_summaries': transport_summaries,
                      'elapsed_seconds': report['resources']['elapsed_seconds'],
                      'max_rss_kib': report['resources']['max_rss_kib']}))


if __name__ == '__main__':
    main()
