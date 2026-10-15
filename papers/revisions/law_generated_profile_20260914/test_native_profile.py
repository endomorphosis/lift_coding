"""Native observation/AST refinement regressions; no effects or models."""
from copy import deepcopy
import tempfile
from pathlib import Path
import unittest
from effects import PURE, EFFECTS
from native_profile import ast_events, build_native_mappings, reconcile
from program import ProgramError
from ipfs_accelerate_py.agent_supervisor.proof.code_security_facts import ChangedCodeDiff, extract_code_security_facts
from ipfs_accelerate_py.agent_supervisor.proof.cve_security_gate import SecurityRequestContext


SOURCE = b"def run(payload):\n    n = length(payload['items'])\n    if n > 0:\n        write_json('public/out.json', {'count': n})\n    write_json('public/out.json', {'count': n}); write_json('public/out2.json', {'count': n})\n    return n\n"


def facts(source=SOURCE):
    return extract_code_security_facts(ChangedCodeDiff(tree_id='tree:test', diff_id='diff:test',
        new_path='candidate.py', before_source='', after_source=source.decode())).to_dict()


class NativeProfileTests(unittest.TestCase):
    def test_complete_mixed_assignment_conditional_repeated_mapping(self):
        import json
        context = SecurityRequestContext(security_root_artifact_id='policy:test', security_root_cid_v1='policy:test',
            security_root_supervisor_digest='a' * 64, principal='did:client:tenant-a', tool='tool:closed-python',
            current_state={'fixture': 'fresh'}, state_version=0, requested_authority='mutation', evaluated_at_ms=1)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_native_mappings(SOURCE, PURE | EFFECTS, context, root)
            generic = json.loads((root / 'generic_native_mapping.json').read_text())
            self.assertTrue(any(row['status'] != 'exact' for row in generic['mappings']))
            self.assertFalse(result['generic_native_mapper_claimed_complete'])
            self.assertEqual(result['findings'], [])
            self.assertEqual(len(result['ast_events']), 6)
            self.assertEqual(len(result['source_profile']['calls']), 4)
            self.assertEqual(len({row['event_id'] for row in result['ast_events']}), 6)

    def test_changed_byte_binding_missing_and_extra_native_facts(self):
        raw = facts()
        with self.assertRaises(ProgramError):
            reconcile(SOURCE.replace(b'count', b'amount'), PURE | EFFECTS, raw)
        semantic = next(index for index, row in enumerate(raw['facts']) if row['kind'] == 'action')
        missing = deepcopy(raw)
        missing['facts'].pop(semantic)
        with self.assertRaises(ProgramError):
            reconcile(SOURCE, PURE | EFFECTS, missing)
        changed = deepcopy(raw)
        changed['facts'][semantic]['value'] = 'unobserved_host_execution'
        with self.assertRaises(ProgramError):
            reconcile(SOURCE, PURE | EFFECTS, changed)

    def test_span_argument_and_duplicate_call_inventory_mismatch(self):
        raw = facts()
        _, events = ast_events(SOURCE, PURE | EFFECTS)
        for mutation in ('column', 'argument', 'duplicate', 'missing'):
            changed = deepcopy(events)
            if mutation == 'column':
                changed[0]['column'] += 1
            elif mutation == 'argument':
                event = next(row for row in changed if row['kind'] == 'sealed_call')
                event['arguments'][0]['source_segment'] = 'different'
            elif mutation == 'duplicate':
                changed.append(deepcopy(changed[-1]))
            else:
                changed.pop()
            with self.subTest(mutation=mutation), self.assertRaises(ProgramError):
                reconcile(SOURCE, PURE | EFFECTS, raw, supplied_events=changed)


if __name__ == '__main__':
    unittest.main()
