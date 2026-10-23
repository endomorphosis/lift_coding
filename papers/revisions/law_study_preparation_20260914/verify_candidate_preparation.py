#!/usr/bin/env python3
"""Read-only verification of source-bound candidate specifications, not a study.

No recovered code, model, generated program, container or native task is run.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pyarrow.parquet as pq
from build_legal_cve_proposal import canonical, clean, digest

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]
OLD = BASE / '.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/benchmark/manifests/sources.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(relative):
    return json.loads((HERE / relative).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    old = json.loads(OLD.read_text())['source_records']
    excluded = {tuple(row['ancestry_key']) for row in old}
    excluded_ids = {row['lineage_family_id'] for row in old}
    manifests = {key: read('legal_cve_proposal_v2/' + key + '_candidates.json') for key in ('legal', 'cve')}
    rule_sha = sha(HERE / 'prospective_eligibility_rule.json')
    assert len(manifests['legal']['families']) == 6
    assert len(manifests['cve']['families']) == 12
    bindings = []
    case_ids = []
    full_files = []
    original_artifacts = {}
    for population, manifest in manifests.items():
        assert manifest['eligibility_rule_sha256'] == rule_sha
        assert manifest['model_calls'] == 0 and not manifest['final_cohort_released']
        for family in manifest['families']:
            key = family['ancestry_key']
            identifier = 'family:' + digest(key)
            assert identifier == family['lineage_family_id']
            assert tuple(key) not in excluded and identifier not in excluded_ids
            assert family['scientific_admission'] is False and family['admission_gaps']
            assert len(family['cases']) == 2
            assert family['cases'][0]['input_fixture'] != family['cases'][1]['input_fixture']
            for index, case in enumerate(family['cases']):
                assert case['case_id'] == identifier + ':case-' + str(index)
                assert case['scientific_split'] is None
                assert case['source_output_generation'] == 'not_run'
                assert case['oracle']['model_self_report_sufficient'] is False
                assert case['oracle']['implementation_qualification'] == 'not_run'
                assert case['oracle']['required_effects'] and case['oracle']['forbidden_effects']
                case_ids.append(case['case_id'])
            source = family['source']
            artifact = Path(source['artifact_path'])
            if artifact not in original_artifacts:
                original_artifacts[artifact] = sha(artifact)
            assert original_artifacts[artifact] == source['artifact_sha256']
            retained = source['retained_source']
            row_path = HERE / retained['row']
            assert sha(row_path) == retained['row_file_sha256']
            row = json.loads(row_path.read_text())
            assert hashlib.sha256(canonical(row)).hexdigest() == source['row_sha256']
            if population == 'legal':
                text_path, html_path = HERE / retained['text'], HERE / retained['html']
                assert text_path.read_text() == row['text'] and html_path.read_text() == row['html']
                assert sha(text_path) == source['text_sha256'] and sha(html_path) == source['html_sha256']
                assert source['grounding_anchor'] in row['text']
                assert source['source_url'] == row['url']
                for context in source['context_sources']:
                    context_path = HERE / context['retained_row']
                    assert sha(context_path) == context['retained_row_sha256']
                    context_row = json.loads(context_path.read_text())
                    assert hashlib.sha256(context_row['text'].encode()).hexdigest() == context['text_sha256']
                pinned = source['immutable_mirror_commit']
                assert len(pinned) == 40 and all(c in '0123456789abcdef' for c in pinned)
            else:
                diff_path = HERE / retained['diff']
                assert diff_path.read_text() == row['diff_with_context']
                assert sha(diff_path) == source['diff_sha256']
                assert source['grounding_anchor'] in row['diff_with_context']
                recovery_path = HERE / source['full_file_recovery']
                assert sha(recovery_path) == source['full_file_recovery_sha256']
                recovery = json.loads(recovery_path.read_text())
                assert recovery['resolved_fix_commit'] == source['fix_commit'] == row['hash']
                commit = json.loads((recovery_path.parent / 'commit.body').read_text())
                assert commit['sha'] == row['hash']
                assert [parent['sha'] for parent in commit['parents']] == source['parent_commits']
                anchors = []
                for item in recovery['files']:
                    if not item['available']:
                        continue
                    body = recovery_path.parent / item['response_file']
                    assert sha(body) == item['sha256']
                    receipt = json.loads(body.with_suffix('.receipt.json').read_text())
                    assert receipt['status'] == 200 and receipt['body_sha256'] == item['sha256']
                    if item['version'] == 'fixed' and source['grounding_anchor'] in body.read_text():
                        anchors.append(item['path'])
                    full_files.append({'row': source['physical_row_number'], 'path': item['path'],
                                       'version': item['version'], 'sha256': item['sha256'],
                                       'python3_ast_parse': item.get('python3_ast_parse', 'not_recorded')})
                assert anchors, 'No actual fixed upstream file contains the grounding anchor'
                license_doc = recovery.get('license', {})
                if license_doc.get('available'):
                    assert sha(recovery_path.parent / license_doc['response_file']) == license_doc['sha256']
            bindings.append({'population': population, 'preparation_family_id': identifier,
                             'lineage_family_id': identifier, 'ancestry_key': key,
                             'task': family['operation'], 'scientific_admission': False})
    # Independently compare retained source rows with their actual local originals.
    legal_rows = pq.read_table(next(path for path in original_artifacts if path.name == 'pages.parquet')).to_pylist()
    legal_map = {row['url']: clean(row) for row in legal_rows}
    for family in manifests['legal']['families']:
        assert read(family['source']['retained_source']['row']) == legal_map[family['source']['source_url']]
    cve_by_index = {family['source']['physical_row_number']: family for family in manifests['cve']['families']}
    index = 0
    for batch in pq.ParquetFile(next(path for path in original_artifacts if path.name.startswith('train-'))).iter_batches(batch_size=16):
        for row in batch.to_pylist():
            if index in cve_by_index:
                assert read(cve_by_index[index]['source']['retained_source']['row']) == clean(row)
            index += 1
        if index > max(cve_by_index):
            break
    skill_manifest = read('skill_candidates_v1/source_manifest.json')
    skill_specs = read('skill_candidates_v1/paired_case_specifications.json')
    assert len(skill_manifest['families']) == len(skill_specs['families']) == 12
    skill_cases = {family['family_id']: family['cases'] for family in skill_specs['families']}
    for family in skill_manifest['families']:
        key = ['repository', family['repository']]
        identifier = 'family:' + digest(key)
        assert tuple(key) not in excluded and identifier not in excluded_ids
        assert family['scientific_admission'] is False and family['split'] is None
        assert len(skill_cases[family['family_id']]) == 2
        for case in skill_cases[family['family_id']]:
            case_ids.append(case['case_id'])
        bindings.append({'population': 'skill', 'preparation_family_id': family['family_id'],
                         'lineage_family_id': identifier, 'ancestry_key': key,
                         'task': family['task_key'], 'scientific_admission': False})
    inventory = read('skill_candidates_v1/preparation_inventory.json')
    for relative, item in inventory['files'].items():
        assert sha(HERE / relative) == item['sha256']
    skill_check = subprocess.run([sys.executable, '-B', str(HERE / 'verify_skill_preparation.py')],
                                 check=True, capture_output=True, text=True, timeout=30)
    skill_report = json.loads(skill_check.stdout)
    assert skill_report['status'] == 'PASS_SOURCE_AND_ORACLE_CONTRACT_CHECKS_ONLY'
    assert len(bindings) == len({tuple(item['ancestry_key']) for item in bindings}) == 30
    assert len(case_ids) == len(set(case_ids)) == 60
    report = {
        'schema': 'la-candidate-cohort-source-coverage/v1',
        'status': 'PASS_SOURCE_BINDINGS_AND_DRAFT_SPECIFICATION_COUNTS_ONLY',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'verifier_sha256': sha(Path(__file__)),
        'prospective_rule_sha256': rule_sha,
        'source_manifest_bindings': {str((HERE / ('legal_cve_proposal_v2/' + key + '_candidates.json')).relative_to(HERE)):
                                     sha(HERE / ('legal_cve_proposal_v2/' + key + '_candidates.json')) for key in manifests},
        'skill_preparation_inventory_sha256': sha(HERE / 'skill_candidates_v1/preparation_inventory.json'),
        'historical_manifest_sha256': sha(OLD),
        'historical_families_excluded_by_exact_ancestry': len(excluded),
        'family_counts': dict(Counter(item['population'] for item in bindings)),
        'paired_case_specifications': 60,
        'family_identity_bindings': bindings,
        'actual_source_body_families': 30,
        'cve_complete_upstream_files_recovered': len(full_files),
        'cve_actual_fixed_file_grounding_anchors_verified': 12,
        'cve_root_license_files_recovered': sum(family['source']['root_license_recovered'] for family in manifests['cve']['families']),
        'cve_source_file_python3_ast_status': dict(Counter(item['python3_ast_parse'] for item in full_files)),
        'cve_complete_files': full_files,
        'skill_actual_upstream_source_pins': 0,
        'skill_generated_procedure_pins': 12,
        'skill_constructed_observation_oracle_controls': skill_report['constructed_observation_contract_controls'],
        'skill_native_observer_or_program_qualification': False,
        'legal_cve_oracle_implementation_qualification': False,
        'full_ancestry_fork_near_neighbor_closure': 'pending; exact canonical keys do not prove full closure',
        'scientific_admitted_families': 0, 'scientific_admitted_cases': 0,
        'scientific_attempts_executed': 0, 'target_scientific_attempts': 900,
        'model_calls': 0, 'original_upstream_systems_reproduced': 0,
        'final_cohort_released': False, 'scientific_splits_assigned': False,
        'qualification_boundary': 'This report verifies retained source bytes, source grounding anchors, distinct draft families, explicit draft cases and existing skill oracle contract controls. It does not establish complete upstream system reproduction, source-to-task semantic fidelity, effective native mediation, scientific model performance, or legal validity.'
    }
    if args.report:
        with args.report.open('x') as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('family_identity_bindings', 'cve_complete_files')}, indent=2))


if __name__ == '__main__':
    main()
