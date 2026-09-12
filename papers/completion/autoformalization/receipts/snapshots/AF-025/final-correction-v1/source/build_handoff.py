#!/usr/bin/env python3
"""Reproduce the anonymous scalar/table package and write an accurate final handoff."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib,json,subprocess,tempfile,zipfile,time,os
from datetime import datetime,timezone
P=Path(__file__).resolve().parents[2]
E=P/'evidence/final_correction'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def now():return datetime.now(timezone.utc).isoformat()
zip_path=P/'submission/supplement.zip';commands=[]
with tempfile.TemporaryDirectory(prefix='af-corrected-reproduction-') as td:
 root=Path(td);home=root/'home';home.mkdir();env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin','HOME':str(home),'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
 with zipfile.ZipFile(zip_path) as z:
  assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist());z.extractall(root)
 bundle=root/'autoformalization-anonymous-reproducibility'
 for label,args in [('zip_regenerate_v2',['regenerate_tables.py','--check']),('zip_inputs_v2',['verify_retained_inputs.py'])]:
  argv=['/usr/bin/python3.12','-B','-S',*args];start=now();t=time.monotonic();r=subprocess.run(argv,cwd=bundle,env=env,capture_output=True,timeout=60)
  (E/'logs'/f'{label}.stdout').write_bytes(r.stdout);(E/'logs'/f'{label}.stderr').write_bytes(r.stderr)
  rec={'argv':argv,'cwd':'fresh temporary anonymous ZIP root','environment':{**env,'HOME':'fresh empty temporary directory'},'started_at':start,'finished_at':now(),'wall_seconds':time.monotonic()-t,'exit_code':r.returncode,'stdout':f'evidence/final_correction/logs/{label}.stdout','stderr':f'evidence/final_correction/logs/{label}.stderr'}
  dump(E/'logs'/f'{label}.json',rec);commands.append(rec)
  if r.returncode:raise RuntimeError(f'{label} failed; original logs retained')
 regeneration=json.loads((E/'logs/zip_regenerate_v2.stdout').read_text())
 expected=json.loads((P/'artifact/manifest.json').read_text())['reported_tables'];actual={k:sha(P/'results'/k) for k in expected};assert expected==actual
 assert all(regeneration['tables'][k]['sha256']==v for k,v in actual.items() if k!='summary.json')
a=json.loads((E/'actual_execution.json').read_text());fmt=json.loads((P/'evidence/format_check.json').read_text())
report={'schema':'autoformalization-final-reproduction/v1','task_id':'AF-025','corrective_scope':'coordinating-assistant correction of stale derived evidence; no new scientific run','created_at':now(),'ok':True,'commands':commands,'expected_tables':expected,'actual_tables':actual,'all_table_hashes_match':True,'supplement':{'sha256':sha(zip_path),'bytes':zip_path.stat().st_size},'paper':{'sha256':sha(P/'submission/paper.pdf'),'bytes':(P/'submission/paper.pdf').stat().st_size,'main_text_pages':9,'total_pages':21},'actual_execution':{'path':'evidence/final_correction/actual_execution.json','sha256':sha(E/'actual_execution.json')},'original_receipts_unchanged':{n:sha(P/'receipts'/f'{n}.json') for n in ['AF-029','AF-013']},'retained_scientific_scope':{'three_T2_T3_seeds_completed':True,'T2_reconstruction_target_assisted':True,'T3_compiler_structural_feedback_only':True,'original_container_failed_checker_OOM':True,'separate_saved_byte_checker_succeeded':True,'native_delivery_succeeded':True,'AF013_canaries':114,'promotion_outcomes':a['AF013']['promotion_outcomes'],'applied_learned_features':False,'T4_unactivated':True,'E_locked':True},'checks_not_rerun':['training','checkpoint loading','native prover/solver execution','canary execution','provider calls','final-test experiments'],'unavailable_or_unmeasured':['1913-unit primary final-test experiments unrun','independent human fidelity/agreement unmeasured','learned-guidance efficacy unavailable after actual promotion rejection'],'latex_is_empirical_validation':False,'outside_reviewer_required':False,'author_signoff_claimed':False,'paper_upload_performed':False}
dump(P/'evidence/final_reproduction.json',report)
text='''# Corrected manuscript and artifact handoff

The manuscript is complete within the retained automated-evidence scope. This corrective build replaces stale derived claims and keeps the original receipts and failed-run evidence as history. It performs no new training, model call, canary run, paper upload, or author sign-off. Outside reviewers and optional author feedback are not completion prerequisites.

- [Anonymous paper](paper.pdf): 9 main-text pages and 21 total pages, unchanged official style, all 16 checklist answers completed, no scientific placeholders.
- [Anonymous supplement](supplement.zip): clean standard-library table regeneration and retained-input hash verification pass. [Checksums](checksums.json) bind the final files.
- [Claim audit](../evidence/final_claim_audit.json), [actual execution projection](../evidence/final_correction/actual_execution.json), and [reproduction record](../evidence/final_reproduction.json) map the retained claims to exact source and result identities.

Three fixed AF-029 seeds completed T2 shared updates (one accepted epoch and all five packed families per seed) and 256 T3 compiler-structural updates per seed. The original full checker/container failed OOM after training; a separate retained-byte checker passed, and native delivery retained the states. Earlier failed profiles and unknown interruptions remain charged/disclosed. T2 cosine 1/MSE 0 is target-assisted projection, not source-free reconstruction or generalization; T0/T2 family CE was unchanged. T1 is a sample-memory diagnostic. T3 feedback is not human semantic gold.

AF-013 loaded/exported the three T3 states sequentially and retained all 3 × 38 fixed native diagnostics. Every actual promotion returned `no_candidate`. Identity ingestion did not apply learned features; default reset was not rollback of an applied effect. T4 and Arm E remain unavailable.

All 44 original primary table cells have explicit status and denominator. The 1913-unit final-test population remains locked/unrun; human fidelity and agreement are unmeasured. Constructed controls, retrieval proxies and source-assisted reconstruction do not fill those cells. Historical AF-020 cost is 481.585523993 seconds counted once; actual amended training/checker/delivery/canary costs are separated in the execution appendix and projection.

All three abstracts are registered in the coordinating status record. The working paper deadline is 14 September 2026 noon UTC. This artifact build does not claim a paper submission or publication. Optional camera-ready identity, acknowledgements, licensing and additional author-supplied facts remain separate from manuscript completion; see [author information](../evidence/author_questions.md).
'''
(P/'submission/author_review_packet.md').write_text(text)
files=['submission/paper.pdf','submission/supplement.zip','submission/author_review_packet.md','evidence/final_reproduction.json','evidence/final_claim_audit.json','evidence/final_correction/actual_execution.json','evidence/format_check.json','evidence/author_questions.md','artifact/README.md','artifact/manifest.json','artifact/S01_S40_map.json','manuscript/main.tex','manuscript/checklist.tex','manuscript/llm_disclosure.tex','results/summary.json','results/table6_pipeline.tex','results/table11_training.tex','results/table13_assistance.tex']
dump(P/'submission/checksums.json',{'schema':'autoformalization-submission-checksums/v2','files':{f:{'sha256':sha(P/f),'bytes':(P/f).stat().st_size} for f in files},'self_hash_omitted':True})
print(json.dumps({'ok':True,'commands_passed':len(commands),'reported_tables':actual,'no_new_scientific_execution':True},indent=2))
