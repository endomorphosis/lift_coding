"""Pure regressions for current-main preservation; no Git operations execute."""
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    'current_main_overlay_fixture', Path(__file__).with_name('prepare_current_main_publication.py'))
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


def blob(oid='a' * 40, mode='100644'):
    return {'mode': mode, 'kind': 'blob', 'oid': oid}


class CurrentMainPreservationFixtures(unittest.TestCase):
    def setUp(self):
        self.baseline = {
            'external/ipfs_accelerate': {'mode': '160000', 'kind': 'commit', 'oid': '4' * 40},
            'maintenance/tool.py': blob('b' * 40, '100755'),
            'qualification/current.json': blob('c' * 40),
            'implementation_plan/docs/plan.md': blob('d' * 40),
        }

    def test_advanced_main_gitlink_and_unrelated_maintenance_are_preserved(self):
        selected = {'implementation_plan/docs/plan.md': blob('e' * 40)}
        result = prepare.overlay_expectation(self.baseline, selected)
        self.assertEqual(result['external/ipfs_accelerate'], self.baseline['external/ipfs_accelerate'])
        self.assertEqual(result['maintenance/tool.py'], self.baseline['maintenance/tool.py'])
        self.assertEqual(result['qualification/current.json'], self.baseline['qualification/current.json'])
        self.assertEqual(result['implementation_plan/docs/plan.md'], selected['implementation_plan/docs/plan.md'])
        self.assertEqual(set(result), set(self.baseline))

    def test_no_baseline_or_selected_input_mutation(self):
        selected = {'implementation_plan/docs/plan.md': blob('e' * 40)}
        before = copy.deepcopy((self.baseline, selected))
        result = prepare.overlay_expectation(self.baseline, selected)
        result['external/ipfs_accelerate']['oid'] = 'f' * 40
        self.assertEqual((self.baseline, selected), before)

    def test_selected_source_cannot_replace_current_main_gitlink(self):
        with self.assertRaisesRegex(ValueError, 'Gitlink'):
            prepare.overlay_expectation(self.baseline, {'external/ipfs_accelerate': blob()})

    def test_selected_source_cannot_write_inside_a_gitlink(self):
        with self.assertRaisesRegex(ValueError, 'collides'):
            prepare.overlay_expectation(self.baseline, {'external/ipfs_accelerate/new.py': blob()})

    def test_selected_parent_file_cannot_erase_unselected_tree_entries(self):
        with self.assertRaisesRegex(ValueError, 'collides'):
            prepare.overlay_expectation(self.baseline, {'qualification': blob()})

    def test_new_source_paths_are_added_without_deleting_baseline_paths(self):
        selected = {'implementation_plan/docs/new.md': blob('e' * 40),
                    'artifacts/campaign/new.py': blob('f' * 40)}
        result = prepare.overlay_expectation(self.baseline, selected)
        self.assertEqual(set(result), set(self.baseline) | set(selected))
        for name, entry in self.baseline.items():
            self.assertEqual(result[name], entry)

    def test_selected_path_collisions_are_rejected_in_either_order(self):
        for selected in ({'new': blob(), 'new/file.py': blob('e' * 40)},
                         {'new/file.py': blob('e' * 40), 'new': blob()}):
            with self.subTest(selected=selected):
                with self.assertRaisesRegex(ValueError, 'collides'):
                    prepare.overlay_expectation(self.baseline, selected)

    def test_unsafe_paths_and_nonordinary_overlay_entries_are_rejected(self):
        for name, entry in (('../escape.py', blob()), ('/absolute.py', blob()),
                            ('.git/config', blob()), ('bad\nname.py', blob()),
                            ('new.py', {'mode': '160000', 'kind': 'commit', 'oid': 'a' * 40}),
                            ('new.py', blob('short')), ('new.py', blob(mode='120000'))):
            with self.subTest(name=name, entry=entry):
                with self.assertRaises(ValueError):
                    prepare.overlay_expectation(self.baseline, {name: entry})


if __name__ == '__main__':
    unittest.main()
