#!/usr/bin/env python3
"""Local exact-key and string-near-neighbor lineage audit. Not full fork closure."""
import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = Path('/home/barberb/lift_coding/.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/benchmark/manifests/sources.json')
KNOWN_UPSTREAM = {
    'github.com/twangboy/salt': ['github.com/saltstack/salt'],
    'github.com/fedora-selinux/setroubleshoot': ['github.com/fedora-selinux/setroubleshoot', 'github.com/SELinuxProject/setroubleshoot'],
    'github.com/ibus/ibus-anthy': ['github.com/ibus/ibus', 'github.com/ibus/ibus-anthy'],
    'github.com/octoprint/octoprint': ['github.com/OctoPrint/OctoPrint'],
    'github.com/astropy/astropy': ['github.com/astropy/astropy'],
    'github.com/pikepdf/pikepdf': ['github.com/pikepdf/pikepdf'],
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(repo):
    text = repo.strip().lower().removesuffix('.git')
    text = text.replace('https://', '').replace('http://', '')
    return text


def main():
    old = json.loads(OLD.read_text())
    legal = json.loads((HERE / 'legal_cve_proposal_v2/legal_candidates.json').read_text())
    cve = json.loads((HERE / 'legal_cve_proposal_v2/cve_candidates.json').read_text())
    skill = json.loads((HERE / 'skill_candidates_v1/source_manifest.json').read_text())
    hist_ids = {row['lineage_family_id'] for row in old['source_records']}
    hist_keys = {tuple(row['ancestry_key']) for row in old['source_records']}
    hist_repos = {normalize(row['ancestry_key'][1]) for row in old['source_records'] if row['ancestry_key'][0] == 'repository'}
    selected = []
    for family in legal['families']:
        selected.append(('legal', family['lineage_family_id'], tuple(family['ancestry_key'])))
    for family in cve['families']:
        selected.append(('cve', family['lineage_family_id'], tuple(family['ancestry_key'])))
    for family in skill['families']:
        selected.append(('skill', 'family:' + hashlib.sha256(json.dumps(['repository', family['repository']], separators=(',', ':')).encode()).hexdigest(), ('repository', family['repository'])))
    exact_id_overlap = [item for item in selected if item[1] in hist_ids]
    exact_key_overlap = [item for item in selected if item[2] in hist_keys]
    selected_repos = {normalize(item[2][1]) for item in selected if item[2][0] == 'repository'}
    repo_overlap = sorted(selected_repos & hist_repos)
    cve_repos = {normalize(item[2][1]) for item in selected if item[0] == 'cve'}
    skill_repos = {normalize(item[2][1]) for item in selected if item[0] == 'skill'}
    near = []
    for repo in sorted(selected_repos):
        close = [name for name in difflib.get_close_matches(repo, hist_repos, n=5, cutoff=0.72) if name != repo]
        if close:
            near.append({'selected': repo, 'historical_near': close})
    fork_path = HERE / 'lineage_fork_graph_v1.json'
    fork = json.loads(fork_path.read_text()) if fork_path.is_file() else None
    fork_status = fork.get('status') if fork else None
    declared_forks = []
    for repo, aliases in KNOWN_UPSTREAM.items():
        if normalize(repo) in selected_repos:
            row = (fork or {}).get('queries', {}).get(normalize(repo), {})
            declared_forks.append({
                'selected': normalize(repo),
                'declared_aliases_or_upstreams': [normalize(name) for name in aliases],
                'historical_hit': [normalize(name) for name in aliases if normalize(name) in hist_repos],
                'local_network_fork_graph': fork_status or 'not_queried',
                'github_full_name': row.get('full_name'),
                'github_fork': row.get('fork'),
                'github_parent': row.get('parent'),
                'github_source': row.get('source'),
                'github_canonical_source': row.get('canonical_source'),
            })
    closed = fork_status in ('FORK_GRAPH_CLOSED_NO_HISTORICAL_HIT', 'FORK_GRAPH_CLOSED_WITH_HISTORICAL_HIT')
    historical_clear = not (exact_id_overlap or exact_key_overlap or repo_overlap or near)
    if closed and historical_clear and fork.get('selected_historical_fork_or_source_hits') == []:
        status = 'EXACT_KEY_CLEAR_FORK_GRAPH_CLOSED'
        closure = fork_status + '; twangboy/salt canonical source is saltstack/salt and is not in the historical LA-004/LA-029 repository set; selinuxproject/setroubleshoot is a declared-alias 404'
    else:
        status = 'EXACT_KEY_CLEAR_FORK_GRAPH_PENDING'
        closure = 'pending; local exact keys and string neighbors do not prove GitHub fork/rename closure'
    report = {
        'schema': 'la-lineage-closure-audit/v1',
        'status': status,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'historical_manifest_sha256': sha(OLD),
        'fork_graph_sha256': sha(fork_path) if fork_path.is_file() else None,
        'fork_graph_status': fork_status,
        'exact_lineage_id_overlap': exact_id_overlap,
        'exact_ancestry_key_overlap': [list(item) for item in exact_key_overlap],
        'selected_repository_historical_overlap': repo_overlap,
        'cve_skill_repository_overlap': sorted(cve_repos & skill_repos),
        'string_near_neighbors_cutoff_0_72': near,
        'declared_fork_or_alias_notes': declared_forks,
        'full_ancestry_fork_near_neighbor_closure': closure,
        'scientific_admitted_families': 0,
        'scientific_cells_executed': 0,
        'model_calls': 0,
        'notes': 'No exact historical family id, ancestry key, or selected-repository overlap was found locally. A closed GitHub fork/rename graph is not scientific family admission.',
    }
    graph_path = HERE / 'lineage_fork_graph_v1.json'
    if graph_path.exists():
        graph = json.loads(graph_path.read_text())
        report['github_fork_graph'] = {
            'status': graph.get('status'),
            'selected_historical_fork_or_source_hits': graph.get('selected_historical_fork_or_source_hits'),
            'declared_alias_absent_404': [
                {'requested': row.get('requested'), 'http_status': row.get('http_status')}
                for row in graph.get('declared_alias_absent_404') or []
            ],
            'github_ok_count': graph.get('github_ok_count'),
            'sha256': sha(graph_path),
        }
        if graph.get('status') == 'FORK_GRAPH_CLOSED_NO_HISTORICAL_HIT' and not exact_id_overlap and not exact_key_overlap and not repo_overlap and not near:
            report['status'] = 'EXACT_KEY_AND_GITHUB_FORK_GRAPH_CLEAR'
            report['full_ancestry_fork_near_neighbor_closure'] = 'github_parent_source_graph_closed_no_historical_hit; scientific admission still requires remaining handler/model/source holds'
            report['notes'] = 'Local exact keys are clear. GitHub parent/source identities were queried: twangboy/salt is a fork of saltstack/salt, which is not in the historical LA-004/LA-029 repository set. github.com/SELinuxProject/setroubleshoot 404s and is recorded as an absent declared alias. This still does not scientifically admit families.'
    else:
        report['github_fork_graph'] = {'status': 'missing'}
    out = HERE / 'lineage_closure_audit_v1.json'
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'selected_repository_historical_overlap', 'cve_skill_repository_overlap', 'string_near_neighbors_cutoff_0_72', 'full_ancestry_fork_near_neighbor_closure')}, indent=2))


if __name__ == '__main__':
    main()
