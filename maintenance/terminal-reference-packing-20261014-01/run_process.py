"""Freeze named producers, retain attempt logs, bound the complete process group."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from packing_io import ROOT,CAPS,read,write,pin,sha
from capsule_io import RICH,TYPED,PRIOR,ABC,DATASETS

LOCAL=['env_run.py','launch.py','packing_io.py','packing_metadata.py','reference_codec.py','nested_context.py',
 'packing_costs.py','packing_run.py','packing_verify.py','packing_faults.py','run_process.py','finalize_stage.py',
 'test_reference_codec.py','test_nested_context.py','test_packing_costs.py','test_packing_integration.py','test_final_evidence.py','test_fault_receipt.py']
BORROWED=['capsule_io.py','native_capsules.py','capsule_codec.py','token_cost_review.py','context_projection.py','capsule_run.py']
TESTS=[name for name in LOCAL if name.startswith('test_')]

def selected():
 paths=[ROOT/name for name in LOCAL]
 paths += [CAPS/name for name in BORROWED]+[CAPS/'evidence-manifest.json']
 paths += [RICH/name for name in ['evidence_io.py','evidence-manifest.json']]
 paths += [TYPED/name for name in ['native_structural_ir.py','scheduler_overlay.py','evidence-manifest.json',
  'native-policy-overlay-01/source-pins.json','native-policy-overlay-01/resource_scheduler.py',
  'native-policy-overlay-01/proof_resource_safety.py']]
 paths += [Path('/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer')/name
  for name in ['proof_resource_safety.py','resource_scheduler.py']]
 paths += [PRIOR/name for name in ['evidence-manifest.json','metadata_projections.py','seal_training_evidence.py']]
 paths += [ABC/name for name in ['benchmarks/agent_supervisor/container_coding/terminal_semantic_context_transport.py',
  'ipfs_accelerate_py/agent_supervisor/context/context_compiler.py',
  'ipfs_accelerate_py/agent_supervisor/context/context_contracts.py','ipfs_accelerate_py/agent_supervisor/planning/structural_codebase_context.py',
  'ipfs_accelerate_py/agent_supervisor/runtime/code_view_minification.py',
  'benchmarks/agent_supervisor/container_coding/terminal_native_semantic_capsule.py',
  'benchmarks/agent_supervisor/container_coding/codebase_ir_metadata.py',
  'benchmarks/agent_supervisor/container_coding/terminal_codebase_supervisor_fixture.py']]
 paths += [DATASETS/name for name in ['logic/software_contracts/codebase_ir.py','logic/software_contracts/content.py',
  'logic/software_contracts/duckdb_ast_store.py','logic/software_contracts/duckdb_ingest.py',
  'logic/software_contracts/cache.py','logic/software_contracts/codebase_resources.py','duckdb_control/codebase_catalog.py',
  'logic/software_contracts/semantic_index/snapshot.py','logic/software_contracts/semantic_state/api.py',
  'logic/software_contracts/semantic_state/capsules.py','logic/software_contracts/semantic_state/models.py',
  'logic/software_contracts/semantic_state/bindings.py','logic/software_contracts/semantic_state/freshness.py']]
 from token_cost_review import BPE_ASSET,TOKENIZER_ROOT,IMPLEMENTATION
 paths += [BPE_ASSET,*[TOKENIZER_ROOT/name for name in IMPLEMENTATION]]
 return [pin(path) for path in paths]

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['test','run','cold','fault'],required=True)
 parser.add_argument('--label',required=True);parser.add_argument('--run',default='experiment-01')
 parser.add_argument('--fault-report',default='native-faults-01-fault-report.json');args=parser.parse_args()
 for name in [args.label,args.run,args.fault_report]:
  if not name or Path(name).name!=name or name in {'.','..'}:raise ValueError('local fresh attempt names required')
 before=selected();directory=ROOT/(args.label+'-frozen-sources');directory.mkdir(mode=0o700);retained=[]
 for index,entry in enumerate(before):
  body=read(Path(entry['path']),32*1024**2)
  if sha(body)!=entry['sha256']:raise ValueError('producer changed before copy')
  target=directory/(f'{index:03d}-'+Path(entry['path']).name)
  with target.open('xb') as stream:
   stream.write(body);stream.flush();os.fchmod(stream.fileno(),0o444);os.fsync(stream.fileno())
  retained.append({**entry,'retained_copy':str(target)})
 write(ROOT/(args.label+'-source-pins.json'),{'pins':before,'retained_copies':retained,
  'complete_transitive_loaded_code_closure':False})
 if args.kind=='test':command=['--module','pytest','-q','-p','no:cacheprovider',
  '--junitxml='+str(ROOT/(args.label+'.xml')),*TESTS]
 elif args.kind=='run':command=['packing_run.py','--output',str(ROOT/args.run)]
 elif args.kind=='cold':command=['packing_verify.py','--run',args.run,'--report',args.label+'-cold-report.json','--fault-report',args.fault_report]
 else:command=['packing_faults.py','--run',args.run,'--report',args.label+'-fault-report.json']
 started=time.monotonic();timed_out=False
 with (ROOT/(args.label+'-stdout.log')).open('xb') as stdout,(ROOT/(args.label+'-stderr.log')).open('xb') as stderr:
  process=subprocess.Popen([sys.executable,'-B',str(ROOT/'env_run.py'),*command],cwd=ROOT,stdout=stdout,stderr=stderr,start_new_session=True)
  try:code=process.wait(timeout=300)
  except subprocess.TimeoutExpired:
   timed_out=True;os.killpg(process.pid,signal.SIGKILL);code=process.wait(timeout=10)
 after=selected();report={'kind':args.kind,'selected_run':args.run,'exit_code':code,'timed_out':timed_out,'seconds':time.monotonic()-started,
  'selected_sources_unchanged':before==after,'qualified':code==0 and not timed_out and before==after,
  'outer_wall_seconds':300,'before':before,'after':after}
 if args.kind=='test' and (ROOT/(args.label+'.xml')).is_file():
  import xml.etree.ElementTree as ET
  suites=list(ET.fromstring(read(ROOT/(args.label+'.xml'))).iter('testsuite'))
  report['tests']={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
  report['qualified']=report['qualified'] and all(report['tests'][k]==0 for k in ['failures','errors','skipped'])
 write(ROOT/(args.label+'-process-report.json'),report)
 print(json.dumps({k:v for k,v in report.items() if k not in ['before','after']}))
 raise SystemExit(0 if report['qualified'] else 1)

if __name__=='__main__':main()
