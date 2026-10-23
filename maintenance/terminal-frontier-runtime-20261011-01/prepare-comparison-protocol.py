"""Record fixed controls without changing either immutable trial config."""
from pathlib import Path
import copy
import hashlib
import json

p = Path(__file__).parent
configs, preps = [], []
for mode in ('expanded', 'compact'):
    d = p / 'pilot' / ('intent-' + mode + '-01')
    config = json.loads((d / 'config.json').read_text())
    prep = json.loads((d / 'preparation.json').read_text())
    projection = copy.deepcopy(config)
    projection.pop('jobs_dir')
    projection['agents'][0]['kwargs'].pop('intent_requirements_transport')
    # Harbor serializes its exclusion set in process-dependent order. Keep both
    # original files intact, and record that this comparison treats it as a set.
    exclusions = projection['retry']['exclude_exceptions']
    assert len(exclusions) == len(set(exclusions))
    projection['retry']['exclude_exceptions'] = sorted(exclusions)
    configs.append(projection)
    preps.append(prep)
assert configs[0] == configs[1]
for key in ('archive_sha256', 'manifest_sha256', 'intent_requirement_contract_sha256',
            'task_input_sha256', 'host_source_sha256'):
    assert preps[0][key] == preps[1][key]
contract = configs[0]['agents'][0]['kwargs']['intent_requirement_contract']
assert len(contract['requirements']) == 17
receipt = {
    'schema': 'terminal-intent-live-comparison-protocol@1',
    'archive_sha256': preps[0]['archive_sha256'], 'manifest_sha256': preps[0]['manifest_sha256'],
    'comparison': 'Expanded versus compact IntentIR with full native retrieval fixed',
    'requested_modes': ['expanded', 'compact'],
    'common_config_sha256': hashlib.sha256(json.dumps(configs[0], sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    'excluded_config_fields': ['jobs_dir', 'agents[0].kwargs.intent_requirements_transport'],
    'comparison_only_set_sorting': ['retry.exclude_exceptions'],
    'both_original_configuration_files_preserved': True,
    'other_configuration_fields_equal_after_exclusion_set_sorting': True,
    'task_input_hashes_equal': True, 'host_adapter_hashes_equal': True,
    'contract_sha256': preps[0]['intent_requirement_contract_sha256'], 'required_requirements': 17,
    'public_instruction_sha256': '89b1abdf0af19399f720233b5cdf6b2e8e0ff7b6e3fe3e2a3af0d4d298a8641a',
    'gates': ['Installed runtime and actual worker expansion qualified', 'Production max5 byte gate recorded',
              'Actual model_router typed residual and coding receipt present',
              'Compact coding inclusion @6 selects compact with verified roundtrip and byte gate',
              'Complete native cumulative usage and official outcome reported'],
    'cached_input_handling': 'Subset of cumulative input; never add twice',
    'output_tokens_4096': 'Requested; enforcement not established', 'causal_efficiency_claimed': False,
    'fresh_context_identity_and_outcome_caveat': 'Per-run task/world identities and provider behavior may differ; one pair is observational.',
}
(p / 'intent-comparison-protocol.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt), flush=True)
