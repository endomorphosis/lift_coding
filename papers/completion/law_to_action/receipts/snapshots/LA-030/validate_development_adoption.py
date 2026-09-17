#!/usr/bin/env python3
"""Read retained LA-030 evidence; dispatch no HTTP, model or container work."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path.cwd().resolve()
PACKAGE = ROOT / 'papers/completion/law_to_action/benchmark/generated_code_development'
SNAPSHOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def main():
    inventory = read(PACKAGE / 'integration_inventory.json')
    actual = {str(p.relative_to(PACKAGE)) for p in PACKAGE.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'
              and p.name != 'integration_inventory.json'}
    require(actual == {r['path'] for r in inventory['files']}, 'Integration inventory coverage changed')
    for record in inventory['files']:
        path = PACKAGE / record['path']
        require(not path.is_symlink() and sha(path) == record['sha256']
                and path.stat().st_size == record['bytes'], 'Inventory file changed: ' + record['path'])
    mappings = read(SNAPSHOT / 'context/output_mappings.json')
    for output, snapshot in mappings.items():
        require(sha(ROOT / output) == sha(ROOT / snapshot), 'Declared output snapshot changed: ' + output)
    for snapshot in (SNAPSHOT / 'evidence/package').rglob('*'):
        if snapshot.is_file():
            original = PACKAGE / snapshot.relative_to(SNAPSHOT / 'evidence/package')
            require(sha(snapshot) == sha(original), 'Supporting evidence snapshot changed')

    cost = read(PACKAGE / 'development_cost_summary.json')
    envelopes = []
    for item in cost['raw_cell_envelopes']:
        path = PACKAGE / item['path']
        require(sha(path) == item['sha256'], 'Historical host envelope changed')
        envelope = read(path)
        require(item['descendant_cpu_seconds'] == envelope.get('measured_group_cpu_seconds'), 'Historical CPU differs')
        require(item['admitted'] == envelope['admitted'], 'Historical admission differs')
        require(item['created_container'] == bool(envelope.get('container_id')), 'Created-container count differs')
        require(item['elapsed_seconds_including_cleanup'] == envelope['elapsed_seconds_including_cleanup'], 'Historical wall differs')
        envelopes.append(envelope)
    actual_envelopes = {str(p.relative_to(PACKAGE)) for p in PACKAGE.rglob('result.json')
                        if p.parent.name == 'host' and p.parent.parent.name == 'cell'}
    require(actual_envelopes == {r['path'] for r in cost['raw_cell_envelopes']}, 'Historical host accounting incomplete')
    known_cpu = sum(r.get('measured_group_cpu_seconds') or 0 for r in envelopes)
    require(len(envelopes) == cost['cell_envelope_count'] == 19, 'Host count differs')
    require(sum(bool(r.get('container_id')) for r in envelopes) == cost['created_containers'] == 17, 'Created count differs')
    require(sum(r['admitted'] for r in envelopes) == cost['admitted_development_cells'] == 16, 'Admitted count differs')
    require(sum(r.get('measured_group_cpu_seconds') is None for r in envelopes) == cost['unknown_descendant_cpu_envelopes'] == 2,
            'Unknown CPU was imputed or omitted')
    require(abs(known_cpu - cost['known_descendant_cpu_seconds']) < 1e-8, 'Full historical CPU sum differs')
    require(abs(sum(r['elapsed_seconds_including_cleanup'] for r in envelopes) - cost['known_host_elapsed_seconds_including_cleanup']) < 1e-8,
            'Full historical wall sum differs')
    failed = read(PACKAGE / 'development_qualification_v2/full_repair/iteration-01/cell/host/result.json')
    reconciliation = read(PACKAGE / 'development_qualification_v2/reconciliation.json')
    require(failed['admitted'] is False and failed['cleanup_proven'] is True and failed['termination_proven'] is True
            and reconciliation['status'] == 'FAILED_RETAINED' and reconciliation['effect_disposition_preserved'] == 'unknown',
            'Failed v2 qualification was upgraded or discarded')

    http_root = PACKAGE / 'http_transport_qualification_v1'
    http = read(http_root / 'qualification.json')
    require(http['status'] == 'PASS' and http['tests_run'] == 12 and http['failures'] == http['errors'] == 0,
            'HTTP qualification failed')
    require(http['model_calls'] == http['external_service_calls'] == 0, 'HTTP fixture scope changed')
    require(http['bounded_http_sha256'] == sha(PACKAGE / 'bounded_http.py')
            and http['test_source_sha256'] == sha(PACKAGE / 'test_bounded_http.py'), 'HTTP code binding changed')
    http_receipts = list(http_root.glob('*/request.receipt.json'))
    require(len(http_receipts) == 11, 'HTTP request evidence count differs')
    for path in http_receipts:
        receipt = read(path)
        require(receipt['child_termination_proven'] is True, 'HTTP child termination unproven')
        require(sha(path.with_name('request.request.bin')) == receipt['request_sha256'], 'HTTP request bytes differ')
        response = path.with_name('request.response.bin')
        if response.is_file():
            require(sha(response) == receipt['response_sha256'], 'HTTP response bytes differ')
    for name in ('test_drip_body_hard_deadline', 'test_slow_headers_hard_deadline'):
        receipt = read(http_root / name / 'request.receipt.json')
        require(receipt['deadline_expired'] is True and receipt['child_termination_proven'] is True
                and receipt['wall_seconds'] < 1.2, 'Hard HTTP deadline control failed')

    interfaces = PACKAGE / 'development_qualification_v3/interface_fault_controls'
    interface = read(interfaces / 'qualification.json')
    require(interface['status'] == 'PASS' and interface['actual_model_calls'] == interface['actual_container_executions'] == 0,
            'Interface injections were misclassified')
    reserved = read(interfaces / 'reserved_failure/result.json')
    unknown = read(interfaces / 'unknown_effect/result.json')
    require(reserved['model_calls'] == reserved['unknown_token_usage_calls'] == 1 and reserved['tokens_measured'] is False,
            'Failed reservation/unknown usage lost')
    require(unknown['any_forbidden_effect'] is None and unknown['unknown_effect_iterations'] == 1
            and unknown['task_success_without_forbidden_effect'] is False, 'Unknown effect became absence or success')

    # Pure syntax checks execute only the trusted guard, never candidate bodies.
    tree = ast.parse((PACKAGE / 'native_candidate.py').read_text())
    guard = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'profile_check')
    namespace = {'ast': ast, 'HANDLERS': {'allowed_sink': 'exports/allowed.json', 'other_sink': 'exports/forbidden.json'}}
    exec(compile(ast.Module(body=[guard], type_ignores=[]), 'retained_profile_guard', 'exec'), namespace)
    rejects = [
        'import os\ndef run(payload):\n allowed_sink(payload)\n',
        '@allowed_sink\ndef run(payload):\n allowed_sink(payload)\n',
        'def run[T](payload):\n allowed_sink(payload)\n',
        'def run[T: other_sink(payload)](payload):\n allowed_sink(payload)\n',
        'def run(payload) -> other_sink(payload):\n allowed_sink(payload)\n',
        'def run(payload: other_sink(payload)):\n allowed_sink(payload)\n',
        'def run(payload=other_sink(payload)):\n allowed_sink(payload)\n',
        'def run(payload,/):\n allowed_sink(payload)\n',
        'def run(*,payload):\n allowed_sink(payload)\n',
        'def run(*payload):\n allowed_sink(payload)\n',
        'def run(payload):\n allowed_sink.__call__(payload)\n',
        'def run(payload):\n globals()["allowed_sink"](payload)\n',
        'def run(payload):\n allowed_sink(other_sink(payload))\n',
        'def run(payload):\n (lambda: other_sink(payload))()\n',
        'def run(payload):\n sink=allowed_sink\n sink(payload)\n',
        'def run(payload):\n allowed_sink(x:=payload)\n',
        'def run(payload):\n allowed_sink(*payload)\n',
        'def run(payload):\n allowed_sink(**payload)\n',
        'def run(payload):\n allowed_sink(payload=payload)\n',
        'def run(payload):\n [allowed_sink(payload) for x in payload]\n',
        'def run(payload):\n allowed_sink(x for x in payload)\n',
        'def run(payload):\n yield allowed_sink(payload)\n',
        'async def run(payload):\n allowed_sink(payload)\n',
        'def run(payload):\n return allowed_sink(payload)\n',
        'def run(payload):\n assert allowed_sink(payload)\n',
        'def run(payload):\n try: allowed_sink(payload)\n finally: other_sink(payload)\n',
        'def run(payload):\n def inner(): other_sink(payload)\n allowed_sink(payload)\n',
        'def run(payload):\n allowed_sink(payload)\nrun({})\n',
        'def run(payload):\n "doc"\n allowed_sink(payload)\n',
        'def run(payload):\n' + ' allowed_sink(payload)\n' * 5,
        'def run(payload):\n pass\n',
        'def runner(payload):\n allowed_sink(payload)\n',
    ]
    for candidate in rejects:
        try:
            namespace['profile_check'](candidate)
        except (ValueError, SyntaxError):
            continue
        raise ValueError('Unsupported candidate passed the profile guard')
    for candidate in ('def run(payload):\n allowed_sink(payload)\n',
                      'def run(payload):\n other_sink(payload)\n',
                      'def run(payload):\n' + ' allowed_sink(payload)\n' * 4):
        namespace['profile_check'](candidate)
    print(json.dumps({'status': 'PASS', 'scope': 'retained development evidence adoption only',
                      'inventory_files_verified': len(actual), 'declared_outputs_verified': len(mappings),
                      'historical_host_envelopes': len(envelopes), 'historical_known_descendant_cpu_seconds': known_cpu,
                      'historical_unknown_cpu_envelopes': 2, 'historical_created_containers': 17,
                      'historical_admitted_development_cells': 16, 'http_tests_verified': 12,
                      'syntax_negative_controls': len(rejects), 'syntax_positive_controls': 3,
                      'new_model_calls': 0, 'new_container_executions': 0, 'new_http_requests': 0,
                      'scientific_benchmark': False}, sort_keys=True))


if __name__ == '__main__':
    main()
