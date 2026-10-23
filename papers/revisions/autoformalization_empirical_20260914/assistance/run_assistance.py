#!/usr/bin/env python3
"""Prospectively frozen small proof-assistance evaluation; bounded, local only.

No natural final-test records, learning labels, target proofs, or checkpoints
are sent to the model. Solver judgments are distinct from Lean kernel proofs.
"""
from __future__ import annotations
import argparse, ast, hashlib, importlib.util, json, os, random, re, resource, statistics, subprocess, time, urllib.request
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SPEC=importlib.util.spec_from_file_location('bounded_recovery',ROOT/'scripts/autoformalization_recovery_probe.py')
NATIVE=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(NATIVE)
SEED=20260914
POLICY_ID='fixed-declaration-complete-turn-core-Lean/v1'
BASELINE='by\n  first | (rfl; done) | (trivial; done) | (decide; done) | (omega; done) | (simp_all; done) | (assumption; done)'
FORBIDDEN=re.compile(r'\b(sorry|admit|sorryAx|axiom|constant|opaque|unsafe|import|open|set_option|theorem|lemma|def|instance|macro|syntax|elab|run_tac|run_elab|native_decide|unsafeCast|IO|System|Lean|eval|include|attribute|initialize|local|section|namespace|end|sorryAx|ofReduceBool)\b')
TACTICS=set('by intro intros exact assumption rfl trivial constructor apply cases case have show from fun let in with first all_goals focus repeat skip done contradiction False True And Or Not Eq Iff Nat Int Type Prop id left right simp simpa simp_all only at rename_i fail_if_success decide omega rcases obtain subst specialize refine revert generalize induction change classical exists clear rcases congr ext intro1 exacts rintro match'.split())
SAFE_PREFIXES={'Nat','Int','Eq','And','Or','Not','False','True','Iff','Exists'}
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def now():return datetime.now(timezone.utc).isoformat()
def wrap_smt(decls,formula,logic='UF'):return f'(set-logic {logic})\n{decls}\n(assert (not {formula}))\n(check-sat)\n'
def propdecl(names):return '\n'.join(f'(declare-const {n} Bool)' for n in names)
def make_goals():
 rows=[]
 for k in range(4):
  c=3+3*k
  for valid in [True,False]:
   suffix='valid' if valid else 'invalid'
   def add(family,decl,proof,smt,witness,fragment='first_order'):
    gid=f'new.{family}.{k}.{suffix}'
    if family not in {'premise_chain','polarity','integer_code','natural_order'}:
     mapping={n:f'{n}{k}' for n in ['U','P','Q','x','y','step','safe','p','f','g','α']}
     for old,new in mapping.items():
      decl=re.sub(r'(?<![\w])'+re.escape(old)+r'(?![\w])',new,decl)
      proof=re.sub(r'(?<![\w])'+re.escape(old)+r'(?![\w])',new,proof)
     if smt:
      for old,new in mapping.items():smt=re.sub(r'(?<![\w])'+re.escape(old)+r'(?![\w])',new,smt)
    rows.append(dict(goal_id=gid,family=family,pair_id=f'{family}.{k}',split='prospective_constructed_test',instance_seed=SEED+k,expected_provable=valid,declaration='theorem empirical_goal '+decl,control_proof=proof if valid else 'by\n  intros\n  first | (rfl; done) | (assumption; done)',smt=smt,expected_solver_status=('unsat' if valid else 'sat') if smt else None,semantic_label_basis=witness,fragment=fragment))
   names=[f'P{k}',f'Q{k}',f'R{k}',f'S{k}'];p,q,r,s=names
   target=r if valid else s
   add('premise_chain',f'({p} {q} {r} {s} : Prop) : ({p} → {q}) → ({q} → {r}) → {p} → {target}', 'by\n  intro h1 h2 h3\n  exact h2 (h1 h3)',wrap_smt(propdecl(names),f'(=> (=> {p} {q}) (=> (=> {q} {r}) (=> {p} {target})))','QF_UF'),'Composition of explicit implications; invalid witness P=Q=R=true,S=false.')
   consequent=f'¬ ({p} ∧ {q})' if valid else f'¬ {r}'
   smtcon=f'(not (and {p} {q}))' if valid else f'(not {r})'
   add('polarity',f'({p} {q} {r} : Prop) : ({p} ∧ ¬ {q}) → {consequent}','by\n  intro h1 h2\n  exact h1.2 h2.2',wrap_smt(propdecl([p,q,r]),f'(=> (and {p} (not {q})) {smtcon})','QF_UF'),'Conjunctive incompatibility; invalid witness P=true,Q=false,R=true.')
   target='P y' if valid else 'Q y';smtarget='(P y)' if valid else '(Q y)'
   add('equality_transport','(U : Type) (P Q : U → Prop) (x y : U) : x = y → P x → '+target,'by\n  intro h1 h2\n  exact h1 ▸ h2',wrap_smt('(declare-sort U 0)\n(declare-fun P (U) Bool)\n(declare-fun Q (U) Bool)\n(declare-const x U)\n(declare-const y U)',f'(=> (= x y) (=> (P x) {smtarget}))'),'Equality substitution preserves predicate identity; invalid singleton witness P=true,Q=false.')
   rhs='n' if valid else 'n + 1'
   add('integer_code',f'(n : Int) : (n + {c}) - {c} = {rhs}','by\n  omega',wrap_smt('(declare-const n Int)',f'(= (- (+ n {c}) {c}) '+('n)' if valid else '(+ n 1))'),'QF_LIA'),'Exact arithmetic identity of increment/decrement code; invalid witness n=0.')
   goal=f'n ≤ n + {c}' if valid else f'n + {c} ≤ n'
   formula=f'(<= n (+ n {c}))' if valid else f'(<= (+ n {c}) n)'
   add('natural_order',f'(n : Nat) : {goal}','by\n  omega',wrap_smt('(declare-const n Int)\n(assert (>= n 0))',formula,'QF_LIA'),'Positive increments preserve/increase natural state; invalid witness n=0.')
   tar='safe (step x)' if valid else 'safe (step (step x))';smttar='(safe (step x))' if valid else '(safe (step (step x)))'
   add('finite_next_state',f'(U : Type) (step : U → U) (safe : U → Prop) (x : U) : (safe x → safe (step x)) → safe x → {tar}','by\n  intro h1 h2\n  exact h1 h2',wrap_smt('(declare-sort U 0)\n(declare-fun step (U) U)\n(declare-fun safe (U) Bool)\n(declare-const x U)',f'(=> (=> (safe x) (safe (step x))) (=> (safe x) {smttar}))'),'Explicit single-step preservation only; invalid witness three states x->y->z, safe={x,y}. No full temporal logic claim.')
   tar='x = x' if valid else 'x = y'
   add('dependent_type',f': ∀ {{α : Type}} (x y : α), {tar}','by\n  intro α x y\n  rfl',None,'Reflexivity across a type parameter; invalid witness alpha=Bool,x=false,y=true. Typed Hammer translation rejects dependent sorts.','dependent_type')
   tar='p f' if valid else 'p g'
   add('higher_order',f': ∀ (p : (Nat → Nat) → Prop) (f g : Nat → Nat), p f → {tar}','by\n  intro p f g h\n  exact h',None,'Propositional identity at function argument; invalid witness p(h)=(h(0)=0),f=constant0,g=constant1. Typed Hammer translation rejects function-valued arguments.','higher_order')
 # Order is fixed by ID hash, not labels or observed outcomes.
 return sorted(rows,key=lambda g:sha(f'{SEED}:{g["goal_id"]}'.encode()))
def check_policy(goal,body):
 if not isinstance(body,str) or len(body)>16000:return 'missing_or_oversized_body'
 if not re.match(r'^by\b',body.strip()):return 'proof_body_must_start_by'
 if any(s in body for s in ['--','/-','-/','"','`','#','\\','\x00','@']):return 'forbidden_syntax'
 if FORBIDDEN.search(body):return 'forbidden_identifier'
 declnames=set(re.findall(r'[^\W\d]\w*',goal['declaration']))
 for word in re.findall(r'[^\W\d]\w*(?:\.[^\W\d]\w*)*',body):
  if word in TACTICS or word in declnames:continue
  if word.split('.')[0] in SAFE_PREFIXES:continue
  if re.fullmatch(r'(?:h\w*|[a-z]|this|ih|ih\w*|α|β|x\w*|y\w*)',word):continue
  return 'unknown_identifier:'+word
 if re.search(r'[^\w\s(){}\[\]:=,;.|<>+*\-/→↔∀∃¬∧∨⟨⟩≤≥≠▸·!?]',body):return 'unsupported_character'
 return None
def check_lean(goal,body,folder):
 folder.mkdir(parents=True,exist_ok=True)
 rejection=check_policy(goal,body)
 if rejection:return dict(status='policy_rejected',reason=rejection,accepted=False)
 source='set_option maxHeartbeats 200000\nset_option maxRecDepth 512\n'+goal['declaration']+' := '+body.strip()+'\n#print axioms empirical_goal\n'
 path=folder/'candidate.lean';path.write_text(source)
 result=NATIVE.command([str(NATIVE.LEAN),'-j1','-M1024',str(path)],folder,seconds=10)
 m=re.search(r"'empirical_goal' depends on axioms: \[(.*?)\]",result['stdout'],re.S)
 axioms=[] if "'empirical_goal' does not depend on any axioms" in result['stdout'] else (re.findall(r'[\w.]+',m.group(1)) if m else None)
 accepted=result['returncode']==0 and axioms is not None and set(axioms)<={'propext','Classical.choice','Quot.sound'} and 'sorry' not in result['stdout'].lower()
 status='native_checked_proof' if accepted else 'timeout' if result['timeout'] else 'native_rejected' if result['returncode']==1 and 'error:' in result['stdout'] else 'checker_failure'
 return dict(result,source_sha256=sha(source.encode()),accepted=accepted,status=status,axioms=axioms)
def extract(choice):
 if choice.get('finish_reason')!='stop':return None,'incomplete_generation'
 message=choice.get('message',{});content=message.get('content')
 if not isinstance(content,str):return None,'malformed_content'
 content=content.strip()
 if any(t in content for t in ['<|im_start|>','<|im_end|>','[INST]','[/INST]','[THINK]','[/THINK]','<think>','</think>','</s>']):return None,'unexpected_transport_or_reasoning'
 if content=='ABSTAIN':return None,'abstained'
 m=re.fullmatch(r'```(?:lean4?)?\s*\n(.*?)\n```',content,re.S)
 return (m.group(1).strip() if m else content),'candidate'
def prompt_for(g):
 return ('Return only a Lean 4 proof body starting with by, or exactly ABSTAIN if this statement is not provable from its explicit parameters. '
 'Use Lean core only, no imports or Mathlib. Do not change the statement or add premises. '
 'Do not use sorry, admit, axioms, native_decide, unsafe features, executable metaprogramming, comments, or explanations. '
 'Arbitrary predicate/function parameters have no hidden axioms; one-step assumptions do not imply later steps.\n\n'+g['declaration']+' :=')
def request(endpoint,payload,folder):
 write(folder/'request.json',payload);start=time.monotonic()
 try:
  req=urllib.request.Request(endpoint.rstrip('/')+'/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  with opener.open(req,timeout=60) as reply:b=reply.read(2_000_001)
  if len(b)>2_000_000:raise ValueError('oversized response')
  (folder/'response.json').write_bytes(b);d=json.loads(b)
  return d,dict(status='response_received',wall_seconds=time.monotonic()-start,usage=d.get('usage'),response_model=d.get('model'))
 except Exception as e:return None,dict(status='request_failed',wall_seconds=time.monotonic()-start,error=f'{type(e).__name__}: {e}')
def model_call(endpoint,g,folder):
 folder.mkdir(parents=True,exist_ok=False)
 payload=dict(model='leanstral_local',messages=[dict(role='user',content=prompt_for(g))],temperature=0,seed=SEED,max_tokens=1024,stream=False,reasoning_effort='none',stop=['</s>'])
 data,result=request(endpoint,payload,folder)
 if data is None:return dict(result,checker=dict(status='not_checked',accepted=False))
 choice=data['choices'][0];body,status=extract(choice)
 checker=dict(status=status,accepted=False)
 if status=='candidate':
  (folder/'extracted.txt').write_text(body);checker=check_lean(g,body,folder)
 return dict(result,finish_reason=choice.get('finish_reason'),framing_status=status,checker=checker)
def freeze():
 out=HERE/'frozen_protocol.json'
 if out.exists():raise RuntimeError('Existing freeze must remain immutable')
 goals=make_goals()
 # Copy prior constructed goals to empirical declaration solely for qualification.
 dev=[dict(g,declaration=g['declaration'].replace('recovery_goal','empirical_goal'),family='historical_qualification',split='historical_qualification') for g in NATIVE.GOALS]
 manifest=dict(schema='autoformalization-native-assistance-empirical/v1',created_at=now(),scope='Prospective constructed proof assistance, not natural-language semantic-fidelity gold',natural_final_test_accessed=False,seed=SEED,goals=goals,qualification_goals=dev,planned_calls=len(goals)+len(dev),new_family_count=8,new_valid_count=32,new_invalid_count=32,pair_count=32,extraction_policy=POLICY_ID,policy='Only complete stop-terminated content; optional entire Lean fence; no thought/turn mining, theorem editing, semantic retries, or proof repair; resumable shards never repeat a completed model request. All accepted proofs checked against exact fixed declaration with only standard Lean axioms.',budget=dict(max_tokens=1024,request_seconds=60,client_soft_stop_seconds=490,job_wall_seconds=900,startup_seconds=360,cpus=4,memory_gib=90),baseline=BASELINE,hammer='Both Z3 and CVC5 must return unsat on the frozen corresponding first-order formula; reconstruct with fixed Lean core tactics. SMT sat is a counterexample, unsupported remains unsupported. No external-solver output counts as a Lean proof.',independence='Four numeric/name variants within a semantic family are not independent families. No natural-source human-label claims; model unseen controls frozen before requests, historic five excluded from effect estimates.',scripts_sha256={p.name:sha(p.read_bytes()) for p in [Path(__file__),HERE/'leanstral_v15.jinja',ROOT/'scripts/run_leanstral_ephemeral.py']})
 write(out,manifest);print('Frozen',len(goals),'new goals +',len(dev),'qualification goals')
def native():
 manifest=json.loads((HERE/'frozen_protocol.json').read_text());out=HERE/'native';out.mkdir(exist_ok=False)
 versions={name:NATIVE.command([str(exe),'--version'],out,seconds=5) for name,exe in [('lean',NATIVE.LEAN),('z3',NATIVE.SOLVERS['z3'][0]),('cvc5',NATIVE.SOLVERS['cvc5'][0])]};write(out/'runtime.json',versions)
 rows=[]
 for g in manifest['qualification_goals']+manifest['goals']:
  folder=out/g['goal_id'];folder.mkdir()
  row=dict(goal_id=g['goal_id'],family=g['family'],split=g['split'],expected_provable=g['expected_provable'])
  row['oracle_control']=check_lean(g,g['control_proof'],folder/'oracle_control')
  row['baseline']=check_lean(g,BASELINE,folder/'baseline')
  row['solvers']={}
  if g['smt']:
   (folder/'goal.smt2').write_text(g['smt'])
   for name,argv in NATIVE.SOLVERS.items():row['solvers'][name]=NATIVE.command(argv,folder,stdin=g['smt'],seconds=5)
   statuses={v['stdout'].strip() for v in row['solvers'].values() if v['returncode']==0}
   solver_ok=all(v['returncode']==0 and v['stdout'].strip()==g['expected_solver_status'] for v in row['solvers'].values())
   row['solver_semantics_match']=solver_ok
   row['hammer']=check_lean(g,BASELINE,folder/'hammer') if statuses=={'unsat'} else dict(status='counterexample' if statuses=={'sat'} else 'solver_failure',accepted=False)
  else:row['hammer']=dict(status='unsupported',accepted=False,reason=g.get('fragment','typed_fragment'))
  write(folder/'result.json',row);rows.append(row)
  with (out/'results.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  print(g['goal_id'],row['oracle_control']['status'],row['baseline']['status'],row['hammer']['status'],flush=True)
 controls_ok=all(r['oracle_control']['accepted']==r['expected_provable'] for r in rows) and all(r.get('solver_semantics_match',True) for r in rows)
 write(out/'summary.json',dict(completed_at=now(),count=len(rows),controls_pass=controls_ok,baseline_counts=dict(Counter(r['baseline']['status'] for r in rows if r['split']=='prospective_constructed_test')),hammer_counts=dict(Counter(r['hammer']['status'] for r in rows if r['split']=='prospective_constructed_test'))))
 if not controls_ok:raise RuntimeError('Native semantic qualification failed; preserve all receipts and fix protocol before model calls')
def model_run():
 manifest=json.loads((HERE/'frozen_protocol.json').read_text())
 assert json.loads((HERE/'native/summary.json').read_text())['controls_pass']
 assert sha(Path(__file__).read_bytes())==manifest['scripts_sha256']['run_assistance.py']
 assert sha((HERE/'leanstral_v15.jinja').read_bytes())==manifest['scripts_sha256']['leanstral_v15.jinja']
 endpoint=os.environ['LEANSTRAL_BASE_URL'];out=HERE/'model';out.mkdir(exist_ok=True)
 start=time.monotonic()
 existing={r['goal_id']:r for r in map(json.loads,(out/'results.jsonl').read_text().splitlines())} if (out/'results.jsonl').exists() else {}
 if len(existing)>=5:
  assert json.loads((out/'qualification.json').read_text())['passed'], 'Prior qualification failed; no fresh goals allowed'
 jobid=now().replace(':','-');jobdir=out/('job-'+jobid);jobdir.mkdir()
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for route in ['/props','/v1/models']:
  with opener.open(endpoint.removesuffix('/v1')+route,timeout=5) as response:(jobdir/(route.replace('/','_')+'.json')).write_bytes(response.read(2_000_000))
 # Confirm serving applied the actual pinned v15 framing on a non-evaluation text.
 req=urllib.request.Request(endpoint.removesuffix('/v1')+'/apply-template',data=json.dumps(dict(messages=[dict(role='user',content='template qualification')])).encode(),headers={'Content-Type':'application/json'})
 with opener.open(req,timeout=5) as response:applied=json.loads(response.read())
 write(jobdir/'applied_template.json',applied)
 expected='<s>[MODEL_SETTINGS]{"reasoning_effort": "none"}[/MODEL_SETTINGS][INST]template qualification[/INST]'
 assert applied['prompt'] in {expected,expected.removeprefix('<s>')},applied
 token_req=urllib.request.Request(endpoint.removesuffix('/v1')+'/tokenize',data=json.dumps(dict(content=applied['prompt'],add_special=True,parse_special=True)).encode(),headers={'Content-Type':'application/json'})
 with opener.open(token_req,timeout=5) as response:tokenized=json.loads(response.read())
 write(jobdir/'template_tokens.json',tokenized)
 tokens=tokenized['tokens']
 assert tokens[0]==1 and tokens.count(1)==1 and 36 in tokens and 37 in tokens and 3 in tokens and tokens[-1]==4,tokenized
 rows=[]
 for g in manifest['qualification_goals']+manifest['goals']:
  if g['goal_id'] in existing:
   rows.append(existing[g['goal_id']]);continue
  if time.monotonic()-start>490:
   write(jobdir/'shard_stop.json',dict(reason='predeclared490secondclientbudget',completed_new_rows=len(rows),elapsed_seconds=time.monotonic()-start));break
  row=dict(goal_id=g['goal_id'],family=g['family'],split=g['split'],expected_provable=g['expected_provable'],model=model_call(endpoint,g,out/g['goal_id']))
  write(out/g['goal_id']/'result.json',row);rows.append(row)
  with (out/'results.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  print(json.dumps(dict(goal_id=g['goal_id'],status=row['model']['checker']['status'],seconds=row['model']['wall_seconds'])),flush=True)
  if len(rows)==len(manifest['qualification_goals']):
   # Qualification must have 5 complete correctly framed responses and no false proof.
   qualified=all(r['model']['status']=='response_received' and r['model'].get('finish_reason')=='stop' and r['model'].get('framing_status') in {'candidate','abstained'} and not (not r['expected_provable'] and r['model']['checker']['accepted']) for r in rows)
   write(out/'qualification.json',dict(passed=qualified,rows=len(rows),accepted=sum(r['model']['checker']['accepted'] for r in rows)))
   if not qualified:raise RuntimeError('Serving qualification failed: no new pool outputs requested')
 summarize()
def summarize():
 manifest=json.loads((HERE/'frozen_protocol.json').read_text());base={r['goal_id']:r for r in map(json.loads,(HERE/'native/results.jsonl').read_text().splitlines())}
 p=HERE/'model/results.jsonl';models={r['goal_id']:r for r in map(json.loads,p.read_text().splitlines())} if p.exists() else {}
 rows=[]
 for g in manifest['goals']:
  b=base[g['goal_id']];m=models.get(g['goal_id'],{}).get('model',dict(status='not_run',checker=dict(status='not_run',accepted=False)))
  rows.append(dict(goal_id=g['goal_id'],family=g['family'],pair_id=g['pair_id'],expected_provable=g['expected_provable'],baseline=b['baseline'],hammer=b['hammer'],model=m))
 summary=dict(completed_at=now(),scope=manifest['scope'],natural_final_test_accessed=False,planned_new_goals=64,valid_goals=32,invalid_goals=32,families=8,model_calls=sum(r['model']['status']!='not_run' for r in rows),model_responses=sum(r['model']['status']=='response_received' for r in rows),model_wall_seconds=sum(r['model'].get('wall_seconds',0) for r in rows),model_prompt_tokens=sum(r['model'].get('usage',{}).get('prompt_tokens',0) for r in rows),model_completion_tokens=sum(r['model'].get('usage',{}).get('completion_tokens',0) for r in rows),arms={})
 for arm in ['baseline','hammer','model']:
  get=lambda r:r['model']['checker'] if arm=='model' else r[arm]
  summary['arms'][arm]=dict(valid_native_accepted=sum(r['expected_provable'] and get(r)['accepted'] for r in rows),invalid_native_accepted=sum(not r['expected_provable'] and get(r)['accepted'] for r in rows),statuses=dict(Counter(get(r)['status'] for r in rows)),by_family={f:dict(valid_native_accepted=sum(r['family']==f and r['expected_provable'] and get(r)['accepted'] for r in rows),valid_denominator=4,invalid_native_accepted=sum(r['family']==f and not r['expected_provable'] and get(r)['accepted'] for r in rows),invalid_denominator=4) for f in sorted({r['family'] for r in rows})})
 families=sorted({r['family'] for r in rows}); rng=random.Random(SEED)
 bootstrap=[]
 for _ in range(2000):
  sampled=[rng.choice(families) for _ in families]
  sample=[r for f in sampled for r in rows if r['family']==f and r['expected_provable']]
  bootstrap.append(sum(int(r['model']['checker']['accepted'])-int(r['baseline']['accepted']) for r in sample)/len(sample))
 bootstrap.sort();summary['model_minus_baseline_valid_family_bootstrap']=dict(draws=2000,seed=SEED,point=sum(int(r['model']['checker']['accepted'])-int(r['baseline']['accepted']) for r in rows if r['expected_provable'])/32,percentile95=[bootstrap[49],bootstrap[1949]],cluster='semantic_family')
 write(HERE/'summary.json',summary);write(HERE/'comparison.json',rows);print(json.dumps(summary,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','native','model','summarize']);a=p.parse_args();{'freeze':freeze,'native':native,'model':model_run,'summarize':summarize}[a.mode]()
