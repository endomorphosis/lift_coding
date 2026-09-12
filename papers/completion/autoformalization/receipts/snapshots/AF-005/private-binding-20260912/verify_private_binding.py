"""Independent artifact checks; never emit private source text or identifiers."""
from fractions import Fraction
import collections,hashlib,json,os,stat
from pathlib import Path
B=Path(__file__).resolve().parent;ROOT=Path('/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization');OLD=ROOT/'af004-v1';NEW=ROOT/'af005-independent-annotation-v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
report=json.loads((B/'binding_report.json').read_text());manifest=json.loads((NEW/'binding_manifest.private.json').read_text())
packets=[json.loads(s) for s in (NEW/'annotation_packets.private.jsonl').read_text().splitlines()]
gold=[json.loads(s) for s in (NEW/'gold_facets.pending.private.jsonl').read_text().splitlines()]
meta=json.loads((OLD/'partitions.private.json').read_text())['membership']['final_test'];allowed={r['record_id']:r for r in meta}
assert len(packets)==len(gold)==100 and len({p['packet_id'] for p in packets})==100
assert len({p['source']['normalized_source_unit_sha256'] for p in packets})==100
counts=collections.Counter(p['source']['component'] for p in packets);assert len(counts)==20
units=collections.defaultdict(set)
for r in meta:units[r['component']].add(r['normalized_source_unit_sha256'])
assert sum(map(len,units.values()))==1913
weights=Fraction(0);forbidden=[]
for p,g in zip(packets,gold):
 s=p['source'];r=allowed[s['record_id']];h=r['component'];N=len(units[h]);n=counts[h]
 assert s['component']==h and s['normalized_source_unit_sha256']==r['normalized_source_unit_sha256']
 assert p['sampling']['N_h']==N and p['sampling']['n_h']==n
 pi=p['sampling']['inclusion_probability'];w=p['sampling']['inverse_probability_weight']
 assert Fraction(pi['numerator'],pi['denominator'])==Fraction(n,N)
 assert Fraction(w['numerator'],w['denominator'])==Fraction(N,n);weights+=Fraction(N,n)
 assert p['evaluation_sample'] is True and p['evaluation_eligible'] is False and p['actual_independent_review'] is False
 assert not any(p[k] for k in ['model_outputs_present','teacher_ir_present','gold_values_present'])
 assert p['packet_id']==g['packet_id'] and g['evaluation_eligible'] is False and g['label_origin'] is None and not g['annotators']
 assert not g['annotator_independence_attested'] and g['semantic_claim_status']=='unmeasured'
 assert g['adjudication']['status']=='pending_independent_review' and not g['adjudication']['records']
 assert all(f['status']=='unmeasured_pending_independent_review' and f['values']==[] and f['adjudication'] is None and not f['annotator_ids'] for f in g['facets'].values())
 forbidden.extend([s['record_id'],s['normalized_source_unit_sha256'],s['text']])
assert weights==1913
assert all(sha(NEW/name)==h for name,h in report['private_commitments'].items())
assert stat.S_IMODE(NEW.stat().st_mode)==0o700 and all(stat.S_IMODE(p.stat().st_mode)==0o600 for p in NEW.iterdir())
# Only aggregate public outputs are checked; hidden bodies never leave this process.
for name in ['sampling_plan.json','binding_report.json']:
 data=(B/name).read_text();assert all(value not in data for value in forbidden if value)
result={'schema':'af005-independent-private-binding-check/v1','passed':True,'bound_units':100,'groups':20,'population_weight_sum':1913,
 'all_unit_probabilities_and_inverse_weights_exact':True,'source_membership_and_unique_unit_counts_exact':True,'public_artifacts_contain_no_selected_source_text_or_ids':True,
 'private_artifact_hashes_and_modes_exact':True,'human_annotations':0,'evaluation_eligible_units':0,
 'helper_sha256':sha(Path(__file__)),'binding_report_sha256':sha(B/'binding_report.json')}
p=B/'independent_binding_verification.json'
with p.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'verification_sha256':sha(p),'bound_units':100,'human_annotations':0}))
