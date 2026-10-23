"""Check explicit public prior seals and the six captured stage source pins."""
import hashlib
import json
from pathlib import Path

STAGE = Path(__file__).resolve().parent
H = STAGE.parent / 'terminal-context-budget-20261011-01'
CHECKOUT = STAGE.parent / 'terminal-token-reduction-20261007-01/checkout'
H_SEAL_SHA = '377bdc6a34c2c1b9ac6b6bb2bc7702ffb75b1dfa5d2a7dd5ed009999b45d1061'
READER = 'ipfs_accelerate_py/agent_supervisor/runtime/codex_usage_receipt.py'
READER_AFTER_SHA = '9a5b1bddbecb4d374c579f93067039991fb1d4420e7cdc31caeca8b8ff2caa18'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def check(expected, group):
    path = Path(expected['path'])
    actual = pin(path)
    assert (actual['bytes'], actual['sha256']) == (expected['bytes'], expected['sha256']), path
    return {**actual, 'group': group, 'unchanged': True}


def main():
    seal = H / 'evidence-manifest.json'
    assert pin(seal)['sha256'] == H_SEAL_SHA
    checks = [check(pin(seal), 'previous_stage_manifest')]
    manifest = json.loads(seal.read_text())
    assert len(manifest['files']) == 49
    for item in manifest['files']:
        checks.append(check({**item, 'path': str(H / item['path'])}, 'previous_stage_public_artifacts'))
    old = json.loads((H / 'preservation-check.json').read_text())
    assert old['all_explicit_checks_passed'] and len(old['files']) == 155
    for item in old['files']:
        checks.append(check(item, 'older_preservation_pins'))
    previous_sources = json.loads((H / 'source-manifest.json').read_text())
    for item in previous_sources['files']:
        checks.append(check({**item, 'path': str(CHECKOUT / item['path'])}, 'previous_stage_sources'))
    baseline = json.loads((STAGE / 'beginning-source-pins.json').read_text())
    beginning = []
    for item in baseline['files']:
        before = pin(STAGE / 'baseline' / item['path'])
        assert (before['sha256'], before['bytes']) == (item['sha256'], item['bytes'])
        actual = pin(CHECKOUT / item['path'])
        if item['path'] == READER:
            assert actual['sha256'] == READER_AFTER_SHA
            assert actual['sha256'] != item['sha256']
            beginning.append({'path': str(CHECKOUT / item['path']), 'intentional_reader_change': True,
                'before_sha256': item['sha256'], 'after_sha256': actual['sha256'],
                'before_bytes': item['bytes'], 'after_bytes': actual['bytes'],
                'captured_before_bytes_retained': True, 'matched_expected_after': True})
        else:
            beginning.append(check({**item, 'path': str(CHECKOUT / item['path'])}, 'beginning_sources'))
    output = {'schema': 'source-inspector-stage-preservation-check@1',
        'enumeration': 'Only explicit public pins from the previous manifest and preservation receipt; no recursive database, credential, hidden-verifier or transcript scan.',
        'all_checks_passed': True, 'previous_stage_manifest_sha256': H_SEAL_SHA,
        'prior_unchanged_pin_checks': len(checks),
        'prior_unchanged_unique_paths': len({item['path'] for item in checks}),
        'previous_stage_49_public_artifacts_unchanged': True,
        'older_155_pins_unchanged': True, 'previous_stage_four_sources_unchanged': True,
        'v14_nineteen_sources_unchanged': True,
        'beginning_six_captured_source_bytes_retained': True,
        'beginning_five_sources_unchanged_one_reader_delta_expected': True,
        'prior_unchanged_checks': checks, 'beginning_source_checks': beginning}
    with (STAGE / 'preservation-check.json').open('x') as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'prior_unchanged_pin_checks': len(checks),
        'beginning_source_checks': len(beginning), 'all_checks_passed': True}))


if __name__ == '__main__':
    main()
