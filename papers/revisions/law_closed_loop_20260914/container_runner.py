"""Development generated-code transport using original LA029 containment helpers.

The watchdog, measured cgroup checks and exact-owned cleanup are retained.
The original pinned image is reused with a new development child entry point.
Nothing is claimed as the old LA029 scientific execution.
"""
from pathlib import Path
import os,json,re,subprocess,time
from common import digest,sha,write as write_fresh,verify_runtime,load_module
HERE=Path(__file__).resolve().parent
original=load_module('la029_containment_original',HERE/'vendor/la029_controller.py')
for _name in ['require','write','command','inspect','owned','configured','cgroup_for_pid','sample','verify_sample','parent_name','parent_sample','parent_empty','Watchdog','DOCKER']:
 globals()[_name]=getattr(original,_name)

def create_argv(admission,authority,index,mounts,name,worker):
 argv=DOCKER+['create','--name',name,'--label','la029.admission='+authority,
  '--cgroup-parent',parent_name(authority,index),'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
  '--cpus','1','--cpuset-cpus',str(admission['cpu']),'--memory','2147483648','--memory-swap','2147483648','--pids-limit','16','--ulimit','core=0',
  '--user',str(os.getuid())+':'+str(os.getgid()),'--workdir','/source','--tmpfs','/tmp:rw,nosuid,nodev,size=67108864,mode=1777']
 for source,destination,writable in mounts:argv+=['--mount','type=bind,src='+str(source)+',dst='+destination+('' if writable else ',readonly')]
 env={**original.ENVIRONMENT,'PYTHONPATH':'/workflow:/runtime/python:/source/external/ipfs_accelerate:/source/external/ipfs_datasets:/source/external/ipfs_kit'}
 for key,value in env.items():argv+=['--env',key+'='+value]
 return argv+['--entrypoint',admission['python'],admission['image'],'-B','/workflow/native_candidate.py','--request','/request.json','--profile','/runtime.json','--source-root','/source','--output','/output','--shared','/shared']

def run_cell(admission, request, candidate_path, directory, shared):
    authority = digest({"profile": admission, "request": request, "directory": str(directory)})
    index = 0
    original.IMAGE = admission["image"]
    started = time.monotonic(); worker = directory / 'worker'; worker.mkdir(mode=0o700)
    host = directory / 'host'; host.mkdir(mode=0o700)
    source = Path(admission["source_root"])
    verify_runtime(admission, source)
    runtime = Path(admission['runtime_root'])
    request_path = directory / 'request.json'; write(request_path, request)
    profile_path = directory / 'runtime.json'; write(profile_path, admission)
    mounts = [(source, '/source', False), (runtime, '/runtime', False),
              (HERE, '/workflow', False), (candidate_path, '/candidate.py', False),
              (request_path, '/request.json', False), (profile_path, '/runtime.json', False),
              (shared, '/shared', True), (worker, '/output', True)]
    name = 'la-generated-dev-' + authority[:16] + '-' + f'{index:04d}'
    parent = Path('/sys/fs/cgroup') / parent_name(authority, index)
    require(not parent.exists(), 'Exact fresh private cgroup parent required')
    ref = {}; watcher = Watchdog(started, admission['cpu'], ref, host, parent); created_attempted = False
    report = {'schema': 'la029-operator-cell-envelope/v1', 'index': index, 'admission_sha256': authority,
              'started_monotonic': started, 'pending': None, 'admitted': False,
              'cpu_allowance_seconds': 20, 'private_parent_cgroup': str(parent), 'parent_preexisting': False, 'termination_proven': False,
              'cleanup_proven': False, 'scientific_retry': False}
    try:
        require(inspect(name) is None, 'Exact container name already exists')
        write(host / 'consumed.json', {'index': index, 'admission_sha256': authority, 'effect_outcome': 'unknown_before_create'})
        watcher.thread.start()
        created_attempted = True; report['pending'] = 'container_create'
        result = command(create_argv(admission, authority, index, mounts, name, worker), timeout=max(.001, 20 - (time.monotonic() - started)))
        (host / 'create.stdout').write_bytes(result.stdout)
        (host / 'create.stderr').write_bytes(result.stderr)
        require(result.returncode == 0 and re.fullmatch(b'[0-9a-f]{64}\n?', result.stdout), 'Docker create not acknowledged')
        cid = result.stdout.decode().strip(); data = inspect(cid); require(data is not None, 'Created container disappeared')
        require(owned(data, name, authority, mounts) == cid, 'Created CID differs'); ref['cid'] = cid
        configured(data, admission['cpu'], parent.name); write(host / 'created.json', data)
        require(watcher.error is None and time.monotonic() - started < 20, 'Prestart wall budget exhausted')
        report.update(pending='running', container_id=cid)
        with (host / 'stdout.txt').open('xb') as out, (host / 'stderr.txt').open('xb') as err:
            process = subprocess.Popen(DOCKER + ['start', '--attach', cid], stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, env={'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent'})
            while process.poll() is None:
                if watcher.root is None:
                    current = inspect(cid)
                    if current and current['State']['Pid']:
                        watcher.root = cgroup_for_pid(current['State']['Pid'])
                        require(watcher.root.parent == parent, 'Running child outside exact private parent')
                if watcher.error is not None:
                    try: process.wait(timeout=6)
                    except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=2)
                    break
                time.sleep(.02)
            report['attach_returncode'] = process.returncode
        terminal = inspect(cid); require(terminal is not None, 'Terminal container unavailable')
        owned(terminal, name, authority, mounts); write(host / 'terminal.json', terminal)
        final = parent_sample(parent); write(host / 'parent_after_exit.json', final)
        require(watcher.parent_inode in (None, final['inode']), 'Terminal parent identity changed')
        report['termination_proven'] = terminal['State']['Running'] is False and terminal['State']['Pid'] == 0 and parent_empty(final)
        report.update(measured_group_cpu_seconds=final['cpu_usage_seconds'], measured_group_user_cpu_seconds=final['cpu_user_seconds'],
                      measured_group_system_cpu_seconds=final['cpu_system_seconds'], measured_group_peak_memory_bytes=int(final['memory.peak']))
        report['wall_seconds_to_group_exit_observation'] = time.monotonic() - started
        report['process_exit_code'] = terminal['State']['ExitCode']; report['oom_killed'] = terminal['State']['OOMKilled']
        require(report['termination_proven'], 'Whole group termination unproven')
        watcher.finish()
        write(host / 'resources.json', {'leaf_samples': watcher.samples, 'parent_samples': watcher.parent_samples, 'decision': watcher.error,
              'kill_result': watcher.kill_result, 'samples_are_cumulative_not_additive': True,
              'final_descendant_counter_retained': True, 'final_parent': final})
        require(watcher.error is None and not report['oom_killed'] and report['process_exit_code'] == 0
                and report['attach_returncode'] == 0 and report['wall_seconds_to_group_exit_observation'] <= 20
                and final['cpu_usage_seconds'] <= 20 and int(final['memory.peak']) <= 2147483648,
                'Cell failed or exceeded its fixed resource boundary')
        kernel = json.loads((worker / 'child_boundary.json').read_bytes()); verify_sample(kernel, admission['cpu'])
        require(not any(int(v) for k, v in (line.split() for line in final['memory.events'].splitlines()) if k in ('oom', 'oom_kill', 'max')), 'Final memory limit event')
        require(not any(int(v) for k,v in (line.split() for line in final['pids.events'].splitlines()) if k=='max'), 'Final process limit event')
        body = json.loads((worker / 'result.json').read_bytes())
        require(body['schema'] == 'la-generated-candidate-result/v1' and body['attempt_id'] == request['attempt_id']
                and body['candidate_sha256'] == request['candidate_sha256'] and body['task_sha256'] == digest(request['task']),
                'Actual byte-bound candidate result missing')
        report.update(result_sha256=sha(worker / 'result.json'), cell_result=body,
                      observed_effects_are_not_model_self_report=True, pending=None)
    except BaseException as exc:
        report.update(error_type=type(exc).__name__, error=str(exc), requires_reconciliation=created_attempted)
    finally:
        if watcher.thread.is_alive():
            try: watcher.finish()
            except BaseException as exc:
                report.update(watchdog_shutdown_error=type(exc).__name__, error_type=type(exc).__name__)
        # A watcher shutdown failure must not skip exact-owned cleanup or
        # retained final counters. No name is removed before our create attempt.
        # Preexisting names are never cleaned. An ambiguous create is cleaned
        # only after exact label/image/mount identity is independently observed.
        if created_attempted:
            try:
                data = inspect(ref.get('cid', name))
                if data is not None:
                    cid = owned(data, name, authority, mounts)
                    cleanup = command(DOCKER + ['rm', '-f', cid], timeout=6)
                    report['cleanup_returncode'] = cleanup.returncode
                    report['cleanup_proven'] = cleanup.returncode == 0 and inspect(cid) is None
                else:
                    report['cleanup_proven'] = bool(ref.get('cid'))
                    if not ref.get('cid'): report['pending'] = 'uncertain_create_manual_reconciliation'
            except BaseException as exc:
                report['cleanup_error_type'] = type(exc).__name__
        if parent.exists():
            try:
                retained = parent_sample(parent); write(host / 'parent_after_cleanup.json', retained)
                require(parent_empty(retained) and watcher.parent_inode in (None, retained['inode']), 'Final parent not empty/stable')
                report.update(final_parent_empty=True, measured_group_cpu_seconds=retained['cpu_usage_seconds'],
                              measured_group_user_cpu_seconds=retained['cpu_user_seconds'], measured_group_system_cpu_seconds=retained['cpu_system_seconds'],
                              measured_group_peak_memory_bytes=int(retained['memory.peak']), empty_parent_retained=True)
                require(retained['cpu_usage_seconds'] <= 20, 'Final CPU overshoot')
            except BaseException as exc:
                report.update(parent_accounting_error=type(exc).__name__, error_type=type(exc).__name__)
        elif created_attempted:
            report.update(parent_accounting_unknown=True, error_type=report.get('error_type', 'MissingFinalParent'))
        report['admitted'] = ('cell_result' in report and report['termination_proven'] and report['cleanup_proven']
                              and report.get('error_type') is None and watcher.error is None and report.get('final_parent_empty') is True)
        report['elapsed_seconds_including_cleanup'] = time.monotonic() - started
        report['watchdog_kill_result'] = watcher.kill_result
        report['cost_scope'] = 'Measured final descendant-inclusive CPU/user/system and memory peak from a fresh private parent retained empty after exact child cleanup. CPU samples are cumulative, never added. Host orchestration/cleanup wall is separately reported; unknown counters stop the run.'
        write(host / 'result.json', report)
    return report
