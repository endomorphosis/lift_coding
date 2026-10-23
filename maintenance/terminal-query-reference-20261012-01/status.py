from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent
value=json.loads(subprocess.check_output([sys.executable,str(root/'collect-comparison.py')],text=True))
for row in value['trials']:
    item={key:row[key] for key in ('name','state','classification')}
    item['tokens']=row['native_usage']['complete_total_tokens']
    item['reference_input_observed']=row['effective_reference_input_observed']
    item['official_reward']=row['official_reward']
    if row['state']=='running_or_unresolved':
        event=root/'launcher-state'/row['name']/'events.jsonl'
        if event.is_file():
            recent=json.loads(event.read_text().splitlines()[-1])
            item.update(at=recent.get('at'),pressure=recent.get('pressure_reasons'))
        phases=list((root/'trials'/row['name']).glob('jobs/*/*/agent/deployment/*'))
        if phases:item['last_setup_artifact']=max(phases,key=lambda p:p.stat().st_mtime).name
    print(json.dumps(item))
