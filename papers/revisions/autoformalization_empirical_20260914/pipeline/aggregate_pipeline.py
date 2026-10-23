#!/usr/bin/env python3
"""Aggregate complete frozen native cohorts; no candidate tuning or missing zeros."""
from pathlib import Path
import collections,hashlib,json,random,statistics
HERE=Path(__file__).resolve().parent
def read(p):return [json.loads(l) for l in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def percentile(x,p):
 x=sorted(x);i=(len(x)-1)*p;lo=int(i);hi=min(lo+1,len(x)-1)
 return x[lo]+(i-lo)*(x[hi]-x[lo])
def cluster_interval(values,meta):
 groups=collections.defaultdict(list)
 for rid,v in values.items():groups[meta[rid]['component_id']].append(float(v))
 sums=[sum(x) for x in groups.values()];counts=[len(x) for x in groups.values()]
 rng=random.Random(104729);samples=[]
 for _ in range(10000):
  ix=[rng.randrange(len(sums)) for _ in sums]
  samples.append(sum(sums[i] for i in ix)/sum(counts[i] for i in ix))
 return {'mean':sum(values.values())/len(values),'interval95':[percentile(samples,.025),percentile(samples,.975)],
  'draws':10000,'seed':104729,'clusters':len(groups),'max_cluster_units':max(counts)}
def valid(row):return row.get('compile_status')=='measured' and all(v['passed'] for v in row.get('checks',{}).values())
def nonempty(row):return valid(row) and row.get('formula_count',0)>0
def cstats(rows):
 passed=[r for r in rows if valid(r)];cyc=[r for r in rows if r.get('cycle',{}).get('status')=='measured']
 return {'units':len(rows),'compile_measured':sum(r.get('compile_status')=='measured' for r in rows),
  'compile_statuses':dict(collections.Counter(r.get('compile_status',r['status']) for r in rows)),
  'schema_and_provenance_pass':len(passed),'nonempty_eligible':sum(nonempty(r) for r in rows),
  'formula_count':sum(r.get('formula_count',0) for r in passed),
  'deontic_nonempty':sum(r.get('family_counts',{}).get('deontic',0)>0 for r in passed),
  'family_formula_counts':dict(sum((collections.Counter(r.get('family_counts',{})) for r in passed),collections.Counter())),
  'cycle_statuses':dict(collections.Counter(r.get('cycle',{}).get('status','not_attempted') for r in rows)),
  'cycle_measured':len(cyc),'cycle_exact_nonempty':sum(nonempty(r) and r.get('cycle',{}).get('exact_semantic_field_multiset',False) for r in rows),
  'cycle_formula_recall_mean':statistics.mean(r['cycle']['formula_multiset_recall'] for r in cyc) if cyc else None,
  'cycle_formula_precision_mean':statistics.mean(r['cycle']['formula_multiset_precision'] for r in cyc) if cyc else None,
  'sum_record_wall_seconds':sum(r['wall_seconds'] for r in rows),
  'sum_compile_wall_seconds':sum(r.get('compile_seconds',0) for r in rows),
  'record_seconds_median':statistics.median(r['wall_seconds'] for r in rows),
  'record_seconds_p95':percentile([r['wall_seconds'] for r in rows],.95),
  'spacy_blank_fallback_units':sum(r.get('spacy_blank_fallback',False) for r in rows),
  'source_truncated_units':sum(r.get('source_truncated',False) for r in rows)}
def main():
 sources=read(HERE/'final.sources.jsonl');meta={r['record_id']:r for r in sources};assert len(meta)==1913
 c=read(HERE/'final_C.jsonl');t=read(HERE/'final_T5.jsonl');b=read(HERE/'final_B.jsonl')
 for rows in [c,t,b]:assert len(rows)==1913 and {r['record_id'] for r in rows}==set(meta)
 cb={r['record_id']:r for r in c};tb={r['record_id']:r for r in t}
 paired=[]
 for rid in meta:
  x,y=cb[rid],tb[rid];xs=x.get('canonical_ir',{}).get('formulas',[]);ys=y.get('canonical_ir',{}).get('formulas',[])
  def semantics(fs):return [{k:f[k] for k in ['operator','predicate','conditions','exceptions']} for f in fs]
  changed=semantics(xs)!=semantics(ys)
  paired.append({'record_id':rid,'both_compiled':x.get('compile_status')==y.get('compile_status')=='measured',
   'semantic_fields_changed':changed,'schema_provenance_regression':valid(x) and not valid(y),
   'schema_provenance_gain':not valid(x) and valid(y),
   'exception_roles_before':sum(f['predicate'].get('role')=='exception' for f in xs),
   'exception_roles_after':sum(f['predicate'].get('role')=='exception' for f in ys),
   'governing_predicate_changes':sum(a['predicate']!=z['predicate'] for a,z in zip(xs,ys) if a['operator']['family']!='conditional_normative') if len(xs)==len(ys) else None,
   'formula_count_delta':len(ys)-len(xs),
   'clause_fields_changed':[(f['conditions'],f['exceptions']) for f in xs]!=[(f['conditions'],f['exceptions']) for f in ys],
   'cycle_exact_delta':int(nonempty(y) and y.get('cycle',{}).get('exact_semantic_field_multiset',False))-int(nonempty(x) and x.get('cycle',{}).get('exact_semantic_field_multiset',False))})
 out={'population':{'units':1913,'components':20,'domain_counts':dict(collections.Counter(r['family'] for r in sources)),
  'component_unit_counts':sorted(collections.Counter(r['component_id'] for r in sources).values(),reverse=True),
  'prefix_truncated_units':sum(len(r['text'])>4096 for r in sources)},'C':cstats(c),'T5':cstats(t),
  'B':{'units':1913,'statuses':dict(collections.Counter(r['status'] for r in b)),
   'native_statuses':dict(collections.Counter(r.get('native_status',r['status']) for r in b)),
   'compile_success':sum(r.get('compile_success',False) for r in b),
   'nonempty_compiled':sum(r.get('compile_success',False) and r.get('canonical_rule_count',0)>0 for r in b),
   'canonical_rule_count':sum(r.get('canonical_rule_count',0) for r in b),
   'roundtrip_completed':sum(r.get('roundtrip_completed',False) for r in b),
   'roundtrip_exact':sum(r.get('roundtrip_exact') is True for r in b),
   'sum_record_wall_seconds':sum(r['wall_seconds'] for r in b)},
  'repair':{'paired_units':len(paired),'both_compiled':sum(r['both_compiled'] for r in paired),
   'changed_units':sum(r['semantic_fields_changed'] for r in paired),
   'schema_provenance_regressions':sum(r['schema_provenance_regression'] for r in paired),
   'schema_provenance_gains':sum(r['schema_provenance_gain'] for r in paired),
   'units_with_more_exception_roles':sum(r['exception_roles_after']>r['exception_roles_before'] for r in paired),
   'units_with_governing_predicate_changes':sum((r['governing_predicate_changes'] or 0)>0 for r in paired),
   'clause_fields_changed_units':sum(r['clause_fields_changed'] for r in paired),
   'changed_units_interval':cluster_interval({r['record_id']:int(r['semantic_fields_changed']) for r in paired},meta),
   'cycle_delta_interval':cluster_interval({r['record_id']:r['cycle_exact_delta'] for r in paired},meta)},
  'sources_sha256':sha(HERE/'final.sources.jsonl'),'input_results_sha256':{n:sha(HERE/f'final_{n}.jsonl') for n in ['B','C','T5']},
  'not_source_semantic_fidelity':True}
 a_ids={r['record_id'] for r in read(HERE/'final_a100.sources.jsonl')}
 out['matched_a100_C']=cstats([r for r in c if r['record_id'] in a_ids])
 out['by_domain']={domain:{arm:cstats([r for r in rows if meta[r['record_id']]['family']==domain]) for arm,rows in [('C',c),('T5',t)]} for domain in sorted(out['population']['domain_counts'])}
 (HERE/'summary.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 (HERE/'repair_pairs.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in paired))
 print(json.dumps(out,indent=2))
if __name__=='__main__':main()
