#!/usr/bin/env python3
"""Bind unchanged normative state files to verified dimension-specific releases.

Only private metadata files are written. The native import preflight is read-only;
this script does not construct ModelManager, load tensors or contact the Hub.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

BASE = Path('/home/barberb/lift_coding')
DATASETS = BASE / '.worktrees/normative-checkpoint-availability-datasets-20261006'
PRIOR = BASE / 'artifacts/autoencoder-progress-reconciliation-20261006/datasets/reconciliation-findings.json'
HELPERS = BASE / 'artifacts/decoder-profile-recovery-20261006'
sys.dont_write_bytecode = True
sys.path.insert(0, str(HELPERS))
from custody import capture, read, require, source, write


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def pins_in(value):
    """Find concrete original file pins within the independent custody receipt."""
    if isinstance(value, dict):
        if {'path', 'bytes', 'sha256'} <= value.keys():
            yield {key: value[key] for key in ('path', 'bytes', 'sha256')}
        for child in value.values():
            yield from pins_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from pins_in(child)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--authentication', type=Path, required=True)
    parser.add_argument('--release-receipt', type=Path, action='append', required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    options = parser.parse_args()
    require(options.output_directory.is_absolute() and not options.output_directory.exists(),
        'fresh absolute metadata output directory required')
    owner = source(DATASETS, 'ipfs_datasets_py/logic/formalization/autoencoder/ir_model_manager_import.py')
    require(owner['head'] == '61c5db04538596ea00091cd4f013500854368397', 'selected source commit differs')
    spec = importlib.util.spec_from_file_location('normative_native_import', owner['pin']['path'])
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    authentication_pin = capture(options.authentication)
    authentication = json.loads(read(authentication_pin))
    require(authentication.get('schema') == 'normative-checkpoint-authentication/v1'
        and authentication.get('complete') is True
        and authentication.get('closing_endpoint_identity_checks_passed') is True
        and all(value is False for value in authentication['authority'].values()),
        'completed independently scoped candidate authentication required')
    authenticated = list(pins_in(authentication))
    prior_pin = capture(PRIOR)
    previous = json.loads(read(prior_pin))['newer_normative_training_already_published']
    require(previous['qualified'] is False and previous['checkpoint_promoted'] is False,
        'original availability scope differs')
    rows = previous['states']
    require(len(rows) == 8 and len({row['native_tensor_sha256'] for row in rows}) == 4,
        'eight containers/four unique tensor endpoints required')
    releases = []
    for path in options.release_receipt:
        receipt_pin = capture(path)
        receipt = json.loads(read(receipt_pin))
        require(receipt['schema'] == native.PUBLICATION_SCHEMA and receipt['files_verified'] is True,
            'verified native publication receipt required')
        releases.append((receipt_pin, receipt))
    require(len(releases) == 2 and {r['repository_id'] for _, r in releases} == {
        'Publicus/legal-ir-autoencoder-384d', 'Publicus/legal-ir-autoencoder-768d'},
        'exact two dimension-specific release receipts required')
    records = []
    for row in rows:
        original = row['original_complete_state_pin']
        require(original in authenticated and capture(original['path']) == original,
            'original state lacks matching independent custody or changed bytes')
        authenticated_rows = [entry for entry in authentication['states']
            if entry['original_checkpoint_pin']['sha256'] == original['sha256']]
        require(len(authenticated_rows) == 1, 'one independently authenticated state record required')
        authenticated_state = authenticated_rows[0]
        state = json.loads(read(original))
        width, arm, role = row['dimension'], row['arm'], row['role']
        require(width in (384, 768) and state['dimension'] == width,
            'exact native input width required')
        require(state['schema'] == row['serialization_schema'] == 'private-native-dimension-source-state/v1',
            'checkpoint serialization differs')
        require(state['recipe'] == {'name': arm, 'weight': 0.0 if arm == 'normative-wording-zero' else 0.05}
            and arm in ('normative-wording-zero', 'normative-wording-ce'), 'exact completed normative recipe required')
        require(state['role'] == role and role in ('selected', 'last-attempt') and state['selected'] is True,
            'original selected/last diagnostic serialization metadata differs')
        require(state['tensor_sha256'] == row['native_tensor_sha256']
            and len(state['model_state']) == row['full_model_state_entries'] == 32,
            'original complete tensor endpoint differs')
        require(state['codec']['schema'] == 'typed-json-lexical/v1'
            and len(state['codec']['target_vocabulary']) == row['vocabulary_size'] == 32,
            'original codec/vocabulary differs')
        require(authenticated_state['task_id'] == 'semantic_IR_reconstruction'
            and authenticated_state['codec_sha256'] == digest(state['codec'])
            and authenticated_state['tensor_sha256'] == state['tensor_sha256'],
            'authenticated intended task, codec or tensor endpoint differs')
        require(all(state[name] is False for name in ('qualified', 'admitted', 'proof_authority',
            'source_semantics_verified', 'fresh_holdout', 'checkpoint_promoted', 'lake_executed')),
            'candidate serialization must not carry qualification')
        repo = f'Publicus/legal-ir-autoencoder-{width}d'
        receipt = next(r for _, r in releases if r['repository_id'] == repo)
        matching = [entry for entry in receipt['files'] if entry['bytes'] == original['bytes']
            and entry['sha256'] == original['sha256'] and entry['verified'] is True]
        require(len(matching) == 1, 'one exact published state path required per container')
        release = dict(repository_id=repo, revision=receipt['revision'],
            path_in_repo=matching[0]['path_in_repo'], checkpoint_sha256=original['sha256'])
        binding_role = arm.replace('-', '_') + '_' + role.replace('-', '_') + '_semantic_decoder_state'
        model_id = native.ir_model_asset_record_id('legal_ir', width, 'input_embedding',
            binding_role, original['sha256'])
        identity = dict(record_id=model_id, ir_family_id='legal_ir', dimension=width,
            dimension_role='input_embedding', role=binding_role, schema_version=None,
            task_id='semantic_IR_reconstruction', profile_id=None, format_id=None,
            original_checkpoint_pin=original, trained=True, initialization_only=False,
            donor=None, runtime_ready=False, teacher_qualified=False, proof_authority=False)
        config = dict(ir_checkpoint=identity, complete_runtime_io_contract=False,
            checkpoint_serialization_schema=state['schema'],
            native_output_schema_status='unknown_not_inferred_from_checkpoint_serialization',
            study_id='decoder-normative-wording-20261006', training_run_id=f'training-{width}-r1',
            recipe=state['recipe'], original_state_role=role, original_selected_field=state['selected'],
            selected_last_tensor_alias_group=dict(dimension=width, arm=arm, tensor_sha256=state['tensor_sha256']),
            full_model_state_entry_count=32, tensor_sha256=state['tensor_sha256'],
            frozen_weights_sha256=state['weights_sha256'], optimizer_resumable=state['optimizer_resumable'],
            decoder_codec=state['codec'], ordered_codec_sha256=digest(state['codec']),
            saved_input_transform_sha256=digest(state['input_transform']),
            original_lineage=state['lineage'], independent_custody_receipt_pin=authentication_pin,
            immediate_parent_pin={key: authenticated_state['immediate_parent_pin'][key]
                for key in ('path', 'bytes', 'sha256')},
            immediate_parent_tensor_sha256=authenticated_state['immediate_parent_tensor_sha256'],
            continued_initial_state_pin={key: authenticated_state['continued_initial_state_pin'][key]
                for key in ('path', 'bytes', 'sha256')},
            intended_task_scope='Restricted ordered seven-field rule JSON; semantic target review and native output schema qualification remain separate.',
            input_contract=dict(paragraph_width=width, clause_width=width, max_source_clauses=8,
                saved_normalization_required=True, original_width_specific_cached_vectors_required=True,
                original_contextual_facade_recipe_supported=False,
                input_vectors_not_authenticated_by_availability_registration=True),
            declared_decoder_output_token_limit=state['lineage']['teacher_output_limit'],
            documented_encoder_context_tokens=512, long_context_8192_qualified=False,
            source_text_reconstruction_qualified=False, fresh_holdout_qualified=False,
            source_semantics_verified=False, production_checkpoint=False, release=release)
        metadata = dict(model_id=model_id, model_name=f'LegalIR {width}D {arm} {role} candidate decoder',
            model_type='decoder_only', architecture=state['architecture']['schema'],
            inputs=[dict(name='native_paragraph_embedding', data_type='embeddings', shape=[-1, width],
                         description='Declared original native-width cached paragraph input; availability is not encoder-producer authentication.'),
                    dict(name='native_clause_embeddings', data_type='embeddings', shape=[-1, 8, width],
                         description='Mandatory original ordered clause conditioning with saved transforms and zero padding.'),
                    dict(name='clause_mask', data_type='features', shape=[-1, 8], dtype='bool',
                         description='Original source-clause count mask; no gold/reference inputs.')],
            outputs=[dict(name='canonical_ir_tokens', data_type='tokens', shape=[-1, -1], dtype='int64',
                          description='Restricted typed JSON lexical rule tokens; native output schema and prose fidelity unqualified.')],
            huggingface_config=config, model_revision=original['sha256'], revision_id=original['sha256'],
            parent_model_id=native.ir_model_asset_record_id('legal_ir', width, 'input_embedding',
                'selected_contextual_semantic_decoder_state', config['immediate_parent_pin']['sha256']),
            source_url=f'https://huggingface.co/{repo}/blob/{release["revision"]}/{release["path_in_repo"]}',
            tags=['legal_ir', f'{width}d', arm, role, 'candidate-asset', 'runtime-unqualified'],
            description='Unchanged completed normative-wording state container. Last-attempt and selected containers alias four unique tensor endpoints. Registration preserves the saved recipe, codec and lineage; it does not grant native decoder dispatch, teacher quality, prose reconstruction, fresh semantic fidelity or proof authority.')
        records.append(dict(model_metadata=metadata, checkpoint_pin=original, release=release))
    require(len({r['model_metadata']['model_id'] for r in records}) == 8, 'unique serialization/role bindings required')
    options.output_directory.mkdir()
    plan_pin = write(options.output_directory / 'model-manager-import-plan.json',
        dict(schema=native.SCHEMA, models=records))
    native._prepare(plan_pin, [pin for pin, _ in releases], native.MAX_REFERENCE_BYTES)
    summary = dict(schema='normative-model-manager-plan-preparation/v1', completed=True,
        import_plan_pin=plan_pin, independent_authentication_pin=authentication_pin,
        prior_observation_pin=prior_pin, importer_owner=owner,
        release_receipt_pins=[pin for pin, _ in releases], serialization_binding_count=8,
        unique_trained_tensor_count=4, native_preparation_passed=True,
        model_ids=[r['model_metadata']['model_id'] for r in records],
        native_schema_profile_format_remain_null=True, runtime_ready=False,
        teacher_qualified=False, proof_authority=False, manager_or_database_constructed=False)
    summary_pin = write(options.output_directory / 'preparation.json', summary)
    require(capture(options.authentication) == authentication_pin and capture(PRIOR) == prior_pin,
        'input metadata changed during preparation')
    print(json.dumps(dict(preparation_pin=summary_pin, models=8, unique_tensor_endpoints=4)))


if __name__ == '__main__':
    main()
