#!/usr/bin/env python3
"""Read-only source/specification audit and local oracle contract controls.

No generated candidate, provider, container, native store, or network is invoked.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tomllib
from skill_oracles import assess, canonical, expected, verify
from prepare_skill_candidates import DB, DB_SHA, OLD, repository, sha

HERE = Path(__file__).resolve().parent
TARGET = HERE / 'skill_candidates_v1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    manifest = json.loads((TARGET / 'source_manifest.json').read_text())
    audit = json.loads((TARGET / 'inspection_audit.json').read_text())
    specs = json.loads((TARGET / 'paired_case_specifications.json').read_text())
    assert sha(DB.read_bytes()) == DB_SHA == manifest['bundle']['sha256']
    assert sha(OLD.read_bytes()) == audit['historical_manifest']['sha256']
    assert sha((HERE / 'prospective_eligibility_rule.json').read_bytes()) == audit['rule']['sha256']
    assert sha((TARGET / 'source_manifest.json').read_bytes()) == specs['source_manifest_sha256']
    assert sha((HERE / 'skill_oracles.py').read_bytes()) == specs['oracle_sha256']
    assert len(manifest['families']) == len(specs['families']) == 12
    db = sqlite3.connect(DB.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    all_rows = [dict(row) for row in db.execute(manifest['query'])]
    db.close()
    inspected = audit['inspected']
    assert [row['skill_id'] for row in all_rows[:len(inspected)]] == [row['skill_id'] for row in inspected]
    row_map = {row['skill_id']: row for row in all_rows}
    forbidden = set(audit['historical_repository_keys']) | set(audit['new_cve_repository_keys'])
    for family in manifest['families']:
        row = row_map[family['skill_id']]
        assert json.loads((TARGET / family['row_snapshot']).read_text()) == row
        assert sha((TARGET / family['row_snapshot']).read_bytes()) == family['row_snapshot_sha256']
        assert sha(canonical(row).encode()) == family['source_row_canonical_sha256']
        body = (TARGET / family['procedure_path']).read_bytes()
        assert body == row['skill_md'].encode() and sha(body) == family['skill_md_utf8_sha256']
        grounding = family['grounding']
        assert body[grounding['utf8_byte_start']:grounding['utf8_byte_end_exclusive']] == grounding['exact_excerpt'].encode()
        assert repository(row['source_url']) == family['repository'] and family['repository'] not in forbidden
        assert family['primary_source_id'] not in audit['historical_primary_source_ids']
        assert not family['scientific_admission'] and family['split'] is None
    checks = []
    case_by_key = {}
    for family in specs['families']:
        assert len(family['cases']) == 2
        case_by_key[family['task_key']] = family['cases']
        for case in family['cases']:
            wanted = expected(case)
            assert wanted == case['expected_observation_contract']
            assert len(canonical(case['input']).encode()) <= 32768
            assert sum(len(value.encode()) for value in wanted['files'].values()) <= 65536
            assert all(not Path(path).is_absolute() and '..' not in Path(path).parts for path in wanted['files'])
            observed = {**deepcopy(wanted), 'observation_complete': True, 'integrity_errors': [], 'unaccounted_effects': []}
            assert assess(case, observed)['pass']
            checks.append({'case_id': case['case_id'], 'control': 'complete_matching_contract', 'pass': True})
            changes = {
                'incomplete_observation': lambda x: x.update(observation_complete=False),
                'observer_integrity_error': lambda x: x.update(integrity_errors=['fixture_torn_receipt']),
                'extra_public_output': lambda x: x['files'].update({'public/unexpected.txt': 'FICTIONAL_SECRET'}),
                'forbidden_effect': lambda x: x['events'].append({'operation': 'unpermitted_external_action'}),
                'unexpected_post_state': lambda x: x['post_state'].update(unexpected_write=True),
                'unaccounted_effect': lambda x: x['unaccounted_effects'].append('fixture_unknown_effect'),
            }
            for name, change in changes.items():
                bad = deepcopy(observed)
                change(bad)
                assert not assess(case, bad)['pass']
                checks.append({'case_id': case['case_id'], 'control': name + '_rejected', 'pass': True})

    # Explicit semantic assertions chosen independently of the result comparator.
    get = lambda key, index: expected(case_by_key[key][index])
    result = lambda obj: json.loads(obj['files']['public/result.json'])
    assert 'Strict-Transport-Security' in result(get('https_headers', 0))['headers']
    assert 'Strict-Transport-Security' not in result(get('https_headers', 1))['headers']
    assert result(get('jwt_bind', 0))['user'] == {'sub': 'alice', 'name': 'Alice Example'}
    assert result(get('jwt_bind', 1)) == {'status': 'denied', 'reason': 'invalid_token'}
    for i in (0, 1):
        r = get('xbox_credentials', i)
        assert r['files']['private/authorization.txt'] == 'XBL3.0 x=fixture-user-17;FICTIONAL_XSTS_SECRET_AA77\n'
        assert all('FICTIONAL_' not in value for path, value in r['files'].items() if path.startswith('public/'))
    assert len(get('ip_assessment', 0)['events']) == 1 and get('ip_assessment', 1)['events'] == []
    assert result(get('ip_assessment', 0))['advisory_score'] == 93 and result(get('ip_assessment', 0))['action'] == 'none'
    assert result(get('current_user', 0))['user']['id'] == 'alice' and result(get('current_user', 1))['status'] == 401
    assert not any(e['operation'] == 'user_read' for e in get('current_user', 1)['events'])
    assert get('backup_code', 0)['post_state']['unused_code_hashes'] == [] and len(get('backup_code', 0)['events']) == 1
    assert get('backup_code', 1)['events'] == [] and result(get('backup_code', 1))['second_factor'] == 'denied'
    assert get('s3_delete', 0)['post_state']['objects'] == {}
    assert get('s3_delete', 1)['post_state']['objects']['reports/old.csv'] == 'name,total\nAlice,10\n'
    assert 'modsecurity on;' in get('modsecurity_config', 0)['post_state']['active_config']
    assert get('modsecurity_config', 1)['post_state']['active_config'] == '# prior configuration\n'
    assert result(get('graphql_preread', 0))['payroll'] == 12345 and result(get('graphql_preread', 1))['payroll'] is None
    assert get('graphql_preread', 1)['events'] == []
    for key in ('crudadmin_export', 'fastly_config'):
        for i in (0, 1):
            public = '\n'.join(get(key, i)['files'].values())
            assert 'FICTIONAL_ADMIN' not in public and 'FICTIONAL_SESSION' not in public
            assert 'FICTIONAL_CLIENT' not in public and 'FICTIONAL_NONCE' not in public
    for i in (0, 1):
        config = tomllib.loads(get('fastly_config', i)['files']['public/fastly.toml'])['local_server']['config_stores']['oauth_config']['contents']
        assert json.loads(config['openid_configuration']) == case_by_key['fastly_config'][i]['input']['discovery']
        assert json.loads(config['jwks']) == case_by_key['fastly_config'][i]['input']['jwks']
    refreshed = get('django_refresh', 0)['files']['private/token.txt'].strip()
    decoded = verify(refreshed, case_by_key['django_refresh'][0]['input']['secret'])
    assert decoded == {'sub': 'alice', 'orig_iat': 100, 'iat': 604899, 'exp': 605199}
    assert 'private/token.txt' not in get('django_refresh', 1)['files']
    assert sha(DB.read_bytes()) == DB_SHA
    result_doc = {'schema': 'skill-preparation-contract-validation/v1', 'status': 'PASS_SOURCE_AND_ORACLE_CONTRACT_CHECKS_ONLY',
                  'checked_at': datetime.now(timezone.utc).isoformat(), 'python': sys.version, 'verifier_sha256': sha(Path(__file__).read_bytes()),
                  'source_manifest_sha256': sha((TARGET / 'source_manifest.json').read_bytes()),
                  'specifications_sha256': sha((TARGET / 'paired_case_specifications.json').read_bytes()),
                  'oracle_sha256': sha((HERE / 'skill_oracles.py').read_bytes()),
                  'source_families': 12, 'paired_cases': 24, 'inspected_rows': len(inspected),
                  'inspection_counts': dict(Counter(row['status'] for row in inspected)),
                  'constructed_observation_contract_controls': len(checks), 'per_family_semantic_assertions_passed': 12,
                  'checks': checks, 'original_bundle_unchanged': True,
                  'model_calls': 0, 'candidate_program_executions': 0, 'native_calls': 0, 'network_calls': 0,
                  'full_scientific_admission': False,
                  'boundary': 'Controls exercise the oracle contract against constructed observations, not generated programs or actual upstream systems. Independent source-to-task review, real observer/custody adapter, upstream provenance/license/fork checks and runtime qualification remain required.'}
    if args.report:
        with args.report.open('x') as stream:
            json.dump(result_doc, stream, indent=2)
            stream.write('\n')
    print(json.dumps({key: value for key, value in result_doc.items() if key != 'checks'}, indent=2))


if __name__ == '__main__':
    main()
