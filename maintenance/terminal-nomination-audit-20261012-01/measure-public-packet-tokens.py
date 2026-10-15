"""Offline local tokenizer counts of explicitly exported public prompt fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

parser = argparse.ArgumentParser()
parser.add_argument("--fixtures", type=Path, required=True)
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists()
asset = args.cache / "fb374d419588a4632f3f557e76b4b70aebbca790"
raw = asset.read_bytes()
assert len(raw) == 3613922 and sha(raw) == "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
os.environ["TIKTOKEN_CACHE_DIR"] = str(args.cache)
def refuse_network(*unused_args, **unused_kwargs):
    raise AssertionError("offline tokenizer qualification cannot connect")
socket.socket.connect = socket.socket.connect_ex = refuse_network
import tiktoken
assert tiktoken.__version__ == "0.13.0"
encoding = tiktoken.get_encoding("o200k_base")
header = "\nReviewed source nominations (descriptive only; behavioral requirements remain pending):\n"
rows = {}
for mode in ("expanded", "compact_v2", "legacy_v1", "identifiers"):
    body = (args.fixtures / (mode + "-model-input.txt")).read_bytes()
    receipt = json.loads((args.fixtures / (mode + "-receipt.json")).read_bytes())
    assert sha(body) == receipt["model_prompt_sha256"] and len(body) == receipt["model_prompt_bytes"]
    text = body.decode("utf-8")
    start = text.index(header)
    json_start = start + len(header)
    catalog, length = json.JSONDecoder().raw_decode(text[json_start:])
    end = json_start + length + 1
    assert text[end - 1] == "\n"
    block = text[start:end]
    assert sha(block.encode()) == receipt["reviewed_source_nomination_context"]["block_sha256"]
    assert len(block.encode()) == receipt["reviewed_source_nomination_context"]["block_bytes"]
    count = lambda value: len(encoding.encode(value, disallowed_special=()))
    total = count(text)
    without = count(text[:start] + text[end:])
    rows[mode] = {"model_input_sha256": sha(body), "model_input_bytes": len(body),
        "complete_model_input_tokens": total, "catalog_bytes": len(block.encode()),
        "isolated_catalog_tokens": count(block), "catalog_increment_at_actual_packet_boundary": total - without,
        "catalog_removed_packet_is_an_analytic_counterfactual_not_an_admitted_run": True}
baseline = rows["expanded"]
for row in rows.values():
    row["complete_packet_tokens_saved_vs_same_fixture_expanded"] = baseline["complete_model_input_tokens"] - row["complete_model_input_tokens"]
    row["complete_packet_token_reduction_fraction"] = row["complete_packet_tokens_saved_vs_same_fixture_expanded"] / baseline["complete_model_input_tokens"]
result = {"schema": "local-public-complete-packet-token-measurement@1", "qualified": True,
    "tokenizer": "o200k_base", "tiktoken_version": tiktoken.__version__,
    "asset_sha256": sha(raw), "asset_bytes": len(raw), "fixtures": str(args.fixtures.absolute()),
    "scope": "Complete router task model input, including workspace, reviewed catalog and literal instruction appendages; provider harness/system context is outside these fixture bytes.",
    "modes": rows, "provider_calls": 0, "network_calls": 0,
    "provider_usage_or_session_token_savings_established": False,
    "paired_live_sessions_or_repair_loops_measured": False, "budget_ledger_modified": False,
    "source_equivalence_full_task_satisfaction_or_convergence_proved": False}
args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
print(json.dumps({mode: row["complete_model_input_tokens"] for mode, row in rows.items()}))
