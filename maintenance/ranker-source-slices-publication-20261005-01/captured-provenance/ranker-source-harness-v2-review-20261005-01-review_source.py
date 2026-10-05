"""Independent source/AST/JSON review; never import or execute target producers."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
Q4 = WORKSPACE / 'qualification/codebase_ir/ranker-source-semantics-20261005-01'
OUT = Path(__file__).resolve().parent
V1_SHA = '362a6ad08063f9920b114f4a68edba87c732b1e5e3e3a24e6f9ba01a96a590f4'
V2_SHA = '3c183e16c3b0b5578048f60055953a34965b958c793734ad59ade9a2e1d68d96'
held = {}


def require(condition, reason):
    if condition is not True:
        raise ValueError(reason)


def read(path, expected=None):
    path = Path(path).absolute()
    require(path.resolve(strict=True) == path, 'canonical input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= 16 * 1024**2,
                'regular bounded source/receipt input required')
        blocks, count = [], 0
        while block := os.read(fd, 1024**2):
            count += len(block)
            require(count <= 16 * 1024**2, 'read bound exceeded')
            blocks.append(block)
        raw = b''.join(blocks)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda value: tuple(getattr(value, key) for key in fields)
        require(signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
                and len(raw) == before.st_size, 'input changed while reading')
    finally:
        os.close(fd)
    binding = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    require(expected is None or binding['sha256'] == expected, 'external source pin mismatch')
    held[str(path)] = binding
    return raw


def functions(tree):
    result, counts = {}, {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            count = counts.get(node.name, 0)
            counts[node.name] = count + 1
            result[(node.name, count)] = node
    return result


def has(text, fragments):
    for fragment in fragments:
        require(fragment in text, 'missing reviewed source gate: ' + fragment)


def main():
    paths = [Q4 / 'run_source_semantics_controls.py', Q4 / 'run_source_semantics_controls_v2.py',
             Q4 / 'freeze_source_profile_01.py', Q4 / 'prepare_request_01.py']
    expectations = [V1_SHA, V2_SHA,
                    '82d36418fc74f5b32ea759b11b2af92aadc6c3d683f4a4cdafbc72edba781de8',
                    '7e54562d463afb399bcc98940f0457a4005436f93e0b0dbbda9107070a0ed027']
    buffers = [read(path, pin) for path, pin in zip(paths, expectations)]
    require(len(buffers[0]) == 37853 and len(buffers[1]) == 38817, 'final harness byte counts')
    trees = [ast.parse(raw) for raw in buffers]
    old, new = functions(trees[0]), functions(trees[1])
    require(set(old) == set(new), 'function interface population changed')
    changed = {key for key in old if ast.dump(old[key], include_attributes=False) !=
               ast.dump(new[key], include_attributes=False)}
    require(changed == {('owned', 0), ('metadata', 0), ('metadata', 1)}, 'unexpected function changes')
    require(len(trees[0].body) == len(trees[1].body), 'module statement population changed')
    for before, after in zip(trees[0].body, trees[1].body):
        if not isinstance(before, ast.FunctionDef):
            require(ast.dump(before, include_attributes=False) == ast.dump(after, include_attributes=False),
                    'module or CLI guard changed')
    old_owned, owned = ast.unparse(old[('owned', 0)]), ast.unparse(new[('owned', 0)])
    require(old_owned.replace("ROOT / 'source'", "ROOT / 'source-v2'") == owned,
            'owned controller change exceeds isolated source-v2 path')
    metadata = ast.unparse(new[('metadata', 1)])
    has(metadata, ["len(prior) == len(records) == 32", "set(records) == set(prior)",
                   "sum(map(len, prior.values())) == 4417",
                   "canonical(records[family][:len(values)]) == canonical(values)",
                   "canonical(records['vectors']) == canonical(prior['vectors'])",
                   "len(additions) == 2", "domain['record_kind'] == 'mathematical_projection_domain'",
                   "domain['runtime_enforced'] is False", "domain['python_source_contract_proved'] is False",
                   "domain['numeric_backend'] == 'exact_real'",
                   "type(domain['dimension']) is int and domain['dimension'] == 80",
                   "canonical(exported) == canonical(values)",
                   "native['fresh_process_readback']['verified'] is True"])
    delta = next(node.value for node in new[('metadata', 1)].body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == 'expected_delta' for target in node.targets))
    require(ast.literal_eval(delta) == {'ast': 2, 'sources': 3, 'contracts': 2,
                                       'ranker_real_curvature_proofs': 2,
                                       'ranker_real_curvature_checks': 3, 'kg': 11}, 'exact 23-row delta whitelist')
    has(metadata, ["expected_delta.get(family, 0)", "'prior_wrapper_row_ids_rebound_to_new_source_snapshot': True",
                   "'prior_contract_payloads_preserved_and_vectors_unchanged': True",
                   "'new_mathematical_projection_domain_contract_rows': 2",
                   "'strict_advisory_cache_entries_added_in_this_phase': 0",
                   "'all32_governing_RPI_exits': 'OPEN'", "'full_task_satisfaction': 'unknown'"])
    require('contracts_and_vectors_payloads_unchanged' not in metadata, 'stale unchanged-contract claim')
    dispatch = [node.args[0].value for node in ast.walk(new[('owned', 0)]) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr == 'startswith'
                and isinstance(node.func.value, ast.Name) and node.func.value.id == 'mode']
    require(sorted(dispatch) == ['compile-source', 'lean', 'metadata', 'pure-tests'], 'authorized dispatch changed')
    has(owned, ["cpu_slots=1, memory_mb=2048, child_process_slots=4, timeout=30",
                '2.0, 50.0, 10.0, 2.0', 'source-slice qualification refuses ranker module import',
                'lease.release()', "state['active_lease_count'] == state['waiting_request_count'] == 0"])
    require(owned.count('verify(h, request)') == 2, 'before/after inherited source guards')
    has(buffers[1].decode(), ['if not __debug__:', 'timeout=120', 'use the separately pinned file-only prepare_request_01.py'])
    prior_review_path = WORKSPACE / 'maintenance/ranker-source-harness-review-20261005-01/review-receipt.json'
    prior_review = json.loads(read(prior_review_path))
    require(prior_review['status'] == 'passed_source_only_review' and prior_review['outstanding_issues'] == [],
            'inherited review not passed')
    require(prior_review['reviewed_producers'] == [held[str(paths[0])], held[str(paths[2])], held[str(paths[3])]],
            'inherited reviewed producer pins changed')
    request_path = Q4 / 'preparation/request-v3.json'
    request = json.loads(read(request_path, '4858034f642fcedd31d7b243d65156eade84332e8401578df12e0c8f30c30861'))
    require(len(request['strict_old_inputs']) == 1808 and len(request['protected_live_sources']) == 4,
            'inherited request denominators changed')
    require(request['root_request'] == {'cpu_slots': 1, 'memory_mb': 2048, 'child_process_slots': 4}
            and request['outer_timeout_seconds'] == 120, 'root/outer caps changed')
    require(request['proof_limits'] == {'wall_seconds': 20, 'cpu_seconds': 20, 'output_bytes': 65536,
                                        'workspace_bytes': 16777216}, 'native bounds changed')
    for flag in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation',
                 'full_source_runtime_equivalence', 'source_interpreter_semantics_proved',
                 'binary64_error_bound_proved', 'native_Float_optimizer_convergence_proved',
                 'global_autoencoder_convergence_proved'):
        require(request[flag] is False, 'request authority/frontier changed')
    reviewed = dict(held)
    for path, binding in reviewed.items():
        read(path)
        require(held[path] == binding, 'reviewed inputs changed before receipt')
    self_path = Path(__file__).resolve()
    read(self_path)
    receipt = {'schema': 'ranker-source-semantics-harness-v2-independent-source-review@1',
               'status': 'passed_source_only_review', 'outstanding_issues': [],
               'review_source': held[str(self_path)], 'reviewed_producers': [held[str(path)] for path in paths],
               'inherited_review': held[str(prior_review_path)], 'request': held[str(request_path)],
               'changed_functions': [[name, index] for name, index in sorted(changed)],
               'dispatch_prefixes': sorted(dispatch), 'strict_old_input_count_in_request': 1808,
               'protected_live_source_count_in_request': 4,
               'guard_leaf_revalidation_in_this_review': False,
               'guard_leaf_revalidation_scope': 'Prior durable review is inherited; this review checks source changes and request pins only.',
               'metadata_delta': ast.literal_eval(delta), 'metadata_additions': 23,
               'metadata_prior_rows': 4417, 'metadata_result_rows': 4440,
               'findings': ['Only owned source-v2 search path and metadata gates change.',
                            'Canonical prior payload prefixes, vectors and complete exports preserve numeric types.',
                            'Exactly two mathematical domain contracts require false runtime/Python-contract claims and exact integer80.',
                            'Exact32 family set and exact23 per-family additions preserve every other family.',
                            'Inherited request/freezer/controller/native/root/import/process/optimization guards retain exact source pins.',
                            'No source runtime, Float, objective, training, task or authority frontier is closed by this review.'],
               'scope': {'source_only': True, 'target_imports': 0, 'target_execution': 0, 'test_jobs': 0,
                         'native_jobs': 0, 'model_jobs': 0, 'codec_jobs': 0, 'Git_actions': 0,
                         'remote_actions': 0, 'protected_writes': 0,
                         'proof_authority': False, 'execution_authority': False, 'completion_authority': False}}
    target = OUT / 'review-receipt.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    raw = target.read_bytes()
    print(json.dumps({'status': receipt['status'], 'harness': held[str(paths[1])],
                      'receipt': {'path': str(target), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                      'review_source': receipt['review_source']}))


if __name__ == '__main__':
    main()
