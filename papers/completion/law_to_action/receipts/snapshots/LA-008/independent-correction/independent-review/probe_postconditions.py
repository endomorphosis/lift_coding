from pathlib import Path
import sys,json,tempfile,copy,hashlib
from datetime import datetime,timezone
base=Path('/home/barberb/lift_coding/papers/completion/runtime_bootstrap/la008_independent_correction/candidate/papers/completion/law_to_action/benchmark')
sys.path.insert(0,str(base));import run
case=run.smoke_cases()[0];rid='review-only-wrong-payload'
with tempfile.TemporaryDirectory(prefix='la008-independent-') as td:
 state=Path(td)/'state';wrong=copy.deepcopy(case['generated_code']);wrong['payload']={'unexpected':True}
 run.BoundedExportHandler(state).execute(wrong,run_id=rid)
 observation=run.EffectObserver(state).observe(run_id=rid)
 post=run.observed_postconditions(case,observation,run_id=rid)
 match=run.measurement_matches(case,{'decision':'allow'},observation,{'returncode':0,'timed_out':False},run_id=rid)
 record={'case':case,'run_id':rid,'decision':{'decision':'allow'},'terminal_outcome':'success','actual_process':{'returncode':0,'timed_out':False},'effect_observation':observation}
 metrics=run.allowed_work_metrics([record])
 assert observation['journal_consistent'] and observation['observed_effect_count']==1
 assert not post['authorized_export_matches_actual_bytes'] and not match
 assert metrics['allowed_work_successful']==0
 # A complete correct file still cannot turn a nonzero process exit into success.
 good=Path(td)/'good';run.BoundedExportHandler(good).execute(case['generated_code'],run_id=rid)
 correct=run.EffectObserver(good).observe(run_id=rid)
 assert run.observed_postconditions(case,correct,run_id=rid)['authorized_export_matches_actual_bytes']
 assert not run.measurement_matches(case,{'decision':'allow'},correct,{'returncode':1,'timed_out':False},run_id=rid)
 print(json.dumps({'observed_at':datetime.now(timezone.utc).isoformat(),'source_sha256':{p:hashlib.sha256((base/p).read_bytes()).hexdigest() for p in ['run.py','handlers/effects.py']},'internally_matching_wrong_payload_and_journal':{'journal_consistent':True,'observed_effect_count':1,'requested_postcondition_match':False,'measurement_match':False,'allowed_work_credit':0},'nonzero_exit_with_correct_postcondition_rejected':True,'scope':'pure reviewer fixture only; no provider or empirical benchmark; temporary state cleaned'},indent=2))
