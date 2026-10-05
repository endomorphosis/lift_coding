"""Review inert closure source bytes and AST only, with no target execution."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
HERE = Path(__file__).resolve().parent
ROOT = W / 'maintenance/ranker-objective-root-review-20261005-01'
PINS = {
    ROOT / 'close_qualification_01.py': (19691, '9d68d8c8575f47887bde85bbda88d57db91a563f91b73756bffe30c405ddeec4'),
    ROOT / 'close_qualification_02.py': (20940, '78c83eec498e1d4432747238f3695b7b7ea40dbc71eedffb22b05b55a2fb7c00'),
    W / 'maintenance/ranker-objective-scalar-metadata-source-review-20261005-02/closure-source-review-receipt.json':
        (2062, '66fbb0c99c08b4192c62f519f4993b6aa3ab734e8dd864fa1fe2df37652e7ccc'),
}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path, expected=None):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical review input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and 0 <= first.st_size <= 1024**2, 'bounded review source')
        chunks, total = [], 0
        while block := os.read(fd, 65536):
            total += len(block)
            need(total <= 1024**2, 'running review read cap')
            chunks.append(block)
        raw = b''.join(chunks)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda row: tuple(getattr(row, key) for key in keys)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and total == first.st_size, 'review input drift')
    finally:
        os.close(fd)
    binding = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected is not None:
        need((binding['bytes'], binding['sha256']) == expected, 'fixed reviewed source pin')
    return raw, binding


def main():
    need(__debug__, 'optimized reviewer refused')
    need(not (HERE / 'review-receipt.json').exists(), 'fresh receipt required')
    raw, pins = {}, {}
    for path, expected in PINS.items():
        raw[path], pins[str(path)] = read(path, expected)
    old_path, new_path = ROOT / 'close_qualification_01.py', ROOT / 'close_qualification_02.py'
    old_ast, new_ast = ast.parse(raw[old_path]), ast.parse(raw[new_path])
    old_pin = next(node for node in old_ast.body if isinstance(node, ast.FunctionDef) and node.name == 'pin')
    new_pin = next(node for node in new_ast.body if isinstance(node, ast.FunctionDef) and node.name == 'pin')
    old_ast.body.remove(old_pin)
    new_ast.body.remove(new_pin)
    need(ast.dump(old_ast, include_attributes=False) == ast.dump(new_ast, include_attributes=False), 'only pin function changed')
    new_segment = ast.get_source_segment(raw[new_path].decode(), new_pin)
    for fragment in ("os.O_RDONLY | os.O_NOFOLLOW", "stat.S_ISREG(first.st_mode)",
                     '0 <= first.st_size <= 256 * 1024**2', 'os.read(fd, 1024**2)',
                     'total <= 256 * 1024**2', 'digest.update(block)',
                     'signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and total == first.st_size',
                     "HELD[str(path)] == observed, 'previously held guard changed'"):
        need(fragment in new_segment, 'streaming guard cap/stat/repeated pin protection')
    need(not any(isinstance(node, (ast.List, ast.ListComp)) for node in ast.walk(new_pin)), 'no whole guard body accumulation')
    prior_path = W / 'maintenance/ranker-objective-scalar-metadata-source-review-20261005-02/closure-source-review-receipt.json'
    prior = json.loads(raw[prior_path])
    need(prior['status'] == 'passed_source_only' and prior['outstanding_source_issues'] == [] and
         prior['reviewed_source'] == pins[str(old_path)], 'exact prior source-review join')
    own = read(Path(__file__).resolve())[1]
    for path, expected in PINS.items():
        need(read(path, expected)[1] == pins[str(path)], 'final source pin drift')
    result = {'schema': 'ranker-objective-scalar-closure-patch-independent-source-review@1',
              'status': 'passed_source_only', 'producer': own, 'reviewed_source': pins[str(new_path)],
              'prior_source': pins[str(old_path)], 'prior_source_review': pins[str(prior_path)],
              'only_changed_AST_function': 'pin', 'streaming_block_bytes': 1048576,
              'streaming_guard_file_max_bytes': 268435456, 'unchanged_parsed_body_max_bytes': 33554432,
              'canonical_regular_no_follow_and_FD_path_stat_guards': True,
              'repeated_HELD_descriptor_conflicts_refused': True, 'whole_body_accumulation': False,
              'all_other_closure_AST_unchanged': True, 'outstanding_source_issues': [],
              'target_imports_or_execution': False, 'runtime_native_tests_metadata_git_remote_jobs_run': False,
              'actual_closure_execution_or_outputs_reviewed_here': False,
              'scope': 'A descriptor-only streaming hash may cover prior large guard inputs while all parsed document reads retain their original 32 MiB limit. The previous independent closure source gates remain unchanged.',
              'atomic_whole_source_snapshot_claimed': False, 'historical_execution_origin_proved': False,
              'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False}
    with (HERE / 'review-receipt.json').open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'review': read(HERE / 'review-receipt.json')[1]}))


if __name__ == '__main__':
    main()
