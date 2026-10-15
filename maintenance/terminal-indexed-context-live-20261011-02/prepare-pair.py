"""Freeze the two public MJCF trials without launching models or containers."""
import json
from pathlib import Path

from aggregate_trials import normalize_config
from benchmarks.agent_supervisor.container_coding.full_supervisor_benchmark import prepare

campaign = Path(__file__).resolve().parent
previous = campaign.with_name('terminal-indexed-context-live-20261011-01')
pins = json.loads((campaign / 'launcher-protocol.json').read_text())
protocol = json.loads((previous / 'comparison-protocol.json').read_text())
protocol['source_commit'] = pins['source_head']
protocol['trials'] = [row for row in protocol['trials'] if row['task'] == 'tune-mjcf']
protocol['preparations'] = {}
protocol['previous_attempt'] = str(previous / 'trials/batching-default-01/receipt.json')
protocol['task_selection'] = {
    'tune-mjcf': 'Public regression establishes three versus two retained capsules.',
    'llm-inference-batching-scheduler': 'Functional regression only: both profiles retain one capsule under the shared byte bound.',
}
protocol['local_projection_evidence'] = str(previous / 'public-budget-regression.json')
protocol['live_token_savings_claimed_before_execution'] = False
for trial in protocol['trials']:
    output = campaign / 'trials' / trial['name']
    prepared = prepare(
        dataset=Path('/home/barberb/lift_coding/.benchmarks/terminal-bench-2'),
        output=output, archive=campaign / 'runtime-archive-v1', arm='full',
        task_name=trial['task'], task_profile=campaign / 'profiles/tune-mjcf.json',
        semantic_context_profile=trial['semantic_context_profile'],
        resource_profile='source384-5cpu-16gib-extended@1',
    )
    assert prepared['prepared'] is True
    assert prepared['archive_sha256'] == pins['archive_sha256']
    config = json.loads((output / 'config.json').read_text())
    frozen = {key: prepared[key] for key in (
        'archive_sha256', 'task_input_sha256', 'host_source_sha256')}
    frozen['normalized_configuration'] = normalize_config(config)
    if trial['task'] in protocol['preparations']:
        assert frozen == protocol['preparations'][trial['task']]
    else:
        protocol['preparations'][trial['task']] = frozen
    print(json.dumps({'trial': trial['name'], 'prepared': True,
                     'profile': trial['semantic_context_profile']}), flush=True)
with (campaign / 'comparison-protocol.json').open('x') as stream:
    json.dump(protocol, stream, indent=2, sort_keys=True)
    stream.write('\n')
