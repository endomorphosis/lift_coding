"""Static scientific provenance inventory; never imports a model or writes a repository."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
OUT = Path(__file__).resolve().parent
P = ROOT / 'artifacts/autoformalization-publication-20261004'
ALIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
V1 = ROOT / 'artifacts/legal-grouped-head-training-20261006'
V2 = ROOT / 'artifacts/legal-grouped-head-v2-20261006'
MAINS = {str(ROOT): 'b0ba1aaa9c8a3f1d0e42bca31aa710f1108c686e',
         str(REPO): '795d960170214d03e2eaf4c0a13ad4eb922c5c08'}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def ref(path):
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def load(path):
    return json.loads(path.read_text())


def git_bytes(repo, revision, path):
    result = subprocess.run(['git', '-C', str(repo), 'show', revision + ':' + path], capture_output=True)
    return result.stdout if result.returncode == 0 else None


def verify_ref(binding):
    path = Path(binding['path'])
    result = {'expected': binding, 'local_exists': path.is_file(), 'numerically_loaded': False}
    if path.is_file():
        result['observed'] = ref(path)
        result['bytes_and_sha_match'] = (result['observed']['sha256'] == binding['sha256']
                                         and result['observed']['bytes'] == binding['bytes'])
    return result


prior_path = ROOT / 'artifacts/autoencoder-integration-review-20261006/findings/evidence-matrix.json'
prior = load(prior_path)
studies = []
for study in prior['entries']:
    source = study['source']
    repo = Path(source['repository'])
    original = git_bytes(repo, source['commit'], source['path'])
    latest = git_bytes(repo, MAINS[str(repo)], source['path'])
    reachable = subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', source['commit'], MAINS[str(repo)]], capture_output=True).returncode == 0
    studies.append({**study, 'independent_static_verification': {
        'original_git_blob_sha_matches': original is not None and hashlib.sha256(original).hexdigest() == source['sha256'],
        'original_git_blob_size_matches': original is not None and len(original) == source['bytes'],
        'reachable_from_new_pinned_main': reachable,
        'new_pinned_main_has_identical_report_bytes': latest == original and original is not None,
        'new_pinned_main_report_present': latest is not None,
        'new_pinned_main': MAINS[str(repo)],
    }})

catalog_path = REPO / 'configs/autoencoders/legal_autoencoder_lineages.json'
catalog = load(catalog_path)
teacher = catalog['lineages']['legacy_hub_v1']
teacher_path = Path('/home/barberb/portland-laws.github.io/ipfs_datasets_py/workspace/todo-queues/legal-ir-autoencoder-canonical.state.json')
teacher_local = verify_ref({'path': str(teacher_path), 'sha256': teacher['checkpoint_policy']['sha256'], 'bytes': teacher['checkpoint_policy']['size_bytes']})
students = [verify_ref(row['checkpoint']) for row in catalog['lineages']['current_legal_v2']['retained_examples']['trained_checkpoints']]
sidecar_path = P / 'huggingface/formula_sidecar_inventory.json'
sidecars = load(sidecar_path)
sidecar_states = []
for comparison in sidecars['comparisons']:
    for arm in comparison['arms']:
        for state in arm['states']:
            sidecar_states.append({'arm': arm['arm'], 'dimension': arm['dimension'],
                'completed_optimizer_steps': arm['completed_optimizer_steps'],
                'optimizer_resumable': state['optimizer_resumable'],
                'verification': verify_ref(state['file_binding'])})

expanded_path = P / 'expansion/expanded-weight-references-01.json'
expanded = load(expanded_path)
expanded_weights = []
for record in expanded['weight_file_references']:
    path = P / 'expansion/hf-stage-01' / record['path']
    expanded_weights.append({**record, 'local_stage_verification': verify_ref({
        'path': str(path), 'sha256': record['sha256'], 'bytes': record['bytes']})})

publication_paths = [P / 'huggingface/retained_publication_receipt.json',
    P / 'huggingface/legal-ir-autoencoder-publication.json',
    P / 'all_weights/staging-review-final-remote-publication-01.json',
    V1 / 'huggingface-verification.json', V2 / 'huggingface-verification.json']
publication_records = []
for path in publication_paths:
    payload = load(path)
    publication_records.append({'receipt': ref(path), 'retained_receipt_scalars': {
        key: value for key, value in payload.items() if type(value) in (str, bool, int, float, type(None))},
        'network_revalidated_in_this_inventory': False})

alignment_names = ['label-evidence-intake-01/validation.json', 'statement-scope-01/validation.json',
    'stage-workflow-01/validation.json', 'masked-contrastive-01/validation.json',
    'masked-contrastive-01/numerical-02/numerical_assay.json',
    'relation-mask-handoff-01/validation.json', 'review-provenance-01/validation.json']
alignment_evidence = []
for name in alignment_names:
    path = ALIGN / name
    payload = load(path)
    alignment_evidence.append({'receipt': ref(path), 'recorded_scalar_outcomes': {
        key: value for key, value in payload.items() if type(value) in (str, bool, int, float, type(None))},
        'numerically_replayed_in_this_inventory': False})

source_paths = [
    'logic/deontic/coordination.py', 'logic/deontic/coordination_decoder.py',
    'logic/autoformal/legal_coordination.py', 'logic/autoformal/legal_coordination_evaluation.py',
    'logic/formalization/autoencoder/legal_grouped_span_decoder.py',
    'logic/formalization/autoencoder/legal_grouped_span_decoder_v2.py',
    'logic/formalization/autoencoder/alignment_projection.py',
    'logic/formalization/autoencoder/alignment_masked_contrastive.py',
    'logic/formalization/autoencoder/alignment_relation_declarations.py',
    'logic/formalization/autoencoder/alignment_relation_mask_handoff.py',
    'logic/formalization/autoencoder/alignment_lane_bundle.py',
    'logic/formalization/autoencoder/alignment_stage_workflow.py',
    'logic/formalization/autoencoder/alignment_review_provenance.py',
    'logic/formalization/autoencoder/checkpoint_hub.py',
    'logic/legal_ir/canonical_binding_review.py',
    'logic/legal_ir/canonical_statement_scope.py', 'logic/legal_ir/canonical_span_decoder.py',
    'optimizers/logic_theorem_optimizer/legal_span_dimensions.py',
    'logic/integration/reasoning/legal_ir_proof_feedback.py',
    'logic/integration/reasoning/legal_ir_proof_router.py',
]
sources = []
for relative in source_paths:
    path = REPO / 'ipfs_datasets_py' / relative
    tree = ast.parse(path.read_text())
    remote = git_bytes(REPO, MAINS[str(REPO)], 'ipfs_datasets_py/' + relative)
    sources.append({'source': ref(path), 'module_docstring': ast.get_docstring(tree),
        'public_functions_and_classes': [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith('_')],
        'pinned_main_present': remote is not None,
        'pinned_main_bytes_identical': remote == path.read_bytes()})

v1_global = load(V1 / 'global-selection.json')
v1_selected = load(Path(v1_global['selected_receipt']['path']))
v2_selected = load(V2 / 'run-02/selected.json')
selected_checkpoints = []
for lane, selected in [('grouped-v1', v1_selected), ('grouped-v2', v2_selected)]:
    selected_checkpoints.append({'lane': lane, 'checkpoint': verify_ref(selected['selected']['checkpoint'])})
v2_completion = load(V2 / 'completion.json')
grouped_evidence = {
    'v1_global_selection': ref(V1 / 'global-selection.json'),
    'v2_selection': ref(V2 / 'run-02/selected.json'),
    'v2_completion': ref(V2 / 'completion.json'),
    'v2_independent_training_review': ref(V2 / 'run-02/independent-training-review.json'),
    'v2_completion_static_review': ref(V2 / 'completion-template-independent-review.json'),
    'selected_checkpoints': selected_checkpoints,
    'v2_training': v2_completion['training'],
    'v1_v2_comparison': v2_completion['architecture_recipe_comparison'],
    'v2_real_uscode_probe': v2_completion['real_uscode_probe'],
    'v2_remaining_gaps': v2_completion['remaining_gaps'],
    'inference_or_training_repeated': False,
}

result = {
    'schema': 'autoencoder-scientific-provenance-consolidation/v1',
    'scope': 'Bounded evidence/owner/checkpoint review; original numerical evidence authenticated as retained bytes, not rerun. Remote publication claims are retained prior verification, not a fresh Hub audit.',
    'runner': ref(Path(__file__)), 'pinned_main_commits_supplied_by_parent': MAINS,
    'prior_matrix': ref(prior_path), 'prior_studies': studies,
    'lineage_catalog': ref(catalog_path),
    'legacy_teacher': {'catalog': teacher, 'local_checkpoint': teacher_local},
    'current384_feature_student_examples': students,
    'formula_sidecar_inventory': {'receipt': ref(sidecar_path),
        'scope': sidecars['scope'], 'states': sidecar_states,
        'state_count': sidecars['state_count'], 'fit_count': sidecars['fit_count'],
        'optimizer_updates_in_historical_reports': sidecars['total_completed_optimizer_updates_in_historical_reports'],
        'not_all_later_sidecar_lineages': True},
    'source_reconstruction_weights': {'receipt': ref(expanded_path), 'revision': expanded['revision'],
        'prefix': expanded['release_prefix'], 'selected_models': expanded['selected_models'],
        'checkpoint_triplets': expanded['checkpoint_triplets'], 'files': expanded_weights},
    'retained_publication_evidence': publication_records,
    'alignment_and_review_contract_evidence': alignment_evidence,
    'owner_api_inventory': sources, 'grouped_decoder_evidence': grouped_evidence,
    'duplicate_publication_receipt': ref(ROOT / 'artifacts/autoencoder-integration-review-20261006/findings/duplicate-publications.json'),
    'model_calls': 0, 'optimizer_updates': 0, 'encoder_calls': 0, 'proof_calls': 0,
    'external_writes': 0, 'repository_writes': 0, 'weights_downloaded': 0,
    'semantic_gold_created': False, 'production_promotion': False,
}
target = OUT / 'scientific-provenance-inventory.json'
assert not target.exists()
target.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps({'inventory': ref(target), 'studies': len(studies),
    'all_original_study_hashes_match': all(s['independent_static_verification']['original_git_blob_sha_matches'] for s in studies),
    'all_new_main_reports_identical': all(s['independent_static_verification']['new_pinned_main_has_identical_report_bytes'] for s in studies),
    'sidecar_state_count': len(sidecar_states), 'expanded_weight_files': len(expanded_weights),
    'owner_count': len(sources)}))
