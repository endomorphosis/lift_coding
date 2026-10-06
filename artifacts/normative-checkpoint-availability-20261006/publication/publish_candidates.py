#!/usr/bin/env python3
"""Private exact-byte staging and review-guarded append-only publication.

Staging uses only the pinned metadata-only native publisher. The --publish path
is for the parent operator after independent review; it never writes a catalog,
loads a model, creates a Hub repository or changes repository settings.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
BASE = Path('/home/barberb/lift_coding')
OUT = BASE / 'artifacts/normative-checkpoint-availability-20261006/publication'
DATASETS = BASE / '.worktrees/normative-checkpoint-availability-datasets-20261006'
SOURCE_COMMIT = '61c5db04538596ea00091cd4f013500854368397'
OWNER_REL = 'ipfs_datasets_py/logic/formalization/autoencoder/ir_model_hub_publish.py'
OWNER = DATASETS / OWNER_REL
AUTH = BASE / 'artifacts/normative-checkpoint-availability-20261006/authentication/authenticated-states.json'
PREFIX = 'releases/20261006-normative-wording-checkpoints-v1'
REPOSITORIES = ('Publicus/legal-ir-autoencoder', 'Publicus/legal-ir-autoencoder-384d',
                'Publicus/legal-ir-autoencoder-768d')
FALSE = {'runtime_admitted': False, 'runtime_ready': False, 'teacher_qualified': False,
         'proof_authority': False, 'quality_qualified': False, 'source_semantics_verified': False,
         'checkpoint_promoted': False, '8192_span_qualified': False}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def closed_pin(value):
    require(type(value) is dict, 'file pin object required')
    result = {key: value[key] for key in ('path', 'bytes', 'sha256')}
    require(type(result['path']) is str and Path(result['path']).is_absolute(), 'absolute pin path required')
    require(type(result['bytes']) is int and 0 <= result['bytes'] <= 512 * 1024 * 1024, 'bounded file pin required')
    require(type(result['sha256']) is str and re.fullmatch('[0-9a-f]{64}', result['sha256']), 'exact SHA256 required')
    return result


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'regular nonsymlink file required')
    size = path.stat().st_size
    require(size <= 512 * 1024 * 1024, 'file byte bound exceeded')
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return {'path': str(path.resolve()), 'bytes': size, 'sha256': digest.hexdigest()}


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')


def write_once(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = pin(path)
        require(existing['bytes'] == len(data) and existing['sha256'] == hashlib.sha256(data).hexdigest(),
                'existing staged/receipt bytes differ; overwrite forbidden')
        return existing
    with path.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    descriptor = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return pin(path)


def load_native():
    require(subprocess.check_output(['git', '--no-optional-locks', '-C', str(DATASETS),
        'rev-parse', 'HEAD'], text=True).strip() == SOURCE_COMMIT, 'native publisher checkout revision changed')
    expected = subprocess.check_output(['git', '--no-optional-locks', '-C', str(DATASETS),
        'show', SOURCE_COMMIT + ':' + OWNER_REL])
    source_pin = pin(OWNER)
    require(source_pin['bytes'] == len(expected) and source_pin['sha256'] == hashlib.sha256(expected).hexdigest(),
            'native publisher owner differs from committed bytes')
    spec = importlib.util.spec_from_file_location('normative_native_hub_publish', OWNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == OWNER.resolve(), 'native publisher import origin differs')
    return module, source_pin


def read_json(native, file_pin):
    raw = native._read_pin(closed_pin(file_pin))
    # Native JSON validation detects duplicate keys and nonfinite values.
    native._json_object(raw)
    return json.loads(raw)


def selected_metadata(state):
    keys = ('dimension', 'dimension_role', 'ir_family_id', 'arm', 'role', 'task_id',
        'serialization_schema', 'tensor_sha256', 'numeric_alias_group', 'selected_header_value',
        'codec', 'codec_sha256', 'lineage', 'full_model_state_entries', 'optimizer_resumable',
        'runtime_api_recipe_supported', 'runtime_api_role_supported', 'decoder_format_id',
        'decoder_profile_id', 'native_ir_schema_version')
    return {**{key: state[key] for key in keys},
        'original_checkpoint_pin': closed_pin(state['original_checkpoint_pin']),
        'immediate_parent_pin': closed_pin(state['immediate_parent_pin']), **FALSE}


def prepare(authentication_sha256):
    require(not (OUT / 'preparation.json').exists(), 'preparation already exists; do not overwrite a frozen stage')
    native, owner_pin = load_native()
    auth_pin = pin(AUTH)
    require(auth_pin['sha256'] == authentication_sha256, 'authentication receipt SHA differs')
    auth = read_json(native, auth_pin)
    require(auth['complete'] is True and auth['serialization_count'] == 8 and
            auth['trained_numeric_endpoint_count'] == 4, 'exact authenticated eight/four inventory required')
    states = auth['states']
    expected = {(dimension, arm, role) for dimension in (384, 768)
        for arm in ('normative-wording-zero', 'normative-wording-ce') for role in ('selected', 'last-attempt')}
    require(len(states) == 8 and {(s['dimension'], s['arm'], s['role']) for s in states} == expected,
            'exact closed dimension/arm/role inventory required')
    require(len({s['tensor_sha256'] for s in states}) == 4, 'four tensor identities required')
    for dimension, arm in {(s['dimension'], s['arm']) for s in states}:
        pair = [s for s in states if s['dimension'] == dimension and s['arm'] == arm]
        require(len({s['tensor_sha256'] for s in pair}) == 1 and
                len({s['numeric_alias_group'] for s in pair}) == 1,
                'selected/last tensor alias join differs')
    inputs = [auth_pin]
    staged = {}
    inventory = []
    for state in states:
        require(state['public_copy_admissible'] is True and state['checkpoint_bytes_authenticated'] is True
                and state['full_model_state_entries'] == 32 and state['optimizer_resumable'] is False,
                'complete nonresumable original state required')
        require(state['ir_family_id'] == 'legal_ir' and state['dimension_role'] == 'input_embedding'
                and state['task_id'] == 'semantic_IR_reconstruction', 'grounded task/input role differs')
        require(state['native_ir_schema_version'] is None and state['decoder_profile_id'] is None
                and state['decoder_format_id'] is None, 'unknown native selectors must remain null')
        source_pin = closed_pin(state['original_checkpoint_pin'])
        raw = native._read_pin(source_pin)
        value = json.loads(raw)
        require(type(value.get('model_state')) is dict and len(value['model_state']) == 32,
                'full32 model-state container required')
        relative = 'checkpoints/' + str(state['dimension']) + 'd/' + state['arm'] + '/' + (
            'selected-state.json' if state['role'] == 'selected' else 'last-attempt-state.json')
        staged[relative] = write_once(OUT / 'stage' / relative, raw)
        require(staged[relative]['sha256'] == source_pin['sha256'], 'state copying changed original bytes')
        inputs.append(source_pin)
        inventory.append({**selected_metadata(state), 'release_relative_path': relative})
    preprocessing = []
    require(len(auth['preprocessing']) == 2 and {p['dimension'] for p in auth['preprocessing']} == {384, 768},
            'two authenticated metadata views required')
    for row in auth['preprocessing']:
        require(row['metadata_public_copy_admissible'] is True and row['direct_public_copy_admissible'] is False,
                'raw preprocessing corpus must not be published')
        source_pin = closed_pin(row['metadata_pin'])
        raw = native._read_pin(source_pin)
        value = json.loads(raw)
        require(value['schema'] == 'normative-frozen-preprocessing-metadata/v1' and
                value['contains_embedding_feature_vectors'] is False, 'metadata-only preprocessing view required')
        require('paragraph_features' not in value['frozen_metadata'] and 'clause_features' not in value['frozen_metadata'],
                'embedding feature arrays cannot be copied')
        relative = 'preprocessing/' + str(row['dimension']) + 'd-metadata.json'
        staged[relative] = write_once(OUT / 'stage' / relative, raw)
        inputs.append(source_pin)
        preprocessing.append({'dimension': row['dimension'], 'metadata_pin': source_pin,
            'original_preprocessing_pin': closed_pin(row['original_preprocessing_pin']),
            'release_relative_path': relative, 'raw_corpus_bundled': False})
    staged['metadata/authenticated-states.json'] = write_once(OUT / 'stage/metadata/authenticated-states.json',
                                                           native._read_pin(auth_pin))
    published_source = []
    for path, relative in (
        ('docs/autoencoders/normative_wording_training.md', 'evidence/normative_wording_training.md'),
        ('docs/implementation/reports/evidence/decoder-normative-wording-20261006/results.json', 'evidence/results.json')):
        size = int(subprocess.check_output(['git', '--no-optional-locks', '-C', str(DATASETS),
            'cat-file', '-s', SOURCE_COMMIT + ':' + path], text=True).strip())
        if size > 1024 * 1024:
            require(path.endswith('/results.json'), 'only known report may be omitted by size')
            blob = subprocess.check_output(['git', '--no-optional-locks', '-C', str(DATASETS),
                'rev-parse', SOURCE_COMMIT + ':' + path], text=True).strip()
            saved = auth['published_result_pin']
            require(saved['bytes'] == size and saved['git_blob_oid'] == blob,
                    'omitted report differs from authenticated immutable source')
            published_source.append({'commit': SOURCE_COMMIT, 'path': path, 'bytes': size,
                'git_blob_oid': blob, 'sha256': saved['sha256'], 'bundled': False,
                'omission_reason': 'exceeds bounded metadata evidence-copy limit',
                'url': 'https://github.com/endomorphosis/ipfs_datasets_py/blob/' + SOURCE_COMMIT + '/' + path})
            continue
        raw = subprocess.check_output(['git', '--no-optional-locks', '-C', str(DATASETS),
            'show', SOURCE_COMMIT + ':' + path])
        require(0 < len(raw) <= 1024 * 1024, 'published documentation/report byte bound exceeded')
        if path.endswith('.json'):
            native._json_object(raw)
        staged[relative] = write_once(OUT / 'stage' / relative, raw)
        published_source.append({'commit': SOURCE_COMMIT, 'path': path,
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'bundled': True})
    plans, manifests = [], []
    for repo in REPOSITORIES:
        dimension = 384 if repo.endswith('-384d') else 768 if repo.endswith('-768d') else None
        lane_states = [s for s in inventory if dimension is None or s['dimension'] == dimension]
        lane_preprocessing = [p for p in preprocessing if dimension is None or p['dimension'] == dimension]
        lane_keys = [s['release_relative_path'] for s in lane_states] + [p['release_relative_path'] for p in lane_preprocessing]
        lane_keys += ['metadata/authenticated-states.json', 'evidence/normative_wording_training.md']
        if 'evidence/results.json' in staged:
            lane_keys.append('evidence/results.json')
        folder = OUT / 'repository-metadata' / repo.replace('/', '--')
        readme = ('# Normative wording LegalIR candidate checkpoints\n\n'
            'This release preserves exact existing trained candidate bytes. It does not promote a decoder.\n\n'
            'The complete study has four unique tensor endpoints and eight serialized states: selected and '
            'last-attempt aliases for zero and 0.05 modality-loss arms at 384D and 768D. This repository contains '
            + str(len(lane_states)) + ' state files. Each has all 32 model-state entries, but no optimizer/resume '
            'contract. Native output schema/version, decoder profile and format identities remain unknown.\n\n'
            'The task is semantic_IR_reconstruction with native 384D/768D paragraph input, ordered eight clause '
            'vectors and a boolean mask. Apply the saved TRAIN-only input transform to real clause vectors '
            'once, then zero-pad; saved internal paragraph/clause normalization is a separate stage. Existing '
            'width-specific assets and embeddings were reused. Publication generates no embeddings.\n\n'
            'The recorded experiment uses 512-token source scope and 512-token decoder output. The 768D encoder\'s '
            '8192-token capacity does not qualify 8192-token reconstruction. The original contextual facade\'s '
            'saved recipe is unsupported for these normative states. Donor weights, original preprocessing '
            'corpora, raw vectors and executable model code are not bundled; metadata extracts preserve '
            'normalization/transform/initializer/prior values and original custody pins. This release alone '
            'does not supply a complete runtime restoration closure or a trained legal-text reconstruction head.\n\n'
            'Runtime readiness, teacher/quality qualification, source-semantics and proof authority are false. '
            'The prospective 60-row wording panel uses previously exposed meanings; it is not a fresh semantic '
            'holdout. Source/context inventory correspondence is separate from independent encoder-producer authentication.\n')
        readme_pin = write_once(folder / 'README.md', readme.encode('utf-8'))
        manifest = {'schema': 'normative-wording-candidate-release/v1', 'repository_id': repo,
            'release_prefix': PREFIX, 'dimension': dimension, 'global_tensor_endpoint_count': 4,
            'global_serialization_count': 8, 'repository_serialization_count': len(lane_states),
            'states': lane_states, 'preprocessing_metadata_views': lane_preprocessing,
            'authentication_source_pin': auth_pin, 'published_source': published_source,
            'original_states_copied_byte_exact': True, 'raw_embedding_corpus_bundled': False,
            'original_parent_weights_bundled': False, 'optimizer_resumable': False,
            'runtime_restoration_closure_bundled': False, 'source_scope_tokens': 512,
            'decoder_output_budget_tokens': 512, 'native_ir_schema_version': None,
            'decoder_profile_id': None, 'decoder_format_id': None,
            'task_id': 'semantic_IR_reconstruction', 'input_dimension_role': 'input_embedding', **FALSE}
        manifest_pin = write_once(folder / 'manifest.json', json_bytes(manifest))
        operations = [{'file_pin': staged[key], 'path_in_repo': PREFIX + '/' + key} for key in lane_keys]
        operations += [{'file_pin': readme_pin, 'path_in_repo': PREFIX + '/README.md'},
                       {'file_pin': manifest_pin, 'path_in_repo': PREFIX + '/manifest.json'}]
        plan = {'schema': native.PLAN_SCHEMA, 'manifest_pin': manifest_pin, 'repository_id': repo,
                'private_new': False, 'operations': operations}
        captured = native._capture_plan(plan)
        native._freeze_files(captured)
        plans.append(write_once(OUT / 'plans' / (repo.replace('/', '--') + '.json'), json_bytes(captured)))
        manifests.extend([readme_pin, manifest_pin])
    for source_pin in inputs:
        native._read_pin(source_pin)
    staged_pins = sorted(list(staged.values()) + manifests, key=lambda p: p['path'])
    preparation = {'schema': 'normative-checkpoint-publication-preparation/v1',
        'driver_pin': pin(Path(__file__).resolve()), 'native_publisher_pin': owner_pin,
        'native_source_commit': SOURCE_COMMIT, 'authentication_pin': auth_pin,
        'authentication_source_inputs_for_stage_pins': inputs,
        'plan_pins': plans, 'staged_file_pins': staged_pins, 'repository_ids': list(REPOSITORIES),
        'release_prefix': PREFIX, 'existing_repositories_only': True, 'root_paths_replaced': False,
        'complete_state_count': 8, 'tensor_endpoint_count': 4, 'preprocessing_metadata_only_count': 2,
        'native_plans_validated_and_file_fenced': True, 'prepared_without_network': True,
        'publication_executed': False, 'database_write_executed': False, **FALSE}
    preparation_pin = write_once(OUT / 'preparation.json', json_bytes(preparation))
    print(json.dumps({'preparation_pin': preparation_pin, 'plan_count': len(plans), 'publication_executed': False}))


def remote_snapshot(native, api, repo, revision=None):
    sha, private, rows = native._info(api, repo, revision)
    info = api.model_info(repo, revision=sha, files_metadata=False)
    settings = {'private': private, 'gated': getattr(info, 'gated', None),
                'disabled': getattr(info, 'disabled', None)}
    identities = {}
    for path, row in rows.items():
        lfs = native._field(row, 'lfs')
        identities[path] = {'bytes': native._field(row, 'size'),
            'git_blob_oid': native._field(row, 'blob_id', 'blobId'),
            'lfs_sha256': native._field(lfs, 'sha256') if lfs is not None else None,
            'lfs_bytes': native._field(lfs, 'size') if lfs is not None else None}
        require(type(identities[path]['bytes']) is int and type(identities[path]['git_blob_oid']) is str,
                'complete prior remote file identity required')
    return {'repository_id': repo, 'revision': sha, 'settings': settings, 'file_identities': identities}


class ExistingAppendOnlyApi:
    """Only model_info and exact reviewed additions reach the genuine HfApi."""
    def __init__(self, api, repo, baseline, allowed_paths):
        self._api, self._repo, self._baseline = api, repo, baseline
        self._allowed_paths = set(allowed_paths)

    def model_info(self, repository_id, **kwargs):
        require(repository_id == self._repo, 'unexpected repository access')
        value = self._api.model_info(repository_id, **kwargs)
        if kwargs.get('revision') is None:
            require(value.sha == self._baseline['revision'], 'repository head changed before append')
        return value

    def create_repo(self, *_args, **_kwargs):
        raise ValueError('existing repositories only; creation is forbidden')

    def create_commit(self, repository_id, **kwargs):
        from huggingface_hub import CommitOperationAdd
        require(repository_id == self._repo and kwargs.get('repo_type') == 'model'
            and kwargs.get('parent_commit') == self._baseline['revision'], 'exact parent-commit fence required')
        operations = kwargs.get('operations')
        require(type(operations) is list and all(isinstance(op, CommitOperationAdd) for op in operations),
                'only genuine add operations permitted')
        destinations = [op.path_in_repo for op in operations]
        require(len(destinations) == len(set(destinations)) and set(destinations) <= self._allowed_paths,
                'unreviewed destination')
        require(all(path.startswith(PREFIX + '/') and path not in self._baseline['file_identities']
                    for path in destinations), 'only absent release-prefix paths may be appended')
        return self._api.create_commit(repository_id, **kwargs)


def fence_preparation(native, preparation, preparation_pin):
    read_json(native, preparation_pin)
    require(pin(Path(__file__).resolve()) == preparation['driver_pin'], 'driver differs from frozen preparation')
    require(pin(OWNER) == preparation['native_publisher_pin'], 'native publisher differs from preparation')
    for file_pin in preparation['authentication_source_inputs_for_stage_pins'] + preparation['staged_file_pins']:
        native._read_pin(file_pin)
    for plan_pin in preparation['plan_pins']:
        plan = native._capture_plan(read_json(native, plan_pin))
        native._freeze_files(plan)


def publish(preparation_sha256, review_arguments):
    native, owner_pin = load_native()
    preparation_pin = pin(OUT / 'preparation.json')
    require(preparation_pin['sha256'] == preparation_sha256, 'explicit preparation SHA differs')
    preparation = read_json(native, preparation_pin)
    require(preparation['schema'] == 'normative-checkpoint-publication-preparation/v1' and
            preparation['native_publisher_pin'] == owner_pin and preparation['existing_repositories_only'] is True,
            'preparation identity/contract differs')
    require(preparation['repository_ids'] == list(REPOSITORIES) and len(preparation['plan_pins']) == 3,
            'exact three repository plans required')
    require(review_arguments, 'independent approval receipt pin required before Hub access')
    review_pins = []
    for argument in review_arguments:
        path, sha = argument.rsplit('=', 1)
        review_pin = pin(Path(path).resolve())
        require(review_pin['sha256'] == sha, 'explicit review receipt SHA differs')
        review = read_json(native, review_pin)
        require(review['schema'] == 'normative-candidate-publication-driver-review/v1' and
                review['approved'] is True and review['findings'] == [], 'independent approval required')
        require(review['reviewed_driver_pin'] == preparation['driver_pin'] and
                review['reviewed_preparation_pin'] == preparation_pin and
                review['reviewed_native_publisher_pin'] == preparation['native_publisher_pin'] and
                review['reviewed_authentication_pin'] == preparation['authentication_pin'] and
                review['reviewed_stage_pins'] == preparation['staged_file_pins'] and
                review['reviewed_plan_pins'] == preparation['plan_pins'], 'review does not bind exact prepared bytes')
        review_pins.append(review_pin)
    fence_preparation(native, preparation, preparation_pin)
    from huggingface_hub import HfApi
    api = HfApi(endpoint='https://huggingface.co')
    run = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    for index, plan_pin in enumerate(preparation['plan_pins']):
        plan = native._capture_plan(read_json(native, plan_pin))
        require(plan['repository_id'] == REPOSITORIES[index], 'repository plan order differs')
        require(all(op['path_in_repo'].startswith(PREFIX + '/') for op in plan['operations']), 'root paths forbidden')
        envelope = {'schema': 'normative-candidate-publication-attempt/v1', 'preparation_pin': preparation_pin,
            'plan_pin': plan_pin, 'review_receipt_pins': review_pins, 'repository_id': plan['repository_id'],
            'complete': False, 'native_publication_receipt': None, **FALSE}
        receipt_path = OUT / 'receipts' / (run + '-' + str(index + 1) + '-' + plan['repository_id'].replace('/', '--') + '.json')
        try:
            fence_preparation(native, preparation, preparation_pin)
            for review_pin in review_pins:
                native._read_pin(review_pin)
            before = remote_snapshot(native, api, plan['repository_id'])
            require(before['settings']['private'] is False, 'existing public repository required')
            adapter = ExistingAppendOnlyApi(api, plan['repository_id'], before,
                                           [op['path_in_repo'] for op in plan['operations']])
            receipt = native.publish_ir_model_hub_release(plan, api=adapter)
            envelope['native_publication_receipt'] = receipt
            after = remote_snapshot(native, api, plan['repository_id'], receipt['revision'])
            require(before['settings'] == after['settings'], 'repository settings changed')
            require(all(after['file_identities'].get(path) == identity for path, identity in before['file_identities'].items()),
                    'a prior remote file identity changed')
            fence_preparation(native, preparation, preparation_pin)
            envelope.update(complete=True, prior_remote_file_count=len(before['file_identities']),
                prior_remote_file_identities_sha256=hashlib.sha256(json_bytes(before['file_identities'])).hexdigest(),
                initial_revision=before['revision'], returned_revision=after['revision'],
                observed_repository_settings=before['settings'], all_prior_remote_file_identities_preserved=True,
                observed_repository_settings_preserved=True, settings_mutation_API_exposed=False,
                existing_only=True, append_only=True, cross_repository_transaction_atomic=False)
            durable_pin = write_once(receipt_path, json_bytes(envelope))
            print(json.dumps({'durable_receipt_pin': durable_pin, 'complete': True}), flush=True)
        except Exception as error:
            if isinstance(error, native.HubPublicationError):
                envelope['native_publication_receipt'] = error.receipt
            envelope['failure_type'] = type(error).__name__
            durable_pin = write_once(receipt_path, json_bytes(envelope))
            print(json.dumps({'durable_receipt_pin': durable_pin, 'complete': False}), flush=True)
            raise


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--publish', action='store_true')
    parser.add_argument('--authentication-sha256')
    parser.add_argument('--preparation-sha256')
    parser.add_argument('--review-receipt', action='append', default=[], help='absolute receipt path=SHA256')
    args = parser.parse_args()
    if args.prepare:
        require(args.authentication_sha256 is not None, 'explicit authentication SHA required')
        prepare(args.authentication_sha256)
    else:
        require(args.preparation_sha256 is not None, 'explicit preparation SHA required')
        publish(args.preparation_sha256, args.review_receipt)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Provider exception strings/tracebacks may contain request details.
        print(json.dumps({'failed': True, 'failure_type': type(error).__name__}), file=sys.stderr)
        raise SystemExit(1)
