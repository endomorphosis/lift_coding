#!/usr/bin/env python3
"""Project immutable native feedback statuses; no model, prover or packet-body read."""
from pathlib import Path
import argparse,json,hashlib,collections

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--raw-root',type=Path,required=True);ap.add_argument('--inventory',type=Path,required=True);ap.add_argument('--inventory-sha256',required=True);args=ap.parse_args()
 assert sha(args.inventory)==args.inventory_sha256
 inventory=json.loads(args.inventory.read_bytes());assert inventory['producer_terminated'] and inventory['all_original_files_hashed'] and inventory['success'];entries={e['path']:e for e in inventory['entries']}
 prefix='evidence/native_training/';receipt_rel=prefix+'native_checker_receipts.jsonl';coverage_rel=prefix+'source_obligation_feedback/coverage.json'
 for rel in [receipt_rel,coverage_rel]:assert sha(args.raw_root/rel)==entries[rel]['sha256']
 receipts=[json.loads(x)for x in (args.raw_root/receipt_rel).read_text().splitlines()];coverage=json.loads((args.raw_root/coverage_rel).read_bytes());rows=[]
 assert len(receipts)==coverage['train_rows']==len(coverage['rows'])==69
 for i,(r,c) in enumerate(zip(receipts,coverage['rows'],strict=True)):
  rel=prefix+f'source_obligation_feedback/row-{i:03d}/receipt.json';p=args.raw_root/rel;assert sha(p)==entries[rel]['sha256'];assert json.loads(p.read_bytes())==r and r['status']==c['status']
  rows.append({'ordinal':i,'status':r['status'],'exit_code':r['exit_code'],'receipt_sha256':sha(p)})
 counts=dict(collections.Counter(r['status']for r in rows));assert counts=={'checked':61,'timeout':6,'unsupported_fragment':2};assert all(r['exit_code']==0 for r in rows if r['status']=='checked')
 out={'schema':'af-final-feedback-status-projection/v1','scope':'final amended run compiler-structural feedback, not prior OOM attempts or semantic gold','frozen_inventory_sha256':args.inventory_sha256,'native_checker_receipts':{'path':receipt_rel,'sha256':entries[receipt_rel]['sha256']},'coverage':{'path':coverage_rel,'sha256':entries[coverage_rel]['sha256'],'train_rows':coverage['train_rows'],'admitted_records':coverage['admitted_records'],'all_generated_obligations':coverage['all_generated_obligations'],'supported_obligations':coverage['supported_obligations']},'counts':counts,'rows':rows,'semantic_fidelity_measured':False,'prior_60_7_2_counts_are_separate_failed_run_history':True}
 q=Path(__file__).resolve().parents[2]/'evidence/final_correction/feedback_status.json';q.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps({'ok':True,'rows':len(rows),'counts':counts,'sha256':sha(q)},indent=2))
if __name__=='__main__':main()
