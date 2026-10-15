"""Fresh signed AA administrative fixture; no START or source execution."""
import hashlib,json,os,pathlib,subprocess,sys
from collections.abc import Mapping
root=pathlib.Path('/opt/ipfs-supervisor');repo=pathlib.Path('/app');state=root/'state/native-fixture-aa17';public=root/'public-fixture-aa17'
assert os.getuid()==os.geteuid()==1000
repo.chmod(0o755)
assert not state.exists() and public.is_dir() and not any(public.iterdir())
state.mkdir(mode=0o700)
def plain(x):
 if isinstance(x,Mapping):return {k:plain(v)for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [plain(v)for v in x]
 return x
def write(name,value):
 path=public/name
 with path.open('x')as f:json.dump(plain(value),f,sort_keys=True,indent=2);f.write('\n')
 path.chmod(0o444)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
sources={'callee.py':b'def increment(n: int) -> int:\n    return n + 1\n','caller.py':b'from callee import increment\n\ndef twice(n: int) -> int:\n    return increment(increment(n))\n','dynamic.py':b'def unsupported(expression):\n    return eval(expression)\n'}
assert sum(map(len,sources.values()))==195
prompt='Under closed-caller-model@1, caller.py::twice(n) must return n + 2.'
sources['build/task-instruction.txt']=prompt.encode()
tracked={name for name in git('ls-files','-z').split('\0') if name}
if not tracked:
 for name,raw in sources.items():
  path=repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.parent.chmod(0o755)
  assert not path.exists();path.write_bytes(raw);path.chmod(0o644)
 git('add','--',*sources)
 git('-c','user.name=AA admitted observer fixture','-c','user.email=fixture@localhost','commit','-qm','Authored pending AA closed-caller review fixture')
else:
 assert tracked==set(sources) and all((repo/name).read_bytes()==raw for name,raw in sources.items()),'reuse only exact previously authored four-file baseline'
exclude=repo/'.git/info/exclude'
if '/.runtime/' not in exclude.read_text().splitlines():exclude.write_text(exclude.read_text()+'\n/.runtime/\n')
git('bundle','create',str(public/'source.gitbundle'),'HEAD')
(public/'source.gitbundle').chmod(0o444)
from ipfs_accelerate_py.agent_supervisor.entrypoints.facade import Supervisor
from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import content_identity
from ipfs_accelerate_py.agent_supervisor.prompt.prompt_workflow import PromptAcceptanceRecord,PromptGoalGraph,PromptGoalRecord,PromptOutputRecord,PromptTaskRecord,PromptValidationRecord
from ipfs_accelerate_py.agent_supervisor.runtime import local_planning_admission as local
from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository
from ipfs_accelerate_py.agent_supervisor.runtime.supervised_task_context import prepare_supervised_task_context
from ipfs_accelerate_py.agent_supervisor.runtime.task_context_bundle import write_task_context_bundle
from ipfs_accelerate_py.agent_supervisor.runtime.router_public_instruction import prepare_public_instruction_context
from ipfs_accelerate_py.agent_supervisor.context.context_compiler import ContextCompiler,build_text_context_references,render_context_capsule
from ipfs_accelerate_py.agent_supervisor.context.context_contracts import ContextBudget
profile=state/'profile';lifecycle=state/'lifecycle'
bootstrap=Supervisor.init_local(repository=repo,consent=True,profile_dir=profile,lifecycle_dir=lifecycle)
policy=content_identity(local.LOCAL_POLICY)
validation=PromptValidationRecord(validation_key='static-git-diff-check',argv=('/usr/bin/git','diff','--check'),policy_cid=policy)
acceptance=PromptAcceptanceRecord(criterion_key='conditional-review-pending',criterion='Conditional arithmetic/source review remains pending. Declared static whitespace validation alone establishes no behavioral or source equivalence.',validation_keys=(validation.validation_key,))
output=PromptOutputRecord(path='caller.py',effect='modify',media_type='text/x-python')
goal=PromptGoalRecord(goal_key='AA-CLOSED-CALLER-GOAL',parent_goal_cid='',dependency_goal_cids=(),title='Review the declared conditional caller model',objective=prompt,rationale='Authored conditional review; no behavioral satisfaction claimed',scope_paths=tuple(sources),acceptance=(acceptance,))
task=PromptTaskRecord(task_key='AA-CLOSED-CALLER-TASK',goal_cid=goal.goal_cid,dependency_task_cids=(),objective=prompt,rationale='Retain full source, assumptions and unsupported dynamic residual; no completion in observer mode',scope_paths=tuple(sources),outputs=(output,),validations=(validation,),acceptance=(acceptance,),evidence_cids=(),policy_roots=(policy,),predicted_files=('caller.py',))
roots={'request_cid':content_identity({'prompt':prompt}),'scan_cid':content_identity({'sources':local._sources(repo,list(sources))}),'program_root':content_identity({'git_tree':git('rev-parse','HEAD^{tree}')})}
graph=PromptGoalGraph(**roots,policy_roots=(policy,),goals=(goal,),tasks=(task,),evidence=())
specs=[{'task_key':task.task_key,'scope_paths':list(task.scope_paths),'dependencies':[],'outputs':[{'path':output.path,'effect':output.effect,'media_type':output.media_type}],'validations':[{k:local._plain(getattr(validation,k))for k in ('validation_key','argv','cwd','expected_exit_codes','policy_cid')}],'acceptance':[{k:local._plain(getattr(acceptance,k))for k in ('criterion_key','criterion','evidence_cids','validation_keys')}]}]
manifest=local.author_local_benchmark_manifest(repository=repo,profile_dir=profile,lifecycle_dir=lifecycle,task_specs=specs,planning_roots=roots)
admission=local.admit_local_benchmark_plan(graph=graph,manifest=manifest)
assert set(manifest['payload']['sources'])==set(sources)
write('manifest.json',manifest);write('graph.json',graph.to_dict());write('admission.json',admission)
with IntentRepository(state/'intent.duckdb')as intent:
 materialized=local.materialize_local_benchmark_plan(admission=admission,intent=intent)
 current=intent.get_task(task.task_cid)
 assert current['status'] not in ('completed','done','skipped')
 context=prepare_supervised_task_context(repository=repo,intent=intent,task_cid=task.task_cid,paths=['callee.py','caller.py','dynamic.py'],required_raw_paths=['callee.py','caller.py','dynamic.py'],output=repo/'.runtime/native-fixture/context',semantic_context_input_tokens=32768)
 context_bundle=write_task_context_bundle(repository=repo,prepared=[context],output=repo/'.runtime/native-fixture/context-nominations.json')
 write('materialization.json',materialized);write('context-preparation.json',context)
 write('task-readback.json',{'task_cid':task.task_cid,'task_alias':current['task_alias'],'status':current['status'],'revision':current['revision'],'event_watermark':intent.event_watermark(),'pending_cid':materialized['pending_cid'],'completion_authority':False,'validation_executed':False})
instruction=prepare_public_instruction_context(repository=repo,admission=admission,task_cid=task.task_cid,source_path='build/task-instruction.txt',expected_source_sha256=sha(prompt.encode()))
refs=[]
for kind,path,digest in [('semantic-context',repo/context['metadata']['Semantic context artifact'],context['metadata']['Semantic context sha256']),('world-context',repo/context['metadata']['World context artifact'],context['metadata']['World context sha256'])]:
 raw=path.read_bytes();assert sha(raw)==digest
 refs.extend(build_text_context_references(raw.decode(),reference_prefix=kind,kind=kind,path=path.relative_to(repo).as_posix(),repository_id=context['repository_id'],tree_id=admission['receipt']['payload']['source_tree_id'],required=True,chunk_bytes=8192))
compiler=ContextCompiler(ContextBudget(max_input_tokens=128000,max_items=256,max_item_bytes=16384,max_serialized_bytes=262144))
compiled=compiler.compile(repository_id=context['repository_id'],tree_id=admission['receipt']['payload']['source_tree_id'],objective_id=task.task_key,objective_revision=content_identity(task.to_dict()),policy_id=policy,policy_revision=policy,caller='supervisor:aa-admitted-fixture',stage='implementation',goal={'id':task.task_key,'objective':prompt,'task_cid':task.task_cid},authority={'mode':'candidate_only','completion_authority':False},scope={'allowed_paths':['caller.py'],'read_only_paths':['callee.py','dynamic.py','build/task-instruction.txt']},acceptance={'criteria':['Conditional review and declared static validation remain pending'],'validation_executed':False},evidence=tuple(refs))
compiler.verify_compile_result(compiled)
native_prompt=render_context_capsule(compiled.capsule)
(public/'native-prompt.txt').write_text(native_prompt);(public/'native-prompt.txt').chmod(0o444)
write('native-capsule.json',compiled.capsule.to_dict());write('compilation-receipt.json',compiled.receipt.to_dict());write('instruction-descriptor.json',instruction);write('context-bundle.json',context_bundle)
for name,raw in sources.items():assert (repo/name).read_bytes()==raw
receipt={'schema':'admitted-budget-genuine-native-fixture@1','qualified':True,'repository':'/app','state':str(state),'database':str(state/'intent.duckdb'),'profile_dir':str(profile),'lifecycle_dir':str(lifecycle),'task_cid':task.task_cid,'task_id':task.task_key,'plan_id':materialized['plan_id'],'manifest_cid':materialized['manifest_cid'],'pending_cid':materialized['pending_cid'],'baseline_commit':git('rev-parse','HEAD'),'git_tree':git('rev-parse','HEAD^{tree}'),'source_inventory':{name:{'bytes':len(raw),'sha256':sha(raw)}for name,raw in sources.items()},'python_source_bytes':195,'instruction_bytes':len(prompt.encode()),'instruction_text':prompt,'semantic_root_cid':context['semantic_root_cid'],'semantic_scope_paths':['callee.py','caller.py','dynamic.py'],'world_snapshot_cid':context['world_snapshot_cid'],'context_bundle':context_bundle,'public_instruction':instruction,'native_prompt':{'path':str(public/'native-prompt.txt'),'bytes':len(native_prompt.encode()),'sha256':sha(native_prompt.encode())},'bootstrap':bootstrap,'materialization':materialized,'context_compiler_used':True,'source_body_executed':False,'validation_executed':False,'START_called':False,'worker_dispatched':False,'manual_native_prompt_is_fixture_only':True,'provider_calls':0,'training_steps':0,'current_facts':[],'task_completed':False,'source_equivalence_or_model_convergence_proved':False,'scope':'Genuine LOCAL signed administrative admission, pending task and native semantic/world context; no task behavior or FullSupervisor/Terminal-Bench qualification.'}
write('owner-receipt.json',receipt)
print(json.dumps({'qualified':True,'public_directory':str(public),'task_cid':task.task_cid,'context_bundle':context_bundle,'native_prompt_bytes':len(native_prompt.encode())}))

