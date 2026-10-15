#!/usr/bin/env python3
"""Query GitHub parent/source identities for selected vs historical repositories.

This is fork/rename closure evidence. It does not scientifically admit families.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = Path("/home/barberb/lift_coding/.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/benchmark/manifests/sources.json")
KNOWN_UPSTREAM = {
    "github.com/twangboy/salt": ["github.com/saltstack/salt"],
    "github.com/fedora-selinux/setroubleshoot": ["github.com/fedora-selinux/setroubleshoot", "github.com/SELinuxProject/setroubleshoot"],
    "github.com/ibus/ibus-anthy": ["github.com/ibus/ibus", "github.com/ibus/ibus-anthy"],
    "github.com/octoprint/octoprint": ["github.com/OctoPrint/OctoPrint"],
    "github.com/astropy/astropy": ["github.com/astropy/astropy"],
    "github.com/pikepdf/pikepdf": ["github.com/pikepdf/pikepdf"],
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(repo):
    text = repo.strip().lower().removesuffix(".git")
    return text.replace("https://", "").replace("http://", "")


def owner_name(repo):
    parts = normalize(repo).split("/")
    if len(parts) < 3 or parts[0] != "github.com":
        return None
    return parts[1], parts[2]


def query(repo):
    parsed = owner_name(repo)
    record = {
        "requested": normalize(repo),
        "owner": None,
        "name": None,
        "ok": False,
        "http_status": None,
        "full_name": None,
        "fork": None,
        "parent": None,
        "source": None,
        "canonical_source": None,
        "error": None,
    }
    if parsed is None:
        record["error"] = "not_github_owner_name"
        return record
    owner, name = parsed
    record["owner"], record["name"] = owner, name
    process = subprocess.run(
        ["gh", "api", f"repos/{owner}/{name}", "--jq",
         "{full_name:.full_name,fork:.fork,parent:(.parent.full_name),source:(.source.full_name)}"],
        capture_output=True, text=True, timeout=60,
    )
    record["http_status"] = process.returncode
    if process.returncode != 0:
        err = (process.stderr or process.stdout or "").strip()
        record["error"] = err[-500:]
        if "404" in err or "Not Found" in err:
            record["http_status"] = 404
        return record
    try:
        blob = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        record["error"] = str(exc)
        return record
    full = (blob.get("full_name") or f"{owner}/{name}").lower()
    parent = (blob.get("parent") or "").lower() or None
    source = (blob.get("source") or "").lower() or None
    record.update({
        "ok": True,
        "full_name": "github.com/" + full,
        "fork": bool(blob.get("fork")),
        "parent": ("github.com/" + parent) if parent else None,
        "source": ("github.com/" + source) if source else None,
        "canonical_source": "github.com/" + (source or full),
    })
    return record


def main():
    old = json.loads(OLD.read_text())
    legal = json.loads((HERE / "legal_cve_proposal_v2/legal_candidates.json").read_text())
    cve = json.loads((HERE / "legal_cve_proposal_v2/cve_candidates.json").read_text())
    skill = json.loads((HERE / "skill_candidates_v1/source_manifest.json").read_text())
    historical = sorted({normalize(row["ancestry_key"][1]) for row in old["source_records"] if row["ancestry_key"][0] == "repository"})
    selected = []
    for family in legal["families"]:
        if family["ancestry_key"][0] == "repository":
            selected.append(("legal", family["lineage_family_id"], normalize(family["ancestry_key"][1])))
    for family in cve["families"]:
        selected.append(("cve", family["lineage_family_id"], normalize(family["source"]["repository"])))
    for family in skill["families"]:
        selected.append(("skill", "family:" + hashlib.sha256(json.dumps(["repository", family["repository"]], separators=(",", ":")).encode()).hexdigest(), normalize(family["repository"])))
    selected_repos = sorted({item[2] for item in selected})
    needed = sorted(set(historical) | set(selected_repos) | {normalize(name) for aliases in KNOWN_UPSTREAM.values() for name in aliases} | set(KNOWN_UPSTREAM))
    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(query, repo): repo for repo in needed}
        for future in as_completed(futures):
            record = future.result()
            results[record["requested"]] = record
    historical_canon = {results[repo]["canonical_source"] for repo in historical if results[repo].get("ok") and results[repo].get("canonical_source")}
    historical_names = {results[repo]["full_name"] for repo in historical if results[repo].get("ok") and results[repo].get("full_name")} | set(historical)
    overlaps = []
    for population, fid, repo in selected:
        row = results[repo]
        canon = row.get("canonical_source")
        hits = []
        if canon and canon in historical_canon:
            hits.append({"kind": "shared_canonical_source", "identity": canon})
        if row.get("full_name") in historical_names:
            hits.append({"kind": "exact_full_name", "identity": row.get("full_name")})
        if row.get("parent") in historical_names:
            hits.append({"kind": "parent_in_historical", "identity": row.get("parent")})
        if row.get("source") in historical_names:
            hits.append({"kind": "source_in_historical", "identity": row.get("source")})
        if hits:
            overlaps.append({"population": population, "lineage_family_id": fid, "selected": repo, "hits": hits})
    declared = []
    for repo, aliases in KNOWN_UPSTREAM.items():
        if normalize(repo) not in selected_repos:
            continue
        row = results[normalize(repo)]
        alias_rows = [results[normalize(name)] for name in aliases if normalize(name) in results]
        declared.append({
            "selected": normalize(repo),
            "selected_query": {k: row.get(k) for k in ("ok", "full_name", "fork", "parent", "source", "canonical_source", "http_status", "error")},
            "declared_aliases_or_upstreams": [normalize(name) for name in aliases],
            "alias_queries": [{k: item.get(k) for k in ("requested", "ok", "full_name", "fork", "parent", "source", "canonical_source", "http_status")} for item in alias_rows],
            "historical_hit": [normalize(name) for name in aliases if normalize(name) in historical_names or (results.get(normalize(name), {}).get("canonical_source") in historical_canon)],
        })
    selected_failed = [results[repo] for repo in selected_repos if not results[repo].get("ok")]
    historical_failed = [results[repo] for repo in historical if not results[repo].get("ok")]
    alias_absent = [row for row in results.values() if row.get("http_status") == 404 and row["requested"] not in selected_repos and row["requested"] not in historical]
    failed = selected_failed + historical_failed
    if overlaps:
        status = "FORK_GRAPH_CLOSED_WITH_HISTORICAL_HIT"
    elif failed:
        status = "FORK_GRAPH_INCOMPLETE"
    else:
        status = "FORK_GRAPH_CLOSED_NO_HISTORICAL_HIT"
    report = {
        "schema": "la-lineage-fork-graph/v1",
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "historical_manifest_sha256": sha(OLD),
        "queried_repository_count": len(needed),
        "github_ok_count": sum(1 for row in results.values() if row.get("ok")),
        "github_failed_count": len(failed),
        "declared_alias_absent_404": alias_absent,
        "selected_historical_fork_or_source_hits": overlaps,
        "declared_fork_or_alias_notes": declared,
        "failed_queries": failed,
        "scientific_admitted_families": 0,
        "scientific_cells_executed": 0,
        "model_calls": 0,
        "notes": "Canonical source is GitHub .source.full_name when the repository is a fork, otherwise .full_name. A 404 on a declared alias that is neither selected nor historical is recorded as absent, not as a selected-family query failure. twangboy/salt is a fork of saltstack/salt; saltstack/salt is not in the historical LA-004/LA-029 repository set. A clear graph does not by itself scientifically admit families.",
        "queries": results,
    }
    out = HERE / "lineage_fork_graph_v1.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": status,
        "queried": len(needed),
        "ok": report["github_ok_count"],
        "failed": len(failed),
        "hits": overlaps,
        "twangboy": results.get("github.com/twangboy/salt"),
        "saltstack": results.get("github.com/saltstack/salt"),
    }, indent=2, sort_keys=True))
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
