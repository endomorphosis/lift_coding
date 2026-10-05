"""Independent standard-library audit of six-condition frozen span outcomes.

The numerical worker and public summarizer are never imported. SHA-selected
earlier independent auditors supply full-sort/token-set replay and literal
grammar checks. Neither structural replay nor receipt agreement establishes
semantic fidelity, numerical-score provenance, or proof authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import types
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
CONTROLS = ('raw_source', 'pca_reconstructed', 'new_ae_reconstructed',
            'zero_raw', 'disabled_raw', 'rotated_raw')
SEEDS = (1729, 1730, 1731)
SPLITS = ('train', 'development')
REPLAY_BINDING = {'path': str(ROOT / 'joint_span/audit_joint_spans.py'), 'bytes': 38451,
                  'sha256': 'eb8d8199d911afb5b88f55aa058ebaf4ab84d6107b7b4bbdad5167029e6b1c0d'}
PUBLIC_CHECK_BINDING = {'path': str(ROOT / 'joint_span/audit_joint_span_publication.py'), 'bytes': 22551,
                        'sha256': '0d1c816a41e99384035e8db8ae4fc897678f7a3b503e389cd81d81337946349a'}
POLICY = {'candidates_per_facet': 16, 'beam_width': 64, 'ambiguity_epsilon': 1e-7,
          'modality_and_presence': 'unchanged_native_argmax_and_float32_margin',
          'span_pair_scores': 'float32_start_plus_end',
          'joint_objective': 'python_math_fsum_of_float32_pair_scores',
          'span_order': 'native_facet_order', 'optimality_scope': 'surviving_beam_only',
          'greedy_fallback': False, 'optional_facet_removal': False}
PROFILE_SHA = '151bd007468651bb720cfa60976c491e3e7cde55a06ef2336d786f9b80fe5f5e'
MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value, *, ascii=False):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=ascii, allow_nan=False).encode()).hexdigest()


def load_independent(reference, name):
    path = Path(reference['path'])
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
            'absolute nonsymlink independently selected source required')
    data = path.read_bytes()
    require(len(data) == reference['bytes'] and hashlib.sha256(data).hexdigest() == reference['sha256'],
            'pinned independent auditor source changed')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    return module


def support(capture=None):
    if capture is not None:
        capture.bound(REPLAY_BINDING)
        capture.bound(PUBLIC_CHECK_BINDING)
    replay = load_independent(REPLAY_BINDING, 'selected_independent_joint_replay')
    public = load_independent(PUBLIC_CHECK_BINDING, 'selected_independent_joint_public_checks')
    require('torch' not in sys.modules, 'independent standard-library sources imported Torch')
    return replay, public


def vector(values):
    require(type(values) is list and len(values) == 768 and
            all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 3.4028234e38 for v in values),
            'finite original-width conditioner required')
    return values


def conditioning(control, position, source_ids, endpoints):
    """Derive the transformation on the complete split before any filtering."""
    require(control in CONTROLS and type(position) is int and 0 <= position < 32 and
            len(source_ids) == 32 and len(set(source_ids)) == 32, 'complete ordered split32 required')
    identity = source_ids[position]
    key = {'pca_reconstructed': 'pca_reconstructed',
           'new_ae_reconstructed': 'new_reconstructed'}.get(control, 'raw_source')
    original = vector(endpoints[identity]['endpoints'][key])
    donor_position = (position + 1) % 32 if control == 'rotated_raw' else position
    donor_id = source_ids[donor_position]
    effective = [0.0] * 768 if control == 'zero_raw' else (
        vector(endpoints[donor_id]['endpoints']['raw_source']) if control == 'rotated_raw' else original)
    model_vector = [struct.unpack('>f', struct.pack('>f', value))[0] for value in effective]
    require(all(math.isfinite(value) for value in model_vector), 'float32 model conditioner overflow')
    return {'original_latent_sha256': digest(original, ascii=True),
            'effective_latent_sha256': digest(effective, ascii=True),
            'latent_donor_id': donor_id, 'latent_donor_position': donor_position,
            'latent_input_enabled': control != 'disabled_raw',
            'model_latent_float32_sha256': digest(model_vector, ascii=True)}


def conditioner_profiles(endpoints):
    return {
        'raw_source': {'kind': 'original_pinned_native_source', 'source_profile_sha256': PROFILE_SHA},
        'pca_reconstructed': {'kind': 'out_of_distribution_frozen_pca_inverse_perturbation',
                              'original_producer_receipt_claimed': False, 'pca_control': endpoints['pca_control']},
        'new_ae_reconstructed': {'kind': 'out_of_distribution_frozen_ae_reconstruction_perturbation',
                                 'original_producer_receipt_claimed': False,
                                 'checkpoint_binding': endpoints['new_checkpoint_binding']},
        'zero_raw': {'kind': 'zero_vector_ablation', 'original_producer_receipt_claimed': False},
        'disabled_raw': {'kind': 'original_raw_vector_gate_disabled', 'latent_input_enabled': False},
        'rotated_raw': {'kind': 'within_split32_one_position_rotation_before_preflight',
                        'original_matched_source_producer_receipt_claimed': False}}


def compare_fields(expected, actual, message):
    require(all(key in actual and type(actual[key]) is type(value) and actual[key] == value
                for key, value in expected.items()), message)


def validate_joint(row, score, replay, public):
    heads, text, source_tokens = score['heads'], score['source_text'], score['tokens']
    fixed = replay.decisions(heads)
    joint = row['joint']
    require(digest(joint['fixed_decisions']) == digest(fixed), 'fixed native modality/presence choices differ')
    if fixed['ambiguous']:
        require(joint['search'] is None and joint['status'] == 'abstained' and
                joint['reason'] == 'ambiguous_fixed_decision_scores' and joint['canonical_ir'] is None and
                joint['facets'] is None and joint['family_syntax_checked'] is False,
                'ambiguous fixed decision contains a promoted proposal')
        return False
    reconstructed, diagnostics = replay.replay(heads, fixed['present'])
    actual = joint['search']
    require(type(actual) is dict and set(actual) == {*reconstructed, 'diagnostics'} and
            all(actual[key] == value for key, value in reconstructed.items()),
            'independent full-sort/token-set joint replay differs')
    compare_fields(diagnostics, actual['diagnostics'], 'independent joint search counters differ')
    metadata = actual['diagnostics']
    compare_fields({'token_count': len(source_tokens), 'candidates_per_facet': 16, 'beam_width': 64,
                    'confidence_scope': 'retained_complete_beam_only', 'global_optimality_established': False,
                    'incomplete_search': bool(diagnostics['pruned_candidate_count'] or diagnostics['pruned_beam_state_count']),
                    'expansion_count_upper_bound': 6144, 'native_head_value_count': 12 * len(source_tokens),
                    'enumerated_span_count_upper_bound': 3 * len(source_tokens) * (len(source_tokens) + 1),
                    'peak_feasible_expanded_state_count': max(x['feasible_expanded_state_count'] for x in diagnostics['layers'])},
                   metadata, 'bounded search interpretation/resource accounting differs')
    require(metadata['attempted_expansion_count'] <= 6144 and metadata['peak_feasible_expanded_state_count'] <= 1024,
            'declared joint expansion resource bound exceeded')
    for key in ('target_access', 'teacher_forcing', 'training_executed', 'grammar_validation_performed',
                'source_fidelity_verified', 'qualified', 'accepted', 'proof_authority'):
        require(metadata[key] is False, 'joint search grants authority or supervision: ' + key)
    if reconstructed['status'] == 'selected':
        ir, facets = replay.literal(text, source_tokens, fixed, reconstructed['selected_spans'])
        try:
            public.complete_copied_rule_contract(ir)
        except ValueError:
            require(joint['status'] == 'abstained' and joint['reason'] == 'joint_generated_ir_rejected' and
                    joint['canonical_ir'] is None and joint['facets'] is None and joint['family_syntax_checked'] is False and
                    type(joint.get('grammar_error')) is str and bool(joint['grammar_error']),
                    'independently invalid literal grammar was promoted')
        else:
            require(joint['status'] == 'proposal' and joint['reason'] is None and joint['canonical_ir'] == ir and
                    joint['facets'] == facets and joint['family_syntax_checked'] is True,
                    'exact copied non-overlapping joint canonical proposal differs')
    else:
        require(joint['status'] == 'abstained' and joint['reason'] == reconstructed['reason'] and
                joint['canonical_ir'] is None and joint['facets'] is None and joint['family_syntax_checked'] is False,
                'joint structural abstention contains a promoted proposal')
    return True


def receipt_joins(receipt, control, split, sources, endpoints, checkpoint_binding, checkpoint, public):
    ids = [source['id'] for source in sources if source['split'] == split]
    require(receipt['schema'] == 'canonical-span-decoder-preflight-inference/v1' and
            len(receipt['rows']) == receipt['eligible_count'] == receipt['input_count'] == 32 and
            receipt['decoder_call_count'] == receipt['decoder_completion_count'] == 1 and
            receipt['backend_exception_type'] is None and receipt['submitted_positions'] == list(range(32)) and
            [row['id'] for row in receipt['rows']] == ids, 'complete ordered split32 receipt required')
    requested = {'zero_raw': 'zero', 'disabled_raw': 'disabled', 'rotated_raw': 'rotate'}.get(control, 'none')
    owner_control = 'disabled' if control == 'disabled_raw' else 'none'
    require(receipt['requested_control'] == requested and receipt['owner_control'] == owner_control and
            receipt['backend_result']['latent_ablation'] == owner_control, 'wrapper versus owner ablation differs')
    require(receipt['decoder_metadata']['checkpoint_sha256'] == checkpoint_binding['sha256'] and
            receipt['decoder_metadata']['input_dimension'] == 768 and
            receipt['decoder_metadata']['context_contract_sha256'] == digest(checkpoint['context_contract'], ascii=True),
            'native dimensional checkpoint/context binding differs')
    source_by_id = {source['id']: source for source in sources}
    require(len(receipt['backend_result']['rows']) == 32, 'native backend denominator differs')
    for position, row in enumerate(receipt['rows']):
        source = source_by_id[row['id']]
        request = {'id': source['id'], 'source_text': source['input']['source_text'],
                   'context_text': '', 'requires_context_resolution': False}
        expected = conditioning(control, position, ids, endpoints)
        compare_fields({key: value for key, value in expected.items() if key != 'model_latent_float32_sha256'}, row,
                       'original/effective vector or complete-split donor/gate join differs')
        require(row['position'] == row['submitted_position'] == position and row['request_sha256'] == digest(request) and
                row['source_sha256'] == source['source_sha256'] and
                row['context_sha256'] == hashlib.sha256(b'').hexdigest(), 'source/request/context/position join differs')
        full_tokens = public.native_source_tokens(request['source_text'])
        require(row['encoding'] == {'outcome': 'admitted', 'reason': None, 'token_count': len(full_tokens),
                                    'token_input_sha256': digest(full_tokens)}, 'native full token/byte_ids recipe differs')
        preflight = row['preflight']
        require(preflight['outcome'] == 'unassessed' and preflight['diagnostics'] == [] and
                preflight['source_text'] == request['source_text'] and preflight['source_sha256'] == source['source_sha256'] and
                preflight['context'] == {'applied': False, 'requires_resolution': False,
                    'sha256': hashlib.sha256(b'').hexdigest(), 'text': ''}, 'unchanged source-only eligibility context differs')
        backend = row['decoder_row']
        require(backend == receipt['backend_result']['rows'][position] and
                backend['latent_sha256'] == row['effective_latent_sha256'] and
                backend['latent_input_enabled'] == row['latent_input_enabled'] and
                backend['source_sha256'] == source['source_sha256'], 'native backend source/vector/gate join differs')
        for value in (receipt, preflight, backend):
            for key in ('proof_authority', 'qualified'):
                require(value[key] is False, 'native receipt grants unexpected authority')
        for key in ('admitted', 'formalized', 'roundtrip_ok', 'promotion_performed', 'publication_performed',
                    'semantic_correctness_verified', 'target_access', 'teacher_forcing', 'training_executed'):
            require(backend[key] is False, 'native backend grants semantic or training authority')
        require(row['outcome'] == ('decoder_proposal' if backend['status'] == 'decoded' else 'decoder_abstained'),
                'native proposal versus source outcome differs')


def audit(plan_path, plan_sha, batch_path, batch_sha, output, summary_path=None, summary_sha=None):
    require('torch' not in sys.modules, 'pure independent audit must remain free of Torch')
    replay, public = support()
    capture = public.Capture()
    support(capture)
    plan, plan_binding = capture.external(plan_path, plan_sha)
    plan_keys = {'schema', 'helper_binding', 'baseline_helper_binding', 'baseline_plan_binding',
                 'frozen_joint_helper_binding', 'selector_binding', 'protocol_binding',
                 'summary_baseline_helper_binding', 'baseline_receipts', 'baseline_joint_ledgers',
                 'controls', 'policy', 'resource_limits', 'semantic_masks', 'content_sha256'}
    require(set(plan) == plan_keys and plan['schema'] == 'source-only-joint-conditioning-plan/v1' and
            tuple(plan['controls']) == CONTROLS and digest(plan['policy']) == digest(POLICY),
            'externally selected closed six-control joint plan differs')
    require([row['seed'] for row in plan['baseline_receipts']] ==
            [row['seed'] for row in plan['baseline_joint_ledgers']] == list(SEEDS),
            'all three unique ordered baseline seed selections required')
    for registered in plan['baseline_receipts']:
        require(set(registered) == {'seed', 'arms'} and set(registered['arms']) == set(CONTROLS) and
                all(set(pair) == {'train_binding', 'development_binding'} for pair in registered['arms'].values()),
                'closed complete six-control/two-split prior receipt selection required')
    for registered in plan['baseline_joint_ledgers']:
        require(set(registered) == {'seed', 'ledger_binding'}, 'closed prior raw joint selection required')
    capture.references(plan)
    public.zero_masks(plan['semantic_masks'])
    base = capture.read(plan['baseline_plan_binding'])
    capture.references(base)
    require(base['schema'] == 'source-only-frozen-downstream-span-plan/v1' and tuple(base['controls']) == CONTROLS and
            tuple(arm['seed'] for arm in base['arms']) == SEEDS, 'original fixed decoder/conditioner selection differs')
    sources, cohort = capture.read(base['source_inputs_binding']), capture.read(base['cohort_binding'])
    require(sources['contains_formal_targets'] is cohort['contains_formal_targets'] is False and
            len(sources['rows']) == len(cohort['rows']) == 64, 'complete source-only64 cohort required')
    public.zero_masks(sources['policy']['semantic_masks'])
    public.zero_masks(cohort['policy']['semantic_masks'])
    source_by_id = {row['id']: row for row in sources['rows']}
    require(len(source_by_id) == 64, 'unique64 source IDs required')
    for source, meta in zip(sources['rows'], cohort['rows'], strict=True):
        require(all(source[key] == meta[key] for key in ('id', 'split', 'group_id', 'source_sha256', 'input_sha256')) and
                source['id'] == 'sha256:' + digest(source['input']) and
                source['input_sha256'] == digest(source['input']) and
                source['source_sha256'] == hashlib.sha256(source['input']['source_text'].encode()).hexdigest(),
                'source input/cohort/hash identity join differs')
    encoding = capture.read(base['encoding_report_binding'])
    native = capture.read(encoding['artifacts']['native768']['full_bundle'])
    require(digest(native['profile']) == PROFILE_SHA and len(native['rows']) == 64 and
            native['profile']['producer']['model_id'] == 'Alibaba-NLP/gte-multilingual-base' and
            native['profile']['fit_input_recipe'] == native['profile']['inference_input_recipe'] == 'exact_source_only/v1',
            'original raw producer profile/recipe differs')
    producer = native['producer_receipt']
    require(producer['profile_sha256'] == PROFILE_SHA and len(producer['rows']) == 64, 'complete producer receipt required')
    native_by_id = {}
    for native_row, source, produced in zip(native['rows'], sources['rows'], producer['rows'], strict=True):
        require(native_row['id'] == source['id'] == produced['id'] and
                native_row['input'] == source['input'] and native_row['status'] == produced['status'] == 'available' and
                native_row['input_sha256'] == produced['input_sha256'] == source['input_sha256'] and
                native_row['encoder_text'] == source['input']['source_text'] and
                native_row['encoder_text_sha256'] == produced['encoder_text_sha256'] == source['source_sha256'] and
                native_row['vector_sha256'] == produced['vector_sha256'] == digest(vector(native_row['vector'])) and
                native_row['producer_row_sha256'] == digest(produced), 'raw source/context/vector/producer joins differ')
        native_by_id[source['id']] = native_row
    batch, batch_binding = capture.external(batch_path, batch_sha)
    require(batch['schema'] == 'source-only-joint-conditioning-batch/v1' and batch['successful_seeds'] == 3 and
            batch['selected_inputs_unchanged'] is True and tuple(row['seed'] for row in batch['seeds']) == SEEDS and
            batch['selected']['plan'] == plan_binding and batch['selected']['worker'] == plan['helper_binding'],
            'complete externally selected conditioning batch required')
    capture.references(batch)
    outcomes, seed_checks, evidence_rows, evidence_scores = [], [], [], []
    all_counts = Counter()
    matched_receipts = matched_previous_joint = joint_calls = proposal_contracts = 0
    for registered in batch['seeds']:
        seed = registered['seed']
        parent, report = capture.read(registered['parent_report_binding']), capture.read(registered['worker_report_binding'])
        require(registered['succeeded'] is True and registered['returncode'] == 0 and parent['succeeded'] is True and
                parent['selected_inputs_unchanged'] is True and parent['returncode'] == 0 and parent['failure'] is None and
                parent['seed'] == seed and parent['selected']['plan'] == plan_binding and
                parent['selected']['worker'] == plan['helper_binding'] and parent['process_group_cleanup_attempted'] is True,
                'successful bounded parent with original selected command required')
        capture.references(parent)
        require(report['schema'] == 'source-only-joint-conditioning-report/v1' and report['status'] == 'completed' and
                report['seed'] == seed and report['plan_binding'] == plan_binding and report['policy'] == POLICY,
                'completed seed worker profile differs')
        capture.references(report)
        for provider in report['selected_provider_entrypoints'].values():
            capture.bound({key: provider[key] for key in ('path', 'bytes', 'sha256')})
        public.zero_masks(report['masks'])
        for key in ('formal_targets_read', 'training_executed', 'semantic_accuracy_measured', 'source_fidelity_established',
                    'qualified', 'accepted', 'proof_authority', 'parameter_gradients_created', 'natural_sources',
                    'pristine_holdout', 'independent_greedy_and_joint_model_forwards'):
            require(report[key] is False, 'worker numerical/semantic authority differs: ' + key)
        for key in ('new_encoder_calls', 'new_model_fits', 'proof_calls'):
            require(type(report[key]) is int and report[key] == 0, 'forbidden numerical/semantic execution reported')
        for key in ('context_contract_unchanged', 'model_state_unchanged', 'checkpoint_unchanged', 'restored_adam_unchanged',
                    'global_cpu_rng_unchanged', 'greedy_profile_unchanged', 'all_requests_retained', 'native768_only'):
            require(report[key] is True, 'frozen numerical/source preservation assertion differs: ' + key)
        require(report['request_count'] == 64, 'all64 original requests required')
        arm = next(arm for arm in base['arms'] if arm['seed'] == seed)
        checkpoint = capture.read(arm['checkpoint_binding'])
        require(report['checkpoint_binding'] == arm['checkpoint_binding'] and
                checkpoint['config']['latent_dimension'] == 768 and checkpoint['progress']['optimizer_steps'] == 400 and
                checkpoint['config']['seed'] == seed and report['model_state_sha256'] == digest(checkpoint['model_state'], ascii=True) and
                report['saved_optimizer_state_sha256'] == digest(checkpoint['optimizer_state'], ascii=True) and
                report['original_context_contract'] == checkpoint['context_contract'],
                'fixed checkpoint/model/Adam/context digests differ')
        require(report['restored_optimizer_state_checksums'] == [
                {'role': 'embedded_source_parent', 'sha256': digest(checkpoint['source_parent_checkpoint']['optimizer_state'], ascii=True)},
                {'role': 'retained_dimensional_decoder', 'sha256': digest(checkpoint['optimizer_state'], ascii=True)}],
                'restored retained Adam checksums differ')
        endpoints, numeric = capture.read(arm['endpoints_binding']), capture.read(arm['numeric_report_binding'])
        require(endpoints['schema'] == 'source-only-expanded-reconstruction-endpoints/v1' and
                endpoints['seed'] == numeric['seed'] == seed and endpoints['lane_id'] == numeric['lane_id'] == 'native768' and
                endpoints['architecture'] == numeric['architecture'] == [768, 128, 64] and
                endpoints['source_profile_sha256'] == PROFILE_SHA and numeric['endpoint_binding'] == arm['endpoints_binding'] and
                endpoints['pca_control'] == numeric['pca_control'] and endpoints['pca_control']['fit_rows'] == 32 and
                endpoints['pca_control']['development_rows_read_before_fit'] == 0 and
                endpoints['pca_control']['retained_axes'] == 31, 'same-seed TRAIN-only frozen conditioner joins differ')
        endpoint_by_id = {row['id']: row for row in endpoints['rows']}
        require(len(endpoints['rows']) == len(endpoint_by_id) == 64 and set(endpoint_by_id) == set(source_by_id),
                'complete unique endpoint64 identities required')
        profiles = conditioner_profiles(endpoints)
        require(report['conditioner_profiles'] == profiles and tuple(report['controls']) == CONTROLS and
                report['conditioner_width'] == 768 and report['conditioning_source_occurrences'] == 384 and
                report['total_greedy_joint_outcomes'] == 768 and
                report['control_transformation_scope'] == 'complete_within_split32_before_preflight' and
                report['frozen_pca_ae_conditioners_reused'] is True and
                report['compression_storage_or_latency_benefit_measured'] is False,
                'conditioning profile/scope/denominator differs')
        for key in ('new_pca_fits', 'new_ae_fits'):
            require(type(report[key]) is int and report[key] == 0, 'new conditioner fitting reported')
        for identity, endpoint in endpoint_by_id.items():
            source = source_by_id[identity]
            require(all(endpoint[key] == source[key] for key in ('id', 'split', 'group_id', 'source_sha256')) and
                    endpoint['panel_input_sha256'] == endpoint['lane_input_sha256'] == source['input_sha256'] and
                    endpoint['endpoints']['raw_source'] == native_by_id[identity]['vector'],
                    'endpoint source/raw producer identity join differs')
        previous = next(row for row in plan['baseline_receipts'] if row['seed'] == seed)
        original_receipts = {}
        for control in CONTROLS:
            original_receipts[control] = {}
            for split in SPLITS:
                original = capture.read(previous['arms'][control][split + '_binding'])
                saved = report['baseline_summaries'][control][split]
                receipt = capture.read(saved['receipt_binding'])
                require(receipt == original and saved['exact_previous_receipt_match'] is True and
                        saved['previous_receipt_binding'] == previous['arms'][control][split + '_binding'],
                        'complete previous greedy receipt differs')
                receipt_joins(receipt, control, split, sources['rows'], endpoint_by_id,
                              arm['checkpoint_binding'], checkpoint, public)
                original_receipts[control].update({row['id']: row for row in receipt['rows']})
                matched_receipts += 1
        prior_raw_binding = next(row['ledger_binding'] for row in plan['baseline_joint_ledgers'] if row['seed'] == seed)
        prior_raw = capture.read(prior_raw_binding)
        require(report['previous_raw_joint_ledger_binding'] == prior_raw_binding and
                report['previous_raw_joint_exact_match'] is True and report['previous_raw_joint_rows_compared'] == 64 and
                report['all36_previous_greedy_receipts_captured_before_ml'] is True and
                report['exact_previous_greedy_receipts_matched'] == 12, 'recorded previous outcomes/receipt counts differ')
        require(prior_raw['schema'] == 'source-only-joint-span-proposal-ledger/v1' and
                prior_raw['seed'] == seed and len(prior_raw['rows']) == 64, 'complete prior raw joint ledger required')
        prior_raw_by_id = {row['id']: row for row in prior_raw['rows']}
        require(len(prior_raw_by_id) == 64 and set(prior_raw_by_id) == set(source_by_id), 'prior raw64 identity set differs')
        bank, ledger = capture.read(report['score_bank_binding']), capture.read(report['proposal_ledger_binding'])
        require(bank['schema'] == 'source-only-joint-conditioning-score-bank/v1' and
                ledger['schema'] == 'source-only-joint-conditioning-proposal-ledger/v1' and
                bank['seed'] == ledger['seed'] == seed and bank['plan_binding'] == ledger['plan_binding'] == plan_binding and
                bank['contains_formal_targets'] is False and len(bank['rows']) == len(ledger['rows']) == 384,
                'complete source-only384 captured score/paired ledger required')
        for value in (bank, ledger):
            public.zero_masks(value['semantic_masks'])
        for key in ('accepted', 'qualified', 'proof_authority', 'semantic_accuracy_measured'):
            require(ledger[key] is False, 'paired ledger authority differs')
        expected_order = [(control, source['id']) for control in CONTROLS for split in SPLITS
                          for source in sources['rows'] if source['split'] == split]
        require([(row['control'], row['id']) for row in bank['rows']] ==
                [(row['control'], row['id']) for row in ledger['rows']] == expected_order,
                'complete six-condition score/ledger source ordering differs')
        seed_joint_calls = 0
        for position, (score, pair) in enumerate(zip(bank['rows'], ledger['rows'], strict=True)):
            source = source_by_id[score['id']]
            native_row = original_receipts[score['control']][score['id']]
            require(score['seed'] == seed and score['capture_index'] == position and
                    score['source_text'] == pair['source_text'] == source['input']['source_text'] and
                    score['split'] == pair['split'] == source['split'] and
                    score['source_sha256'] == pair['source_sha256'] == source['source_sha256'] and
                    score['input_sha256'] == source['input_sha256'] and
                    score['profile_sha256'] == score['source_profile_sha256'] == PROFILE_SHA and pair['seed'] == seed,
                    'complete source/seed/control/profile score identity differs')
            for value in (score, pair):
                compare_fields({key: native_row[key] for key in ('original_latent_sha256', 'effective_latent_sha256',
                               'latent_donor_id', 'latent_donor_position', 'latent_input_enabled')}, value,
                               'score/ledger conditioning hash/donor/gate differs')
                ids = [item['id'] for item in sources['rows'] if item['split'] == source['split']]
                expected_conditioner = conditioning(score['control'], ids.index(source['id']), ids, endpoint_by_id)
                require(value['model_latent_float32_sha256'] == expected_conditioner['model_latent_float32_sha256'] and
                        value['latent_ablation'] == {'zero_raw': 'zero', 'disabled_raw': 'disabled',
                            'rotated_raw': 'rotate'}.get(score['control'], 'none') and
                        value['conditioning_profile'] == profiles[score['control']] and
                        value['control_transformation_scope'] == 'complete_within_split32_before_preflight',
                        'captured model-float32/profile/ablation/scope differs')
            require(score['request_sha256'] == native_row['request_sha256'] and
                    score['latent_sha256'] == pair['latent_sha256'] == native_row['effective_latent_sha256'] and
                    score['tokens'] == replay.tokens(source['input']['source_text']) and
                    score['token_input_sha256'] == digest(score['tokens']) and pair['score_row_sha256'] == digest(score),
                    'source/request/effective-vector/token/head binding differs')
            replay.validate_heads(score['heads'], len(score['tokens']))
            require(pair['greedy'] == native_row['decoder_row'], 'paired greedy differs from saved exact native receipt')
            replay.validate_greedy_from_heads(pair['greedy'], score)
            if pair['greedy']['status'] == 'decoded':
                public.complete_copied_rule_contract(pair['greedy']['canonical_ir'])
                proposal_contracts += 1
            seed_joint_calls += validate_joint(pair, score, replay, public)
            proposal_contracts += pair['joint']['status'] == 'proposal'
            for key in ('accepted', 'source_fidelity_established', 'independent_semantic_review_completed', 'proof_authority'):
                require(pair[key] is False, 'paired policy output grants unexpected authority')
            if score['control'] == 'raw_source':
                previous_joint = prior_raw_by_id[score['id']]
                require(pair['joint'] == previous_joint['joint'] and pair['greedy'] == previous_joint['greedy'] and
                        pair['latent_sha256'] == previous_joint['latent_sha256'],
                        'previous192 raw greedy/joint paired outcomes differ')
                matched_previous_joint += 1
            outcomes.append({'seed': seed, 'control': score['control'], 'id': score['id'], 'split': source['split'],
                             'greedy_status': pair['greedy']['status'], 'greedy_reason': pair['greedy']['reason'],
                             'joint_status': pair['joint']['status'], 'joint_reason': pair['joint']['reason']})
        stats = public.statistics(ledger['rows'])
        require(report['joint_proposals'] == stats['joint_proposals'] and report['greedy_proposals'] == stats['greedy_proposals'] and
                report['joint_reason_counts'] == stats['joint_reason_counts'] and
                report['transition_counts'] == stats['transition_counts'] and
                report['search_incomplete_rows'] == stats['search_totals'].get('incomplete_search_rows', 0),
                'worker384 structural aggregate differs')
        require(report['ambiguous_fixed_decision_rows'] == 384 - seed_joint_calls ==
                sum(row['joint']['reason'] == 'ambiguous_fixed_decision_scores' for row in ledger['rows']),
                'conditional selector calls versus fixed ambiguity denominator differs')
        expected_counts = {'optimizer_step_attempts': 0, 'optimizer_updates': 0, 'dimensional_restores': 1,
                           'embedded_parent_restores': 1, 'model_constructors': 3, 'wrapper_calls': 12,
                           'owner_decoder_calls': 12, 'source_row_decode_calls': 384, 'actual_model_forward_calls': 384,
                           'joint_selection_calls': seed_joint_calls, 'joint_additional_model_forward_calls': 0}
        require(all(type(v) is int for v in report['counts'].values()) and report['counts'] == expected_counts,
                'single-forward/two-policy/frozen restoration counts differ')
        all_counts.update(report['counts'])
        joint_calls += seed_joint_calls
        seed_checks.append({'seed': seed, 'worker_report_binding': registered['worker_report_binding'],
                            'parent_report_binding': registered['parent_report_binding'], 'structural_statistics': stats,
                            'score_and_paired_rows_replayed': 384, 'exact_previous_greedy_receipts': 12,
                            'exact_previous_raw_joint_rows': 64, 'source_vector_donor_context_token_joins_exact': True})
        evidence_rows.append((seed, ledger['rows'], report, parent))
        evidence_scores.append((seed, bank['rows']))
    require(dict(all_counts) == batch['completed_worker_counts'] and all_counts['actual_model_forward_calls'] == 1152 and
            matched_receipts == 36 and matched_previous_joint == 192 and len(outcomes) == 1152,
            'complete1152 forward/2304 outcome/36 receipt/192 raw repeat denominator differs')
    public_checks = None
    if summary_path is not None:
        public_checks = check_public(capture, public, plan_binding, batch_binding, all_counts,
                                    evidence_rows, evidence_scores, summary_path, summary_sha)
    for reference in tuple(capture.files.values()):
        capture.bound(reference)
    data = Path(__file__).read_bytes()
    result = {'schema': 'independent-source-only-joint-conditioning-audit/v1', 'status': 'passed',
              'plan_binding': plan_binding, 'batch_binding': batch_binding,
              'auditor_binding': {'path': str(Path(__file__).absolute()), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()},
              'independent_replay_source_binding': REPLAY_BINDING, 'independent_public_checks_source_binding': PUBLIC_CHECK_BINDING,
              'checked_file_count': len(capture.files), 'checked_file_bindings': list(capture.files.values()),
              'seed_checks': seed_checks, 'actual_root_worker_counts': dict(all_counts),
              'native_head_records_checked': 1152, 'paired_condition_source_seed_occurrences': 1152,
              'policy_outcomes_checked': 2304, 'previous_greedy_receipts_matched_exactly': matched_receipts,
              'previous_raw_joint_rows_matched_exactly': matched_previous_joint,
              'independent_joint_selection_replays': joint_calls, 'generated_proposal_contract_checks': proposal_contracts,
              'public_checks': public_checks, 'policy_outcomes': outcomes,
              'independent_algorithm': 'full_candidate_sort_and_token_set_beam_prefix_expansion/v1',
              'all64_denominators_retained_per_seed_and_control': True,
              'conditioning_transformation_scope': 'complete_ordered_within_split32_before_preflight',
              'source_literal_copy_and_global_nonoverlap_checked': True, 'native_modality_presence_choices_checked': True,
              'all_semantic_masks_integer_zero': True, 'torch_imported': False, 'audit_model_calls': 0,
              'audit_optimizer_updates': 0, 'audit_network_calls': 0, 'audit_prover_calls': 0,
              'semantic_target_bodies_read': False, 'semantic_accuracy_measured': False, 'source_fidelity_established': False,
              'independent_semantic_reviews_created': 0, 'accepted': False, 'qualified': False, 'proof_authority': False,
              'limitations': ['Saved score provenance and numerical correctness are not independently attested.',
                  'Checkpoint/Adam checks verify saved bytes and recorded preservation assertions; this auditor restores no model.',
                  'Selected provider/source bindings are not a complete binary dependency closure.',
                  'Top16/beam64 replay validates an approximate structural policy within its surviving beam.',
                  'Copied spans, non-overlap, grammar checks and raw-relative differences do not establish semantic fidelity.']}
    result['content_sha256'] = digest(result)
    require('torch' not in sys.modules, 'unexpected Torch import during independent audit')
    with Path(output).open('xb') as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode() + b'\n')
    print(json.dumps({'status': 'passed', 'checked_file_count': len(capture.files), 'policy_outcomes_checked': 2304,
                      'public_results_checked': public_checks is not None, 'audit_model_calls': 0}, sort_keys=True))


def scalar_differences(pairs):
    require(all(value is None or type(value) in (int, float) and math.isfinite(value)
                for pair in pairs for value in pair), 'finite optional diagnostic scalar required')
    defined = [(left, right) for left, right in pairs if left is not None and right is not None]
    signed = [right - left for left, right in defined]
    absolute = [abs(value) for value in signed]
    return {'paired_defined_count': len(defined),
            'changed_definedness_count': sum((left is None) != (right is None) for left, right in pairs),
            'changed_value_count': sum(left != right for left, right in defined),
            'maximum_absolute_difference': max(absolute) if absolute else None,
            'mean_absolute_difference': math.fsum(absolute) / len(defined) if defined else None,
            'mean_signed_difference': math.fsum(signed) / len(defined) if defined else None,
            'semantic_improvement_measured': False}


def raw_comparison(raw_rows, condition_rows, raw_banks, condition_banks):
    """Reconstruct each declared comparison by independent grouped columns."""
    def identities(rows):
        return [(row['seed'], row['split'], row['id']) for row in rows]
    selected = identities(raw_rows)
    require(len(set(selected)) == len(selected) and
            selected == identities(condition_rows) == identities(raw_banks) == identities(condition_banks),
            'unique matched source/seed/split comparisons required')
    rows = list(zip(raw_rows, condition_rows, strict=True))
    fields = ('actor', 'action', 'object', 'conditions', 'exceptions', 'temporal')
    changes = {}
    for policy in ('greedy', 'joint'):
        for key in ('status', 'reason', 'canonical_ir'):
            changes[policy + '_' + key] = sum(left[policy][key] != right[policy][key] for left, right in rows)
        changes[policy + '_status_reason_ir'] = sum(
            any(left[policy][key] != right[policy][key] for key in ('status', 'reason', 'canonical_ir'))
            for left, right in rows)
    fixed = [(left['joint']['fixed_decisions'], right['joint']['fixed_decisions']) for left, right in rows]
    changes.update(fixed_modality=sum(a['modality'] != b['modality'] for a, b in fixed),
                   fixed_presence=sum(a['present'] != b['present'] for a, b in fixed),
                   fixed_ambiguity=sum(a['ambiguous'] != b['ambiguous'] for a, b in fixed))
    presence = {field: sum(a['present'][index] != b['present'][index] for a, b in fixed)
                for index, field in enumerate(fields)}

    def intervals(row):
        facets = (row['greedy'].get('span_diagnostics') or {}).get('facets', {})
        return [[facets[field].get('present'), facets[field].get('token_start'),
                 facets[field].get('token_end_inclusive')] if field in facets else [False, None, None]
                for field in fields]

    searches = [(left['joint']['search'], right['joint']['search']) for left, right in rows]
    coordinates = [(None if a is None else a['selected_spans'],
                    None if b is None else b['selected_spans']) for a, b in searches]
    changes['greedy_facet_intervals'] = sum(intervals(left) != intervals(right) for left, right in rows)
    changes['joint_selected_spans'] = sum(a != b for a, b in coordinates)
    intervals_by_field = {field: sum((None if a is None else a[index]) != (None if b is None else b[index])
                                    for a, b in coordinates) for index, field in enumerate(fields)}
    changes['joint_search_presence'] = sum((a is None) != (b is None) for a, b in searches)
    changes['joint_search_status_reason'] = sum(
        (None if a is None else (a['status'], a['reason'])) != (None if b is None else (b['status'], b['reason']))
        for a, b in searches)
    pruning_keys = ('incomplete_search', 'pruned_candidate_count', 'pruned_beam_state_count',
                    'attempted_expansion_count', 'overlap_rejected_expansion_count', 'complete_retained_state_count')
    def prune(search):
        return None if search is None else {key: search['diagnostics'][key] for key in pruning_keys}
    changes['joint_search_pruning_diagnostics'] = sum(prune(a) != prune(b) for a, b in searches)
    changes['joint_search_full_diagnostics'] = sum((None if a is None else a['diagnostics']) !=
                                                (None if b is None else b['diagnostics']) for a, b in searches)
    head_checks = {}
    for head in ('start', 'end', 'presence', 'modality'):
        lists = [(a['heads'][head], b['heads'][head]) for a, b in zip(raw_banks, condition_banks, strict=True)]
        if head != 'modality':
            lists = [([value for facet in a for value in facet], [value for facet in b for value in facet])
                     for a, b in lists]
        require(all(len(a) == len(b) and a for a, b in lists), 'paired nonempty native head shape differs')
        deltas = [abs(x - y) for a, b in lists for x, y in zip(a, b, strict=True)]
        head_checks[head] = {'paired_scalar_count': len(deltas), 'changed_rows': sum(a != b for a, b in lists),
                             'changed_scalar_count': sum(value != 0 for value in deltas),
                             'maximum_absolute_difference': max(deltas) if deltas else None,
                             'mean_absolute_difference': math.fsum(deltas) / len(deltas) if deltas else None}
    return {'paired_source_seed_occurrences': len(rows), 'changed_counts': changes,
            'changed_presence_by_facet': presence, 'changed_joint_selected_interval_by_facet': intervals_by_field,
            'head_value_diagnostics': head_checks,
            'fixed_decision_margin_diagnostics': {key: scalar_differences([(a['margins'][key], b['margins'][key])
                for a, b in fixed]) for key in ('modality', 'object', 'conditions', 'exceptions', 'temporal')},
            'joint_search_score_diagnostics': {key: scalar_differences([(None if a is None else a[key],
                None if b is None else b[key]) for a, b in searches])
                for key in ('best_score', 'runner_up_score', 'joint_score_margin')},
            'score_scope': 'Native head values and retained-beam objectives; diagnostic differences without calibrated semantic confidence.',
            'semantic_improvement_measured': False}


def check_public(capture, public, plan_binding, batch_binding, all_counts, evidence_rows, evidence_scores,
                 summary_path, summary_sha):
    summary, summary_binding = capture.external(summary_path, summary_sha)
    require(summary['schema'] == 'source-only-joint-conditioning-structural-summary/v1' and
            summary['status'] == 'completed' and summary['plan_binding'] == plan_binding and
            summary['batch_binding'] == batch_binding and tuple(summary['controls']) == CONTROLS and
            summary['policy'] == POLICY, 'public structural summary lineage/profile differs')
    capture.references(summary)
    require([row['seed'] for row in summary['public_ledger_bindings']] ==
            [row['seed'] for row in summary['worker_evidence_bindings']] ==
            [row['seed'] for row in summary['seeds']] == list(SEEDS), 'all three unique ordered public seed partitions required')
    compare_fields({'original_source_count': 64, 'source_condition_seed_occurrences': 1152, 'policy_outcomes': 2304,
                    'unique_policy_model_forwards': 1152, 'joint_extra_model_forwards': 0,
                    'exact_previous_greedy_receipts': 36, 'exact_previous_greedy_repeat_occurrences': 1152,
                    'exact_previous_raw_joint_repeat_occurrences': 192}, summary, 'public denominators differ')
    public.zero_masks(summary['semantic_masks'])
    for key in ('accepted', 'qualified', 'proof_authority', 'training_executed', 'formal_targets_read',
                'source_fidelity_established', 'semantic_accuracy_measured', 'independent_semantic_review_completed',
                'new_model_weights_created'):
        require(summary[key] is False, 'public summary authority/execution scope differs: ' + key)
    for key in ('new_encoder_calls', 'new_ae_or_pca_fits', 'proof_calls'):
        require(type(summary[key]) is int and summary[key] == 0, 'public summary reports new execution: ' + key)
    all_rows, all_banks, recomputed_seeds = [], [], []
    statistic_sets = comparison_sets = 0
    public_bindings = []
    for index, ((seed, rows, report, parent), (score_seed, banks)) in enumerate(zip(evidence_rows, evidence_scores, strict=True)):
        require(seed == score_seed, 'saved score/ledger seed join differs')
        evidence = summary['worker_evidence_bindings'][index]
        require(evidence == {'seed': seed, 'report_binding': next(row['worker_report_binding'] for row in capture.read(batch_binding)['seeds'] if row['seed'] == seed),
                'parent_binding': next(row['parent_report_binding'] for row in capture.read(batch_binding)['seeds'] if row['seed'] == seed),
                'ledger_binding': report['proposal_ledger_binding'], 'score_bank_binding': report['score_bank_binding']},
                'public exact worker/parent/ledger/head evidence selection differs')
        public_binding = summary['public_ledger_bindings'][index]['ledger_binding']
        published = capture.read(public_binding)
        public_bindings.append(public_binding)
        require(published['schema'] == 'source-only-joint-conditioning-public-proposal-ledger/v1' and
                published['seed'] == seed and published['plan_binding'] == plan_binding and
                published['batch_binding'] == batch_binding and published['helper_binding'] == summary['helper_binding'] and
                tuple(published['controls']) == CONTROLS and published['policy'] == POLICY and
                published['row_count'] == len(published['rows']) == 384 and published['policy_outcome_count'] == 768,
                'complete exact public384 seed partition required')
        public.zero_masks(published['semantic_masks'])
        for key in ('contains_full_head_score_arrays', 'contains_source_vectors', 'contains_model_weights',
                    'contains_formal_targets', 'accepted', 'qualified', 'proof_authority',
                    'source_fidelity_established', 'independent_semantic_review_completed'):
            require(published[key] is False, 'public ledger grants authority or includes excluded numerical material')
        expected_rows = [public.public_row(row, seed, position % 64) for position, row in enumerate(rows)]
        require(digest(published['rows']) == digest(expected_rows),
                'public384 exact source-position/authority/logit-removal transformation differs')
        for row in published['rows']:
            public.zero_masks(row['semantic_masks'])
            for key in ('accepted', 'qualified', 'source_fidelity_established',
                        'independent_semantic_review_completed', 'proof_authority'):
                require(row[key] is False, 'public row grants unexpected authority')
            require('modality_logits' not in row['greedy'].get('span_diagnostics', {}),
                    'native modality head array leaked into public row')
        controls = {}
        raw_rows = [row for row in rows if row['control'] == 'raw_source']
        raw_banks = [row for row in banks if row['control'] == 'raw_source']
        for control in CONTROLS:
            selected_rows = [row for row in rows if row['control'] == control]
            selected_banks = [row for row in banks if row['control'] == control]
            splits = {split: {**public.statistics([row for row in selected_rows if row['split'] == split]),
                             'vs_raw': raw_comparison([row for row in raw_rows if row['split'] == split],
                                 [row for row in selected_rows if row['split'] == split],
                                 [row for row in raw_banks if row['split'] == split],
                                 [row for row in selected_banks if row['split'] == split])} for split in SPLITS}
            controls[control] = {**public.statistics(selected_rows), 'splits': splits,
                                'vs_raw': raw_comparison(raw_rows, selected_rows, raw_banks, selected_banks)}
            statistic_sets += 3
            comparison_sets += 3
        selected = {'seed': seed, 'aggregate': public.statistics(rows), 'controls': controls, 'counts': report['counts'],
                    'exact_previous_greedy_receipts': 12, 'exact_previous_raw_joint_rows': 64,
                    'resources': report['resources'], 'parent_wall_seconds': parent['wall_seconds']}
        require(summary['seeds'][index] == selected, 'public per-seed/control/split structural or score-difference scalars differ')
        recomputed_seeds.append(selected)
        statistic_sets += 1
        all_rows.extend(rows)
        all_banks.extend(banks)
    require(len(all_rows) == 1152 and len({(row['seed'], row['control'], row['id']) for row in all_rows}) == 1152,
            'public partitions contain duplicate or missing condition/source/seed occurrence')
    aggregate_controls = {}
    raw_rows = [row for row in all_rows if row['control'] == 'raw_source']
    raw_banks = [row for row in all_banks if row['control'] == 'raw_source']
    for control in CONTROLS:
        selected_rows = [row for row in all_rows if row['control'] == control]
        selected_banks = [row for row in all_banks if row['control'] == control]
        splits = {split: {**public.statistics([row for row in selected_rows if row['split'] == split]),
                         'vs_raw': raw_comparison([row for row in raw_rows if row['split'] == split],
                             [row for row in selected_rows if row['split'] == split],
                             [row for row in raw_banks if row['split'] == split],
                             [row for row in selected_banks if row['split'] == split])} for split in SPLITS}
        aggregate_controls[control] = {**public.statistics(selected_rows), 'splits': splits,
                                      'vs_raw': raw_comparison(raw_rows, selected_rows, raw_banks, selected_banks)}
        statistic_sets += 3
        comparison_sets += 3
    require(summary['aggregate_controls'] == aggregate_controls and summary['aggregate'] == public.statistics(all_rows) and
            summary['actual_counts'] == dict(all_counts), 'public aggregate/condition/split statistics or forward counts differ')
    statistic_sets += 1
    resources = {'worker_wall_seconds_total': math.fsum(row['resources']['elapsed_seconds'] for row in recomputed_seeds),
                 'worker_cpu_seconds_total': math.fsum(row['resources']['cpu_seconds'] for row in recomputed_seeds),
                 'maximum_worker_peak_rss_kib': max(row['resources']['peak_rss_kib'] for row in recomputed_seeds),
                 'parent_wall_seconds_total': math.fsum(row['parent_wall_seconds'] for row in recomputed_seeds),
                 'scope': 'Current native model/head capture plus both span selection policies; excludes upstream encoding/vector-bank creation/prior fitting/independent audits.',
                 'per_condition_performance_measured': False, 'compression_latency_gain_measured': False}
    require(summary['resources'] == resources and summary['verified_input_binding_count'] == len(summary['verified_input_bindings']) and
            len({row['path'] for row in summary['verified_input_bindings']}) == len(summary['verified_input_bindings']),
            'public measured resources or exact binding accounting differs')
    return {'summary_binding': summary_binding, 'public_ledger_bindings': public_bindings,
            'public_condition_source_seed_rows_joined_exactly': 1152, 'public_policy_outcomes_joined': 2304,
            'structural_statistic_sets_recomputed': statistic_sets, 'raw_relative_comparison_sets_recomputed': comparison_sets,
            'all_head_scalar_margin_and_joint_score_difference_diagnostics_recomputed': True,
            'native_full_token_encoding_rows_checked': 1152, 'resource_aggregate_recomputed': True,
            'exact_public_transformation': 'Remove only greedy modality_logits; add seed/within-control source_position/qualifiedFalse/integerZeroMasks.',
            'semantic_accuracy_measured': False, 'source_fidelity_established': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'batch'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--summary', type=Path)
    parser.add_argument('--summary-sha256')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require((args.summary is None) == (args.summary_sha256 is None), 'summary requires explicit SHA selection')
    audit(args.plan, args.plan_sha256, args.batch, args.batch_sha256, args.output,
          args.summary, args.summary_sha256)


if __name__ == '__main__':
    main()
