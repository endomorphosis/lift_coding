"""Regeneration retains reviewed present-target identities without trusting live bytes."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("doep_generator", Path(__file__).parents[2] / "scripts/generate_agent_supervisor_direct_objective_event_driven_planning_board.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def test_dataset_baseline_survives_regeneration():
    tasks = generator.parse_tasks()
    selected = next(task for task in tasks if task["task_id"] == "DOEP-011")
    expected = 'baseline = { state = "present", sha256 = "6883fb2498ef6fba4e623036a30a2df8f3b3dce2d7a088180043dbfbda8613a0" }'
    assert generator._datasets_baseline(selected) == expected
    assert expected in generator._render_datasets_contract_block(tasks)
    assert generator._datasets_baseline(next(task for task in tasks if task["task_id"] == "DOEP-012")) == 'baseline = { state = "declared-output-absent" }'


@pytest.mark.parametrize("key", ["task_cid", "test_output"])
def test_requalified_identity_change_rejected(key):
    task = next(task for task in generator.parse_tasks() if task["task_id"] == "DOEP-011")
    task[key] = "different"
    with pytest.raises(ValueError, match="identity changed"):
        generator._datasets_baseline(task)
