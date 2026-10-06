"""Read committed API source and prior receipts; never open the selected database.

This private artifact reproduces the metadata survey. It imports only stdlib,
reads fixed Git objects, and writes one detached survey JSON beside itself.
It does not import either project, read checkpoint payloads, change refs, call
the Hub, construct ModelManager, or execute a training/inference operation.
"""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import stat
import subprocess

ROOT = Path('/home/barberb/lift_coding')
OUT = Path(__file__).resolve().parent
ACCELERATE = ROOT / '.worktrees/contextual-legal-runtime-accelerate-20261006'
DATASETS = ROOT / '.worktrees/autoencoder-progress-reconciliation-datasets-20261006'
ACCELERATE_COMMIT = '45803f0dca3365982b6058bf7e7c9c94a95aefcf'
DATASETS_COMMIT = '61c5db04538596ea00091cd4f013500854368397'
OLD_ACCELERATE = '26dc83812d25093594752fedf3c0ef5b998f4d79'
OLD_DATASETS = '3b3b994407b2fcfef955ce5153afc2eea01e4eff'
STORE = ROOT / 'external/ipfs_accelerate/model_manager.duckdb'
PRIOR = ROOT / 'artifacts/decoder-profile-recovery-20261006'


def git(repository, *arguments):
    return subprocess.run(['git', '-C', str(repository), *arguments],
                          capture_output=True, check=True).stdout


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def inspect(repository, current, previous, relative, names):
    raw = git(repository, 'show', current + ':' + relative)
    old = git(repository, 'show', previous + ':' + relative)
    tree = ast.parse(raw.decode('utf-8'))
    declarations = []
    for parent in tree.body:
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes = [(None, parent)]
        elif isinstance(parent, ast.ClassDef):
            nodes = [(parent.name, item) for item in parent.body
                     if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
        else:
            nodes = []
        for owner, node in nodes:
            qualified = (owner + '.' if owner else '') + node.name
            if qualified in names:
                declarations.append({'name': qualified, 'line': node.lineno,
                    'end_line': node.end_lineno,
                    'arguments': ast.unparse(node.args),
                    'docstring': ast.get_docstring(node)})
    return {'repository': str(repository), 'commit': current,
            'relative_path': relative, 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob_oid': git(repository, 'rev-parse', current + ':' + relative).decode().strip(),
            'prior_commit': previous, 'bytes_identical_to_prior': raw == old,
            'declarations': declarations}


def main():
    sources = [
        inspect(ACCELERATE, ACCELERATE_COMMIT, OLD_ACCELERATE,
            'ipfs_accelerate_py/model_manager.py',
            {'ModelManager.__init__', 'ModelManager.add_model',
             'ModelManager.get_model', 'ModelManager.close',
             'ModelManager._save_to_database', 'ModelManager._record_model_access'}),
        inspect(ACCELERATE, ACCELERATE_COMMIT, OLD_ACCELERATE,
            'ipfs_accelerate_py/model_catalog/sources/ir_persistent.py',
            {'IRPersistentCatalogSource.__init__', 'IRPersistentCatalogSource.load',
             'IRPersistentCatalogSource.refresh', 'IRPersistentCatalogSource.resolve_ir_binding',
             'IRPersistentCatalogResult.resolve_ir_binding'}),
        inspect(ACCELERATE, ACCELERATE_COMMIT, OLD_ACCELERATE,
            'ipfs_accelerate_py/model_catalog/sources/persistent.py', set()),
        inspect(DATASETS, DATASETS_COMMIT, OLD_DATASETS,
            'ipfs_datasets_py/logic/formalization/autoencoder/ir_model_manager_import.py',
            {'ir_model_asset_record_id', 'ir_model_component_record_id',
             'import_ir_model_manager_records', '_prepare', '_metadata', '_matches'}),
        inspect(DATASETS, DATASETS_COMMIT, OLD_DATASETS,
            'ipfs_datasets_py/logic/formalization/autoencoder/ir_model_hub_publish.py',
            {'publish_ir_model_hub_release'}),
    ]
    registration = json.loads((PRIOR / 'model-manager-registration.json').read_text())
    mirrors = json.loads((PRIOR / 'dimension-mirrors/publication-summary.json').read_text())
    stats = STORE.lstat()
    report = {
        'schema': 'normative-candidate-native-api-survey/v1',
        'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_scope': 'Fixed committed Git objects; current worktree HEAD is not assumed to match them.',
        'accelerate_commit': ACCELERATE_COMMIT, 'datasets_commit': DATASETS_COMMIT,
        'sources': sources,
        'all_five_relevant_current_source_files_identical_to_prior_registration_owners':
            all(item['bytes_identical_to_prior'] for item in sources),
        'selected_store': {'path': str(STORE), 'regular_file': stat.S_ISREG(stats.st_mode),
            'bytes': stats.st_size, 'mtime_ns': stats.st_mtime_ns,
            'content_read': False, 'database_connection_opened': False,
            'current_record_count': None, 'current_catalog_revision': None},
        'prior_registration': {
            'receipt_pin': pin(PRIOR / 'model-manager-registration.json'),
            'completed': registration['completed'],
            'before_count': registration['before_count'],
            'after_count': registration['after_count'],
            'current_record_count_claimed': False,
            'record_ids': registration['new_model_ids'],
            'cold_native_readback_verified': registration['cold_native_readback_verified'],
            'cold_genuine_manager_reload_verified': registration['cold_genuine_manager_reload_verified'],
            'driver_pin': pin(PRIOR / 'register_original_contextual_states.py'),
            'import_plan_pin': pin(PRIOR / 'contextual-model-manager-import-plan.json'),
            'native_result_pin': pin(PRIOR / 'model-manager-api-import-result.json'),
        },
        'existing_dimension_repositories': {
            'receipt_pin': pin(PRIOR / 'dimension-mirrors/publication-summary.json'),
            'repositories': [{'dimension': item['dimension'],
                'repository_id': item['repository_id'],
                'prior_immutable_mirror_revision': item['revision']} for item in mirrors['outcomes']],
            'current_remote_heads_observed': False,
            'publisher_driver_pin': pin(PRIOR / 'dimension-mirrors/publish_dimension_mirrors.py'),
        },
        'binding_representation': {
            'public_IRModelAssetBinding_class_found': False,
            'native_representation': 'ir-model-asset-binding/v1 deterministic record ID plus huggingface_config.ir_checkpoint declaration',
            'asset_id_hash_fields': ['ir_family_id', 'dimension', 'dimension_role', 'role', 'checkpoint_sha256'],
            'exact_catalog_selector_fields': ['record_id', 'ir_family_id', 'dimension',
                'dimension_role', 'schema_version', 'task_id', 'profile_id', 'format_id',
                'checkpoint_sha256', 'role'],
            'task_schema_profile_format_or_run_are_not_implicitly_hashed': True,
        },
        'known_source_requirements': {
            'public_import_requires_verified_immutable_publication_receipts_first': True,
            'all_collisions_inspected_before_first_add': True,
            'matching_existing_records_skipped_by_import_adapter': True,
            'driver_must_supply_independently_reopened_persisted_readback': True,
            'adapter_cannot_authenticate_readback_implementation_or_remote_account': True,
            'genuine_manager_save_and_close_rewrite_all_in_memory_rows_and_updated_at': True,
            'genuine_manager_save_errors_are_logged_so_add_success_is_not_persistence_proof': True,
            'catalog_import_or_refresh_does_not_update_other_running_managers': True,
            'null_native_output_schema_profile_format_must_remain_explicit': True,
            'serving_config_forbidden_by_import_plan': True,
        },
        'survey_authority': {'read_only': True, 'ModelManager_constructed': False,
            'database_opened': False, 'checkpoint_payload_read': False,
            'models_loaded': False, 'training_or_inference': False,
            'HF_calls': False, 'refs_changed': False, 'runtime_qualified': False,
            'teacher_qualified': False, 'proof_authority': False},
    }
    destination = OUT / 'findings.json'
    payload = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
    destination.write_bytes(payload)
    print(json.dumps({'path': str(destination), 'bytes': len(payload),
                      'sha256': hashlib.sha256(payload).hexdigest()}))


if __name__ == '__main__':
    main()
