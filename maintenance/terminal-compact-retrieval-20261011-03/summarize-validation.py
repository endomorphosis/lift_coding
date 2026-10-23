"""Summarize qualified test reports without reading fixture/private state."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
G=Path(__file__).parent
names=['codec-delivery-validation-01.xml','codec-delivery-followup-01.xml',
 'runner-validation-01.xml','runner-validation-02.xml','control-wire-frozen-tests.xml',
 'unit-audit-comparison-03/tests.xml']
seen={};reports=[];records=0
for name in names:
 p=G/name;raw=p.read_bytes();root=ET.fromstring(raw);cases=list(root.iter('testcase'))
 counts={tag:sum(c.find(tag)is not None for c in cases) for tag in ('failure','error','skipped')}
 assert counts=={'failure':0,'error':0,'skipped':0}
 for c in cases:
  parts=c.attrib.get('classname','').split('.')
  start=next((i for i,s in enumerate(parts) if s.startswith('test_')),0)
  key=('.'.join(parts[start:]),c.attrib['name'])
  seen.setdefault(key,[]).append(name)
 records+=len(cases)
 reports.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'records':len(cases),**counts})
validation={'schema':'materialized-wire-qualified-test-summary@1','scope':'Focused codec, file delivery, runner, control/deployment, audit and comparison regressions; not the whole repository.',
 'reports':reports,'selected_junit_records':records,'unique_passing_cases':len(seen),
 'repeated_passing_records':records-len(seen), 'failed_cases':0,'errors':0,'skipped_cases':0,
 'node_key_normalization':'Canonical module beginning at test_ filename stem, remaining class suffix and full parameterized test name.',
 'repeated_cases':[{'module':key[0],'case':key[1],'reports':value} for key,value in sorted(seen.items()) if len(value)>1],
 'initial_unqualified_attempts_retained':[{'receipt':'unit-audit-comparison-01/receipt.json','reason':'Incorrect dependency import roots; setup/import errors; source changed while running.'},
 {'script_log':'legacy-codec-replay.log','reason':'Legacy API lacks the new keyword; corrected and independently replayed against both historical modules.'},
 {'report':'control-wire-final-tests.xml','reason':'AST-seal cache skips; fresh final seal rerun passes all209.'}],
 'independent_legacy_replay':'legacy-codec-replay-final.json','live_model_provider_calls':0,
 'whole_repository_test_pass_claimed':False,'task_correctness_or_convergence_proof_claimed':False}
(G/'validation-summary.json').write_text(json.dumps(validation,indent=2,sort_keys=True)+'\n')
print(json.dumps({'selected_records':records,'unique_passing_cases':len(seen),'repeated_records':records-len(seen),'failures':0,'errors':0,'skips':0}),flush=True)
