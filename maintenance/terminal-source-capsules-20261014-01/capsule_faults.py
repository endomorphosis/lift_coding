"""Real current-source guards, including mutation during the supervisor seam."""
import argparse
import json
import os
from pathlib import Path
import resource
from capsule_io import ROOT,FALSE,read,write,pin,sha

def replace_owned(path,raw):
 if ROOT not in path.parents:raise ValueError('owned fault path required')
 read(path,32*1024**2)
 descriptor=os.open(path,os.O_WRONLY|os.O_TRUNC|os.O_NOFOLLOW)
 try:
  with os.fdopen(descriptor,'wb',closefd=False) as stream:
   stream.write(raw);stream.flush();os.fsync(stream.fileno())
 finally:os.close(descriptor)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--report',required=True);args=parser.parse_args()
 for name in [args.run,args.report]:
  if not name or Path(name).name!=name or name in {'.','..'}:raise ValueError('local fault names required')
 resource.setrlimit(resource.RLIMIT_CPU,(240,240));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
 resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
 output=ROOT/args.run;structural=json.loads(read(output/'structural-report.json'))
 source=output/'source-repository'/'headless-terminal/environment/base_terminal.py'
 packet=output/'codec-views.json';result=output/'result.json';paths=[source,packet,result]
 before=[pin(p) for p in paths];controls=[]
 from native_structural_ir import _owner,_scheduler,verify_structural_ir
 from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
 from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
 from ipfs_accelerate_py.agent_supervisor.planning.structural_codebase_context import run_with_structural_codebase_context
 head=CodebaseHead.from_dict(structural['head'])
 original=read(source,8192)
 with _scheduler().acquire(ResourceLane.ORCHESTRATION,cpu_slots=1,memory_mb=512,child_process_slots=1,
  timeout=30,request_id='terminal-source-capsules:mid-context-fault') as lease:
  with _owner(output/'structural',existing=True) as (index,_):
   entered=[]
   def drift(context):
    entered.append(context.to_dict());replace_owned(source,original+b'\n# owned mid-context stale source\n')
    return {'candidate_context':'must not escape before final observation'}
   try:
    try:
     run_with_structural_codebase_context(index,output/'source-repository',drift,repository_id=head.repository_id,
      expected_head=head,parent_lease=lease,memory_mb=256,
      timeout_seconds=60,admission_timeout_seconds=20)
    except Exception as error:
     if type(error).__name__!='StaleCodebaseError' or len(entered)!=1:raise
     controls.append({'control':'source_mutated_inside_real_supervisor_context_callback',
      'refused':True,'exception':type(error).__name__,'before_observation_passed':True,
      'candidate_escaped_context':False,'changed_file':'headless-terminal/environment/base_terminal.py'})
    else:raise ValueError('mid-context source drift accepted')
   finally:replace_owned(source,original)
 from capsule_verify import verify
 def control(name,path,transform,exception,message):
  raw=read(path,32*1024**2)
  try:
   replace_owned(path,transform(raw))
   try:verify(output)
   except Exception as error:
    if type(error).__name__!=exception or message not in str(error):raise
    controls.append({'control':name,'refused':True,'exception':type(error).__name__,'message':str(error)})
   else:raise ValueError('negative source-capsule control accepted')
  finally:replace_owned(path,raw)
 control('persisted_codec_packet_changed',packet,lambda b:b+b' ','ValueError','selected artifact changed')
 def promote(raw):
  data=json.loads(raw);data['provider_token_savings_measured']=True
  return json.dumps(data,sort_keys=True,separators=(',',':')).encode()
 control('estimated_tokens_promoted_to_provider_usage',result,promote,'ValueError','provider authority')
 verify_structural_ir(repository=output/'source-repository',output=output/'structural',expected=structural)
 if [pin(p) for p in paths]!=before:raise ValueError('fault bodies not exactly restored')
 report={'schema':'terminal-source-capsules-live-faults@1','qualified':True,'controls':controls,
  'all_original_bodies_restored':True,'positive_cold_replay_required_after_controls':True,
  'provider_invocations':0,'source_body_execution':False,**FALSE}
 write(ROOT/args.report,report);print(json.dumps({'qualified':True,'refused_controls':len(controls)}))

if __name__=='__main__':main()
