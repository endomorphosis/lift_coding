"""Pure guard/output tests for frozen checker1d8cf; never executes Lean.

All compiled/source fixture files are inert bytes. The external-tool boundary
is replaced with a stub; its output is test data, not qualification evidence.
The root owns the sole admitted pytest phase. Authoring/AST parsing this source
does not import the checker, pytest, or any project module.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import types

import pytest

CHECKER_SHA = '1d8cf650a781591ca966be653b97b1194a4870ce2dbf6cab1b979b5820efa7f6'


def file_pin(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


@pytest.fixture(scope='module')
def checker():
    path = Path(os.environ.get('RANKER_ANALYTIC_CHECKER_SOURCE',
                               str(Path(__file__).with_name('bounded_analytic_checker-v4.py')))).resolve()
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CHECKER_SHA
    module = types.ModuleType('frozen_analytic_checker_pure_tests')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


@pytest.fixture
def profile(tmp_path):
    root = tmp_path.resolve()
    library = root / 'library'
    library.mkdir()
    executable = root / 'inert-lean'
    executable.write_bytes(b'inert fixture; never executable\n')
    modules = []
    files = [file_pin(executable)]
    for name in ('Init', 'Allowed'):
        source = root / (name + '.lean')
        source.write_text('-- inert dependency fixture\n')
        compiled = library / (name + '.olean')
        compiled.write_bytes(('inert fixture object ' + name).encode())
        row = {'module': name, 'source': file_pin(source), 'compiled': [file_pin(compiled)]}
        modules.append(row)
        files.extend([row['source'], *row['compiled']])
    source = root / 'FixtureProof.lean'
    source.write_text('import Allowed\ntheorem fixtureTruth : True := by trivial\n')
    source_pin = file_pin(source)
    files.append(source_pin)
    manifest = {'schema': 'ranker-real-curvature-lean-environment@1',
        'lean_executable': file_pin(executable), 'lean_path': [str(library)], 'files': files,
        'source_import_modules': modules, 'selected_proof_sources': [source_pin]}
    return {'root': root, 'library': library, 'source': source, 'source_pin': source_pin,
            'manifest': manifest, 'manifest_path': root / 'environment.json'}


def freeze(profile):
    path = profile['manifest_path']
    path.write_text(json.dumps(profile['manifest'], sort_keys=True))
    return path, file_pin(path)['sha256']


def replace_source(profile, source):
    prior = profile['source_pin']
    profile['source'].write_text(source)
    current = file_pin(profile['source'])
    profile['source_pin'] = current
    profile['manifest']['files'] = [current if row == prior else row for row in profile['manifest']['files']]
    profile['manifest']['selected_proof_sources'] = [current]


def before_admission(checker, profile, monkeypatch, *, source_pin=None, **kwargs):
    """Bad input must refuse before any scheduler/project/tool boundary."""
    def boundary(*args, **kw):
        pytest.fail('bad input crossed actual admission/native boundary')
    monkeypatch.setattr(checker, '_lease', boundary)
    path, digest = freeze(profile)
    output = profile['root'] / 'output'
    output.mkdir()
    with pytest.raises((ValueError, KeyError, TypeError, OSError)):
        checker.compile_analytic_lean(environment_manifest=path,
            expected_environment_manifest_sha256=digest,
            source_pin=source_pin or profile['source_pin'], output=output,
            root_lease=object(), theorem_names=('fixtureTruth',), **kwargs)


@pytest.fixture
def native_stub(checker, monkeypatch):
    state = {'calls': [], 'stdout': "'fixtureTruth' does not depend on any axioms\n",
             'stderr': '', 'returncode': 0, 'ok': True,
             'output_files': {'FixtureProof.olean': b'inert compiled test bytes'}}

    class Limits:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Request:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class Runner:
        def run(self, request):
            state['calls'].append(request)
            return types.SimpleNamespace(command=request.argv, stdout=state['stdout'], stderr=state['stderr'],
                returncode=state['returncode'], ok=state['ok'], output_files=state['output_files'],
                timed_out=False, cancelled=False, unavailable=False, resource_exhausted=False,
                output_truncated=False, workspace_limit_exceeded=False, workspace_cleaned=True,
                elapsed_seconds=0.0)

    names = ('ipfs_datasets_py', 'ipfs_datasets_py.logic', 'ipfs_datasets_py.logic.backends',
             'ipfs_datasets_py.logic.backends.process')
    modules = {}
    for name in names:
        module = types.ModuleType(name)
        module.__path__ = []
        modules[name] = module
        monkeypatch.setitem(sys.modules, name, module)
    for name in names[1:]:
        parent, leaf = name.rsplit('.', 1)
        setattr(modules[parent], leaf, modules[name])
    process = modules[names[-1]]
    process.BoundedToolRunner, process.ToolRunLimits, process.ToolRunRequest = Runner, Limits, Request
    monkeypatch.setattr(checker, '_lease', lambda lease: {'lease_id': 'inert-unit-stub', 'cpu_slots': 1, 'memory_mb': 2048})
    return state


def invoke(checker, profile, **kwargs):
    path, digest = freeze(profile)
    output = profile['root'] / 'output'
    output.mkdir()
    return checker.compile_analytic_lean(environment_manifest=path,
        expected_environment_manifest_sha256=digest, source_pin=profile['source_pin'],
        output=output, root_lease=object(), theorem_names=('fixtureTruth',), **kwargs)


def test_minimal_inert_environment_binds_manifest_itself(checker, profile):
    path, digest = freeze(profile)
    descriptor, value = checker._environment(path, digest)
    assert descriptor == file_pin(path)
    assert value == profile['manifest']


@pytest.mark.parametrize('which', ['selected_only', 'inventory_only', 'both'])
def test_missing_actual_source_refuses_before_admission(checker, profile, monkeypatch, which):
    if which in ('selected_only', 'both'):
        profile['manifest']['selected_proof_sources'] = []
    if which in ('inventory_only', 'both'):
        profile['manifest']['files'].remove(profile['source_pin'])
    before_admission(checker, profile, monkeypatch)


def test_changed_source_cannot_use_prior_pin(checker, profile, monkeypatch):
    profile['source'].write_text('import Allowed\ntheorem differentTruth : True := by trivial\n')
    before_admission(checker, profile, monkeypatch)


@pytest.mark.parametrize('declaration', ['import Outside', 'import all Outside', 'public meta import Outside'])
def test_import_outside_profile_refuses_before_admission(checker, profile, monkeypatch, declaration):
    replace_source(profile, declaration + '\ntheorem fixtureTruth : True := by trivial\n')
    before_admission(checker, profile, monkeypatch)


def test_compiled_lookup_shadow_refuses_even_when_original_pin_is_valid(checker, profile, monkeypatch):
    shadow = profile['root'] / 'shadow'
    shadow.mkdir()
    (shadow / 'Allowed.olean').write_bytes(b'untracked shadow object')
    profile['manifest']['lean_path'].insert(0, str(shadow))
    before_admission(checker, profile, monkeypatch)


@pytest.mark.parametrize('kind', ['source', 'compiled', 'Init', 'duplicate_module', 'duplicate_file'])
def test_missing_or_duplicate_closure_records_refuse_before_admission(checker, profile, monkeypatch, kind):
    row = profile['manifest']['source_import_modules'][1]
    if kind in ('source', 'compiled'):
        descriptor = row['source'] if kind == 'source' else row['compiled'][0]
        profile['manifest']['files'].remove(descriptor)
    elif kind == 'Init':
        profile['manifest']['source_import_modules'] = [row]
    elif kind == 'duplicate_module':
        profile['manifest']['source_import_modules'].append(deepcopy(row))
    else:
        profile['manifest']['files'].append(deepcopy(profile['manifest']['files'][0]))
    before_admission(checker, profile, monkeypatch)


@pytest.mark.parametrize('pin', [None, True, 'A' * 64, '0' * 63, 'not-a-pin'])
def test_malformed_external_manifest_pin_refuses(checker, profile, pin):
    path, unused = freeze(profile)
    with pytest.raises(ValueError):
        checker._environment(path, pin)


def test_manifest_reseal_does_not_hide_changed_compiled_file(checker, profile, monkeypatch):
    (profile['library'] / 'Allowed.olean').write_bytes(b'changed after frozen file inventory')
    before_admission(checker, profile, monkeypatch)


@pytest.mark.parametrize('bad', [True, -1, '42'])
def test_malformed_source_byte_field_refuses(checker, profile, monkeypatch, bad):
    supplied = dict(profile['source_pin'], bytes=bad)
    before_admission(checker, profile, monkeypatch, source_pin=supplied)


@pytest.mark.parametrize('axiom', ['sorryAx', 'untrustedAxiom', 'propext, propext'])
def test_nonstandard_or_duplicate_axiom_reports_refuse(checker, axiom):
    with pytest.raises(ValueError):
        checker._axioms("'A.foo' depends on axioms: [" + axiom + ']\n', ('A.foo',))


def test_consistent_repeated_reports_are_counted(checker):
    line = "'A.foo' depends on axioms: [propext, Classical.choice, Quot.sound]\n"
    result = checker._axioms(line + line, ('A.foo',))
    assert result == [{'theorem': 'A.foo', 'axioms': ['propext', 'Classical.choice', 'Quot.sound'], 'report_occurrences': 2}]


def test_conflicting_spoof_and_actual_reports_refuse(checker):
    forged = "'A.foo' does not depend on any axioms\n"
    actual = "'A.foo' depends on axioms: [sorryAx]\n"
    with pytest.raises(ValueError):
        checker._axioms(forged + actual, ('A.foo',))


@pytest.mark.parametrize('existing', ['', '#print axioms fixtureTruth\n', '#print axioms A.fixtureTruth\n'])
def test_actual_fully_qualified_query_is_always_appended(checker, profile, native_stub, existing):
    replace_source(profile, 'import Allowed\ntheorem fixtureTruth : True := by trivial\n' + existing)
    result = invoke(checker, profile)
    assert result['status'] == 'passed' and len(native_stub['calls']) == 1
    request = native_stub['calls'][0]
    assert request.input_files['FixtureProof.lean'].endswith('#print axioms _root_.fixtureTruth\n')


def test_external_profile_cannot_relax_native_limits(checker, profile, native_stub):
    profile['manifest']['native_bounds'] = {'timeout_seconds': 900, 'max_output_bytes': 1024**3}
    result = invoke(checker, profile)
    request = native_stub['calls'][0]
    assert request.limits.kwargs == {'timeout_seconds': 20, 'cpu_seconds': 20, 'max_input_bytes': 262144,
                                   'max_output_bytes': 65536, 'max_workspace_bytes': 16777216}
    assert request.environment == {'LEAN_PATH': str(profile['library']), 'LEAN_NUM_THREADS': '1'}
    assert result['native_bounds'] == request.limits.kwargs


@pytest.mark.parametrize('diagnostic', [
    'FixtureProof.lean:1:0: error: unexpected token\n',
    'FixtureProof.lean:1:0: error: unknown module prefix\n',
    'FixtureProof.lean:1:0: error: unsolved goals\n',
])
def test_generic_negative_failure_is_inconclusive(checker, profile, native_stub, diagnostic):
    replace_source(profile, 'import Allowed\ntheorem fixtureTruth : True := by trivial\n'
                   'theorem falseControl : False := by decide +kernel\n')
    native_stub.update(stdout="'fixtureTruth' does not depend on any axioms\n" + diagnostic,
                       returncode=1, ok=False, output_files={})
    result = invoke(checker, profile, expected_success=False)
    assert result['status'] == 'inconclusive' and result['matches_expectation'] is False


def test_only_closed_decide_false_diagnostic_is_rejected(checker, profile, native_stub):
    replace_source(profile, 'import Allowed\ntheorem fixtureTruth : True := by trivial\n'
                   'theorem falseControl : False := by decide +kernel\n')
    native_stub.update(stdout="'fixtureTruth' does not depend on any axioms\n"
        'FixtureProof.lean:3:43: error: Tactic `decide` proved that the proposition\n  False\nis false\n',
        returncode=1, ok=False, output_files={})
    result = invoke(checker, profile, expected_success=False)
    assert result['status'] == 'rejected' and result['matches_expectation'] is True


def test_oversize_stub_artifact_preserves_inconclusive_receipt(checker, profile, native_stub):
    native_stub['output_files'] = {'FixtureProof.olean': b'x' * 70000}
    result = invoke(checker, profile)
    assert result['status'] == 'inconclusive' and result['matches_expectation'] is False
    assert result['compiled_artifacts'][0]['bytes'] == 65536
    assert result['compiled_artifacts'][0]['complete'] is False
    assert (profile['root'] / 'output/FixtureProof.check.json').is_file()


def test_declared_optional_companions_are_bound_without_cap_relaxation(checker, profile, native_stub):
    native_stub['output_files']['FixtureProof.olean.private'] = b'inert private companion'
    result = invoke(checker, profile)
    assert result['status'] == 'passed' and len(result['compiled_artifacts']) == 2
    assert all(row['complete'] is True and row['bytes'] <= 65536 for row in result['compiled_artifacts'])
    assert native_stub['calls'][0].output_paths == (
        'FixtureProof.olean', 'FixtureProof.olean.private', 'FixtureProof.olean.server', 'FixtureProof.ir')
