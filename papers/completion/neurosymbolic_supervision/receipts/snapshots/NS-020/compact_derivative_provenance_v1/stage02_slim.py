import hashlib, json
from pathlib import Path

CURRENT = Path('papers/completion/neurosymbolic_supervision/analysis/boundary_witnesses.json')
SNAP = Path('papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-020/reconciled_final32/analysis/boundary_witnesses.json')
w = json.loads(CURRENT.read_bytes())

def slim_disclosures(items):
    out = []
    for d in items or []:
        out.append({
            'category': d.get('category'),
            'signed_outcome': d.get('signed_outcome'),
            'useful_completion': d.get('useful_completion'),
            'sanitized_only': d.get('sanitized_only'),
            'original_signed_receipt_sha256': d.get('original_signed_receipt_sha256'),
            'evidence': [{'sha256': e.get('sha256'), 'repository_path': e.get('repository_path'),
                          'retained_object_available': e.get('retained_object_available')}
                         for e in (d.get('evidence') or []) if isinstance(e, dict)],
        })
    return out

def slim_failure(f):
    if f is None:
        return None
    return {
        'classification': f.get('classification'),
        'success_credit': f.get('success_credit'),
        'retry_allowed': f.get('retry_allowed'),
        'accounting_reviewed_at': f.get('accounting_reviewed_at'),
        'signed_disposition': f.get('signed_disposition'),
        'operator_accounting': f.get('operator_accounting'),
    }

def slim_phases(phases):
    out = []
    for p in phases or []:
        out.append({
            'phase': p.get('phase'),
            'elapsed_host_wall_seconds': p.get('elapsed_host_wall_seconds'),
            'measured': p.get('measured'),
            'exit_code': p.get('exit_code'),
            'automatic_retry': p.get('automatic_retry'),
            'changes_signed_compliance': p.get('changes_signed_compliance'),
            'summed_with_nested_clocks': p.get('summed_with_nested_clocks'),
            'execution_sha256': p.get('execution_sha256'),
            'execution_repository_path': p.get('execution_repository_path'),
        })
    return out

for cell in w['empirical_final_cells']:
    cell['validation_and_operational_disclosures'] = slim_disclosures(cell.get('validation_and_operational_disclosures'))
    cell['failure_accounting'] = slim_failure(cell.get('failure_accounting'))
    clocks = cell.get('time_and_resources') or {}
    clocks['operator_phases'] = slim_phases(clocks.get('operator_phases'))
    cell['time_and_resources'] = clocks
    # drop review binding dump; keep reference sha and flags
    cand = cell.get('candidate') or {}
    review = cand.get('candidate_review')
    if review and 'binding_sha256s' in review:
        # keep only cell_id/record_kind plus a count; the review reference sha remains
        binding = review.pop('binding_sha256s')
        review['binding_digest_count'] = len(binding)
        cand['candidate_review'] = review
        cell['candidate'] = cand

encoded = (json.dumps(w, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
print('minified_bytes', len(encoded))
assert len(encoded) < 700000
blob = encoded.decode()
assert 'original_paths_provenance_only' not in blob
assert '/home/barberb/lift_coding' not in blob
assert w['table18_rows']
assert len(w['empirical_final_cells']) == 32
CURRENT.write_bytes(encoded)
SNAP.write_bytes(encoded)
print('sha256', hashlib.sha256(encoded).hexdigest())
print('lines', blob.count('\n'))
