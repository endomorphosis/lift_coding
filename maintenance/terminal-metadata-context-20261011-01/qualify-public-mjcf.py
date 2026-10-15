"""Fresh public-only MJCF context qualification, without a provider or verifier."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import tempfile

import tiktoken

from benchmarks.agent_supervisor.container_coding import terminal_indexed_preparation as prep
from benchmarks.agent_supervisor.container_coding import terminal_initial_context as initial
from ipfs_accelerate_py.agent_supervisor.runtime import semantic_metadata_view as metadata
from ipfs_accelerate_py.agent_supervisor.runtime import semantic_router_translation as transport
from test.api.test_indexed_semantic_metadata_view import compile_metadata_case

OUT = Path(__file__).resolve().parent
PREVIOUS = OUT.with_name("terminal-indexed-context-live-20261011-02")
TASK = Path("/home/barberb/lift_coding/.benchmarks/terminal-bench-2/tune-mjcf")
ENCODING = tiktoken.get_encoding("o200k_base")


def measure(text):
    return {"utf8_bytes": len(text.encode()), "local_o200k_base_tokens": len(ENCODING.encode(text, disallowed_special=())),
        "sha256": hashlib.sha256(text.encode()).hexdigest()}


def main():
    profile_path = PREVIOUS / "profiles/tune-mjcf.json"
    profile = json.loads(profile_path.read_text())
    instruction_bytes = (TASK / "instruction.md").read_bytes()
    with tempfile.TemporaryDirectory(prefix="metadata-public-mjcf-") as temporary:
        root = Path(temporary) / "app"
        root.mkdir()
        state = root.parent / "state"
        instruction = root.parent / "instruction.md"
        instruction.write_bytes(instruction_bytes)
        hashes = {}
        for relative in profile["input_paths"]:
            assert relative in {"eval.py", "model_ref.xml"}
            raw = (TASK / "environment/src" / relative).read_bytes()
            (root / relative).write_bytes(raw)
            hashes[relative] = hashlib.sha256(raw).hexdigest()
        for args in (("init", "-q"), ("add", "--all"), ("-c", "user.name=Public qualification", "-c",
            "user.email=qualification@example.invalid", "commit", "-qm", "public input baseline")):
            subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
        prepared = prep.prepare(repository=root, instruction=instruction, state=state,
            task_profile=profile, disable_intent_autoencoder=True, semantic_context_profile="indexed-default@1")
        receipt = prep.initial_context(state=state)
        loaded = initial.load_initial_context(state=state, prepared=prepared, require_empty_owner=True)
        descriptor = loaded["descriptor"]
        artifact = root / descriptor["metadata"]["Semantic context artifact"]
        retrieval = descriptor["metadata"]["Code retrieval artifact"]
        extra = [("code-retrieval-context", retrieval, (root / retrieval).read_text()),
                 ("intent-world-context", descriptor["world"]["artifact"],
                  json.dumps(loaded["capture"]["planning_context"], sort_keys=True, separators=(",", ":")))]
        case = compile_metadata_case(root, artifact, instruction_bytes.decode(), extra)
        semantic, view, encoded = case["semantic"], case["view"], case["encoded"]
        assert semantic["schema"] == "supervisor-semantic-worker-context@2"
        assert len(semantic["capsules"]) == 3
        assert receipt["worker_payload_bytes"] <= 32768
        assert semantic["raw_sources"][prep.INSTRUCTION].encode() == instruction_bytes
        original_artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
        restored = metadata.restore_semantic_metadata_view(provider_prompt=view.provider_prompt, receipt=view.receipt)
        original = json.loads(encoded.provider_prompt)
        factored = json.loads(view.provider_prompt)
        preserved = {
            "semantic_transport_exact_roundtrip": restored == encoded.provider_prompt,
            "native_compiled_prompt_exact_roundtrip": transport.restore_semantic_router_prompt(
                provider_prompt=restored, table=encoded.table, repository=root) == case["prompt"],
            "selected_capsule_population": len(factored["translated_semantic"]["capsules"]) == 3,
            "worker_projection_exact": factored["translated_semantic"]["worker_projection"] == semantic["worker_projection"],
            "literal_public_instruction_exact": factored["translated_semantic"]["raw_sources"][prep.INSTRUCTION].encode() == instruction_bytes,
            "literal_suffix_exact": factored["native_suffix"] == case["suffix"],
            "retrieval_and_empty_world_exact": factored["native_context"] == original["native_context"],
            "artifact_unchanged": original_artifact_sha == hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "public_sources_unchanged": all(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items()),
        }
        assert all(preserved.values()), preserved
        selection = metadata.select_semantic_metadata_view(view=view, native_complete_prompt=case["baseline"],
            candidate_complete_prompt=case["candidate"])
        baseline, candidate = measure(case["baseline"]), measure(case["candidate"])
        assert selection.selected_mode == "common-bindings@1"
        assert candidate["local_o200k_base_tokens"] < baseline["local_o200k_base_tokens"]
        record = {"schema": "public-terminal-metadata-qualification@1", "task": "tune-mjcf",
            "context_profile": "indexed-default@1", "metadata_profile": "common-bindings@1",
            "fresh_offline_reconstruction": True, "historical_live_prompt_reconstructed": False,
            "provider_calls": 0, "verifier_or_solutions_read": False, "task_executed": False,
            "actual_selected_capsules": 3, "full_capsule_count": receipt["full_capsules"],
            "selected_symbols": semantic["worker_projection"]["selected_symbols"],
            "worker_payload_bytes": receipt["worker_payload_bytes"], "source_sha256": hashes,
            "public_profile_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
            "public_instruction_sha256": hashlib.sha256(instruction_bytes).hexdigest(),
            "preservation_checks": preserved, "selected_mode": selection.selected_mode,
            "baseline_complete_input": baseline, "candidate_complete_input": candidate,
            "bytes_saved": baseline["utf8_bytes"] - candidate["utf8_bytes"],
            "local_tokens_saved": baseline["local_o200k_base_tokens"] - candidate["local_o200k_base_tokens"],
            "local_token_reduction_percent": 100 * (baseline["local_o200k_base_tokens"] - candidate["local_o200k_base_tokens"]) / baseline["local_o200k_base_tokens"],
            "tokenizer": {"library": "tiktoken", "version": importlib.metadata.version("tiktoken"), "encoding": ENCODING.name,
                "provider_tokenizer_verified": False},
            "shared_fields": view.receipt["shared_field_paths"], "provider_token_savings_claimed": False,
            "limitations": [
                "Fresh current producer output for public input bytes; prior live prompt artifacts were not retained after container cleanup.",
                "The real pre-admission empty owner world is included; this is not the live admitted-task world or planner output.",
                "The actual ContextCompiler and workspace wrapper are used. Literal instruction is preserved as an explicit native suffix; no signed public-instruction receipt or Doctor residual is fabricated.",
                "Legacy coding reply mode matches prior live trials. Provider CLI system context and subsequent tool turns are not measured.",
                "Local o200k_base token counts are neither provider-native cumulative usage nor measured task quality."]}
        source_root = Path(transport.__file__).resolve().parents[3]
        record["source_head"] = subprocess.check_output(["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True).strip()
        record["source_sha256_for_qualification"] = {
            name: hashlib.sha256((source_root / name).read_bytes()).hexdigest() for name in (
                "test/api/test_indexed_semantic_metadata_view.py",
                "ipfs_accelerate_py/agent_supervisor/runtime/semantic_metadata_view.py",
                "ipfs_accelerate_py/agent_supervisor/runtime/semantic_router_translation.py",
                "benchmarks/agent_supervisor/container_coding/terminal_initial_context.py",
                "benchmarks/agent_supervisor/container_coding/terminal_indexed_preparation.py")}
        record["tokenizer"]["exact_encoding_fingerprint_reference"] = "qualification.json#/tokenizer"
        output = OUT / "public-mjcf-qualification.json"
        output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"output": str(output), "capsules": 3, "selected_mode": selection.selected_mode,
            "bytes_saved": record["bytes_saved"], "local_tokens_saved": record["local_tokens_saved"],
            "local_token_reduction_percent": record["local_token_reduction_percent"]}, sort_keys=True))


if __name__ == "__main__":
    main()
