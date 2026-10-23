"""Reconstruct captured input digests from retained public sources; no provider."""
import hashlib
import json
from pathlib import Path
from benchmarks.agent_supervisor.container_coding.terminal_source_input_experiment import _native_prompt
from ipfs_accelerate_py.agent_supervisor.runtime.semantic_router_translation import replay_semantic_router_prompt_for_audit
from ipfs_accelerate_py.agent_supervisor.runtime.source_input_view import replay_source_input_view_for_audit
from ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner import render_model_prompt

campaign = Path(__file__).resolve().parent
comparison = campaign / 'public-input-comparison-final'
report = json.loads((comparison / 'qualification.json').read_text())
results = []
for task in report['tasks']:
    root = comparison / task['task_name'] / 'repository'
    artifact = root / '.runtime/semantic/worker-context.json'
    payload = json.loads(artifact.read_text())
    workspace = root.parent / 'allocated-worktree'
    if workspace.exists():
        raise ValueError('historical replay requires the worktree to remain absent')
    prompt = _native_prompt(root, artifact, 'SOURCE-INPUT-QUALIFICATION', sorted(payload['manifest']))
    encoded = replay_semantic_router_prompt_for_audit(prompt=prompt, repository=root)
    for arm in task['arms']:
        if arm['disposition'] != 'captured':
            continue
        router = encoded.provider_prompt
        binding = arm.get('source_input_receipt')
        if binding is not None:
            router = replay_source_input_view_for_audit(encoded=encoded, repository=root, receipt=binding).provider_prompt
        model, _ = render_model_prompt(prompt=router, purpose='coding', workspace=workspace, semantic_transport=True)
        matched = (hashlib.sha256(model.encode()).hexdigest() == arm['full_input_sha256']
                   and len(model.encode()) == arm['full_input_bytes'])
        if not matched:
            raise ValueError('retained public input reconstruction differs')
        results.append({'task_name':task['task_name'], 'policy':arm['policy'], 'full_input_sha256_matches':True,
                        'full_input_bytes_match':True, 'allocated_worktree_absent':True})
result = {'schema':'terminal-source-input-independent-replay@1', 'all_captured_inputs_replayed':len(results)==report['local_capture_calls'],
          'provider_calls':0, 'containers_started':0, 'model_prompt_content_exported':False, 'results':results}
with (campaign / 'independent-public-replay.json').open('x') as stream:
    json.dump(result, stream, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps({'replayed_inputs':len(results),'all_matched':result['all_captured_inputs_replayed'],'provider_calls':0}))
