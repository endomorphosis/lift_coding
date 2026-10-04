"""Validate saved next-experiment planning evidence without executing models."""

import ast
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
OUTPUT = CAMPAIGN / 'alignment-next-experiments-validation-01'
MAIN_PLAN = ROOT / 'implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md'
CHECKOUT = ROOT / '.worktrees/alignment-decoder-768-20261003'
CHECKOUT_HEAD = '64bc5734dc82db72e955f2e809b770127e9b6cfc'
CHECKOUT_BRANCH = 'codex/alignment-decoder-768-20261003'
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 2_000_000
GIB = 1024**3
SHA = re.compile(r'[0-9a-f]{64}\Z')
MASKS = dict(weak_decoder_fit=1, strong_semantic_fit=0, contrastive_supervision=0,
             proof_supervision=0, fidelity_evaluation=0)
FACETS = ('modality', 'actor', 'action', 'object', 'conditions', 'exceptions', 'temporal')
CORE = FACETS[:4]
MODEL = Path('/home/barberb/.cache/ipfs_accelerate_py/llama_cpp/models/cid-v1/bafkreicgnd6su3jhmtpckbejqurdb2lchdvvydluswdg5m5zy3cpvroh3i/Leanstral-1.5-119B-A6B-NVFP4.gguf')
EXPECTED = {
    'binding-review-admission-validation-01/validation.json': '22d028c5618cce6e4bf30fa7c54511e4163704d8750ad95fb92ebc75be1030a9',
    'leanstral-embedding-inventory-01/inventory.json': 'b6ae6bce48b644f6fe0b4f9f31c05b0e64e0af5f3834d596482e4ebaf195e1af',
    'leanstral-embedding-inventory-01/audit_saved_embeddings.py': '69f748373f8de60064fc982084df7c2c3b7df3f63c5b87dd3b9e7e086e6c0817',
    'alignment-next-experiments-readiness-01/snapshot.json': '9cf6e692e10017d1750b8c2895e82420293f5ba31a621f3f810a0aa5022560fa',
    'alignment-next-experiments-readiness-02/snapshot.json': '3844b11d72de83646656d7379e53271d98fe10e48ff3e7e07d6581adad9acddb',
    'canonical-codec-01/train_weak_supervision.json': '97a333821790db1ad11a542f918a32e583b9b4ab150b82cdd71bbd883bbc42ba',
    'canonical-codec-01/target_free_inputs.json': '134f9a3bf917f0613fb474c04d8a5e414da443b133e12149f026cd3b5aa9473d',
    'label_admission_contract_design.md': 'ddf00af08646687c9f35ffffa41db928bbf55580ce2525fc499cc01fe988798d',
    'contrastive_prototype_design.md': '894595dd9891b506cec179f6c7c734e335698be1876959218d4f3854e7234e0f',
    'alignment-next-experiments-report.md': 'b45457190a29d22fac37ad46b781bd04cc0f5f794aa25627c3dc2568adf77ec0',
}
MAIN_PLAN_SHA = '7c48f55bfbdaa882b24cc8fd6afb03d6f3020580b3ef101c985a863adfcdb442'
OWNER_HASHES = {
    'logic/formalization/autoencoder/alignment_projection.py': 'd29853a4238350eabe2265b51c48913c9e77280af0ee131bbd04ef760199c18e',
    'logic/formalization/autoencoder/alignment_experiment.py': '3c5940850b3104dba8896a496c9c37729661bbe7778ced745c410c339798be27',
    'logic/formalization/autoencoder/action_contrastive_decoder_training.py': '18dc019d86cb96d670dd583ad16f6930a3b8a2ffd49a587f40d1ef6cb105b497',
    'optimizers/logic_theorem_optimizer/legal_ir_loss_configuration.py': 'd088888477452dab1e2d7a26fe754e95049f3a688a56d7a719ee59ed0a34d9d3',
    'optimizers/logic_theorem_optimizer/legal_joint_retrieval.py': '577698c99d0cdd2209bdaaee01b40778f46251e9e1256d7537312d6655cdcb9d',
    'optimizers/logic_theorem_optimizer/modal_latent_formula.py': 'ec5bdcd752d157c9fc0257a45551cfe9ce7be172af767e8ed769bf1bc8a31d36',
    'optimizers/logic_theorem_optimizer/modal_joint_formula.py': '5dda48e79614f49c2e2c8b107811bde37260355f7d4ca4e0e54a88d883725204',
}
FALSE_AUTHORITY = ('qualified', 'accepted', 'source_fidelity_established', 'proof_authority',
                   'independent_semantic_review_completed', 'reviewer_identity_authenticated',
                   'reviewer_independence_authenticated', 'semantic_gold_created',
                   'actual_training_or_evaluation_admission')


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'duplicate JSON key'
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError('nonfinite JSON constant')


def finite_json(value):
    nodes = 0

    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        assert nodes <= MAX_JSON_NODES and depth <= MAX_JSON_DEPTH
        if type(item) is dict:
            assert all(type(key) is str for key in item)
            for key, child in item.items():
                key.encode('utf-8')
                visit(child, depth + 1)
        elif type(item) is list:
            for child in item:
                visit(child, depth + 1)
        elif type(item) is float:
            assert math.isfinite(item), 'nonfinite JSON number'
        elif type(item) is str:
            item.encode('utf-8')
        else:
            assert item is None or type(item) in (bool, int), 'ordinary JSON required'

    visit(value, 0)


def binding(path):
    path = Path(path).resolve(strict=True)
    before = path.stat()
    assert stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= MAX_FILE_BYTES
    assert path != MODEL.resolve(), 'whole-model hashing forbidden'
    checksum, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while chunk := stream.read(262144):
            size += len(chunk)
            assert size <= MAX_FILE_BYTES
            checksum.update(chunk)
    after = path.stat()
    assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    assert size == before.st_size
    return dict(path=str(path), bytes=size, sha256=checksum.hexdigest())


def load(path, checksum_key='content_sha256'):
    path = Path(path)
    assert stat.S_ISREG(path.stat().st_mode) and path.stat().st_size <= MAX_JSON_BYTES
    value = json.loads(path.read_bytes().decode('utf-8'), object_pairs_hook=unique_object,
                       parse_constant=reject_constant)
    finite_json(value)
    if checksum_key is not None:
        assert type(value) is dict and type(value.get(checksum_key)) is str
        assert SHA.fullmatch(value[checksum_key])
        assert value[checksum_key] == digest({key: item for key, item in value.items() if key != checksum_key})
    return value


def require_int(value, expected):
    assert type(value) is int and value == expected


def no_authority(value):
    assert all(value[field] is False for field in FALSE_AUTHORITY)


def main():
    assert not OUTPUT.exists(), 'fresh validation generation required'
    checked = {}

    def verify(reference):
        assert type(reference) is dict and SHA.fullmatch(reference['sha256'])
        observed = binding(reference['path'])
        assert reference['sha256'] == observed['sha256'], reference['path']
        assert 'bytes' not in reference or reference['bytes'] == observed['bytes']
        previous = checked.get(observed['path'])
        assert previous is None or previous == observed
        checked[observed['path']] = observed
        return observed

    def pin(relative):
        return verify(dict(path=str(CAMPAIGN / relative), sha256=EXPECTED[relative]))

    prior_binding = pin('binding-review-admission-validation-01/validation.json')
    prior = load(prior_binding['path'])
    no_authority(prior)
    require_int(prior['checked_file_count'], 501)
    assert len(prior['checked_file_bindings']) == 501
    for reference in prior['checked_file_bindings']:
        assert Path(reference['path']).resolve() != MAIN_PLAN.resolve()
        verify(reference)
    require_int(prior['actual_submissions'], 0)
    require_int(prior['authenticated_reviews'], 0)
    require_int(prior['adjudications_completed'], 0)
    require_int(prior['reviewer_packet_items'], 64)
    require_int(prior['blank_annotation_slots'], 512)
    require_int(prior['receipt_mask_values_zero'], 320)
    require_int(prior['organizer_mask_values_zero'], 320)
    assert prior['numerical_model_execution'] is prior['training_execution'] is prior['prover_execution'] is False
    assert len(prior['new_implementation_test_bindings']) == 5
    for reference in prior['new_implementation_test_bindings']:
        verify(reference)
    for field in ('runner_binding', 'report_binding', 'independent_audit_binding'):
        verify(prior[field])
    historic_main_plan = []
    for reference in prior['documentation_bindings']:
        if Path(reference['path']).resolve() == MAIN_PLAN.resolve():
            historic_main_plan.append(reference)
        else:
            verify(reference)
    assert len(historic_main_plan) == 1

    inventory_binding = pin('leanstral-embedding-inventory-01/inventory.json')
    inventory_runner_binding = pin('leanstral-embedding-inventory-01/audit_saved_embeddings.py')
    inventory = load(inventory_binding['path'])
    assert inventory['schema'] == 'leanstral-saved-embedding-static-inventory/v1'
    require_int(len(inventory['file_bindings']), 36)
    assert all(value is False for value in inventory['false_flags'].values())
    for reference in inventory['file_bindings']:
        verify(reference)
    assert inventory_runner_binding in inventory['file_bindings']
    vectors = inventory['vector_checks']
    require_int(vectors['total_rows'], 2400)
    require_int(vectors['total_finite_4096_values'], 9_830_400)
    assert vectors['all_three_output_files_byte_identical'] is vectors['fixed_profile_repeatability_only'] is True
    assert len(vectors['runs']) == 3
    assert len({row['file_sha256'] for row in vectors['runs']}) == 1
    assert len({row['payload_sha256'] for row in vectors['runs']}) == 1
    saved_report_path = ROOT / 'artifacts/autoformal-leanstral4096-800x20-20261004-fixed16/report.json'
    saved = load(saved_report_path, None)
    assert saved['status'] == 'completed' and saved['dimension'] == 4096
    assert saved['pooling'] == 'last' and saved['normalization'] == 'l2'
    assert saved['input'] == 'exact raw source, no chat template'
    assert saved['original_service_restored'] is True
    assert saved['workload_sha256'] == inventory['saved_run_identity']['workload_sha256']
    assert len(saved['runs']) == 3
    for observed, recorded in zip(vectors['runs'], saved['runs'], strict=True):
        require_int(observed['row_count'], 800)
        require_int(observed['finite_4096_value_count'], 3_276_800)
        require_int(observed['exact_workload_id_joins'], 800)
        assert observed['registered_payload_hash_matches'] is True
        assert observed['repeat'] == recorded['repeat']
        assert observed['payload_sha256'] == recorded['outputs_sha256']
        assert abs(observed['norm_min'] - 1) < 1e-4 and abs(observed['norm_max'] - 1) < 1e-4
    canary = inventory['canary_checks']
    assert canary['single_batch_equivalent_at_tolerance'] is False
    assert canary['saved_report_metrics_exactly_recomputed'] is True
    assert canary['single_vs_batch_l2'] == saved['canary']['single_vs_batch_l2'] == 0.14593208421713977
    assert canary['a_b_a_replay_l2'] == saved['canary']['a_b_a_replay_l2'] == 0
    assert canary['registered_tolerance_l2'] == 0.001
    profile = inventory['registered_embedding_profile']
    assert profile['input'] == saved['input'] and profile['chat_template_applied'] is False
    require_int(profile['parallel_slots'], 16)
    require_int(profile['context_total_requested'], 8192)
    require_int(profile['context_per_slot_observed'], 512)
    assert inventory['producer_checks']['executed_producer_matches_saved_report'] is True
    assert inventory['producer_checks']['current_script_identical_to_executed'] is False
    assert inventory['producer_checks']['embedding_inference_measurement_body_unchanged'] is True
    assert inventory['reported_historical_cost']['new_benchmark_executed'] is False
    assert inventory['reported_historical_cost']['load_seconds'] == saved['server_load_seconds']
    assert inventory['reported_historical_cost']['medians'] == saved['medians']
    assert inventory['model_asset']['declared_model_digest_independently_verified_this_stage'] is False
    require_int(inventory['model_asset']['whole_model_bytes_hashed_this_stage'], 0)
    assert inventory['model_asset']['header']['full_model_hash_verified'] is False
    assert inventory['model_asset']['header']['tensor_headers_or_weights_read'] is False
    assert inventory['model_asset']['header']['metadata_prefix_sha256'] == '550c9abbf62aa6acee190e8a3f621910c111b26ca32cf6cfbfbb4203ed7c77b4'
    require_int(inventory['backend_checks']['native_hidden_width'], 4096)
    require_int(inventory['backend_checks']['vocabulary_logits_width'], 131072)
    assert len(inventory['backend_checks']['binaries']) == 9 and len(inventory['backend_checks']['sources']) == 4
    overlap = inventory['current_panel_overlap']
    for field, expected in [('old_request_rows', 34), ('old_unique_source_texts', 33),
                            ('new_public_packet_rows', 64), ('new_unique_source_texts', 64),
                            ('old_exact_source_overlap', 0), ('new_exact_source_overlap', 0)]:
        require_int(overlap[field], expected)
    assert overlap['cached_vectors_directly_join_current_panels'] is False
    assert inventory['prior_failed_run']['status'] == 'failed'
    assert any('batch-peer, order, padding or slot independence' in text for text in inventory['limitations'])

    snapshots = []
    for generation in ('01', '02'):
        snapshot_binding = pin(f'alignment-next-experiments-readiness-{generation}/snapshot.json')
        snapshot = load(snapshot_binding['path'])
        assert snapshot['schema'] == 'alignment-next-experiments-static-readiness/v1'
        verify(snapshot['runner_binding'])
        assert len(snapshot['source_bindings']) == 6
        for reference in snapshot['source_bindings']:
            verify(reference)
        verify(snapshot['training_manifest_binding'])
        assert snapshot['model_loaded'] is snapshot['projection_fit_executed'] is snapshot['masks_changed'] is False
        assert snapshot['service_queries_or_mutations_executed'] is False
        for field in ('embeddings_generated', 'optimizer_updates', 'prover_calls',
                      'authenticated_reviews_created', 'labels_admitted', 'original_contrastive_masks_enabled'):
            require_int(snapshot[field], 0)
        for field in ('qualified', 'accepted', 'source_fidelity_established', 'proof_authority',
                      'existing_group_ids_are_equivalence_labels'):
            assert snapshot[field] is False
        require_int(snapshot['training_rows'], 16)
        require_int(snapshot['distinct_canonical_targets'], 16)
        require_int(snapshot['source_groups'], 4)
        require_int(snapshot['variants_per_group'], 4)
        assert snapshot['original_training_masks'] == MASKS
        assert snapshot['new_weak_contrastive_policy_required_before_diagnostic_fit'] is True
        assert snapshot['gpu_query']['numeric_gpu_memory_availability_established'] is False
        formula = snapshot['common_runner_resource_formula']
        assert formula['runner_preflight_invoked'] is False
        assert formula['scope'] == 'evaluation_of_existing_common_runner_formula_not_an_executed_embedding_preflight'
        model_stat = snapshot['model_stat']
        assert model_stat['full_model_hash_verified'] is False
        require_int(model_stat['bytes'], 67_135_119_264)
        assert Path(model_stat['resolved_model_path']) == MODEL.resolve()
        require_int(formula['memory_limit_bytes'], 90 * GIB)
        require_int(formula['reserve_bytes'], 12 * GIB)
        # Round only after evaluating the same floating-point formula as the runner.
        estimate = model_stat['bytes'] * 1.10 + min(4 * GIB, formula['memory_limit_bytes'] * 0.1)
        required = estimate + formula['reserve_bytes']
        require_int(formula['estimated_model_and_headroom_bytes'], int(estimate))
        require_int(formula['estimated_model_headroom_and_reserve_bytes'], int(required))
        available = snapshot['memory_observation']['MemAvailable_bytes']
        assert type(available) is int and 0 < available < required
        assert formula['admitted_by_formula'] is False and formula['result'] == 'would_reject_at_snapshot'
        snapshots.append((snapshot_binding, snapshot))
    authoritative_binding, authoritative = snapshots[1]
    require_int(authoritative['memory_observation']['MemAvailable_bytes'], 45_221_969_920)
    require_int(authoritative['common_runner_resource_formula']['estimated_model_headroom_and_reserve_bytes'], 91_028_500_374)
    observed_model_stat = MODEL.stat()
    assert observed_model_stat.st_size == authoritative['model_stat']['bytes']
    assert observed_model_stat.st_mtime_ns == authoritative['model_stat']['modified_ns']

    training_binding = pin('canonical-codec-01/train_weak_supervision.json')
    inputs_binding = pin('canonical-codec-01/target_free_inputs.json')
    training = load(training_binding['path'])
    inputs = load(inputs_binding['path'])
    assert training['split'] == 'train' and training['neural_training_executed'] is False
    assert len(training['rows']) == training['row_count'] == 16
    assert len(inputs['rows']) == inputs['row_count'] == 34
    assert inputs['contains_canonical_ir'] is inputs['contains_target_token_ids'] is inputs['training_executed'] is False
    require_int(len({row['id'] for row in inputs['rows']}), 34)
    input_by_id = {row['id']: row for row in inputs['rows']}
    expected_profile = 'thenlper/gte-small@17e1f347d17fe144873b1201da91788898c639cd:d384:pool=mean:norm=l2:precision=float32:input_policy=exact_source_no_truncation'
    for row in inputs['rows']:
        assert row['source_sha256'] == hashlib.sha256(row['source_text'].encode('utf-8')).hexdigest()
        assert row['context_sha256'] == hashlib.sha256(row['context_text'].encode('utf-8')).hexdigest()
        assert set(row['embeddings']) == {'legacy8', 'native384', 'native768'}
        for lane, dimension in [('legacy8', 8), ('native384', 384), ('native768', 768)]:
            vector = row['embeddings'][lane]
            require_int(vector['dimension'], dimension)
            assert len(vector['embedding']) == dimension
            assert all(type(number) in (int, float) and math.isfinite(number) for number in vector['embedding'])
        assert row['embeddings']['native384']['profile_id'] == expected_profile
    group_counts = Counter()
    target_ids, rules = [], []
    anchor_count = 0
    for row in training['rows']:
        assert set(row['masks']) == set(MASKS)
        for key, expected in MASKS.items():
            require_int(row['masks'][key], expected)
        assert row['source_sha256'] == row['proposal']['source_sha256'] == input_by_id[row['id']]['source_sha256']
        assert row['independent_semantic_review_completed'] is row['source_fidelity_established'] is row['proof_authority'] is row['qualified'] is False
        assert set(row['proposal']['canonical_ir']) == {'rules'}
        assert len(row['proposal']['canonical_ir']['rules']) == 1
        rule = row['proposal']['canonical_ir']['rules'][0]
        assert set(rule) == set(FACETS)
        rules.append(rule)
        target_ids.append(digest(row['proposal']['canonical_ir']))
        group_counts[row['group_id']] += 1
        anchor_count += len(row['proposal']['anchors'])
    require_int(len(set(target_ids)), 16)
    require_int(anchor_count, 124)
    assert len(group_counts) == 4 and set(group_counts.values()) == {4}
    feature_widths = {facet: len({rule[facet] for rule in rules}) + 1 if index < 4 else
                      len({value for rule in rules for value in rule[facet]}) + 1
                      for index, facet in enumerate(FACETS)}
    require_int(sum(feature_widths.values()), 27)
    optional_qualifier_pairs = [(left, right) for left, a in enumerate(rules) for right, b in enumerate(rules)
                               if left != right and all(a[facet] == b[facet] for facet in CORE)
                               and any(a[facet] != b[facet] for facet in FACETS[4:])]
    old_hard_pairs = [(left, right) for left, a in enumerate(rules) for right, b in enumerate(rules)
                      if all(a[facet] == b[facet] for facet in ('modality', 'actor', 'object'))
                      and a['action'] != b['action']]
    action_positive_pairs = [(left, right) for left, a in enumerate(rules) for right, b in enumerate(rules)
                             if a['action'] == b['action'] and a['actor'] != b['actor']]
    assert len(optional_qualifier_pairs) == 8 and not old_hard_pairs and not action_positive_pairs
    head_parameter_counts = {str(width): width * (384 + 27 + 2) for width in (384, 512)}
    assert head_parameter_counts == {'384': 158592, '512': 211456}

    prototype_owners = []
    for relative, expected in OWNER_HASHES.items():
        prototype_owners.append(verify(dict(path=str(REPO / 'ipfs_datasets_py' / relative), sha256=expected)))
    projection_source = Path(prototype_owners[0]['path']).read_text(encoding='utf-8')
    assignments = {node.targets[0].id: node.value.value for node in ast.parse(projection_source).body
                   if isinstance(node, ast.Assign) and len(node.targets) == 1
                   and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Constant)}
    assert assignments['SOURCE_SPACE_ID'] == expected_profile

    document_bindings = [pin('label_admission_contract_design.md'), pin('contrastive_prototype_design.md'),
                         pin('alignment-next-experiments-report.md'),
                         verify(dict(path=str(MAIN_PLAN), sha256=MAIN_PLAN_SHA))]
    label_text = Path(document_bindings[0]['path']).read_text(encoding='utf-8')
    prototype_text = Path(document_bindings[1]['path']).read_text(encoding='utf-8')
    assert label_text.startswith('# Semantic label admission evidence contract')
    assert 'Design only; no reviews, verification, adjudication, labels or mask changes.' in label_text
    assert 'Verification and admission remain separate, unavailable operations.' in label_text
    assert 'All five current masks stay zero.' in label_text
    assert prototype_text.startswith('# Proposed weak contrastive prototype')
    assert '`weak_decoder_fit=1` does not admit alignment training: `contrastive_supervision=0`' in prototype_text
    assert '960 requested main updates' in prototype_text
    assert 'proposed, not executed or measured' in prototype_text
    assert 'separately versioned weak-contrastive-diagnostic fit policy/manifest' in prototype_text
    for checksum in OWNER_HASHES.values():
        assert checksum in prototype_text
    for relative in ('canonical-codec-01/train_weak_supervision.json', 'canonical-codec-01/target_free_inputs.json'):
        assert EXPECTED[relative] in prototype_text
    links = []
    for reference in document_bindings:
        document = Path(reference['path'])
        for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            target_path = unquote(target.strip('<>').split('#', 1)[0])
            resolved = (document.parent / target_path).resolve()
            assert resolved.is_file() or resolved == OUTPUT / 'validation.json', target
            links.append(dict(document=str(document), target=target, resolved=str(resolved),
                              planned_validation_output=resolved == OUTPUT / 'validation.json'))
    plan_text = MAIN_PLAN.read_text(encoding='utf-8')
    afi_ids = re.findall(r'^\| (AFI-[0-9]+[ab]?) \|', plan_text, flags=re.M)
    assert len(afi_ids) == len(set(afi_ids)) == 25
    milestones = re.findall(r'^\| (M[0-9]+) ', plan_text, flags=re.M)
    assert milestones == [f'M{index}' for index in range(6)]

    def git(*args):
        return subprocess.run(['git', '-C', str(CHECKOUT), *args], check=True,
                              capture_output=True, text=True, timeout=10).stdout.strip()

    assert git('rev-parse', 'HEAD') == CHECKOUT_HEAD
    assert git('symbolic-ref', '--short', 'HEAD') == CHECKOUT_BRANCH
    assert git('status', '--porcelain=v1', '--untracked-files=normal') == ''
    worktrees = subprocess.run(['git', '-C', str(CHECKOUT), 'worktree', 'list', '--porcelain'],
                              check=True, capture_output=True, text=True, timeout=10).stdout
    own_blocks = [block for block in worktrees.split('\n\n') if block.startswith('worktree ' + str(CHECKOUT) + '\n')]
    assert len(own_blocks) == 1 and any(line == 'locked' or line.startswith('locked ') for line in own_blocks[0].splitlines())
    assert not {'torch', 'numpy', 'spacy', 'transformers', 'llama_cpp'}.intersection(sys.modules)
    runner_binding = verify(binding(__file__))
    for reference in tuple(checked.values()):
        assert binding(reference['path']) == reference

    result = dict(
        schema='alignment-next-experiments-root-static-validation/v1', status='passed_planning_evidence_only',
        runner_binding=runner_binding, prior_validation_binding=prior_binding,
        checked_file_bindings=list(checked.values()), checked_file_count=len(checked),
        preserved_prior_checked_file_count=501,
        preserved_implementation_test_bindings=prior['new_implementation_test_bindings'],
        preserved_historical_document_bindings=[reference for reference in prior['documentation_bindings']
                                                if Path(reference['path']).resolve() != MAIN_PLAN.resolve()],
        mutable_main_plan_historical_reference=historic_main_plan[0],
        mutable_main_plan_preservation_required=False,
        current_main_plan_binding=document_bindings[-1], documentation_bindings=document_bindings,
        local_link_checks=links, work_package_ids=afi_ids, milestone_ids=milestones,
        leanstral_inventory_binding=inventory_binding, leanstral_inventory_runner_binding=inventory_runner_binding,
        saved_vector_audit_rows=2400, saved_vector_audit_finite_values=9_830_400,
        independent_vector_audit_result_metadata_rechecked=True,
        full_vector_numeric_recomputation_this_validator=False,
        saved_fixed_batch_repeatability_established=True,
        batch_peer_order_padding_slot_independence_established=False,
        saved_single_vs_batch_l2=canary['single_vs_batch_l2'], saved_a_b_a_l2=0.0,
        old_unique_source_texts=33, old_exact_source_overlap=0, new_exact_source_overlap=0,
        model_identity_scope='current stat and sealed earlier metadata-prefix audit; full weight digest remains manifest declaration',
        full_model_hash_verified=False, whole_model_bytes_hashed=0,
        original_readiness_binding=snapshots[0][0], authoritative_readiness_binding=authoritative_binding,
        recorded_resource_formula_recomputed=True, runner_preflight_invoked=False,
        recorded_available_memory_bytes=authoritative['memory_observation']['MemAvailable_bytes'],
        recorded_required_memory_bytes=authoritative['common_runner_resource_formula']['estimated_model_headroom_and_reserve_bytes'],
        recorded_available_memory_gib=authoritative['memory_observation']['MemAvailable_bytes'] / GIB,
        recorded_required_memory_gib=authoritative['common_runner_resource_formula']['estimated_model_headroom_and_reserve_bytes'] / GIB,
        recorded_formula_admits_residency=False, new_live_resource_query_executed=False,
        prototype_owner_bindings=prototype_owners, prototype_input_bindings=[training_binding, inputs_binding],
        prototype_train_rows=16, prototype_distinct_targets=16, prototype_anchor_count=124,
        prototype_author_groups=4, prototype_variants_per_group=4, author_groups_are_equivalence_labels=False,
        original_train_masks=MASKS, original_contrastive_masks_enabled=0,
        proposed_weak_diagnostic_fit_policy_required=True, proposed_weak_diagnostic_policy_created=False,
        formal_feature_widths=feature_widths, formal_feature_dimension=27,
        projection_source_dimension=384, proposed_shared_dimensions=[384, 512],
        head_parameter_counts=head_parameter_counts, optional_directed_weak_qualifier_pair_count=8,
        old_action_hard_negative_pair_count=0, old_action_positive_pair_count=0,
        proposed_main_arms=12, proposed_steps_per_arm=80, proposed_main_updates=960, executed_optimizer_updates=0,
        prototype_fit_executed=False, source_encoder_or_projection_imports=False,
        semantic_label_evidence_intake_implemented=False, semantic_label_evidence_intake_executed=False,
        semantic_label_verification_or_admission_executed=False, labels_admitted=0,
        actual_review_submissions=0, authenticated_reviews_created=0, adjudications_completed=0,
        packet_pending_items=64, packet_blank_annotation_slots=512, packet_zero_mask_values=320,
        previous_review_test_result_scope='historical224 tests; no tests run by this prose/static-validation stage',
        model_inference_executed=False, new_embeddings_generated=0, service_operation_executed=False,
        training_executed=False, prover_execution=False, new_retrieval_quality_measurement=False,
        isolated_decoder_checkout=dict(path=str(CHECKOUT), head=CHECKOUT_HEAD, branch=CHECKOUT_BRANCH,
                                      clean=True, locked=True),
        complete_dependency_manifest=False,
        seal_recipe='SHA256 sorted compact UTF8 JSON excluding content_sha256; ensure_ascii=False; allow_nan=False',
        **{field: False for field in FALSE_AUTHORITY},
    )
    result['content_sha256'] = digest(result)
    OUTPUT.mkdir(mode=0o700)
    path = OUTPUT / 'validation.json'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw(result) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    load(path)
    print(json.dumps(dict(validation=binding(path), checked_files=len(checked), preserved_prior_files=501,
                          semantic_labels_admitted=0, optimizer_updates=0), sort_keys=True))


if __name__ == '__main__':
    main()
