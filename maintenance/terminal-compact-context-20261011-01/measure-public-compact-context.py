"""Offline paired representation measurement; never dispatch a provider/prover.

Run with the isolated checkout and its dependency roots on PYTHONPATH. The only
optional network operation is a bounded, independently SHA256-verified public
o200k_base vocabulary download. All fixture state and signing keys are fresh.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import time
import urllib.request

DEFAULT_CODE = Path('/home/barberb/lift_coding/maintenance/terminal-coding-transport-20261011-01/pilot/coding-identifiers-01/jobs/supervisor-full-identifiers-fix-code-vulnerability/fix-code-vulnerability__NW2EqdA/agent/public-output-evidence/before/bottle.py')


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def capture(path, maximum):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path:
        raise ValueError('canonical source path required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise ValueError('bounded independent regular source required')
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            raw = handle.read(maximum + 1)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if len(raw) > maximum or any(getattr(before, key) != getattr(after, key) for key in fields):
            raise ValueError('source changed during capture')
    finally:
        os.close(fd)
    return raw, {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def write_new(path, raw):
    with Path(path).open('xb') as handle:
        handle.write(raw)


def tokenizer(cache):
    """Use the installed official definition and only its verified public asset."""
    started = time.monotonic()
    result = {'scope': 'LOCAL o200k_base representation counts, not provider usage or an asserted gpt-5.6-sol tokenizer',
              'status': 'unknown', 'provider_native_usage': False}
    try:
        import tiktoken
        from tiktoken_ext import openai_public
        definition = inspect.getsource(openai_public.o200k_base)
        url = re.search(r'"(https://openaipublic\.blob\.core\.windows\.net/encodings/o200k_base\.tiktoken)"', definition).group(1)
        expected = re.search(r'expected_hash="([0-9a-f]{64})"', definition).group(1)
        cache = Path(cache).absolute()
        cache.mkdir(mode=0o700, exist_ok=True)
        if cache.resolve(strict=True) != cache:
            raise ValueError('canonical tokenizer cache required')
        asset = cache / hashlib.sha1(url.encode()).hexdigest()
        downloaded = False
        if not asset.exists():
            chunks, total, deadline = [], 0, time.monotonic() + 30
            with urllib.request.urlopen(url, timeout=30) as response:
                if response.geturl() != url:
                    raise ValueError('tokenizer download redirected')
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('tokenizer download exceeded thirty seconds')
                    if response.fp is None:
                        break
                    response.fp.raw._sock.settimeout(remaining)
                    block = response.read(65536)
                    if not block:
                        break
                    total += len(block)
                    if total > 8 * 1024 * 1024:
                        raise ValueError('tokenizer asset exceeded eight MiB')
                    chunks.append(block)
            raw = b''.join(chunks)
            if sha(raw) != expected:
                raise ValueError('public tokenizer asset SHA256 differs from official definition')
            write_new(asset, raw)
            downloaded = True
        raw, asset_pin = capture(asset, 8 * 1024 * 1024)
        if sha(raw) != expected:
            raise ValueError('cached tokenizer asset SHA256 differs')
        os.environ['TIKTOKEN_CACHE_DIR'] = str(cache)
        encoding = tiktoken.get_encoding('o200k_base')
        result.update(status='available', encoding=encoding.name, vocabulary_size=encoding.n_vocab,
                      tiktoken_version=importlib.metadata.version('tiktoken'), asset=asset_pin,
                      official_expected_sha256=expected, url=url, asset_downloaded=downloaded,
                      official_definition_source=capture(Path(openai_public.__file__), 2 * 1024 * 1024)[1],
                      elapsed_seconds=time.monotonic() - started)
        return encoding, result
    except Exception as error:
        result.update(error_type=type(error).__name__, reason=str(error)[:256],
                      elapsed_seconds=time.monotonic() - started)
        return None, result


@contextmanager
def offline_execution():
    """Allow only Git and exact interpreter-version probes during the fixture."""
    original_run = subprocess.run
    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
    git_calls = []
    def run(argv, *args, **kwargs):
        allowed = (type(argv) in (list, tuple) and bool(argv) and
                   (Path(argv[0]).name == 'git' or list(argv) == [sys.executable, '--version']))
        if not allowed or kwargs.get('shell'):
            raise AssertionError('offline experiment refuses subprocesses outside Git and exact Python version probes')
        git_calls.append({'executable': str(argv[0]), 'arguments': list(argv[1:])})
        return original_run(argv, *args, **kwargs)
    def connect(*args, **kwargs):
        raise AssertionError('offline fixture cannot open a network connection')
    subprocess.run, socket.socket.connect, socket.socket.connect_ex = run, connect, connect
    try:
        yield git_calls
    finally:
        subprocess.run = original_run
        socket.socket.connect, socket.socket.connect_ex = original_connect, original_connect_ex


def metrics(raw, encoding):
    return {'bytes': len(raw), 'sha256': sha(raw),
            'LOCAL_o200k_base_tokens': len(encoding.encode(raw.decode('utf-8'), disallowed_special=())) if encoding else None}


def field_breakdown(value, encoding):
    rows = {key: metrics(wire(key) + b':' + wire(item), encoding) for key, item in value.items()}
    punctuation = 2 + max(0, len(rows) - 1)
    assert sum(row['bytes'] for row in rows.values()) + punctuation == len(wire(value))
    return {'fields': rows, 'object_punctuation_bytes': punctuation,
            'bytes_additive': True, 'tokens_additive': False}


def producer_pins(modules):
    return {name: capture(Path(module.__file__), 8 * 1024 * 1024)[1] for name, module in modules.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--tokenizer-cache', required=True, type=Path)
    parser.add_argument('--public-code', default=DEFAULT_CODE, type=Path)
    args = parser.parse_args()
    output = args.output.absolute()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    encoding, token_receipt = tokenizer(args.tokenizer_cache)
    write_new(output / 'tokenizer.json', wire(token_receipt))
    code, code_pin = capture(args.public_code, 262144)
    if args.public_code.parent.name != 'before' or args.public_code.parent.parent.name != 'public-output-evidence':
        raise ValueError('only the explicitly allowed captured public before source may be used')
    raw_capture_receipt, capture_receipt_pin = capture(args.public_code.parent / 'receipt.json', 65536)
    captured = json.loads(raw_capture_receipt)
    saved = captured['files']['bottle.py']
    if (saved['status'] != 'captured' or saved['bytes'] != len(code) or saved['sha256'] != sha(code)
            or captured['phase'] != 'before' or captured['candidate_code_executed'] is not False
            or captured['verifier_state_accessed'] is not False):
        raise ValueError('public code bytes differ from selected before-capture receipt')
    names = (
        'benchmarks.agent_supervisor.container_coding.test_terminal_compact_intent_experiment',
        'benchmarks.agent_supervisor.container_coding.terminal_indexed_preparation',
        'benchmarks.agent_supervisor.container_coding.terminal_public_intent_contract',
        'ipfs_accelerate_py.agent_supervisor.planning.intent_symbolic_planning',
        'ipfs_accelerate_py.agent_supervisor.prompt.intent_plan_coverage',
        'ipfs_accelerate_py.agent_supervisor.runtime.local_planning_admission',
        'ipfs_accelerate_py.agent_supervisor.runtime.intent_requirement_context',
        'ipfs_accelerate_py.agent_supervisor.runtime.compact_intent_requirements',
        'ipfs_accelerate_py.agent_supervisor.runtime.router_public_instruction',
        'ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner',
    )
    modules = {name: importlib.import_module(name) for name in names}
    before = producer_pins(modules)
    fixture = modules[names[0]]
    prep, codec, public, runner = modules[names[1]], modules[names[7]], modules[names[8]], modules[names[9]]
    def forbidden(*args, **kwargs):
        raise AssertionError('offline public symbolic fixture cannot invoke planning providers')
    prep.generate_prompt_goal_graph = prep.build_prompt_goal_provider_request = forbidden
    started = time.monotonic()
    with offline_execution() as git_calls:
        case = fixture.build_public_case(output / 'native-fixture', bottle_source=code)
        context = case['context']
        expanded_raw = wire(context)
        compact = codec.encode_task_intent_requirements(context, source_text=case['source_text'])
        decoded = codec.decode_task_intent_requirements(compact, source_text=case['source_text'])
        if wire(decoded) != expanded_raw or wire(context) != expanded_raw:
            raise AssertionError('canonical same-context roundtrip differs')
        expanded_appendix, expanded_projection = public.render_task_intent_requirements(context,
            source_text=case['source_text'], requirements_transport='expanded')
        compact_appendix, compact_projection = public.render_task_intent_requirements(context,
            source_text=case['source_text'], requirements_transport='compact')
        descriptor = public.prepare_public_instruction_context(repository=case['repository'],
            admission=case['admission'], task_cid=case['task'].task_cid,
            source_path=prep.INSTRUCTION, expected_source_sha256=sha(case['source']))
        workspace = output / 'allocated-public-worktree'
        subprocess.run(['git', '-C', str(case['repository']), 'worktree', 'add', '--detach', '-q', str(workspace)],
                       check=True, capture_output=True)
        envelope = wire({'objective_id': case['task'].task_key}).decode()
        request = dict(artifact=Path(descriptor['artifact']), expected_sha256=descriptor['sha256'],
                       task_cid=case['task'].task_cid, prompt=envelope, workspace=workspace)
        expanded_block, expanded_receipt = public.load_public_instruction(**request, requirements_transport='expanded')
        compact_block, compact_receipt = public.load_public_instruction(**request, requirements_transport='compact')
        if not expanded_block.endswith(expanded_appendix) or not compact_block.endswith(compact_appendix):
            raise AssertionError('full loader differs from actual task appendix rendering')
        if expanded_block[:-len(expanded_appendix)] != compact_block[:-len(compact_appendix)]:
            raise AssertionError('literal public instruction wrapper differs between matched arms')
        if expanded_block.count(case['source_text']) != 1 or compact_block.count(case['source_text']) != 1:
            raise AssertionError('literal original instruction must occur exactly once')
        expanded_fragment, workspace_advisory = runner.render_model_prompt(prompt=envelope + expanded_block,
            purpose='coding', workspace=workspace)
        compact_fragment, paired_workspace_advisory = runner.render_model_prompt(prompt=envelope + compact_block,
            purpose='coding', workspace=workspace)
        assert paired_workspace_advisory == workspace_advisory
    values = {
        'expanded-context.json': expanded_raw,
        'compact-payload.json': wire(compact),
        'decoded-context.json': wire(decoded),
        'public-profile.json': wire(case['profile']),
        'native-graph.json': wire(case['planned']['graph'].to_dict()),
        'checked-coverage.json': wire(case['coverage']),
        'symbolic-planning-receipt.json': wire(case['planned']['receipt']),
        'signed-admission.json': wire(case['admission']),
        'public-instruction.md': case['source'],
        'public-code-capture-receipt.json': raw_capture_receipt,
        'expanded-requirements-appendix.txt': expanded_appendix.encode(),
        'compact-selected-appendix.txt': compact_appendix.encode(),
        'expanded-full-public-block.txt': expanded_block.encode(),
        'compact-full-public-block.txt': compact_block.encode(),
        'expanded-model-input-fragment.txt': expanded_fragment.encode(),
        'compact-model-input-fragment.txt': compact_fragment.encode(),
        'workspace-advisory.txt': workspace_advisory.encode(),
        'native-task-envelope.json': envelope.encode(),
        'expanded-inclusion-receipt.json': wire(expanded_receipt),
        'compact-inclusion-receipt.json': wire(compact_receipt),
        'offline-subprocess-observations.json': wire(git_calls),
    }
    for name, raw in values.items():
        write_new(output / name, raw)
    after = producer_pins(modules)
    if before != after:
        raise AssertionError('selected producer source changed during matched measurement')
    for name, module in modules.items():
        raw, pin = capture(Path(module.__file__), 8 * 1024 * 1024)
        if pin != before[name]:
            raise AssertionError('producer snapshot differs')
        write_new(output / (name + '.py'), raw)
    source_pin = capture(fixture.PUBLIC_FIXTURE, 32768)[1]
    metric = {name: metrics(raw, encoding) for name, raw in values.items()}
    comparisons = {}
    for label, left, right in (
        ('canonical_json', 'expanded-context.json', 'compact-payload.json'),
        ('actual_appendix_including_decoder_and_tables', 'expanded-requirements-appendix.txt', 'compact-selected-appendix.txt'),
        ('full_public_block_including_verbatim_instruction', 'expanded-full-public-block.txt', 'compact-full-public-block.txt'),
        ('model_input_fragment_including_workspace_advisory', 'expanded-model-input-fragment.txt', 'compact-model-input-fragment.txt')):
        l, r = metric[left], metric[right]
        lt, rt = l['LOCAL_o200k_base_tokens'], r['LOCAL_o200k_base_tokens']
        comparisons[label] = {'expanded': l, 'compact': r, 'saved_bytes': l['bytes'] - r['bytes'],
            'saved_byte_fraction': (l['bytes'] - r['bytes']) / l['bytes'],
            'LOCAL_saved_tokens': lt - rt if lt is not None and rt is not None else None,
            'LOCAL_saved_token_fraction': (lt - rt) / lt if lt and rt is not None else None}
    ledger_rows = case['profile']['ledger']['requirements']
    result = {'schema': 'terminal-public-compact-intent-local-measurement@1',
        'scope': 'Offline same-object task requirement appendix serialization using real public instruction and captured public before/bottle.py; fresh local graph/coverage/admission; no provider, hidden verifier, solution or source behavior execution.',
        'status': 'measured', 'source_fixture': source_pin, 'public_code': code_pin,
        'public_code_capture_receipt': capture_receipt_pin, 'public_code_capture_authenticated': False,
        'code_fixture_scope': case['code_fixture_scope'], 'tokenizer': token_receipt,
        'native_context_cid': context['requirements_context_cid'],
        'native_graph_cid': case['planned']['graph'].content_id, 'coverage_cid': context['coverage_cid'],
        'canonical_roundtrip': {'byte_identical': wire(decoded) == expanded_raw,
            'expanded_sha256': sha(expanded_raw), 'decoded_sha256': sha(wire(decoded)),
            'context_cid_preserved': decoded['requirements_context_cid'] == context['requirements_context_cid'],
            'all_original_fields_arrays_and_selectors_preserved': decoded == context,
            'literal_public_instruction_same_in_both_arms': True,
            'native_context_unchanged_by_encoding': wire(context) == expanded_raw},
        'populations': {'ledger_goal_atoms': len(ledger_rows),
            'ledger_required': sum(r['modality'] == 'required' for r in ledger_rows),
            'ledger_permitted': sum(r['modality'] == 'permitted' for r in ledger_rows),
            'selected_requirements': len(context['requirements']),
            'dependency_requirements': len(context['dependency_requirements']),
            'global_prohibitions': len(context['global_prohibitions']), 'operations': len(context['operations']),
            'permissions_in_worker_context': 0,
            'permissions_preserved_in_literal_instruction_and_unchanged_ledger': True},
        'rendering': {'expanded_projection': expanded_projection, 'compact_projection': compact_projection,
            'full_loader_signature_and_source_checks_executed': True,
            'receipts_are_accounting_artifacts_not_model_prompt_blocks': True},
        'comparisons': comparisons, 'artifact_measurements': metric,
        'field_breakdown': {'expanded_context': field_breakdown(context, encoding),
                            'compact_payload': field_breakdown(compact, encoding)},
        'provenance': {'producer_pins_before': before, 'producer_pins_after': after,
            'selected_sources_unchanged': True, 'script': capture(Path(__file__), 2 * 1024 * 1024)[1],
            'python': sys.version, 'subprocesses': len(git_calls),
            'git_subprocesses': sum(Path(row['executable']).name == 'git' for row in git_calls),
            'exact_python_version_probes': sum(row['executable'] == sys.executable for row in git_calls),
            'elapsed_seconds': time.monotonic() - started},
        'claims': {'provider_calls': 0, 'provider_native_cumulative_usage_measured': False,
            'actual_full_coding_prompt_measured': False, 'source_semantic_equivalence_proved': False,
            'behavioral_satisfaction_verified': False, 'whole_program_proved': False,
            'training_steps': 0, 'lean_calls': 0, 'benchmark_reward_measured': False,
            'causal_token_advantage_established': False},
        'limitations': [
            'LOCAL o200k_base representation counts do not establish the configured provider model tokenizer or cumulative input/output/cache usage.',
            'The minimal native task envelope plus actual loader/workspace wrappers is an input fragment, not the full production semantic capsule, retrieval tables, residual advice or provider system/tool messages.',
            'The same real public instruction interpretation is authored and coverage is administrative; unresolved report field count, error types and CWE identities remain unresolved.',
            'The native task context selects seventeen required atoms; two permitted GOAL atoms remain outside its selected population in the original ledger and verbatim instruction.',
            'Byte-exact decoding establishes representation equality only, not natural-language, source-model or runtime semantic equivalence.',
            'A single local paired measurement cannot establish benchmark success or a causal provider token advantage.']}
    write_new(output / 'measurement.json', wire(result))
    write_new(output / 'measurement-script.py', Path(__file__).read_bytes())
    write_new(output / 'command.json', wire({'argv': sys.argv, 'cwd': os.getcwd(),
        'environment': {name: os.environ.get(name) for name in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE',
            'TIKTOKEN_CACHE_DIR', 'IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB', 'IPFS_ACCELERATE_META_INDEX_DUCKDB')}}))
    print(json.dumps({'output': str(output), 'measurement_sha256': sha(wire(result)),
        'populations': result['populations'], 'comparisons': comparisons,
        'tokenizer_status': token_receipt['status'], 'canonical_roundtrip': result['canonical_roundtrip']}, sort_keys=True))


if __name__ == '__main__':
    main()
