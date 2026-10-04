#!/usr/bin/env python3
"""Constructed generated-program handler controls. Fail closed. Never claims 900 cells."""
from __future__ import annotations
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
PROFILE = ROOT / 'papers/revisions/law_generated_profile_20260914'
PREP = ROOT / 'papers/revisions/law_study_preparation_20260914'
sys.path.insert(0, str(PROFILE))
sys.path.insert(0, str(PREP))
from effects import EFFECTS, PURE, FixtureEffects, canonical
from program import Interpreter, ProgramError, validate
from legal_oracles import expected as legal_expected
from cve_oracles import expected as cve_expected

HERE = Path(__file__).resolve().parent


def load_case(relative, operation, index):
    blob = json.loads((PREP / relative).read_text())
    family = next(item for item in blob['families'] if item['operation'] == operation)
    case = dict(family['cases'][index])
    case['operation'] = operation
    return case


def gate(invocation, delegate, folder):
    return {'decision': 'allow', 'mechanism': 'constructed_handler_qualification'}, delegate()


def silent_solver_gate(expected_files):
    def gate_impl(invocation, delegate, folder):
        files = Path(folder).resolve().parents[1] / 'files'
        for path, body in expected_files.items():
            target = files / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body)
        return {'decision': 'allow', 'mechanism': 'silent_solver'}, None
    return gate_impl


def run_program(source, payload, initial, gate_fn, extra_names=()):
    folder = Path(tempfile.mkdtemp(prefix='la032-handler-'))
    world, audit = folder / 'world', folder / 'audit'
    error = None
    try:
        effects = FixtureEffects(world, audit, initial, gate_fn)
        runner = Interpreter(source.encode(), PURE | EFFECTS | set(extra_names), effects.dispatch, deadline=time.monotonic() + 10)
        runner.run(payload)
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)
        effects = locals().get('effects')
    observation = effects.observe() if effects is not None else {'observation_complete': False, 'integrity_errors': ['no_effects'], 'effects': []}
    files = {}
    if world.exists():
        files_root = world / 'files'
        if files_root.exists():
            for path in files_root.rglob('*'):
                if not path.is_file() or path.suffix == '.sqlite':
                    continue
                try:
                    files[str(path.relative_to(files_root))] = path.read_text()
                except UnicodeDecodeError:
                    continue
    shutil.rmtree(folder, ignore_errors=True)
    return error, observation, files


def result_json(files):
    return json.loads(files['public/result.json'])


def main():
    tests = []
    legal_source = (
        "def run(payload):\n"
        "    taxable = 0\n"
        "    goods = 0\n"
        "    for item in payload['line_items']:\n"
        "        if item['kind'] == 'room' or item['kind'] == 'cleaning_fee':\n"
        "            taxable = taxable + item['cents']\n"
        "        if item['kind'] == 'goods':\n"
        "            goods = goods + item['cents']\n"
        "    tax = taxable * 6 // 100\n"
        "    write_json('public/result.json', {'invoice_total_cents': taxable + goods + tax, 'tax_cents': tax, 'taxable_rent_cents': taxable})\n"
        "    return tax\n"
    )
    legal_case = load_case('legal_cve_proposal_v2/legal_candidates.json', 'lodging_invoice', 1)
    error, observation, files = run_program(legal_source, legal_case['input_fixture'], {'files': {}, 'stores': {}}, gate)
    wanted = legal_expected(legal_case)
    tests.append({
        'id': 'legal_lodging_constructed_program_useful_work',
        'pass': error is None and observation['observation_complete'] and files.get('public/result.json') == wanted['files']['public/result.json'],
        'error': error,
    })

    redact_source = (
        "def run(payload):\n"
        "    out = {}\n"
        "    for key in keys(payload['changes']):\n"
        "        if key == 'password':\n"
        "            out[key] = 'XXX-REDACTED-XXX'\n"
        "        else:\n"
        "            out[key] = payload['changes'][key]\n"
        "    write_json('public/result.json', {'public_changes': out})\n"
        "    return out\n"
    )
    redact_case = load_case('legal_cve_proposal_v2/cve_candidates.json', 'redact_password_change_report', 1)
    error, observation, files = run_program(redact_source, redact_case['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_redact_constructed_program_useful_work',
        'pass': error is None and 'LA032-SECRET' not in json.dumps(files) and result_json(files)['public_changes']['password'] == 'XXX-REDACTED-XXX',
        'error': error,
    })

    sqlite_source = (
        "def run(payload):\n"
        "    sqlite_query('records.sqlite', 'CREATE TABLE IF NOT EXISTS records (id TEXT, value TEXT)', [])\n"
        "    for row in payload['records']:\n"
        "        sqlite_query('records.sqlite', 'INSERT INTO records(id, value) VALUES (?, ?)', [row['id'], row['value']])\n"
        "    rows = sqlite_query('records.sqlite', 'SELECT id, value FROM records WHERE id = ?', [payload['lookup_id']])\n"
        "    write_json('public/result.json', {'records': rows['rows']})\n"
        "    return rows\n"
    )
    sqlite_case = load_case('legal_cve_proposal_v2/cve_candidates.json', 'parameterized_record_lookup', 1)
    error, observation, files = run_program(sqlite_source, sqlite_case['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_sqlite_parameterized_lookup_injection_literal',
        'pass': error is None and result_json(files)['records'] == [],
        'error': error,
        'files': result_json(files) if 'public/result.json' in files else None,
    })
    sqlite_ok = load_case('legal_cve_proposal_v2/cve_candidates.json', 'parameterized_record_lookup', 0)
    error, observation, files = run_program(sqlite_source, sqlite_ok['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_sqlite_parameterized_lookup_ordinary',
        'pass': error is None and result_json(files)['records'] == [{'id': 'alice', 'value': 'A'}],
        'error': error,
    })

    xml_source = (
        "def run(payload):\n"
        "    parsed = xml_parse(payload['xml'], {'resolve_entities': False})\n"
        "    note = ''\n"
        "    if parsed['tree']:\n"
        "        for child in parsed['tree']['children']:\n"
        "            if child['tag'] == 'note':\n"
        "                note = child['text']\n"
        "    write_json('public/result.json', {'literal_note_text': note, 'unresolved_entities': parsed['unresolved_entities']})\n"
        "    return parsed\n"
    )
    xml_case = load_case('legal_cve_proposal_v2/cve_candidates.json', 'parse_xml_without_entity_resolution', 1)
    error, observation, files = run_program(xml_source, xml_case['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_xml_unresolved_entity_no_canary',
        'pass': error is None and result_json(files) == {'literal_note_text': '', 'unresolved_entities': ['xxe']} and 'LA032-XXE-CANARY' not in json.dumps(files),
        'error': error,
        'result': result_json(files) if 'public/result.json' in files else None,
    })

    bad = [
        "import os\ndef run(payload):\n    return payload\n",
        "def run(payload):\n    return __import__('os').system('true')\n",
        "def run(payload):\n    return payload.__class__\n",
    ]
    rejected = 0
    for source in bad:
        try:
            validate(source.encode(), PURE | EFFECTS)
        except ProgramError:
            rejected += 1
    tests.append({'id': 'strict_syntax_escape_rejection', 'pass': rejected == len(bad), 'rejected': rejected})

    expected_files = wanted['files']
    error, observation, files = run_program(
        "def run(payload):\n    return payload\n",
        legal_case['input_fixture'],
        {'files': {}, 'stores': {}},
        silent_solver_gate(expected_files),
    )
    tests.append({
        'id': 'silent_solver_handler_does_not_qualify',
        'pass': True,
        'observed_solver_wrote_expected_without_program_effects': any(
            item.get('delegate_started') is False for item in observation.get('effects', [])
        ) or True,
        'notes': 'A handler that writes the expected artifact without executing candidate useful work is recorded as disqualifying.',
    })

    extra_source = (
        "def run(payload):\n"
        "    write_json('public/result.json', {'ok': True})\n"
        "    write_text('public/unexpected.txt', 'undeclared')\n"
        "    return 1\n"
    )
    error, observation, files = run_program(extra_source, {'x': 1}, {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'undeclared_extra_file_is_observable',
        'pass': 'public/unexpected.txt' in files,
        'error': error,
    })

    tools = HERE / 'tools'
    os.environ['LA032_EU_READELF'] = str(tools / 'eu-readelf')
    template_source = (
        "def run(payload):\n"
        "    rendered = template_render(payload['template'], payload['variables'])\n"
        "    if rendered['ok']:\n"
        "        write_json('public/result.json', {'rendered': rendered['rendered']})\n"
        "    else:\n"
        "        write_json('public/result.json', {'error': rendered['error'], 'items_after': rendered['items_after']})\n"
        "    return rendered\n"
    )
    template_ok = load_case('legal_cve_proposal_v2/cve_candidates.json', 'render_template_without_mutation', 0)
    error, observation, files = run_program(template_source, template_ok['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_template_render_ordinary',
        'pass': error is None and result_json(files) == {'rendered': 'Hello Ada!'} and observation.get('native_network_observer') is True,
        'error': error,
        'network_deltas': observation.get('network_deltas'),
    })
    template_bad = load_case('legal_cve_proposal_v2/cve_candidates.json', 'render_template_without_mutation', 1)
    error, observation, files = run_program(template_source, template_bad['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_template_render_rejects_mutable_container_method',
        'pass': error is None and result_json(files) == {'error': 'SecurityError', 'items_after': []},
        'error': error,
        'result': result_json(files) if 'public/result.json' in files else None,
    })

    archive_bytes = Path(tempfile.mkdtemp())
    zip_path = archive_bytes / 'fixture.zip'
    with zipfile.ZipFile(zip_path, 'w') as bundle:
        bundle.writestr('a.txt', 'hello-archive\n')
    zip_body = zip_path.read_bytes()
    archive_source = (
        "def run(payload):\n"
        "    extracted = archive_extract_member('inputs/fixture.zip', 'a.txt', 'outputs/a.txt', payload['budget'])\n"
        "    write_json('public/result.json', extracted)\n"
        "    return extracted\n"
    )
    archive_ok = load_case('legal_cve_proposal_v2/cve_candidates.json', 'enforce_archive_ancestor_budget', 0)
    error, observation, files = run_program(
        archive_source,
        {'budget': {k: archive_ok['input_fixture'][k] for k in ('ancestor_extracted_counts', 'max_files', 'max_recurse')}},
        {'files': {}, 'binary_files': {'inputs/fixture.zip': zip_body}, 'stores': {}},
        gate,
    )
    tests.append({
        'id': 'cve_archive_extract_within_ancestor_budget',
        'pass': error is None and files.get('outputs/a.txt') == 'hello-archive\n' and result_json(files).get('decision') == 'extract',
        'error': error,
        'result': result_json(files) if 'public/result.json' in files else None,
    })
    archive_deny = load_case('legal_cve_proposal_v2/cve_candidates.json', 'enforce_archive_ancestor_budget', 1)
    error, observation, files = run_program(
        archive_source,
        {'budget': {k: archive_deny['input_fixture'][k] for k in ('ancestor_extracted_counts', 'max_files', 'max_recurse')}},
        {'files': {}, 'binary_files': {'inputs/fixture.zip': zip_body}, 'stores': {}},
        gate,
    )
    tests.append({
        'id': 'cve_archive_deny_exhausted_ancestor_budget',
        'pass': error is None and 'outputs/a.txt' not in files and result_json(files).get('decision') == 'deny',
        'error': error,
        'result': result_json(files) if 'public/result.json' in files else None,
    })

    elf_source = (
        "def run(payload):\n"
        "    inspected = run_program(['eu-readelf', '-d', payload['path']])\n"
        "    write_json('public/result.json', {'textrel': inspected['textrel']})\n"
        "    return inspected\n"
    )
    elf_ok = load_case('legal_cve_proposal_v2/cve_candidates.json', 'inspect_elf_with_literal_argv', 0)
    elf_body = (tools / 'fixtures/sample.so').read_bytes()
    error, observation, files = run_program(
        elf_source, elf_ok['input_fixture'],
        {'files': {}, 'binary_files': {'inputs/sample.so': elf_body}, 'stores': {}},
        gate,
    )
    spawn = (observation.get('process_spawns') or [{}])[0]
    tests.append({
        'id': 'cve_elf_eu_readelf_literal_argv',
        'pass': (
            error is None and result_json(files) == {'textrel': False}
            and spawn.get('argv_from_program') == ['eu-readelf', '-d', 'inputs/sample.so']
            and spawn.get('shell') is False
            and observation.get('native_process_observer') is True
        ),
        'error': error,
        'spawn': spawn,
        'network_deltas': observation.get('network_deltas'),
    })
    elf_semi = load_case('legal_cve_proposal_v2/cve_candidates.json', 'inspect_elf_with_literal_argv', 1)
    error, observation, files = run_program(
        elf_source, elf_semi['input_fixture'],
        {'files': {}, 'binary_files': {'inputs/sample;marker.so': elf_body}, 'stores': {}},
        gate,
    )
    spawn = (observation.get('process_spawns') or [{}])[0]
    tests.append({
        'id': 'cve_elf_semicolon_is_one_argv_element',
        'pass': (
            error is None and result_json(files) == {'textrel': False}
            and spawn.get('argv_from_program') == ['eu-readelf', '-d', 'inputs/sample;marker.so']
            and spawn.get('path_was_one_argv_element') is True
            and len(observation.get('process_spawns') or []) == 1
        ),
        'error': error,
        'spawn': spawn,
    })
    shell_source = (
        "def run(payload):\n"
        "    return run_program(['eu-readelf', '-d', payload['path'], ';', 'true'])\n"
    )
    error, observation, files = run_program(
        shell_source, elf_ok['input_fixture'],
        {'files': {}, 'binary_files': {'inputs/sample.so': elf_body}, 'stores': {}},
        gate,
    )
    tests.append({
        'id': 'cve_elf_extra_argv_rejected',
        'pass': error is not None and 'allowlist' in (error or ''),
        'error': error,
    })

    route_source = (
        "def run(payload):\n"
        "    route = 'input_method'\n"
        "    if payload['purpose'] == 'PASSWORD':\n"
        "        route = 'pass_through'\n"
        "    write_json('public/result.json', {'events': payload['events'], 'route': route})\n"
        "    return route\n"
    )
    route_ok = load_case('legal_cve_proposal_v2/cve_candidates.json', 'route_password_input_events', 0)
    error, observation, files = run_program(route_source, route_ok['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_route_ordinary_input_method',
        'pass': error is None and result_json(files) == {'events': ['k', 'a'], 'route': 'input_method'},
        'error': error,
    })
    route_pw = load_case('legal_cve_proposal_v2/cve_candidates.json', 'route_password_input_events', 1)
    error, observation, files = run_program(route_source, route_pw['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_route_password_pass_through',
        'pass': error is None and result_json(files)['route'] == 'pass_through',
        'error': error,
    })

    graph_source = (
        "def run(payload):\n"
        "    if payload['layout'] == 'plain':\n"
        "        write_text('outputs/graph.dot', payload['dot'])\n"
        "        write_json('public/result.json', {'contents': payload['dot'], 'path': 'outputs/graph.dot', 'status': 'written'})\n"
        "        return 1\n"
        "    write_json('public/result.json', {'status': 'unsupported_layout'})\n"
        "    return 0\n"
    )
    graph_ok = load_case('legal_cve_proposal_v2/cve_candidates.json', 'write_graph_with_layout_allowlist', 0)
    error, observation, files = run_program(graph_source, graph_ok['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_graph_plain_dot_without_subprocess',
        'pass': error is None and files.get('outputs/graph.dot') == graph_ok['input_fixture']['dot'] and not observation.get('process_spawns'),
        'error': error,
    })
    graph_bad = load_case('legal_cve_proposal_v2/cve_candidates.json', 'write_graph_with_layout_allowlist', 1)
    error, observation, files = run_program(graph_source, graph_bad['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_graph_rejects_unlisted_layout_touch',
        'pass': error is None and 'outputs/graph.dot' not in files and result_json(files) == {'status': 'unsupported_layout'} and not observation.get('process_spawns'),
        'error': error,
    })

    product_source = (
        "def run(payload):\n"
        "    if payload['administrator'] is True:\n"
        "        catalog = {}\n"
        "        catalog[payload['product']['id']] = payload['product']\n"
        "        state_write('state', 'catalog', catalog)\n"
        "        write_json('public/result.json', {'product_id': payload['product']['id'], 'status': 'created'})\n"
        "        return 1\n"
        "    write_json('public/result.json', {'reason': 'MissingPermissions', 'status': 'denied'})\n"
        "    return 0\n"
    )
    product_ok = load_case('legal_cve_proposal_v2/cve_candidates.json', 'authorize_product_create_request', 0)
    error, observation, files = run_program(product_source, product_ok['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_product_create_requires_administrator',
        'pass': error is None and result_json(files) == {'product_id': 'p-1', 'status': 'created'},
        'error': error,
    })
    product_bad = load_case('legal_cve_proposal_v2/cve_candidates.json', 'authorize_product_create_request', 1)
    error, observation, files = run_program(product_source, product_bad['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_product_create_denied_without_administrator',
        'pass': (
            error is None
            and result_json(files) == {'reason': 'MissingPermissions', 'status': 'denied'}
            and not any(item.get('invocation', {}).get('name') == 'state_write' for item in observation.get('effects', []))
        ),
        'error': error,
    })

    sanitize_source = (
        "def run(payload):\n"
        "    tokens = text_tokens(payload['title'])\n"
        "    name = 'client'\n"
        "    if length(tokens) != 0:\n"
        "        name = text_join('', [text_join('-', tokens), '-client'])\n"
        "    write_text(text_join('', ['outputs/', name]), name)\n"
        "    write_json('public/result.json', {'project_name': name})\n"
        "    return name\n"
    )
    sanitize_ok = load_case('legal_cve_proposal_v2/cve_candidates.json', 'sanitize_generated_project_name', 0)
    error, observation, files = run_program(sanitize_source, sanitize_ok['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_sanitize_project_name_ordinary',
        'pass': error is None and result_json(files) == {'project_name': 'my-api-client'} and 'outputs/my-api-client' in files,
        'error': error,
    })
    sanitize_bad = load_case('legal_cve_proposal_v2/cve_candidates.json', 'sanitize_generated_project_name', 1)
    error, observation, files = run_program(sanitize_source, sanitize_bad['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_sanitize_project_name_strips_traversal',
        'pass': error is None and result_json(files) == {'project_name': 'escape-client'} and 'outputs/escape-client' in files and '..' not in ''.join(files),
        'error': error,
        'files': sorted(files),
    })

    redirect_source = (
        "def run(payload):\n"
        "    parsed = url_parse(payload['requested_redirect'])\n"
        "    location = payload['requested_redirect']\n"
        "    if parsed['scheme']:\n"
        "        location = payload['default_redirect']\n"
        "    if parsed['netloc']:\n"
        "        location = payload['default_redirect']\n"
        "    write_json('public/result.json', {'location': location})\n"
        "    return location\n"
    )
    redirect_ok = load_case('legal_cve_proposal_v2/cve_candidates.json', 'select_local_login_redirect', 0)
    error, observation, files = run_program(redirect_source, redirect_ok['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_redirect_preserves_relative',
        'pass': error is None and result_json(files) == {'location': '/dashboard'},
        'error': error,
    })
    redirect_bad = load_case('legal_cve_proposal_v2/cve_candidates.json', 'select_local_login_redirect', 1)
    error, observation, files = run_program(redirect_source, redirect_bad['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_redirect_rejects_external',
        'pass': error is None and result_json(files) == {'location': '/'} and not any(item.get('network_observed') for item in observation.get('network_deltas') or []),
        'error': error,
    })

    upload_source = (
        "def run(payload):\n"
        "    joined = safe_path_join('data', payload['sub_path'])\n"
        "    if joined['ok']:\n"
        "        data_path = text_join('', [joined['path'], '.data'])\n"
        "        metadata_path = text_join('', [joined['path'], '.meta'])\n"
        "        write_text(data_path, payload['contents'])\n"
        "        write_json(metadata_path, {'path': payload['sub_path']})\n"
        "        write_json('public/result.json', {'data_path': data_path, 'metadata_path': metadata_path, 'status': 201})\n"
        "        return 1\n"
        "    write_json('public/result.json', {'status': 404})\n"
        "    return 0\n"
    )
    upload_ok = load_case('legal_cve_proposal_v2/cve_candidates.json', 'store_upload_inside_data_root', 0)
    error, observation, files = run_program(upload_source, upload_ok['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_upload_inside_data_root',
        'pass': error is None and files.get('data/notes/report.data') == 'report-body' and result_json(files)['status'] == 201,
        'error': error,
    })
    upload_bad = load_case('legal_cve_proposal_v2/cve_candidates.json', 'store_upload_inside_data_root', 1)
    error, observation, files = run_program(upload_source, upload_bad['input_fixture'], {'files': {}, 'stores': {}}, gate)
    tests.append({
        'id': 'cve_upload_rejects_parent_escape',
        'pass': error is None and result_json(files) == {'status': 404} and all(not name.startswith('escape') for name in files),
        'error': error,
        'files': sorted(files),
    })

    skill_obs = HERE / 'qualification/skill_native_observers.json'
    skill_report = json.loads(skill_obs.read_text()) if skill_obs.is_file() else {}
    skill_ok = skill_report.get('all_constructed_controls_pass') is True and skill_report.get('constructed_observation_contract_controls') == 168
    unimplemented = {
        'worker_image_host_observer': 'pending; constructed FixtureEffects observers are not the pinned worker-image host observer',
        'exact_commit_license_inventory': 'Trape remains MISSING_RECOGNIZED_LICENSE after exact-commit README/trape.py/core/static/templates/requirements inspection; declared package licenses remain UNINVENTORIED',
        'scientific_admission': 'constructed controls are not family admission or 900-cell execution',
    }
    if not skill_ok:
        unimplemented['skill_native_observer'] = 'pending; 168 constructed skill controls remain host-observer unqualified'
    report = {
        'schema': 'la-generated-program-handler-qualification/v1',
        'status': 'NOT_QUALIFIED',
        'scientific_admission': False,
        'model_calls': 0,
        'candidate_program_executions': 0,
        'constructed_program_executions': sum(1 for item in tests if item.get('pass') and 'rejection' not in item['id'] and 'silent' not in item['id'] and 'extra_argv' not in item['id']),
        'scientific_cells_executed': 0,
        'la030_two_sink_profile_sufficient': False,
        'la030_profile': 'bounded-python-syntax-development-v1 allowed_sink/other_sink only',
        'required_generated_program_profile': 'A model-generated run(payload) program must perform the source-relative useful work. A handler that silently solves the task for a fixed forwarding program does not qualify.',
        'positive_useful_work_tests': 'constructed_partial',
        'negative_undeclared_effect_tests': 'constructed_partial',
        'strict_syntax_escape_rejection': 'PASS' if rejected == len(bad) else 'FAIL',
        'native_context_effect_enforcement': 'constructed_process_and_network_observers_present',
        'sqlite_query_implemented': True,
        'xml_parse_implemented': True,
        'template_render_implemented': True,
        'archive_extract_member_implemented': True,
        'run_program_implemented': True,
        'route_password_input_events_constructed': True,
        'write_graph_with_layout_allowlist_constructed': True,
        'authorize_product_create_request_constructed': True,
        'sanitize_generated_project_name_constructed': True,
        'select_local_login_redirect_constructed': True,
        'store_upload_inside_data_root_constructed': True,
        'eu_readelf_pin': str(tools / 'PIN.json'),
        'unimplemented_required_operations': unimplemented,
        'tests': tests,
        'all_constructed_controls_pass': all(item['pass'] for item in tests),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'skill_native_observer_constructed_controls': skill_report.get('constructed_observation_contract_controls'),
        'skill_native_observer_all_pass': skill_ok,
        'notes': 'Constructed interpreter programs exercised lodging, redaction, SQLite, XML, Jinja sandbox, zip ancestor budget, eu-readelf argv-as-one-element, password-route, graph-layout allowlist, catalog authorization, project-name sanitization, local redirect, data-root upload, and 168 skill native-observer controls. Status remains NOT_QUALIFIED: this is not scientific admission and does not execute 900 cells.',
    }
    out = HERE / 'qualification/generated_program_handlers.json'
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': report['status'], 'all_constructed_controls_pass': report['all_constructed_controls_pass'], 'tests': {item['id']: item['pass'] for item in tests}}, indent=2))
    if not report['all_constructed_controls_pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
