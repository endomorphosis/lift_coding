"""Protocol selection regression: no Docker calls, providers, or benchmark reads."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("resource_collector", Path(__file__).with_name("collect-resource-observations.py"))
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class ProtocolSelectionTests(unittest.TestCase):
    def test_all_four_protocol_trials_preserve_execution_order(self):
        names = ["tune-mjcf-legacy-01", "tune-mjcf-factored-01", "tune-mjcf-factored-02", "tune-mjcf-legacy-02"]
        called = []
        def collect(name):
            position = names.index(name)
            called.append(name)
            stamp = f"2026-10-11T00:{position * 2:02}:00+00:00"
            row = {"trial": name, "launcher_started_at": stamp, "launcher_finished_at": stamp,
                "resources": {"maximum_observed_sample_interval_seconds": 0},
                "pressure_event_count": 0, "backoff_event_count": 0,
                "post_trial_container_observation": {"owned_trial_containers_absent": True}}
            sample = {"at": stamp, "mem_available_bytes": 32 * collector.GIB,
                "disk_free_bytes": 40 * collector.GIB, "load_1m": 1., "affinity_cpus": 20}
            return row, [sample]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "comparison-protocol.json").write_text(json.dumps({"trials": [{"name": name} for name in names]}))
            with patch.object(collector, "ROOT", root), patch.object(collector, "collect_trial", collect), \
                    patch.object(collector.subprocess, "check_output", side_effect=AssertionError("unexpected Docker call")), \
                    patch("sys.stdout", io.StringIO()):
                collector.main()
            result = json.loads((root / "resource-observations.json").read_text())
        self.assertEqual(called, names)
        self.assertEqual(result["trial_order"], names)
        self.assertEqual([row["trial"] for row in result["trials"]], names)
        self.assertEqual(result["aggregate_sampled_resources"]["sample_count"], 4)
        self.assertTrue(result["sequential_trials"])

    def test_duplicate_or_malformed_protocol_stops_before_trial_io(self):
        cases = [[], [{"name": "same"}, {"name": "same"}], [{"name": "../other"}],
                 [{"name": "/absolute"}], [{"name": ""}], [{"name": None}],
                 [{"name": []}], [{}], [None], [{"name": f"trial-{n}"} for n in range(17)]]
        for trials in cases:
            with self.subTest(trials=trials), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "comparison-protocol.json").write_text(json.dumps({"trials": trials}))
                with patch.object(collector, "ROOT", root), patch.object(collector, "collect_trial") as collect, \
                        patch.object(collector.subprocess, "check_output") as docker:
                    # Shape failures can currently be ValueError, TypeError or
                    # KeyError; every one must stop before reads/query dispatch.
                    with self.assertRaises((ValueError, TypeError, KeyError)):
                        collector.main()
                    collect.assert_not_called()
                    docker.assert_not_called()
                    self.assertFalse((root / "resource-observations.json").exists())


if __name__ == "__main__":
    unittest.main()
