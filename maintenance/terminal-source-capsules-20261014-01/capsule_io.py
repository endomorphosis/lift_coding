"""Read only the named sealed public inputs; never reopen a predecessor DB."""
import json
from pathlib import Path
from evidence_io import read,write,wire,sha,pin
ROOT=Path(__file__).resolve().parent
RICH=ROOT.parent/'terminal-typed-ir-training-20261014-01'
TYPED=ROOT.parent/'terminal-typed-ir-proof-index-20261014-01'
PRIOR=ROOT.parent/'terminal-codebase-ir-training-20261014-01'
ABC=ROOT.parent/'terminal-dispatch-evidence-20261014-01'/'checkout'
DATASETS=ROOT.parent/'terminal-compact-retrieval-20261011-01'/'pinned-dependencies-v10'/'datasets'/'ipfs_datasets_py'
FALSE={'proof_authority':False,'execution_authority':False,'completion_authority':False,
 'source_runtime_equivalence_proved':False,'source_model_equivalence_proved':False,
 'full_task_satisfaction':False,'provider_token_savings_measured':False,'official_terminal_bench_harness_executed':False,
 'native_full_supervisor_invoked':False,'asymptotic_optimizer_convergence_proved':False,
 'global_durable_budget':False,'neural_candidate_promoted':False}

def inputs():
 sealed={};pins=[]
 for root,expected in [(RICH,'c159e5b4eb9b8e93ad5452a81501523d8175a38beec5807e06681c3155e56edd'),
   (PRIOR,'204724395eaa15c1c224e84473fe89447cd0e15470abd507bba30116fdd8ae94')]:
  raw=read(root/'evidence-manifest.json',1024**2)
  if sha(raw)!=expected:raise ValueError('sealed predecessor inventory changed')
  sealed[root]={r['path']:r for r in json.loads(raw)['files']}
 def selected(root,name,maximum):
  entry=sealed[root][name];raw=read(root/name,maximum)
  if len(raw)!=entry['bytes'] or sha(raw)!=entry['sha256']:raise ValueError('named sealed public input changed')
  pins.append({'path':str(root/name),'bytes':len(raw),'sha256':sha(raw)});return raw
 corpus=json.loads(selected(RICH,'experiment-02/corpus-manifest.json',65536))
 old=json.loads(selected(RICH,'experiment-02/result.json',16*1024**2))
 status=json.loads(selected(RICH,'improvement-status-01.json',1024**2))
 bodies={};instructions={}
 for task in corpus['tasks']:
  for source in task['sources']:
   raw=selected(RICH,'experiment-02/source-repository/'+source['path'],8192)
   if sha(raw)!=source['sha256'] or len(raw)!=source['bytes']:raise ValueError('corpus source differs')
   bodies[source['path']]=raw
  source=task['instruction'];raw=selected(PRIOR,'experiment-05/captured-sources/'+source['path'],8192)
  if sha(raw)!=source['sha256'] or len(raw)!=source['bytes']:raise ValueError('complete public instruction differs')
  instructions[task['task_id']]=raw
 if len(bodies)!=5 or old['completed'] is not True or status['neural_candidate_promoted'] is not False:
  raise ValueError('complete public corpus and unpromoted learner required')
 return corpus,bodies,instructions,sorted(pins,key=lambda r:r['path'])
