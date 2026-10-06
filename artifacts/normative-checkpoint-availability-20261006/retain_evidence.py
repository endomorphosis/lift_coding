"""Retain an explicit metadata-only availability evidence allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import re


FILES = (
    "completion.json",
    "verify_hf_cli_roundtrip.py",
    "retain_evidence.py",
    "authentication/authenticated-states.json",
    "authentication/authentication-summary.json",
    "authentication/public-copy-list.json",
    "authentication/preprocessing-384-metadata.json",
    "authentication/preprocessing-768-metadata.json",
    "authentication/authenticate_saved_states.py",
    "presence/query.py",
    "presence/freshness-receipt.json",
    "contracts/findings.json",
    "contracts/native-api-recipe.json",
    "contracts/inspect_native_contracts.py",
    "publication/publish_candidates.py",
    "publication/preparation.json",
    "publication/publication-review.json",
    "publication/publication-summary.json",
    "publication/Publicus--legal-ir-autoencoder-native-publication-receipt.json",
    "publication/Publicus--legal-ir-autoencoder-384d-native-publication-receipt.json",
    "publication/Publicus--legal-ir-autoencoder-768d-native-publication-receipt.json",
    "registration/build_plan.py",
    "registration/builder-review.json",
    "registration/builder-review-v2.json",
    "registration/register_normative_states.py",
    "registration/custody.py",
    "registration/test_registration_boundary.py",
    "registration/boundary-tests.xml",
    "registration/root-review-controls.xml",
    "registration/driver-readiness.json",
    "registration/driver-review.json",
    "registration/author-preflight-01/preflight.json",
    "registration/preparation-r1/model-manager-import-plan.json",
    "registration/preparation-r1/preparation.json",
    "registration/import-r1/preflight.json",
    "registration/import-r1/before-schema.json",
    "registration/import-r1/missing-only-import-plan.json",
    "registration/import-r1/registration-result.json",
    "registration/idempotent-r1/preflight.json",
    "registration/idempotent-r1/before-schema.json",
    "registration/idempotent-r1/registration-result.json",
    "roundtrip/repository-1-download.json",
    "roundtrip/repository-2-download.json",
    "roundtrip/repository-3-download.json",
    "roundtrip/roundtrip-verification.json",
    "roundtrip/published-metadata-verification.json",
)
GLOBS = (
    "presence/manifests/**/*.json",
    "publication/plans/*.json",
    "publication/receipts/*.json",
    "publication/repository-metadata/**/README.md",
    "publication/repository-metadata/**/manifest.json",
)
SECRETS = re.compile(
    rb"(?:hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    rb"github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    destination = args.destination.resolve()
    relative_paths = set(FILES)
    for glob in GLOBS:
        relative_paths.update(str(p.relative_to(source)) for p in source.glob(glob))
    entries = []
    for relative in sorted(relative_paths):
        original = source / relative
        if original.is_symlink() or not original.is_file():
            raise RuntimeError(f"Missing/nonregular allowlisted input: {relative}")
        data = original.read_bytes()
        if len(data) > 1_000_000 or SECRETS.search(data):
            raise RuntimeError(f"Unexpected size or credential in allowlist: {relative}")
        target = destination / relative
        if target.exists() and target.read_bytes() != data:
            raise RuntimeError(f"Refusing to overwrite different evidence: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        entries.append({"original_path": str(original), "retained_path": relative,
                        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {
        "schema": "normative-availability-metadata-retention/v1",
        "files": entries,
        "retained_count": len(entries),
        "retained_bytes": sum(p["bytes"] for p in entries),
        "raw_weights_included": False,
        "embedding_caches_or_corpus_included": False,
        "database_or_full_model_manager_rows_included": False,
        "original_bytes_preserved": True,
        "scope": "Explicit metadata, receipts, scripts and inert control results only. "
                 "Original physical paths remain historical custody evidence; private "
                 "payload pins do not imply those payloads are retained in Git.",
    }
    (destination / "retention-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}))


if __name__ == "__main__":
    main()
