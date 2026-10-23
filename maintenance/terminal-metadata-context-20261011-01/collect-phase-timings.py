"""Export native phase durations separately from cumulative model token counts."""
import hashlib
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parent
protocol = json.loads((root / 'comparison-protocol.json').read_text())
rows = []
for selected in protocol['trials']:
    path = root / 'trials' / selected['name'] / 'receipt.json'
    raw = path.read_bytes()
    receipt = json.loads(raw)
    if receipt.get('complete_single_trial_receipt') is not True or len(receipt.get('trials', [])) != 1:
        raise ValueError('complete single-trial receipt required')
    trial = receipt['trials'][0]
    durations = trial['durations_seconds']
    keys = ('environment_setup', 'agent_setup', 'agent_execution', 'verifier')
    if any(durations.get(key) is not None and (type(durations[key]) not in (int, float)
           or not math.isfinite(durations[key]) or durations[key] < 0) for key in keys):
        raise ValueError('finite nonnegative native phase durations or unknown values required')
    rows.append({key: selected[key] for key in ('name', 'repeat', 'semantic_metadata_view')}
                | {'durations_seconds': {key: durations.get(key) for key in keys},
                   'receipt_sha256': hashlib.sha256(raw).hexdigest()})
report = {'schema': 'terminal-metadata-phase-timings@1', 'trials': rows,
          'timing_scope': 'Native Harbor phase durations; supervisor execution includes planning, coding, auditing and cleanup.',
          'setup_scope': 'Fresh runtime and CLI installation, reported separately from supervisor execution.',
          'provider_calls_by_collector': 0}
(root / 'phase-timings.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps(report, indent=2))
