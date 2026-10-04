from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

ROOT = Path('/home/barberb/lift_coding/maintenance/terminal-ir-publication-20261004-01/datasets')
OUT = ROOT / 'focused-validation-02'

def main():
    request = json.loads((OUT / 'invocation.json').read_text())
    env = dict(os.environ)
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    env['PYTHONPATH'] = str(ROOT / 'checkout')
    started = time.monotonic()
    receipt = {'schema': 'datasets-publication-focused-test-outer@1', 'status': 'running', 'returncode': None, 'exception': None, 'child_started': False, 'cleanup_errors': [], 'scope': request['scope'], 'environment_policy': {'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONPATH': str(ROOT / 'checkout')}, 'timeout_seconds': 240}
    child = None
    error = None
    try:
        with (OUT / 'stdout.log').open('xb') as stdout, (OUT / 'stderr.log').open('xb') as stderr:
            child = subprocess.Popen(request['argv'], cwd=ROOT / 'checkout', env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            receipt['child_started'] = True
            receipt['returncode'] = child.wait(timeout=240)
            receipt['status'] = 'passed' if receipt['returncode'] == 0 else 'failed'
    except BaseException as exc:
        error = exc
        receipt['status'] = 'failed'
        receipt['exception'] = {'type': type(exc).__name__, 'message': str(exc)}
        if child is not None and child.poll() is None:
            for action in [child.terminate, lambda: child.wait(timeout=5), child.kill, lambda: child.wait(timeout=5)]:
                if child.poll() is not None:
                    break
                try:
                    action()
                except BaseException as cleanup:
                    receipt['cleanup_errors'].append({'type': type(cleanup).__name__, 'message': str(cleanup)})
    finally:
        receipt['actual_outer_elapsed_seconds'] = time.monotonic() - started
        receipt['after_source_pins'] = []
        for original in request['before_source_pins']:
            try:
                raw = (ROOT / 'checkout' / original['path']).read_bytes()
                pin = dict(path=original['path'], bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                pin['unchanged'] = pin['bytes'] == original['bytes'] and pin['sha256'] == original['sha256']
                receipt['after_source_pins'].append(pin)
            except BaseException as cleanup:
                receipt['cleanup_errors'].append({'path': original['path'], 'type': type(cleanup).__name__, 'message': str(cleanup)})
        receipt['logs'] = []
        for name in ['stdout.log', 'stderr.log', 'junit.xml']:
            try:
                raw = (OUT / name).read_bytes()
                receipt['logs'].append({'path': str(OUT / name), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
            except FileNotFoundError:
                receipt['logs'].append({'path': str(OUT / name), 'absent': True})
        (OUT / 'closed-attempt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: receipt[k] for k in ['status', 'returncode', 'actual_outer_elapsed_seconds', 'cleanup_errors']}))
    if error:
        raise error
    if receipt['returncode']:
        raise SystemExit(receipt['returncode'])

if __name__ == '__main__':
    main()
