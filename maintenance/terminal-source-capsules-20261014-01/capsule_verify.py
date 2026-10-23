"""Cold replay of current source, codec, native capsules, SQL and full costs."""
import argparse
import json
from pathlib import Path
import resource
from capsule_io import ROOT,FALSE,inputs,read,write,wire,sha
from capsule_run import POLICY,check_lease,build_indexed_contexts

FILES=['policy.json','corpus-manifest.json','lineage.json','structural-report.json','native-capsules.json',
 'codec-views.json','tokenizer.json','metadata-report.json','context-costs.json']

def verify(output):
 resource.setrlimit(resource.RLIMIT_CPU,(240,240));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
 resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
 if output.resolve()!=output or output.parent!=ROOT:raise ValueError('owned canonical run required')
 result_raw=read(output/'result.json');result=json.loads(result_raw)
 fields={'schema','completed','policy','native_head','source_count','task_count','native_capsule_inventory',
  'old_adapter_refusal','metadata_original_record_counts','source_roundtrips','context_compilations',
  'paired_local_scenarios','artifact_pins','provider_invocations','new_optimizer_updates','new_prover_invocations',
  'native_structural_context_and_plan_materials_exercised','native_context_compiler_exercised',
  'planning_requirements_all_unresolved','token_accounting_is_counterfactual','source_body_execution',
  'seconds','peak_rss_kib',*FALSE}
 if type(result) is not dict or set(result)!=fields:raise ValueError('closed source capsule result scope required')
 if result['schema']!='terminal-current-source-capsule-experiment@1' or result['completed'] is not True or result['policy']!=POLICY:
  raise ValueError('complete source-capsule profile required')
 if any(result.get(k) is not False for k in FALSE) or result['source_body_execution'] is not False or result['provider_invocations']!=0:
  raise ValueError('unobserved runtime or provider authority')
 if any(result[k] is not True for k in ['native_structural_context_and_plan_materials_exercised',
  'native_context_compiler_exercised','planning_requirements_all_unresolved','token_accounting_is_counterfactual']):
  raise ValueError('observed local context or counterfactual scope differs')
 if [r['relative_path'] for r in result['artifact_pins']]!=sorted(FILES):raise ValueError('complete closed selected artifact scope required')
 for row in result['artifact_pins']:
  if set(row)!={'relative_path','bytes','sha256'}:raise ValueError('closed artifact pin required')
  raw=read(output/row['relative_path'],32*1024**2)
  if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('selected artifact changed')
 corpus,bodies,instructions,lineage=inputs()
 if wire(corpus)!=read(output/'corpus-manifest.json') or wire(lineage)!=read(output/'lineage.json'):
  raise ValueError('sealed lineage differs')
 for task in corpus['tasks']:
  if read(output/'instructions'/task['task_id']/'instruction.md',8192)!=instructions[task['task_id']]:
   raise ValueError('complete copied task instruction changed')
 structural=json.loads(read(output/'structural-report.json'))
 from native_structural_ir import verify_structural_ir,_scheduler
 verify_structural_ir(repository=output/'source-repository',output=output/'structural',expected=structural)
 for s in structural['sources']:
  if read(output/'source-repository'/s['path'],8192)!=bodies[s['path']]:raise ValueError('original source changed')
 from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
 from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
 from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
 from native_capsules import verify_native_capsules
 from capsule_codec import build_capsule_codec,expand_capsule_codec
 from token_cost_review import load_tokenizer
 from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as metadata_api
 from benchmarks.agent_supervisor.container_coding.terminal_codebase_supervisor_fixture import reconstruct_terminal_codebase_metadata_records
 from metadata_selection import build_records
 native=json.loads(read(output/'native-capsules.json'));codecs=json.loads(read(output/'codec-views.json'))
 metadata=json.loads(read(output/'metadata-report.json'))
 with _scheduler().acquire(ResourceLane.VALIDATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
  timeout=30,request_id='terminal-source-capsules:cold-replay') as lease:
  check_lease(lease)
  verify_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']),CodebaseHead.from_dict(structural['head']),native)
  for s in structural['sources']:
   path=s['path']
   for arm in ['minified','aliased']:
    codec=codecs[path][arm]
    regenerated=build_capsule_codec(bodies[path],path,s['source_cid'],structural['head'],aliases=arm=='aliased')
    if codec!=regenerated or expand_capsule_codec(codec,structural['head'],s['sha256'],s['source_cid'],expected_path=path)!=bodies[path]:
     raise ValueError('source codec or exact expansion differs')
  tokenizer,descriptor=load_tokenizer(json.loads(read(output/'tokenizer.json')))
  with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,child_process_slots=1,
   timeout=20,request_id='terminal-source-capsules:cold-lake') as child:
   check_lease(child)
   reopened=metadata_api.validate_codebase_ir_metadata(output=output/'metadata',expected=metadata['native_metadata'],fresh_process=True)
  restored={}
  for family,export in reopened['exports'].items():
   restored[family]=[json.loads(line)['payload'] for line in read(output/'metadata'/export['relative_path'],32*1024**2).splitlines()]
  recovered=reconstruct_terminal_codebase_metadata_records(restored)
  records=build_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,native=native,codecs=codecs,lineage=lineage)
  from metadata_projections import _wire as metadata_wire
  if metadata_wire(recovered)!=metadata_wire(records) or sha(metadata_wire(recovered))!=metadata['records_sha256']:
   raise ValueError('complete metadata replay differs')
  contexts=build_indexed_contexts(output=output,structural=structural,corpus=corpus,instructions=instructions,
   native=native,metadata=metadata,tokenizer=tokenizer,descriptor=descriptor,lease=lease)
  if wire(contexts)!=read(output/'context-costs.json'):raise ValueError('complete cold context and cost scripts differ')
 if result['native_head']!=structural['head'] or result['native_capsule_inventory']!=native['complete_inventory'] or result['metadata_original_record_counts']!=metadata['family_counts'] or result['old_adapter_refusal']!=native['sealed_adapter_outcome']:
  raise ValueError('headline source/capsule/metadata bindings differ')
 if any(type(result[k]) is not int or result[k]!=v for k,v in {'source_count':5,'task_count':4,
  'source_roundtrips':10,'context_compilations':12,'paired_local_scenarios':32,'new_optimizer_updates':0,'new_prover_invocations':0}.items()):
  raise ValueError('headline local work counters differ')
 verify_structural_ir(repository=output/'source-repository',output=output/'structural',expected=structural)
 if inputs()[3]!=lineage:raise ValueError('sealed lineage changed during use')
 if read(output/'result.json')!=result_raw:raise ValueError('experiment result changed during cold replay')
 for row in result['artifact_pins']:
  raw=read(output/row['relative_path'],32*1024**2)
  if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('selected artifact changed during cold replay')
 return {'schema':'terminal-source-capsules-cold-replay@1','qualified':True,
  'native_current_owner_observed_before_and_after':True,'generic_native_capsules_complete':True,
  'all_ten_source_views_byte_exact':True,'native_context_compiler_and_plan_materials_replayed':True,
  'all_32_counterfactual_pairs_exact':True,'complete_duckdb_ducklake_records_reopened':True,
  'offline_tokenizer_definition_and_implementation_pinned':True,'provider_usage':None,
  'context_native_reserved_budget_separate_from_whole_serialized_bpe':True,**FALSE}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--report',required=True);args=parser.parse_args()
 for name in [args.run,args.report]:
  if not name or Path(name).name!=name or name in {'.','..'}:raise ValueError('local names required')
 report=verify(ROOT/args.run);write(ROOT/args.report,report);print(json.dumps({'qualified':True,'counterfactual_pairs':32}))
