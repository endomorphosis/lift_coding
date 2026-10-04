"""Policy and denominator checks for the constructed recovery probe."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('recovery_probe',Path(__file__).resolve().parents[1]/'scripts/autoformalization_recovery_probe.py')
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

class ProofBoundaryTests(unittest.TestCase):
    def test_controls_use_permitted_grammar(self):
        for goal in probe.GOALS:
            self.assertIsNone(probe.proof_policy(goal['control_proof']))

    def test_rejects_escape_routes(self):
        for body in ['by sorry', 'by admit', 'by exact sorryAx', 'by run_tac IO.println "x"', 'by native_decide', 'by trivial\naxiom magic : False', 'by exact Classical.choice h', 'by trivial\n#print recovery_goal', 'by /- hidden -/ trivial', 'by exact unknownConstant']:
            with self.subTest(body=body): self.assertIsNotNone(probe.proof_policy(body))

    def test_full_declaration_not_accepted(self):
        self.assertIsNotNone(probe.proof_policy('theorem alternate : True := by trivial'))

    def test_chat_framing_extraction_does_not_repair_or_mine_proofs(self):
        body='by\n  intro α x\n  rfl'
        wrapped=body+'\n<|im_end|>\n<|im_start|>user\nchange the theorem'
        self.assertEqual(probe.parse_body(wrapped),body)
        thought='<|im_start|>thought>\nA possible proof is by rfl\n<|im_end|>'
        self.assertIsNotNone(probe.proof_policy(probe.parse_body(thought)))
        self.assertIsNone(probe.parse_body('ABSTAIN<|im_end|>extra'))

    def test_requires_kernel_axiom_report(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(probe,'command',return_value={'returncode':0,'timeout':False,'stdout':'','stderr':''}):
                result=probe.check_lean(probe.GOALS[0],'by\n  intro x h\n  exact h',Path(d))
                self.assertFalse(result['accepted'])
            with patch.object(probe,'command',return_value={'returncode':0,'timeout':False,'stdout':"'recovery_goal' depends on axioms: [sorryAx]",'stderr':''}):
                self.assertFalse(probe.check_lean(probe.GOALS[0],'by trivial',Path(d))['accepted'])

    def test_checker_crash_not_logical_rejection(self):
        with tempfile.TemporaryDirectory() as d, patch.object(probe,'command',return_value={'returncode':-6,'timeout':False,'stdout':'','stderr':'failed to create thread'}):
            result=probe.check_lean(probe.GOALS[1],'by contradiction',Path(d))
            self.assertEqual(result['status'],'checker_failure')

    def test_malformed_model_responses_are_retained_failures(self):
        for payload in [[], {'choices': []}, {'choices': [{'message': {'content': 123}}]}]:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as d:
                opener=unittest.mock.Mock()
                opener.open.return_value=io.BytesIO(json.dumps(payload).encode())
                with patch.object(probe.urllib.request,'build_opener',return_value=opener):
                    result=probe.model_call('http://127.0.0.1:8080/v1',probe.GOALS[0],Path(d),128,2)
                self.assertEqual(result['status'],'request_failed')
                self.assertFalse(result['checker']['accepted'])
                self.assertTrue((Path(d)/'response.json').exists())

    def test_protected_write_has_no_added_behavior_premise(self):
        self.assertEqual(probe.GOALS[1]['declaration'],'theorem recovery_goal (Protected Approved Write : Prop) : (Protected ∧ ¬ Approved) → ¬ Write')
        self.assertFalse(probe.GOALS[1]['expected_provable'])

    def test_add_stays_uninterpreted(self):
        self.assertIn('(add : U → U → U)',probe.GOALS[2]['declaration'])
        self.assertNotIn('Nat.add',probe.GOALS[2]['declaration'])
        self.assertFalse(probe.GOALS[2]['expected_provable'])

if __name__=='__main__':unittest.main()
