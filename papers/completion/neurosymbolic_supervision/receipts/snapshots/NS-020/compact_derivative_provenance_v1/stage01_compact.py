import copy
import hashlib
import json
from pathlib import Path

ROOT = Path('.').resolve()
P = ROOT / 'papers/completion/neurosymbolic_supervision'
CURRENT = P / 'analysis/boundary_witnesses.json'
SNAP = P / 'receipts/snapshots/NS-020/reconciled_final32/analysis/boundary_witnesses.json'
MANIFEST_SHA = '0891bee6e3a556f5448250bbf11815ac255958a2f02add848d4e0934f23aeeac'
RESULTS_SHA = '6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e'
ANALYZER_SHA = '16da76bbe3fe032cde70599790ad8ad1e52d9eb1baf4ea799cf4856d23410251'
CORE = ('number', 'cell_id', 'unit', 'arm', 'repetition', 'cache', 'terminal', 'outcome', 'useful_completion')
JOIN_FIELDS = {
    'F-HTTP': ('http',),
    'F-custody': ('candidate',),
    'F-score': ('score',),
    'F-lease': ('time_and_resources', 'termination'),
    'F-failure': ('http', 'score', 'failure_accounting', 'termination'),
}

raw = json.loads(CURRENT.read_bytes())
assert CURRENT.read_bytes() == SNAP.read_bytes()
assert 'empirical_final_cells' not in raw
joins = raw['final_empirical_boundary_joins']

def compact_ref(obj):
    if obj is None:
        return None
    if not isinstance(obj, dict):
        return obj
    keep = {}
    for key in (
        'sha256', 'repository_path', 'label', 'retained_object_available',
        'body_read_and_hash_verified', 'body_read_by_this_helper',
    ):
        if key in obj:
            keep[key] = obj[key]
    return keep

def compact_provenance(p):
    if not p:
        return p
    out = {
        'continuation_applied': p.get('continuation_applied'),
        'epoch': p.get('epoch'),
        'lease_liveness_verified': p.get('lease_liveness_verified'),
        'original_frozen_package_sha256': p.get('original_frozen_package_sha256'),
    }
    if p.get('contract_sha256'):
        out['contract_sha256'] = p['contract_sha256']
    rc = p.get('runtime_continuation')
    if rc:
        out['runtime_continuation'] = {
            'continuation_id': rc.get('continuation_id'),
            'effective_source_sha256': rc.get('effective_source_sha256'),
            'original_frozen_package_sha256': rc.get('original_frozen_package_sha256'),
            'authority_sha256': (rc.get('authority') or {}).get('sha256'),
            'successor_resource_reservation_sha256': (rc.get('successor_resource_reservation') or {}).get('sha256'),
        }
    return out

def compact_candidate(c):
    if c is None:
        return None
    out = {
        'candidate_present': c.get('candidate_present'),
        'candidate_code_or_patch_read': c.get('candidate_code_or_patch_read'),
        'candidate_review': None,
        'derived_metadata_provenance_categories': [d.get('category') for d in (c.get('derived_metadata_provenance') or [])],
    }
    if not c.get('candidate_present'):
        out['reason'] = c.get('reason')
        out['candidate_binding_metadata'] = None
        return out
    out.update({
        'signed_candidate_inventory_sha256': c.get('signed_candidate_inventory_sha256'),
        'candidate_binding_metadata': compact_ref(c.get('candidate_binding_metadata')),
        'candidate_binding_metadata_origin': c.get('candidate_binding_metadata_origin'),
        'patch_sha256': c.get('patch_sha256'),
        'patch_bytes': c.get('patch_bytes'),
        'changed_paths': c.get('changed_paths'),
        'review_after_grant_expiry': c.get('review_after_grant_expiry'),
    })
    review = c.get('candidate_review')
    if review:
        out['candidate_review'] = {
            'approved': review.get('approved'),
            'reviewed_at': review.get('reviewed_at'),
            'human_annotation': review.get('human_annotation'),
            'comprehensive_adversarial_scorer_qualification': review.get('comprehensive_adversarial_scorer_qualification'),
            'scope': review.get('scope'),
            'reference': compact_ref(review.get('reference')),
            'binding_sha256s': {k: v for k, v in (review.get('binding') or {}).items() if k.endswith('_sha256') or k in ('cell_id', 'record_kind')},
        }
    return out

def compact_time(t):
    if t is None:
        return None
    phases = []
    for p in t.get('operator_phases') or []:
        phases.append({
            'phase': p.get('phase'),
            'number': p.get('number'),
            'elapsed_host_wall_seconds': p.get('elapsed_host_wall_seconds'),
            'measured': p.get('measured'),
            'exit_code': p.get('exit_code'),
            'automatic_retry': p.get('automatic_retry'),
            'changes_signed_compliance': p.get('changes_signed_compliance'),
            'summed_with_nested_clocks': p.get('summed_with_nested_clocks'),
            'missing_reason': p.get('missing_reason'),
            'execution_sha256': (p.get('execution') or {}).get('sha256'),
            'execution_repository_path': p.get('execution_repository_path'),
        })
    return {
        'clocks': t.get('clocks'),
        'signed_resource_compliance': t.get('signed_resource_compliance'),
        'operator_phases': phases,
        'clock_grand_total': t.get('clock_grand_total'),
        'overlapping_clocks_summed': t.get('overlapping_clocks_summed'),
    }

def compact_failure(f):
    if f is None:
        return None
    return {
        'classification': f.get('classification'),
        'success_credit': f.get('success_credit'),
        'retry_allowed': f.get('retry_allowed'),
        'accounting_reviewed_at': f.get('accounting_reviewed_at'),
        'signed_disposition': compact_ref(f.get('signed_disposition')),
        'operator_accounting': compact_ref(f.get('operator_accounting')),
        'retained_accounting_statement': f.get('retained_accounting_statement'),
    }

def compact_disclosures(items):
    out = []
    for d in items or []:
        item = {k: d[k] for k in d if k != 'evidence'}
        item['evidence'] = [compact_ref(e) for e in (d.get('evidence') or [])]
        out.append(item)
    return out

def compact_runtime(rt):
    return {
        'row_provenance': compact_provenance(rt.get('row_provenance')),
        'source_epoch': rt.get('source_epoch'),
        'source_files': [{'role': s['role'], **compact_ref(s.get('binding') or {})} for s in (rt.get('source_files') or [])],
        'cooperative_lease_not_physical_exclusivity': rt.get('cooperative_lease_not_physical_exclusivity'),
        'current_liveness_rechecked': rt.get('current_liveness_rechecked'),
    }

cells = {}
order = []
native_versions = None
for boundary in joins:
    for row in boundary['empirical_final_rows']:
        cid = row['cell_id']
        if cid not in cells:
            cells[cid] = {k: row[k] for k in CORE}
            order.append(cid)
            native_versions = row['runtime']['native_source_versions']
        cell = cells[cid]
        if row.get('http') is not None:
            cell.setdefault('http', row['http'])
        if row.get('score') is not None:
            cell.setdefault('score', row['score'])
        if 'candidate' in row:
            cell['candidate'] = compact_candidate(row['candidate'])
        if 'time_and_resources' in row:
            cell['time_and_resources'] = compact_time(row['time_and_resources'])
        if 'failure_accounting' in row:
            cell['failure_accounting'] = compact_failure(row['failure_accounting'])
        if 'termination' in row:
            cell['termination'] = row['termination']
        cell.setdefault('references', {name: compact_ref(ref) for name, ref in row['references'].items()})
        cell.setdefault('runtime', compact_runtime(row['runtime']))
        cell.setdefault('validation_and_operational_disclosures', compact_disclosures(row.get('validation_and_operational_disclosures')))
        cell.setdefault('human_annotation', False)

require_order = raw['actual_final32_reconciliation']['original_ordered_cells']
assert order == require_order
compact_cells = [cells[cid] for cid in order]
assert len(compact_cells) == 32
for cell in compact_cells:
    assert set(CORE) <= set(cell)
    assert isinstance(cell['http'], dict)
    assert isinstance(cell['score'], dict)
    assert isinstance(cell.get('candidate'), dict)
    assert isinstance(cell.get('time_and_resources'), dict)
    assert 'failure_accounting' in cell
    assert cell['references']['original_signed_receipt']['sha256']
    assert cell['runtime']['source_files']
    assert cell['human_annotation'] is False

new_joins = []
for boundary in joins:
    item = {k: copy.deepcopy(v) for k, v in boundary.items() if k != 'empirical_final_rows'}
    item['selected_fields'] = list(JOIN_FIELDS[boundary['id']])
    item['empirical_final_rows'] = [{k: cells[cid][k] for k in CORE} for cid in order]
    item['empirical_final_row_recipe'] = 'core_identity_fields_only; HTTP/custody/score/lease/failure mapping is in empirical_final_cells as SHA256 pointers to retained NS-017 objects'
    new_joins.append(item)

compact = copy.deepcopy(raw)
compact['envelope_recipe'] = {
    'full_envelopes_reemitted': False,
    'generator_snapshot': 'papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-020/reconcile_boundaries.py',
    'kind': 'compact_sha256_pointer_recipe',
    'private_original_paths_omitted': True,
    'retained_population': {
        'NS017_manifest_sha256': MANIFEST_SHA,
        'NS019_renderer_sha256': ANALYZER_SHA,
        'NS019_results_sha256': RESULTS_SHA,
    },
    'scope': 'Each of 32 original-order terminals is mapped by SHA256 to retained signed receipts, candidate metadata, cold-score fields, lease/time clocks and failure accounting. Full retained bodies stay in NS-017 objects and NS-019 results; they are not re-copied into this file.',
}
compact['empirical_final_cells'] = compact_cells
compact['final_empirical_boundary_joins'] = new_joins
compact['native_source_versions'] = native_versions

encoded = (json.dumps(compact, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
print('compact_bytes', len(encoded))
assert len(encoded) < 1048576, len(encoded)
blob = encoded.decode()
assert 'original_paths_provenance_only' not in blob
assert compact['table18_rows'] == raw['table18_rows']
# Private original host paths must not be re-emitted as envelope dumps.
for needle in ('/home/barberb/lift_coding', 'research-inputs/neurosymbolic_supervision/final-host'):
    if needle in blob:
        idx = blob.find(needle)
        raise SystemExit('private path remained: ' + blob[max(0,idx-80):idx+160])
CURRENT.write_bytes(encoded)
SNAP.write_bytes(encoded)
digest = hashlib.sha256(encoded).hexdigest()
print('boundary_witnesses_sha256', digest)
print('cells', len(compact_cells), 'useful', sum(c['useful_completion'] is True for c in compact_cells))
print('outcomes', {k: sum(1 for c in compact_cells if c['outcome']==k) for k in sorted({c['outcome'] for c in compact_cells})})
print('current_size', CURRENT.stat().st_size, 'snap_size', SNAP.stat().st_size)
