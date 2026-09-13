"""Future NS016 actual evidence audit. No scientific or native execution.

This audit creates no receipt and no criterion judgment. Only its real future
invocation writes a fresh report, with actual clocks, argv and observed hashes.
"""
import argparse
import ast
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LOCK_SHA = 'b889be2e5d76bb662267db2fcae4e2c2aa04da44eab2d5eab8b830d7806390fa'
OLD16 = '0268ead2952a90bf46f2d0acb67fe04a03176796bbc88184154be81ca2fe4d7d'
P = 'papers/completion/neurosymbolic_supervision/'

def require(ok, message):
    if not ok: raise ValueError(message)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def reference(path, sha):
    return {'path': str(path), 'sha256': sha}

def utc(value):
    t = dt.datetime.fromisoformat(value)
    require(t.tzinfo is not None and t.utcoffset() == dt.timedelta(0), 'aware UTC required')
    return t

class Custody:
    def __init__(self): self.bindings = {}; self.bytes_checked = 0
    def raw(self, ref, limit=16 << 20):
        p = Path(ref['path'])
        require(p.is_absolute() and p.resolve() == p, 'canonical bound path required')
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            a = os.fstat(fd)
            require(stat.S_ISREG(a.st_mode) and a.st_size <= limit, 'bounded regular file required')
            with os.fdopen(fd, 'rb', closefd=False) as stream: raw = stream.read(limit + 1)
            b = os.fstat(fd)
        finally: os.close(fd)
        require((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns) == (b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns)
                and len(raw) == a.st_size and digest(raw) == ref['sha256'], 'bound bytes changed')
        require(str(p) not in self.bindings or self.bindings[str(p)] == ref['sha256'], 'input changed during audit')
        self.bindings[str(p)] = ref['sha256']; self.bytes_checked += len(raw)
        require(self.bytes_checked <= 1 << 30, 'audit aggregate read bound exceeded')
        return raw
    def json(self, ref, limit=16 << 20):
        def pairs(items):
            out = {}
            for key, value in items:
                require(key not in out, 'duplicate JSON key'); out[key] = value
            return out
        return json.loads(self.raw(ref, limit), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite metadata')))

def pure_source(raw, functions, assignments=(), extra=None):
    nodes = []
    for n in ast.parse(raw).body:
        if isinstance(n, ast.FunctionDef) and n.name in functions: nodes.append(n)
        elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assignments for t in n.targets): nodes.append(n)
    ns = {'hashlib': hashlib, 'json': json, **(extra or {})}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<exact-reviewed-pure-functions>', 'exec'), ns)
    return ns

def producers(c, refs):
    # No production module imports, native SDKs or provider/scorer functions.
    rr = pure_source(c.raw(refs['receipt_route']), {'require', 'complete32'})
    names = {'require','digest','canonical','metadata_guard','source_versions_guard','disclosure_guard'}
    constants = {'ACTIVATION_SHA','ANALYZER_SHA','EXPORTER_SHA','CLIENT_SHA','ANALYSIS_PACKAGE_SHA',
                 'SOURCE_INVENTORY_SHA','TASK_CONTRACTS_SHA','POLICY_SHA','FREEZE_FILE_SHA',
                 'FREEZE_CANONICAL_SHA','UNITS','REPS'}
    b = pure_source(c.raw(refs['bundle_builder']), names, constants)
    for name in ('analysis_producer','export_producer','cost_producer','client_extension','pilot_producer'):
        c.raw(refs[name], 1 << 20)
    require(refs['analysis_producer']['sha256'] == b['ANALYZER_SHA'] and
            refs['export_producer']['sha256'] == b['EXPORTER_SHA'], 'qualified producer identities differ')
    return rr['complete32'], b

def entry_gate(inputs, read, complete32):
    require(inputs.get('schema') == 'ns016-actual-completion-audit-input/v1' and
            inputs.get('fixture') is False and inputs.get('input_kind') == 'actual_signed_complete_final32',
            'actual complete evidence inputs required')
    review = read(inputs['root_complete_review'])
    complete32(review)  # Always before admission, analysis, bundle or cell reads.
    adm = read(inputs['bundle_admission'])
    require(adm.get('schema') == 'ns017-actual-final32-adoption-admission/v1' and
            adm.get('approved') is True and adm.get('authority') == 'root_operator' and
            adm.get('fixture') is False and adm.get('allow_partial') is False and
            adm.get('input_kind') == 'actual_signed_complete_final32' and
            adm.get('operation') == 'build_actual_adoption_bundle_only' and
            adm.get('root_complete_review') == inputs['root_complete_review'], 'exact R1 bundle admission required')
    bundle = read(inputs['bundle_manifest'])
    require(bundle.get('schema') == 'ns017-actual-final32-preinstallation-bundle/v1' and
            bundle.get('success') is True and bundle.get('actual_terminal_cells') == 32 and
            bundle.get('current_output_count') == 5 and bundle.get('scientific_calls') == 0 and
            bundle.get('native_writes') == 0 and bundle.get('admission_file') == inputs['bundle_admission'] and
            bundle.get('admission_canonical_sha256') == digest(canonical(adm)), 'actual successful bound bundle required')
    return review, adm, bundle

def verify_pilot(c, refs, freeze, final_units):
    review = c.json(refs['pilot_review']); pilot = c.json(refs['pilot_analysis']); lineage = c.json(refs['pilot_bindings'])
    pa = c.json(refs['pilot_activation']); pb = c.json(pa['batch']); cohort = c.json(refs['pilot_cohort'])
    require(review['accepted_developmental_analysis_and_export'] is True and review['analysis'] == refs['pilot_analysis']
            and review['bindings']['sha256'] == refs['pilot_bindings']['sha256'], 'accepted retained pilot review required')
    require(pilot['complete'] is True and pilot['planned_cells'] == pilot['terminal_cells'] == 24
            and pilot['unissued_or_nonterminal'] == 0 and pilot['schema'] == 'ns028-pilot-retained-evidence-analysis/v1', 'strict pilot24 required')
    rows = pilot['rows']; units = {r['unit'] for r in rows}
    require(len(rows) == 24 and len(units) == 4 and units == set(pb['units']) and
            units <= set(freeze['developmental_task_ids']) and not units.intersection(final_units), 'pilot/final split differs')
    require([r['cell_id'] for r in rows] == pa['ordered_cells'] == pb['enabled_cells'] and
            len({r['cell_id'] for r in rows}) == 24 and all(r['terminal'] is True for r in rows), 'pilot identities differ')
    require(all(sum(r['unit'] == u and r['arm'] == a for r in rows) == 3 for u in units for a in ('A','B')), 'three nested pilot repetitions required')
    witnesses = {}
    def retained(ref):
        require(lineage.get(ref['path']) == ref['sha256'], 'pilot witness absent from reviewed producer lineage')
        return c.json(ref)
    driver = c.json(pa['driver_package'])
    driver_root = Path(pa['driver_package']['path']).parent
    for name in ('launch.py','bootstrap.py'):
        c.raw(reference(driver_root/name,driver['package_files'][name]),1 << 20)
    for arm in ('A','B'):
        selected = [r for r in rows if r['arm'] == arm and r['useful_completion'] is True]
        require(len(selected) == 5 and freeze['arm_useful_paths'][arm]['useful_pilot_cells'] == 5 and
                freeze['arm_useful_paths'][arm]['pilot_analysis_sha256'] == refs['pilot_analysis']['sha256'], 'actual useful pilot5 per arm required')
        witnesses[arm] = []
        for row in selected:
            t = retained(reference(row['signed_terminal_path'], row['signed_terminal_sha256']))
            execution = retained(t['client_execution']); client = retained(t['client_result'])
            result = client['results'][0]['result']; verified = result['host_verified']; scalar = t['cold_scalar_result']
            require(t['terminal_verified'] is True and t['terminal_failure'] is False and t['cell_id'] == row['cell_id'] and
                    client['terminal'] is True and client['batch_sha256'] == pilot['batch_sha256'] == pa['batch']['sha256'] and
                    len(client['results']) == 1 and client['results'][0]['cell_id'] == row['cell_id'], 'actual pilot terminal join differs')
            require(execution['success'] is True and execution['cleanup_exit_code'] == 0 and
                    execution['package_sha256'] == pa['driver_package']['sha256'], 'retained qualified pilot client execution differs')
            plan = c.json(reference(Path(t['client_execution']['path']).parent/'plan.json',execution['plan_sha256']))
            require(plan['package_sha256'] == pa['driver_package']['sha256'] and plan['image'] == driver['image'],
                    'retained pilot invocation plan differs')
            require(verified['signature_and_scope_verified'] is True and verified['admitted_historical_pilot'] is True and
                    scalar == result['cold_scalar_result'] and scalar['cold_full_validation'] is True and
                    scalar['candidate_valid'] is True and scalar['human_annotation'] is False and row['actual_cold_scored'] is True,
                    'actual separately scored pilot authority required')
            private = Path(pa['private_root']) / row['cell_id']
            original_path = private / 'result.json'; original = retained(reference(original_path, lineage[str(original_path)]))
            body = original['receipt']; require(body == verified['receipt'] and body['final_scientific_run'] is False and
                    body['cell_id'] == row['cell_id'] and body['batch_sha256'] == pa['batch']['sha256'], 'pilot signed body differs')
            grant = retained(reference(private / 'grant.json', body['grant_sha256']))
            require(grant['profile'] == body['profile'] and grant['request_binding'] == body['request_binding'] and
                    grant['batch_binding']['sha256'] == pa['batch']['sha256'], 'pilot scoring grant scope differs')
            witnesses[arm].append({'cell_id': row['cell_id'], 'terminal_sha256': row['signed_terminal_sha256'],
                                   'original_signed_envelope_canonical_sha256': digest(canonical(original)),
                                   'original_receipt_file_sha256': lineage[str(original_path)], 'client_execution': t['client_execution']})
    require(cohort['useful_witnesses'] == {'A':5,'B':5} and cohort['all24_full600_host_compliance'] is False, 'pilot limitations lost')
    return {'units': sorted(units), 'cells':24, 'useful_witnesses':witnesses,
            'authority_scope':'Exact retained actual offline client signature-and-scope verification plus original signed body/scalar/grant joins; no fresh cryptographic verification.',
            'final_resource_policy_compliance_claimed':False,
            'timing_limitations':'Historical pilot useful labels remain unchanged. Child overshoots and cell20 wrapper/gateway over600 are not retrospectively final-policy-compliant.'}

def audit(inputs, repository, c, refs, complete32, b):
    review, adm, bundle = entry_gate(inputs, c.json, complete32)
    require(adm['builder_sha256'] == refs['bundle_builder']['sha256'], 'successful bundle must use exact reviewed producer')
    for key in ('activation','analysis','analysis_bindings','export_manifest','candidate_payload_manifest',
                'public_baseline_manifest','validation_disclosures','operator_phase_cost_manifest','continuation_contract'):
        require(review[key] == adm[key], 'R1/bundle evidence join differs: ' + key)
    a = c.json(adm['activation']); an = c.json(adm['analysis']); ex = c.json(adm['export_manifest']); freeze = c.json(a['freeze'])
    b['metadata_guard'](adm,a,an,ex,review,freeze)
    # From here every actual cell read is behind the complete32/R1/bundle gates.
    output_spec = c.json(refs['original_outputs']); pending = c.json(reference(repository / (P+'receipts/NS-016.json'), OLD16))
    require(pending['status'] == 'pending_operator_evidence_review' and
            pending['outputs'] == output_spec['original_five_outputs'], 'original pending five-output contract differs')
    for current, snapshot in pending['outputs'].items():
        h = output_spec['original_five_snapshot_hashes'][snapshot]
        require(pending['artifacts'][snapshot] == h, 'old owned snapshot binding differs')
        c.raw(reference(repository/current,h)); c.raw(reference(repository/snapshot,h))
    bundle_root = Path(inputs['bundle_manifest']['path']).parent
    require(type(bundle['total_bytes']) is int and bundle['total_bytes'] <= adm['max_preinstallation_bytes'] <= 256 << 20, 'bounded actual bundle required')
    total = 0
    for relative, meta in bundle['files'].items():
        p = Path(relative)
        require(not p.is_absolute() and str(p) == relative and not any(x in ('.','..','.git') for x in p.parts), 'unsafe bundle member')
        raw = c.raw(reference(bundle_root/p,meta['sha256']),64 << 20); require(len(raw) == meta['bytes'], 'bundle size differs'); total += len(raw)
    require(total == bundle['total_bytes'], 'bundle aggregate byte count differs')
    def member(relative):
        return c.json(reference(bundle_root/relative,bundle['files'][relative]['sha256']))
    main = member(P+'runs/main/manifest.json')
    require(main['ordered_cells'] == a['ordered_cells'] and main['terminal_cells'] == main['planned_cells'] == 32 and
            main['private_original_refs']['root_complete_review']['sha256'] == inputs['root_complete_review']['sha256'] and
            main['actual_useful_completions'] == an['useful_completions'], 'materialized main/R1/analysis differs')
    batch = c.json(a['batch']); manifest = c.json(reference(repository/(P+'protocol/final_run_manifest.json'),
                          output_spec['original_five_snapshot_hashes'][pending['outputs'][P+'protocol/final_run_manifest.json']]))
    require(batch['planned_cells'] == batch['enabled_cells'] == freeze['planned_cells'] == a['ordered_cells'] and
            batch['enabled_arms'] == ['A','B'] and batch['enabled_cache'] == 'local_cold' and
            set(batch['units']) == set(freeze['final_task_ids']) == set(b['UNITS']), 'original fixed final design differs')
    require({x['family_id'] for x in batch['units'].values()} == set(freeze['final_family_ids']) and
            len(freeze['final_family_ids']) == 8 and not set(freeze['final_family_ids']).intersection(freeze['developmental_family_ids']), 'family split differs')
    require(manifest['planned_cells'] == 32 and manifest['removed_factor_cells'] == 160 and
            manifest['unrecruited_original_final_families'] == 8 and
            set(freeze['removed_arms']) == {'C','D','C-no-route','C-no-reuse'} and
            freeze['retained_executable_arms'] == ['A','B'], 'prospective removed comparison scope differs')
    for unit, entry in batch['units'].items():
        for arm in ('A','B'):
            expected = entry['arms'][arm]; got = an['request_profile_lineage'][unit][arm]
            require(all(got[k] == expected[k] for k in ('profile_sha256','request_binding_sha256','context_binding_sha256')),
                    'original16 request/profile/context commitments differ')
    for path, h in freeze['immutable_pins'].items(): c.raw(reference(path,h),64 << 20)
    require(len(freeze['immutable_pins']) == 37 and freeze['analysis_policy_sha256'] == refs['policy']['sha256'], 'original37/policy differs')
    policy = c.json(refs['policy']); authority = c.json(refs['freeze_authority']); fx = c.json(refs['freeze_execution'])
    require(freeze['root_freeze_authority'] == refs['freeze_authority'] and authority['approved'] is True and
            authority['final_outcomes_observed'] == authority['provider_calls'] == authority['scorer_calls'] == 0 and fx['exit_code'] == 0,
            'actual pre-outcome freeze execution required')
    scientific = c.json(a['scientific_review']); operator = c.json(a['operator_admission'])
    require(scientific['accepted'] is True and scientific['frozen_before_comparison_outcomes'] is True and
            operator['approved'] is True and operator['freeze_sha256'] == a['freeze']['sha256'] and
            operator['analysis_policy_sha256'] == refs['policy']['sha256'], 'pre-outcome scientific admission differs')
    context = c.json(adm['continuation_contract']); require(context['original_activation'] == adm['activation'] and
            context['original_batch'] == a['batch'] and context['original_freeze'] == a['freeze'] and
            context['consumed_cells'] == a['ordered_cells'][:7] and context['remaining_cells'] == a['ordered_cells'][7:], 'mixed epochs alter original design')
    b['source_versions_guard'](adm['source_versions'], {'summary': an['runtime_continuation']})
    disclosures = c.json(adm['validation_disclosures']); b['disclosure_guard'](adm,an,review,disclosures)
    costs = c.json(adm['operator_phase_cost_manifest'])
    require(costs['actual_complete32'] is True and costs['analysis'] == adm['analysis'] and
            costs['continuation_contract'] == adm['continuation_contract'] and set(costs['cells']) == set(a['ordered_cells']) and
            costs['source_sha256'] == refs['cost_producer']['sha256'] and costs['all_signed_clocks_unchanged'] is True and
            costs['frozen_analysis_policy_changed'] is False, 'actual additive cost availability differs')
    for path,h in costs['input_bindings'].items(): c.raw(reference(path,h),16 << 20)
    lineage = c.json(adm['analysis_bindings']); starts = []; epochs = collections.Counter()
    for row in an['rows']:
        t = c.json(reference(row['signed_terminal_path'],row['signed_terminal_sha256']))
        e = c.json(t['client_execution']); client = c.json(t['client_result']); v = client['results'][0]['result']['host_verified']
        require(t['terminal_verified'] is True and t['cell_id'] == row['cell_id'] and e['success'] is True and e['cleanup_exit_code'] == 0
                and v['signature_and_scope_verified'] is True, 'actual final typed authority differs')
        path = str(Path(a['private_root'])/row['cell_id']/row['original_receipt_filename'])
        require(lineage.get(path) == row['original_signed_receipt_sha256'], 'original signed body outside actual lineage')
        signed = c.json(reference(path,row['original_signed_receipt_sha256'])); body = signed['receipt']
        require(body == v['receipt'] and body['cell_id'] == row['cell_id'] and body['final_freeze_sha256'] == a['freeze']['sha256'], 'signed final receipt join differs')
        starts.append(utc(body['started_at'])); epoch = row['runtime_source_provenance']['epoch']; epochs[epoch] += 1
        if row['number'] <= 7:
            require(epoch == 'original_resource_lease' and 'runtime_continuation' not in body and
                    body.get('source_bindings',context['original_frozen_source_bindings']) == context['original_frozen_source_bindings'], 'prefix source relabeled')
        else:
            require(epoch == 'prospective_resource_lease_continuation' and body['runtime_continuation'] == context['runtime_continuation'] and
                    body['source_bindings'] == context['effective_source_bindings'] and body['frozen_source_bindings'] == context['original_frozen_source_bindings'], 'suffix actual source lost')
    require(epochs == {'original_resource_lease':7,'prospective_resource_lease_continuation':25}, 'exact epochs required')
    chronology = [utc(authority['at']),utc(fx['at']),utc(scientific['at']),utc(operator['at']),utc(a['at']),min(starts)]
    require(chronology == sorted(chronology) and utc(a['at']) < min(starts), 'freeze/removal/admission not before first final attempt')
    pilot = verify_pilot(c, refs, freeze, set(batch['units']))
    ledgers = an['prior_and_preparation_cost_ledgers']
    require(len(ledgers) == 6 and len({x['scope'] for x in ledgers}) == 6 and
            all(x['pooled_into_final_outcomes'] is False and x['summed_with_nested_phase_costs'] is False for x in ledgers), 'separate prior/setup ledgers required')
    for x in ledgers: c.raw(x,16 << 20)
    require(any(x['path'] == refs['pilot_cohort']['path'] and x['sha256'] == refs['pilot_cohort']['sha256'] for x in ledgers), 'original pilot ledger lost')
    return {'original_five_outputs_checked':pending['outputs'], 'bundle_files_checked':len(bundle['files']),
            'pilot':pilot, 'final_design':{'cells':32,'families':8,'nested_repetitions':2,'arms':['A','B'],'cache':'local_cold',
                'request_profile_commitments':16,'withdrawn_old_cells':160,'unrecruited_original_families':8},
            'runtime_epochs':dict(epochs), 'chronology_utc':[x.isoformat() for x in chronology],
            'original37_checked':True, 'policy_sha256':refs['policy']['sha256'],
            'bound_actual_bundle_source_versions':adm['source_versions'],
            'additive_disclosure_records':len(disclosures['records']), 'operator_cost_cells':len(costs['cells']),
            'prior_cost_ledgers':ledgers, 'costs_summed_across_nested_scopes':False,
            'scientific_judgments_supplied':False, 'native_task_completion_claimed':False,
            'limitations':[
                'Retained actual typed-client cryptographic authority and the exact successful bundle producer are relied on; this audit reruns no signature algorithm, candidate reconstruction, hidden test, native harness, provider or scorer.',
                'Original signed outcomes and useful labels remain unchanged. Import/collection failure is not a hidden assertion failure or established infrastructure fault. Pilot usefulness is not final resource-policy compliance.',
                'Root still supplies four justified scientific judgments. This audit is not a completed receipt or normal task validation.',
                'Source and custody hash checks are not source-body replay. Bundle public candidate bytes remain distinct from binding metadata and explicit derivation disclosures.',
                'Runtime epochs are historical; no current lease liveness, full settled cost, human semantic fidelity or expert effort is established.']}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True); p.add_argument('--inputs-sha256',required=True)
    p.add_argument('--repository',type=Path,required=True); p.add_argument('--expected-head',required=True)
    p.add_argument('--report',type=Path,required=True); args = p.parse_args()
    require(args.report.is_absolute() and args.report.resolve() == args.report and not args.report.exists(), 'fresh report required')
    require(args.repository.is_absolute() and args.repository.resolve() == args.repository, 'canonical repository required')
    started = dt.datetime.now(dt.timezone.utc).isoformat(); clock = time.monotonic(); c = Custody(); error = None; result = None
    try:
        locked = c.json(reference(HERE/'immutable_inputs.private.json',LOCK_SHA)); refs = locked['files']
        inputs = c.json(reference(args.inputs,args.inputs_sha256)); gate,b = producers(c,refs)
        head = subprocess.run(['git','rev-parse','HEAD'],cwd=args.repository,text=True,capture_output=True,check=True,timeout=10).stdout.strip()
        require(head == args.expected_head, 'observed repository HEAD differs')
        result = audit(inputs,args.repository,c,refs,gate,b)
    except Exception as exc:
        error = {'type':type(exc).__name__,'message':str(exc)}
    record = {'schema':'ns016-actual-completion-audit/v1','actual_execution':True,'fixture':False,
              'success':error is None,'started_at':started,'finished_at':dt.datetime.now(dt.timezone.utc).isoformat(),
              'elapsed_wall_seconds':time.monotonic()-clock,'argv':[sys.executable,*sys.argv],
              'python_version':sys.version,'source_sha256':digest(Path(__file__).read_bytes()),
              'repository':str(args.repository),'observed_head':locals().get('head'),
              'input_bindings':c.bindings,'result':result,'error':error,'criterion_judgments':None,
              'provider_calls':0,'scorer_calls':0,'native_calls':0,'receipt_created':False}
    with os.fdopen(os.open(args.report,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb') as stream:
        stream.write(json.dumps(record,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n');stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'success':record['success'],'report':str(args.report),'report_sha256':digest(args.report.read_bytes()),'criterion_judgments_supplied':False}))
    return 0 if record['success'] else 1

if __name__ == '__main__': raise SystemExit(main())
