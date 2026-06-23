from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"


def _imports():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import ObjectiveGoal
    from ipfs_accelerate_py.agent_supervisor.objective_task_janitor import (
        JANITOR_RECEIPT_SCHEMA,
        reconcile_objective_task_strategy,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalTask

    return ObjectiveGoal, PortalTask, JANITOR_RECEIPT_SCHEMA, reconcile_objective_task_strategy


def test_objective_task_janitor_blocks_orphans_deprioritizes_noise_and_reopens_launch_goal():
    ObjectiveGoal, PortalTask, schema, reconcile = _imports()
    goals = [
        ObjectiveGoal(
            "VAIOS-G697",
            "Production launch readiness gate",
            {
                "status": "active",
                "fib_priority": "1",
                "priority": "P0",
                "track": "launch",
                "goal": "Phone-hosted Swissknife virtual desktop with desktop offload and Meta glasses terminal.",
            },
        ),
        ObjectiveGoal(
            "VAIOS-G111",
            "Completed scanner churn",
            {"status": "completed", "fib_priority": "8", "priority": "P3", "track": "ops"},
        ),
    ]
    tasks = [
        PortalTask(
            "VAI-001",
            "Old generated task",
            "todo",
            "manual",
            "P2",
            "ops",
            metadata={"goal id": "VAIOS-G111"},
        ),
        PortalTask(
            "VAI-002",
            "Objective scan: generic AST scrape",
            "todo",
            "manual",
            "P3",
            "ops",
            metadata={"missing evidence": "generic symbol match", "bundle shard": "data/old.todo.md"},
        ),
    ]
    strategy = {
        "blocked_tasks": ["VAI-KEEP", "VAI-OLD"],
        "deprioritized_tasks": ["VAI-KEEP-D", "VAI-OLD-D"],
        "objective_task_janitor_receipts": [
            {"schema": schema, "action": "block", "task_id": "VAI-OLD"},
            {"schema": schema, "action": "deprioritize", "task_id": "VAI-OLD-D"},
        ],
    }

    result = reconcile(goals=goals, tasks=tasks, strategy=strategy, now="2026-06-23T00:00:00+00:00")
    updated = result["strategy"]

    assert result["changed"]
    assert updated["blocked_tasks"] == ["VAI-KEEP", "VAI-001"]
    assert updated["deprioritized_tasks"] == ["VAI-KEEP-D", "VAI-002"]
    assert updated["objective_task_janitor_reopen_goal_ids"] == ["VAIOS-G697"]
    assert updated["objective_task_janitor_force_goal_ids"] == ["VAIOS-G697"]
    assert updated["heap_goal_retirement_receipt"][0]["retired_task_reason"] == "goal_completed"
    assert all(receipt["schema"] == schema for receipt in updated["objective_task_janitor_receipts"])


def test_objective_task_janitor_releases_owned_blocks_when_goal_has_open_work():
    ObjectiveGoal, PortalTask, schema, reconcile = _imports()
    goals = [
        ObjectiveGoal(
            "VAIOS-G697",
            "Production launch readiness gate",
            {
                "status": "active",
                "fib_priority": "1",
                "priority": "P0",
                "track": "launch",
                "goal": "Phone-hosted Swissknife virtual desktop with desktop offload and Meta glasses terminal.",
            },
        )
    ]
    tasks = [
        PortalTask(
            "VAI-003",
            "Launch gate implementation",
            "todo",
            "manual",
            "P0",
            "launch",
            metadata={"goal id": "VAIOS-G697"},
        )
    ]
    strategy = {
        "blocked_tasks": ["VAI-003", "VAI-KEEP"],
        "objective_task_janitor_receipts": [
            {"schema": schema, "action": "block", "task_id": "VAI-003"},
        ],
    }

    result = reconcile(goals=goals, tasks=tasks, strategy=strategy, now="2026-06-23T00:00:00+00:00")
    updated = result["strategy"]

    assert result["changed"]
    assert updated["blocked_tasks"] == ["VAI-KEEP"]
    assert updated["objective_task_janitor_reopen_goal_ids"] == []
    assert result["open_goal_ids"] == ["VAIOS-G697"]


def test_objective_task_janitor_records_configured_mission_terms():
    ObjectiveGoal, PortalTask, _schema, reconcile = _imports()
    goals = [
        ObjectiveGoal(
            "VAIOS-G777",
            "Desktop peer router",
            {
                "status": "active",
                "fib_priority": "1",
                "priority": "P1",
                "track": "integration",
                "goal": "Build an edge compositor handshake for phone to desktop routing.",
            },
        )
    ]

    result = reconcile(
        goals=goals,
        tasks=[],
        strategy={},
        now="2026-06-23T00:00:00+00:00",
        mission_terms=("edge compositor handshake",),
    )
    updated = result["strategy"]

    assert updated["objective_task_janitor_reopen_goal_ids"] == ["VAIOS-G777"]
    assert updated["objective_task_janitor_force_goal_ids"] == ["VAIOS-G777"]
    assert updated["objective_task_janitor_mission_terms"] == ["edge compositor handshake"]


def test_objective_task_janitor_deprioritizes_off_mission_codebase_scan_backlog():
    _ObjectiveGoal, PortalTask, schema, reconcile = _imports()
    tasks = [
        PortalTask(
            "VAI-199",
            "Review swallowed exception path in hallucinate_app/python/hallucinate_app/control_surface_policy.py:1032",
            "todo",
            "manual",
            "P1",
            "runtime",
            acceptance=(
                "Codebase scan filed this finding from hallucinate_app/python/hallucinate_app/"
                "control_surface_policy.py:1032."
            ),
        ),
        PortalTask(
            "MGW-026",
            "Resolve validation retry-budget failure for MGW-003",
            "todo",
            "manual",
            "P1",
            "ops",
            acceptance="Validation retry-budget guardrail filed this from repeated validation failures.",
        ),
        PortalTask(
            "MGW-027",
            "Resolve code annotation in swissknife/meta_glasses_overlay.ts:44",
            "todo",
            "manual",
            "P1",
            "runtime",
            acceptance="Keep the Meta glasses interface Playwright launch replay covered.",
        ),
    ]

    result = reconcile(
        goals=[],
        tasks=tasks,
        strategy={},
        now="2026-06-23T00:00:00+00:00",
        mission_terms=("Meta glasses interface", "Playwright launch replay"),
    )
    updated = result["strategy"]

    assert result["changed"]
    assert updated["deprioritized_tasks"] == ["VAI-199"]
    assert updated["objective_task_janitor_receipts"] == [
        {
            "schema": schema,
            "recorded_at": "2026-06-23T00:00:00+00:00",
            "task_id": "VAI-199",
            "action": "deprioritize",
            "retired_task_reason": "off_mission_codebase_scan_task",
            "goal_ids": [],
            "title": (
                "Review swallowed exception path in hallucinate_app/python/hallucinate_app/"
                "control_surface_policy.py:1032"
            ),
            "priority": "P1",
            "track": "runtime",
        }
    ]


def test_supervisor_objective_refill_forces_janitor_reopened_goals(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        PortalImplementationSupervisor,
        PortalSupervisorConfig,
    )

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    todo_path = tmp_path / "vai.todo.md"
    strategy_path = state_dir / "virtual_ai_os_strategy.json"
    state_path = state_dir / "virtual_ai_os_task_state.json"
    events_path = state_dir / "virtual_ai_os_supervisor_events.jsonl"
    objective_path = tmp_path / "objective.md"
    todo_path.write_text(
        "\n".join(
            (
                "# VAI",
                "## VAI-001 First ready item",
                "- Status: todo",
                "- Priority: P1",
                "- Track: ops",
                "## VAI-002 Second ready item",
                "- Status: todo",
                "- Priority: P1",
                "- Track: ops",
            )
        ),
        encoding="utf-8",
    )
    objective_path.write_text(
        "\n".join(
            (
                "# Goals",
                "## VAIOS-G697 Launch gate",
                "- Status: active",
                "- Fib priority: 1",
                "- Track: launch",
            )
        ),
        encoding="utf-8",
    )
    strategy_path.write_text(
        json.dumps(
            {
                "last_objective_goal_scan_at": "2026-06-23T00:00:00+00:00",
                "objective_task_janitor_force_goal_ids": ["VAIOS-G697"],
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}
    supervisor = PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            events_path=events_path,
            state_dir=state_dir,
            task_prefix="## VAI-",
            state_prefix="virtual_ai_os",
            objective_refill_enabled=True,
            objective_path=objective_path,
            objective_scan_min_open_tasks=0,
            objective_scan_cooldown_seconds=86400,
            repo_root=tmp_path,
        )
    )

    def fake_refill(_run_objective_daemon, args):
        captured["force_goal_id"] = list(args.force_goal_id)
        return {
            "generated_count": 0,
            "task_ids": [],
            "refined_goal_ids": [],
            "completed_goal_ids": [],
            "seeded_interoperability_goal_ids": [],
            "objective_goal_count": 1,
            "objective_active_goal_count": 1,
            "objective_completed_goal_count": 0,
            "objective_heap_schedule_count": 1,
            "todo_vector_index_path": "",
        }

    supervisor._run_objective_refill_with_timeout = fake_refill  # type: ignore[method-assign]

    payload = supervisor.refill_objective_backlog()
    updated_strategy = json.loads(strategy_path.read_text(encoding="utf-8"))

    assert payload["objective_heap_schedule_count"] == 1
    assert captured["force_goal_id"] == ["VAIOS-G697"]
    assert updated_strategy["last_objective_goal_scan_mode"] == "force"
    assert updated_strategy["last_objective_task_janitor_force_goal_ids"] == ["VAIOS-G697"]


def test_supervisor_run_forever_runs_preflight_before_daemon_loop(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        PortalImplementationSupervisor,
        PortalSupervisorConfig,
    )

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    calls: list[str] = []
    supervisor = PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=tmp_path / "vai.todo.md",
            state_path=state_dir / "virtual_ai_os_task_state.json",
            strategy_path=state_dir / "virtual_ai_os_strategy.json",
            events_path=state_dir / "virtual_ai_os_supervisor_events.jsonl",
            state_dir=state_dir,
            task_prefix="## VAI-",
            state_prefix="virtual_ai_os",
            repo_root=tmp_path,
        )
    )

    supervisor.ensure_event_log_file = lambda: calls.append("ensure_event_log_file") or {}  # type: ignore[method-assign]
    supervisor.repair_main_checkout_merge_state = lambda: calls.append("repair_main_checkout_merge_state") or {}  # type: ignore[method-assign]
    supervisor.ensure_managed_daemon_pid_file = lambda: calls.append("ensure_managed_daemon_pid_file") or {}  # type: ignore[method-assign]
    supervisor.run_once = lambda: calls.append("run_once") or {"objective_task_janitor": {}}  # type: ignore[method-assign]
    supervisor.build_supervisor_loop_config = lambda: calls.append("build_supervisor_loop_config") or object()  # type: ignore[method-assign]

    class FakeSupervisorLoop:
        def __init__(self, _config, watchdog_hook=None):
            calls.append("loop_init")
            assert "run_once" in calls
            assert calls.index("run_once") < calls.index("loop_init")
            self.watchdog_hook = watchdog_hook

        def run(self):
            calls.append("loop_run")
            return SimpleNamespace(
                status="stopped",
                restart_count=0,
                last_exit_code=0,
                last_recycle_reason="",
                last_run_id="test",
                last_log_path="",
            )

    supervisor.shared_supervisor_loop_class = FakeSupervisorLoop

    supervisor.run_forever()

    assert calls[:4] == [
        "ensure_event_log_file",
        "repair_main_checkout_merge_state",
        "ensure_managed_daemon_pid_file",
        "run_once",
    ]
    assert calls[-2:] == ["loop_init", "loop_run"]


def test_supervisor_rewrite_strategy_blocks_stale_merge_reconciliation(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalTaskState
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        PortalImplementationSupervisor,
        PortalSupervisorConfig,
    )

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    strategy_path = state_dir / "virtual_ai_os_strategy.json"
    strategy_path.write_text(
        json.dumps(
            {
                "generation": 7,
                "focus_tracks": ["ops", "launch"],
                "blocked_tasks": ["VAI-KEEP"],
                "deprioritized_tasks": [],
            }
        ),
        encoding="utf-8",
    )
    supervisor = PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=tmp_path / "vai.todo.md",
            state_path=state_dir / "virtual_ai_os_task_state.json",
            strategy_path=strategy_path,
            events_path=state_dir / "virtual_ai_os_supervisor_events.jsonl",
            state_dir=state_dir,
            task_prefix="## VAI-",
            state_prefix="virtual_ai_os",
            repo_root=tmp_path,
        )
    )
    state = PortalTaskState(
        active_task_id="VAI-046",
        active_task_track="ops",
        active_phase="merge_resolver",
    )

    strategy = supervisor.rewrite_strategy(
        state,
        "merge_resolver stalled for active task VAI-046: no active worker for 252s",
    )

    assert strategy["generation"] == 8
    assert strategy["focus_tracks"][0] == "launch"
    assert strategy["blocked_tasks"] == ["VAI-KEEP", "VAI-046"]
    assert strategy["deprioritized_tasks"] == ["VAI-046"]
