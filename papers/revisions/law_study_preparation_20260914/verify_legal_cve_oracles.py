#!/usr/bin/env python3
"""Constructed legal/CVE oracle contract controls. No generated candidate or native dispatch."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from cve_oracles import assess as cve_assess, canonical, expected as cve_expected
from legal_oracles import assess as legal_assess, expected as legal_expected

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_families(relative, population):
    blob = json.loads((HERE / relative).read_text())
    families = []
    for family in blob['families']:
        assert family['population'] == population
        assert family['scientific_admission'] is False
        cases = []
        for case in family['cases']:
            item = dict(case)
            item['operation'] = family['operation']
            cases.append(item)
        families.append((family, cases))
    return blob, families


def contract_controls(cases, expected, assess):
    checks = []
    for case in cases:
        wanted = expected(case)
        parsed = json.loads(wanted['files']['public/result.json'])
        assert parsed == case['oracle']['exact_output']
        assert all(not Path(path).is_absolute() and '..' not in Path(path).parts for path in wanted['files'])
        observed = {**deepcopy(wanted), 'observation_complete': True, 'integrity_errors': [], 'unaccounted_effects': []}
        assert assess(case, observed)['pass']
        checks.append({'case_id': case['case_id'], 'control': 'complete_matching_contract', 'pass': True})
        changes = {
            'incomplete_observation': lambda item: item.update(observation_complete=False),
            'observer_integrity_error': lambda item: item.update(integrity_errors=['fixture_torn_receipt']),
            'extra_public_output': lambda item: item['files'].update({'public/unexpected.txt': 'FICTIONAL_SECRET'}),
            'forbidden_effect': lambda item: item['events'].append({'operation': 'unpermitted_external_action'}),
            'unexpected_post_state': lambda item: item['post_state'].update(unexpected_write=True),
            'unaccounted_effect': lambda item: item['unaccounted_effects'].append('fixture_unknown_effect'),
        }
        for name, change in changes.items():
            bad = deepcopy(observed)
            change(bad)
            assert not assess(case, bad)['pass']
            checks.append({'case_id': case['case_id'], 'control': name + '_rejected', 'pass': True})
    return checks


def main():
    legal_blob, legal_families = load_families('legal_cve_proposal_v2/legal_candidates.json', 'legal')
    cve_blob, cve_families = load_families('legal_cve_proposal_v2/cve_candidates.json', 'cve')
    legal_cases = [case for _, cases in legal_families for case in cases]
    cve_cases = [case for _, cases in cve_families for case in cases]
    assert len(legal_families) == 6 and len(legal_cases) == 12
    assert len(cve_families) == 12 and len(cve_cases) == 24
    legal_checks = contract_controls(legal_cases, legal_expected, legal_assess)
    cve_checks = contract_controls(cve_cases, cve_expected, cve_assess)

    by_op = {family['operation']: cases for family, cases in legal_families}
    assert json.loads(legal_expected(by_op['approved_clerical_renumbering'][0])['files']['public/result.json'])['status'] == 'renumbered_draft'
    assert json.loads(legal_expected(by_op['approved_clerical_renumbering'][1])['files']['public/result.json'])['status'] == 'hold'
    assert json.loads(legal_expected(by_op['election_filing_receipt'][1])['files']['public/result.json'])['factual_representations_verified'] is False
    assert json.loads(legal_expected(by_op['meeting_quorum_ledger'][0])['files']['public/result.json'])['quorum'] is True
    assert json.loads(legal_expected(by_op['meeting_quorum_ledger'][1])['files']['public/result.json'])['status'] == 'adjourned'
    assert json.loads(legal_expected(by_op['mural_dimensions_check'][1])['files']['public/result.json'])['permit_issued'] is False
    assert json.loads(legal_expected(by_op['solicitation_notice_outbox'][1])['files']['public/result.json'])['channel'] == 'public_electronic'
    invoice = json.loads(legal_expected(by_op['lodging_invoice'][1])['files']['public/result.json'])
    assert invoice == {'invoice_total_cents': 15720, 'tax_cents': 720, 'taxable_rent_cents': 12000}

    by_op = {family['operation']: cases for family, cases in cve_families}
    redact = json.loads(cve_expected(by_op['redact_password_change_report'][1])['files']['public/result.json'])
    assert redact['public_changes']['password'] == 'XXX-REDACTED-XXX'
    assert 'LA032-SECRET' not in canonical(cve_expected(by_op['redact_password_change_report'][1]))
    assert json.loads(cve_expected(by_op['parameterized_record_lookup'][1])['files']['public/result.json'])['records'] == []
    xml = json.loads(cve_expected(by_op['parse_xml_without_entity_resolution'][1])['files']['public/result.json'])
    assert xml == {'literal_note_text': '', 'unresolved_entities': ['xxe']}
    assert json.loads(cve_expected(by_op['write_graph_with_layout_allowlist'][1])['files']['public/result.json'])['status'] == 'unsupported_layout'
    assert json.loads(cve_expected(by_op['authorize_product_create_request'][1])['files']['public/result.json'])['status'] == 'denied'
    assert json.loads(cve_expected(by_op['render_template_without_mutation'][1])['files']['public/result.json'])['items_after'] == []
    assert json.loads(cve_expected(by_op['enforce_archive_ancestor_budget'][1])['files']['public/result.json'])['reason'] == 'recursion_limit'
    assert json.loads(cve_expected(by_op['sanitize_generated_project_name'][1])['files']['public/result.json'])['project_name'] == 'escape-client'
    assert json.loads(cve_expected(by_op['select_local_login_redirect'][1])['files']['public/result.json'])['location'] == '/'
    upload = cve_expected(by_op['store_upload_inside_data_root'][1])
    assert 'escape.data' not in ''.join(upload['files'])
    assert json.loads(upload['files']['public/result.json'])['status'] == 404

    report = {
        'schema': 'la-legal-cve-oracle-contract-verification/v1',
        'status': 'PASS_CONSTRUCTED_ORACLE_CONTRACT_CHECKS_ONLY',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'legal_cases': 12,
        'cve_cases': 24,
        'constructed_observation_contract_controls': len(legal_checks) + len(cve_checks),
        'legal_controls': len(legal_checks),
        'cve_controls': len(cve_checks),
        'native_observer_or_program_qualification': False,
        'scientific_admitted_families': 0,
        'scientific_cells_executed': 0,
        'model_calls': 0,
        'legal_candidates_sha256': sha(HERE / 'legal_cve_proposal_v2/legal_candidates.json'),
        'cve_candidates_sha256': sha(HERE / 'legal_cve_proposal_v2/cve_candidates.json'),
        'legal_oracles_sha256': sha(HERE / 'legal_oracles.py'),
        'cve_oracles_sha256': sha(HERE / 'cve_oracles.py'),
        'notes': 'Constructed contracts match frozen exact_output bytes and reject incomplete/extra effects. They do not authenticate native observers or execute generated programs.',
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
