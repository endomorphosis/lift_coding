#!/usr/bin/env python3
"""Verify final corrected handoff/file identities without empirical execution."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parents[2]
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
r=json.loads((P/'evidence/final_reproduction.json').read_text());c=json.loads((P/'submission/checksums.json').read_text())
assert r['ok'] and r['all_table_hashes_match'] and r['expected_tables']==r['actual_tables']
for path,v in c['files'].items():assert sha(P/path)==v['sha256'] and (P/path).stat().st_size==v['bytes'],path
for n,h in r['original_receipts_unchanged'].items():assert sha(P/'receipts'/f'{n}.json')==h
assert all(x['exit_code']==0 for x in r['commands']) and len(r['commands'])==2
assert r['retained_scientific_scope']['original_container_failed_checker_OOM'] and r['retained_scientific_scope']['E_locked']
assert r['retained_scientific_scope']['AF013_canaries']==114 and not r['retained_scientific_scope']['applied_learned_features']
assert not r['outside_reviewer_required'] and not r['author_signoff_claimed'] and not r['paper_upload_performed']
p=(P/'submission/author_review_packet.md').read_text();assert 'target-assisted' in p and 'no_candidate' in p and '481.585523993' in p
print(json.dumps({'ok':True,'file_identities':len(c['files']),'clean_reproduction_commands':2,'original_AF013_AF029_receipts_unchanged':True,'no_new_scientific_execution':True},indent=2))
