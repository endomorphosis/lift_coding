#!/usr/bin/env python3
"""Authored process-boundary fault probes; never runs npm or a provider."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
DEPLOYMENT = SOURCE / 'benchmarks/agent_supervisor/container_coding/terminal_deployment.py'
START_HASH = hashlib.sha256(DEPLOYMENT.read_bytes()).hexdigest()


def alive(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z'
    except FileNotFoundError:
        return False


rows = []
with tempfile.TemporaryDirectory(prefix='independent-installer-boundary-') as temporary:
    for case in ('popen_return_interruption', 'repeated_cleanup_signals', 'cleanup_observation_error', 'deadline'):
        folder = Path(temporary) / case
        folder.mkdir()
        owned_root = folder / 'runtime'
        (owned_root / 'home').mkdir(parents=True)
        marker = folder / 'pids.json'
        node, npm = folder / 'node', folder / 'npm'
        node.write_text('#!' + sys.executable + '\nprint("v20.11.0")\n')
        node.chmod(0o755)
        npm.write_text('#!' + sys.executable + '\n' + f'''
import json,os,pathlib,signal,sys,time
if '--version' in sys.argv:
 print('10.2.0')
 raise SystemExit(0)
signal.signal(signal.SIGTERM,signal.SIG_IGN)
signal.signal(signal.SIGINT,signal.SIG_IGN)
child=os.fork()
if child==0:
 while True:time.sleep(1)
pathlib.Path({str(marker)!r}).write_text(json.dumps([os.getpid(),child]))
while True:time.sleep(1)
''')
        npm.chmod(0o755)
        runner = folder / 'runner.py'
        runner.write_text(f'''
import hashlib,json,os,pathlib,shutil,signal,subprocess,time
from benchmarks.agent_supervisor.container_coding import terminal_deployment as deployment
case={case!r}
marker=pathlib.Path({str(marker)!r})
node={str(node)!r}
npm={str(npm)!r}
real_which=shutil.which
real_popen=subprocess.Popen
real_killpg=os.killpg
real_waitid=os.waitid
target=[None]
observation_fault=[False]
def which(name,path=None):
 return {{'node':node,'npm':npm}}.get(name) or real_which(name,path=path)
def popen(command,*args,**kwargs):
 process=real_popen(command,*args,**kwargs)
 if command[0]==npm and 'install' in command:
  target[0]=process.pid
  end=time.monotonic()+2
  while not marker.exists() and time.monotonic()<end:time.sleep(.005)
  if not marker.exists():raise RuntimeError('authored fixture did not start')
  if case=='popen_return_interruption':os.kill(os.getpid(),signal.SIGTERM)
 return process
def killpg(group,number):
 result=real_killpg(group,number)
 if group==target[0] and number==signal.SIGTERM:
  if case=='repeated_cleanup_signals':
   os.kill(os.getpid(),signal.SIGTERM)
   os.kill(os.getpid(),signal.SIGINT)
   os.kill(os.getpid(),signal.SIGTERM)
  if case=='cleanup_observation_error':observation_fault[0]=True
 return result
def waitid(*args):
 if observation_fault[0]:
  observation_fault[0]=False
  raise PermissionError('authored cleanup observation fault')
 return real_waitid(*args)
shutil.which=which
subprocess.Popen=popen
os.killpg=killpg
os.waitid=waitid
deployment.CODEX_INSTALL_TIMEOUT_SEC=.35
script=deployment.native_codex_install_script({str(owned_root)!r})
pathlib.Path({str(folder / 'generated-script.sha256')!r}).write_text(hashlib.sha256(script.encode()).hexdigest())
exec(compile(script,'<authored-installer-probe>','exec'),{{'__name__':'__main__'}})
''')
        environment = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(folder),
                       'PYTHONPATH': str(SOURCE) + ':/home/barberb/lift_coding_worktrees/indexed-worker-context-datasets-20261011',
                       'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
        start = time.monotonic()
        result = subprocess.run([sys.executable, str(runner)], env=environment,
                                capture_output=True, timeout=8)
        elapsed = time.monotonic() - start
        report = json.loads(result.stdout)
        pids = json.loads(marker.read_bytes())
        until = time.monotonic() + 2
        while any(alive(pid) for pid in pids) and time.monotonic() < until:
            time.sleep(.01)
        escaped = [pid for pid in pids if alive(pid)]
        rescue_required = bool(escaped)
        if rescue_required:
            try:
                os.killpg(pids[0], signal.SIGKILL)
            except ProcessLookupError:
                pass
        expected_reason = {'popen_return_interruption': 'interrupted',
                           'repeated_cleanup_signals': 'timeout',
                           'cleanup_observation_error': 'installer_error', 'deadline': 'timeout'}[case]
        rows.append({'case': case, 'passed': result.returncode == 1 and report['completed'] is False
                     and report['reason'] == expected_reason and not rescue_required
                     and report['phase'] == 'npm-install' and elapsed < 5,
                     'installer_completed': report['completed'], 'reported_reason': report['reason'],
                     'elapsed_seconds': elapsed, 'authored_processes_alive_after_return': len(escaped),
                     'reviewer_rescue_required': rescue_required,
                     'generated_script_sha256': (folder / 'generated-script.sha256').read_text(),
                     'report_did_not_include_child_output': set(report) <= {
                         'schema', 'completed', 'phase', 'reason', 'commands_completed', 'deadline_seconds', 'provider_calls'}})

report = {'schema': 'independent-native-installer-process-probes@1',
          'source_file_sha256_before': START_HASH,
          'source_file_sha256_after': hashlib.sha256(DEPLOYMENT.read_bytes()).hexdigest(),
          'probe_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'all_checks_passed': all(row['passed'] and row['report_did_not_include_child_output'] for row in rows),
          'cases': rows, 'provider_calls': 0, 'npm_or_network_calls': 0,
          'raw_logs_or_auth_read': False, 'scope': 'Authored child processes exercising cleanup boundaries; not live package installation.'}
(ROOT / 'independent-installer-process-probes.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({'all_checks_passed': report['all_checks_passed'], 'cases': rows}))
raise SystemExit(0 if report['all_checks_passed'] else 1)
