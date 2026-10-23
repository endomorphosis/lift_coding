"""Keep recovered developmental/planning leads separate from the 32/24 cohorts."""
import hashlib
import json
import os
import subprocess
from collections import Counter
from audit_io import ROOT,OUT,write_json

def main():
    sources=json.loads((OUT/'workstreams/git_population_inputs.json').read_text())
    documents={}
    for source in sources:
        spec=source['commit']+':'+source['path']
        size=int(subprocess.run(['git','-C',str(ROOT),'cat-file','-s',spec],check=True,capture_output=True,text=True).stdout)
        if size>512*1024:raise ValueError('Bound exceeded')
        raw=subprocess.run(['git','-C',str(ROOT),'show',spec],check=True,capture_output=True).stdout
        assert hashlib.sha256(raw).hexdigest()==source['sha256']
        documents[source['path']]=[json.loads(s) for s in raw.decode().splitlines()] if source['path'].endswith('.jsonl') else json.loads(raw)
    prefix='papers/completion/neurosymbolic_supervision/'
    rows=documents[prefix+'pilot/results.jsonl'];freeze=documents[prefix+'artifacts/final_experiment_freeze.json'];plan=documents[prefix+'protocol/final_run_manifest.json']
    summary={'schema':'unmatched-historical-population-leads@1','source_commit':sources[0]['commit'],'sources':sources,
             'pilot_named_file':{'rows':len(rows),'record_kind_counts':dict(Counter(r['record_kind'] for r in rows)),
                                 'terminal_state_counts':dict(Counter(r['terminal_state'] for r in rows)),
                                 'declared_developmental_rows':sum(r['developmental'] is True for r in rows),
                                 'declared_fixture_rows':sum(r.get('fixture') is True for r in rows),
                                 'counts_as_live_repair_rows':sum(r.get('counts_as_live_repair') is True for r in rows),
                                 'terminal_reason_counts':dict(Counter(r['terminal_reason'] for r in rows)),
                                 'matches_selected_manuscript_24_cell_cohort':False},
             'final_freeze':{'freeze_id':freeze['freeze_id'],'final_dispatch_authorized':freeze['final_dispatch_authorized'],
                             'first_final_attempt_started':freeze['first_final_attempt_started'],'retained_executable_arm_count':len(freeze['retained_executable_arms'])},
             'final_plan':{'units':len(plan['units']),'dispatch_authorized':plan['dispatch_authorized'],'first_final_attempt_started':plan['first_final_attempt_started'],
                           'preregistered_units':plan['preregistered_final_units_if_n16'],'matches_selected_manuscript_32_terminal_cells':False},
             'new_executions':0,'added_to_selected_32_or_24_cohort':False,
             'conclusion':'These exact-title-paper Git artifacts are earlier developmental and uninvoked planning records; filenames alone do not identify the selected manuscript32/24cohorts.',
             'gap_update':{'prior_gap':16,'status':'unchanged','searched_new_routes':[x['commit']+':'+x['path'] for x in sources],
                           'remaining':'Exact original 32-cell and 24-cell ledgers remain unmatched. Inspect later scoped histories or provide original cohort manifests; do not substitute76developmental rows or192planned units.'}}
    write_json('workstreams/git_population_leads.json',summary)
    print(json.dumps({'developmental_rows':len(rows),'planned_units':len(plan['units']),'selected_32_or_24_cohort_recovered':False,'new_executions':0}))

if __name__=='__main__':
    os.umask(0o077);main()
