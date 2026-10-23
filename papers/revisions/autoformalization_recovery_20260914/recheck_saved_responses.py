#!/usr/bin/env python3
"""Post-hoc transport-framing check. No model calls or proof edits."""
from pathlib import Path
import importlib.util,hashlib,json
root=Path(__file__).resolve().parent
script=root.parents[2]/'scripts/autoformalization_recovery_probe.py'
spec=importlib.util.spec_from_file_location('framing_probe',script)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=root/'saved_response_recheck';out.mkdir(exist_ok=False)
manifest={'scope':'post-hoc extraction of the first assistant turn; not a new model run or held-out estimate','model_calls':0,'final_test_accessed':False,'proof_text_edited':False,'original_strict_protocol_native_acceptances':0,'extractor_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'input_files':{}}
rows=[]
for index,goal in enumerate(m.GOALS):
 source=root/'leanstral_retry_probe'/f'{index+1:02d}-{goal["goal_id"]}'/'model/response.json'
 raw=source.read_bytes();manifest['input_files'][str(source.relative_to(root))]=hashlib.sha256(raw).hexdigest()
 data=json.loads(raw);content=data['choices'][0]['message']['content']
 body=m.parse_body(content)
 folder=out/f'{index+1:02d}-{goal["goal_id"]}';folder.mkdir()
 if body is not None:(folder/'extracted.txt').write_text(body)
 result={'status':'abstained','accepted':False} if body is None else m.check_lean(goal,body,folder)
 row={'goal_id':goal['goal_id'],'original_finish_reason':data['choices'][0]['finish_reason'],'explicit_turn_terminator_present':'<|im_end|>' in content,'checker':result}
 rows.append(row);m.write(folder/'result.json',row)
manifest['rechecked_responses']=len(rows)
manifest['accepted_proofs']=sum(r['checker']['accepted'] for r in rows)
manifest['statuses']={r['goal_id']:r['checker']['status'] for r in rows}
m.write(out/'summary.json',manifest)
print(json.dumps(manifest,indent=2))
