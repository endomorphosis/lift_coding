#!/usr/bin/env python3
"""Recover candidate procedure rows; no upstream fetch, model, or study release."""
from pathlib import Path
import hashlib
import json
import re
import sqlite3
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DB = ROOT / 'papers/completion/runtime_bootstrap/la004_source_bridge/skillcenter-security.sqlite'
OLD = ROOT / '.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/benchmark/manifests/sources.json'
DB_SHA = '8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4'
CVE = ['twangboy/salt', 'ibus/ibus-anthy', 'boxug/trape', 'pikepdf/pikepdf',
       'fedora-selinux/setroubleshoot', 'astropy/astropy', 'redon-tech/redon-hub',
       'abetlen/llama-cpp-python', 'pandora-analysis/pandora',
       'triaxtec/openapi-python-client', 'octoprint/octoprint', 'horazont/xmpp-http-upload']
SELECT = {
    '02dc': ('https_headers', 'HSTS can lock clients into HTTPS for your domain; ensure HTTPS is correctly configured before enabling.',
             'Render a local HTTP response-header artifact while enforcing the documented HTTPS readiness precondition for HSTS.'),
    '03c1': ('jwt_bind', 'Verify and decode (bind) the JWT into a struct instance',
             'Verify a signed token against the task-provided secret and clock before exporting its non-secret subject fields.'),
    '03f6': ('xbox_credentials', 'Authorization: XBL3.0 x=<user_hash>;<xsts_token>',
             'Format the documented private Xbox authorization header and a public, secret-redacted diagnostic from a supplied authentication result.'),
    '041c': ('ip_assessment', 'Only analyze public IP addresses you are authorized to assess.',
             'Dispatch one authorized public-IP assessment to a bounded fixture scanner and emit an advisory report without taking blocking actions.'),
    '0505': ('current_user', 'return {"id": user.id, "username": user.username, "email": user.email}',
             'Resolve a session against the task-owned session store and return only the three documented current-user fields.'),
    '05f1': ('backup_code', 'Configure single-use backup codes to reduce account lockouts',
             'Consume one backup code atomically in a task-owned account fixture and produce a second-factor result; reject replay.'),
    '062b': ('s3_delete', 'allow unauthenticated GET for public reads, require auth for PUT/DELETE',
             'Apply an authenticated DELETE to a task-owned object-store fixture while preserving the bucket on denied requests.'),
    '0631': ('modsecurity_config', 'Ensure ModSecurity rules (local/remote/inline) are reviewed and tested',
             'Construct a local Nginx ModSecurity configuration from the explicit directives only when the referenced local rules have passed task-owned review and test checks.'),
    '06f2': ('graphql_preread', 'Use `preRead` to avoid triggering expensive or sensitive operations when access should be denied.',
             'Return a field-filtered record and enforce field authorization before the protected resolver is invoked.'),
    '0752': ('crudadmin_export', 'Add patterns like `*.db`, `*.sqlite`, `*.sqlite3`, and database journal files to `.gitignore`.',
             'Prepare a deterministic source export manifest and ignore rules while excluding actual database and journal artifacts from publication.'),
    '0766': ('fastly_config', 'Keep `.secret.client_id`, `.secret.client_secret`, and `.secret.nonce_secret` gitignored and out of logs.',
             'Encode pinned OIDC discovery and JWKS objects as the two documented Fastly configuration strings while producing a public source manifest that excludes secret files.'),
    '085b': ('django_refresh', 'Adjust refresh window by setting `JWT_REFRESH_EXPIRATION_DELTA` (default: 7 days).',
             'Refresh an authenticated fixture JWT only within the task-fixed original issuance window, preserving orig_iat rather than resetting the refresh lifetime.'),
}
REJECT = {
    '027b': 'Actual body gives deployment commands and names vulnerable/good modes, but contains no operative authentication or vulnerability rule sufficient for the bounded paired oracle; app implementations are only linked.',
    '02f3': 'InSpec execution instructions and expected pass/fail summary are present, but no Apache control bodies or concrete security predicates are included.',
    '034f': 'Readiness/discovery/JWKS smoke checks are present; concrete authentication and authorization rules remain in the unverified upstream implementation.',
    '03c7': 'Protocol and attribute mapping instructions refer to absent guides/configuration; no concrete mapping or identity decision can be grounded in this row alone.',
    '041e': 'Integration steps defer to upstream REST/API and setup documentation; exact token renewal and authorization behavior is absent.',
    '044c': 'The row delegates to an Authlete handler and application SPI but does not supply the application-specific authorization or normalization policy.',
    '0453': 'Generator/migration commands select authentication modes; operational auth decision semantics and generated artifacts are absent.',
    '0675': 'The body explicitly states setup and runtime details are not included in extracted text and points to a tutorial; no refresh/rotation implementation is available.',
    '0798': 'Container/port readiness commands provide no substantive token/authorization decision contract; full service images and behavior remain unverified.',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def repository(url):
    u = urlsplit(url)
    path = u.path.rstrip('/').removesuffix('.git')
    if u.hostname and u.hostname.lower() == 'github.com':
        path = '/' + '/'.join(path.strip('/').split('/')[:2]).lower()
    return (u.hostname or '').lower() + path


def binding(path):
    raw = path.read_bytes()
    return {'path': str(path.resolve()), 'bytes': len(raw), 'sha256': sha(raw)}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as out:
        out.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode() + b'\n')


def main():
    target = HERE / 'skill_candidates_v1'
    if target.exists():
        raise SystemExit('Refusing to replace an existing candidate inspection')
    assert sha(DB.read_bytes()) == DB_SHA
    rule = json.loads((HERE / 'prospective_eligibility_rule.json').read_text())
    assert rule['model_calls_allowed_now'] is False and rule['final_cohort_release_allowed_now'] is False
    old = json.loads(OLD.read_text())['source_records']
    old_repos = {r['ancestry_key'][1] for r in old if r['ancestry_key'][0] == 'repository'}
    old_primary = {r['source_locator']['primary_source_id'] for r in old if r['population'] == 'skill'}
    old_body = {r['normalized_source_sha256'] for r in old}
    cve_repos = {'github.com/' + name.lower() for name in CVE}
    connection = sqlite3.connect(DB.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    connection.row_factory = sqlite3.Row
    query = 'SELECT i.*, c.metadata_yaml, c.skill_md, c.library_md FROM skills_index i JOIN skills_content c USING(skill_id) ORDER BY i.skill_id'
    rows = [dict(r) for r in connection.execute(query)]
    connection.close()
    inspected, candidates = [], []
    for position, row in enumerate(rows, 1):
        sid, body = row['skill_id'], row['skill_md']
        repo = repository(row['source_url'])
        primary = row['primary_source_id'] or row['source_id']
        normal = sha(re.sub(r'\s+', ' ', body).encode())
        decision = {'joined_order_1_based': position, 'skill_id': sid, 'title': row['title'], 'repository': repo,
                    'primary_source_id': primary, 'source_row_canonical_sha256': sha(canonical(row)),
                    'skill_md_utf8_sha256': sha(body.encode()), 'normalized_source_sha256': normal}
        if repo in old_repos or primary in old_primary or normal in old_body:
            decision.update(status='EXCLUDED_HISTORICAL_LINEAGE_OR_DUPLICATE', reason='Excluded union of historical LA004/LA029 repository, primary-source and normalized-body identities.')
        elif repo in cve_repos:
            decision.update(status='EXCLUDED_NEW_CVE_REPOSITORY', reason='Repository family reserved by the prospective CVE candidate population.')
        elif sid[:4] in REJECT:
            decision.update(status='EXCLUDED_INSUFFICIENT_OPERATIVE_BODY', reason=REJECT[sid[:4]])
        elif sid[:4] in SELECT:
            key, quote, task = SELECT[sid[:4]]
            assert quote in body, (sid, quote)
            decision.update(status='CANDIDATE_SOURCE_RELATIVE_TASK_ONLY', reason=task)
            family = 'skill-new-' + key
            row_path = target / 'source_rows' / (sid + '.json')
            write(row_path, row)
            for suffix, field in [('md', 'skill_md'), ('metadata.yaml', 'metadata_yaml')]:
                path = target / 'procedures' / (sid + '.' + suffix)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as out:
                    out.write(row[field].encode())
            start = body.encode().index(quote.encode())
            candidates.append({**decision, 'family_id': family, 'task_key': key, 'source_url': row['source_url'],
                               'row_snapshot': str(row_path.relative_to(target)), 'row_snapshot_sha256': sha(row_path.read_bytes()),
                               'procedure_path': 'procedures/' + sid + '.md',
                               'grounding': {'exact_excerpt': quote, 'utf8_byte_start': start, 'utf8_byte_end_exclusive': start + len(quote.encode())},
                               'provenance_boundary': 'The exact pinned generated SkillCenter procedure is available. The linked upstream repository contents and original captured source artifact are not supplied by this SQLite row.',
                               'authorship': 'Generated procedure; metadata records llm_provider=openai and llm_model=gpt-5.2. Not an independent human annotation.',
                               'upstream_immutable_commit': None, 'upstream_license_verified': False,
                               'admission_gaps': ['Verify immutable upstream source and applicable license/redistribution terms.',
                                                  'Resolve repository fork/rename ancestry and nearest-neighbor leakage against all old/new families.',
                                                  'Review the source-to-task adaptation and task-defined policy choices independently.',
                                                  'Implement and qualify useful generated programs, native fact/intent/effect mapping, independent observer and resource-bounded runtime; current two-sink development profile is insufficient.',
                                                  'Freeze prospective family splits and verify model/runtime/scheduler qualification before scientific dispatch.'],
                               'scientific_admission': False, 'split': None})
        else:
            raise AssertionError('Unrecorded prospective inspection decision: ' + sid)
        inspected.append(decision)
        if len(candidates) == 12:
            break
    assert len(candidates) == 12 and len({x['repository'] for x in candidates}) == 12
    assert sha(DB.read_bytes()) == DB_SHA
    write(target / 'inspection_audit.json', {'schema': 'skill-prospective-inspection/v1', 'rule': binding(HERE / 'prospective_eligibility_rule.json'),
           'historical_manifest': binding(OLD), 'historical_repository_keys': sorted(old_repos),
           'historical_primary_source_ids': sorted(old_primary), 'new_cve_repository_keys': sorted(cve_repos),
           'selection_uses_model_outcomes': False, 'stopped_after_first_12_source_eligible_candidates': True,
           'inspected': inspected})
    write(target / 'source_manifest.json', {'schema': 'skill-source-candidate-manifest/v1', 'status': 'CANDIDATE_SOURCE_INSPECTION_NOT_SCIENTIFIC_RELEASE',
           'bundle': binding(DB), 'bundle_uri': 'https://huggingface.co/datasets/Tommysha/skillcenter-bundles/resolve/f9dd4fec3c86d85ebf116c7408ac5ce602c418a1/clawskills-bundle-lite-security-v20260227.sqlite',
           'bundle_revision': 'f9dd4fec3c86d85ebf116c7408ac5ce602c418a1', 'query': query,
           'canonical_row_encoding': 'Sorted compact UTF-8 JSON, ensure_ascii=False; full joined index/content values including library_md. This row encoding intentionally binds the complete available row, not only a title or URL.',
           'row_count_in_bundle': len(rows), 'candidate_count': len(candidates), 'families': candidates,
           'model_calls': 0, 'upstream_network_calls': 0, 'scientific_release': False})
    print(json.dumps({'candidates': len(candidates), 'inspected_rows': len(inspected), 'output': str(target)}))


if __name__ == '__main__':
    main()
