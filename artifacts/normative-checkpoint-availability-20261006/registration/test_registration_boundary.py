"""Private inert controls: no project imports, database, Hub, or model calls."""
import copy
from contextlib import nullcontext
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

import register_normative_states as driver


class Native:
    MAX_REFERENCE_BYTES = 1024

    @staticmethod
    def _stable_metadata(metadata):
        return {key: value for key, value in metadata.items() if key != 'updated_at'}

    @classmethod
    def _matches(cls, actual, expected):
        return cls._stable_metadata(actual) == cls._stable_metadata(expected)


def record(model_id):
    return {'model_metadata': {'model_id': model_id, 'architecture': 'inert',
        'huggingface_config': {'ir_checkpoint': {'runtime_ready': False}}},
        'checkpoint_pin': {}, 'release': {}}


def test_late_collision_refuses_before_missing_plan_or_construction():
    early, late = record('early'), record('late')
    baseline = [dict(late['model_metadata'], architecture='conflicting')]
    calls = []
    with pytest.raises(ValueError, match='conflicting metadata: late'):
        driver.import_missing(Native, {'schema': 'inert', 'models': [early, late]}, baseline,
            make_manager=lambda _: calls.append('constructor'),
            stage_plan=lambda _: calls.append('stage'), readback=None,
            releases=[], max_reference_bytes=1024)
    assert calls == []


def test_all_present_zero_constructor_zero_missing_plan_zero_saves():
    rows = [record('one'), record('two')]
    baseline = [dict(item['model_metadata'], updated_at='original') for item in rows]
    calls = []
    result = driver.import_missing(Native, {'schema': 'inert', 'models': rows}, baseline,
        make_manager=lambda _: calls.append('constructor'),
        stage_plan=lambda _: calls.append('stage'), readback=None,
        releases=[], max_reference_bytes=1024)
    assert calls == []
    assert result == {'missing_count': 0, 'already_present_count': 2,
        'manager_constructed': False, 'native_result': None, 'missing_plan_pin': None}
    assert baseline[0]['updated_at'] == baseline[1]['updated_at'] == 'original'


def test_mixed_existing_never_enters_any_save_population_and_close_is_empty():
    old, new = record('already-present'), record('absent')
    baseline = [dict(old['model_metadata'], updated_at='original')]
    saved, staged, persisted = [], [], copy.deepcopy(baseline)

    class Manager:
        def __init__(self):
            self._model_lock = nullcontext()
            self.models = {}
            self.con = None
        def _save_data(self):
            saved.append(set(self.models))
        def close(self):
            self._save_data()
        def add_model(self, metadata):
            self.models[metadata['model_id']] = metadata
            self._save_data()
            persisted.append(copy.deepcopy(metadata))
            return True

    class Importer(Native):
        @staticmethod
        def import_ir_model_manager_records(pin, *, release_receipts, manager,
                                           readback, max_reference_bytes):
            assert staged[0]['models'] == [new]
            for item in staged[0]['models']:
                assert manager.add_model(item['model_metadata']) is True
                assert readback(item['model_metadata']['model_id']) == item['model_metadata']
            return {'completed': True, 'registered_count': 1,
                'already_present_count': 0, 'persisted_metadata_matched_count': 1}

    def make_manager(ids):
        assert ids == {'absent'}
        manager = Manager()
        driver.guard_save_population(manager, ids)
        return manager

    result = driver.import_missing(Importer, {'schema': 'inert', 'models': [old, new]}, baseline,
        make_manager=make_manager, stage_plan=lambda p: staged.append(p) or {},
        readback=lambda model_id: next(row for row in persisted if row['model_id'] == model_id),
        releases=[], max_reference_bytes=1024)
    assert result['missing_count'] == result['already_present_count'] == 1
    assert saved == [{'absent'}, set()]
    assert persisted[0] == baseline[0]


def test_partial_constructor_initial_load_mismatch_closes_with_empty_population():
    calls = []
    class BrokenManager:
        def __init__(self, **kwargs):
            self._model_lock = nullcontext()
            self.models = {'unexpected-baseline': {'model_id': 'unexpected-baseline'}}
            self.use_database = True
            self.storage_path = kwargs['storage_path']
            self.con = None
        def close(self):
            calls.append(set(self.models))
    with pytest.raises(ValueError, match='initial loaded population differs'):
        driver.construct_owned_manager(BrokenManager, Native, [], {'new-target'})
    assert calls == [set()]


def test_strict_metadata_boundary_refuses_python_bool_integer_equivalence():
    value = record('id')['model_metadata']
    changed = copy.deepcopy(value)
    changed['huggingface_config']['ir_checkpoint']['runtime_ready'] = 0
    assert Native._matches(changed, value) is True
    assert driver.strict_matches(Native, changed, value) is False


def test_guard_refuses_late_unapproved_save_population():
    class Manager:
        _model_lock = nullcontext()
        models = {'already-present': {}}
        def _save_data(self):
            pytest.fail('unapproved population reached native storage')
    manager = Manager()
    driver.guard_save_population(manager, {'new-target'})
    with pytest.raises(ValueError, match='unapproved owned save population'):
        manager._save_data()


def test_baseline_activity_and_typed_fields_are_compared_exactly():
    row = record('existing')['model_metadata']
    row['updated_at'] = 'original'
    changed = dict(row, updated_at='rewritten')
    with pytest.raises(ValueError, match='baseline row or activity changed'):
        driver.check_population(Native, [changed], [row], {'models': [record('existing')]})


def test_constructor_throws_before_lock_cleanup_still_has_empty_save_population():
    calls = []
    class BrokenManager:
        def __init__(self, **kwargs):
            self.models = {'baseline': {}}
            raise RuntimeError('constructor early failure')
        def close(self):
            calls.append(set(self.models))
    with pytest.raises(RuntimeError, match='constructor early failure'):
        driver.construct_owned_manager(BrokenManager, Native, [], {'new-target'})
    assert calls == [set()]


def test_loaded_source_origin_refuses_foreign_same_named_owner(tmp_path, monkeypatch):
    current = tmp_path / 'current.py'
    foreign = tmp_path / 'foreign.py'
    current.write_text('same bytes\n')
    foreign.write_text('same bytes\n')
    owner = {'relative_path': 'private_test_owner.py', 'pin': {'path': str(current)}}
    monkeypatch.setitem(sys.modules, 'private_test_owner', SimpleNamespace(__file__=str(current)))
    driver.loaded_owner_origins([{}, owner])
    monkeypatch.setitem(sys.modules, 'private_test_owner', SimpleNamespace(__file__=str(foreign)))
    with pytest.raises(ValueError, match='wrong source origin'):
        driver.loaded_owner_origins([{}, owner])


def test_private_store_parent_alias_exchange_refused_at_later_endpoint(tmp_path, monkeypatch):
    parent = tmp_path / 'assets'
    parent.mkdir()
    selected = parent / 'metadata.duckdb'
    selected.write_bytes(b'private inert bytes; never opened as a database')
    monkeypatch.setattr(driver, 'STORE', selected)
    before = driver.store_witness()
    retained = tmp_path / 'renamed'
    parent.rename(retained)
    parent.symlink_to(retained, target_is_directory=True)
    assert driver.witness(selected.lstat()) == before
    with pytest.raises(ValueError, match='parent/path alias changed'):
        driver.store_witness()
