"""Exercise both real driver CLIs, then measure paired complete input locally.

Reads only explicit public task metadata and named fresh phase reports. The
original public Docker recipe is built locally for ARM64; its published image
digest is not claimed. No Trial, task hasher, solution or verifier is used.
The fresh named-owner comparison is timed separately after driver STOP. It is
not provider-native billing, a full-session token experiment, or official wall.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import importlib
import json
from pathlib import Path
import re
import shlex
import time
import tomllib

STAGE = Path(__file__).resolve().parent
ROOT = '/opt/ipfs-supervisor'
PYTHON = ROOT + '/venv/bin/python'
TOKENIZER_CACHE = ROOT + '/tokenizer-cache'
TOKENIZER_ASSET_SHA256 = '446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d'
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
    if (output.parent != STAGE or output.resolve(strict=False) != output
            or re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}', output.name) is None
            or re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,47}', args.attempt) is None):
        raise ValueError('One fresh canonical Q output and bounded attempt label required')
    if args.contract.absolute() != STAGE/'public-task-inputs/reviewed-intent-contract.json':
        raise ValueError('Only the explicitly copied public reviewed contract is permitted')
    if (args.archive.absolute().parent != STAGE or args.archive.name not in
            {'runtime-archive','runtime-archive-02','runtime-archive-03'}
            or args.archive.resolve(strict=True) != args.archive.absolute()):
        raise ValueError('One canonical fresh Q runtime archive is required')
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
        session_id='token-pair-' + args.attempt, trial_paths=paths, task_env_config=task_config)
    manifest = json.loads((args.archive / 'manifest.json').read_bytes())
    receipt = {'schema': 'actual-terminal-token-pair-qualification@1', 'qualified': False,
        'actual_harbor_sdk_environment': True, 'original_public_task_recipe_used': True,
        'published_original_task_image_digest_qualified': False, 'published_original_image': original_image,
        'resource_limits': {'cpus': task_config.cpus, 'memory_mb': task_config.memory_mb, 'storage_mb': task_config.storage_mb},
        'runtime_archive_sha256': manifest['archive_sha256'], 'harness_sha256': sha(Path(__file__).read_bytes()),
        'public_requirement_contract_sha256': sha(contract_raw), 'public_requirement_contract_bytes': len(contract_raw),
        'real_auth_transferred': False, 'task_verifier_or_solution_read_hashed_or_run': False,
        'image_setup_target_execution_not_instrumented': True,
        'source_equivalence_proved': False, 'model_convergence_proved': False,
        'full_task_satisfaction_established': False, 'provider_total_session_token_savings_established': False,
        'official_wall_budget_qualified': False, 'token_comparison_is_separate_after_driver_stop': True,
        'token_comparison_in_official_agent_budget_claimed': False,
        'tokenizer_counts_are_local_not_provider_native': True}
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
            code = r'''import hashlib,json,os,pathlib,stat,subprocess,time
import sys
sys.path[:0]=['/opt/ipfs-supervisor/source','/opt/ipfs-supervisor/datasets','/opt/ipfs-supervisor/kit']
root=pathlib.Path('/opt/ipfs-supervisor/state')
reports={}
for phase in ('prepare_only','resume'):
 p=root/('retained-lifecycle-source-nomination-'+phase+'-result.json')
 if p.is_file():
  fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   s=os.fstat(fd);assert stat.S_ISREG(s.st_mode) and s.st_uid==1000 and s.st_nlink==1 and 0<s.st_size<=2000000
   raw=os.read(fd,2000001);assert len(raw)==s.st_size
   witness=lambda i:(i.st_dev,i.st_ino,i.st_size,i.st_mtime_ns,i.st_ctime_ns)
   assert witness(s)==witness(os.fstat(fd))==witness(p.lstat())
  finally:os.close(fd)
  v=json.loads(raw)
  assert v['schema']=='terminal-admitted-supervisor-run@1' and v['source_nomination_phase']==phase
  token_comparison=None
  token_comparison_seconds=None
  observation_binding=None
  if phase=='resume':
   observations=v['model_input_observations']
   if type(observations) is not list or len(observations)!=1:
    raise ValueError('Exactly one actual model-input observation required for paired comparison')
   observation_binding={key:observations[0][key] for key in (
    'observation_id','native_prompt_sha256','native_prompt_bytes','model_prompt_sha256','model_prompt_bytes')}
   from benchmarks.agent_supervisor.container_coding.terminal_input_token_comparison import compare_terminal_input_tokens
   from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
   os.environ['TIKTOKEN_CACHE_DIR']='/opt/ipfs-supervisor/tokenizer-cache'
   begun=time.monotonic()
   with public_replay_without_metadata():
    token_comparison=compare_terminal_input_tokens(state=pathlib.Path('/opt/ipfs-supervisor/state/retained-lifecycle'),
     observations=observations,workspace_root=pathlib.Path('/opt/ipfs-supervisor/worktrees'))
   token_comparison_seconds=time.monotonic()-begun
   def scalar_only(value,depth=0):
    if depth>12:raise ValueError('Comparison receipt nesting exceeds bounds')
    if value is None or type(value) in (bool,int,float):return
    if type(value) is str:
     if len(value.encode())>2048:raise ValueError('Comparison receipt contains unbounded text')
     return
    if type(value) is list:
     if len(value)>256:raise ValueError('Comparison receipt list exceeds bounds')
     for child in value:scalar_only(child,depth+1)
     return
    if type(value) is dict:
     if len(value)>128:raise ValueError('Comparison receipt field count exceeds bounds')
     for key,child in value.items():
      if type(key) is not str or len(key)>128 or key in {'prompt','packet','source_text','query','wire','payload','command','text'}:
       raise ValueError('Only comparison scalar metadata may be exported')
      scalar_only(child,depth+1)
     return
    raise ValueError('Comparison receipt contains non-JSON data')
   scalar_only(token_comparison)
   if len(json.dumps(token_comparison,sort_keys=True,allow_nan=False).encode())>65536:
    raise ValueError('Comparison scalar receipt exceeds bounds')
  initial=v.get('initial_context',{})
  learner=initial.get('codebase_autoencoder') or {}
  learner_keys=('schema','domain','source_count','sample_count','receipt_sha256','checkpoint_sha256',
   'source_hashes','epochs_completed','training_elapsed_seconds','metrics','authority','provider_calls','proof_authority')
  reports[phase]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
   'token_comparison':token_comparison,'token_comparison_seconds':token_comparison_seconds,
   'model_input_observation_binding':observation_binding,
   'active_budget':v.get('source_nomination_active_budget'),
   'model_input_observation_audit':v.get('model_input_observation_audit'),
   'context_audit':v.get('context_input_audit'),
   'phases':v.get('phases'),'native_diagnostics':v.get('native_diagnostics'),
   'native_dispatch_diagnostics':v.get('native_dispatch_diagnostics'),
   'observer_stop':v.get('observer_stop'),'observer_lifecycle_qualified':v.get('observer_lifecycle_qualified'),
   'model_input_worker_error_diagnostics':v.get('model_input_worker_error_diagnostics'),
   'task_state':v.get('task_state'),'implementation_route':v.get('implementation_route'),
   'unavailable_settlement':v.get('unavailable_settlement'),
   'codebase_autoencoder':{k:learner[k] for k in learner_keys if k in learner},
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
            receipt['named_report_export'] = await execute('named-owner-public-metadata', code, user='supervisor', timeout=40)
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
        deployed = await deploy_supervisor(env, archive_dir=args.archive,
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
        installed = await env.exec(command=shlex.join([PYTHON,'-m','pip','install','--no-cache-dir','tiktoken==0.13.0']),
            cwd='/app', user='root', env=runtime_environment(), timeout_sec=120)
        receipt['tokenizer_install'] = {'requested':'tiktoken==0.13.0','returncode':installed.return_code,
            'stdout_sha256':sha((installed.stdout or '').encode()),'stderr_sha256':sha((installed.stderr or '').encode()),
            'raw_install_output_exported':False}
        if type(installed.return_code) is not int or installed.return_code != 0:
            raise RuntimeError('Pinned local tokenizer installation failed')
        # The official constructor verifies the expected data digest before use.
        # Warm while setup still has network, then prohibit supervisor writes.
        code = r'''import hashlib,importlib.metadata,json,os,pathlib,stat
cache=pathlib.Path('/opt/ipfs-supervisor/tokenizer-cache')
cache.mkdir(mode=0o755)
os.environ['TIKTOKEN_CACHE_DIR']=str(cache)
import tiktoken,tiktoken_ext.openai_public,tiktoken._tiktoken
assert importlib.metadata.version('tiktoken')=='0.13.0'
encoding=tiktoken.get_encoding('o200k_base')
url='https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken'
expected='446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d'
name=hashlib.sha1(url.encode()).hexdigest()
assert sorted(p.name for p in cache.iterdir())==[name]
p=cache/name
fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
 before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=8000000
 raw=b''
 while len(raw)<=8000000:
  block=os.read(fd,min(65536,8000001-len(raw)))
  if not block:break
  raw+=block
 witness=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 assert len(raw)==before.st_size and witness(before)==witness(os.fstat(fd))==witness(p.lstat())
finally:os.close(fd)
assert hashlib.sha256(raw).hexdigest()==expected
os.chown(p,0,0);os.chmod(p,0o444);os.chown(cache,0,0);os.chmod(cache,0o555)
modules=[]
for module in (tiktoken,tiktoken_ext.openai_public,tiktoken._tiktoken):
 f=pathlib.Path(module.__file__);s=f.stat();data=f.read_bytes()
 assert f.is_relative_to('/opt/ipfs-supervisor/venv') and s.st_uid==0 and not s.st_mode&0o022
 modules.append({'module':module.__name__,'path':str(f),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'uid':0})
print(json.dumps({'schema':'terminal-local-tokenizer-setup@1','version':'0.13.0','encoding':encoding.name,
 'vocabulary_size':encoding.n_vocab,'asset_path':str(p),'asset_bytes':len(raw),'asset_sha256':expected,
 'official_expected_hash_verified':True,'warmed_before_network_detach':True,
 'cache_uid':0,'cache_mode':0o555,'asset_uid':0,'asset_mode':0o444,'module_files':modules,
 'local_counts_not_provider_native':True},sort_keys=True))'''
        receipt['tokenizer_setup'] = await execute('local-tokenizer-setup',code,user='root',timeout=60)
        code = r'''import hashlib,importlib.metadata,json,os,pathlib
assert os.getuid()==1000 and os.geteuid()==1000
cache=pathlib.Path('/opt/ipfs-supervisor/tokenizer-cache');os.environ['TIKTOKEN_CACHE_DIR']=str(cache)
files=list(cache.iterdir());assert len(files)==1
p=files[0];assert not os.access(cache,os.W_OK) and not os.access(p,os.W_OK)
assert os.access(cache,os.R_OK|os.X_OK) and os.access(p,os.R_OK)
assert hashlib.sha256(p.read_bytes()).hexdigest()=='446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d'
import tiktoken
assert importlib.metadata.version('tiktoken')=='0.13.0'
encoding=tiktoken.get_encoding('o200k_base')
print(json.dumps({'supervisor_uid':os.getuid(),'cache_read_only_to_supervisor':True,
 'encoding':encoding.name,'local_sample_token_count':len(encoding.encode('paired-input qualification')),
 'local_counts_not_provider_native':True},sort_keys=True))'''
        receipt['tokenizer_supervisor_probe'] = await execute('local-tokenizer-supervisor-probe',code,user='supervisor',timeout=15)
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
            'container_worker_deployment','terminal_observer_stop','retained_source_nomination_lifecycle',
            'terminal_input_token_comparison')]
        modules += ['ipfs_accelerate_py.agent_supervisor.entrypoints.admitted_benchmark_runtime',
            'ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon',
            'ipfs_accelerate_py.agent_supervisor.context.database_context']
        modules += ['ipfs_accelerate_py.agent_supervisor.runtime.'+n for n in (
            'router_implementation_runner','model_input_observation_receipt','reviewed_source_nomination_context',
            'reviewed_source_nomination_audit','verified_code_retrieval_projection','compact_code_retrieval',
            'router_public_instruction','native_dispatch_diagnostics',
            'code_source_inspection','intent_source_inspection','native_task_identity')]
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
        resume = reports.get('resume',{})
        paired = resume.get('token_comparison')
        receipt['token_comparison'] = paired
        receipt['token_comparison_seconds'] = resume.get('token_comparison_seconds')
        binding = resume.get('model_input_observation_binding') or {}
        tokenizer = paired.get('tokenizer',{}) if type(paired) is dict else {}
        checks = paired.get('checks',{}) if type(paired) is dict else {}
        measures = paired.get('measurements',{}) if type(paired) is dict else {}
        compact = measures.get('compact',{})
        expected_checks = {'observed_compact_replay_verified','expanded_counterfactual_replay_verified',
            'identical_public_requirement_bindings','literal_public_source_preserved',
            'shared_catalog_and_residual_preserved','whole_packet_tokenization',
            'tokenizer_roundtrip_verified','capture_unchanged_after_counting'}
        receipt['token_comparison_qualified'] = (
            type(paired) is dict and paired.get('schema')=='terminal-input-token-comparison@1'
            and paired.get('qualified') is True and paired.get('observed_arm')=='compact'
            and paired.get('counterfactual_arm')=='expanded'
            and type(paired.get('observed_records_seen')) is int and paired['observed_records_seen']==1
            and tokenizer.get('version')=='0.13.0' and tokenizer.get('encoding')=='o200k_base'
            and tokenizer.get('bpe_asset_sha256')==TOKENIZER_ASSET_SHA256
            and tokenizer.get('vocabulary_pattern_special_tokens_sha256')==
                'a6557bbd3ceb299981ac87fd86a51fa8f0e9505be18ed608c5ada94bdfd0f63f'
            and tokenizer.get('provider_tokenizer_equivalence_established') is False
            and set(checks)==expected_checks and all(value is True for value in checks.values())
            and set(measures)=={'expanded','compact'}
            and all(type(row) is dict and set(row)=={'sha256','bytes','tokens'}
                and re.fullmatch(r'[a-f0-9]{64}',str(row['sha256'])) is not None
                and type(row['bytes']) is int and 0<row['bytes']<=256000
                and type(row['tokens']) is int and 0<row['tokens']<=1000000 for row in measures.values())
            and type(paired.get('tokens_saved')) is int
            and paired['tokens_saved']==measures['expanded']['tokens']-compact.get('tokens')
            and type(paired.get('byte_savings')) is int
            and paired['byte_savings']==measures['expanded']['bytes']-compact.get('bytes')
            and paired.get('bindings',{}).get('observation_id')==binding.get('observation_id')
            and paired.get('bindings',{}).get('native_prompt_sha256')==binding.get('native_prompt_sha256')
            and compact.get('sha256')==binding.get('model_prompt_sha256')
            and compact.get('bytes')==binding.get('model_prompt_bytes')
            and all(paired.get(key) is False for key in ('provider_usage_measured',
                'provider_total_session_token_savings_established','current_freshness_verified',
                'source_equivalence_proved','full_task_satisfaction_established','global_model_convergence_proved',
                'raw_prompts_exported','proof_authority','execution_authority','completion_authority'))
            and receipt.get('tokenizer_supervisor_probe',{}).get('cache_read_only_to_supervisor') is True)
        receipt['qualified'] = receipt['qualified'] and receipt['token_comparison_qualified']
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
            try:
                ids=(await shell(['docker','ps','-aq','--filter','id='+receipt['container_id']])).strip()
                receipt['fresh_container_removed'] = not bool(ids)
                receipt['qualified'] = receipt['qualified'] and not bool(ids)
            except BaseException as error:
                receipt['fresh_container_removed'] = None
                receipt['container_removal_inspection_error_type'] = type(error).__name__
                receipt['qualified'] = False
        (output/'qualification.json').write_bytes(wire(receipt)+b'\n')
        print(json.dumps({'stage':'qualification-finished','qualified':receipt['qualified'],
            'failure':receipt.get('lifecycle',{}).get('failure'),'seconds':receipt['seconds']}),flush=True)

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--attempt',required=True)
    parser.add_argument('--archive',type=Path,default=STAGE/'runtime-archive')
    asyncio.run(main(parser.parse_args()))
