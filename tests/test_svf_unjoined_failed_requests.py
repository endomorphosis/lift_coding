"""Failed owner requests stay visible to review without becoming success proof."""
import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import swissknife_visual_functional_final_coverage as final

ATTEMPT = ROOT / 'data/agent_supervisor/swissknife_visual_functional/tasks/SVF-1032/verification/attempt-nqe0k6ke'


class UnjoinedFailedRequestTests(unittest.TestCase):
    def test_rejected_probe_receipt_is_projected_and_not_a_success_row(self):
        if not ATTEMPT.is_dir():
            self.skipTest('retained SVF-1032 attempt is not in this checkout')
        parent = json.loads((ATTEMPT / 'workflow.json').read_text())
        scenario = json.loads((ROOT / 'swissknife/test/e2e/functional-workflows/system-monitor.json').read_text())
        added = 0
        for entry in parent['viewport_reports']:
            child_path = ROOT / entry['report']['path']
            child = json.loads(child_path.read_text())
            rows = final._unjoined_failed_requests(ROOT, child, scenario, child_path)
            self.assertEqual(len(rows), 1, entry['name'])
            request, phase, step, error, receipt = rows[0]
            self.assertEqual(phase, 2)
            self.assertEqual(step, 2)
            self.assertIn('Unsupported native observation arguments', error)
            self.assertRegex(receipt, r'^b[a-z2-7]{58}$')
            joined = {item['request_phase_index'] for item in child['backend_observations']}
            self.assertNotIn(request, joined)
            self.assertTrue(any(item['receipt_id'] == receipt and item['phase'] == 'failure_recovery'
                                 for item in child['backend_request_artifacts']['requests']))
            added += len(json.dumps(rows, separators=(',', ':')).encode())
        evidence = json.loads((ATTEMPT / 'model-inputs/visual-review-c925ef6798c94be4bdfca80b3e1f7807/evidence-0.json').read_text())
        expanded = final._expand_projection(evidence)
        note = (' failed_requests rows are request, phase index, step, owner error, receipt CID. '
                'phase indexes scenario_phase_order. Outcome is failed. Not semantic success proof.')
        expanded['instruction'] += note
        expanded['failed_requests_columns'] = ['request', 'phase', 'step', 'error', 'receipt_cid']
        self.assertLessEqual(len(final.encoded(expanded)) + added, 18000)


if __name__ == '__main__':
    unittest.main()
