"""Policy and denominator checks for the constructed recovery probe."""
import importlib.util
import contextlib
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
    def test_raw_lean_success_is_a_compile_diagnostic_without_admission(self):
        completed={'returncode':0,'timeout':False,'stdout':"'recovery_goal' does not depend on any axioms",'stderr':''}
        with tempfile.TemporaryDirectory() as d, patch.object(probe,'command',return_value=completed) as command:
            result=probe.check_lean(probe.GOALS[0],'by\n  intro x h\n  exact h',Path(d))
        self.assertTrue(result['compile_passed'])
        self.assertEqual(result['status'],'native_compile_diagnostic')
        self.assertFalse(result['accepted'])
        self.assertFalse(result['admitted'])
        self.assertFalse(result['lake_executed'])
        self.assertEqual(command.call_args.args[0][0],str(probe.LEAN))

    def test_compile_summary_preserves_diagnostic_counts_without_proof_counts(self):
        rows=[]
        for goal in probe.GOALS:
            checker={'status':'native_compile_diagnostic' if goal['expected_provable'] else 'native_rejected',
                     'compile_passed':goal['expected_provable'],'accepted':False,'admitted':False,'lake_executed':False}
            rows.append({'goal_id':goal['goal_id'],'expected_provable':goal['expected_provable'],
                         'native_control':checker,'solvers':{},'model':{'status':'response_received','checker':checker}})
        summary=probe.summarize_probe(rows,True,'mocked raw compile diagnostic')
        self.assertEqual(summary['schema'],'autoformalization-recovery-constructed-probe/v2')
        self.assertEqual(summary['model_compile_passed'],3)
        self.assertEqual(summary['native_positive_controls_compile_passed'],3)
        self.assertEqual(summary['native_negative_controls_rejected'],2)
        self.assertEqual(summary['completed_model_dispositions'],5)
        self.assertEqual(summary['model_native_accepted_proofs'],0)
        self.assertEqual(summary['native_positive_controls_accepted'],0)
        for field in ('accepted','admitted','lake_executed'):
            self.assertFalse(summary[field])

    def test_mocked_native_run_keeps_compile_gate_and_v2_receipts_separate(self):
        def mocked_command(argv,cwd,stdin=None,seconds=20):
            if '--version' in argv:
                stdout='mocked runtime version'
                returncode=0
            elif stdin is not None:
                stdout='sat' if '(set-logic QF_UF)' in stdin or '(declare-fun add' in stdin else 'unsat'
                returncode=0
            else:
                text=Path(argv[-1]).read_text()
                positive=not any(marker in text for marker in ('Protected Approved Write','(add : U → U → U)'))
                stdout="'recovery_goal' does not depend on any axioms" if positive else 'error: synthetic failed proof'
                returncode=0 if positive else 1
            return {'returncode':returncode,'timeout':False,'stdout':stdout,'stderr':''}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            historical=root/'historical.py'
            historical.write_text('ASSIST_GOALS = '+repr(probe.GOALS)+'\n')
            output=root/'result'
            with patch.object(probe,'HISTORICAL',historical), patch.object(probe,'command',side_effect=mocked_command), \
                 patch.object(probe,'model_call') as model_call, \
                 patch('sys.argv',['probe','--output',str(output),'--native-only']), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(probe.main(),0)
            model_call.assert_not_called()
            manifest=json.loads((output/'frozen_manifest.json').read_text())
            summary=json.loads((output/'summary.json').read_text())
            self.assertTrue(summary['native_controls_passed'])
            self.assertEqual(summary['native_positive_controls_compile_passed'],3)
            self.assertEqual(summary['native_negative_controls_rejected'],2)
            self.assertEqual(summary['native_positive_controls_accepted'],0)
            for receipt in (manifest,summary):
                self.assertEqual(receipt['schema'],probe.SCHEMA)
                for field in ('accepted','admitted','lake_executed'):
                    self.assertFalse(receipt[field])

    def test_compile_timeout_is_not_a_success_or_logical_rejection(self):
        with tempfile.TemporaryDirectory() as d, patch.object(probe,'command',return_value={'returncode':-9,'timeout':True,'stdout':'','stderr':''}):
            result=probe.check_lean(probe.GOALS[0],'by trivial',Path(d))
        self.assertEqual(result['status'],'timeout')
        for field in ('compile_passed','accepted','admitted','lake_executed'):
            self.assertFalse(result[field])

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
