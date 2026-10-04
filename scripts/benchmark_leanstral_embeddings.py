#!/usr/bin/env python3
"""Temporarily replace the managed generation service with an isolated encoder.

Stops ipfs-accelerate-leanstral.service, benchmarks native last-pooled vectors,
then restores the original service in finally. Requires authorization to stop
the generation service. GPU offload is retained and explicitly reported.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time
import urllib.request

from benchmark_autoformal_outputs import ROOT, LEXICAL, digest, write

SERVICE = 'ipfs-accelerate-leanstral.service'
UNIT = 'leanstral-throughput-embedding-benchmark.service'
URL = 'http://127.0.0.1:18080'


def command(*args, timeout=180):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def request(path, data=None, timeout=180):
    req = urllib.request.Request(URL + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def wait_ready(url=URL, timeout=900):
    deadline = time.monotonic() + timeout
    last_update = 0
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url + '/health', timeout=2) as response:
                if json.load(response).get('status') == 'ok':
                    return
        except Exception:
            pass
        if time.monotonic() - last_update > 30:
            print(json.dumps({'status': 'waiting_for_server', 'url': url}), flush=True)
            last_update = time.monotonic()
        time.sleep(1)
    raise RuntimeError('server readiness timed out: ' + url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workload', type=Path, default=ROOT / 'artifacts/autoformal-throughput-800x20-20261003/workload.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--batch-size', type=int, default=16)
    args = parser.parse_args()
    assert 1 <= args.batch_size <= 16 and args.repeats > 0
    rows = json.loads(args.workload.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    pid = int(command('systemctl', '--user', 'show', SERVICE, '-p', 'MainPID', '--value').strip())
    if pid <= 0:
        raise RuntimeError('original generation service must be running')
    original = Path(f'/proc/{pid}/cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
    model_path = Path(original[original.index('-m') + 1])
    report = {'schema': 'leanstral-native-embedding-throughput/v1', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'workload_sha256': digest(rows), 'transactions_per_run': len(rows), 'dimension': 4096,
              'pooling': 'last', 'normalization': 'l2', 'input': 'exact raw source, no chat template',
              'original_server_pid': pid, 'original_server_argv': original,
              'original_unit': command('systemctl', '--user', 'cat', SERVICE),
              'cpu_threads': 20, 'gpu_offload': 'CUDA0, requested 36 layers, same offload request as original generation service',
              'model_path': str(model_path), 'model_bytes': model_path.stat().st_size,
              'binary_sha256': hashlib.sha256(Path(original[0]).read_bytes()).hexdigest(),
              'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_lexical_tokens': sum(len(LEXICAL.findall(row['source_text'])) for row in rows),
              'cache_policy': 'erase every slot before each batch; batch size <= slot count, so each request gets an empty slot',
              'timing_scope': 'warm client wall time includes tokenization inside server, full vector inference, HTTP, vector validation and cache erasure; disk writes excluded',
              'runs': [], 'original_service_restored': False}
    write(args.output / 'workload.json', rows)
    write(args.output / 'report.json', report)
    slots_path = args.output.resolve() / 'slots'
    slots_path.mkdir()
    binary = original[0]
    argv = [binary, '-m', str(model_path), '--host', '127.0.0.1', '--port', '18080', '--alias', 'leanstral_local',
            '-c', '8192', '-ngl', '36', '--device', 'CUDA0', '--fit', 'off',
            '--no-warmup', '-b', '512', '-ub', '512', '--parallel', str(args.batch_size),
            '--threads', '20', '--threads-batch', '20', '--embeddings', '--pooling', 'last', '--embd-normalize', '2',
            '--slot-save-path', str(slots_path), '--metrics']
    report['embedding_server_argv'] = argv
    report['status'] = 'starting'
    write(args.output / 'report.json', report)
    stopped = False
    try:
        print(json.dumps({'status': 'stopping_original_generation_service'}), flush=True)
        stopped = True
        command('systemctl', '--user', 'stop', SERVICE)
        command('systemd-run', '--user', '--unit=' + UNIT, '--collect', '--property=Type=exec',
                '--property=CPUAffinity=0-19', '--property=MemoryMax=90G', '--property=MemorySwapMax=0',
                '--setenv=CUDA_VISIBLE_DEVICES=0', *argv)
        startup_started = time.perf_counter()
        wait_ready()
        report['server_load_seconds'] = time.perf_counter() - startup_started
        report['server_props'] = request('/props')
        server_pid = int(command('systemctl', '--user', 'show', UNIT, '-p', 'MainPID', '--value').strip())
        report['server_pid'] = server_pid
        report['server_cpu_affinity'] = sorted(os.sched_getaffinity(server_pid))
        assert report['server_cpu_affinity'] == list(range(20))
        assert report['server_props']['total_slots'] == args.batch_size

        def erase(slot):
            return request(f'/slots/{slot}?action=erase', {})

        with ThreadPoolExecutor(max_workers=args.batch_size) as eraser:
            def infer(batch):
                clear_started = time.perf_counter()
                list(eraser.map(erase, range(args.batch_size)))
                clear_seconds = time.perf_counter() - clear_started
                started = time.perf_counter()
                response = request('/v1/embeddings', {'input': [row['source_text'] for row in batch],
                                                       'model': 'leanstral_local', 'encoding_format': 'float'})
                request_seconds = time.perf_counter() - started
                data = sorted(response['data'], key=lambda row: row['index'])
                assert len(data) == len(batch)
                outputs = []
                for row, item in zip(batch, data, strict=True):
                    vector = item['embedding']
                    assert len(vector) == 4096 and all(math.isfinite(x) for x in vector)
                    assert abs(math.hypot(*vector) - 1) < 1e-4
                    outputs.append({'id': row['id'], 'embedding': vector})
                return outputs, response['usage']['prompt_tokens'], request_seconds, clear_seconds

            # Canary: single/batch agreement and A/B/A replay with empty caches.
            single, _, _, _ = infer(rows[:1])
            batch, _, _, _ = infer(rows[:args.batch_size])
            infer(rows[1:2])
            replay, _, _, _ = infer(rows[:1])
            distance = lambda a, b: math.sqrt(sum((x-y)**2 for x, y in zip(a, b, strict=True)))
            batch_difference = distance(single[0]['embedding'], batch[0]['embedding'])
            replay_difference = distance(single[0]['embedding'], replay[0]['embedding'])
            report['canary'] = {'finite_dimension': 4096, 'single_vs_batch_l2': batch_difference,
                                'single_batch_equivalent_at_1e_3': batch_difference <= 1e-3,
                                'a_b_a_replay_l2': replay_difference, 'tolerance_l2': 1e-3,
                                'evaluation_profile': 'fixed batch-size profile; cross-batch equivalence is diagnostic, repeatability within profile is required'}
            write(args.output / 'canary.json', {'single': single, 'batch': batch, 'replay': replay, 'metrics': report['canary']})
            write(args.output / 'report.json', report)
            print(json.dumps({'status': 'canary', **report['canary']}), flush=True)
            assert replay_difference <= 1e-3
            report['token_receipts'] = [{'id': row['id'], **request('/tokenize', {'content': row['source_text'],
                                         'add_special': True, 'parse_special': True})} for row in rows]
            expected_native = sum(len(row['tokens']) for row in report['token_receipts'])
            for repeat in range(args.repeats):
                print(json.dumps({'status': 'encoding', 'repeat': repeat + 1, 'transactions': len(rows)}), flush=True)
                outputs, batches = [], []
                started = time.perf_counter()
                last_update = started
                for offset in range(0, len(rows), args.batch_size):
                    values, count, seconds, clear_seconds = infer(rows[offset:offset + args.batch_size])
                    outputs.extend(values)
                    batches.append({'offset': offset, 'native_tokens': count, 'request_seconds': seconds, 'clear_seconds': clear_seconds})
                    if time.perf_counter() - last_update > 30:
                        print(json.dumps({'repeat': repeat + 1, 'completed': len(outputs)}), flush=True)
                        last_update = time.perf_counter()
                wall = time.perf_counter() - started
                native = sum(batch['native_tokens'] for batch in batches)
                assert native == expected_native
                write(args.output / f'outputs-{repeat + 1}.json', outputs)
                run = {'repeat': repeat + 1, 'wall_seconds': wall, 'transactions_per_second': len(rows) / wall,
                       'source_lexical_tokens_per_second': report['source_lexical_tokens'] / wall,
                       'native_input_tokens': native, 'native_input_tokens_per_second': native / wall,
                       'embedding_request_seconds': sum(batch['request_seconds'] for batch in batches),
                       'cache_erase_seconds': sum(batch['clear_seconds'] for batch in batches),
                       'outputs_sha256': digest(outputs), 'batches': batches}
                report['runs'].append(run)
                write(args.output / 'report.json', report)
                print(json.dumps({key: value for key, value in run.items() if key != 'batches'}), flush=True)
        report['status'] = 'completed'
        report['medians'] = {key: statistics.median(run[key] for run in report['runs'])
                             for key in ['wall_seconds', 'transactions_per_second', 'source_lexical_tokens_per_second',
                                         'native_input_tokens_per_second', 'embedding_request_seconds', 'cache_erase_seconds']}
    except BaseException as error:
        report['status'] = 'failed'
        report['reason'] = type(error).__name__ + ': ' + str(error)
        write(args.output / 'report.json', report)
        print(json.dumps({'status': 'failed', 'reason': report['reason']}), flush=True)
        raise
    finally:
        try:
            command('systemctl', '--user', 'stop', UNIT)
        except Exception as error:
            # An already-failed --collect unit can disappear before cleanup.
            report['embedding_unit_stop_error'] = str(error)
        try:
            logs = command('journalctl', '--user', '-u', UNIT, '--no-pager', '-o', 'cat')
            (args.output / 'embedding-server.log').write_text(logs)
        except Exception as error:
            report['log_collection_error'] = str(error)
        try:
            if stopped:
                print(json.dumps({'status': 'restoring_original_generation_service'}), flush=True)
                command('systemctl', '--user', 'start', SERVICE, timeout=1200)
                wait_ready('http://172.17.0.1:8080')
                report['original_service_restored'] = True
                report['restored_server_pid'] = int(command('systemctl', '--user', 'show', SERVICE, '-p', 'MainPID', '--value').strip())
        except BaseException as error:
            report['restoration_error'] = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            write(args.output / 'report.json', report)


if __name__ == '__main__':
    main()
