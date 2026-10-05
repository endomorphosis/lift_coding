"""File/source-only emitter correction review; no target imports or execution."""
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
Q = WORKSPACE / 'qualification/codebase_ir/ranker-source-semantics-20261005-01'
OUT = Path(__file__).resolve().parent
OLD_PROOF = '''  simpa only [RankerRealCurvature.realGradientStep] using
    emitted_update_projection RankerRealCurvature.originalRealEta weights
      (RankerRealCurvature.realCoordinateGradient RankerRealCurvature.originalRealMu
        RankerRealCurvature.originalRealDifferences weights)'''
NEW_PROOF = '''  rw [emitted_update_projection]
  rfl'''


def read(path):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path:
        raise ValueError('aliased review input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('nonregular review input')
        chunks = []
        while block := os.read(fd, 1024**2):
            chunks.append(block)
        raw = b''.join(chunks)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda row: tuple(getattr(row, key) for key in keys)
        if signature(before) != signature(os.fstat(fd)) or signature(before) != signature(path.lstat()) or len(raw) != before.st_size:
            raise ValueError('input changed during read')
        return raw
    finally:
        os.close(fd)


def pin(path, raw=None):
    raw = read(path) if raw is None else raw
    return {'path': str(Path(path).absolute()), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    old_paths = sorted((Q / 'source').rglob('*'))
    held = {path: read(path) for path in old_paths if path.is_file()}
    old = Q / 'source/typed_slice_compiler.py'
    tests_old = Q / 'source/test_typed_slice_compiler.py'
    new = Q / 'source-v2/typed_slice_compiler.py'
    tests_new = Q / 'source-v2/test_typed_slice_compiler.py'
    compiler_old = held[old]
    compiler_new = read(new)
    tests = read(tests_new)
    if pin(old, compiler_old)['sha256'] != 'f318a6879d9eac517127a4440cfca8e48b2ad61a7411453b16f17847b3dd1f06':
        raise ValueError('frozen v1 compiler differs')
    if pin(tests_old, held[tests_old])['sha256'] != 'fd3a6a4926786aa8f45dc2bfc6419c0577c64c93523f1e6e80d2ee2d501b44b3':
        raise ValueError('frozen v1 tests differ')
    if compiler_old.decode().count(OLD_PROOF) != 1 or compiler_new != compiler_old.replace(OLD_PROOF.encode(), NEW_PROOF.encode(), 1):
        raise ValueError('change exceeds the one emitted proof correction')
    if tests != held[tests_old]:
        raise ValueError('tests need no text change for this correction')
    before_ast = ast.parse(compiler_old)
    after_ast = ast.parse(compiler_new)
    ast.parse(tests)
    old_definitions = {node.name: ast.dump(node, include_attributes=False) for node in before_ast.body if isinstance(node, ast.FunctionDef)}
    new_definitions = {node.name: ast.dump(node, include_attributes=False) for node in after_ast.body if isinstance(node, ast.FunctionDef)}
    changed = [name for name in old_definitions if old_definitions[name] != new_definitions.get(name)]
    if changed != ['render_generated_lean'] or old_definitions.keys() != new_definitions.keys():
        raise ValueError('compiler APIs or numerical translation changed')
    check_path = Q / 'evidence/lean-typed-scalar-02/check-result.json'
    check_raw = read(check_path)
    check = json.loads(check_raw)
    if check['status'] != 'passed' or check['matches_expectation'] is not True or len(check['theorem_axiom_output']) != 14:
        raise ValueError('referenced corrected generic module not actually qualified')
    allowed = {'propext', 'Classical.choice', 'Quot.sound'}
    if any(not set(row['axioms']) <= allowed for row in check['theorem_axiom_output']):
        raise ValueError('referenced generic module has an unexpected axiom')
    if not all(read(path) == raw for path, raw in held.items()) or read(new) != compiler_new or read(tests_new) != tests or read(check_path) != check_raw:
        raise ValueError('whole reviewed inputs changed across review')
    diff = ''.join(difflib.unified_diff(compiler_old.decode().splitlines(True), compiler_new.decode().splitlines(True), fromfile=str(old), tofile=str(new)))
    report = {'schema': 'ranker-source-emitter-v2-file-only-diff-review@1', 'status': 'passed_source_only_diff_review', 'outstanding_issues': [], 'review_source': pin(Path(__file__).resolve()), 'v1_compiler': pin(old, compiler_old), 'v2_compiler': pin(new, compiler_new), 'v1_tests': pin(tests_old, held[tests_old]), 'v2_tests': pin(tests_new, tests), 'unchanged_v1_source_population': [pin(path, raw) for path, raw in held.items()], 'qualified_generic_module_check': pin(check_path, check_raw), 'changed_function': changed, 'exact_diff': diff, 'findings': ['Only the emitted_originalRealStep_join proof string changes.', 'Rewriting emitted_update_projection exposes the same coordinate update expression; rfl then unfolds the existing realGradientStep definition.', 'This mirrors the corrected generic module proof that actually passed fourteen bounded native queries.', 'All compiler APIs, pinned original AST/source identity, IR translation, list/shape semantics, constructor rendering and seven generated theorem query names are unchanged.', 'Tests copy byte-for-byte; the existing renderer test checks gates, bodies, hashes and absence of sorry/axiom declarations without depending on the superseded proof text.', 'The emitter remains a candidate until its fresh generated module actually qualifies.'], 'scope': {'source_only': True, 'target_imports': 0, 'target_execution': 0, 'test_jobs': 0, 'native_jobs': 0, 'ranker_execution': 0, 'codec_jobs': 0, 'remote_actions': 0, 'Git_actions': 0, 'old_input_writes': 0, 'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'full_Python_or_Float_equivalence_proved': False}}
    destination = OUT / 'review-receipt.json'
    with destination.open('xb') as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': report['status'], 'compiler': report['v2_compiler'], 'tests': report['v2_tests'], 'receipt': pin(destination), 'review_source': report['review_source']}))


if __name__ == '__main__':
    main()
