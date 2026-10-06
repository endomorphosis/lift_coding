"""Reviewed, explicit availability-only import of eight pinned serializations.

Without --register this authenticates metadata/source files and writes a local
preflight receipt only. Live-store execution belongs to the root operator, and
requires a separately pinned independent review receipt. It never imports or
executes an encoder, decoder, optimizer, provider or Hub client.

There are four trained numeric endpoints and eight serialization records:
selected and last-attempt headers are distinct records, not eight teachers.
The live ModelManager owns all actual inserts. Its instance-local save guard
permits only absent target IDs; every genuine close has an empty population.
Sequential file/source/store fences are cooperative, not an atomic snapshot.
"""
import argparse
import datetime
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from custody import capture, read, require, source, witness, write

BASE = Path('/home/barberb/lift_coding')
DATASETS = BASE / '.worktrees/normative-checkpoint-availability-datasets-20261006'
ACCELERATE = BASE / '.worktrees/normative-checkpoint-availability-accelerate-20261006'
DATASETS_HEAD = '61c5db04538596ea00091cd4f013500854368397'
ACCELERATE_HEAD = '45803f0dca3365982b6058bf7e7c9c94a95aefcf'
STORE = BASE / 'external/ipfs_accelerate/model_manager.duckdb'
IMPORTER = 'ipfs_datasets_py/logic/formalization/autoencoder/ir_model_manager_import.py'
MAX_METADATA_BYTES = 8 * 1024**2
MAX_DATABASE_BYTES = 4 * 1024**3
JSON_FIELDS = {'inputs', 'outputs', 'huggingface_config', 'supported_backends',
    'hardware_requirements', 'performance_metrics', 'tags', 'repository_structure', 'serving_config'}
SELECTORS = ('record_id', 'ir_family_id', 'dimension', 'dimension_role', 'schema_version',
    'task_id', 'profile_id', 'format_id', 'checkpoint_sha256', 'role')
FORBIDDEN = {'torch', 'numpy', 'transformers', 'sentence_transformers', 'huggingface_hub',
    'ipfs_accelerate_py.common.storage_wrapper', 'ipfs_accelerate_py.ipfs_kit_integration',
    'ipfs_accelerate_py.datasets_integration', 'ipfs_accelerate_py.model_manager_graphrag'}


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def core_pin(value):
    require(type(value) is dict and {'path', 'bytes', 'sha256'} <= set(value), 'file pin required')
    require(type(value['path']) is str and Path(value['path']).is_absolute(), 'absolute pin path required')
    require(type(value['bytes']) is int and 0 < value['bytes'] <= MAX_DATABASE_BYTES,
            'positive exact bounded pinned size required')
    require(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
            'exact SHA256 required')
    return {key: value[key] for key in ('path', 'bytes', 'sha256')}


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def json_file(pin):
    require(pin['bytes'] <= MAX_METADATA_BYTES, 'metadata byte cap exceeded')
    return json.loads(read(pin), object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def strict_matches(native, actual, expected):
    return native._matches(actual, expected) and wire(native._stable_metadata(actual)) == wire(native._stable_metadata(expected))


def partition_records(native, plan, baseline):
    """Inspect every target collision before a manager can be constructed."""
    by_id = {row['model_id']: row for row in baseline}
    require(len(by_id) == len(baseline), 'unique baseline IDs required')
    ids, absent, present = set(), [], []
    for record in plan['models']:
        metadata = record['model_metadata']
        model_id = metadata['model_id']
        require(model_id not in ids, 'unique target IDs required')
        ids.add(model_id)
        existing = by_id.get(model_id)
        require(existing is None or strict_matches(native, existing, metadata),
                'existing model_id has conflicting metadata: ' + model_id)
        (absent if existing is None else present).append(record)
    return absent, present


def empty_close(manager):
    """Always remove the owned save population, even after partial construction."""
    if manager is None:
        return
    lock = getattr(manager, '_model_lock', None)
    if lock is None:
        manager.models = {}
    else:
        with lock:
            manager.models = {}
    try:
        manager.close()
    finally:
        connection = getattr(manager, 'con', None)
        if connection is not None:
            connection.close()


def guard_save_population(manager, allowed_ids):
    """Delegate to genuine storage only for this instance's absent target IDs."""
    allowed = frozenset(allowed_ids)
    real_save = manager._save_data
    def guarded_save():
        with manager._model_lock:
            require(set(manager.models) <= allowed, 'unapproved owned save population')
            return real_save()
    manager._save_data = guarded_save
    return allowed


def construct_owned_manager(ModelManager, native, baseline, allowed_ids):
    # Retain the object before __init__: early constructor failures must not leave
    # an unbounded full-population close in an exception cleanup path.
    manager = ModelManager.__new__(ModelManager)
    try:
        ModelManager.__init__(manager, storage_path=str(STORE), use_database=True,
            enable_ipfs=False, project_legacy_models=True, usage_service=None)
        require(manager.use_database is True and str(manager.storage_path) == str(STORE),
                'genuine selected DuckDB store differs')
        expected = {row['model_id']: row for row in baseline}
        require(set(manager.models) == set(expected), 'genuine initial loaded population differs')
        for key, row in expected.items():
            require(strict_matches(native, manager.models[key], row),
                    'genuine initial loaded metadata differs: ' + key)
        require(all(getattr(manager, name) is None for name in
            ('_ipfs_backend', '_datasets_manager', '_filesystem_handler', '_provenance_logger',
             '_artifact_storage', '_storage_wrapper', '_knowledge_graph')),
            'optional registration side-effect owner active')
        with manager._model_lock:
            manager.models = {key: item for key, item in manager.models.items() if key in allowed_ids}
        guard_save_population(manager, allowed_ids)
        return manager
    except BaseException:
        empty_close(manager)
        raise


def import_missing(native, plan, baseline, *, make_manager, stage_plan, readback,
                   releases, max_reference_bytes):
    """Fixture-testable mutation boundary; all-present never calls the factory."""
    absent, present = partition_records(native, plan, baseline)
    if not absent:
        return {'missing_count': 0, 'already_present_count': len(present),
                'manager_constructed': False, 'native_result': None, 'missing_plan_pin': None}
    missing_plan = {'schema': plan['schema'], 'models': absent}
    missing_pin = stage_plan(missing_plan)
    manager = None
    try:
        manager = make_manager(frozenset(item['model_metadata']['model_id'] for item in absent))
        result = native.import_ir_model_manager_records(missing_pin,
            release_receipts=releases, manager=manager, readback=readback,
            max_reference_bytes=max_reference_bytes)
        require(result['completed'] is True and result['registered_count'] == len(absent)
                and result['already_present_count'] == 0
                and result['persisted_metadata_matched_count'] == len(absent),
                'every absent target must be newly registered and independently read back')
        return {'missing_count': len(absent), 'already_present_count': len(present),
            'manager_constructed': True, 'native_result': result, 'missing_plan_pin': missing_pin}
    finally:
        empty_close(manager)


def decode(connection):
    cursor = connection.execute('SELECT * FROM model_metadata ORDER BY model_id')
    columns = [item[0] for item in cursor.description]
    rows = []
    for row in cursor.fetchall():
        value = dict(zip(columns, row))
        for key in JSON_FIELDS:
            if value.get(key) is not None:
                value[key] = json.loads(value[key], object_pairs_hook=pairs,
                    parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite persisted JSON')))
        for key, item in value.items():
            if isinstance(item, datetime.datetime):
                value[key] = item.isoformat()
        rows.append(value)
    wire(rows)
    return rows


def schema_snapshot(connection):
    tables = connection.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('information_schema','pg_catalog') ORDER BY 1,2").fetchall()
    require(tables == [('main', 'model_metadata')], 'selected existing single model_metadata table required')
    columns = connection.execute("SELECT table_schema, table_name, column_name, ordinal_position, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema NOT IN ('information_schema','pg_catalog') ORDER BY 1,2,4").fetchall()
    indexes = connection.execute('SELECT schema_name, table_name, index_name, is_unique, is_primary, expressions, sql FROM duckdb_indexes() ORDER BY 1,2,3').fetchall()
    return {'tables': [list(row) for row in tables], 'columns': [list(row) for row in columns],
            'indexes': [list(row) for row in indexes]}


def fresh_snapshot(duckdb, *, read_only=True):
    before = store_witness()
    connection = duckdb.connect(str(STORE), read_only=read_only)
    try:
        rows, schema = decode(connection), schema_snapshot(connection)
    finally:
        connection.close()
    require(store_witness() == before, 'selected store changed during native snapshot')
    return rows, schema


def store_witness():
    require(STORE.resolve(strict=True) == STORE, 'selected store parent/path alias changed')
    info = STORE.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and 0 < info.st_size <= MAX_DATABASE_BYTES, 'bounded single-link regular selected store required')
    return witness(info)


def check_population(native, actual, baseline, plan):
    by_id = {row['model_id']: row for row in actual}
    old = {row['model_id']: row for row in baseline}
    targets = {item['model_metadata']['model_id']: item['model_metadata'] for item in plan['models']}
    require(len(by_id) == len(actual) and set(by_id) == set(old) | set(targets),
            'unexpected persisted population change')
    for key, row in old.items():
        require(wire(by_id[key]) == wire(row), 'baseline row or activity changed: ' + key)
    for key, metadata in targets.items():
        require(strict_matches(native, by_id[key], metadata), 'target persisted metadata differs: ' + key)
    return by_id


def backup_database(out):
    require(not Path(str(STORE) + '.wal').exists(), 'active WAL needs a separately coordinated native snapshot')
    before = STORE.lstat()
    require(store_witness() == witness(before), 'selected store path changed before backup')
    original = capture(STORE, maximum=MAX_DATABASE_BYTES)
    destination = out / 'model-manager-before.duckdb'
    require(store_witness() == witness(before), 'store changed before backup')
    with STORE.open('rb') as incoming, destination.open('xb') as outgoing:
        require(witness(os.fstat(incoming.fileno())) == witness(before), 'backup source descriptor changed')
        count = 0
        for chunk in iter(lambda: incoming.read(1024**2), b''):
            count += len(chunk)
            require(count <= original['bytes'], 'backup source grew')
            outgoing.write(chunk)
        outgoing.flush()
        os.fsync(outgoing.fileno())
        require(count == original['bytes'] and witness(os.fstat(incoming.fileno())) == witness(before),
                'backup source changed')
    require(store_witness() == witness(before)
            and not Path(str(STORE) + '.wal').exists(), 'store endpoint changed during backup')
    backup = capture(destination, maximum=MAX_DATABASE_BYTES)
    require((backup['bytes'], backup['sha256']) == (original['bytes'], original['sha256']),
            'backup bytes differ from selected original store')
    return original, backup, before


def selected_source_owners():
    require(subprocess.check_output(['git', '-C', str(DATASETS), 'rev-parse', 'HEAD'], text=True).strip() == DATASETS_HEAD,
            'datasets source generation differs')
    require(subprocess.check_output(['git', '-C', str(ACCELERATE), 'rev-parse', 'HEAD'], text=True).strip() == ACCELERATE_HEAD,
            'accelerate source generation differs')
    catalog = subprocess.check_output(['git', '-C', str(ACCELERATE), 'ls-files',
        'ipfs_accelerate_py/model_catalog/*.py', 'ipfs_accelerate_py/model_catalog/**/*.py'], text=True).splitlines()
    return [source(DATASETS, IMPORTER)] + [source(ACCELERATE, p) for p in
        ['ipfs_accelerate_py/__init__.py', 'ipfs_accelerate_py/model_manager.py', *catalog]]


def authentication_join(plan, authentication):
    require(authentication.get('schema') == 'normative-checkpoint-authentication/v1'
            and authentication.get('complete') is True
            and authentication.get('closing_endpoint_identity_checks_passed') is True,
            'completed closing-fenced native authentication required')
    require(type(authentication.get('serialization_count')) is int and authentication['serialization_count'] == 8
            and type(authentication.get('trained_numeric_endpoint_count')) is int
            and authentication['trained_numeric_endpoint_count'] == 4,
            'eight serializations must remain four trained numeric endpoints')
    require(type(authentication.get('authority')) is dict
            and all(value is False for value in authentication['authority'].values()),
            'authentication cannot promote runtime/quality/proof authority')
    states = authentication.get('states')
    require(type(states) is list and len(states) == 8 and len(plan['models']) == 8,
            'exact eight authenticated serialization records required')
    lookup = {}
    for state in states:
        original = core_pin(state['original_checkpoint_pin'])
        require(state.get('checkpoint_bytes_authenticated') is True
                and state.get('typed_JSON_tensor_digest_authenticated') is True
                and state.get('ir_family_id') == 'legal_ir'
                and type(state.get('dimension')) is int and state['dimension'] in (384, 768)
                and state.get('dimension_role') == 'input_embedding'
                and state.get('task_id') == 'semantic_IR_reconstruction'
                and state.get('native_ir_schema_version') is None
                and state.get('decoder_profile_id') is None and state.get('decoder_format_id') is None,
                'authenticated exact LegalIR lane/task with unknown native format required')
        require(original['sha256'] not in lookup, 'unique serialization byte identities required')
        lookup[original['sha256']] = state
    used, joins = set(), []
    for record in plan['models']:
        metadata = record['model_metadata']
        declaration = metadata['huggingface_config']['ir_checkpoint']
        original = core_pin(declaration['original_checkpoint_pin'])
        require(original['sha256'] in lookup and original['sha256'] not in used,
                'exact unique authenticated checkpoint binding required')
        state = lookup[original['sha256']]
        require(wire(original) == wire(core_pin(state['original_checkpoint_pin']))
                and declaration['ir_family_id'] == state['ir_family_id']
                and type(declaration['dimension']) is int and declaration['dimension'] == state['dimension']
                and declaration['dimension_role'] == state['dimension_role']
                and declaration['task_id'] == state['task_id'], 'authentication lane/task/source-pin join differs')
        require(all(declaration.get(name) is None for name in ('schema_version', 'profile_id', 'format_id'))
                and all(declaration.get(name) is False for name in ('runtime_ready', 'teacher_qualified', 'proof_authority'))
                and metadata['huggingface_config'].get('complete_runtime_io_contract') is False,
                'availability-only false runtime/proof flags and unknown native identities required')
        used.add(original['sha256'])
        joins.append({'model_id': metadata['model_id'], 'dimension': state['dimension'],
            'original_checkpoint_pin': original, 'serialization_role': state['role'],
            'selected_header_value': state['selected_header_value'],
            'numeric_alias_group': state['numeric_alias_group'], 'tensor_sha256': state['tensor_sha256']})
    require(len(used) == 8 and len({item['numeric_alias_group'] for item in joins}) == 4,
            'serialization bindings must retain four numeric alias groups')
    return joins


def nested_pins(value):
    collected = {}
    def walk(item):
        if type(item) is dict:
            if {'path', 'bytes', 'sha256'} <= set(item):
                pin = core_pin(item)
                require(pin['path'] not in collected or wire(collected[pin['path']]) == wire(pin),
                        'conflicting authenticated same-path pin')
                collected[pin['path']] = pin
            for child in item.values():
                walk(child)
        elif type(item) is list:
            for child in item:
                walk(child)
    walk(value)
    return list(collected.values())


def fence(pins, owners):
    for pin in pins:
        require(capture(pin['path'], maximum=max(MAX_METADATA_BYTES, pin['bytes'])) == pin,
                'authenticated pinned input changed')
    for index, owner in enumerate(owners):
        root = DATASETS if index == 0 else ACCELERATE
        require(wire(source(root, owner['relative_path'])) == wire(owner), 'current committed source owner changed')
    loaded_owner_origins(owners)


def loaded_owner_origins(owners):
    for owner in owners[1:]:
        relative = owner['relative_path']
        parts = list(Path(relative).with_suffix('').parts)
        if parts[-1] == '__init__':
            parts.pop()
        module = sys.modules.get('.'.join(parts))
        if module is not None:
            location = getattr(module, '__file__', None)
            require(type(location) is str and Path(location).resolve(strict=True) == Path(owner['pin']['path']),
                    'loaded committed owner has wrong source origin: ' + relative)


def validate_review(review, *, driver_pin, custody_pin, plan_pin, auth_pin, releases, owners):
    require(review.get('schema') == 'normative-model-manager-registration-driver-review/v1'
            and review.get('approved') is True, 'explicit approved independent registration review required')
    expected = {'reviewed_driver_pin': driver_pin, 'reviewed_custody_pin': custody_pin,
        'reviewed_plan_pin': plan_pin, 'reviewed_authentication_pin': auth_pin,
        'reviewed_release_receipt_pins': releases, 'reviewed_source_owners': owners}
    for key, value in expected.items():
        require(wire(review.get(key)) == wire(value), 'reviewed bytes/source do not match: ' + key)


def environment():
    for key, value in {'IPFS_ACCEL_SKIP_CORE': '1', 'IPFS_DATASETS_ENABLED': '0',
        'IPFS_ACCEL_AUTO_INSTALL': '0', 'IPFS_KIT_DISABLE': '1', 'STORAGE_FORCE_LOCAL': '1',
        'IPFS_DATASETS_PY_MINIMAL_IMPORTS': '1', 'IPFS_DATASETS_AUTO_INSTALL': '0',
        'IPFS_KIT_AUTO_INSTALL_DEPS': '0', 'ENABLE_IPFS_MODEL_STORAGE': '0',
        'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}.items():
        os.environ[key] = value
    sys.dont_write_bytecode = True


def install_execution_fence(owners):
    refused_imports, refused_events = [], []
    allowed_git = {('git', '-C', str(root), 'rev-parse', 'HEAD') for root in (DATASETS, ACCELERATE)}
    allowed_git.update(('git', '-C', str(DATASETS if index == 0 else ACCELERATE),
        'show', owner['head'] + ':' + owner['relative_path']) for index, owner in enumerate(owners))
    class OptionalFence(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if any(fullname == name or fullname.startswith(name + '.') for name in FORBIDDEN):
                refused_imports.append(fullname)
                raise ImportError('availability registration disables optional owner: ' + fullname)
            return None
    def hook(event, args):
        if event in {'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'os.system', 'os.exec'}:
            refused_events.append(event)
            raise RuntimeError('availability registration forbids network/extra process: ' + event)
        if event == 'subprocess.Popen':
            require(args[0] == 'git' and tuple(args[1]) in allowed_git,
                    'only exact pinned read-only Git source checks allowed')
    require(not any(name in sys.modules for name in FORBIDDEN), 'optional heavy owner loaded before fence')
    sys.meta_path.insert(0, OptionalFence())
    sys.addaudithook(hook)
    return refused_imports, refused_events


def genuine_manager_class():
    spec = importlib.util.spec_from_file_location('ipfs_accelerate_py.model_manager',
        ACCELERATE / 'ipfs_accelerate_py/model_manager.py')
    module = importlib.util.module_from_spec(spec)
    module.logger = logging.getLogger('ipfs_accelerate_model_manager')
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == ACCELERATE / 'ipfs_accelerate_py/model_manager.py',
            'genuine manager came from wrong source')
    return module.ModelManager


def exact_catalog(plan):
    module = importlib.import_module('ipfs_accelerate_py.model_catalog.sources.ir_persistent')
    require(Path(module.__file__).resolve() == ACCELERATE / 'ipfs_accelerate_py/model_catalog/sources/ir_persistent.py',
            'persistent IR reader came from wrong source')
    source_instance = module.IRPersistentCatalogSource(path=STORE,
        source='normative-candidate-registration.persisted')
    result = source_instance.load()
    resolutions = []
    for record in plan['models']:
        declaration = record['model_metadata']['huggingface_config']['ir_checkpoint']
        request = {name: declaration[name] for name in SELECTORS if name != 'checkpoint_sha256'}
        request['checkpoint_sha256'] = record['checkpoint_pin']['sha256']
        resolved = result.resolve_ir_binding(request)
        require(all(value is False for value in resolved['authority'].values()),
                'catalog metadata must remain non-operational')
        resolutions.append(resolved)
    return {'catalog_revision': result.revision,
        'binding_snapshot_revision': result.binding_snapshot_revision,
        'resolutions': resolutions, 'running_external_process_refreshed': False}


def genuine_catalog_targets(manager, expected_ids):
    snapshot = manager.catalog.snapshot()
    cursor, matches = None, []
    for _ in range(100):
        page = manager.list_catalog_models(limit=100, cursor=cursor, snapshot=snapshot)
        for item in page.items:
            for provenance in item.provenance:
                if provenance.source == 'model-manager.persistent' and provenance.source_record_id in expected_ids:
                    matches.append({'source_record_id': provenance.source_record_id,
                        'canonical_model_id': item.model_id})
        cursor = page.next_cursor
        if cursor is None:
            break
    require(cursor is None and len(matches) == len(expected_ids)
            and {item['source_record_id'] for item in matches} == set(expected_ids),
            'cold genuine catalog must expose every exact target serialization ID')
    return {'catalog_revision': snapshot.revision, 'matching_bindings': matches}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--release-receipt', action='append', required=True)
    parser.add_argument('--authentication', required=True)
    parser.add_argument('--output-directory', required=True)
    parser.add_argument('--register', action='store_true')
    parser.add_argument('--review-receipt')
    parser.add_argument('--review-sha256')
    args = parser.parse_args()
    out = Path(args.output_directory)
    require(out.is_absolute() and not out.exists(), 'fresh absolute output directory required')
    out.mkdir(parents=True)
    phase, mutation_possible, manager = 'preflight', False, None
    absent_ids = frozenset()  # defined before any constructor/exception cleanup
    try:
        environment()
        owners = selected_source_owners()
        driver_pin = capture(Path(__file__).resolve())
        custody_pin = capture(Path(__file__).resolve().with_name('custody.py'))
        plan_pin = capture(Path(args.plan), maximum=MAX_METADATA_BYTES)
        auth_pin = capture(Path(args.authentication), maximum=MAX_METADATA_BYTES)
        releases = [capture(Path(path), maximum=MAX_METADATA_BYTES) for path in args.release_receipt]
        spec = importlib.util.spec_from_file_location('availability_native_importer', DATASETS / IMPORTER)
        native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native)
        full_plan, native_pins, _, _ = native._prepare(plan_pin, releases, native.MAX_REFERENCE_BYTES)
        authentication = json_file(auth_pin)
        joins = authentication_join(full_plan, authentication)
        protected = nested_pins(authentication) + native_pins + [auth_pin, driver_pin, custody_pin]
        fence(protected, owners)
        preflight = {'schema': 'normative-model-manager-registration-preflight/v1',
            'completed': True, 'plan_pin': plan_pin, 'authentication_pin': auth_pin,
            'release_receipt_pins': releases, 'source_owners': owners,
            'driver_pin': driver_pin, 'custody_pin': custody_pin, 'authentication_joins': joins,
            'model_count': 8, 'trained_numeric_endpoint_count': 4,
            'database_opened': False, 'manager_constructed': False, 'runtime_ready': False,
            'teacher_qualified': False, 'proof_authority': False}
        preflight_pin = write(out / 'preflight.json', preflight)
        if not args.register:
            print(json.dumps({'status': 'preflight_only', 'preflight_pin': preflight_pin}))
            return
        require(args.review_receipt and args.review_sha256, '--register requires explicit independent review pin')
        review_pin = capture(Path(args.review_receipt), maximum=MAX_METADATA_BYTES)
        require(review_pin['sha256'] == args.review_sha256, 'independent review SHA differs')
        review = json_file(review_pin)
        validate_review(review, driver_pin=driver_pin, custody_pin=custody_pin,
            plan_pin=plan_pin, auth_pin=auth_pin, releases=releases, owners=owners)
        protected.append(review_pin)
        sys.path[:0] = [str(ACCELERATE), str(DATASETS)]
        refused_imports, refused_events = install_execution_fence(owners)
        fence(protected, owners)
        store_witness()
        require(not Path(str(STORE) + '.wal').exists(), 'active writer/WAL needs coordinated snapshot')
        import duckdb
        phase = 'fresh_read_only_baseline'
        baseline, baseline_schema = fresh_snapshot(duckdb)
        absent, present = partition_records(native, full_plan, baseline)
        absent_ids = frozenset(item['model_metadata']['model_id'] for item in absent)
        before_records_pin = write(out / 'before-records.json', baseline)
        before_schema_pin = write(out / 'before-schema.json', baseline_schema)
        queries = []
        if absent:
            phase = 'coherent_store_backup'
            original_store, backup_pin, backup_stat = backup_database(out)
            # Repeat full baseline and collision observation after the large backup,
            # before even the first genuine constructor can write schema/rows.
            repeated, repeated_schema = fresh_snapshot(duckdb)
            require(wire(repeated) == wire(baseline) and wire(repeated_schema) == wire(baseline_schema),
                    'baseline changed during backup')
            repeated_absent, _ = partition_records(native, full_plan, repeated)
            require({item['model_metadata']['model_id'] for item in repeated_absent} == set(absent_ids),
                    'missing targets changed before construction')
            fence(protected, owners)
            require(store_witness() == witness(backup_stat)
                    and not Path(str(STORE) + '.wal').exists(), 'store changed before construction')
            ModelManager = genuine_manager_class()
            loaded_owner_origins(owners)
            def make_manager(ids):
                nonlocal mutation_possible
                mutation_possible = True
                candidate = construct_owned_manager(ModelManager, native, baseline, ids)
                try:
                    loaded_owner_origins(owners)
                    require(wire(schema_snapshot(candidate.con)) == wire(baseline_schema),
                            'genuine constructor changed selected schema')
                    return candidate
                except BaseException:
                    empty_close(candidate)
                    raise
            def readback(model_id):
                # Matching configuration while genuine writable connection is open;
                # this is a fresh native handle, not an independent engine/process.
                rows, schema = fresh_snapshot(duckdb, read_only=False)
                require(wire(schema) == wire(baseline_schema), 'schema changed during registration')
                found = [row for row in rows if row['model_id'] == model_id]
                require(len(found) <= 1, 'unique native readback required')
                queries.append({'model_id': model_id, 'fresh_native_connection': True,
                    'shared_engine_cache_possible': True, 'manager_models_not_used': True})
                return found[0] if found else None
            phase = 'genuine_public_api_import'
            result = import_missing(native, full_plan, baseline, make_manager=make_manager,
                stage_plan=lambda p: write(out / 'missing-only-import-plan.json', p),
                readback=readback, releases=releases, max_reference_bytes=native.MAX_REFERENCE_BYTES)
        else:
            original_store, backup_pin = None, None
            result = import_missing(native, full_plan, baseline,
                make_manager=lambda _: (_ for _ in ()).throw(RuntimeError('all-present must not construct')),
                stage_plan=lambda _: (_ for _ in ()).throw(RuntimeError('all-present must not stage missing plan')),
                readback=None, releases=releases, max_reference_bytes=native.MAX_REFERENCE_BYTES)
        phase = 'cold_native_readback'
        rows, schema = fresh_snapshot(duckdb)
        require(wire(schema) == wire(baseline_schema), 'schema differs after first genuine close')
        check_population(native, rows, baseline, full_plan)
        cold_catalog = exact_catalog(full_plan)
        if absent:
            phase = 'cold_genuine_reload'
            manager = construct_owned_manager(ModelManager, native, rows, frozenset())
            loaded_owner_origins(owners)
            require(wire(schema_snapshot(manager.con)) == wire(baseline_schema), 'cold genuine schema differs')
            cold_genuine_catalog = genuine_catalog_targets(manager,
                {item['model_metadata']['model_id'] for item in full_plan['models']})
            empty_close(manager)
            manager = None
        else:
            cold_genuine_catalog = None
        phase = 'final_readback_after_closes'
        final_rows, final_schema = fresh_snapshot(duckdb)
        require(wire(final_schema) == wire(baseline_schema), 'final schema differs')
        check_population(native, final_rows, baseline, full_plan)
        require(wire(final_rows) == wire(rows), 'zero-population cold close changed persisted rows')
        final_catalog = exact_catalog(full_plan)
        require(wire(final_catalog) == wire(cold_catalog), 'exact IR catalog generation changed at closing endpoint')
        require(not Path(str(STORE) + '.wal').exists(), 'WAL remains at closing endpoint')
        fence(protected, owners)
        native._prepare(plan_pin, releases, native.MAX_REFERENCE_BYTES)
        final_pin = write(out / 'after-records.json', final_rows)
        summary = {'schema': 'normative-model-manager-registration-result/v1', 'completed': True,
            'selected_storage': str(STORE), 'preflight_pin': preflight_pin,
            'independent_review_pin': review_pin, 'before_records_pin': before_records_pin,
            'before_schema_pin': before_schema_pin, 'original_store_pin': original_store,
            'backup_pin': backup_pin, 'after_records_pin': final_pin,
            'before_count': len(baseline), 'after_count': len(final_rows),
            'planned_serialization_count': 8, 'trained_numeric_endpoint_count': 4,
            'absent_ids': sorted(absent_ids), 'already_present_ids':
                sorted(item['model_metadata']['model_id'] for item in present),
            'registration': result, 'persisted_native_queries': queries,
            'cold_exact_catalog': final_catalog, 'cold_genuine_catalog': cold_genuine_catalog,
            'all_baseline_metadata_and_activity_exactly_preserved': True,
            'schema_and_indexes_unchanged': True, 'genuine_close_save_population_always_empty': True,
            'genuine_add_save_population_absent_ids_only': True,
            'all_original_and_published_input_bytes_unchanged': True,
            'optional_import_refusals': refused_imports, 'execution_refusals': refused_events,
            'active_other_manager_process_refreshed': False, 'model_numerically_loaded': False,
            'training_executed': False, 'inference_executed': False, 'new_embeddings_generated': False,
            'Hub_updated_by_registration': False, 'runtime_ready': False, 'teacher_qualified': False,
            'proof_authority': False, 'cooperative_endpoint_scope': True,
            'source_scope': 'Pinned genuine manager/catalog/import owners; heavy optional owners blocked. Not a guarded full eager-import closure.'}
        result_pin = write(out / 'registration-result.json', summary)
        print(json.dumps({'status': 'completed', 'result_pin': result_pin,
            'registered_count': len(absent_ids), 'already_present_count': len(present)}))
    except BaseException as error:
        write(out / 'failure.json', {'phase': phase, 'exception_type': type(error).__name__,
            'message': str(error), 'database_may_have_changed': mutation_possible,
            'absent_ids': sorted(absent_ids), 'no_automatic_rollback_or_retry': True,
            'partial_native_outcomes': getattr(error, 'outcomes', [])})
        raise
    finally:
        empty_close(manager)


if __name__ == '__main__':
    main()
