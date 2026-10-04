#!/usr/bin/env python3
"""Read private holdout programmatically and report only public-stage disclosure counts."""
import hashlib
import json
from pathlib import Path
from build_lexical_graph import PRIVATE, STAGE, save, sha


def main():
    root = STAGE / "candidate"
    files = [p for p in root.rglob("*") if p.is_file()]
    assert all(not p.is_symlink() for p in root.rglob("*"))
    assert all(not p.resolve().is_relative_to(PRIVATE.resolve()) for p in files)
    assert all(".private." not in p.name for p in files)
    raw_hash = sha(PRIVATE / "raw/patent-legal-corpus-86c77cb6.documents.jsonl")
    assert all(sha(p) != raw_hash for p in files)
    payloads = [p.read_bytes() for p in files]
    finals = [json.loads(line) for line in (PRIVATE / "final_test.private.jsonl").open()]
    final_ids = {r["record_id"].encode() for r in finals}
    final_bodies = {r["text"].encode() for r in finals}
    id_disclosures = sum(any(identity in payload for payload in payloads) for identity in final_ids)
    full_body_disclosures = sum(any(body in payload for payload in payloads if len(body) <= len(payload)) for body in final_bodies)
    assert id_disclosures == 0 and full_body_disclosures == 0
    result = {"passed": True, "candidate_file_count_checked": len(files), "private_final_identifiers_disclosed": id_disclosures, "complete_private_final_source_bodies_disclosed": full_body_disclosures, "private_source_subtree_or_symlink_present": False, "full_raw_corpus_copied": False, "source_body_or_identifier_values_printed": False, "limit": "Programmatic exact-identity/full-body stage scan only; does not exclude every overlapping phrase, public-source download, pretrained exposure, or unmeasured semantic paraphrase", "script_sha256": sha(Path(__file__))}
    save(STAGE / "final_handoff_privacy_verification.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
