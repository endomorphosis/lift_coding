"""Exercise both actual driver CLIs in one actual Harbor SDK environment.

Reads only explicit public task metadata and named fresh phase reports. The
original public Docker recipe is built locally for ARM64; its published image
digest is not claimed. No Trial, task hasher, solution or verifier is used.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import importlib
import json
from pathlib import Path
import shlex
import time
import tomllib

STAGE = Path(__file__).resolve().parent
ROOT = '/opt/ipfs-supervisor'
PYTHON = ROOT + '/venv/bin/python'
TASK = Path('/home/barberb/lift_coding/.benchmarks/terminal-bench-2/fix-code-vulnerability')

def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

async def shell(argv):
    proc = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), 60)
    except BaseException:
        if proc.returncode is None:
            proc.kill()
        await proc.wait()
        raise
    if proc.returncode:
        raise RuntimeError('owned Docker operation failed')
    return out.decode()

async def main(args):
    from harbor.environments.factory import EnvironmentFactory
    from harbor.models.trial.config import EnvironmentConfig as TrialEnvironmentConfig
    from harbor.models.task.config import EnvironmentConfig as TaskEnvironmentConfig
    from harbor.models.trial.paths import TrialPaths
    from benchmarks.agent_supervisor.container_coding.terminal_deployment import deploy_supervisor, runtime_environment
    from benchmarks.agent_supervisor.container_coding.container_worker_deployment import deploy_worker_boundary
    from benchmarks.agent_supervisor.container_coding.retained_source_nomination_lifecycle import (
        run_retained_source_nomination_lifecycle, ReviewDecision)
    output = args.output.absolute()
    output.mkdir(exist_ok=False)
    started = time.monotonic()
    for row in json.loads((STAGE/'public-task-metadata.json').read_bytes())['files']:
        raw = Path(row['public_copy']).read_bytes()
        assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
    contract_raw = args.contract.read_bytes()
    metadata = tomllib.loads((STAGE / 'public-task-inputs/task.toml').read_text())
    task_config = TaskEnvironmentConfig.model_validate(metadata['environment'])
    original_image = task_config.docker_image
    task_config.docker_image = 'ipfs-nomination-lifecycle-public-task:20261012-01'
    paths = TrialPaths(trial_dir=output / 'sdk-trial-paths')
    paths.mkdir()
    environment = EnvironmentFactory.create_environment_from_config(
        config=TrialEnvironmentConfig(type='docker', force_build=False, delete=True),
        environment_dir=TASK / 'environment', environment_name='fix-code-vulnerability',
        session_id='nomination-lifecycle-' + args.attempt, trial_paths=paths, task_env_config=task_config)
    manifest = json.loads((STAGE / 'runtime-archive/manifest.json').read_bytes())
    receipt = {'schema': 'actual-retained-harbor-nomination-qualification@1', 'qualified': False,
        'actual_harbor_sdk_environment': True, 'original_public_task_recipe_used': True,
        'published_original_task_image_digest_qualified': False, 'published_original_image': original_image,
        'resource_limits': {'cpus': task_config.cpus, 'memory_mb': task_config.memory_mb, 'storage_mb': task_config.storage_mb},
        'runtime_archive_sha256': manifest['archive_sha256'], 'harness_sha256': sha(Path(__file__).read_bytes()),
        'public_requirement_contract_sha256': sha(contract_raw), 'public_requirement_contract_bytes': len(contract_raw),
        'real_auth_transferred': False, 'task_verifier_or_solution_read_hashed_or_run': False,
        'image_setup_target_execution_not_instrumented': True,
        'source_equivalence_proved': False, 'model_convergence_proved': False,
        'full_task_satisfaction_established': False, 'provider_total_session_token_savings_established': False}
    counts = {'start': 0, 'stop': 0}
    original_start, original_stop = environment.start, environment.stop
    container = None

    async def execute(label, code, *, user='root', timeout=60):
        answer = await environment.exec(command=shlex.join([PYTHON, '-I', '-c', code]),
            cwd='/app', user=user, env=runtime_environment(), timeout_sec=timeout)
        # Only static code / explicitly public scalar result exports are retained.
        (output / (label + '.stdout')).write_text(answer.stdout or '')
        (output / (label + '.stderr')).write_text(answer.stderr or '')
        if answer.return_code:
            raise RuntimeError(label + ' failed')
        return json.loads(answer.stdout)

    async def start():
        counts['start'] += 1
        # Current installed Harbor SDK requires the explicit build choice.
        return await original_start(force_build=False)

    async def stop(*, delete):
        counts['stop'] += 1
        try:
            # Named fresh report metadata only, before deletion. This additional
            # qualification export is explicitly outside official wall claims.
            code = r'''import hashlib,json,pathlib,subprocess
root=pathlib.Path('/opt/ipfs-supervisor/state')
reports={}
for phase in ('prepare_only','resume'):
 p=root/('retained-lifecycle-source-nomination-'+phase+'-result.json')
 if p.is_file():
  raw=p.read_bytes();assert len(raw)<=2000000;v=json.loads(raw)
  initial=v.get('initial_context',{})
  reports[phase]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
   'active_budget':v.get('source_nomination_active_budget'),
   'model_input_observation_audit':v.get('model_input_observation_audit'),
   'context_audit':v.get('context_audit'),
   'codebase_autoencoder':initial.get('codebase_autoencoder'),
   'codebase_ir_training_trace':initial.get('codebase_ir_training_trace'),
   'error_type':v.get('error',{}).get('type'),
   'error_message':v.get('error',{}).get('message'),
   'step_statuses':[{k:r.get(k) for k in ('name','returncode','seconds')} for r in v.get('steps',[])],
   'doctor_dispatch':{k:v.get('doctor_dispatch',{}).get(k) for k in ('route','selected_route','status','fallback_reason')}}
source=pathlib.Path('/app/bottle.py').read_bytes()
head=subprocess.check_output(['git','-C','/app','rev-parse','HEAD'],text=True).strip()
old=pathlib.Path('/opt/ipfs-supervisor/qualification-original-head.txt').read_text().strip()
ancestry=subprocess.run(['git','-C','/app','merge-base','--is-ancestor',old,head],capture_output=True).returncode==0
print(json.dumps({'reports':reports,'original_bottle_sha256_after':hashlib.sha256(source).hexdigest(),
 'old_head_ancestor':ancestry,'current_head':head},sort_keys=True,allow_nan=False))'''
            receipt['named_report_export'] = await execute('named-owner-public-metadata', code, user='supervisor', timeout=8)
        except BaseException as error:
            receipt['named_report_export_error_type'] = type(error).__name__
            if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                raise
        finally:
            stopped = await original_stop(delete=delete)
        return stopped

    environment.start, environment.stop = start, stop

    async def setup(env):
        nonlocal container
        deployed = await deploy_supervisor(env, archive_dir=STAGE / 'runtime-archive',
            output=output / 'deployment', auth_json=None, install_codex=True)
        if not deployed['qualified']:
            raise ValueError('actual production deployment refused')
        receipt['deployment_qualified'] = True
        receipt['original_bottle_sha256_before'] = deployed['original_inputs']['files']['bottle.py']['sha256']
        receipt['original_head'] = deployed['original_inputs']['head']
        head = output / 'original-head.txt'
        head.write_text(receipt['original_head'] + '\n')
        await env.upload_file(head, ROOT + '/qualification-original-head.txt')
        synthetic = output / 'synthetic-auth.json'
        synthetic.write_text('{}\n')
        await env.upload_file(synthetic, ROOT + '/codex-auth/auth.json')
        protected = await env.exec(command='chown 1000:1000 /opt/ipfs-supervisor/codex-auth/auth.json && chmod 0600 /opt/ipfs-supervisor/codex-auth/auth.json',
            cwd='/', user='root', env=None, timeout_sec=30)
        assert protected.return_code == 0
        boundary = await deploy_worker_boundary(env, output=output / 'worker-boundary')
        assert boundary['qualified']
        receipt['worker_boundary_qualified'] = True
        container = await env._platform._resolve_service_container('main')
        receipt['container_id'] = (await shell(['docker','inspect','--format','{{.Id}}',container])).strip()
        image_pin = json.loads((STAGE/'public-task-image.json').read_bytes())
        actual_image = (await shell(['docker','inspect','--format','{{.Image}}',container])).strip()
        pinned_image = image_pin.get('image_id') or image_pin.get('id')
        if actual_image != pinned_image:
            raise ValueError('Running container image differs from independently pinned public recipe image')
        receipt['actual_container_image_id'] = actual_image
        receipt['actual_container_image_matches_public_recipe_pin'] = True
        networks = json.loads(await shell(['docker','inspect','--format','{{json .NetworkSettings.Networks}}',container]))
        for network in networks:
            await shell(['docker','network','disconnect',network,container])
        receipt['external_network_detached'] = True
        receipt['local_unix_owner_control_not_disabled_by_qualification'] = True
        for source, name in [(STAGE/'public-task-inputs/instruction.md','public-instruction.md'),
                (args.contract,'public-requirement-contract.json')]:
            if source==args.contract and source.read_bytes()!=contract_raw:
                raise ValueError('Public contract changed before upload')
            await env.upload_file(source, ROOT + '/' + name)
            result = await env.exec(command='chown root:root ' + shlex.quote(ROOT+'/'+name) + ' && chmod 0444 ' + shlex.quote(ROOT+'/'+name),
                cwd='/', user='root', env=None, timeout_sec=30)
            assert result.return_code == 0
        # Actual imported module paths are joined to independently pinned archive
        # members inside the installed container, never to host source execution.
        modules = ['benchmarks.agent_supervisor.container_coding.' + n for n in (
            'terminal_container_supervisor','terminal_context_audit','terminal_model_input_observation_audit',
            'terminal_source_nomination_budget','source_nomination_review_preparation','terminal_initial_context',
            'container_worker_deployment')]
        modules += ['ipfs_accelerate_py.agent_supervisor.runtime.'+n for n in (
            'router_implementation_runner','model_input_observation_receipt','reviewed_source_nomination_context',
            'reviewed_source_nomination_audit','verified_code_retrieval_projection','compact_code_retrieval',
            'router_public_instruction')]
        rows = {row['path']: row for row in manifest['files']}
        expected = {n: rows['source/' + n.replace('.','/') + '.py'] for n in modules}
        code = "import sys;sys.path[:0]=['/opt/ipfs-supervisor/source','/opt/ipfs-supervisor/datasets','/opt/ipfs-supervisor/kit']\n"
        code += 'expected=' + repr(expected) + '\n'
        code += r'''import hashlib,importlib,json,pathlib,os
from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
records=[]
with public_replay_without_metadata():
 for name,row in expected.items():
  p=pathlib.Path(importlib.import_module(name).__file__);s=p.stat();raw=p.read_bytes()
  assert str(p)=='/opt/ipfs-supervisor/'+row['path'] and s.st_uid==0 and not s.st_mode&0o022
  assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
  records.append({'module':name,'path':str(p),'bytes':len(raw),'sha256':row['sha256'],'uid':s.st_uid})
print(json.dumps({'all_actual_imports_join_archive':True,'records':records},sort_keys=True))'''
        receipt['installed_import_provenance'] = await execute('installed-import-provenance',code,user='supervisor',timeout=60)
        print(json.dumps({'stage':'setup-complete','seconds':time.monotonic()-started}),flush=True)
        return {'qualified': True}

    async def review(inputs):
        baseline = json.loads(inputs.baseline)
        contract = json.loads(contract_raw)
        rows = contract['ledger']['requirements']
        def requirement(statement):
            return next(r['requirement_id'] for r in rows if statement in r['statement_ids'])
        value = {'schema':'supervisor-intent-source-nomination-review@1','bindings':baseline['bindings'],
            'review_ref':'authored-public-lifecycle-qualification@1', 'selectors':[
            {'requirement_id':requirement('public-bottle:statement:invalid-input-error'),'path':'bottle.py','qualified_symbol':symbol}
            for symbol in ('bottle._hkey','bottle._hval')]+[
            {'requirement_id':requirement('public-bottle:statement:identify-bottle'),'path':'bottle.py','qualified_symbol':'bottle.HeaderDict'}]}
        raw = wire(value)
        return ReviewDecision(raw=raw,sha256=sha(raw))

    try:
        lifecycle = await run_retained_source_nomination_lifecycle(environment=environment,setup=setup,review=review,
            output=output/'lifecycle',instruction=ROOT+'/public-instruction.md',
            requirement_contract=ROOT+'/public-requirement-contract.json',state=ROOT+'/state/retained-lifecycle',
            driver_controls={'semantic_transport':'native','doctor_profile':'generic','intent_requirements_transport':'compact',
                'code_retrieval_transport':'full','code_retrieval_codec':'compact','code_retrieval_wire_delivery':'inline',
                'disable_intent_autoencoder':True}, timeout_seconds=300,observer_mode=True)
        receipt['lifecycle'] = lifecycle
        receipt['qualified'] = lifecycle['qualified'] and counts == {'start':1,'stop':1}
        exported = receipt.get('named_report_export',{})
        reports = exported.get('reports',{})
        joins = {phase['phase']: reports.get(phase['phase'],{}).get('sha256') == phase['driver_report_sha256']
            for phase in lifecycle['phases']}
        receipt['named_report_sha256_joins'] = joins
        observed_audit = reports.get('resume',{}).get('model_input_observation_audit') or {}
        receipt['rendered_model_input_replay_verified'] = (observed_audit.get('schema') ==
            'terminal-model-input-observation-audit@1' and observed_audit.get('status') ==
            'verified_all_rendered_model_inputs' and observed_audit.get('all_rendered_model_inputs_verified') is True)
        receipt['qualified'] = receipt['qualified'] and set(joins)=={'prepare_only','resume'} and all(joins.values())
        receipt['qualified'] = receipt['qualified'] and receipt['rendered_model_input_replay_verified']
        receipt['original_bottle_preserved'] = exported.get('original_bottle_sha256_after') == receipt.get('original_bottle_sha256_before')
        receipt['old_head_ancestor'] = exported.get('old_head_ancestor')
        if not receipt['original_bottle_preserved'] or receipt['old_head_ancestor'] is not True:
            receipt['qualified'] = False
    except BaseException as error:
        receipt['failure_error_type'] = type(error).__name__
        receipt['qualified'] = False
    finally:
        receipt['environment_call_counts'] = counts
        receipt['seconds'] = time.monotonic()-started
        if container:
            ids=(await shell(['docker','ps','-aq','--filter','id='+receipt['container_id']])).strip()
            receipt['fresh_container_removed'] = not bool(ids)
            receipt['qualified'] = receipt['qualified'] and not bool(ids)
        (output/'qualification.json').write_bytes(wire(receipt)+b'\n')
        print(json.dumps({'stage':'qualification-finished','qualified':receipt['qualified'],
            'failure':receipt.get('lifecycle',{}).get('failure'),'seconds':receipt['seconds']}),flush=True)

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--attempt',required=True)
    asyncio.run(main(parser.parse_args()))
