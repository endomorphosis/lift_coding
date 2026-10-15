"""Independent bounded source-only review of the unexecuted closer02 patch."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
ROOT = W / 'maintenance/ranker-objective-container-core-v1-failure-closure-source-review-20261005-02'
Q = W / 'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-01'
P = W / 'maintenance/ranker-objective-container-core-v1-failure-closure-20261005-01'
EXPECTED = {
    P/'close_failed_v1_01.py': (16379, 'c58db4e0c928630bd95a47a9692e9bb849c953792bcd2f003e89032a392b1ac4'),
    P/'close_failed_v1_02.py': (18157, '4e9bbf4766c5b17c1cf4b6db48b464d941244b59f3189d74ad35d56c0ae76be3'),
    P/'closure-attempt-01.json': (679, '5f9feaeaae801439656684871cf94938d411c30a905b831ef52100e3b75c3007'),
    Q/'evidence/lean-objective-container-core-01/closed.json': (18690, '37b775169ca4c2cc34a94b1dedfe33d30a5f438af63bb468536218da89168464'),
    Q/'evidence/lean-objective-container-core-01/check-result.json': (10128, '9eea43fd7e1a67da9b135b84e3ad2646d5cbb42488baa3c31a8f74bcd86e4d80'),
    Q/'preparation/request-v3.json': (628543, 'b1aba00577a79bb2e2818ddb426c3422d8247124b9fc274ae3a7620a4ff4e90d'),
    W/'maintenance/ranker-objective-container-core-input-review-20261005-01/review-receipt.json': (2616, '4c003a3cdaa3dda51bd07137b30e181af748dee5b29399cfa0ebbaf0beb1512b'),
}

def need(value, message):
    if value is not True:
        raise ValueError(message)

def read(path):
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical source/input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and first.st_size <= 1024**2, 'bounded regular review input')
        parts, total = [], 0
        while part := os.read(fd, 65536):
            total += len(part)
            need(total <= first.st_size, 'review input grew')
            parts.append(part)
        signature = lambda x: (x.st_dev, x.st_ino, x.st_mode, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
        need(total == first.st_size and signature(first) == signature(os.fstat(fd)) == signature(path.lstat()), 'review input changed')
        raw = b''.join(parts)
        pin = {'path': str(path), 'bytes': total, 'sha256': hashlib.sha256(raw).hexdigest()}
        if path in EXPECTED:
            need((pin['bytes'], pin['sha256']) == EXPECTED[path], 'external exact input pin')
        return raw, pin
    finally:
        os.close(fd)

def main():
    need(__debug__, 'optimized source review refused')
    loaded = {path: read(path) for path in EXPECTED}
    old, new = [loaded[P/name][0].decode() for name in ('close_failed_v1_01.py', 'close_failed_v1_02.py')]
    old_tree, new_tree = ast.parse(old), ast.parse(new)
    old_funcs = {node.name: ast.dump(node, include_attributes=False) for node in old_tree.body if isinstance(node, ast.FunctionDef)}
    new_funcs = {node.name: ast.dump(node, include_attributes=False) for node in new_tree.body if isinstance(node, ast.FunctionDef)}
    need(set(old_funcs) == set(new_funcs) and all(old_funcs[key] == new_funcs[key] for key in old_funcs if key != 'main'), 'all I/O, census, cap and writer helper ASTs unchanged')
    need([ast.dump(n, include_attributes=False) for n in old_tree.body if isinstance(n, (ast.Import, ast.ImportFrom))] ==
         [ast.dump(n, include_attributes=False) for n in new_tree.body if isinstance(n, (ast.Import, ast.ImportFrom))], 'imports unchanged')
    need(old.count('for body in (request,owned,check):authority_false(body)') == 1 and
         'for body in (request,check):authority_false(body)' in new and
         "and 'planner_activation' not in owned" in new and
         "prepared['planner_activation'] is False" in new, 'explicit legacy authority format patch')
    owned = json.loads(loaded[Q/'evidence/lean-objective-container-core-01/closed.json'][0])
    docs = [json.loads(loaded[path][0]) for path in (Q/'preparation/request-v3.json', Q/'evidence/lean-objective-container-core-01/check-result.json', W/'maintenance/ranker-objective-container-core-input-review-20261005-01/review-receipt.json')]
    keys = ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')
    need('planner_activation' not in owned and all(owned[key] is False for key in keys[:3]), 'actual legacy owned authority format')
    need(all(body[key] is False for body in docs for key in keys), 'actual frozen request/check/prepared deny all authorities')
    attempt = json.loads(loaded[P/'closure-attempt-01.json'][0])
    need(attempt['producer'] == loaded[P/'close_failed_v1_01.py'][1] and attempt['exception_key'] == 'planner_activation' and
         attempt['new_review_or_seal_written'] is False and attempt['old_source_or_receipt_mutations'] == 0 and
         attempt['native_or_model_or_test_or_metadata_jobs'] == 0, 'safe retained pre-output refusal')
    need(owned['status'] == 'failed' and docs[1]['status'] == 'inconclusive' and docs[1]['compiled_artifacts'] == [] and
         docs[1]['retained_chunk_artifacts'] == [], 'no qualified object from failed native diagnostics')
    for token in ("len(initial)==28", "==10850381", "len(rows)==29", "'qualified_native_checks':0", "'qualified_theorem_queries':0", "'only review and seal append complete final census'", "'cpu_seconds':20", "'timeout_seconds':20"):
        need(token in old and token in new, 'unchanged census/qualification/native predicate')
    need(all(read(path)[1] == pin for path, (_, pin) in loaded.items()), 'all review inputs rehashed')
    own_pin = read(Path(__file__).resolve())[1]
    result = {
        'schema': 'ranker-objective-container-core-failed-closure-independent-source-review@1',
        'status': 'passed_source_only', 'findings': [],
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': own_pin, 'reviewed_source': loaded[P/'close_failed_v1_02.py'][1],
        'reviewed_input_pins': [pin for _, pin in loaded.values()],
        'reviewed_patch': ['Self path selects immutable successor02.', 'Legacy owned receipt requires exactly three present false authority fields and absent planner field; separately pinned request/check/prepared require planner false.', 'Immutable executed closer01 and its safe pre-output KeyError receipt are joined and retained in output provenance.'],
        'reviewed_unchanged_controls': ['All I/O/census/descriptor/JSON/writer helper ASTs and imports unchanged.', 'Original 28 leaves and 10,850,381 bytes retained; exclusive review append then 29-leaf seal plus self.', 'Native inconclusive return1 and zero compiled objects imply zero qualified checks/queries.', 'Native 20-second bounds, strict2391/live4 pins, final held rehash, original guard joins, cleanup/drain and four false output authorities unchanged.'],
        'mode': 'unexecuted_target_source_only', 'source_execution_calls': 0,
        'native_test_model_metadata_or_remote_jobs': 0,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False,
        'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
        'limits': ['Root must execute the exact reviewed successor and retain its actual result. This review executes only its independent stdlib reviewer; no closer or target source is imported or executed.']}
    output = ROOT/'review-receipt.json'
    with output.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+'\n').encode())
        stream.flush(); os.fsync(stream.fileno())
    print(json.dumps(read(output)[1], sort_keys=True))

if __name__ == '__main__':
    main()
