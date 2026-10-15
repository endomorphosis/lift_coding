#!/usr/bin/env python3
"""Complete source screens for the five remaining alternative Python CVE rows.

This inspects retained parquet diffs. It does not admit families or execute cells.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
PARQUET = Path('/home/barberb/lift_coding/papers/completion/runtime_bootstrap/la004_source_bridge/train-00000-of-00003.parquet')
AUDIT = HERE / 'cve_screening_audit.json'
OUT = HERE / 'alternative_row_screen_v1'
WANTED = (130, 150, 151, 152, 153)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_rows():
    found = {}
    index = 0
    for batch in pq.ParquetFile(PARQUET).iter_batches(batch_size=16):
        for row in batch.to_pylist():
            if index in WANTED:
                found[index] = row
            index += 1
        if index > max(WANTED):
            break
    if set(found) != set(WANTED):
        raise SystemExit('missing alternative rows: ' + str(sorted(set(WANTED) - set(found))))
    return found


def main():
    rows = load_rows()
    decisions = [
        {
            'physical_row': 130,
            'cve_id': rows[130]['cve_id'],
            'repository': 'github.com/nicolargo/glances',
            'fix_commit': rows[130]['hash'],
            'diff_sha256': hashlib.sha256(rows[130]['diff_with_context'].encode()).hexdigest(),
            'inspected_paths': rows[130]['file_paths'],
            'status': 'SAME_CANDIDATE_REPOSITORY_NOT_AN_INDEPENDENT_FAMILY',
            'reason': 'Same repository as inspected-not-qualified row 129. The retained diff is README/requirements plus a process-wide defusedxml.xmlrpc monkey_patch. That is not an independent family, and it is not a bounded local generated-program task under the chosen profile.',
        },
        {
            'physical_row': 150,
            'cve_id': rows[150]['cve_id'],
            'repository': 'github.com/dpgaspar/flask-appbuilder',
            'fix_commit': rows[150]['hash'],
            'diff_sha256': hashlib.sha256(rows[150]['diff_with_context'].encode()).hexdigest(),
            'inspected_paths': rows[150]['file_paths'],
            'status': 'SAME_CANDIDATE_REPOSITORY_NOT_AN_INDEPENDENT_FAMILY',
            'reason': 'Same canonical repository as inspected-not-qualified row 149. Eligibility treats the repository, including other CVEs, as one family. The OAuth next-URL change cannot occupy an additional family slot.',
        },
        {
            'physical_row': 151,
            'cve_id': rows[151]['cve_id'],
            'repository': 'github.com/dpgaspar/flask-appbuilder',
            'fix_commit': rows[151]['hash'],
            'diff_sha256': hashlib.sha256(rows[151]['diff_with_context'].encode()).hexdigest(),
            'inspected_paths': rows[151]['file_paths'],
            'status': 'SAME_CANDIDATE_REPOSITORY_NOT_AN_INDEPENDENT_FAMILY',
            'reason': 'Same Flask-AppBuilder family as row 149. Login-schema changes are not an independent source lineage.',
        },
        {
            'physical_row': 152,
            'cve_id': rows[152]['cve_id'],
            'repository': 'github.com/dpgaspar/flask-appbuilder',
            'fix_commit': rows[152]['hash'],
            'diff_sha256': hashlib.sha256(rows[152]['diff_with_context'].encode()).hexdigest(),
            'inspected_paths': rows[152]['file_paths'],
            'status': 'SAME_CANDIDATE_REPOSITORY_NOT_AN_INDEPENDENT_FAMILY',
            'reason': 'Same Flask-AppBuilder family as row 149. The retained diff is CRUD log/error-message handling, not an independent family and not a replacement for the timing-side-channel exclusion.',
        },
        {
            'physical_row': 153,
            'cve_id': rows[153]['cve_id'],
            'repository': 'github.com/dpgaspar/flask-appbuilder',
            'fix_commit': rows[153]['hash'],
            'diff_sha256': hashlib.sha256(rows[153]['diff_with_context'].encode()).hexdigest(),
            'inspected_paths': rows[153]['file_paths'],
            'status': 'SAME_CANDIDATE_REPOSITORY_NOT_AN_INDEPENDENT_FAMILY',
            'reason': 'Same Flask-AppBuilder family as row 149. OpenID provider-URL validation cannot create a thirteenth CVE family.',
        },
    ]
    audit = json.loads(AUDIT.read_text())
    by_row = {item['physical_row']: item for item in audit['rows']}
    for decision in decisions:
        item = by_row[decision['physical_row']]
        if item['status'] not in {'ADDITIONAL_ROW_REQUIRING_SCREEN_COMPLETION', decision['status']}:
            raise SystemExit('unexpected prior status for row %s: %s' % (decision['physical_row'], item['status']))
        item['status'] = decision['status']
        item['reason'] = decision['reason']
        item['screen_completed_at'] = datetime.now(timezone.utc).isoformat()
        item['screen_evidence'] = 'alternative_row_screen_v1/screen.json'
    counts = {}
    for item in audit['rows']:
        counts[item['status']] = counts.get(item['status'], 0) + 1
    audit['counts'] = counts
    audit['complete_deterministic_scientific_selection_qualified'] = False
    audit['alternative_python_rows_screen_completed'] = True
    audit['notes'] = 'Rows 130 and 150-153 are now screened as same-repository non-independent families. Fork/alias/near-neighbor closure and remaining source-to-task qualification still block scientific admission.'
    OUT.mkdir(exist_ok=True)
    report = {
        'schema': 'la-alternative-cve-row-screen/v1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'parquet_sha256': sha(PARQUET),
        'audit_sha256_before_write': sha(AUDIT),
        'scientific_admitted_families': 0,
        'scientific_cells_executed': 0,
        'model_calls': 0,
        'decisions': decisions,
        'counts_after': counts,
        'notes': 'Screen completion is not family admission. The twelve selected CVE families are unchanged.',
    }
    (OUT / 'screen.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    AUDIT.write_text(json.dumps(audit, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': 'SCREEN_COMPLETED_NOT_ADMITTED', 'counts': counts, 'report': str(OUT / 'screen.json')}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
