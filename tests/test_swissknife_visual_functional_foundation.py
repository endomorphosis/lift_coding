"""Foundation decomposition preserves work and refuses fabricated completion."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_swissknife_visual_functional_plan as planner
import swissknife_visual_functional_worker as worker


def test_decomposition_preserves_every_unrelated_contract_and_final_acceptance():
    spec = {"tasks": [{"task_id": "SVF-030", "dependencies": ["SVF-111", "SVF-011"],
                       "edit_paths": ["swissknife/runner.mjs", "swissknife/test.mjs"],
                       "acceptance": "Independent real app and raw proof acceptance", "checks": []},
                      {"task_id": "SVF-111", "status": "completed", "dependencies": []},
                      {"task_id": "SVF-011", "status": "completed", "dependencies": []},
                      {"task_id": "SVF-112", "dependencies": ["SVF-030"]}], "goals": []}
    before = copy.deepcopy(spec)
    result = planner.decompose_foundation(spec)
    assert spec == before
    indexed = {t["task_id"]: t for t in result["tasks"]}
    for task in before["tasks"][1:]:
        assert indexed[task["task_id"]] == task
    assert indexed["SVF-030"]["acceptance"] == before["tasks"][0]["acceptance"]
    assert indexed["SVF-030"]["kind"] == "foundation-gate"
    assert indexed["SVF-030"]["dependencies"] == ["SVF-111", "SVF-011", "SVF-034"]
    assert indexed["SVF-031"]["kind"] == "command"
    assert indexed["SVF-034"]["foundation_pilot"] is True
    assert len(worker.validate_dag(result["tasks"])) == 8
    with pytest.raises(ValueError, match="already present"):
        planner.decompose_foundation(result)


def test_stage_snapshots_survive_next_stage_without_accepting_tampering(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    source = tmp_path / "swissknife/runner.mjs"
    source.parent.mkdir()
    source.write_text("// stage1 strict admission\n")
    directory = tmp_path / "data/task031"
    task = {"foundation_stage": 1, "edit_paths": ["swissknife/runner.mjs"]}
    retained, records = worker.snapshot_foundation_sources(task, directory, [source])
    assert len(retained) == len(records) == 1
    source.write_text("// stage2 actual browser engine\n")
    worker.check_artifacts([records[0]["snapshot"]], allowed_prefix=directory)
    assert retained[0].read_text() == "// stage1 strict admission\n"
    retained[0].write_text("// replaced historical source\n")
    with pytest.raises(ValueError, match="changed or missing"):
        worker.check_artifacts([records[0]["snapshot"]], allowed_prefix=directory)


def test_pilot_flags_do_not_replace_current_sources_screenshots_and_observations(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    profile = {"runtimeRoot": "data/agent_supervisor/swissknife_visual_functional"}
    directory = worker.runtime_root(profile) / "tasks/SVF-034/pilot"
    directory.mkdir(parents=True)
    source = tmp_path / "driver.mjs"
    source.write_text("// authored source fixture\n")
    images = []
    for name in ("desktop.png", "mobile.png"):
        p = directory / name
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"authored unit fixture" * 16)
        images.append(worker.artifact(p))
    task = {"task_id": "SVF-034", "pilot_sources": ["driver.mjs"]}
    report = {"schema": "swissknife.visual-functional-driver-pilot.v1", "app_id": "calculator",
              "actual_desktop": True, "foundation_integration_only": True, "functional_acceptance": False,
              "source_sha256": {"driver.mjs": worker.sha(source)}, "artifacts": images,
              "viewports": [{"viewport": {"name": name, "width": width, "height": height}, "actual_desktop": True,
                             "arithmetic": "50", "keyboard": "42", "recovered": "50", "division_error_observed": True,
                             "error_text": "Cannot divide by zero"} for name, width, height in (("desktop",1440,900),("mobile",390,844))],
              "observations": [{"kind": kind, "observation": {"operator": "equals", "actual": [result, result], "expected": [result, result]}}
                               for kind, result in (("arithmetic_result","50"),("keyboard_result","42"),("clear_recovery","50"))]}
    path = directory / "pilot.json"
    path.write_text(json.dumps(report))
    worker.validate_foundation_pilot(profile, task)
    report["observations"][0]["observation"]["actual"] = "12"
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="contradict"):
        worker.validate_foundation_pilot(profile, task)
    report["observations"][0]["observation"]["actual"] = ["50", "50"]
    path.write_text(json.dumps(report))
    source.write_text("// changed driver\n")
    with pytest.raises(ValueError, match="current driver"):
        worker.validate_foundation_pilot(profile, task)


def test_final_gate_cannot_skip_required_stages(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="required stages"):
        worker.validate_foundation_dependencies({}, {"tasks": []}, {"foundation_stages": ["SVF-031"]})


@pytest.mark.parametrize("skipped", [False, True])
def test_real_node_reporter_requires_positive_pass_count(tmp_path, monkeypatch, skipped):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    test = tmp_path / "detector.test.mjs"
    test.write_text("import test from 'node:test';\n" +
                    ("test.skip('unexecuted', () => {});\n" if skipped else
                     "test('real assertion', () => { if (2 + 2 !== 4) throw Error('wrong'); });\n"))
    if skipped:
        with pytest.raises(ValueError, match="no passing execution"):
            worker.run(["node", "--test", str(test)])
    else:
        result = worker.run(["node", "--test", str(test)])
        assert result["exit_code"] == 0
