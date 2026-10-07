"""Prepare new, exact publication paths; leave existing owners and indexes intact."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

R = Path(__file__).resolve().parent
W = R.parents[1]
P = W / "external/ipfs_datasets"
GUIDE = "docs/autoencoders/balanced_wording_continuation_20261007.md"
EVIDENCE = "docs/autoencoders/evidence/balanced-wording-20261007"
REPLAY = "scripts/ops/autoencoder/dual_bank_wording_replay"
REVIEWS = [
    "pipeline/publisher-independent-review.json",
    "pipeline/replay-helper-independent-review.json",
    "documentation-review/evidence-documentation-and-retention-source-review.json",
    "archive-review/actual-archive-independent-review.json",
]
COMPACT = {
    "comparison-protocol.json": "predeclared-comparison-protocol.json",
    "candidate-review.json": "review/candidate-pair-independent-review-draft-r3.json",
    "native-preparation-review.json": "preparation-review/actual-preparation-r2-audit.json",
    "preflight-compact.json": "preflight-review/actual-preflight-384-r2-compact.json",
    "training-compact.json": "training-review/actual-training-384-r2-compact.json",
    "evaluation-compact.json": "evaluation-review/actual-evaluation-r1-compact.json",
    "parent-comparison.json": "evaluation-review/actual-evaluation-r1-parent-comparison.json",
    "reconstruction-decision.json": "documentation/reconstruction-decision.json",
    "sampled-outputs.json": "documentation/sampled-outputs.json",
    "replay-contract.json": "next-retention-plan/implementation-contract.json",
    "replay-coverage.json": "next-retention-plan/schedule-census-proof.json",
}


def git(repo, *args):
    return subprocess.check_output(["git", "-c", "gc.auto=0", "-C", str(repo), *args])


def record(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1_048_576), b""):
            digest.update(block)
            size += len(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def copy_new(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(source.read_bytes())


def main():
    if (R / "publication-scope.json").exists():
        raise ValueError("selected scope is immutable")
    history = R / "historical-source-retention"
    if history.exists():
        REVIEWS.append("historical-source-retention/independent-review.json")
    for relative in REVIEWS:
        value = json.loads((R / relative).read_bytes())
        if value.get("passed") is not True or value.get("findings"):
            raise ValueError("clean independent review required: " + relative)
    archive = json.loads((R / "retention-manifest.json").read_bytes())
    if record(W / archive["archive"]["path"]) != {
        key: archive["archive"][key] for key in ("bytes", "sha256")
    }:
        raise ValueError("completed evidence archive changed")
    text = (R / "RESULTS.md").read_text().replace(
        "documentation/sampled-outputs.json", EVIDENCE.split("docs/autoencoders/", 1)[1] + "/sampled-outputs.json"
    )
    text += (
        "\n## Reproduction and retained source material\n\n"
        "The [evidence index](evidence/balanced-wording-20261007/evidence-index.json) binds "
        "the compact reports to the [immutable experiment archive](https://github.com/endomorphosis/lift_coding/blob/main/"
        + archive["archive"]["path"] + "). It preserves all generated formulas, readout traces, "
        "failed attempts and producer sources. Raw checkpoints and prepared embedding inventories "
        "remain in the owned local attempts; reconstructed vectors and normalized feature observations "
        "are retained as numerical outputs.\n\n"
        "The standalone [replay preparation helper](../../scripts/ops/autoencoder/dual_bank_wording_replay/dual_bank_retention.py) "
        "exports `build_schedule`, `validate_schedule` and `retention_gate`. Its sibling tests cover "
        "budget conservation, full coverage, malformed receipts and complete formula retention. "
        "It neither invokes nor modifies a trainer. The proposed fit still needs a reviewed dual-cache "
        "adapter and truthful per-bank training receipts.\n\n"
        "The [main/worktree reconciliation](https://github.com/endomorphosis/lift_coding/blob/main/"
        "artifacts/autoencoder-balanced-wording-20261007/publication/final-main-worktree-reconciliation.md) "
        "also records older local-only tips and remaining provenance review. Their experimental cards "
        "and source material remain separate from live model owners; archived findings are not a runtime port "
        "or checkpoint promotion. Existing upstream cached-inference and source-span-decoder contributions "
        "are preserved by building this commit on current main.\n"
    )
    final_guide = R / "documentation/final-publication-guide.md"
    with final_guide.open("x") as stream:
        stream.write(text)
    copy_new(final_guide, P / GUIDE)
    package_paths = [GUIDE]
    for name, source in COMPACT.items():
        target = EVIDENCE + "/" + name
        copy_new(R / source, P / target)
        package_paths.append(target)
    for name in ("dual_bank_retention.py", "test_dual_bank_retention.py"):
        target = REPLAY + "/" + name
        if record(P / target) != record(R / "next-retention-plan" / name):
            raise ValueError("pure helper publication copy changed")
        package_paths.append(target)
    index = {
        "schema": "balanced-wording-completed-evidence-index/v1", "passed": True, "findings": [],
        "experiment_archive": archive["archive"], "archive_members": len(archive["entries"]),
        "archive_source_bytes": archive["source_bytes"],
        "historical_source_retention_files": {
            str(path.relative_to(W)): record(path) for path in sorted(history.iterdir())
            if path.is_file() and path.suffix in (".py", ".json", ".gz", ".md")
        } if history.exists() else {},
        "compact_files": {name: record(P / name) for name in package_paths},
        "independent_reviews": {str((R / relative).relative_to(W)): record(R / relative) for relative in REVIEWS},
        "numerical_outcome": {"parent_exposed_v3": 31, "control_exposed_v3": 33,
            "balanced_exposed_v3": 19, "balanced_retained_normative": 33, "cohort_denominator": 48,
            "balanced_replacement_rejected": True},
        "physical_evaluation_panels": 16, "physical_paragraph_outputs": 768,
        "reference_rules": 2880, "scalar_reference_sites": 11520,
        "replay_helper_wired_into_trainer": False, "replay_fit_executed": False,
        "source_semantics_verified": False, "fresh_holdout": False, "qualified": False,
        "admitted": False, "lake_executed": False, "formalized": False,
        "Constitution_formalized": False, "checkpoint_promoted": False,
        "convergence_proven": False, "huggingface_upload_performed": False,
    }
    save(P / EVIDENCE / "evidence-index.json", index)
    package_paths.append(EVIDENCE + "/evidence-index.json")
    workspace_paths = [
        "README.md", "RESULTS.md", "initial-state.json", "predeclared-comparison-protocol.json",
        "retain_evidence.py", "retention-manifest.json", "balanced-wording-evidence.tar.gz",
        "prepare_publication.py", "publish_integration.py", "publisher_review_tests.py",
        "documentation/final-publication-guide.md", "documentation/reconstruction-decision.json",
        "documentation/sampled-outputs.json", *REVIEWS,
        "pipeline/publisher-adaptation.json", "pipeline/publisher-adaptation.diff.gz",
        "pipeline/publisher-synthetic-validation.json", "pipeline/replay-publication-copy.json",
        "pipeline/replay-helper-independent-pure-validation.json",
        "pipeline/advertised-ref-coverage-supplement.json",
        "archive-review/audit_archive-r2.py", "archive-review/test_audit_archive-r2.py",
        "archive-review/auditor-source-results-freeze-r2.json",
        "publication/final-main-worktree-reconciliation.json",
        "publication/final-main-worktree-reconciliation.md",
        "publication/reconciliation-source-results-freeze.json",
        "publication/published-owner-bindings.json",
        "publication/historical-autoencoder-intake.json",
        "publication/historical-divergent-delta-audit.json.gz",
        "publication/historical-tip-origin-reachability.json",
    ]
    workspace_paths += [str(path.relative_to(R)) for path in sorted((R / "next-retention-plan").iterdir())
        if path.is_file() and path.suffix in (".py", ".json", ".md")]
    # Additional historical-source retention is separate from the already-sealed
    # numerical archive and is evidence only, with its own review/manifest.
    if history.exists():
        historical_review = history / "independent-review.json"
        review = json.loads(historical_review.read_bytes())
        if review.get("passed") is not True or review.get("findings"):
            raise ValueError("clean historical retention review required")
        workspace_paths += [str(path.relative_to(R)) for path in sorted(history.iterdir())
            if path.is_file() and path.suffix in (".py", ".json", ".gz", ".md")]
    workspace_paths = list(dict.fromkeys(workspace_paths))
    scope = {"schema": "balanced-wording-exact-main-publication-scope/v1", "passed": True,
        "reviewed": True, "required_reviews": ["pipeline/publication-scope-independent-review.json", *REVIEWS]}
    for label, repo, paths in (("datasets", P, package_paths),
        ("workspace", W, [str((R / name).relative_to(W)) for name in workspace_paths])):
        git(repo, "fetch", "--no-tags", "origin", "main")
        parent = git(repo, "rev-parse", "origin/main").decode().strip()
        files = {}
        for relative in paths:
            if git(repo, "--literal-pathspecs", "ls-tree", "-z", parent, "--", relative):
                raise ValueError("new scoped path already exists on main: " + relative)
            files[relative] = {**record(repo / relative), "parent_sha256": None, "mode": "100644"}
        scope[label] = {"parent": parent, "files": files}
    save(R / "publication-scope.json", scope)
    print(json.dumps({"package_files": len(package_paths), "workspace_files": len(workspace_paths)}))


if __name__ == "__main__":
    main()
