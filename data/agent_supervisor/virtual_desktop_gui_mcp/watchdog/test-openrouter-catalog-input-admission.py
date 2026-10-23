"""Pure R23 task transition and ownership tests; no GUI or completion authority."""
import copy
from contextlib import nullcontext, redirect_stdout
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path
import shlex
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r23_admission_test_subject', HERE / 'admit-openrouter-catalog-input-repair.py')
admission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admission)
ORIGINAL = (HERE / 'smoke-receipts/openrouter-catalog-input/actual-failure/taskboard-before.todo').read_text()
REAL_ROOT = Path('/home/barberb/lift_coding')

def field(text, task, label, value):
    import re
    pattern = re.compile(r'(^## '+re.escape(task)+r'\b[^\n]*\n)(.*?)(?=^## |\Z)', re.M | re.S)
    match = pattern.search(text)
    assert match is not None
    body, count = re.subn(r'^- '+re.escape(label)+r': [^\n]*$', '- '+label+': '+value, match.group(2), count=1, flags=re.M)
    assert count == 1
    return text[:match.start()]+match.group(1)+body+text[match.end():]

class TransitionTests(unittest.TestCase):
    def build(self, text=ORIGINAL):
        return admission.build_admission(text, root=REAL_ROOT)

    def test_real_archived_board_gains_only_one_pending_repair_and_twelve_prefixes(self):
        result, before, after = self.build()
        self.assertEqual((len(before), len(after)), (64, 65))
        self.assertEqual(set(after)-set(before), {'VDG-013-R23'})
        self.assertEqual(after['VDG-013-R23']['status'], 'pending')
        for task, pair in admission.ORIGINAL_COMMANDS.items():
            for key, command in zip(('deterministic_command','validation'), pair):
                actual = after[task][key]
                self.assertEqual(actual, admission.WRAPPER+command)
                self.assertEqual(shlex.split(actual)[3:], shlex.split(command))
        self.assertTrue(result['admitted'])

    def test_all_other_fields_statuses_history_budgets_and_unrelated_tasks_are_exact(self):
        _, before, after = self.build()
        for task, row in before.items():
            expected = dict(row)
            if task == admission.TARGET:
                expected['depends_on'] += ', '+admission.REPAIR
            if task in admission.ORIGINAL_COMMANDS:
                for key in ('deterministic_command','validation'):
                    expected[key] = admission.WRAPPER+row[key]
            self.assertEqual(after[task], expected, task)

    def test_existing_commands_cannot_be_replaced_or_add_fresh_before_admission(self):
        for task, pair in admission.ORIGINAL_COMMANDS.items():
            for label, command in zip(('Deterministic command','Validation'), pair):
                changed = field(ORIGINAL, task, label, command+' --fresh')
                with self.subTest(task=task, label=label), mock.patch.object(admission, 'admit_gate_repair_task') as helper:
                    with self.assertRaisesRegex(ValueError, 'Original command changed'):
                        self.build(changed)
                    helper.assert_not_called()

    def test_no_completed_pipeline_task_can_be_reclassified(self):
        for task in admission.ORIGINAL_COMMANDS:
            with self.subTest(task=task), self.assertRaisesRegex(ValueError, 'pending'):
                self.build(field(ORIGINAL, task, 'Status', 'completed'))

    def test_prerequisite_must_have_naturally_completed(self):
        with self.assertRaisesRegex(ValueError, 'R22 must naturally complete'):
            self.build(field(ORIGINAL, 'VDG-013-R22', 'Status', 'pending'))

    def test_missing_pipeline_task_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'pipeline task missing'):
            self.build(ORIGINAL.replace('## VDG-036-R02 ', '## VDG-999-R02 ', 1))

    def test_dependency_cycle_and_missing_dependency_are_rejected(self):
        for task, dep in [('VDG-013-R22','VDG-039-R01'), ('VDG-039-R01','VDG-DOES-NOT-EXIST')]:
            with self.subTest(task=task), self.assertRaises(ValueError):
                self.build(field(ORIGINAL, task, 'Depends on', dep))

    def test_unexpected_helper_history_mutation_is_rejected(self):
        real = admission.admit_gate_repair_task
        def faulty(*args, **kwargs):
            result = real(*args, **kwargs)
            result['todo_text'] = field(result['todo_text'], 'VDG-013-R22', 'Completion', 'fabricated completion')
            return result
        with mock.patch.object(admission, 'admit_gate_repair_task', side_effect=faulty), self.assertRaisesRegex(ValueError, 'Unapproved existing task/history'):
            self.build()

    def test_idempotent_admission_does_not_create_another_repair_or_rewrap(self):
        first, _, after = self.build()
        second, before2, after2 = self.build(first['todo_text'])
        self.assertFalse(second['admitted'])
        self.assertEqual(second['reason'], 'already_admitted')
        self.assertEqual(second['todo_text'], first['todo_text'])
        self.assertEqual(before2, after)
        self.assertEqual(after2, after)

    def test_existing_repair_contract_or_guarded_child_tampering_is_rejected(self):
        result, _, _ = self.build()
        samples = [field(result['todo_text'], 'VDG-013-R23', 'Validation', 'python3 wrong.py'),
                   field(result['todo_text'], 'VDG-036-R01', 'Deterministic command', admission.WRAPPER+'node wrong.mjs')]
        for changed in samples:
            with self.subTest(changed=changed[:40]), self.assertRaises(ValueError):
                self.build(changed)

    def test_idempotent_main_requires_the_existing_admission_proof(self):
        verifier = SimpleNamespace(verify_ready_proof=mock.Mock(return_value={}))
        spec = SimpleNamespace(loader=SimpleNamespace(exec_module=mock.Mock()))
        with mock.patch.object(admission, 'lifecycle_fence', return_value=nullcontext({})), \
             mock.patch.object(admission, 'BOARD') as board, \
             mock.patch.object(admission, 'build_admission', return_value=({'todo_text':'same','admitted':False}, {}, {})), \
             mock.patch.object(admission, 'recheck_fence'), \
             mock.patch.object(admission.importlib.util, 'spec_from_file_location', return_value=spec), \
             mock.patch.object(admission.importlib.util, 'module_from_spec', return_value=verifier), \
             redirect_stdout(io.StringIO()):
            board.read_text.return_value = 'same'
            admission.main([])
        verifier.verify_ready_proof.assert_called_once_with(require_admission=True)

class OwnedHoldTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory(prefix='r23-admission-hold-test-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        markers = {}
        for name in ('HOLD','repair-dispatcher.hold'):
            path = root/name
            path.write_text(json.dumps({'token':'08af974871cc4577a9744d6043df8c80','lane_pid':1960744}))
            info = path.stat()
            markers[name] = {'device':info.st_dev,'inode':info.st_ino,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        receipt = {'token':'08af974871cc4577a9744d6043df8c80','lane_pid':1960744,'markers':markers}
        (root/'r23-catalog-drift-repair-hold.json').write_text(json.dumps(receipt))
        return root, receipt

    def test_matching_owned_uid_inode_bytes_and_tokens_are_required(self):
        root, _ = self.fixture()
        admission.verify_owned_holds(root)

    def test_same_bytes_on_a_replaced_inode_cannot_be_removed_as_owned(self):
        root, _ = self.fixture()
        original = root/'HOLD'
        replacement = root/'replacement'
        replacement.write_bytes(original.read_bytes())
        os.replace(replacement, original)
        with self.assertRaisesRegex(ValueError, 'inode/UID'):
            admission.verify_owned_holds(root)

    def test_symlink_marker_is_rejected_even_if_target_bytes_match(self):
        root, _ = self.fixture()
        original = root/'HOLD'
        target = root/'target'
        target.write_bytes(original.read_bytes())
        original.unlink()
        original.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'inode/UID'):
            admission.verify_owned_holds(root)

    def test_changed_marker_bytes_missing_marker_and_wrong_receipt_token_reject(self):
        root, receipt = self.fixture()
        (root/'HOLD').write_text('operator replacement')
        with self.assertRaisesRegex(ValueError, 'bytes'):
            admission.verify_owned_holds(root)
        (root/'HOLD').unlink()
        with self.assertRaises(OSError):
            admission.verify_owned_holds(root)
        receipt['token'] = 'wrong'
        (root/'r23-catalog-drift-repair-hold.json').write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            admission.verify_owned_holds(root)

    def test_unexpected_marker_path_is_rejected_without_access(self):
        root, receipt = self.fixture()
        receipt['markers']['../../unrelated'] = dict(receipt['markers']['HOLD'])
        (root/'r23-catalog-drift-repair-hold.json').write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'Unexpected hold marker'):
            admission.verify_owned_holds(root)

class EntrypointTests(unittest.TestCase):
    def test_options_with_values_do_not_hide_the_entrypoint(self):
        wrapper = str(REAL_ROOT/'swissknife/scripts/run-with-vdg-openrouter-catalog-input.mjs')
        for option in ('--title','--redirect-warnings','--env-file','--inspect-port','--diagnostic-dir'):
            with self.subTest(option=option):
                self.assertEqual(admission.node_scripts(['node',option,'value',wrapper,'argument']), {wrapper})
                self.assertEqual(admission.node_scripts(['node',option,wrapper,'unrelated.mjs']), {'unrelated.mjs'})
        self.assertEqual(admission.node_scripts(['node','--future-value-option','value',wrapper]), {'value',wrapper})
        self.assertEqual(admission.node_scripts(['node','--future-boolean-option',wrapper]), {wrapper})
        self.assertEqual(admission.node_scripts(['node','unrelated.mjs',wrapper]), {'unrelated.mjs'})
        self.assertEqual(admission.node_scripts(['node','--trace-warnings',wrapper,'data']), {wrapper})
        self.assertEqual(admission.node_scripts(['node','--title=label',wrapper]), {wrapper})
        self.assertEqual(admission.node_scripts(['node','--run','task',wrapper]), set())

    def test_only_actual_node_operands_are_recognized(self):
        wrapper = str(REAL_ROOT/'swissknife/scripts/run-with-vdg-openrouter-catalog-input.mjs')
        self.assertEqual(admission.node_script(['node','--import','/tmp/loader.mjs',wrapper,'--','node','child.mjs']), wrapper)
        for argv in [['node','-e',wrapper],['bash','-lc','node '+wrapper],['node','--eval='+wrapper]]:
            self.assertIsNone(admission.node_script(argv))

    def test_active_wrapper_is_a_capture_owner_even_before_child_launch(self):
        temporary = tempfile.TemporaryDirectory(prefix='r23-admission-proc-test-')
        self.addCleanup(temporary.cleanup)
        proc = Path(temporary.name)
        wrapper = REAL_ROOT/'swissknife/scripts/run-with-vdg-openrouter-catalog-input.mjs'
        for number, argv in [(101,['node',str(wrapper),'--','node','child.mjs']),
                             (102,['node','-e',str(wrapper)]),
                             (103,['node','--title','worker',str(wrapper)]),
                             (104,['node','--redirect-warnings','/tmp/warnings',str(wrapper)]),
                             (105,['node','--unknown-option','value',str(wrapper)]),
                             (106,['node','unrelated.mjs',str(wrapper)]),
                             (107,['node','--title',str(wrapper),'unrelated.mjs'])]:
            item = proc/str(number)
            item.mkdir()
            (item/'cmdline').write_bytes(b'\0'.join(value.encode() for value in argv)+b'\0')
            (item/'exe').symlink_to('/usr/bin/node')
            (item/'cwd').symlink_to(REAL_ROOT, target_is_directory=True)
        self.assertEqual(sorted(admission.active_captures(root=REAL_ROOT, proc_root=proc)), [101,103,104,105])

if __name__ == '__main__':
    unittest.main()
