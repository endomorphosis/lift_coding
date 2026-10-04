#!/usr/bin/env python3
"""Bounded recovery diagnostic on five existing constructed AF-018 goals.

This is runtime qualification, not the untouched 1,913-unit evaluation.
No source labels/checkpoints/final-test data are loaded. Model proof bodies
are untrusted: a small identifier grammar is checked before kernel checking.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / '.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/receipts/snapshots/AF-018/measure_assistance.py'
LEAN = Path('/home/barberb/.local/share/vericodegen-research-runtime/bin/lean')
SOLVERS = {'z3': ['/home/barberb/.local/bin/z3', '-in', '-smt2'], 'cvc5': ['/home/barberb/.local/bin/cvc5', '--lang=smt2']}
GOALS = [
 {'goal_id':'h.fol_identity','declaration':'theorem recovery_goal (U : Type) (P : U → Prop) : ∀ x, P x → P x', 'control_proof':'by\n  intro x h\n  exact h', 'expected_provable':True,
  'smt':'(set-logic UF)\n(declare-sort U 0)\n(declare-fun P (U) Bool)\n(assert (not (forall ((x U)) (=> (P x) (P x)))))\n(check-sat)\n','expected_solver_status':'unsat'},
 {'goal_id':'h.fol_protected_write','declaration':'theorem recovery_goal (Protected Approved Write : Prop) : (Protected ∧ ¬ Approved) → ¬ Write', 'control_proof':'by\n  intro h w\n  contradiction', 'expected_provable':False,
  'smt':'(set-logic QF_UF)\n(declare-const Protected Bool)\n(declare-const Approved Bool)\n(declare-const Write Bool)\n(assert (not (=> (and Protected (not Approved)) (not Write))))\n(check-sat)\n','expected_solver_status':'sat'},
 {'goal_id':'h.fol_add_zero','declaration':'theorem recovery_goal (U : Type) (add : U → U → U) (zero : U) : ∀ a, add a zero = a', 'control_proof':'by\n  intro a\n  rfl', 'expected_provable':False,
  'smt':'(set-logic UF)\n(declare-sort Nat 0)\n(declare-fun add (Nat Nat) Nat)\n(declare-const zero Nat)\n(assert (not (forall ((a Nat)) (= (add a zero) a))))\n(check-sat)\n','expected_solver_status':'sat'},
 {'goal_id':'h.unsupported_dependent','declaration':'theorem recovery_goal : ∀ {α : Type} (x : α), x = x', 'control_proof':'by\n  intro α x\n  rfl', 'expected_provable':True, 'smt':None},
 {'goal_id':'h.unsupported_higher_order','declaration':'theorem recovery_goal : ∀ (p : (Nat → Nat) → Prop), p id → p id', 'control_proof':'by\n  intro p h\n  exact h', 'expected_provable':True, 'smt':None},
]
# No imports, command syntax, arbitrary constants, metaprogramming, or I/O.
WORDS = set('by intro intros exact assumption rfl trivial constructor apply cases case have show from fun let in with first all_goals focus repeat skip done contradiction false elim False True And Or Not Eq Iff Nat Type Prop id left right simp simpa only at rename_i fail_if_success decide U P Protected Approved Write add zero α x a p h h1 h2 h3 h4 h5 hx ha hp hw hP hA hW hnot hProtected hApproved hWrite w this'.split())
FORBIDDEN = re.compile(r'\b(sorry|admit|sorryAx|axiom|constant|opaque|unsafe|import|open|set_option|theorem|def|instance|macro|syntax|elab|run_tac|native_decide|IO|System|Lean|eval|include|attribute)\b')

def sha(data):return hashlib.sha256(data).hexdigest()
def write(path, obj):path.write_text(json.dumps(obj, indent=2, ensure_ascii=False)+'\n')
def stamp():return datetime.now(timezone.utc).isoformat()

def limits():
 # Lean reserves more virtual address space than its resident working set.
 resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
 resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
 resource.setrlimit(resource.RLIMIT_FSIZE, (8*1024**2, 8*1024**2))
 resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def command(argv, cwd, stdin=None, seconds=20):
 start=time.monotonic()
 env={k:os.environ[k] for k in ['PATH','HOME','LANG'] if k in os.environ}
 env.update({'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','LEAN_NUM_THREADS':'1'})
 proc=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True,preexec_fn=limits)
 timeout=False
 try:
  stdout,stderr=proc.communicate(stdin,timeout=seconds)
 except subprocess.TimeoutExpired:
  timeout=True;os.killpg(proc.pid,signal.SIGKILL);stdout,stderr=proc.communicate()
 finally:
  try:os.killpg(proc.pid,signal.SIGKILL)
  except ProcessLookupError:pass
 return {'argv':argv,'returncode':proc.returncode,'timeout':timeout,'stdout':stdout,'stderr':stderr,'wall_seconds':time.monotonic()-start}

def proof_policy(body):
 if not isinstance(body,str) or len(body)>8000:return 'missing_or_oversized_body'
 if not body.strip().startswith('by'):return 'proof_body_must_start_by'
 if any(s in body for s in ['--','/-','-/','"','`','#','\\','\x00']):return 'forbidden_syntax'
 if FORBIDDEN.search(body):return 'forbidden_identifier'
 words=re.findall(r'[^\W\d]\w*',body,flags=re.UNICODE)
 unknown=set(words)-WORDS
 if unknown:return 'unknown_identifiers:'+','.join(sorted(unknown))
 if re.search(r'[^\w\s(){}\[\]:=,;.|<>+*\-→↔∀∃¬∧∨⟨⟩]',body):return 'unsupported_character'
 return None

def check_lean(goal,body,folder):
 rejection=proof_policy(body)
 if rejection:return {'status':'policy_rejected','reason':rejection,'accepted':False}
 source='set_option maxHeartbeats 100000\nset_option maxRecDepth 512\n'+goal['declaration']+' := '+body.strip()+'\n#print axioms recovery_goal\n'
 path=folder/'candidate.lean';path.write_text(source)
 result=command([str(LEAN),'-j1','-M1024',str(path)],folder)
 # These simple diagnostic proofs need no added or classical axioms.
 no_axioms="'recovery_goal' does not depend on any axioms" in result['stdout']
 accepted=result['returncode']==0 and no_axioms and 'sorry' not in result['stdout'].lower()
 rejected=result['returncode']==1 and 'error:' in result['stdout']
 return {**result,'source_sha256':sha(source.encode()),'accepted':accepted,'axiom_policy':'no axioms','status':'native_checked_proof' if accepted else ('timeout' if result['timeout'] else ('native_rejected' if rejected else 'checker_failure'))}

def parse_body(content):
 content=content.strip()
 # Retain only the first explicitly terminated generated turn. This is
 # framing removal, not proof repair. Never mine a thought/preamble for code.
 if '<|im_end|>' in content:
  content=content.split('<|im_end|>',1)[0].strip()
 if content=='ABSTAIN':return None
 match=re.fullmatch(r'```(?:lean4?|text)?\s*\n(.*?)\n```',content,re.S)
 return match.group(1).strip() if match else content

def model_call(endpoint,goal,folder,max_tokens,request_timeout):
 prompt=('Return only a Lean 4 proof body starting with by for the declaration below. '
 'Do not change the declaration or add premises. Do not use imports, sorry, admit, axioms, unsafe features, native_decide, or executable metaprogramming. '
 'Use only elementary core Lean tactics. If the statement is not provable from its explicit parameters, return exactly ABSTAIN. '
 'Names such as add and zero denote arbitrary parameters, not arithmetic operations.\n\n'+goal['declaration']+' :=')
 payload={'model':'leanstral_local','messages':[{'role':'user','content':prompt}],'temperature':0,'seed':104729,'max_tokens':max_tokens,'stream':False}
 write(folder/'request.json',payload)
 req=urllib.request.Request(endpoint.rstrip('/')+'/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
 start=time.monotonic()
 try:
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  with opener.open(req,timeout=request_timeout) as response:
   raw=response.read(2_000_001)
  if len(raw)>2_000_000:raise ValueError('response exceeds 2 MB bound')
  (folder/'response.json').write_bytes(raw)
  result=json.loads(raw)
  if not isinstance(result,dict) or not isinstance(result.get('choices'),list) or not result['choices']:
   raise ValueError('malformed chat response')
  message=result['choices'][0]['message']
  if not isinstance(message,dict) or not isinstance(message.get('content'),str):
   raise ValueError('missing string response content')
  content=message['content']
  body=parse_body(content)
  check={'status':'abstained','accepted':False} if body is None else check_lean(goal,body,folder)
  return {'status':'response_received','response_model':result.get('model'),'usage':result.get('usage'),'finish_reason':result['choices'][0].get('finish_reason'),'wall_seconds':time.monotonic()-start,'checker':check}
 except (OSError,ValueError,KeyError,IndexError,TypeError,AttributeError,urllib.error.URLError) as exc:
  return {'status':'request_failed','error':type(exc).__name__+': '+str(exc),'wall_seconds':time.monotonic()-start,'checker':{'accepted':False,'status':'not_checked'}}

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',required=True,type=Path)
 parser.add_argument('--endpoint',default=os.environ.get('LEANSTRAL_BASE_URL'))
 parser.add_argument('--native-only',action='store_true')
 parser.add_argument('--max-tokens',type=int,default=256)
 parser.add_argument('--request-timeout',type=float,default=45)
 args=parser.parse_args()
 if not args.native_only:
  parsed=urllib.parse.urlparse(args.endpoint or '')
  if parsed.scheme!='http' or parsed.hostname not in {'127.0.0.1','localhost','::1'}:parser.error('a loopback HTTP endpoint is required')
  endpoint=args.endpoint.rstrip('/')
  if not endpoint.endswith('/v1'):endpoint+='/v1'
 if not (1<=args.max_tokens<=512 and 0<args.request_timeout<=90):parser.error('request budget out of range')
 args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=False)
 hist=HISTORICAL.read_bytes();tree=ast.parse(hist)
 original=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ASSIST_GOALS' for t in n.targets))
 assert [g['goal_id'] for g in original]==[g['goal_id'] for g in GOALS]
 manifest={'schema':'autoformalization-recovery-constructed-probe/v1','created_at':stamp(),'scope':'five existing constructed assistance goals; runtime qualification only','final_test_accessed':False,'historical_inputs_sha256':sha(hist),'original_goals':original,'fixed_goals':GOALS,'mapping_notes':['The protected-write statement has no policy premise and is a negative control.','The original SMT add/zero are uninterpreted; the Lean goal preserves that fact using arbitrary U, add, zero.','Dependent/higher-order unsupported flags refer to the historical Hammer translator, not Lean.'],'max_tokens':args.max_tokens,'request_timeout_seconds':args.request_timeout,'lean':str(LEAN),'script_sha256':sha(Path(__file__).read_bytes())}
 write(args.output/'frozen_manifest.json',manifest)
 versions={'lean':command([str(LEAN),'-j1','--version'],args.output,seconds=5)}
 for name,argv in SOLVERS.items():versions[name]=command([argv[0],'--version'],args.output,seconds=5)
 write(args.output/'runtime.json',versions)
 rows=[]
 for index,goal in enumerate(GOALS):
  folder=args.output/f'{index+1:02d}-{goal["goal_id"]}';folder.mkdir()
  control=folder/'native_control';control.mkdir()
  row={'goal_id':goal['goal_id'],'expected_provable':goal['expected_provable'],'native_control':check_lean(goal,goal['control_proof'],control),'solvers':{}}
  if goal['smt']:
   (folder/'goal.smt2').write_text(goal['smt'])
   for name,argv in SOLVERS.items():row['solvers'][name]=command(argv,folder,stdin=goal['smt'],seconds=10)
  write(folder/'result.json',row);rows.append(row)
 native_pass=all(r['native_control']['accepted'] if r['expected_provable'] else r['native_control']['status']=='native_rejected' for r in rows)
 native_pass=native_pass and all(v['returncode']==0 for v in versions.values())
 native_pass=native_pass and all(c['returncode']==0 and c['stdout'].strip()==g['expected_solver_status'] for g,r in zip(GOALS,rows) for c in r['solvers'].values())
 if not args.native_only and native_pass:
  for index,(goal,row) in enumerate(zip(GOALS,rows)):
   folder=args.output/f'{index+1:02d}-{goal["goal_id"]}'
   model_folder=folder/'model';model_folder.mkdir()
   row['model']=model_call(endpoint,goal,model_folder,args.max_tokens,args.request_timeout)
   write(folder/'result.json',row)
   with (args.output/'results.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
   print(json.dumps({'goal_id':goal['goal_id'],'model':row['model']['status'],'model_proof_accepted':row['model']['checker']['accepted']}),flush=True)
   if row['model']['status']=='request_failed':break
 summary={'completed_at':stamp(),'scope':manifest['scope'],'final_test_accessed':False,'planned_goals':5,'completed_native_goals':len(rows),'native_controls_passed':native_pass,'model_calls':sum('model' in r for r in rows),'model_responses':sum(r.get('model',{}).get('status')=='response_received' for r in rows),'model_native_accepted_proofs':sum(r.get('model',{}).get('checker',{}).get('accepted',False) for r in rows),'model_abstentions':sum(r.get('model',{}).get('checker',{}).get('status')=='abstained' for r in rows),'native_positive_controls_accepted':sum(r['expected_provable'] and r['native_control']['accepted'] for r in rows),'native_negative_controls_rejected':sum(not r['expected_provable'] and r['native_control']['status']=='native_rejected' for r in rows),'solver_observations':{r['goal_id']:{n:c['stdout'].strip() for n,c in r['solvers'].items()} for r in rows},'does_not_fill_primary_manuscript_cells':True}
 checker_counts=Counter(r['model']['checker']['status'] for r in rows if 'model' in r)
 summary['model_checker_statuses']=dict(checker_counts)
 summary['completed_model_dispositions']=sum(checker_counts[s] for s in ['abstained','policy_rejected','native_rejected','native_checked_proof'])
 write(args.output/'summary.json',summary)
 print(json.dumps(summary,indent=2),flush=True)
 return 0 if native_pass and (args.native_only or summary['model_responses']==5 and summary['completed_model_dispositions']==5) else 1
if __name__=='__main__':raise SystemExit(main())
