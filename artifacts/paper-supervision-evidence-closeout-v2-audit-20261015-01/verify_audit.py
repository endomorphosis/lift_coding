"""Read-only standard-library hash, identity, schema and release-boundary checks."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent

def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    output = parser.parse_args().output
    checks = []
    def check(name, passed, detail=None):
        checks.append({'check': name, 'passed': bool(passed), 'detail': detail})
    artifacts = rows(BASE/'artifacts.jsonl')
    for item in artifacts:
        p = Path(item['path'])
        valid = p.is_relative_to('/home/barberb/lift_coding') and p.resolve() == p and p.is_file()
        valid = valid and p.stat().st_size == item['bytes'] and p.stat().st_size <= 2*1024*1024
        check('original input unchanged: '+item['path'], valid and sha(p) == item['sha256'])
    manifest = json.loads((BASE/'audit/output_manifest.json').read_text())
    for item in manifest['files']:
        p = BASE/item['path']
        valid = p.is_relative_to(BASE) and p.resolve() == p and p.is_file()
        check('audit file hash: '+item['path'], valid and sha(p) == item['sha256'])
    ledger = rows(BASE/'runs.jsonl')
    sessions = rows(BASE/'sessions.jsonl')
    traces = rows(BASE/'cross_ir_trace.jsonl')
    by_id = {r['ledger_id']:r for r in ledger}
    check('unique ledger identities', len(by_id) == len(ledger))
    check('unique session/call identities', len({s['ledger_id'] for s in sessions}) == len(sessions))
    graph = rows(BASE/'evidence_graph.jsonl')
    check('call IDs never imply shared sessions', all(e.get('identity_kind') != 'provider_call_id_not_a_session' for e in graph if e.get('relation') == 'same-session-as'))
    check('null IDs never joined as actual invocation', all(x['status']=='unavailable/unsupported' for x in traces if x['run_id'] is None))
    check('uninvoked slots never promoted', all(x['status'] != 'actually invoked' for x in traces if by_id[x['ledger_id']]['invoked'] is False))
    check('source inference does not assert Intent grounding', all(x['stage'] != 'intent_to_source_grounding' and x['intent_to_codebase_admitted_correspondence']=='unavailable/unsupported' for x in traces if x['domain']=='CodebaseIR'))
    table = list(csv.DictReader((BASE/'results.csv').open()))
    for r in table:
        expected = by_id[r['audit_id']]['reported_tokens'].get('total_tokens')
        check('table preserves reported counters: '+r['audit_id'], r['reported_total_tokens'] == ('' if expected is None else str(expected)))
    numerical = json.loads((BASE/'audit/numerical_audit.json').read_text())
    check('arithmetic checks', numerical['passed'] and all(x['passed'] for x in numerical['checks']), len(numerical['checks']))
    plan = json.loads((BASE/'next_experiments.yaml').read_text())
    approvals = []
    def walk(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if ('approved' in k or 'approval' in k) and isinstance(v,bool): approvals.append(v)
                walk(v)
        elif isinstance(value,list):
            for v in value: walk(v)
    walk(plan)
    check('experiment approvals false', bool(approvals) and not any(approvals),len(approvals))
    public = (BASE/'anonymous/results.csv').read_text()
    original_ids = [r['original_run_id'] for r in ledger if r['original_run_id']]
    check('anonymous derivative excludes original IDs and local paths', '/home/' not in public and all(x not in public for x in original_ids))
    inv = json.loads((BASE/'anonymous/release_inventory.json').read_text())
    check('anonymous derivative has new hash and no inherited signature', inv['derivatives'][0]['sha256']==sha(BASE/'anonymous/results.csv') and inv['original_signatures_inherited'] is False)
    check('publication remains unauthorized', inv['release_authorized'] is False and inv['uploaded'] is False)
    auth = json.loads((BASE/'authorization.json').read_text())
    check('supervisor state remains outside audit authority', auth['supervisor_objective_submitted'] is False and auth['supervisor_state_mutated'] is False)
    result = {'schema':'paper-closeout-integrity@1','passed':all(c['passed'] for c in checks),
              'checks':checks, 'scope':'Hash/schema/identity/release-boundary checks; no signatures, behavioral authenticity, solver execution or model calls',
              'manifest_sha256':sha(BASE/'audit/output_manifest.json')}
    with output.open('x') as f:
        json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    output.chmod(0o600)
    print(json.dumps({'passed':result['passed'],'checks':len(checks),'failures':[x for x in checks if not x['passed']],'output':str(output)}))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':
    os.umask(0o077)
    main()
