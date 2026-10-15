#!/usr/bin/env python3
"""Independently rebuild retained public qualification inputs without a provider."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/terminal-query-reference-20261012')
DATASETS = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-datasets-20261011')
sys.path[:0] = [str(SOURCE), str(DATASETS)]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('bounded regular evidence required')
    raw = path.read_bytes()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate evidence key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique), sha(raw)


def main():
    from benchmarks.agent_supervisor.container_coding.terminal_context_audit import _receipt, _model_projection
    from benchmarks.agent_supervisor.container_coding.terminal_source_view_experiment import local_token_counter
    from ipfs_accelerate_py.agent_supervisor.runtime.semantic_query_reference import restore_semantic_query_reference
    evidence = ROOT / 'public-final'
    qualification, evidence_sha = read(evidence / 'qualification.json')
    expected_tasks = {'tune-mjcf', 'llm-inference-batching-scheduler'}
    rows = qualification['tasks']
    if (len(rows) != 2 or {row['task_name'] for row in rows} != expected_tasks
            or qualification['provider_calls'] != 0 or qualification['qualified'] is not True):
        raise ValueError('complete qualified two-task population required')
    counter, tokenizer = local_token_counter()
    if tokenizer != qualification['local_tokenizer']:
        raise ValueError('local tokenizer binding changed')
    observations = []
    for row in rows:
        directory = evidence / row['task_name']
        repository = directory / 'repository'
        if (directory / 'allocated-worktree').exists():
            raise ValueError('qualification worktree must already be removed')
        native, native_file_sha = read(directory / 'native-context-input.json')
        native_prompt = json.dumps(native, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if native_file_sha != row['native_context_input_sha256'] or sha(native_prompt.encode()) != row['native_prompt_sha256']:
            raise ValueError('retained native context binding changed')
        if [arm['policy'] for arm in row['arms']] != ['legacy', 'required-instruction-ref@1']:
            raise ValueError('exact paired input population required')
        original = None
        for arm in row['arms']:
            policy = arm['policy']
            receipt, receipt_sha = read(directory / ('legacy-receipt.json' if policy == 'legacy' else 'reference-receipt.json'))
            if receipt_sha != arm['receipt_sha256']:
                raise ValueError('retained receipt binding changed')
            parsed = _receipt(receipt, directory)
            model, _, checks = _model_projection(rendered=native_prompt, receipt=parsed, repository=repository)
            model_bytes = model.encode()
            if (not all(value is True for value in checks.values())
                    or sha(model_bytes) != arm['full_input_sha256'] or len(model_bytes) != arm['full_input_bytes']
                    or (counter(model) if counter else None) != arm['full_input_proxy_tokens']):
                raise ValueError('reconstructed complete input differs from captured measurement')
            start = receipt['workspace_advisory_bytes']
            router = model_bytes[start:start + receipt['router_prompt_bytes']].decode()
            if policy == 'legacy':
                original = router
            elif restore_semantic_query_reference(provider_prompt=router, receipt=receipt['query_reference_view']) != original:
                raise ValueError('independent exact query restoration failed')
            observations.append({'task': row['task_name'], 'policy': policy,
                'model_prompt_sha256': sha(model_bytes), 'model_prompt_bytes': len(model_bytes),
                'local_tokenizer_proxy_tokens': counter(model) if counter else None,
                'full_input_exact': True, 'workspace_absent': True})
    result = {'schema': 'terminal-query-reference-independent-replay@1',
        'qualification_sha256': evidence_sha, 'source': str(SOURCE),
        'script_sha256': sha(Path(__file__).read_bytes()), 'inputs': observations,
        'all_four_inputs_exact': len(observations) == 4,
        'provider_calls': 0, 'containers_started': 0,
        'hidden_verifiers_or_solutions_read': False, 'provider_logs_read': False,
        'local_proxy_is_provider_usage': False}
    with (ROOT / 'independent-public-replay.json').open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'replayed_inputs': len(observations), 'all_exact': True, 'provider_calls': 0}))


if __name__ == '__main__':
    main()
