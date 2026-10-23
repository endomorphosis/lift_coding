#!/usr/bin/env python3
"""Host client: 8-probe interface qualification then the 900-cell generated-code study.

The ephemeral runner must already have a warm Leanstral on loopback. This process
does not start or install a service. One transport job owns all model calls.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TRANSPORT = HERE.parent / 'law_model_transport_20260914'
QUAL = HERE.parent / 'law_model_qualification_20260914'
WALL = 36000
STARTUP = 360
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(TRANSPORT))
import freeze
import execute
import transport
from client import exchange, close_job


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(canonical(value) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def emit(path, value):
    print(canonical(value), flush=True)
    with path.open('a') as stream:
        stream.write(canonical(value) + '\n')


def listener_pid(port=8080):
    address = '0100007F:' + format(port, '04X')
    inodes = {line.split()[9] for line in Path('/proc/net/tcp').read_text().splitlines()[1:]
              if line.split()[1] == address and line.split()[3] == '0A'}
    if not inodes:
        raise RuntimeError('No loopback listener on port %s' % port)
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            for item in (proc / 'fd').iterdir():
                try:
                    if os.readlink(item) in {'socket:[' + inode + ']' for inode in inodes}:
                        return int(proc.name)
                except FileNotFoundError:
                    continue
        except (FileNotFoundError, PermissionError):
            continue
    raise RuntimeError('Could not identify the process that owns port %s' % port)


def owner_record(report_path):
    pid = listener_pid(8080)
    identity = transport.identity(pid)
    profile = json.loads((QUAL / 'static_model_profile.json').read_text())
    model_identity = profile['model_identity']
    started = time.monotonic()
    report = {
        'schema': 'law-warm-model-owner-qualification/v1',
        'status': 'PASS',
        'model_identity': model_identity,
        'wall_seconds': WALL,
        'startup_seconds': STARTUP,
        'cleanup_qualified': True,
        'cleanup_evidence': 'scripts/run_leanstral_ephemeral.py plus tests/test_leanstral_ephemeral.py',
        'keep_warm_across_active_calls': True,
        'port': 8080,
        'process': identity,
        'created_monotonic': started,
    }
    save(report_path, report)
    return {
        'host': '127.0.0.1', 'port': 8080, 'scope': 'real_model', 'model': 'leanstral_local',
        'model_identity': model_identity, 'wall_seconds': WALL, 'startup_seconds': STARTUP,
        'started_monotonic': started, 'deadline_monotonic': started + WALL,
        'process': identity,
        'qualification': {'path': str(report_path), 'sha256': sha(report_path)},
    }


def messages_for(task, arm, history):
    messages = [{'role': 'system', 'content': freeze.SYSTEM},
                {'role': 'user', 'content': task['instruction'] + '\nPayload JSON: ' + canonical(task['payload'])}]
    if arm != 'A0':
        messages.append({'role': 'user', 'content': 'Task policy: ' + canonical(task['policy'])})
    if arm in ('A2', 'A3', 'A4'):
        messages.append({'role': 'user', 'content': 'Retrieved public source context: ' + canonical(task['retrieval'])})
    for old in history:
        messages.append({'role': 'assistant', 'content': old['response_text']})
        messages.append({'role': 'user', 'content': 'Observed execution feedback: ' + canonical(old['feedback']) +
                             ' Return a complete short run(payload). payload is a dict, not a JSON string. No imports.'})
    return messages


def completed_keys(path):
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text().splitlines():
        row = json.loads(line)
        keys.add((row['case_id'], row['arm'], row['seed']))
    return keys


def run_cell(job, task, row, output, log):
    stem = 'cell-%04d-%s-%s-%s' % (row['index'], row['case_id'].replace(':', '_')[-40:], row['arm'], row['seed'])
    cell = output / stem
    if (cell / 'result.json').exists():
        result = json.loads((cell / 'result.json').read_text())
        emit(log, result)
        return result
    suffix = 0
    while cell.exists():
        suffix += 1
        cell = output / ('%s-r%s' % (stem, suffix))
    cell.mkdir(parents=True)
    save(cell / 'identity.json', row)
    started = time.monotonic()
    history, records = [], []
    terminal = 'budget_exhausted'
    for iteration in range(2):
        remaining = 90 - (time.monotonic() - started)
        if remaining < 20:
            terminal = 'budget_exhausted_before_full_execution_allowance'
            break
        folder = cell / ('iteration-%02d' % iteration)
        folder.mkdir()
        body = {'model': 'leanstral_local', 'messages': messages_for(task, row['arm'], history),
                'temperature': 0, 'seed': row['seed'], 'max_tokens': 512, 'stream': False}
        save(folder / 'messages.json', body['messages'])
        record = {'iteration': iteration, 'model_calls': 0, 'status': 'started'}
        try:
            response, receipt = exchange(job, body, folder / 'transport',
                                         budget_seconds=min(60, remaining - 15),
                                         request_id=hashlib.sha256(('la900/' + str(row['index']) + '/' + str(iteration) + '/' + str(time.time_ns())).encode()).hexdigest()[:32])
            record['model_calls'] = 1
            record['transport_ok'] = bool(response and response.get('ok'))
            record['prompt_tokens'] = receipt.get('prompt_tokens')
            record['completion_tokens'] = receipt.get('completion_tokens')
            if not response or not response.get('ok'):
                raise RuntimeError(receipt.get('error') or 'transport_failed')
            generation = json.loads((folder / 'transport/response.bin').read_bytes())
            text = generation['choices'][0]['message']['content']
            (folder / 'assistant.txt').write_text(text)
            source = execute.extract_program(text)
            executed = execute.execute_candidate(source, task, row['arm'], folder / 'execution')
            record.update(status='executed', useful_work=executed['useful_work'],
                          forbidden_effect=executed['forbidden_effect'],
                          execution_error=executed['execution_error'])
            history.append({'response_text': text, 'feedback': {
                'useful_work': executed['useful_work'], 'forbidden_effect': executed['forbidden_effect'],
                'execution_error': executed['execution_error']}})
            records.append(record)
            save(folder / 'iteration_result.json', record)
            if executed['useful_work']:
                terminal = 'useful_work'
                break
            terminal = 'candidate_failed'
        except Exception as exc:
            record.update(status='transport_or_format_failure', error=type(exc).__name__ + ': ' + str(exc))
            records.append(record)
            save(folder / 'iteration_result.json', record)
            terminal = record['status']
            break
    result = {
        'schema': 'la-generated-code-cell/v1', 'index': row['index'], 'case_id': row['case_id'],
        'source_family': row['source_family'], 'split': row['split'], 'population': task['population'],
        'pair_role': task.get('pair_role'), 'arm': row['arm'], 'seed': row['seed'],
        'terminal': terminal, 'iterations': records, 'model_calls': sum(item.get('model_calls') or 0 for item in records),
        'useful_work': any(item.get('useful_work') is True for item in records),
        'forbidden_effect': any(item.get('forbidden_effect') is True for item in records),
        'wall_seconds': time.monotonic() - started,
        'known_prompt_tokens': sum(item.get('prompt_tokens') or 0 for item in records),
        'known_completion_tokens': sum(item.get('completion_tokens') or 0 for item in records),
    }
    save(cell / 'result.json', result)
    emit(log, result)
    return result


def bucket():
    return {'n': 0, 'useful': 0, 'forbidden': 0, 'format_fail': 0}


def summarize(study, results):
    by_arm = {arm: bucket() for arm in freeze.ARMS}
    by_arm_split = {arm: {split: bucket() for split in ('development', 'calibration', 'final')} for arm in freeze.ARMS}
    for row in results:
        for stats in (by_arm[row['arm']], by_arm_split[row['arm']][row['split']]):
            stats['n'] += 1
            stats['useful'] += int(bool(row.get('useful_work')))
            stats['forbidden'] += int(bool(row.get('forbidden_effect')))
            stats['format_fail'] += int(row.get('terminal') == 'transport_or_format_failure')
    return {
        'schema': 'la-generated-code-study-summary/v1',
        'planned_cells': 900,
        'recorded_cells': len(results),
        'unique_identities': len({(row['case_id'], row['arm'], row['seed']) for row in results}),
        'model_calls': sum(row.get('model_calls') or 0 for row in results),
        'prompt_tokens': sum(row.get('known_prompt_tokens') or 0 for row in results),
        'completion_tokens': sum(row.get('known_completion_tokens') or 0 for row in results),
        'arms': by_arm,
        'arms_by_split': by_arm_split,
        'final_cells': sum(1 for row in results if row.get('split') == 'final'),
        'complete': len(results) == 900,
        'interface_probes_planned': 8,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true',
                        help='Reuse the live job socket and skip probes; do not reload the model')
    args = parser.parse_args()
    output = HERE
    log = output / 'results.jsonl'
    study_path = output / 'prospective_study.json'
    if not study_path.exists():
        freeze.main()
    study = json.loads(study_path.read_text())
    tasks = {case['id']: case for case in study['cases']}
    job_root = Path('/tmp/la-job')
    gateway = None
    if args.resume:
        client_dir = job_root / 'client'
        if not (client_dir / 'socket').exists():
            raise RuntimeError('Resume requires a live transport socket')
        print(canonical({'event': 'resume_existing_job', 'job': str(job_root),
                         'completed': len(completed_keys(log))}), flush=True)
        try:
            return finish_cells(study, tasks, client_dir, output, log)
        finally:
            pass
    report_path = output / 'owner_qualification.json'
    if report_path.exists():
        report_path.unlink()
    owner = owner_record(report_path)
    if job_root.exists():
        raise RuntimeError('Refusing to reuse /tmp/la-job; remove it only after inspecting retained receipts')
    transport.prepare(job_root, owner, max_requests=8192, max_tokens=1024)
    gateway = subprocess.Popen([sys.executable, '-B', str(TRANSPORT / 'transport.py'), 'serve', '--job', str(job_root)],
                               start_new_session=True)
    try:
        deadline = time.monotonic() + 10
        while not (job_root / 'started.json').exists():
            if gateway.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError('Transport gateway failed to start')
            time.sleep(0.05)
        client_dir = job_root / 'client'
        probe_out = output / 'interface_qualification'
        if not (probe_out / 'qualification_results.json').exists():
            probe = subprocess.run([sys.executable, '-B', str(QUAL / 'qualification_worker.py'),
                                    '--job', str(client_dir), '--output', str(probe_out),
                                    '--transport-client', str(TRANSPORT / 'client.py'),
                                    '--workload-seconds', '600'], cwd=str(ROOT))
            print(canonical({'event': 'interface_qualification_exit', 'code': probe.returncode}), flush=True)
            if probe.returncode != 0:
                raise RuntimeError('Eight-probe interface qualification failed; see ' + str(probe_out))
        return finish_cells(study, tasks, client_dir, output, log)
    finally:
        if gateway is not None and gateway.poll() is None:
            gateway.send_signal(signal.SIGTERM)
            try:
                gateway.wait(timeout=8)
            except subprocess.TimeoutExpired:
                gateway.kill()
                gateway.wait()


def finish_cells(study, tasks, client_dir, output, log):
    done = completed_keys(log)
    for row in study['schedule']:
        key = (row['case_id'], row['arm'], row['seed'])
        if key in done:
            continue
        run_cell(client_dir, tasks[row['case_id']], row, output / 'cells', log)
        done.add(key)
    results = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    summary = summarize(study, results)
    summary_path = output / 'summary.json'
    if summary_path.exists():
        summary_path.unlink()
    save(summary_path, summary)
    print(canonical({'event': 'study_summary', **{k: summary[k] for k in ('recorded_cells', 'model_calls', 'complete', 'arms')}}), flush=True)
    try:
        close_job(client_dir)
    except Exception as exc:
        print(canonical({'event': 'close_job_error', 'error': type(exc).__name__ + ': ' + str(exc)}), flush=True)
    return 0 if summary['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
