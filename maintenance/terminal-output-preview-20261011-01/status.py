"""Print bounded structured campaign status without prompts or installer output."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
protocol = json.loads((root / 'comparison-protocol.json').read_text())
for selected in protocol['trials']:
    name = selected['name']
    row = {'trial': name, 'state': 'pending'}
    state = root / 'launcher-state' / name
    events = state / 'events.jsonl'
    if events.exists():
        event = json.loads(events.read_text().splitlines()[-1])
        row['state'] = event['event']
        sample = event.get('sample', {})
        row['resources_gib'] = {key.removesuffix('_bytes'): round(sample[key] / 2**30, 2) for key in
                            ('mem_available_bytes', 'disk_free_bytes') if key in sample}
        row['load'] = sample.get('load_1m')
        row['pressure'] = event.get('pressure_reasons', [])
    outcome = state / 'outcome.json'
    if outcome.exists():
        row['outcome'] = json.loads(outcome.read_text()).get('classification')
    trial = root / 'trials' / name
    receipts = list(trial.glob('jobs/*/*/agent/supervisor-result.json'))
    if receipts:
        report = json.loads(receipts[0].read_text())
        row['supervisor_status'] = report.get('status')
        row['input_audit'] = (report.get('context_input_audit') or {}).get('status')
        row['provider_invocations'] = len(report.get('provider_invocations') or [])
    stages = [path for path in trial.glob('jobs/*/*/agent/deployment/**/*') if path.is_file()]
    if stages:
        latest = max(stages, key=lambda path: path.stat().st_mtime_ns)
        row['latest_deployment_stage'] = latest.name
    receipt = trial / 'receipt.json'
    if receipt.exists():
        retained = json.loads(receipt.read_text())
        row['complete_receipt'] = retained.get('complete_single_trial_receipt')
        row['rewards'] = [item.get('reward') for item in retained.get('trials', [])]
        row['metadata_dispatch'] = [(item.get('semantic_metadata_dispatch') or {}).get('status')
                                   for item in retained.get('trials', [])]
    print(json.dumps(row, sort_keys=True))
