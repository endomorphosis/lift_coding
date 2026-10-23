"""Exact public task preparation regression; never reads verifier or solution files."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile

from benchmarks.agent_supervisor.container_coding import terminal_indexed_preparation as prep
from benchmarks.agent_supervisor.container_coding import terminal_initial_context as initial
from benchmarks.agent_supervisor.container_coding.terminal_semantic_context_policy import semantic_context_objective

CAMPAIGN = Path(__file__).parent
DATASET = Path('/home/barberb/lift_coding/.benchmarks/terminal-bench-2')
rows = []
for task in ('llm-inference-batching-scheduler', 'tune-mjcf'):
    profile = json.loads((CAMPAIGN / 'profiles' / (task + '.json')).read_text())
    public = DATASET / task
    prefix = public / 'environment' / 'src' if task == 'tune-mjcf' else public / 'environment'
    instruction_bytes = (public / 'instruction.md').read_bytes()
    for mode in ('indexed-default@1', 'indexed-compact@1'):
        with tempfile.TemporaryDirectory(prefix='terminal-public-budget-regression-') as tmp:
            root = Path(tmp) / 'app'
            root.mkdir()
            state = Path(tmp) / 'state'
            instruction = Path(tmp) / 'instruction.md'
            instruction.write_bytes(instruction_bytes)
            hashes = {}
            for rel in profile['input_paths']:
                raw = (prefix / rel).read_bytes()
                out = root / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(raw)
                hashes[rel] = hashlib.sha256(raw).hexdigest()
            for args in [('init', '-q'), ('add', '--all'), ('-c', 'user.name=Public regression',
                    '-c', 'user.email=regression@example.invalid', 'commit', '-qm', 'public inputs')]:
                subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
            prepared = prep.prepare(repository=root, instruction=instruction, state=state,
                task_profile=profile, disable_intent_autoencoder=True, semantic_context_profile=mode)
            result = prep.initial_context(state=state)
            loaded = initial.load_initial_context(state=state, prepared=prepared, require_empty_owner=True)
            payload = loaded['semantic']
            assert payload['raw_sources'][prep.INSTRUCTION].encode() == instruction_bytes
            assert payload['worker_projection']['query'].encode() == instruction_bytes
            assert payload['objective'] == semantic_context_objective(mode, instruction_bytes.decode())
            assert payload['pack']['pack']['objective'] == payload['objective']
            assert result['worker_payload_bytes'] <= 32768
            assert result['worker_capsules'] > 0
            for rel, expected in hashes.items():
                assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == expected
                assert payload['manifest'][rel]['sha256'] == expected
            assert all(row['path'] not in payload['raw_sources'] for row in profile['data_inputs'])
            row = dict(task=task, profile=mode, full_capsules=result['full_capsules'],
                selected_capsules=result['worker_capsules'], payload_bytes=result['worker_payload_bytes'],
                max_bytes=32768, instruction_bytes=len(instruction_bytes),
                objective_bytes=len(payload['objective'].encode()), exact_instruction_preserved=True,
                exact_query_preserved=True, source_hashes=hashes, provider_calls=result['provider_calls'])
            rows.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
eligibility = {}
for task in ('llm-inference-batching-scheduler', 'tune-mjcf'):
    pair = [row for row in rows if row['task'] == task]
    eligibility[task] = dict(actual_capsule_count_difference=pair[0]['selected_capsules'] > pair[1]['selected_capsules'],
        reason='eligible' if pair[0]['selected_capsules'] > pair[1]['selected_capsules'] else 'shared_byte_budget_clips_both_profiles_to_the_same_capsule_count')
assert eligibility['tune-mjcf']['actual_capsule_count_difference']
result = dict(schema='terminal-public-context-budget-regression@1', rows=rows, pair_eligibility=eligibility,
    provider_calls=0, verifier_or_solutions_read=False, task_execution=False)
(CAMPAIGN / 'public-budget-regression.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
