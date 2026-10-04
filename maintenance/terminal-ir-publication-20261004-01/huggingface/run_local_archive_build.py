"""Durable local-only archive invocation; no Hugging Face or source writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def pin(path):
    before = path.stat(); digest = hashlib.sha256(); size = 0
    with path.open('rb') as stream:
        while block := stream.read(8 * 1024**2): digest.update(block); size += len(block)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('wrapper input changed')
    return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush(); os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--builder', type=Path, required=True)
    parser.add_argument('--scopes', type=Path, required=True)
    parser.add_argument('--expected-builder-sha256', required=True)
    parser.add_argument('--expected-scopes-sha256', required=True)
    parser.add_argument('--archive-output', type=Path, required=True)
    parser.add_argument('--receipt-output', type=Path, required=True)
    parser.add_argument('--wall-seconds', type=float, default=7200)
    args = parser.parse_args(); start = time.monotonic()
    output = args.receipt_output.resolve(); output.mkdir(parents=True, exist_ok=False)
    state = {'schema': 'terminal-ir-local-archive-outer-attempt@1', 'started_wall_time': time.time(),
             'status': 'started', 'returncode': None, 'primary_error_type': None,
             'enclosing_invocation_before_wrapper_main_elapsed_seconds': None,
             'remote_mutations': 0, 'complete_descendant_cleanup_qualified': False}
    child = None; bindings = None
    argv = [sys.executable, '-u', str(args.builder), '--scopes', str(args.scopes),
            '--output', str(args.archive_output), '--expected-script-sha256', args.expected_builder_sha256,
            '--expected-scopes-sha256', args.expected_scopes_sha256, '--wall-seconds', str(args.wall_seconds),
            '--zstd', '/usr/bin/zstd', '--zstd-library', '/usr/lib/aarch64-linux-gnu/libzstd.so.1.5.5']
    save(output / 'invocation.json', {'argv': argv, 'wrapper': pin(Path(__file__).resolve()),
        'expected_builder_sha256': args.expected_builder_sha256, 'expected_scopes_sha256': args.expected_scopes_sha256})
    save(output / 'started.json', state)
    try:
        bindings = {'builder': pin(args.builder), 'scopes': pin(args.scopes)}
        if bindings['builder']['sha256'] != args.expected_builder_sha256 or bindings['scopes']['sha256'] != args.expected_scopes_sha256:
            raise ValueError('wrapper expected input pin mismatch')
        save(output / 'inputs-before.json', bindings)
        with (output / 'stdout.log').open('xb') as stdout, (output / 'stderr.log').open('xb') as stderr:
            child = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
            state['child_pid'] = child.pid
            state['returncode'] = child.wait(timeout=args.wall_seconds + 60)
        state['status'] = 'closed_local_preparation' if state['returncode'] == 0 else 'failed_local_preparation_preserved'
    except BaseException as error:
        state['primary_error_type'] = type(error).__name__; state['status'] = 'failed_outer_preserved'
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM); child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL); child.wait()
            except ProcessLookupError:
                child.wait()
            state['returncode'] = child.returncode
        raise
    finally:
        state['elapsed_seconds'] = time.monotonic() - start
        if bindings is not None:
            try:
                after = {'builder': pin(args.builder), 'scopes': pin(args.scopes)}
                save(output / 'inputs-after.json', after)
                state['input_pins_unchanged'] = after == bindings
            except BaseException as error:
                state['final_input_check_error_type'] = type(error).__name__
        save(output / 'closed.json', state)
    return state['returncode']


if __name__ == '__main__':
    raise SystemExit(main())
