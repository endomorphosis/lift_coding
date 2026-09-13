"""Allowlisted unsigned prior evidence, separate from the final32 component."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path
from common import binding, decode, digest, encoded, numeric_tree, number, public_check, read_bytes, write
from reproduce import SUMMARY_FIELDS, cost_summary, summarize_pilot

PILOT_FIELDS = ('number', 'cell_id', 'unit', 'arm', 'repetition', 'terminal', 'outcome',
                'useful_completion', 'actual_provider_posts', 'actual_cold_scored',
                'gateway_proposal_elapsed_seconds', 'gateway_score_elapsed_seconds',
                'http_wrapper_elapsed_seconds', 'provider_child_elapsed_seconds',
                'visible_passed', 'visible_collected', 'hidden_passed', 'hidden_collected',
                'http_status', 'response_bytes', 'usage', 'unknown_external_charge',
                'signed_terminal_sha256')

def interval(start, end):
    if start is None or end is None:
        return None
    result = (dt.datetime.fromisoformat(end)-dt.datetime.fromisoformat(start)).total_seconds()
    return number(result, False)

class Inputs:
    def __init__(self, path, sha):
        self.spec = decode(read_bytes(path, sha))
        assert self.spec['schema'] == 'ns-anonymous-prior-inputs/v1'
        self.refs = self.spec['refs']
        self.used = set()
    def raw(self, role):
        self.used.add(role)
        r = self.refs[role]
        raw = read_bytes(r['path'], r['sha256'])
        assert len(raw) == r['bytes']
        return raw
    def get(self, role):
        return decode(self.raw(role))

def project(inputs):
    I = inputs
    output, sources, records = {}, {}, []
    def emit(name, value, roles, raw=False):
        data = value if raw else encoded(value)
        public_check(data)
        output[name] = data
        sources[name] = [{'role': role, 'original_sha256': I.refs[role]['sha256'], 'original_bytes': I.refs[role]['bytes']} for role in roles]
    def record(scope, index, measurements, roles, relation='nested_do_not_add', **fields):
        for value in measurements.values():
            number(value)
        row = dict(record_id='%s/%s' % (scope, index), scope=scope, clock_relation=relation,
                   measurements=measurements, source_roles=roles, **fields)
        public_check(encoded(row))
        records.append(row)
    review = I.get('pilot_root_review')
    assert review['accepted_developmental_analysis_and_export'] is True
    analysis = I.get('pilot_analysis')
    assert analysis['complete'] is True and analysis['planned_cells'] == analysis['terminal_cells'] == 24
    assert analysis['unissued_or_nonterminal'] == 0 and analysis['batch_sha256'] == '7f15268d26c338b1c46722db9eb1988545dfc41b08605e945673b8b50d297866'
    assert review['analysis']['sha256'] == I.refs['pilot_analysis']['sha256']
    I.get('pilot_export_manifest')
    adopted = [decode(row) for row in I.raw('adopted_results').splitlines()]
    adopted_costs = [decode(row) for row in I.raw('adopted_costs').splitlines()]
    assert len(adopted) == len(adopted_costs) == 24
    rows = []
    for actual, prior, cost in zip(analysis['rows'], adopted, adopted_costs):
        assert all(prior[k] == v for k, v in actual.items()), 'adopted result differs from accepted analysis'
        assert all(actual[k] == v for k, v in cost.items() if k != 'scope'), 'adopted cost differs from accepted analysis'
        row = {key: actual[key] for key in PILOT_FIELDS}
        assert re.fullmatch(r'ns-hist-0[5-8]-[a-z]+', row['unit']) and row['arm'] in ('A', 'B')
        assert re.fullmatch('[0-9a-f]{64}', row['cell_id']) and re.fullmatch('[0-9a-f]{64}', row['signed_terminal_sha256'])
        row['usage'] = numeric_tree(row['usage'])
        row['settled_provider_cost'] = None
        row['settlement_scope'] = 'No settlement evidence; observed API usage and ticks are not settled monetary cost.'
        rows.append(row)
    source = I.raw('pilot_analyzer_source')
    pilot_summary = summarize_pilot(rows, source, analysis['batch_sha256'])
    assert all(pilot_summary[k] == analysis[k] for k in SUMMARY_FIELDS), 'exact original arithmetic differs'
    emit('pilot/rows.jsonl', b''.join(json.dumps(r, sort_keys=True, allow_nan=False).encode()+b'\n' for r in rows), ['pilot_analysis', 'adopted_results'], True)
    emit('pilot/adopted_costs.jsonl', I.raw('adopted_costs'), ['adopted_costs', 'pilot_analysis'], True)
    emit('pilot/summary.json', pilot_summary, ['pilot_analysis', 'pilot_analyzer_source'])
    emit('source/original_pilot_analyze.py', source, ['pilot_analyzer_source'], True)
    table = ['| Historical family | A useful / 3 | B useful / 3 | B minus A |', '|---|---:|---:|---:|']
    for unit in sorted({r['unit'] for r in rows}):
        a, b = [next(g['useful'] for g in pilot_summary['groups'] if g['unit'] == unit and g['arm'] == arm) for arm in ('A', 'B')]
        table.append('| %s | %d | %d | %d |' % (unit, a, b, b-a))
    table += ['', 'Descriptive four-family pilot only. Three repetitions per arm are nested within each family. The retained result is 10 useful completions (A 5/12, B 5/12), 12 scores and 24 provider POSTs. No final32 pooling or retrospective resource reclassification.', '']
    emit('pilot/table.md', '\n'.join(table).encode(), ['pilot_analysis'], True)
    boundary = I.get('pilot_boundary')
    b = boundary['cell20']
    emit('pilot/timing_disclosure.json', dict(schema='ns-pilot-resource-disclosure-public/v1',
         all24_full600second_host_compliance=False,
         cell20={k:b[k] for k in ('cell_id','child_seconds','gateway_seconds','http_wrapper_seconds','durations_are_nested','scientific_postprocessing_exclusion_prespecified','disposition_sha256')},
         child_overruns_595=pilot_summary['legacy_child_overruns_595'],
         outcome_labels_unchanged=True, no_retrospective_final_policy_reclassification=True), ['pilot_boundary', 'pilot_analysis'])
    partial = I.get('six_ledger_index')
    ledger_refs = partial['prior_and_preparation_cost_ledgers']
    assert len(ledger_refs) == 6
    for i, ref in enumerate(ledger_refs):
        assert ref['sha256'] == I.refs['ledger_%d' % i]['sha256']
    prep = I.get('pilot_preparation')
    assert len(prep['preparation_attempts']) == 26
    assert len({r['sha256'] for r in prep['preparation_attempts']}) == 26
    for i, row in enumerate(prep['preparation_attempts']):
        raw = I.get('pilot_prep_%02d' % i)
        assert row['sha256'] == I.refs['pilot_prep_%02d' % i]['sha256']
        assert row['started_at'] == raw['started_at'] and row['finished_at'] == raw['finished_at']
        record('pilot_shared_native_preparation', i,
               dict(host_timestamp_interval_seconds=interval(row['started_at'], row['finished_at']), cpu_seconds=None),
               ['pilot_preparation', 'pilot_prep_%02d' % i], success=row['success'],
               cleanup_returncode=row['cleanup_returncode'], start_returncode=row['start_returncode'],
               cpu_measurement_available=False, interval_kind='derived_from_saved_host_timestamps',
               interrupted_cpu_total_available=row['interrupted_cpu_total_available'])
    final_prep = I.get('ledger_0')
    assert len(final_prep['preparation_attempts']) == 11
    for i, row in enumerate(final_prep['preparation_attempts']):
        q = I.get('final_prep_%02d' % i)
        assert row['qualification']['sha256'] == I.refs['final_prep_%02d' % i]['sha256']
        assert q['success'] == row['success'] and q['cleanup_exit_code'] == 0 and q['pending'] is None
        assert row['host_wall_seconds'] == q['wall_seconds']
        record('final_shared_native_preparation', i, {k:row[k] for k in ('child_cpu_seconds','child_wall_seconds','host_wall_seconds')},
               ['ledger_0','final_prep_%02d' % i], attempt=row['attempt'], success=row['success'], scientific_calls=0)
    baseline = I.get('ledger_1')
    registry = I.get('original_registry')
    for i, unit in enumerate(sorted(registry['units'])[4:8]):
        old = I.get('pilot_baseline_old_%02d'%i)
        assert I.refs['pilot_baseline_old_%02d'%i]['sha256'] == registry['units'][unit]['baseline_qualification']['command_report_sha256']
        assert len(old['runs']) == 2
        for j, run in enumerate(old['runs']):
            record('pilot_public_baseline_historical128', '%d-%d'%(i,j),
                   dict(host_timestamp_interval_seconds=interval(run['started_at'],run['finished_at']),cpu_seconds=None,memory_bytes=None),
                   ['original_registry','pilot_baseline_old_%02d'%i], relation='separate_interval',unit=unit,
                   stage=run['stage'],returncode=run['returncode'],timed_out=run['timed_out'],interval_kind='derived_from_saved_stage_timestamps')
    for i, unit in enumerate(baseline['unit_results']):
        old = I.get('baseline_old_%02d' % i)
        assert len(old['runs']) == 2
        for j, run in enumerate(old['runs']):
            record('final_public_baseline_historical128', '%d-%d' % (i,j),
                   dict(host_timestamp_interval_seconds=interval(run['started_at'], run['finished_at']), cpu_seconds=None, memory_bytes=None),
                   ['ledger_1','baseline_old_%02d' % i], relation='separate_interval', unit=unit['unit_id'],
                   stage=run['stage'], returncode=run['returncode'], timed_out=run['timed_out'], interval_kind='derived_from_saved_stage_timestamps')
    for i, role in enumerate(['baseline_32_%02d' % i for i in range(8)] + ['baseline_new_128']):
        r = I.get(role)
        c = r['costs']
        record('final_public_baseline_current32' if i < 8 else 'final_public_baseline_new128', i,
               dict(host_attach_wall_seconds=r['host_execution_elapsed_seconds'], host_cleanup_wall_seconds=r['cleanup']['wall_seconds'],
                    cgroup_cpu_seconds_lower_bound=c['cgroup_cpu_seconds_lower_bound'],
                    cgroup_peak_memory_bytes_lower_bound=c['cgroup_peak_memory_bytes_lower_bound'],
                    child_elapsed_seconds=c['elapsed_seconds']), ['ledger_1',role],
               success=r['success'], counts=r.get('counts'), cpu_and_memory_scope='sampled_lower_bounds')
    emit('costs/baseline_transfer.json', {k:baseline[k] for k in ('all8_newly_executed_under_exact128_recipe','all9_new_containers_cleanup_absence_proven','full_unchanged_public_denominator','original128_baseline_tests_passed','original128_baselines_units','other7_current_exact_observe32_tests_passed','new_exact_observe128_tests_passed','new_exact_observe128_units')}, ['ledger_1'])
    for role, key in [('ledger_2','elapsed_seconds'),('ledger_3','metadata_elapsed_seconds')]:
        r = I.get(role)
        record('final_metadata_staging', role, {'host_wall_seconds':r[key], 'cpu_seconds':None}, [role], relation='separate_interval')
    I.get('ledger_4')
    recovery = I.get('ledger_5')
    addendum = I.get('v2_addendum')
    for key, value in addendum['new_measured_metadata_intervals'].items():
        if type(value) in (float, int):
            record('v2_metadata_%s' % key, 0, {'wall_seconds':value, 'cpu_seconds':None}, ['v2_addendum'],
                   interval_relation='installed_metadata_builder_seconds is nested inside enclosing_installation_seconds; these scopes must not be summed')
    old_calls = {r['cell_id']:r for r in addendum['prior_provider_calls']}
    I.get('v2_batch')
    for version in (1,2):
        cancel = I.get('cancel_v%d' % version)
        assert (cancel['cancelled_unissued_count'] if version == 1 else cancel['unissued_cancelled_count']) == 21
        for i in range(3):
            roles = ['cancel_v%d'%version,'v%d_terminal_%d'%(version,i),'v%d_client_%d'%(version,i),'v%d_client_execution_%d'%(version,i)]
            t, c, e = [I.get(role) for role in roles[1:]]
            assert t['terminal_verified'] and t['terminal_failure'] and e['success'] and e['cleanup_exit_code'] == 0
            h = c['results'][0]['result']['host_verified']; r = h['receipt']
            assert h['signature_and_scope_verified'] is True and h['terminal_failure'] is True
            assert r['cell_id'] == t['cell_id'] and r['provider_termination']['termination_proven'] is True
            measures = dict(gateway_proposal_seconds=r['elapsed_seconds'], http_wrapper_seconds=None, provider_child_seconds=None,
                            provider_cpu_seconds=None, settled_provider_cost=None)
            usage = r['provider_stream_metadata'].get('usage')
            if version == 1:
                old = old_calls[r['cell_id']]
                measures['http_wrapper_seconds'] = old['enclosing_proposer_seconds']
                measures['provider_child_seconds'] = old['retained_provider_metadata']['elapsed_seconds']
                assert old['retained_provider_metadata'].get('usage') == usage
                roles.append('v2_addendum')
            else:
                provider = I.get('v2_provider_%d'%i)
                assert digest(I.raw('v2_provider_%d'%i)) == r['proposal_result_sha256']
                measures['http_wrapper_seconds'] = provider['elapsed_seconds']
                measures['provider_child_seconds'] = (provider.get('provider') or {}).get('elapsed_seconds')
                assert (provider.get('provider') or {}).get('usage') == usage
                roles.extend(['v2_batch','v2_provider_%d'%i])
            record('prior_protocol_v%d'%version, i, measures, roles,
                   useful_completion=False, scorer_calls=0, consumed_slot=1,
                   known_provider_posts=1 if r['provider_invoked'] else None, provider_posts_upper_bound=1,
                   usage=numeric_tree(usage), remote_execution_or_settlement_may_be_unknown=True,
                   typed_client_result_sha256=t['client_result']['sha256'], cleanup_proven=True)
            record('prior_terminal_client_verification', '%d-%d'%(version,i),
                   dict(host_wall_seconds=e['wall_seconds'], child_wall_seconds=c['wall_seconds'], child_cpu_seconds=c['cpu_seconds']),
                   roles[1:4], poll_scope='only the terminal client poll, not all prior polls or all operator overhead')
    d = recovery['diagnostic']; actual = I.get('diagnostic_execution'); I.get('diagnostic_accounting')
    assert actual['success'] and actual['elapsed_seconds'] == d['enclosing_wall_seconds'] and actual['scientific_credit'] is False
    record('separate_constructed_generation_diagnostic', 0,
           dict(enclosing_wall_seconds=d['enclosing_wall_seconds'], nested_http_seconds=d['nested_http_seconds'], cpu_seconds=None, settled_provider_cost=None),
           ['ledger_5','diagnostic_execution','diagnostic_accounting'], generated_calls=1, scorer_calls=0, scientific_credit=False, usage=numeric_tree(d['usage']))
    authority = I.get('continuation_authority')
    old, released, new, launch, after = [I.get(k) for k in ('old_reservation','old_release','successor_reservation','holder_launch_evidence','holder_after_caller_exit_evidence')]
    assert released['resource_reservation_evidence_sha256'] == I.refs['old_reservation']['sha256']
    record('original_lease_lifecycle', 0, dict(timestamp_occupancy_seconds=interval(old['created_at'], released['released_at']), cpu_seconds=None),
           ['old_reservation','old_release'], relation='lifecycle_not_compute', terminal_reason='SIGTERM; sender unknown',
           scientific_cell7_costs='belong only in the separate final32 component; not repeated here')
    assert launch['success'] and after['success']
    record('successor_lease_launcher', 0, dict(launcher_wall_seconds=launch['launcher_wall_seconds'], holder_cpu_seconds=None),
           ['successor_reservation','holder_launch_evidence','holder_after_caller_exit_evidence'], relation='separate_interval',
           holder_lifetime_total=None, holder_lifetime_scope='Only launch and saved post-caller-exit observation; no current lease query or inferred terminal.')
    cost_roles = sorted({role for r in records for role in r['source_roles']})
    emit('costs/records.jsonl', b''.join(json.dumps(r, sort_keys=True, allow_nan=False).encode()+b'\n' for r in records), cost_roles, True)
    emit('costs/summary.json', cost_summary(records), cost_roles)
    # Record the precise six-ledger coverage plus the newly discovered omissions.
    coverage = dict(schema='ns-prior-component-coverage/v1', signature_authentication_of_derivatives=False,
        pilot=dict(cells=24, independent_families=4, nested_repetitions=3, scalar_reproduction=True, pooled_with_final32=False),
        six_ledgers=[dict(index=i, original_sha256=I.refs['ledger_%d'%i]['sha256']) for i in range(6)],
        additional_coverage=['26 original four-family native preparation attempts including failures and setup controls',
            '24 saved collect/run timestamp intervals for original four pilot and eight final-family 128-PID baselines',
            'Six prior protocol terminal gateway clocks and six terminal-client poll clocks; v1 nested provider clocks',
            'V2 metadata staging intervals, one separate generated diagnostic, original lease lifecycle and successor launch'],
        no_clock_grand_total=True, no_outcome_pooling=True,
        unresolved=['Settled provider charges absent; observed API ticks are not settlement.',
            'Prior interrupted preparation CPU and complete original preparation CPU are unavailable in the admitted metadata.',
            'V2 timeout child CPU/duration and remote effects remain unknown where no child result exists.',
            'Historical baseline CPU/memory unavailable; timestamps yield stage wall intervals only.',
            'All operator polls, source qualification, authoring, human/AI review, network diagnostics, and packaging costs are not a complete measured ledger.',
            'Lease occupancy is not computation; successor full lifetime CPU/wall is not measured here.',
            'Baseline coverage is the four-family pilot plus eight final families; earlier NS026 families and other unrelated controls are outside this component and are not asserted zero.',
            'Private signed originals, candidate/reference/oracle bytes and original-source-tree replay are not released by this numerical component.'],
        whole_NS024_obligation='Combine this prior numerical component with separately reviewed final32 anonymous component and permitted source/license/candidate reproduction material. This component alone is not the complete supplement.')
    emit('coverage.json', coverage, ['six_ledger_index','pilot_root_review','continuation_authority'])
    return output, sources, I.used

def build(inputs, sha, output):
    I = Inputs(inputs, sha)
    files, sources, used = project(I)
    here = Path(__file__).resolve().parent
    for name in ('common.py','reproduce.py','build_component.py','prepare_inputs.py'):
        raw = read_bytes(here/name); public_check(raw)
        files['source/'+name] = raw
        sources['source/'+name] = [dict(role='component_source/'+name, original_sha256=digest(raw), original_bytes=len(raw))]
    readme = read_bytes(here/'RELEASE_README.md'); public_check(readme)
    files['README.md'] = readme; sources['README.md'] = []
    manifest = dict(schema='ns-anonymous-prior-component/v1',
        signature_authentication_of_derived_records=False,
        private_originals_retained_unchanged=True, unsigned_data_replay_only=True,
        original_signature_replay_requires_private_custody=True,
        no_new_provider_scorer_native_calls=True,
        members={name:dict(sha256=digest(raw), bytes=len(raw), original_sources=sources[name],
                           treatment='byte_exact_source' if name.startswith('source/') else 'explicitly_unsigned_scalar_projection_or_document') for name,raw in files.items()})
    manifest['members']['pilot/adopted_costs.jsonl']['treatment'] = 'byte_exact_preexisting_unsigned_projection'
    files['manifest.json'] = encoded(manifest)
    assert sum(len(x) for x in files.values()) < 4*1024*1024
    dest = Path(output); dest.mkdir(mode=0o700)
    for name, raw in files.items():
        public_check(raw); write(dest/name, raw)
    return dict(schema='ns-prior-component-build/v1', success=True, indexed_members=len(files)-1,
                total_files=len(files), total_bytes=sum(map(len,files.values())),
                inputs_sha256=sha, used_roles=sorted(used), unused_roles=sorted(set(I.refs)-used),
                manifest=binding(dest/'manifest.json'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--inputs-sha256', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    result = build(args.inputs, args.inputs_sha256, args.output)
    write(args.report, encoded(result))
    print(json.dumps({k:result[k] for k in ('success','indexed_members','total_files','total_bytes')}))
