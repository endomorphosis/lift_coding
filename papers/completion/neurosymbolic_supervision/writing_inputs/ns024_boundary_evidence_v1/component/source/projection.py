"""Exact public scalar projection rule; needs original metadata supplied separately."""
STRINGS = {'schema', 'task_id', 'case_id', 'record_id', 'extension_id', 'step', 'step_index', 'family', 'family_id', 'kind', 'polarity', 'status', 'qualification_status', 'result_class', 'observed_reason', 'expected_reason', 'reason', 'reuse_action', 'reuse_reason', 'expected_reuse_action', 'expected_reuse_reason', 'scoring_class', 'profile', 'oracle_status', 'cold_outcome', 'disposition', 'mutation_kind', 'translation_progress', 'result_status', 'observed_action', 'expected_action', 'consumption_mode', 'observation_kind', 'decision', 'pre_fix_commit', 'upstream_revision', 'source_sha256', 'policy_id', 'node_id', 'pair_id'}
EXCLUDE = {'argv', 'command', 'commands', 'stdout', 'stderr', 'stdout_tail', 'stderr_tail', 'traceback', 'message', 'error', 'cwd', 'path', 'paths', 'source', 'script', 'code', 'proof_payload', 'statement_and_public_inputs', 'patch_text', 'description', 'context', 'output', 'text', 'candidate', 'request', 'prompt', 'capability', 'observation_profile', 'native_probe', 'current_source_inventory'}

def project(x):
    if isinstance(x, dict):
        out = {}
        for key, value in x.items():
            if key in EXCLUDE:
                continue
            if value is None or type(value) in (bool, int, float):
                out[key] = value
            elif isinstance(value, str) and (key in STRINGS or key.endswith(('_cid', '_sha256'))):
                if '/home/' in value or 'overleaf.com/' in value:
                    raise ValueError('Unexpected private value in selected scalar')
                out[key] = value
            elif isinstance(value, (dict, list)):
                v = project(value)
                if v not in ({}, []):
                    out[key] = v
        return out
    if isinstance(x, list):
        return [v for value in x if isinstance(value, (dict, list, bool, int, float)) or value is None for v in [project(value)] if v not in ({}, [])]
    return x
