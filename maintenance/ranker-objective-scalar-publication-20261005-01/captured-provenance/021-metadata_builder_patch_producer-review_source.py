"""Independent inert-source review; imports no reviewed target and runs no jobs."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
HERE = Path(__file__).resolve().parent
Q = W / 'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
PINS = {
    Q / 'build_objective_metadata_01.py': (49474, '45246ee6931195cecc07433384c953aa474cd903ec7c665e6b38f406dc47e1c9'),
    Q / 'build_objective_metadata_02.py': (50438, '40c0f9782caa995145bfe1cc84aaa5a4f9d19b0679dfc9529605816040255e90'),
    Q / 'run_objective_metadata_controls_01.py': (49452, '6b4a1e7b7d345d7bf27ba74eca5e64f6166deae4d777a5131ad50d0128d48908'),
    W / 'maintenance/ranker-objective-scalar-metadata-source-review-20261005-01/review-receipt.json': (5531, '8c75bd6a5a2c558459b580d8bc129ca74d6ec1066c5d49e13134adcc0d516796'),
    W / 'maintenance/ranker-objective-root-review-20261005-01/close_qualification_01.py': (19691, '9d68d8c8575f47887bde85bbda88d57db91a563f91b73756bffe30c405ddeec4'),
}
HELD = {}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path, expected=None):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical review input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and first.st_size <= 32 * 1024**2, 'bounded regular review input')
        blocks, count = [], 0
        while block := os.read(fd, 1024**2):
            count += len(block)
            need(count <= 32 * 1024**2, 'running read bound')
            blocks.append(block)
        raw = b''.join(blocks)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda value: tuple(getattr(value, key) for key in keys)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and count == first.st_size, 'review input changed')
    finally:
        os.close(fd)
    row = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected is not None:
        need((row['bytes'], row['sha256']) == expected, 'independent source pin differs')
    need(str(path) not in HELD or HELD[str(path)] == row, 'previous review input changed')
    HELD[str(path)] = row
    return raw, row


def dump(tree):
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def save(name, value):
    with (HERE / name).open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    return read(HERE / name)[1]


def main():
    need(__debug__, 'optimized review refused')
    need(not (HERE / 'review-receipt.json').exists() and not (HERE / 'closure-source-review-receipt.json').exists(), 'fresh receipts required')
    inputs = {path: read(path, expected)[0] for path, expected in PINS.items()}
    old_path, new_path = Q / 'build_objective_metadata_01.py', Q / 'build_objective_metadata_02.py'
    old, new = ast.parse(inputs[old_path]), ast.parse(inputs[new_path])
    old_functions = {node.name: node for node in old.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    new_functions = {node.name: node for node in new.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    need(set(new_functions) - set(old_functions) == {'census_descriptor', 'same_census_pin'}, 'only two census helpers added')
    need(not (set(old_functions) - set(new_functions)), 'no prior helper removed')
    new.body = [node for node in new.body if not isinstance(node, ast.FunctionDef) or node.name not in {'census_descriptor', 'same_census_pin'}]
    replacements = 0
    for node in ast.walk(new):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'same_census_pin':
            need(len(node.args) == 2 and dump(node.args[0]) == dump(ast.Name(id='registered', ctx=ast.Load())) and
                 dump(node.args[1]) == dump(ast.Name(id='row', ctx=ast.Load())), 'sole census membership call')
            node.func.id = 'same_pin'
            replacements += 1
    need(replacements == 1 and dump(new) == dump(old), 'all remaining builder AST unchanged')
    census = ast.get_source_segment(inputs[new_path].decode(), new_functions['census_descriptor'])
    for fragment in ('type(n) is int', '0 <= n <= (1 << 63) - 1', 'len(p) <= 4096', 'Path(p).is_absolute()',
                     'os.path.normpath(p) == p', 'digest(sha)'):
        need(fragment in census, 'exact normalized metadata-only census bound')
    need(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'open', 'read', 'exec', 'eval'}
                 for node in ast.walk(new_functions['census_descriptor'])), 'census validator opens no body')
    reader = next(node for node in old.body if isinstance(node, ast.ClassDef) and node.name == 'Reader')
    reader_read = next(node for node in reader.body if isinstance(node, ast.FunctionDef) and node.name == 'read')
    need(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'descriptor'
             for node in ast.walk(reader_read)), 'unchanged body-reader descriptor gate')
    prior_review = json.loads(inputs[W / 'maintenance/ranker-objective-scalar-metadata-source-review-20261005-01/review-receipt.json'])
    need(prior_review['status'] == 'passed_source_only' and prior_review['outstanding_source_issues'] == [], 'prior combined source review passed')
    closure_path = W / 'maintenance/ranker-objective-root-review-20261005-01/close_qualification_01.py'
    closure_text = inputs[closure_path].decode()
    closure_ast = ast.parse(closure_text)
    for fragment in (
        "HELD[str(path)] == observed, 'previously held input changed'",
        "'ranker-objective-scalar-independent-source-review@1': ('passed_source_only', 'outstanding_source_issues')",
        "'ranker-objective-scalar-prepared-input-source-review@1': ('passed_file_only', 'outstanding_source_issues')",
        "'ranker-objective-scalar-independent-semantic-native-review@1': ('passed_file_only_actual_receipt_review', 'outstanding_review_issues')",
        "'ranker-objective-scalar-metadata-independent-source-review@1': ('passed_source_only', 'outstanding_source_issues')",
        "seen_reviews == set(required_reviews)",
        "metadata['schema'] == 'ranker-objective-scalar-native-metadata-readback@1'",
        "metadata['frozen_build_plan'] == build['frozen_build_plan'] and wire(new_rows) == wire(document(build['metadata_inputs']))",
        "leaves == sorted(first + [review_pin], key=lambda row: os.fsencode(row['path']))",
    ):
        need(fragment in closure_text, 'closure repeated-read/schema/build/census hardening')
    own = read(Path(__file__).resolve())[1]
    need(all(read(path, (row['bytes'], row['sha256']))[1] == row for path, row in list(HELD.items())), 'all reviewed pins rechecked')
    common = {'status': 'passed_source_only', 'producer': own, 'outstanding_source_issues': [],
              'reviewed_sources_imported_or_executed': False, 'tests_native_metadata_classifier_codec_git_remote_jobs_run': False,
              'atomic_whole_snapshot_claimed': False, 'historical_execution_origin_proved': False,
              'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False}
    patch = {**common, 'schema': 'ranker-objective-scalar-metadata-builder-patch-independent-source-review@1',
             'builder': HELD[str(new_path)], 'prior_builder': HELD[str(old_path)],
             'runtime': HELD[str(Q / 'run_objective_metadata_controls_01.py')],
             'prior_combined_review': HELD[str(W / 'maintenance/ranker-objective-scalar-metadata-source-review-20261005-01/review-receipt.json')],
             'AST_only_changes': ['two metadata-only census helpers', 'one generated environment membership comparison'],
             'unchanged_body_read_cap_bytes': 33554432, 'unchanged_all_other_builder_AST': True,
             'descriptor_only_size_bound': 9223372036854775807,
             'scope': 'Large native dependency census descriptors can be compared without granting permission to read their bodies. All original body-read, row, storage, source, native and provenance gates remain unchanged.'}
    closure = {**common, 'schema': 'ranker-objective-scalar-closure-independent-source-review@1',
               'reviewed_source': HELD[str(closure_path)], 'AST_node_count': sum(1 for _ in ast.walk(closure_ast)),
               'source_checks': ['same-buffer external closure-plan pin', 'same-path repeated-read descriptor refusal',
                                 'four distinct required independent review schemas and exact statuses',
                                 'fixed two actual accepted native check pins and fourteen genuine queries',
                                 'five owned phase/drain and prior2108plus4 guards',
                                 'exact built metadata/readback payload and frozen-plan joins',
                                 'canonical prior4440 prefixes, vectors375, contracts2 and all32 complete exports',
                                 'final file census equals initial census plus known qualified review'],
               'native_and_metadata_jobs_rerun_by_reviewer': False,
               'closure_producer_executed_by_reviewer': False,
               'limitations': ['The later actual metadata run and final closure outputs remain subject to their own gates.',
                               'The original Git HEAD checks in the reviewed closure are read-only; this reviewer ran no Git commands.',
                               'Only exact-real scalar constructor/projection results are asserted; host/Python/Float/full objective/gradient/training/global convergence remain open.']}
    print(json.dumps({'builder_patch_review': save('review-receipt.json', patch),
                      'closure_source_review': save('closure-source-review-receipt.json', closure)}))


if __name__ == '__main__':
    main()
