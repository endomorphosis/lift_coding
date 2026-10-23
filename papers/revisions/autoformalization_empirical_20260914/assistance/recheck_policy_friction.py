#!/usr/bin/env python3
"""Posthoc strict-policy sensitivity: original bodies, no model calls/edits."""
from pathlib import Path
import importlib.util,json,hashlib
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('assist',HERE/'run_assistance.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
manifest=json.loads((HERE/'frozen_protocol.json').read_text());goals={g['goal_id']:g for g in manifest['goals']}
rows=[json.loads(x) for x in (HERE/'model/results.jsonl').read_text().splitlines()]
selected=[r for r in rows if r['goal_id'] in goals and r['model']['checker'].get('reason') in {'unknown_identifier:rw','unknown_identifier:safe_x'}]
assert len(selected)==6
out=HERE/'policy_friction_posthoc';out.mkdir(exist_ok=False)
m.TACTICS.update({'rw','safe_x'})
results=[]
for row in selected:
 gid=row['goal_id'];body=(HERE/'model'/gid/'extracted.txt').read_text();folder=out/gid;folder.mkdir()
 checked=m.check_lean(goals[gid],body,folder)
 result={'goal_id':gid,'expected_provable':goals[gid]['expected_provable'],'original_policy_reason':row['model']['checker']['reason'],'proof_body_sha256':hashlib.sha256(body.encode()).hexdigest(),'proof_body_edited':False,'checker':checked};results.append(result);m.write(folder/'result.json',result)
summary={'scope':'Posthoc admission-policy sensitivity on six retained complete outputs; not a new model result or prospective primary estimate','primary_acceptances_unchanged':12,'primary_valid_denominator':32,'model_calls':0,'proof_edits':0,'extension':['rw (core Lean rewrite tactic)','safe_x (model-chosen local binder name)'],'records':len(results),'new_valid_native_accepted':sum(r['expected_provable'] and r['checker']['accepted'] for r in results),'invalid_native_accepted':sum(not r['expected_provable'] and r['checker']['accepted'] for r in results),'statuses':{r['goal_id']:r['checker']['status'] for r in results},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};m.write(out/'summary.json',summary);print(json.dumps(summary,indent=2))
