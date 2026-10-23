"""Local, provider-free metadata view qualification on real producer fixtures."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import tempfile

import tiktoken

from test.api.test_semantic_metadata_view import native_factory
from ipfs_accelerate_py.agent_supervisor.runtime import semantic_metadata_view as codec
from ipfs_accelerate_py.agent_supervisor.runtime import semantic_router_translation as native
from ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner import render_model_prompt
from ipfs_accelerate_py.agent_supervisor.runtime.coding_reply_contract import apply_coding_reply_contract


OUT = Path(__file__).resolve().parent
SOURCE = Path(native.__file__).resolve().parents[3]
ENC = tiktoken.get_encoding("o200k_base")


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def measured(text):
    return {"utf8_bytes": len(text.encode()), "local_o200k_base_tokens": len(ENC.encode(text, disallowed_special=())),
            "sha256": sha(text)}


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="metadata-public-fixture-") as directory:
        build = native_factory.__wrapped__(Path(directory))
        for functions in (0, 1, 6):
            repository, encoded, source = build(functions)
            view = codec.project_semantic_metadata_view(encoded.provider_prompt)
            wire = json.loads(encoded.provider_prompt)
            capsule_count = len(wire["translated_semantic"]["capsules"])
            complete, advisory = render_model_prompt(prompt=encoded.provider_prompt, purpose="coding",
                                                    workspace=repository.parent / "allocated-worktree",
                                                    semantic_transport=True)
            candidate, candidate_advisory = render_model_prompt(prompt=view.provider_prompt, purpose="coding",
                                                    workspace=repository.parent / "allocated-worktree",
                                                    semantic_transport=True)
            for reply_mode in ("legacy", "ordinary-completion@1"):
                before, before_reply = apply_coding_reply_contract(model_prompt=complete, mode=reply_mode,
                                                    purpose="coding", provider="codex_cli")
                after, after_reply = apply_coding_reply_contract(model_prompt=candidate, mode=reply_mode,
                                                    purpose="coding", provider="codex_cli")
                selection = codec.select_semantic_metadata_view(view=view, native_complete_prompt=before,
                                                               candidate_complete_prompt=after)
                restored = codec.restore_semantic_metadata_view(provider_prompt=view.provider_prompt,
                                                                 receipt=view.receipt)
                native_restored = native.restore_semantic_router_prompt(provider_prompt=restored,
                                                    table=encoded.table, repository=repository)
                candidate_wire = json.loads(view.provider_prompt)
                preserved = {
                    "semantic_transport_exact_roundtrip": restored == encoded.provider_prompt,
                    "original_compiled_prompt_exact_roundtrip": native_restored == encoded.native_prompt,
                    "all_native_context_unchanged": candidate_wire["native_context"] == wire["native_context"],
                    "literal_suffix_unchanged": candidate_wire["native_suffix"] == wire["native_suffix"],
                    "raw_source_unchanged": candidate_wire["translated_semantic"]["raw_sources"]["module.py"] == source,
                    "workspace_advisory_unchanged": advisory == candidate_advisory,
                    "reply_instruction_unchanged": (before_reply or {}).get("instruction_sha256") == (after_reply or {}).get("instruction_sha256"),
                    "capsule_population_unchanged": len(candidate_wire["translated_semantic"]["capsules"]) == capsule_count,
                    "execution_authority_false": candidate_wire["execution_authority"] is False,
                    "completion_authority_false": candidate_wire["completion_authority"] is False,
                }
                assert all(preserved.values()), preserved
                baseline = measured(before)
                projected = measured(after)
                chosen = measured(selection.selected_prompt)
                rows.append({"authored_functions": functions, "capsules": capsule_count,
                    "reply_mode": reply_mode, "baseline": baseline, "candidate": projected, "selected": chosen,
                    "selected_mode": selection.selected_mode, "fallback_reason": selection.receipt["fallback_reason"],
                    "preservation_checks": preserved, "shared_fields": view.receipt["shared_field_paths"],
                    "selected_bytes_reduction_percent": 100 * (baseline["utf8_bytes"]-chosen["utf8_bytes"]) / baseline["utf8_bytes"],
                    "selected_local_tokens_reduction_percent": 100 * (baseline["local_o200k_base_tokens"]-chosen["local_o200k_base_tokens"]) / baseline["local_o200k_base_tokens"]})
    ranks = hashlib.sha256()
    for token, rank in sorted(ENC._mergeable_ranks.items(), key=lambda row: row[1]):
        ranks.update(len(token).to_bytes(8, "big")); ranks.update(token); ranks.update(rank.to_bytes(8, "big"))
    report = {"schema": "local-semantic-metadata-view-qualification@1",
        "source_commit": subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip(),
        "profile": "common-bindings@1", "provider_calls": 0, "model_calls": 0,
        "historical_live_prompt_reconstructed": False,
        "historical_unavailable_reason": "Previous trials retained input hashes and audits, but not native context artifacts after container cleanup.",
        "fixture": "Existing authored real-producer test_semantic_metadata_view.native_factory; not the Terminal Bench task.",
        "measurement_scope": "Complete router model prompt including actual workspace advisory and selected coding reply instruction. No CLI system prompt or provider-native token usage.",
        "tokenizer": {"library": "tiktoken", "version": importlib.metadata.version("tiktoken"),
            "encoding": ENC.name, "mergeable_ranks_sha256": ranks.hexdigest(),
            "special_tokens_sha256": sha(json.dumps(ENC._special_tokens, sort_keys=True, separators=(",", ":"))),
            "vocabulary_entries": len(ENC._mergeable_ranks), "regex_sha256": sha(ENC._pat_str),
            "provider_tokenizer_verified": False},
        "cases": rows, "provider_token_savings_claimed": False, "task_quality_measured": False,
        "limitations": ["Public authored fixture only; source content and repeated metadata distribution differ from the prior live task.",
            "Local o200k_base counts are not the configured provider tokenizer or billing counts.",
            "No task-specific Doctor residual or public-instruction inclusion blocks are fabricated; codec preserves arbitrary complete-input suffixes exactly.",
            "Legacy reply mode matches previous live trial setting; ordinary-completion@1 is a separate representation regression."]}
    (OUT / "qualification.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(OUT / "qualification.json"), "cases": [{k: row[k] for k in (
        "capsules", "reply_mode", "selected_mode", "selected_bytes_reduction_percent", "selected_local_tokens_reduction_percent")}
        for row in rows]}, sort_keys=True))


if __name__ == "__main__":
    main()
