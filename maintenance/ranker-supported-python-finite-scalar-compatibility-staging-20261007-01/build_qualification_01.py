"""Root-only stdlib source/data staging; executes no imported repository code."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
BASE = ROOT / 'qualification/codebase_ir/ranker-supported-python-own-numeric-comprehensions-qualification-20261007-03'
CONTEXT = ROOT / 'maintenance/ranker-supported-python-ast-scalar-native-staging-20261007-01/prior-import-context-06.json'
MODE = 'lean-python-finite-scalar-compatibility-01'
QUERIES = ['RankerSupportedPythonFiniteScalarCompatibility.scalar_projection_local_bindings',
           'RankerSupportedPythonFiniteScalarCompatibility.own_scalar_compatibility']

def pin(path):
    path = Path(path)
    body = path.read_bytes()
    return {'path': str(path), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}

def data(path):
    return json.loads(Path(path).read_bytes())

def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    return pin(path)

def literals(source):
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                result[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return result

def assignments(source, replacements):
    lines = source.splitlines(keepends=True)
    edits = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in replacements:
                edits.append((node.lineno - 1, node.end_lineno, name + ' = ' + repr(replacements[name]) + '\n'))
    assert len(edits) == len(replacements)
    for begin, end, value in sorted(edits, reverse=True):
        lines[begin:end] = [value]
    return ''.join(lines)

def function_dumps(source):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--expected-gate-sha256', required=True)
    args = parser.parse_args()
    assert args.version.isdigit() and len(args.version) == 2
    suffix = '20261007-' + args.version
    candidate = ROOT / ('qualification/codebase_ir/ranker-supported-python-finite-scalar-compatibility-candidate-' + suffix)
    qualifier = ROOT / ('qualification/codebase_ir/ranker-supported-python-finite-scalar-compatibility-qualification-' + suffix)
    gatepath = ROOT / ('maintenance/ranker-supported-python-finite-scalar-compatibility-math-source-review-' + suffix + '/review-receipt-01.json')
    gatepin = pin(gatepath)
    assert gatepin['sha256'] == args.expected_gate_sha256
    gate = data(gatepath)
    assert gate['status'] == 'passed_source_only' and gate['findings'] == [] and gate['candidate_compiled'] is False
    assert all(gate[key] is False for key in ['execution_authority', 'proof_authority', 'completion_authority', 'planner_activation'])
    source = pin(candidate / 'math/PyFiniteScalarCompatibility.lean')
    candidatepins = {name: pin(candidate / name) for name in ['candidate-interface.json', 'math/PyFiniteScalarCompatibility.lean', 'obligations.json']}
    context = data(CONTEXT)
    assert len(context['PRIOR_IMPORTS']) == 12
    selected = {'module': 'PyFiniteScalarCompatibility', 'source': source,
                'qualification_root': str(qualifier), 'direct_imports': ['PyOwnNumericComprehensions'],
                'prior_modes': [row['mode'] for row in context['PRIOR_IMPORTS']], 'queries': QUERIES}
    assert gate['candidate_pins'] == candidatepins and gate['reviewed_modules'] == {MODE: selected}
    qualifier.mkdir()
    mappin = write(qualifier / 'module-map-01.json', {MODE: selected})
    write(qualifier / 'candidate-pins-01.json', candidatepins)
    oldsource = (BASE / 'language_file_helpers_01.py').read_text()
    oldliteral = literals(oldsource)
    frozen = copy.deepcopy(oldliteral['FROZEN'])
    frozen.update(MODULE_MAP=mappin, CANDIDATE_PINS=candidatepins, SOURCE_GATE=gatepin)
    extra = frozen['EXTRA_CONTEXT']
    extra.extend([oldliteral['FROZEN']['MODULE_MAP'], oldliteral['FROZEN']['SOURCE_GATE'], pin(CONTEXT), pin(Path(__file__))])
    for relative in [
        'maintenance/ranker-objective-source-model-progress-20261006-01/progress-12.json',
        'maintenance/ranker-supported-python-own-numeric-comprehensions-tooling-source-review-20261007-03/review-receipt-01.json',
        'maintenance/ranker-supported-python-own-numeric-comprehensions-native-readback-review-20261007-03/review-receipt-01.json',
        'maintenance/ranker-supported-python-own-numeric-comprehensions-input-review-20261007-03/read_completed_01.py',
        'maintenance/ranker-supported-python-own-numeric-comprehensions-input-review-20261007-03/lean-python-own-numeric-comprehensions-01-prepared-audit-01.json',
        'maintenance/ranker-supported-python-own-numeric-comprehensions-input-review-20261007-03/lean-python-own-numeric-comprehensions-01-completed-readback-01.json']:
        extra.append(pin(ROOT / relative))
    for scope in [BASE, candidate]:
        sealpin = pin(scope / 'file-only-seal-01.json')
        seal = data(sealpin['path'])
        frozen['CONTEXT_SEALS'].append({'seal': sealpin, 'scope_root': str(scope), 'schema': seal['schema'],
                                       'regular_file_count': seal['regular_file_count'], 'regular_file_bytes': seal['regular_file_bytes']})
    checkpoint = data(frozen['CHECKPOINT']['path'])
    rows = {row['path']: row for row in checkpoint['closure']}
    def add(row):
        assert row['path'] not in rows or rows[row['path']] == row
        rows[row['path']] = row
    for expected in frozen['CONTEXT_SEALS']:
        seal = data(expected['seal']['path'])
        for row in [expected['seal'], seal['review'], *seal['files']]:
            add(row)
    for row in [frozen['REPLAY_SOURCE'], frozen['CHECKPOINT'], frozen['REPLAY_GATE'],
                mappin, *candidatepins.values(), gatepin, *extra]:
        add(row)
    previous = data(BASE / 'preparation/lean-python-own-numeric-comprehensions-01-request.json')['strict_old_inputs']
    assert len(previous) == 4589 and all(rows[row['path']] == row for row in previous)
    frozen['STRICT_GUARD_COUNT'] = len(rows)
    replacements = dict(context)
    replacements.update(FROZEN=frozen, MODE_ORDER=[MODE])
    helper = assignments(oldsource, replacements)
    old = "ROOT.with_name('ranker-supported-python-finite-bindings-qualification-20261007-02')),"
    new = "ROOT.with_name('ranker-supported-python-finite-bindings-qualification-20261007-02'), ROOT.with_name('ranker-supported-python-own-numeric-comprehensions-qualification-20261007-03')),"
    assert helper.count(old) == 1
    helper = helper.replace(old, new)
    assert helper.count('len(imports)==11') == 1
    helper = helper.replace('len(imports)==11', 'len(imports)==12').replace(
        'exact eleven actually owned prior scalar-target, AST support and finite-binding modules required',
        'exact twelve actually owned prior scalar-target, AST, finite-binding and comprehension modules required')
    before, after = function_dumps(oldsource), function_dumps(helper)
    assert len(before) == 17 and before.keys() == after.keys()
    assert {name for name in before if before[name] != after[name]} == {'_append_imports', 'import_extension'}
    (qualifier / 'language_file_helpers_01.py').write_text(helper)
    helperpin = pin(qualifier / 'language_file_helpers_01.py')
    common = (helperpin['bytes'], helperpin['sha256'])
    prepold = (BASE / 'prepare_language_batch_01.py').read_text()
    prep = assignments(prepold, {'COMMON': common})
    prep = prep.replace('only selected own numeric-comprehension module allowed; earlier accepted stages are reuse only',
                        'only selected finite scalar compatibility module allowed; earlier accepted stages are reuse only')
    prep = prep.replace('Own numeric generator setup/capture, ordered first errors and exact-real generator materialization',
                        'Ordinary finite scoped projection membership and own-to-old scalar AST observation compatibility')
    prep = prep.replace('Own pure numeric-comprehension observation scope; target lowering/parser/globalpurity/protocol timing/Float/fullPython/task/planner/globalAE remain OPEN',
                        'Own finite scoped scalar AST compatibility; target lowering/parser/globalpurity/protocol timing/Float/fullPython/task/planner/globalAE remain OPEN')
    assert prep.count('combined_source_gate_expected_qualified_queries=3') == 1
    prep = prep.replace('combined_source_gate_expected_qualified_queries=3', 'combined_source_gate_expected_qualified_queries=2')
    assert function_dumps(prepold)['helpers'] == function_dumps(prep)['helpers']
    (qualifier / 'prepare_language_batch_01.py').write_text(prep)
    driverold = (BASE / 'run_language_batch_01.py').read_text()
    driver = assignments(driverold, {'COMMON': common, 'MODES': (MODE,)})
    assert function_dumps(driverold) == function_dumps(driver)
    (qualifier / 'run_language_batch_01.py').write_text(driver)
    print(json.dumps({'status': 'fresh_unexecuted_source_and_data_staged', 'mode': MODE,
                      'strict_guard_count': len(rows), 'contexts': len(frozen['CONTEXT_SEALS']),
                      'map': mappin, 'sources': [helperpin, pin(qualifier / 'prepare_language_batch_01.py'), pin(qualifier / 'run_language_batch_01.py')],
                      'native_jobs': 0, 'qualified_queries': 0}))

if __name__ == '__main__':
    main()
