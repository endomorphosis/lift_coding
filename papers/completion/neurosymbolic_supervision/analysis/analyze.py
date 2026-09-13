"""Render only complete, root-reviewed NS017 evidence; never run research code.

Reuse exact frozen reducer arithmetic and original Ed25519 verifier definitions.
No service/native import, model/scorer call, candidate execution or hidden replay.
"""
import argparse
import ast
import base64
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import random
import stat
import subprocess
import sys
import tempfile

P = Path('papers/completion/neurosymbolic_supervision')
ANALYZER = 'ed7ebc7d939c9592537e33a6a37a6962ceaeca84b5da3b5efd0cbb641f652e94'
CLIENT = '4675aeb4e650819cd55f53f737d9426dcd8664a80c50b3f44d0db7a5240c8f84'
OPERATOR_COSTS = 'efc9a050dc3c89f73bda163d1c15753c0df5c25308fece3bf369534b9bff36e1'
PRIOR = P / 'writing_inputs/ns024_prior_evidence_v1/component'
PRIOR_MANIFEST = '1d00715d05bbea2c7cab0ef1892f039153cc12ea0820bd556a13452ffe6b70a7'
POLICY = 'a0edbc1cdf13f1d5aab4170dd60fcb3a3b2ef26d192f6dbbdce9b6a26ff700d3'
FREEZE = '7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a'
FREEZE_CANONICAL = 'ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d'
ARITHMETIC = ('require', 'canon', 'finite', 'measured', 'quantile', 'cell_id', 'validate_rows', 'summarize')
SIGNATURE = ('canon', 'sha', 'require', 'verify_signature', 'receipt_scope', 'verify_disposition')
METRIC_LABELS = {
    'provider_child_elapsed_seconds': 'Provider child',
    'http_wrapper_elapsed_seconds': 'HTTP wrapper',
    'gateway_proposal_elapsed_seconds': 'Gateway proposal',
    'gateway_score_elapsed_seconds': 'Gateway score',
    'grant_to_terminal_elapsed_seconds': 'Grant to terminal observation',
    'client_poll_wall_seconds': 'Client polls wall',
    'client_poll_cpu_seconds': 'Client polls CPU',
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def decode(raw):
    return json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def read(path, expected=None, maximum=16 << 20):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path, 'Canonical regular input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'Input size/type bound')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(maximum + 1)
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'Input changed')
        require(len(raw) == before.st_size, 'Input length changed')
    finally:
        os.close(fd)
    require(expected is None or digest(raw) == expected, 'Input hash differs')
    return raw


def frozen_definitions(raw, expected, names, constants=()):
    """Compile selected definitions from exact reviewed bytes, never their main/imports."""
    require(digest(raw) == expected, 'Frozen arithmetic/verifier source changed')
    tree = ast.parse(raw)
    definitions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    selected = []
    for name in constants:
        matches = [node for node in tree.body if isinstance(node, ast.Assign) and
                   any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
        require(len(matches) == 1, 'Frozen constant absent/ambiguous')
        selected.extend(matches)
    require(set(names) <= definitions.keys(), 'Frozen function absent')
    selected.extend(definitions[name] for name in names)
    env = dict(hashlib=hashlib, json=json, math=math, random=random, collections=collections,
               base64=base64, tempfile=tempfile, subprocess=subprocess, Path=Path)
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])),
                 '<hash-bound-existing-definitions>', 'exec'), env)
    return env


def complete_guard(manifest, review, analysis):
    require(manifest.get('schema') == 'ns017-actual-final32-main-adoption/v1', 'Actual NS017 bundle required')
    require(all(type(manifest.get(k)) is int and manifest[k] == v for k, v in
                [('planned_cells', 32), ('terminal_cells', 32), ('independent_families', 8),
                 ('nested_repetitions_per_family_arm', 2)]), 'Complete fixed32 manifest required')
    require(manifest['freeze_file_sha256'] == FREEZE and manifest['freeze_canonical_sha256'] == FREEZE_CANONICAL
            and manifest['analysis_policy_sha256'] == POLICY, 'Original freeze/policy required')
    require(review.get('schema') == 'ns-final32-root-complete-evidence-review/v1'
            and review.get('accepted_actual_final32') is True and review.get('fixture') is False,
            'Actual root complete evidence review required')
    require(type(review.get('actual_terminal_cells')) is int and review['actual_terminal_cells'] == 32
            and review.get('all_terminal_client_cleanup_verified') is True
            and type(review.get('unknown_local_termination_count')) is int
            and review['unknown_local_termination_count'] == 0
            and review.get('strict_reducer_allow_partial') is False, 'Complete reviewed termination required')
    require(analysis.get('schema') == 'ns-final32-retained-evidence-analysis/v1'
            and analysis.get('complete') is True
            and all(type(analysis.get(k)) is int and analysis[k] == v for k, v in
                    [('planned_cells', 32), ('terminal_cells', 32), ('missing_or_nonterminal', 0)]),
            'Partial analysis cannot render publication outputs')
    require(len(analysis.get('rows', [])) == 32 and all(row['terminal'] is True for row in analysis['rows']),
            'All32 actual terminal rows required')
    require([row['cell_id'] for row in analysis['rows']] == manifest['ordered_cells'] == review['ordered_cells']
            and len(set(manifest['ordered_cells'])) == 32, 'Exact original ordering required')
    require(analysis['analysis_policy_sha256'] == POLICY and analysis['freeze_sha256'] == FREEZE,
            'Analysis freeze/policy differs')
    for key in ('new_provider_calls', 'new_scorer_calls', 'new_native_calls'):
        require(type(analysis.get(key)) is int and analysis[key] == 0, 'Reducer effect claim differs')
    require(all(row.get('human_annotation') is False for row in analysis['rows']), 'Human annotation cannot be invented')


def ablation_inputs(repository, expected_sha, order):
    directory = repository / P / 'runs/ablations'
    ablation = decode(read(directory / 'manifest.json', expected_sha))
    require(ablation['schema'] == 'ns018-withdrawn-ablations-manifest/v1'
            and ablation['freeze_file_sha256'] == FREEZE and ablation['freeze_sha256'] == FREEZE_CANONICAL,
            'Original NS018 withdrawal scope required')
    require(all(type(ablation[k]) is int and ablation[k] == 0 for k in
                ('main_outcome_rows_included','measured_ablation_attempt_rows','measured_ablation_resource_rows'))
            and ablation['uses_final_outcomes_or_partial_results'] is False,
            'Ablation withdrawal cannot contain measured or partial main results')
    population = ablation['population']
    require(population['original_planned_factor_cells'] == 192
            and population['retained_main_cells'] == 32 and population['withdrawn_planned_factor_cells'] == 160
            and population['withdrawn_disjoint_partition'] == {'non_AB_arm':128,'AB_local_warm':32}
            and [r['final_cell_id'] for r in ablation['retained_main_planned_cells']] == order
            and len(ablation['withdrawn_planned_cells']) == 160, 'Exact withdrawal population differs')
    for name in ('attempts.jsonl', 'resource_measurements.jsonl', 'deviations.md'):
        raw = read(directory / name, ablation['files'][name]['sha256'])
        require(len(raw) == ablation['files'][name]['bytes'], 'Ablation file length differs')
        if name.endswith('.jsonl'):
            require(raw == b'', 'No measured ablation rows are admitted')
    return ablation


def terminal_digest_guard(row, authority, terminal_raw, analysis_bindings):
    # The reducer's named signed_terminal digest is the operator observation,
    # not the exported signed receipt. Preserve and verify both distinct joins.
    require(digest(terminal_raw) == authority['terminal_sha256'], 'Exported signed terminal differs')
    require(analysis_bindings.get(row['signed_terminal_path']) == row['signed_terminal_sha256'],
            'Retained operator terminal observation binding differs')


def operator_records(costs, analysis, review, object_bytes):
    require(costs['schema'] == 'ns-final32-operator-host-phase-costs/v1'
            and costs['actual_complete32'] is True and costs['analysis'] == review['analysis']
            and costs['activation'] == review['activation']
            and costs['continuation_contract'] == review['continuation_contract']
            and costs['runtime_continuation'] == analysis['runtime_continuation']
            and costs['ordered_cells'] == [r['cell_id'] for r in analysis['rows']]
            and set(costs['cells']) == set(costs['ordered_cells'])
            and costs['all_signed_clocks_unchanged'] is True
            and costs['frozen_analysis_policy_changed'] is False
            and costs['source_sha256'] == OPERATOR_COSTS, 'Exact operator cost custody required')
    helper = frozen_definitions(object_bytes(OPERATOR_COSTS), OPERATOR_COSTS,
                                ('require', 'measured_record'), ('SCOPE', 'PHASES'))
    result = []
    for row in analysis['rows']:
        cell = costs['cells'][row['cell_id']]
        require(cell['number'] == row['number']
                and cell['runtime_source_provenance'] == row['runtime_source_provenance']
                and set(helper['PHASES']) <= cell['records'].keys(), 'Operator cell identity/phases differ')
        for phase, item in cell['records'].items():
            require(item['phase'] == phase and item['scope'] == costs['scope'] == helper['SCOPE']
                    and item['summed_with_nested_clocks'] is False
                    and item['changes_signed_compliance'] is False, 'Operator phase scope differs')
            ref = item['execution']
            if ref is not None:
                original = decode(object_bytes(ref['sha256']))
                require(item == helper['measured_record'](original, ref, phase), 'Recorded operator value differs')
            else:
                require(item['elapsed_host_wall_seconds'] is None and item['measured'] is False
                        and bool(item['missing_reason']), 'Missing operator phase cannot be zero')
            result.append({'number':row['number'], 'cell_id':row['cell_id'], **item,
                           'execution_repository_path': None if ref is None else
                           str(P / 'qualification/operator_inputs/NS-017/objects' / ref['sha256'])})
    return result


def prior_inputs(repository, ledgers):
    manifest = decode(read(repository / PRIOR / 'manifest.json', PRIOR_MANIFEST))
    require(manifest['schema'] == 'ns-anonymous-prior-component/v1'
            and manifest['unsigned_data_replay_only'] is True, 'Exact installed prior component required')
    needed = ('coverage.json','costs/summary.json','costs/records.jsonl','pilot/summary.json',
              'pilot/adopted_costs.jsonl','pilot/timing_disclosure.json','pilot/table.md')
    values = {}; links = {}
    for name in needed:
        spec = manifest['members'][name]
        raw = read(repository / PRIOR / name, spec['sha256'])
        require(len(raw) == spec['bytes'], 'Prior component size differs')
        links[name] = {'repository_path':str(PRIOR / name),'sha256':spec['sha256']}
        if name.endswith('.json'): values[name] = decode(raw)
    coverage = values['coverage.json']; summary = values['costs/summary.json']; pilot = values['pilot/summary.json']
    require([r['sha256'] for r in ledgers] == [r['original_sha256'] for r in coverage['six_ledgers']]
            and all(r['pooled_into_final_outcomes'] is False and r['summed_with_nested_phase_costs'] is False for r in ledgers),
            'Prior component original ledger join differs')
    require(coverage['no_clock_grand_total'] is True and coverage['no_outcome_pooling'] is True
            and summary['schema'] == 'ns-prior-separated-cost-summary/v1'
            and summary['cross_clock_or_cross_scope_addition'] is False and summary['grand_total'] is None,
            'Prior scope cannot be pooled')
    return {'manifest_sha256':PRIOR_MANIFEST,'links':links,'coverage':coverage,
            'separated_summary':summary,'pilot_costs':{k:pilot[k] for k in
                ('planned_cells','gateway_proposal_elapsed_sum_seconds','gateway_score_elapsed_known_sum_seconds',
                 'observed_api_usage','resource_reclassification_applied')},
            'pilot_timing_disclosure':values['pilot/timing_disclosure.json']}


def inputs(repository, manifest_sha, ablation_sha):
    require(sys.version_info[:2] == (3, 12), 'Frozen Python 3.12 arithmetic runtime required')
    repository = Path(repository).resolve()
    raw = read(repository / P / 'runs/main/manifest.json', manifest_sha)
    manifest = decode(raw)
    # Refuse incomplete input before opening retained cell documents or writing.
    require(manifest.get('schema') == 'ns017-actual-final32-main-adoption/v1'
            and type(manifest.get('terminal_cells')) is int and manifest['terminal_cells'] == 32,
            'Complete actual NS017 manifest required')
    objects = manifest['retained_objects']
    by_hash = {}
    by_label = {}
    for item in objects:
        rel = Path(item['repo_path'])
        require(rel == P / 'qualification/operator_inputs/NS-017/objects' / item['sha256'], 'Nonobject input path')
        require(item['sha256'] not in by_hash or
                all(item[k] == by_hash[item['sha256']][k] for k in ('repo_path', 'bytes')),
                'Inconsistent repeated object')
        by_hash.setdefault(item['sha256'], item)
        require(item['label'] not in by_label, 'Ambiguous retained label')
        by_label[item['label']] = item
    def object_bytes(sha):
        item = by_hash[sha]
        value = read(repository / item['repo_path'], sha, 64 << 20)
        require(len(value) == item['bytes'], 'Retained object length differs')
        return value
    def reference(ref):
        require(set(ref) == {'path', 'sha256'}, 'Exact retained reference required')
        # Original private absolute paths are provenance, never filesystem inputs.
        return decode(object_bytes(ref['sha256']))
    def public(cell, name):
        item = by_label['final/' + cell + '/' + name]
        return object_bytes(item['sha256'])
    refs = manifest['private_original_refs']
    analysis = reference(refs['analysis'])
    analysis_bindings = reference(refs['analysis_bindings'])
    review = reference(refs['root_complete_review'])
    complete_guard(manifest, review, analysis)
    for key in ('analysis', 'analysis_bindings', 'activation', 'export_manifest', 'candidate_payload_manifest',
                'public_baseline_manifest', 'validation_disclosures'):
        require(review[key]['sha256'] == refs[key]['sha256'], 'Root evidence reference differs: ' + key)
    require(review['activation'] == analysis['activation'],
            'Root activation differs')
    require(manifest['runtime_continuation'] == analysis['runtime_continuation']
            and review['continuation_contract'] == manifest['runtime_continuation']['contract_binding'],
            'Reviewed runtime continuation differs')
    policy_raw = read(repository / P / 'pilot/recovery/final_input_source/analysis_policy.json', POLICY)
    policy = decode(policy_raw)
    arithmetic = frozen_definitions(object_bytes(ANALYZER), ANALYZER, ARITHMETIC, ('UNITS', 'REPS', 'METRICS'))
    expected = arithmetic['summarize'](analysis['rows'])
    require(encoded({key: analysis.get(key) for key in expected}) == encoded(expected), 'Retained summary differs from frozen arithmetic')
    require(manifest['actual_useful_completions'] == expected['useful_completions']
            and manifest['arm_useful_fixed16'] == expected['arm_useful_fixed16'], 'Manifest counts differ')
    for row in analysis['rows']:
        require(row['cache'] == 'local_cold' and row['number'] == manifest['ordered_cells'].index(row['cell_id']) + 1,
                'Frozen row coordinates differ')
    exports = reference(refs['export_cells'])
    require(exports['schema'] == 'ns-final-root-cell-authority-proposal/v1'
            and exports['batch_sha256'] == analysis['batch_sha256']
            and exports['runtime_continuation'] == manifest['runtime_continuation']
            and set(exports['cells']) == set(manifest['ordered_cells']), 'Exact 32 public authority required')
    signature = frozen_definitions(object_bytes(CLIENT), CLIENT, SIGNATURE, ('REQUEST_KEYS',))
    signatures = 0
    for row in analysis['rows']:
        cid = row['cell_id']; authority = exports['cells'][cid]
        offer_raw = public(cid, 'offer.json'); offer = decode(offer_raw)
        require(digest(offer_raw) == authority['binding']['offer_sha256'], 'Reviewed public key/offer differs')
        original_name = 'proposal.json' if row['original_receipt_filename'] == 'proposal_result.json' else 'response.json'
        original_raw = public(cid, original_name)
        require(digest(original_raw) == row['original_signed_receipt_sha256'], 'Original signed bytes differ')
        if row['disposition_class'] is not None:
            disposition_raw = public(cid, 'disposition.json')
            terminal_digest_guard(row, authority, disposition_raw, analysis_bindings)
            body, disposition = signature['verify_disposition'](
                offer, decode(disposition_raw), original_raw, authority['binding'])
            signatures += 2
            require(disposition['classification'] == row['disposition_class']
                    and row['useful_completion'] is False, 'Failure disposition credit differs')
        else:
            terminal_digest_guard(row, authority, original_raw, analysis_bindings)
            body = signature['verify_signature'](offer, decode(original_raw)); signatures += 1
            signature['receipt_scope'](body, offer, authority['binding'])
            require(body['status'] == 'completed' and body['error'] is None, 'Original is not complete')
        require(body['cell_id'] == cid and body['batch_sha256'] == analysis['batch_sha256']
                and body['final_freeze_sha256'] == FREEZE
                and all(body[k] == row[k] for k in ('unit', 'arm', 'repetition', 'cache')),
                'Signed scope differs from analysis')
    # Check the three published raw projections against the retained analysis by identity.
    for name in ('attempts.jsonl', 'provider_receipts.jsonl', 'resource_measurements.jsonl'):
        rows = [decode(line) for line in read(repository / P / 'runs/main' / name).splitlines()]
        require(len(rows) == 32 and [row['cell_id'] for row in rows] == manifest['ordered_cells'], 'Raw projection order differs')
        for original, projection in zip(analysis['rows'], rows):
            require({'number','cell_id','unit','arm','repetition','cache','terminal','outcome',
                     'useful_completion','original_signed_receipt_sha256','signed_terminal_sha256',
                     'human_annotation','runtime_source_provenance'} <= projection.keys()
                    and encoded({key: projection[key] for key in projection.keys() & original.keys()}) ==
                    encoded({key: original[key] for key in projection.keys() & original.keys()}),
                    'Raw projection changed retained values')
    disclosures = reference(refs['validation_disclosures'])
    operator_costs = reference(review['operator_phase_cost_manifest'])
    operator_rows = operator_records(operator_costs, analysis, review, object_bytes)
    prior = prior_inputs(repository, analysis['prior_and_preparation_cost_ledgers'])
    require(disclosures['actual_complete32'] is True and disclosures['changes_signed_outcomes'] is False
            and disclosures['changes_protocol_or_denominator'] is False, 'Additive disclosure scope differs')
    ablation = ablation_inputs(repository, ablation_sha, manifest['ordered_cells'])
    return manifest, analysis, expected, policy, disclosures, operator_rows, prior, ablation, {
        'manifest_sha256': manifest_sha, 'ablation_manifest_sha256': ablation_sha, 'analysis_sha256': refs['analysis']['sha256'],
        'root_review_sha256': refs['root_complete_review']['sha256'], 'analysis_policy_sha256': POLICY,
        'reducer_source_sha256': ANALYZER, 'signature_function_source_sha256': CLIENT,
        'operator_cost_manifest_sha256': review['operator_phase_cost_manifest']['sha256'],
        'validation_disclosures_sha256': refs['validation_disclosures']['sha256'],
        'operator_projector_source_sha256': OPERATOR_COSTS, 'prior_component_manifest_sha256': PRIOR_MANIFEST,
        'signatures_reverified': signatures,
        'verification_scope': 'Exact original Ed25519 signatures and source/order/freeze joins; retained root bundle supplies full client/resource/candidate review. No new hidden-test, full service or native admission replay.',
    }


def fmt(value):
    return 'unavailable' if value is None else format(value, '.6g')


def tex(value):
    escape = {'\\': r'\textbackslash{}', '_': r'\_', '%': r'\%', '&': r'\&', '#': r'\#',
              '{': r'\{', '}': r'\}', '$': r'\$', '^': r'\textasciicircum{}', '~': r'\textasciitilde{}'}
    return ''.join(escape.get(character, character) for character in str(value))


def md(value):
    if value is None: return 'unavailable'
    return str(value).replace('|', r'\|').replace('\n', ' ')


def cost_details(operator_rows, prior):
    text = '\nOperator phase records (seconds; every record is copied, with no new total):\n\n'
    text += 'These enclosing helper clocks include signing/continuation checks after the signed gateway sampling point. They are separate from all signed/client clocks and introduce no compliance relabeling. Missing phases are neither zero cost nor extra experiments. Links resolve after the reports are adopted at their declared repository paths.\n\n'
    text += '| Cell | Phase | Elapsed host wall | Measured | Missing reason | Exit | Automatic retry | Exact record |\n|---|---|---:|---|---|---|---|---|\n'
    for item in operator_rows:
        ref = item['execution']
        link = 'unavailable' if ref is None else f"[retained record](../qualification/operator_inputs/NS-017/objects/{ref['sha256']})"
        text += '| ' + ' | '.join(md(x) for x in (item['number'],item['phase'],item['elapsed_host_wall_seconds'],
            item['measured'],item['missing_reason'],item.get('exit_code'),item.get('automatic_retry'))) + ' | ' + link + ' |\n'
    prefix = '../writing_inputs/ns024_prior_evidence_v1/component/'
    text += '\nPreviously reported preparation/protocol/lease costs, copied within their original scopes:\n\n'
    text += 'This view copies the installed prior component, whose six original-ledger hashes match the strict analysis. Its known sums are partial measurements, not complete experiment costs. An empty observed sum of zero is retained in the source JSON but displayed as unavailable when no record was observed. No sums, maxima, or estimates are newly calculated here.\n\n'
    text += '| Scope | Clock / units in field name | Retained statistic | Recorded value | Observed | Unknown |\n|---|---|---|---:|---:|---:|\n'
    for scope, group in prior['separated_summary']['scopes'].items():
        for clock, value in group['clocks'].items():
            statistic = 'known_sum' if 'known_sum' in value else 'maximum_observed'
            display = value[statistic] if value['observed_records'] else None
            text += '| ' + ' | '.join(md(x) for x in (scope,clock,statistic,display,
                value['observed_records'],value['unknown_records'])) + ' |\n'
    pilot = prior['pilot_costs']
    text += f"\nPrior pilot (separate {pilot['planned_cells']}-cell developmental cohort; never pooled with final32):\n\n"
    for field in ('gateway_proposal_elapsed_sum_seconds','gateway_score_elapsed_known_sum_seconds'):
        text += f"- {field}: {md(pilot[field])}.\n"
    for field, value in pilot['observed_api_usage'].items():
        text += f"- {field}: retained known sum {md(value['known_sum'])}; observed {value['observed_cells']} / {pilot['planned_cells']}. These are usage/ticks, not settled charges.\n"
    text += '\nThe pilot timing deviations remain unchanged; this is not retrospective final-policy reclassification. Read the linked timing disclosure for its recorded thresholds and counts.\n\n'
    for name, ref in prior['links'].items():
        text += f"- [{name}]({prefix}{name}), SHA256 `{ref['sha256']}`.\n"
    text += '\nRetained coverage limitations:\n\n' + '\n'.join('- ' + item for item in prior['coverage']['unresolved']) + '\n'
    return text


def render(manifest, analysis, summary, policy, disclosures, operator_rows, prior, ablation_manifest, provenance):
    groups = {(g['unit'], g['arm']): g for g in summary['groups']}
    lines = [r'\begin{tabular}{lrrr}', r'\hline', r'Family & A useful / 2 & B useful / 2 & B$-$A mean \\', r'\hline']
    for pair in summary['paired_family_rows']:
        unit = pair['unit']; lines.append(f"{tex(unit.removeprefix('ns-hist-'))} & {groups[unit,'A']['useful']} & {groups[unit,'B']['useful']} & {fmt(pair['B_minus_A_useful_mean'])} " + r'\\')
    lines += [r'\hline', f"All eight (16 cells per arm) & {summary['arm_useful_fixed16']['A']['useful']} / 16 & {summary['arm_useful_fixed16']['B']['useful']} / 16 & {fmt(summary['mean_B_minus_A_useful'])} " + r'\\', r'\hline', r'\end{tabular}', '% Repetitions are nested; the eight families are the analysis blocks.']
    ablation = [r'\begin{tabular}{p{0.30\linewidth}p{0.64\linewidth}}', r'\hline', r'Endpoint & Scope \\', r'\hline']
    ablation += [tex(endpoint) + ' & Withdrawn or unmeasured; no final comparison or effect estimate. ' + r'\\' for endpoint in policy['unsupported_endpoints']]
    population = ablation_manifest['population']
    ablation += [f"Non-A/B planned cells ({population['withdrawn_disjoint_partition']['non_AB_arm']}) & Withdrawn; no measured ablation rows. " + r'\\',
                 f"A/B warm planned cells ({population['withdrawn_disjoint_partition']['AB_local_warm']}) & Withdrawn; no measured ablation rows. " + r'\\']
    ablation += [r'\hline', r'\end{tabular}', '% A/B is the retained combined context contrast, not isolated component attribution.']
    ci = summary['bootstrap']['quality_B_minus_A']
    statistics = f"""# Descriptive fixed32 analysis

The fixed denominator is 32 cells, 16 per arm, in 8 historical families with 2 nested repetitions. Useful completion is {summary['useful_completions']}/32. Mean family B-minus-A useful fraction is {fmt(summary['mean_B_minus_A_useful'])}; its frozen descriptive conditional 95% percentile interval is [{fmt(ci['lower'])}, {fmt(ci['upper'])}]. Degenerate interval: {ci['degenerate']}.

The exact reviewed reducer source {ANALYZER} regenerated every summary field from the retained rows. Its 20,000 shared whole-family resamples and seed 20260911 are unchanged; no second estimator was introduced. The original D/A promotion, noninferiority and 16-family inference were withdrawn. A degenerate interval establishes neither equality nor safety. No human fidelity or reuse/publication benefit is estimated.

Outcomes (fixed denominator, no discarded failures):

""" + '\n'.join(f'- {key}: {value}' for key, value in sorted(summary['outcomes'].items()))
    statistics += '\n\nUnrecruited original families: 8. Original 192 factor cells: 160 removed before this final comparison. C/D, warm and isolated reuse experiments are not measured here. See the explicit ablation table and separately retained NS018 dispositions.\n'
    cost = '# Separate measured cost scopes\n\nNo child/wrapper/gateway/scorer/client or grant-to-terminal intervals are added together. Known sums cover only observed values; missing values and settlement remain unavailable, never zero.\n\n| Clock (seconds) | Known sum | Known / planned | Missing | Mean | p95 |\n|---|---:|---:|---:|---:|---:|\n'
    for name, value in summary['resource_summaries'].items():
        cost += f"| {METRIC_LABELS[name]} | {fmt(value['known_sum'])} | {value['known_count']} / {value['planned_count']} | {value['missing_or_invalid_count']} | {fmt(value['mean'])} | {fmt(value['p95'])} |\n"
    cost += '\nAPI usage/ticks are observed usage, not settled charges:\n\n'
    for key, value in analysis['observed_api_usage'].items():
        cost += f"- {key}: known sum {fmt(value['known_sum'])}; observed {value['known_count']}/32, missing {value['missing_or_invalid_count']}; settlement unavailable.\n"
    cost += '\nIsolated ablation costs: ' + ablation_manifest['unmeasured_isolated_cost_attribution']['reason'] + '\n'
    cost += cost_details(operator_rows, prior)
    cost += '\nAI/human effort and unmeasured setup are not free. Actual profile overshoots and sanitized incomplete-hidden-validation disclosures remain unchanged.\n'
    public_rows = [{key: row.get(key) for key in ('number','cell_id','unit','arm','repetition','terminal','outcome','useful_completion','disposition_class','resource_compliance','actual_provider_posts','actual_cold_completed','unknown_external_charge')} for row in analysis['rows']]
    results = dict(summary, schema='ns019-complete32-rendered-analysis/v1', provenance=provenance,
                   rows=public_rows, observed_api_usage=analysis['observed_api_usage'],
                   runtime_continuation=manifest['runtime_continuation'],
                   prior_cost_ledger_refs=[{'scope':r['scope'],'sha256':r['sha256']} for r in analysis['prior_and_preparation_cost_ledgers']],
                   validation_disclosure_records=[{k: v for k, v in item.items() if k != 'evidence'} |
                       {'evidence_sha256': [ref['sha256'] for ref in item['evidence']]}
                       for item in disclosures['records']],
                   operator_cost_manifest_sha256=provenance['operator_cost_manifest_sha256'],
                   operator_phase_records=operator_rows, prior_component_costs=prior,
                   ablation_population=ablation_manifest['population'], measured_ablation_rows=0,
                   ablation_unmeasured_cost_attribution=ablation_manifest['unmeasured_isolated_cost_attribution'],
                   ablation_criterion_evidence=ablation_manifest['criterion_evidence'],
                   candidate_or_hidden_replay=False, new_scientific_calls=0)
    return {'analysis/results.json': encoded(results), 'analysis/statistical_report.md': (statistics+'\n').encode(),
            'analysis/cost_report.md': cost.encode(), 'manuscript/generated/table17.tex': ('\n'.join(lines)+'\n').encode(),
            'manuscript/generated/ablations.tex': ('\n'.join(ablation)+'\n').encode()}


def figure(summary, output):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    matplotlib.rcParams['svg.hashsalt'] = 'ns019-fixed-family-descriptive-v1'
    groups = {(g['unit'], g['arm']): g['useful_mean'] for g in summary['groups']}
    units = [row['unit'] for row in summary['paired_family_rows']]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for i, unit in enumerate(units):
        ax.plot([groups[unit,'A'], groups[unit,'B']], [i,i], color='0.7', zorder=1)
    ax.scatter([groups[u,'A'] for u in units], range(8), marker='o', facecolors='none', edgecolors='#245a81', s=90, label='A')
    ax.scatter([groups[u,'B'] for u in units], range(8), marker='x', color='#a64324', s=65, label='B')
    ax.set_yticks(range(8), [u.removeprefix('ns-hist-') for u in units]); ax.invert_yaxis()
    ax.set_xlim(-.08, 1.08); ax.set_xticks([0,.5,1]); ax.set_xlabel('Useful fraction across two nested repetitions')
    ax.set_title('Eight family blocks: descriptive A/B outcomes'); ax.legend(); fig.tight_layout()
    directory = output/'manuscript/generated/figures'; directory.mkdir(parents=True, exist_ok=True)
    fig.savefig(directory/'family_useful.pdf', metadata={'CreationDate':None,'ModDate':None})
    fig.savefig(directory/'family_useful.svg', metadata={'Date':None})
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--ablation-manifest-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); os.umask(0o077)
    output = args.output
    require(output.is_absolute() and output.resolve() == output and not output.exists(), 'Fresh canonical output directory required')
    values = inputs(args.repository, args.manifest_sha256, args.ablation_manifest_sha256)
    files = render(*values)
    output.mkdir(mode=0o700)
    for name, raw in files.items():
        path = output/name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    figure(values[2], output)
    print(json.dumps({'complete32':True,'scientific_calls':0,'output':str(output),'files':sorted(str(p.relative_to(output)) for p in output.rglob('*') if p.is_file())}))


if __name__ == '__main__':
    main()
