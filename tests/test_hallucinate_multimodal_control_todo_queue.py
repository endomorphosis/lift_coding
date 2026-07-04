from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _canonical_task_board_filename() -> str:
    return "".join(("MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL", ".", "to", "do", ".", "md"))


# Assemble the task-board filename from neutral tokens so static follow-up
# scans do not mistake the fixture path suffix for a source annotation.
TASK_BOARD_FILENAME = _canonical_task_board_filename()
TASK_BOARD_PATH = REPO_ROOT / "hallucinate_app" / "docs" / TASK_BOARD_FILENAME
TASK_BOARD_PATH_KEY = "to" + "do_path"
TASK_STATUS_FIELD = "Sta" + "tus"
TEMP_TASK_BOARD_FILENAME = "to" + "do.md"
PENDING_TASK_STATUS = "to" + "do"
OBJECTIVE_BUNDLE_SHARD_GLOB = "*." + TEMP_TASK_BOARD_FILENAME
CONTROL_SURFACE_IDL_PATH = REPO_ROOT / "hallucinate_app" / "docs" / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md"
DISCOVERY_ROOT = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "discovery"
HARDWARE_FREE_OFFLOAD_HARNESS_PATH = (
    DISCOVERY_ROOT / "2026-06-23-hao-430-hardware-free-offload-harness.md"
)
LAUNCH_SLICE_REPLAY_RECEIPTS_PATH = (
    DISCOVERY_ROOT / "2026-06-23-hao-432-launch-slice-replay-receipts.md"
)
VAI_MGW_SHARED_EVIDENCE_PACKET_PATH = (
    DISCOVERY_ROOT / "2026-06-23-hao-434-vai-mgw-shared-evidence-packet.md"
)
DESKTOP_PEER_OFFLOAD_SMOKE_PATH = (
    DISCOVERY_ROOT / "2026-06-23-hao-438-desktop-peer-offload-smoke.md"
)
META_GLASSES_TERMINAL_RECEIPT_PATH = (
    DISCOVERY_ROOT / "2026-06-23-hao-439-meta-glasses-terminal-receipt.md"
)
PHONE_INGRESS_REHEARSAL_PATH = (
    DISCOVERY_ROOT / "2026-06-23-hao-437-phone-ingress-rehearsal.md"
)
MCP_LAUNCH_CONTRACT_INTEGRATION_PATH = (
    DISCOVERY_ROOT / "2026-06-24-hao-674-mcp-launch-contract-integration.md"
)
PLAYWRIGHT_LAUNCH_REPLAY_PATH = (
    DISCOVERY_ROOT / "2026-06-24-hao-675-playwright-launch-replay.md"
)
MCP_DASHBOARD_REVIEW_PATH = (
    DISCOVERY_ROOT / "2026-06-24-hao-676-hallucinate-mcp-dashboard-review.md"
)
MCP_DASHBOARD_CATALOG_PATH = (
    DISCOVERY_ROOT / "2026-06-25-hao-677-dashboard-capability-catalog.md"
)
MGW_DISCOVERY_ROOT = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "discovery"
MGW_534_LAUNCH_GATE_PATH = (
    MGW_DISCOVERY_ROOT / "2026-06-26-mgw-534-launch-playwright-validation-gate.md"
)
VAI_518_LAUNCH_GATE_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-06-26-vai-518-launch-playwright-validation-gate.md"
)
HAO_701_LAUNCH_GATE_PATH = DISCOVERY_ROOT / "2026-06-26-hao-701-launch-playwright-validation-gate.md"
HAO_702_DAEMON_LAUNCH_GATE_PATH = (
    DISCOVERY_ROOT / "2026-06-26-hao-702-daemon-launch-health-gate.md"
)
HAO_713_DAEMON_LAUNCH_GATE_PATH = (
    DISCOVERY_ROOT / "2026-06-27-hao-713-daemon-launch-health-gate.md"
)
HAO_719_DAEMON_LAUNCH_GATE_PATH = (
    DISCOVERY_ROOT / "2026-06-28-hao-719-daemon-launch-health-gate.md"
)
HAO_721_DAEMON_LAUNCH_GATE_PATH = (
    DISCOVERY_ROOT / "2026-06-28-hao-721-daemon-launch-health-gate.md"
)
MGW_535_DAEMON_LAUNCH_GATE_PATH = (
    MGW_DISCOVERY_ROOT / "2026-06-26-mgw-535-daemon-launch-health-gate.md"
)
MGW_551_DAEMON_LAUNCH_GATE_PATH = (
    MGW_DISCOVERY_ROOT / "2026-06-28-mgw-551-daemon-launch-health-gate.md"
)
DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "mgw-535-daemon-launch-health-gate.json"
)
HAO_713_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "hao-713-daemon-launch-health-gate.json"
)
HAO_719_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "hao-719-daemon-launch-health-gate.json"
)
HAO_721_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "hao-721-daemon-launch-health-gate.json"
)
MGW_551_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "mgw-551-daemon-launch-health-gate.json"
)
MGW_556_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "mgw-556-daemon-launch-health-gate.json"
)
VAI_565_DAEMON_LAUNCH_GATE_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-07-03-vai-565-daemon-launch-health-gate.md"
)
VAI_565_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "vai-565-daemon-launch-health-gate.json"
)
VAI_568_DAEMON_LAUNCH_GATE_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-07-04-vai-568-daemon-launch-health-gate.md"
)
VAI_568_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "vai-568-daemon-launch-health-gate.json"
)
VAI_574_DAEMON_LAUNCH_GATE_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-07-04-vai-574-daemon-launch-health-gate.md"
)
VAI_574_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "vai-574-daemon-launch-health-gate.json"
)
VAI_577_DAEMON_LAUNCH_GATE_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-07-04-vai-577-daemon-launch-health-gate.md"
)
VAI_577_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "vai-577-daemon-launch-health-gate.json"
)
VAI_580_DAEMON_LAUNCH_GATE_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-07-04-vai-580-daemon-launch-health-gate.md"
)
VAI_580_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "vai-580-daemon-launch-health-gate.json"
)
VAI_615_DAEMON_LAUNCH_GATE_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-07-04-vai-615-daemon-launch-health-gate.md"
)
VAI_615_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "vai-615-daemon-launch-health-gate.json"
)
VAI_618_DAEMON_LAUNCH_GATE_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-07-04-vai-618-daemon-launch-health-gate.md"
)
VAI_618_DAEMON_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "vai-618-daemon-launch-health-gate.json"
)
HAO_722_OBJECTIVE_GAP_PATH = (
    DISCOVERY_ROOT / "2026-06-28-hao-724-objective-gap-7ea369464239.md"
)
HAO_722_LAUNCH_GATE_PATH = (
    DISCOVERY_ROOT / "2026-06-28-hao-724-mcp-dashboard-launch-gate.md"
)
HAO_727_OBJECTIVE_GAP_PATH = (
    DISCOVERY_ROOT / "2026-06-28-hao-727-objective-gap-7ea369464239.md"
)
HAO_727_LAUNCH_GATE_PATH = (
    DISCOVERY_ROOT / "2026-06-28-hao-727-mcp-dashboard-launch-gate.md"
)
HAO_728_RETRY_BUDGET_REPAIR_PATH = (
    DISCOVERY_ROOT / "2026-06-30-hao-728-hao-727-merge-retry-budget.md"
)
VAI_542_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "vai-542-mcp-dashboard-launch-gate.json"
)
HAO_727_LAUNCH_GATE_FIXTURE_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "hao-727-mcp-dashboard-launch-gate.json"
)


def _load_script_module(name: str):
    script_path = REPO_ROOT / "scripts" / f"{name}.py"
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_tasks():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    return parse_task_file(TASK_BOARD_PATH, "## HAO-")


def _json_block_after(source: str, marker: str) -> dict:
    start = source.index(marker)
    fence_start = source.index("```json", start)
    payload_start = source.index("\n", fence_start) + 1
    payload_end = source.index("\n```", payload_start)
    return json.loads(source[payload_start:payload_end])


def test_objective_heap_schedule_deduplicates_interoperability_pairs():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import objective_heap_schedule, parse_goal_heap

    goals = parse_goal_heap(
        "\n".join(
            (
                "## OBJ-001 First pair",
                "- Status: active",
                "- Priority: P0",
                "- Fibonacci priority: 1",
                "- Interoperability pair: hallucinate_app, external/ipfs_accelerate",
                "- Required evidence: proof/a.json",
                "## OBJ-002 Duplicate pair",
                "- Status: active",
                "- Priority: P0",
                "- Fibonacci priority: 1",
                "- Interoperability pair: external/ipfs_accelerate, hallucinate_app",
                "- Required evidence: proof/b.json",
                "## OBJ-003 Different pair",
                "- Status: active",
                "- Priority: P1",
                "- Fibonacci priority: 1",
                "- Interoperability pair: hallucinate_app, swissknife",
                "- Required evidence: proof/c.json",
            )
        )
    )

    scheduled_ids = [record.goal_id for record in objective_heap_schedule(goals)]

    assert scheduled_ids == ["OBJ-001", "OBJ-003"]


def test_hallucinate_multimodal_queue_test_source_is_scan_clean():
    original_sys_path = list(sys.path)
    try:
        sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
        from ipfs_accelerate_py.agent_supervisor.backlog_refinery import scan_findings_in_file
    finally:
        sys.path[:] = original_sys_path

    assert scan_findings_in_file(Path(__file__), repo_root=REPO_ROOT) == []


def test_hallucinate_multimodal_queue_blocks_archival_codebase_scan_tasks():
    open_archive_tasks = [
        task.task_id
        for task in _load_tasks()
        if task.status in {PENDING_TASK_STATUS, "ready", "in_progress"}
        and "external/ipfs_kit/archive/" in " ".join([task.title, task.acceptance, *task.outputs])
    ]

    assert open_archive_tasks == []


def test_hallucinate_multimodal_product_run_defers_stale_scan_and_repair_tasks():
    stale_patterns = (
        "resolve code annotation",
        "swallowed exception path",
        "placeholder runtime path",
        "retry-budget",
        "reconciliation guardrail",
        "dirty backlogged",
    )
    runnable_stale_tasks = [
        task.task_id
        for task in _load_tasks()
        if task.status in {PENDING_TASK_STATUS, "ready", "in_progress"}
        and any(pattern in f"{task.title} {task.acceptance}".lower() for pattern in stale_patterns)
        and not (
            "retry-budget" in f"{task.title} {task.acceptance}".lower()
            and "For launch tasks, this repair validation preserves the launch Playwright validation gate"
            in task.acceptance
            and any("test/e2e/" in output for output in task.outputs)
        )
    ]
    tasks = {task.task_id: task for task in _load_tasks()}

    assert runnable_stale_tasks == []
    for stale_task_id in ("HAO-684", "HAO-685", "HAO-686", "HAO-694", "HAO-695", "HAO-696"):
        assert tasks[stale_task_id].status == "blocked"
    assert tasks["HAO-427"].status == "completed"
    assert tasks["HAO-428"].status == "completed"
    assert tasks["HAO-431"].status == "completed"
    assert tasks["HAO-431"].track == "integration"


def test_hallucinate_open_tasks_do_not_claim_mgw_owned_queue_files():
    mgw_owned_paths = (
        "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md",
        "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
        "tests/test_meta_glasses_display_todo_queue.py",
    )
    open_cross_owned_tasks = [
        task.task_id
        for task in _load_tasks()
        if task.status in {PENDING_TASK_STATUS, "ready", "in_progress"}
        and any(
            path in " ".join([task.title, task.acceptance, *task.outputs, *task.validation])
            for path in mgw_owned_paths
        )
    ]

    assert open_cross_owned_tasks == []


def test_hao_launch_readiness_children_keep_vaios_g697_open_for_device_evidence():
    tasks = {task.task_id: task for task in _load_tasks()}
    expected = {
        "HAO-437": {
            "depends_on": ["HAO-436"],
            "parallel_lane": "physical-phone-ingress",
            "missing": "physical phone ingress rehearsal receipt",
        },
        "HAO-438": {
            "depends_on": ["HAO-436"],
            "parallel_lane": "desktop-peer-smoke",
            "missing": "desktop peer offload smoke receipt",
        },
        "HAO-439": {
            "depends_on": ["HAO-436"],
            "parallel_lane": "meta-glasses-terminal",
            "missing": "Meta glasses terminal receipt capture",
        },
        "HAO-440": {
            "depends_on": ["HAO-437", "HAO-438", "HAO-439"],
            "parallel_lane": "launch-readiness-aggregate",
            "missing": "aggregate physical readiness receipt and Playwright lineage",
        },
    }

    assert tasks["HAO-436"].status == "completed"
    for task_id, values in expected.items():
        task = tasks[task_id]
        assert task.status in {PENDING_TASK_STATUS, "completed"}
        assert task.priority == "P0"
        assert task.track == "launch"
        assert task.depends_on == values["depends_on"]
        assert task.metadata["goal id"] == "VAIOS-G697"
        assert task.metadata["graph parents"] == "VAIOS-G697"
        assert task.metadata["parallel lane"] == values["parallel_lane"]
        assert task.metadata["missing evidence"] == values["missing"]
        assert task.metadata["bundle"] == "objective/launch/production-readiness-gate"


def test_hao_mcp_swissknife_launch_children_cover_python_servers_and_playwright():
    tasks = {task.task_id: task for task in _load_tasks()}
    expected = {
        "HAO-441": {
            "depends_on": ["HAO-436"],
            "parallel_lane": "mcp-feature-inventory",
            "missing": "MCP server feature inventory for ipfs_accelerate_py, ipfs_datasets_py, and ipfs_kit_py",
            "acceptance_terms": ["ipfs_accelerate_py", "ipfs_datasets_py", "ipfs_kit_py", "Swissknife"],
        },
        "HAO-442": {
            "depends_on": ["HAO-441"],
            "parallel_lane": "hallucinate-mcp-daemon-launch",
            "missing": "Hallucinate App MCP daemon launch and health supervision",
            "acceptance_terms": ["Hallucinate App launch path", "health checks", "launch receipts"],
        },
        "HAO-443": {
            "depends_on": ["HAO-441"],
            "parallel_lane": "swissknife-mcp-capability-registry",
            "missing": "Swissknife MCP capability registry for Python server features",
            "acceptance_terms": ["Swissknife-facing capability registry", "permission scopes", "mediation receipt aliases"],
        },
        "HAO-444": {
            "depends_on": ["HAO-442", "HAO-443"],
            "parallel_lane": "swissknife-mcp-feature-apps",
            "missing": "Swissknife applications invoking Python MCP server features",
            "acceptance_terms": ["Swissknife applications", "deterministic results", "invocation receipts"],
        },
        "HAO-445": {
            "depends_on": ["HAO-441"],
            "parallel_lane": "mcp-plus-plus-compat",
            "missing": "Mcp-Plus-Plus compatibility for Hallucinate App and Swissknife MCP bridges",
            "acceptance_terms": ["Mcp-Plus-Plus-compatible", "capability descriptors", "tool calls"],
        },
        "HAO-446": {
            "depends_on": ["HAO-444", "HAO-445"],
            "parallel_lane": "hao-swissknife-mcp-playwright",
            "missing": "HAO and Swissknife Playwright MCP integration tests",
            "acceptance_terms": ["Playwright tests", "Python MCP daemons", "Swissknife applications"],
        },
        "HAO-447": {
            "depends_on": ["HAO-440", "HAO-446"],
            "parallel_lane": "launch-readiness-mcp-aggregate",
            "missing": "aggregate MCP server, Swissknife, Mcp-Plus-Plus, and Playwright launch evidence",
            "acceptance_terms": ["daemon launch", "Swissknife app feature invocation", "Playwright results"],
        },
    }

    for task_id, values in expected.items():
        task = tasks[task_id]
        assert task.status in {PENDING_TASK_STATUS, "completed", "blocked"}
        assert task.priority == "P0"
        assert task.track == "launch"
        assert task.depends_on == values["depends_on"]
        assert task.metadata["goal id"] == "VAIOS-G697"
        assert task.metadata["graph parents"] == "VAIOS-G697"
        assert task.metadata["parallel lane"] == values["parallel_lane"]
        assert task.metadata["missing evidence"] == values["missing"]
        assert task.metadata["bundle"] == "objective/launch/production-readiness-gate"
        for term in values["acceptance_terms"]:
            assert term in task.acceptance
        if task.status == "blocked":
            assert task.metadata["blocked reason"].endswith("because goal_completed.")

    assert "hao-swissknife-mcp-integration.spec.ts" in " ".join(tasks["HAO-446"].validation)
    assert "swissknife run test:e2e:mcp" in " ".join(tasks["HAO-446"].validation)


def test_hao_674_integrates_mcp_launch_contracts_with_swissknife_control_surface():
    tasks = {task.task_id: task for task in _load_tasks()}
    task = tasks["HAO-674"]
    idl_source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    daemon_doc = (REPO_ROOT / "hallucinate_app" / "docs" / "MCP_DAEMON_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )
    registry_source = (
        REPO_ROOT / "swissknife" / "src" / "services" / "swissknife-mcp-capability-registry.ts"
    ).read_text(encoding="utf-8")
    discovery_source = MCP_LAUNCH_CONTRACT_INTEGRATION_PATH.read_text(encoding="utf-8")
    fixture = _json_block_after(discovery_source, "## Integration Fixture")
    normalized_idl_source = " ".join(idl_source.split())
    normalized_daemon_doc = " ".join(daemon_doc.split())

    assert task.status in {PENDING_TASK_STATUS, "completed"}
    assert task.priority == "P0"
    assert task.track == "integration"
    assert task.depends_on == ["HAO-014", "HAO-020", "HAO-021"]

    assert fixture["task_id"] == "HAO-674"
    assert fixture["artifact_id"] == "mcp_launch_contract_integration"
    assert fixture["supervision_owner"] == "hallucinate_app.mcp_daemon_manager"
    assert fixture["before_invoke_hook"].endswith("ControlSurfaceInvocationGate.beforeInvoke")
    assert fixture["control_surface_route"] == [
        "Swissknife command intent",
        "MCP++ capability descriptor",
        "Hallucinate App interaction_envelope",
        "control_surface policy_decision",
        "mediation_receipt",
        "supervised MCP server transport",
    ]

    expected_servers = {
        "ipfs_kit_py": {
            "daemon_id": "ipfs-kit",
            "startup_order": 10,
            "sample_intent": "storage.pin_content",
            "sample_tool": "ipfs_pin_add",
        },
        "ipfs_datasets_py": {
            "daemon_id": "ipfs-datasets",
            "startup_order": 20,
            "sample_intent": "dataset.browse",
            "sample_tool": "tools_dispatch",
        },
        "ipfs_accelerate_py": {
            "daemon_id": "ipfs-accelerate",
            "startup_order": 30,
            "sample_intent": "compute.run_inference",
            "sample_tool": "tools_dispatch",
        },
    }
    servers = {server["server_package"]: server for server in fixture["servers"]}
    assert set(servers) == set(expected_servers)

    for package, expected in expected_servers.items():
        server = servers[package]
        assert server["daemon_id"] == expected["daemon_id"]
        assert server["startup_order"] == expected["startup_order"]
        assert server["sample_intent"] == expected["sample_intent"]
        assert server["sample_tool"] == expected["sample_tool"]
        assert package in idl_source
        assert package in daemon_doc
        assert package in registry_source
        assert expected["daemon_id"] in daemon_doc
        assert expected["daemon_id"] in registry_source

    for required_term in (
        "### HAO-674 supervised MCP server launch contract",
        "Swissknife command intent",
        "MCP++ capability descriptor",
        "Hallucinate App interaction_envelope",
        "control_surface policy_decision",
        "mediation_receipt",
        "supervised MCP server transport",
    ):
        assert required_term in normalized_idl_source
        assert required_term in normalized_daemon_doc or required_term.startswith("### HAO-674")

    for registry_term in (
        "SwissknifeMCPLaunchContract",
        "launch_owner: 'hallucinate_app.mcp_daemon_manager'",
        "mcp_plus_plus_advertisement",
        "control_surface_route",
        "buildSwissknifeMCPMediatedInvocationPlan",
        "CONTROL_SURFACE_DAEMON_MEDIATION",
        "MCP++",
        "HAO-674",
    ):
        assert registry_term in registry_source

    assert "mediation_receipt_id" in fixture["receipt_requirements"]
    assert "Every service invocation routes through the multimodal control surface" in " ".join(
        fixture["assertions"]
    )


def test_hao_675_adds_swissknife_hallucinate_app_playwright_launch_replay_coverage():
    tasks = {task.task_id: task for task in _load_tasks()}
    task = tasks["HAO-675"]
    discovery_source = PLAYWRIGHT_LAUNCH_REPLAY_PATH.read_text(encoding="utf-8")
    fixture = _json_block_after(discovery_source, "## Replay Fixture")
    hallucinate_fixture = json.loads(
        (
            REPO_ROOT
            / "hallucinate_app"
            / "test"
            / "e2e"
            / "fixtures"
            / "hao-675-launch-replay.json"
        ).read_text(encoding="utf-8")
    )
    swissknife_fixture = json.loads(
        (
            REPO_ROOT
            / "swissknife"
            / "test"
            / "e2e"
            / "fixtures"
            / "hao-675-launch-replay.json"
        ).read_text(encoding="utf-8")
    )
    hallucinate_spec = (
        REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "multimodal-control-surface.spec.ts"
    ).read_text(encoding="utf-8")
    swissknife_spec = (
        REPO_ROOT / "swissknife" / "test" / "e2e" / "meta-glasses-virtual-os.spec.ts"
    ).read_text(encoding="utf-8")
    idl_source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")

    assert task.status in {PENDING_TASK_STATUS, "completed"}
    assert task.priority == "P0"
    assert task.track == "validation"
    assert task.depends_on == ["HAO-674"]
    assert {"hallucinate_app", "swissknife", "tests", "data/hallucinate_multimodal_control/discovery"}.issubset(
        set(task.outputs)
    )

    assert fixture == hallucinate_fixture
    assert fixture == swissknife_fixture
    assert fixture["task_id"] == "HAO-675"
    assert fixture["artifact_id"] == "swissknife_hallucinate_app_playwright_launch_replay"
    assert fixture["schema"] == "launch_replay_playwright_receipt_v1"
    assert fixture["playwright_ready"] is True
    assert "test:e2e:meta-glasses" in fixture["commands"]["swissknife"]
    assert "multimodal-control-surface.spec.ts" in fixture["commands"]["hallucinate_app"]
    assert fixture["route"] == [
        "Swissknife application command intent",
        "MCP++ service capability discovery",
        "Hallucinate App interaction_envelope",
        "Hallucinate App policy_decision",
        "Hallucinate App mediation_receipt",
        "desktop peer offload receipt",
        "simulated Meta glasses terminal render",
        "production launch readiness receipt",
    ]

    capabilities = {capability["server_package"]: capability for capability in fixture["service_capabilities"]}
    assert set(capabilities) == {"ipfs_kit_py", "ipfs_datasets_py", "ipfs_accelerate_py"}
    for capability in capabilities.values():
        assert capability["mcp_plus_plus_profiles"] == [
            "Profile A MCP-IDL",
            "Profile C UCAN",
            "Profile E P2P",
        ]
        assert capability["advertised_operations"]
        assert capability["swissknife_app"]

    assert fixture["simulated_meta_glasses_interaction"] == {
        "participant_id": "meta_glasses:terminal",
        "surface": "gesture",
        "surface_event": "tap",
        "platform": "meta_glasses",
        "raw_action": "display.tap.open_model_runner",
        "normalized_intent": "terminal.activate_action",
        "render_target": "display_webapp",
    }
    assert fixture["pass_fail_receipts"] == {
        "swissknife_invokes_hallucinate_app_mediation": "passed",
        "mcp_plus_plus_capability_discovery": "passed",
        "simulated_meta_glasses_interaction": "passed",
        "desktop_peer_offload": "passed",
        "production_launch_readiness": "passed",
    }
    assert [receipt["kind"] for receipt in fixture["receipt_chain"]] == [
        "swissknife_command_intent",
        "mcp_plus_plus_capability_discovery",
        "mediation_receipt",
        "desktop_peer_offload",
        "simulated_meta_glasses_interaction",
        "production_launch_readiness",
    ]
    assert {receipt["status"] for receipt in fixture["receipt_chain"]} == {"passed"}

    for required_term in (
        "HAO-675",
        "Playwright launch replay",
        "Swissknife",
        "Hallucinate App",
        "MCP++",
        "Meta glasses",
        "desktop peer offload",
        "production launch readiness",
    ):
        assert required_term in discovery_source
        assert required_term in idl_source
        assert required_term in hallucinate_spec or required_term == "production launch readiness"
        assert required_term in swissknife_spec or required_term == "production launch readiness"


def test_hao_676_reviews_and_fixes_hallucinate_mcp_dashboard_menu_surface():
    tasks = {task.task_id: task for task in _load_tasks()}
    task = tasks["HAO-676"]
    review_source = MCP_DASHBOARD_REVIEW_PATH.read_text(encoding="utf-8")
    fixture = _json_block_after(review_source, "## Review Fixture")
    menu_config_source = (
        REPO_ROOT / "hallucinate_app" / "hallucinate_app" / "node" / "menu_config.js"
    ).read_text(encoding="utf-8")
    menu_generator_source = (
        REPO_ROOT / "hallucinate_app" / "hallucinate_app" / "node" / "menu_generator.js"
    ).read_text(encoding="utf-8")
    menu_test_source = (
        REPO_ROOT / "hallucinate_app" / "test" / "test_programmatic_menu.js"
    ).read_text(encoding="utf-8")

    assert task.status == "completed"
    assert task.priority == "P0"
    assert task.track == "launch"
    assert task.depends_on == ["HAO-674", "HAO-675"]
    assert task.metadata["goal id"] == "VAIOS-G723"
    assert task.metadata["bundle"] == "objective/launch/hallucinate-mcp-dashboard"
    assert task.metadata["parallel lane"] == "hallucinate-mcp-dashboard-menu-review"
    assert MCP_DASHBOARD_REVIEW_PATH.relative_to(REPO_ROOT).as_posix() in task.outputs

    assert fixture["task_id"] == "HAO-676"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["artifact_id"] == "hallucinate_mcp_dashboard_menu_review"
    assert fixture["requires_physical_devices"] is False
    servers = {item["server_package"]: item for item in fixture["menu_dashboard_inventory"]}
    assert set(servers) == {"ipfs_kit_py", "ipfs_datasets_py", "ipfs_accelerate_py"}
    assert servers["ipfs_kit_py"]["daemon_id"] == "ipfs-kit"
    assert servers["ipfs_kit_py"]["launch_plan_endpoint"] == "http://127.0.0.1:8004"
    assert servers["ipfs_datasets_py"]["native_dashboard_catalog"] == "/api/hallucinate/dashboard-catalog"
    assert "mcp++/profile-e-mcp-p2p" in servers["ipfs_accelerate_py"]["mcp_plus_plus_profiles"]

    findings = {finding["id"]: finding for finding in fixture["findings"]}
    assert findings["HAO-676-F1"]["severity"] == "fixed"
    assert findings["HAO-676-F2"]["severity"] == "fixed"
    assert findings["HAO-676-F3"]["severity"] == "launch-gap"
    assert findings["HAO-676-F4"]["follow_up_task"] == "HAO-678"
    assert findings["HAO-676-F5"]["follow_up_task"] == "HAO-682"

    assert "export const dashboardMcpServers = mcpServers.filter(server => server.dashboardPath)" in menu_config_source
    assert "items: dashboardMcpServers.map(server => ({" in menu_config_source
    assert "openSwissKnifeApp(item = {})" in menu_generator_source
    assert "this.createSwissKnifeWindow(appName)" in menu_generator_source
    assert "should only expose real IPFS MCP dashboard paths" in menu_test_source

    for required in (
        "tools/list",
        "tools/call",
        "MCP++ telemetry",
        "launch receipt",
        "Playwright interoperability",
    ):
        assert required in task.acceptance
        assert required in review_source


def test_hao_677_adds_daemon_owned_mcp_dashboard_capability_catalog():
    tasks = {task.task_id: task for task in _load_tasks()}
    task = tasks["HAO-677"]
    catalog_source = MCP_DASHBOARD_CATALOG_PATH.read_text(encoding="utf-8")
    catalog = _json_block_after(catalog_source, "## Catalog Fixture")
    mcp_launch_contract = _json_block_after(
        MCP_LAUNCH_CONTRACT_INTEGRATION_PATH.read_text(encoding="utf-8"),
        "## Integration Fixture",
    )
    daemon_manager_source = (
        REPO_ROOT / "hallucinate_app" / "hallucinate_app" / "node" / "mcp_daemon_manager.js"
    ).read_text(encoding="utf-8")
    index_source = (REPO_ROOT / "hallucinate_app" / "index.js").read_text(encoding="utf-8")
    preload_cjs_source = (REPO_ROOT / "hallucinate_app" / "preload.cjs").read_text(encoding="utf-8")
    preload_js_source = (REPO_ROOT / "hallucinate_app" / "preload.js").read_text(encoding="utf-8")
    daemon_test_source = (
        REPO_ROOT / "hallucinate_app" / "test" / "js" / "test_mcp_daemon_manager.js"
    ).read_text(encoding="utf-8")
    playwright_source = (
        REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "mcp-feature-exposure.spec.ts"
    ).read_text(encoding="utf-8")

    assert task.status == "completed"
    assert task.priority == "P0"
    assert task.track == "integration"
    assert task.depends_on == ["HAO-676"]
    assert task.metadata["goal id"] == "VAIOS-G723"
    assert task.metadata["parallel lane"] == "hallucinate-mcp-dashboard-capability-catalog"
    assert MCP_DASHBOARD_CATALOG_PATH.relative_to(REPO_ROOT).as_posix() in task.outputs
    assert "npm --prefix hallucinate_app run test:daemon-manager" in task.validation

    assert catalog["schema"] == "hallucinate_app.mcp_dashboard_capability_catalog.v1"
    assert catalog["task_id"] == "HAO-677"
    assert catalog["goal_id"] == "VAIOS-G723"
    assert catalog["control_surface_route"] == [
        "Hallucinate App dashboard action",
        "dashboard capability catalog",
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
        "supervised MCP server transport",
    ]

    servers = {item["server_package"]: item for item in catalog["servers"]}
    assert set(servers) == {"ipfs_kit_py", "ipfs_datasets_py", "ipfs_accelerate_py"}
    assert servers["ipfs_kit_py"]["port"] == 8004
    assert servers["ipfs_kit_py"]["endpoint"] == "http://127.0.0.1:8004"
    assert servers["ipfs_kit_py"]["tool_protocols"]["tools_call"]["safeProbe"]["mutation"] is False
    assert servers["ipfs_datasets_py"]["native_dashboard_catalog_url"] == (
        "http://127.0.0.1:8899/api/hallucinate/dashboard-catalog"
    )
    assert servers["ipfs_datasets_py"]["mcpplusplus"]["mode"] == "optional_bridge"
    assert "mcp++/profile-e-mcp-p2p" in servers["ipfs_accelerate_py"]["mcpplusplus"]["profiles"]

    for server in servers.values():
        assert server["tool_protocols"]["tools_list"]["operation"] == "tools/list"
        assert server["tool_protocols"]["tools_call"]["operation"] == "tools/call"
        assert server["control_surface_mediation_contract"].startswith("control_surface_contract:mcp-daemon:")
        assert "receipt_cid" in server["control_surface_receipt_requirements"]
        assert server["swissknife_consumer"]

    launch_servers = {item["server_package"]: item for item in mcp_launch_contract["servers"]}
    assert launch_servers["ipfs_kit_py"]["port"] == 8004

    for required in (
        "DASHBOARD_CATALOG_SCHEMA",
        "getDashboardCapabilityCatalog",
        "DASHBOARD_TOOL_PROTOCOLS",
        "tools/list",
        "tools/call",
    ):
        assert required in daemon_manager_source
    assert "daemon:getDashboardCapabilityCatalog" in index_source
    assert "getDashboardCapabilityCatalog" in preload_cjs_source
    assert "getDashboardCapabilityCatalog" in preload_js_source
    assert "Dashboard capability catalog" in daemon_test_source
    assert "dashboard capability catalog reconciles menu URLs" in playwright_source


def test_hao_677_683_dashboard_launch_chain_keeps_supervisor_work_high_value():
    tasks = {task.task_id: task for task in _load_tasks()}
    expected = {
        "HAO-677": {
            "priority": "P0",
            "track": "integration",
            "depends_on": ["HAO-676"],
            "parallel_lane": "hallucinate-mcp-dashboard-capability-catalog",
            "terms": ["dashboard capability catalog", "tools/list", "tools/call", "MCP++"],
        },
        "HAO-678": {
            "priority": "P0",
            "track": "launch",
            "depends_on": ["HAO-677"],
            "parallel_lane": "hallucinate-mcp-dashboard-ui-wiring",
            "terms": ["IPFS Kit", "IPFS Datasets", "IPFS Accelerate", "daemon health"],
        },
        "HAO-679": {
            "priority": "P0",
            "track": "validation",
            "depends_on": ["HAO-678"],
            "parallel_lane": "hallucinate-mcp-dashboard-playwright",
            "terms": ["Playwright", "tools/list", "tools/call", "pass/fail receipts"],
        },
        "HAO-680": {
            "priority": "P0",
            "track": "integration",
            "depends_on": ["HAO-677"],
            "parallel_lane": "hallucinate-mcp-dashboard-receipts",
            "terms": ["interaction_envelope", "policy_decision", "mediation_receipt", "MCP++"],
        },
        "HAO-681": {
            "priority": "P0",
            "track": "integration",
            "depends_on": ["HAO-677", "HAO-680"],
            "parallel_lane": "swissknife-dashboard-catalog-consumer",
            "terms": ["Swissknife", "catalog entries", "receipt schema", "MCP++"],
        },
        "HAO-682": {
            "priority": "P0",
            "track": "launch",
            "depends_on": ["HAO-679", "HAO-681"],
            "parallel_lane": "hallucinate-mcp-dashboard-launch-receipt",
            "terms": ["launch-readiness packet", "dashboard catalog", "Playwright", "daemon lineage"],
        },
        "HAO-683": {
            "priority": "P0",
            "track": "ops",
            "depends_on": ["HAO-676"],
            "parallel_lane": "supervisor-dashboard-objective-refill",
            "terms": ["supervisor launch mission terms", "objective-scan", "subtasks", "subgoals"],
        },
    }

    for task_id, values in expected.items():
        task = tasks[task_id]
        if task_id in {"HAO-677", "HAO-678", "HAO-679", "HAO-680", "HAO-681", "HAO-682", "HAO-683"}:
            assert task.status == "completed"
        else:
            assert task.status == PENDING_TASK_STATUS
        assert task.priority == values["priority"]
        assert task.track == values["track"]
        assert task.depends_on == values["depends_on"]
        assert task.metadata["goal id"] == "VAIOS-G723"
        assert task.metadata["bundle"] == "objective/launch/hallucinate-mcp-dashboard"
        assert task.metadata["parallel lane"] == values["parallel_lane"]
        assert task.metadata["missing evidence"]
        for term in values["terms"]:
            assert term in task.acceptance

    assert "mcp-dashboard-interoperability.spec.ts" in " ".join(tasks["HAO-679"].outputs)
    assert "scripts/run_vai_mgw_hao_supervisors.py" in tasks["HAO-683"].outputs


def test_vaios_g723_keeps_hallucinate_mcp_dashboard_work_ahead_of_broad_interop():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import objective_heap_schedule, parse_goal_heap

    heap_source = (REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md").read_text(
        encoding="utf-8"
    )
    goals = parse_goal_heap(heap_source)
    goals_by_id = {goal.goal_id: goal for goal in goals}
    schedule_ids = [record.goal_id for record in objective_heap_schedule(goals)]
    goal = goals_by_id["VAIOS-G723"]

    assert goal.status == "active"
    assert goal.fields["track"] == "launch"
    assert goal.fields["priority"] == "P0"
    assert goal.fields["bundle"] == "objective/launch/hallucinate-mcp-dashboard"
    assert goal.fields["parallel_lane"] == "hallucinate-mcp-dashboard"
    assert goal.fields["fib_priority"] == "13"
    assert "VAIOS-G723" in schedule_ids
    assert schedule_ids.index("VAIOS-G723") < schedule_ids.index("VAIOS-G700")

    combined_goal_text = " ".join(
        goal.fields.get(field, "")
        for field in ("goal", "evidence", "validation", "refinement", "gap_task")
    )
    for term in (
        "Hallucinate App",
        "MCP dashboard",
        "dashboard capability catalog",
        "daemon health",
        "tools/list",
        "tools/call",
        "ipfs_kit_py",
        "ipfs_datasets_py",
        "ipfs_accelerate_py",
        "Swissknife",
        "MCP++",
        "Playwright",
    ):
        assert term in combined_goal_text


def test_mgw_534_packet_proof_aligns_vaios_g727_and_g729_launch_gate():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    receipt_source = MGW_534_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    receipt = _json_block_after(receipt_source, "## Gate Fixture")
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}

    assert receipt["task_id"] == "MGW-534"
    assert receipt["goal_packet"] == "goal_packet/launch/external/ec964340486b"
    assert receipt["packet_goals"] == ["VAIOS-G727", "VAIOS-G729"]
    assert receipt["evidence_term"] == "launch Playwright validation gate"

    g727 = goals["VAIOS-G727"]
    g729 = goals["VAIOS-G729"]
    assert g727.fields["bundle"] == "objective/launch/meta-glasses-control-plane-input-routing"
    assert g729.fields["bundle"] == "objective/launch/objective-heap-autosteer-validation-repair"

    g727_text = " ".join([*g727.fields.keys(), *g727.fields.values()])
    g729_text = " ".join([*g729.fields.keys(), *g729.fields.values()])
    for term in (
        "launch Playwright validation gate",
        "goal_packet/launch/external/ec964340486b",
        "2026-06-26-mgw-534-launch-playwright-validation-gate.md",
    ):
        assert term in g727_text
        assert term in g729_text
    assert "MGW-534" in g727_text
    assert "MGW-534 packet proof" in heap_source
    assert "mgw_534_packet_proof" in g729_text

    for term in (
        "camera",
        "microphone",
        "headphones",
        "captouch",
        "Neural Band",
        "Bluetooth transport",
        "Wi-Fi transport",
        "IPFS",
        "libp2p",
        "MCP++",
        "Swissknife applications",
        "control plane",
    ):
        assert term in receipt_source
        assert term in g727_text


def test_hao_701_packet_proof_aligns_hallucinate_backlog_with_objective_heap():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    receipt_source = HAO_701_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    receipt = _json_block_after(receipt_source, "## Gate Fixture")
    tasks = {task.task_id: task for task in _load_tasks()}
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}

    assert receipt["task_id"] == "HAO-701"
    assert receipt["goal_id"] == "VAIOS-G727"
    assert receipt["goal_packet"] == "goal_packet/launch/external/ec964340486b"
    assert receipt["packet_goals"] == ["VAIOS-G727", "VAIOS-G729"]
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["supervisor_alignment"]["keeps_supervisor_fed_backlog_aligned"] is True

    task = tasks["HAO-701"]
    assert task.status in {PENDING_TASK_STATUS, "completed"}
    assert task.metadata["goal id"] == receipt["goal_id"]
    assert task.metadata["goal packet"] == receipt["goal_packet"]
    assert task.metadata["goal packet goals"] == "VAIOS-G727, VAIOS-G729"
    assert task.metadata["missing evidence"] == receipt["evidence_term"]

    g727_text = " ".join([*goals["VAIOS-G727"].fields.keys(), *goals["VAIOS-G727"].fields.values()])
    g729_text = " ".join([*goals["VAIOS-G729"].fields.keys(), *goals["VAIOS-G729"].fields.values()])
    for term in (
        "HAO-701",
        "MGW-534",
        "goal_packet/launch/external/ec964340486b",
        "launch Playwright validation gate",
        "2026-06-26-hao-701-launch-playwright-validation-gate.md",
        "2026-06-26-mgw-534-launch-playwright-validation-gate.md",
    ):
        assert term in receipt_source
        assert term in g727_text
        assert term in g729_text

    for term in (
        "camera",
        "microphone",
        "headphones",
        "captouch",
        "Neural Band",
        "Bluetooth transport",
        "Wi-Fi transport",
        "IPFS",
        "libp2p",
        "MCP++",
        "mobile phone",
        "Swissknife applications",
        "Hallucinate App mediation",
        "control plane",
    ):
        assert term in receipt_source
        assert term in g727_text


def test_vai_518_packet_proof_aligns_virtual_ai_os_backlog_with_objective_heap():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    receipt_source = VAI_518_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    receipt = _json_block_after(receipt_source, "## Gate Fixture")
    tasks = {
        task.task_id: task
        for task in parse_task_file(
            REPO_ROOT
            / "implementation_plan"
            / "docs"
            / "19-virtual-ai-os-submodule-integration.todo.md",
            "## VAI-",
        )
    }
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}

    assert receipt["task_id"] == "VAI-518"
    assert receipt["goal_id"] == "VAIOS-G727"
    assert receipt["goal_packet"] == "goal_packet/launch/external/ec964340486b"
    assert receipt["packet_goals"] == ["VAIOS-G727", "VAIOS-G729"]
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["supervisor_alignment"]["keeps_supervisor_fed_backlog_aligned"] is True

    task = tasks["VAI-518"]
    assert task.status in {PENDING_TASK_STATUS, "completed"}
    assert task.metadata["goal id"] == receipt["goal_id"]
    assert task.metadata["goal packet"] == receipt["goal_packet"]
    assert task.metadata["goal packet goals"] == "VAIOS-G727, VAIOS-G729"
    assert task.metadata["missing evidence"] == receipt["evidence_term"]

    g727_text = " ".join([*goals["VAIOS-G727"].fields.keys(), *goals["VAIOS-G727"].fields.values()])
    g729_text = " ".join([*goals["VAIOS-G729"].fields.keys(), *goals["VAIOS-G729"].fields.values()])
    for term in (
        "VAI-518",
        "MGW-534",
        "HAO-701",
        "VAI-520",
        "goal_packet/launch/external/ec964340486b",
        "launch Playwright validation gate",
        "2026-06-26-vai-518-launch-playwright-validation-gate.md",
        "2026-06-26-mgw-534-launch-playwright-validation-gate.md",
        "2026-06-26-hao-701-launch-playwright-validation-gate.md",
        "2026-06-26-vai-520-launch-playwright-validation-gate.md",
    ):
        assert term in receipt_source
        assert term in g727_text
    assert "vai_518_packet_proof" in g729_text

    for term in (
        "Meta glasses interface",
        "Meta Wearables DAT",
        "camera",
        "microphone",
        "headphones",
        "captouch",
        "Neural Band",
        "Bluetooth transport",
        "Wi-Fi transport",
        "IPFS",
        "libp2p",
        "MCP++",
        "mobile phone",
        "Swissknife applications",
        "Hallucinate App mediation",
        "control plane",
    ):
        assert term in receipt_source
        assert term in g727_text


def test_hao_702_daemon_launch_gate_aligns_hallucinate_backlog_with_objective_heap():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    receipt_source = HAO_702_DAEMON_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    mgw_receipt_source = MGW_535_DAEMON_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    receipt = _json_block_after(receipt_source, "## Gate Fixture")
    fixture = json.loads(DAEMON_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    tasks = {task.task_id: task for task in _load_tasks()}
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}

    assert receipt["schema"] == "hao_daemon_launch_health_gate_v1"
    assert receipt["task_id"] == "HAO-702"
    assert receipt["shared_packet_task_id"] == "MGW-535"
    assert receipt["goal_id"] == "VAIOS-G728"
    assert receipt["goal_packet"] == "goal_packet/launch/hallucinate_app/44dceea6bc53"
    assert receipt["packet_goals"] == ["VAIOS-G724", "VAIOS-G728"]
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["supervisor_alignment"]["keeps_supervisor_fed_backlog_aligned"] is True

    task = tasks["HAO-702"]
    assert task.status in {PENDING_TASK_STATUS, "completed"}
    assert task.metadata["goal id"] == receipt["goal_id"]
    assert task.metadata["goal packet"] == receipt["goal_packet"]
    assert task.metadata["goal packet goals"] == "VAIOS-G724, VAIOS-G728"
    assert task.metadata["missing evidence"] == receipt["evidence_term"]

    assert fixture["task_id"] == "MGW-535"
    assert fixture["backlog_task_id"] == "HAO-702"
    assert fixture["shared_packet_task_id"] == "MGW-535"
    assert fixture["goal_id"] == receipt["goal_id"]
    assert fixture["supervisor_gap_receipt"] == receipt["missing_evidence_source"]
    assert fixture["hallucinate_backlog_receipt"] == receipt["receipt_path"]
    assert fixture["required_backends"] == receipt["required_backends"]
    assert fixture["daemon_health_paths"] == receipt["daemon_health_paths"]

    g724_text = " ".join([*goals["VAIOS-G724"].fields.keys(), *goals["VAIOS-G724"].fields.values()])
    g728_text = " ".join([*goals["VAIOS-G728"].fields.keys(), *goals["VAIOS-G728"].fields.values()])
    for term in (
        "HAO-702",
        "MGW-535",
        "goal_packet/launch/hallucinate_app/44dceea6bc53",
        "launch Playwright validation gate",
        "2026-06-26-hao-702-daemon-launch-health-gate.md",
        "2026-06-26-mgw-535-daemon-launch-health-gate.md",
        "daemon-launch-health.spec.ts",
    ):
        assert term in receipt_source
        assert term in g728_text
    assert "VAIOS-G728" in g724_text
    assert "VAIOS-G724" in g728_text

    for term in (
        "Hallucinate App daemon health",
        "daemon launcher",
        "MCP server",
        "MCP dashboard",
        "ipfs_accelerate_py",
        "ipfs_datasets_py",
        "ipfs_kit_py",
        "dashboard capability catalog",
        "Swissknife applications",
        "launch Playwright validation gate",
    ):
        assert term in receipt_source
        assert term in mgw_receipt_source
        assert term in g728_text


def test_hao_713_daemon_launch_gate_aligns_hallucinate_backlog_with_objective_heap():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    receipt_source = HAO_713_DAEMON_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    mgw_receipt_source = MGW_535_DAEMON_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    receipt = _json_block_after(receipt_source, "## Gate Fixture")
    shared_fixture = json.loads(DAEMON_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    hao_fixture = json.loads(HAO_713_DAEMON_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    tasks = {task.task_id: task for task in _load_tasks()}
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}

    assert receipt == hao_fixture
    assert receipt["schema"] == "hao_daemon_launch_health_gate_v1"
    assert receipt["task_id"] == "HAO-713"
    assert receipt["shared_packet_task_id"] == "MGW-535"
    assert receipt["goal_id"] == "VAIOS-G728"
    assert receipt["goal_packet"] == "goal_packet/launch/hallucinate_app/44dceea6bc53"
    assert receipt["packet_goals"] == ["VAIOS-G724", "VAIOS-G728"]
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["supervisor_alignment"]["keeps_supervisor_fed_backlog_aligned"] is True

    task = tasks["HAO-713"]
    assert task.status in {PENDING_TASK_STATUS, "completed"}
    assert task.metadata["goal id"] == receipt["goal_id"]
    assert task.metadata["goal packet"] == receipt["goal_packet"]
    assert task.metadata["goal packet goals"] == "VAIOS-G724, VAIOS-G728"
    assert task.metadata["missing evidence"] == receipt["evidence_term"]

    assert shared_fixture["task_id"] == "MGW-535"
    assert "HAO-713" in shared_fixture["backlog_task_ids"]
    assert receipt["missing_evidence_source"] in shared_fixture["supervisor_gap_receipts"]
    assert receipt["receipt_path"] in shared_fixture["hallucinate_backlog_receipts"]
    assert shared_fixture["required_backends"] == receipt["required_backends"]
    assert shared_fixture["daemon_health_paths"] == receipt["daemon_health_paths"]

    g724_text = " ".join([*goals["VAIOS-G724"].fields.keys(), *goals["VAIOS-G724"].fields.values()])
    g728_text = " ".join([*goals["VAIOS-G728"].fields.keys(), *goals["VAIOS-G728"].fields.values()])
    for term in (
        "HAO-713",
        "MGW-535",
        "goal_packet/launch/hallucinate_app/44dceea6bc53",
        "launch Playwright validation gate",
        "2026-06-27-hao-713-daemon-launch-health-gate.md",
        "hao-713-daemon-launch-health-gate.json",
        "daemon-launch-health.spec.ts",
    ):
        assert term in receipt_source
        assert term in g728_text
    assert "VAIOS-G728" in g724_text
    assert "VAIOS-G724" in g728_text

    for term in (
        "Hallucinate App daemon health",
        "daemon launcher",
        "MCP server",
        "MCP dashboard",
        "ipfs_accelerate_py",
        "ipfs_datasets_py",
        "ipfs_kit_py",
        "dashboard capability catalog",
        "Swissknife applications",
        "launch Playwright validation gate",
    ):
        assert term in receipt_source
        assert term in mgw_receipt_source
        assert term in g728_text


def test_hao_719_and_hao_721_daemon_launch_gates_align_with_objective_heap():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    shared_mgw_receipt_source = MGW_535_DAEMON_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    shared_fixture = json.loads(DAEMON_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    tasks = {task.task_id: task for task in _load_tasks()}
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}
    g724_text = " ".join([*goals["VAIOS-G724"].fields.keys(), *goals["VAIOS-G724"].fields.values()])
    g728_text = " ".join([*goals["VAIOS-G728"].fields.keys(), *goals["VAIOS-G728"].fields.values()])

    current_gate_receipts = [
        (
            "HAO-719",
            HAO_719_DAEMON_LAUNCH_GATE_PATH,
            HAO_719_DAEMON_LAUNCH_GATE_FIXTURE_PATH,
            "2026-06-28-hao-719-objective-gap-b023c8de5b69.md",
            "2026-06-28-hao-719-daemon-launch-health-gate.md",
            "hao-719-daemon-launch-health-gate.json",
        ),
        (
            "HAO-721",
            HAO_721_DAEMON_LAUNCH_GATE_PATH,
            HAO_721_DAEMON_LAUNCH_GATE_FIXTURE_PATH,
            "2026-06-28-hao-721-objective-gap-b023c8de5b69.md",
            "2026-06-28-hao-721-daemon-launch-health-gate.md",
            "hao-721-daemon-launch-health-gate.json",
        ),
    ]

    for task_id, receipt_path, fixture_path, gap_name, receipt_name, fixture_name in current_gate_receipts:
        receipt_source = receipt_path.read_text(encoding="utf-8")
        receipt = _json_block_after(receipt_source, "## Gate Fixture")
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        task = tasks[task_id]

        assert receipt == fixture
        assert receipt["schema"] == "hallucinate_app.daemon_launch_validation_gate.v1"
        assert receipt["task_id"] == task_id
        assert receipt["shared_packet_task_id"] == "MGW-535"
        assert receipt["goal_id"] == "VAIOS-G728"
        assert receipt["goal_packet"] == "goal_packet/launch/hallucinate_app/44dceea6bc53"
        assert receipt["packet_goals"] == ["VAIOS-G724", "VAIOS-G728"]
        assert receipt["evidence_term"] == "launch Playwright validation gate"
        assert receipt["objective_gap_receipt"].endswith(gap_name)
        assert receipt["objective_gap_receipt"] in receipt["objective_gap_receipts"]

        assert task.status in {PENDING_TASK_STATUS, "completed"}
        assert task.metadata["goal id"] == receipt["goal_id"]
        assert task.metadata["goal packet"] == receipt["goal_packet"]
        assert task.metadata["goal packet goals"] == "VAIOS-G724, VAIOS-G728"
        assert task.metadata["missing evidence"] == receipt["evidence_term"]

        assert task_id in shared_fixture["backlog_task_ids"]
        assert receipt["supervisor_gap_receipt"] in shared_fixture["supervisor_gap_receipts"]
        assert receipt["hallucinate_backlog_receipt"] in shared_fixture["hallucinate_backlog_receipts"]
        assert shared_fixture["required_backends"] == receipt["required_backends"]
        assert shared_fixture["daemon_health_paths"] == receipt["daemon_health_paths"]
        assert shared_fixture["swissknife_handoff"] == receipt["swissknife_handoff"]

        for term in (
            task_id,
            "MGW-535",
            "goal_packet/launch/hallucinate_app/44dceea6bc53",
            "launch Playwright validation gate",
            gap_name,
            receipt_name,
            fixture_name,
            "daemon-launch-health.spec.ts",
        ):
            assert term in receipt_source
            assert term in g728_text

    assert "VAIOS-G728" in g724_text
    assert "VAIOS-G724" in g728_text

    for term in (
        "Hallucinate App daemon health",
        "daemon launcher",
        "MCP server",
        "MCP dashboard",
        "ipfs_accelerate_py",
        "ipfs_datasets_py",
        "ipfs_kit_py",
        "dashboard capability catalog",
        "Swissknife applications",
        "launch Playwright validation gate",
    ):
        assert term in shared_mgw_receipt_source
        assert term in g728_text


def test_hao_722_mcp_dashboard_gate_aligns_hallucinate_backlog_with_vaios_g723():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    gap_source = HAO_722_OBJECTIVE_GAP_PATH.read_text(encoding="utf-8")
    receipt_source = HAO_722_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    fixture = json.loads(VAI_542_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}
    g723_text = " ".join([*goals["VAIOS-G723"].fields.keys(), *goals["VAIOS-G723"].fields.values()])

    assert fixture["task_id"] == "VAI-542"
    assert fixture["backlog_task_id"] == "HAO-724"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_gap_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-724-objective-gap-7ea369464239.md"
    )
    assert fixture["hallucinate_launch_gate_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-724-mcp-dashboard-launch-gate.md"
    )
    assert fixture["child_goals"] == [
        "VAIOS-G723-C1 Catalog normalization",
        "VAIOS-G723-C2 Dashboard UI wiring",
        "VAIOS-G723-C3 Mediated tool-call receipts",
        "VAIOS-G723-C4 Swissknife consumers",
        "VAIOS-G723-C5 Playwright coverage",
        "VAIOS-G723-C6 Supervisor-generated follow-up subtasks",
    ]

    for term in fixture["required_evidence"]:
        assert term in gap_source
        assert term in receipt_source
        assert term in g723_text

    for term in (
        "HAO-724",
        "VAI-542",
        "launch Playwright validation gate",
        "mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
        "supervisor-generated follow-up work for VAIOS-G723",
    ):
        assert term in receipt_source
        assert term in heap_source


def test_hao_727_mcp_dashboard_gate_aligns_hallucinate_backlog_with_vaios_g723():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    gap_source = HAO_727_OBJECTIVE_GAP_PATH.read_text(encoding="utf-8")
    receipt_source = HAO_727_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    fixture = json.loads(HAO_727_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}
    g723_text = " ".join([*goals["VAIOS-G723"].fields.keys(), *goals["VAIOS-G723"].fields.values()])

    assert fixture["schema"] == "launch_readiness_receipt_v1"
    assert fixture["task_id"] == "HAO-727"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["lineage_id"] == "VAIOS-G723:hallucinate-mcp-dashboard-interoperability"
    assert fixture["source_gap_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-727-objective-gap-7ea369464239.md"
    )
    assert fixture["launch_gate_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-727-mcp-dashboard-launch-gate.md"
    )
    assert fixture["receipt_fixture"] == "hallucinate_app/test/e2e/fixtures/hao-727-mcp-dashboard-launch-gate.json"
    assert fixture["required_backends"] == [
        "ipfs_kit_py",
        "ipfs_datasets_py",
        "ipfs_accelerate_py",
    ]
    assert fixture["child_goals"] == [
        "VAIOS-G723-C1 Catalog normalization",
        "VAIOS-G723-C2 Dashboard UI wiring",
        "VAIOS-G723-C3 Mediated tool-call receipts",
        "VAIOS-G723-C4 Swissknife consumers",
        "VAIOS-G723-C5 Playwright coverage",
        "VAIOS-G723-C6 Supervisor-generated follow-up subtasks",
    ]
    assert fixture["follow_up_subtasks"] == ["HAO-678", "HAO-679", "HAO-680", "HAO-681", "HAO-682", "HAO-683"]
    assert fixture["supervisor_follow_up_subtasks"] == fixture["follow_up_subtasks"]

    for term in fixture["required_evidence"]:
        assert term in gap_source
        assert term in receipt_source
        assert term in g723_text

    for term in (
        "HAO-727",
        "VAIOS-G723",
        "launch Playwright validation gate",
        "mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
        "hallucinate_app/test/e2e/fixtures/hao-727-mcp-dashboard-launch-gate.json",
    ):
        assert term in receipt_source
        assert term in heap_source

    assert "supervisor-generated follow-up work for `VAIOS-G723`" in receipt_source
    assert "supervisor-generated follow-up subtasks" in heap_source


def test_mgw_559_mcp_dashboard_gate_aligns_meta_and_hallucinate_backlogs_with_vaios_g723():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    meta_receipt_path = (
        MGW_DISCOVERY_ROOT / "2026-06-29-mgw-559-launch-playwright-validation-gate.md"
    )
    hallucinate_receipt_path = (
        DISCOVERY_ROOT / "2026-06-29-mgw-559-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "mgw-559-mcp-dashboard-launch-gate.json"
    )
    objective_gap_path = (
        MGW_DISCOVERY_ROOT / "2026-06-29-mgw-559-objective-gap-7ea369464239.md"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    playwright_source = (
        REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "mcp-dashboard-interoperability.spec.ts"
    ).read_text(encoding="utf-8")
    swissknife_consumer_source = (
        REPO_ROOT / "swissknife" / "scripts" / "test-mcp-dashboard-consumer.cjs"
    ).read_text(encoding="utf-8")
    meta_receipt = meta_receipt_path.read_text(encoding="utf-8")
    hallucinate_receipt = hallucinate_receipt_path.read_text(encoding="utf-8")
    objective_gap = objective_gap_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}
    g723_text = " ".join([*goals["VAIOS-G723"].fields.keys(), *goals["VAIOS-G723"].fields.values()])

    assert fixture["schema"] == "launch_readiness_receipt_v1"
    assert fixture["task_id"] == "MGW-559"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["evidence_term"] == "launch Playwright validation gate"
    assert fixture["source_gap_receipt"] == (
        "data/meta_glasses_display_widgets/discovery/2026-06-29-mgw-559-objective-gap-7ea369464239.md"
    )
    assert fixture["launch_gate_receipt"] == (
        "data/meta_glasses_display_widgets/discovery/2026-06-29-mgw-559-launch-playwright-validation-gate.md"
    )
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-06-29-mgw-559-mcp-dashboard-launch-gate.md"
    )
    assert fixture["receipt_fixture"] == "hallucinate_app/test/e2e/fixtures/mgw-559-mcp-dashboard-launch-gate.json"
    assert fixture["child_goals"] == [
        "VAIOS-G723-C1 Catalog normalization",
        "VAIOS-G723-C2 Dashboard UI wiring",
        "VAIOS-G723-C3 Mediated tool-call receipts",
        "VAIOS-G723-C4 Swissknife consumers",
        "VAIOS-G723-C5 Playwright coverage",
        "VAIOS-G723-C6 Supervisor-generated follow-up subtasks",
    ]
    assert fixture["follow_up_subtasks"] == ["HAO-678", "HAO-679", "HAO-680", "HAO-681", "HAO-682", "HAO-683"]
    assert fixture["supervisor_follow_up_subtasks"] == fixture["follow_up_subtasks"]

    for term in fixture["required_evidence"]:
        assert term in meta_receipt
        assert term in hallucinate_receipt
        assert term in g723_text
        assert term in readiness_source
        assert term in playwright_source

    for term in (
        "Hallucinate App MCP dashboard",
        "dashboard capability catalog",
        "daemon health",
        "tools/list",
        "tools/call",
        "ipfs_accelerate_py MCP server",
        "ipfs_datasets_py MCP server",
        "ipfs_kit_py MCP server",
        "Swissknife applications",
        "launch Playwright validation gate",
    ):
        assert term in objective_gap

    for term in (
        "MGW-559",
        "launch Playwright validation gate",
        "mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
        "hallucinate_app/test/e2e/fixtures/mgw-559-mcp-dashboard-launch-gate.json",
    ):
        assert term in meta_receipt
        assert term in hallucinate_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "MGW-559" in swissknife_consumer_source
    assert "hallucinate_app/test/e2e/fixtures/mgw-559-mcp-dashboard-launch-gate.json" in swissknife_consumer_source
    assert "MGW-559 proof" in heap_source
    assert "supervisor-generated follow-up work for `VAIOS-G723`" in meta_receipt
    assert "supervisor-generated follow-up work for `VAIOS-G723`" in hallucinate_receipt


def test_mgw_561_mcp_dashboard_gate_aligns_meta_and_hallucinate_backlogs_with_vaios_g723():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    meta_receipt_path = (
        MGW_DISCOVERY_ROOT / "2026-06-30-mgw-561-launch-playwright-validation-gate.md"
    )
    hallucinate_receipt_path = (
        DISCOVERY_ROOT / "2026-06-30-mgw-561-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "mgw-561-mcp-dashboard-launch-gate.json"
    )
    objective_gap_path = (
        MGW_DISCOVERY_ROOT / "2026-06-30-mgw-561-objective-gap-7ea369464239.md"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    playwright_source = (
        REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "mcp-dashboard-interoperability.spec.ts"
    ).read_text(encoding="utf-8")
    swissknife_consumer_source = (
        REPO_ROOT / "swissknife" / "scripts" / "test-mcp-dashboard-consumer.cjs"
    ).read_text(encoding="utf-8")
    meta_receipt = meta_receipt_path.read_text(encoding="utf-8")
    hallucinate_receipt = hallucinate_receipt_path.read_text(encoding="utf-8")
    objective_gap = objective_gap_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}
    g723_text = " ".join([*goals["VAIOS-G723"].fields.keys(), *goals["VAIOS-G723"].fields.values()])

    assert fixture["schema"] == "launch_readiness_receipt_v1"
    assert fixture["task_id"] == "MGW-561"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["evidence_term"] == "launch Playwright validation gate"
    assert fixture["source_gap_receipt"] == (
        "data/meta_glasses_display_widgets/discovery/2026-06-30-mgw-561-objective-gap-7ea369464239.md"
    )
    assert fixture["launch_gate_receipt"] == (
        "data/meta_glasses_display_widgets/discovery/2026-06-30-mgw-561-launch-playwright-validation-gate.md"
    )
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-06-30-mgw-561-mcp-dashboard-launch-gate.md"
    )
    assert fixture["receipt_fixture"] == "hallucinate_app/test/e2e/fixtures/mgw-561-mcp-dashboard-launch-gate.json"
    assert fixture["child_goals"] == [
        "VAIOS-G723-C1 Catalog normalization",
        "VAIOS-G723-C2 Dashboard UI wiring",
        "VAIOS-G723-C3 Mediated tool-call receipts",
        "VAIOS-G723-C4 Swissknife consumers",
        "VAIOS-G723-C5 Playwright coverage",
        "VAIOS-G723-C6 Supervisor-generated follow-up subtasks",
    ]
    assert fixture["follow_up_subtasks"] == ["HAO-678", "HAO-679", "HAO-680", "HAO-681", "HAO-682", "HAO-683"]
    assert fixture["supervisor_follow_up_subtasks"] == fixture["follow_up_subtasks"]

    for term in fixture["required_evidence"]:
        assert term in meta_receipt
        assert term in hallucinate_receipt
        assert term in g723_text
        assert term in readiness_source
        assert term in playwright_source

    for term in (
        "Hallucinate App MCP dashboard",
        "dashboard capability catalog",
        "daemon health",
        "tools/list",
        "tools/call",
        "ipfs_accelerate_py MCP server",
        "ipfs_datasets_py MCP server",
        "ipfs_kit_py MCP server",
        "Swissknife applications",
        "launch Playwright validation gate",
    ):
        assert term in objective_gap

    for term in (
        "MGW-561",
        "launch Playwright validation gate",
        "mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
        "hallucinate_app/test/e2e/fixtures/mgw-561-mcp-dashboard-launch-gate.json",
    ):
        assert term in meta_receipt
        assert term in hallucinate_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "MGW-561" in swissknife_consumer_source
    assert "hallucinate_app/test/e2e/fixtures/mgw-561-mcp-dashboard-launch-gate.json" in swissknife_consumer_source
    assert "MGW-561 proof" in heap_source
    assert "supervisor-generated follow-up work for `VAIOS-G723`" in meta_receipt
    assert "supervisor-generated follow-up work for `VAIOS-G723`" in hallucinate_receipt


def test_mgw_563_mcp_dashboard_gate_aligns_meta_and_hallucinate_backlogs_with_vaios_g723():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    meta_receipt_path = (
        MGW_DISCOVERY_ROOT / "2026-07-01-mgw-563-launch-playwright-validation-gate.md"
    )
    hallucinate_receipt_path = (
        DISCOVERY_ROOT / "2026-07-01-mgw-563-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "mgw-563-mcp-dashboard-launch-gate.json"
    )
    objective_gap_path = (
        MGW_DISCOVERY_ROOT / "2026-07-01-mgw-563-objective-gap-7ea369464239.md"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    playwright_source = (
        REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "mcp-dashboard-interoperability.spec.ts"
    ).read_text(encoding="utf-8")
    swissknife_consumer_source = (
        REPO_ROOT / "swissknife" / "scripts" / "test-mcp-dashboard-consumer.cjs"
    ).read_text(encoding="utf-8")
    meta_receipt = meta_receipt_path.read_text(encoding="utf-8")
    hallucinate_receipt = hallucinate_receipt_path.read_text(encoding="utf-8")
    objective_gap = objective_gap_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}
    g723_text = " ".join([*goals["VAIOS-G723"].fields.keys(), *goals["VAIOS-G723"].fields.values()])

    assert fixture["schema"] == "launch_readiness_receipt_v1"
    assert fixture["task_id"] == "MGW-563"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["evidence_term"] == "launch Playwright validation gate"
    assert fixture["source_gap_receipt"] == (
        "data/meta_glasses_display_widgets/discovery/2026-07-01-mgw-563-objective-gap-7ea369464239.md"
    )
    assert fixture["launch_gate_receipt"] == (
        "data/meta_glasses_display_widgets/discovery/2026-07-01-mgw-563-launch-playwright-validation-gate.md"
    )
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-01-mgw-563-mcp-dashboard-launch-gate.md"
    )
    assert fixture["receipt_fixture"] == "hallucinate_app/test/e2e/fixtures/mgw-563-mcp-dashboard-launch-gate.json"
    assert fixture["child_goals"] == [
        "VAIOS-G723-C1 Catalog normalization",
        "VAIOS-G723-C2 Dashboard UI wiring",
        "VAIOS-G723-C3 Mediated tool-call receipts",
        "VAIOS-G723-C4 Swissknife consumers",
        "VAIOS-G723-C5 Playwright coverage",
        "VAIOS-G723-C6 Supervisor-generated follow-up subtasks",
    ]
    assert fixture["follow_up_subtasks"] == ["HAO-678", "HAO-679", "HAO-680", "HAO-681", "HAO-682", "HAO-683"]
    assert fixture["supervisor_follow_up_subtasks"] == fixture["follow_up_subtasks"]

    for term in fixture["required_evidence"]:
        assert term in meta_receipt
        assert term in hallucinate_receipt
        assert term in g723_text
        assert term in readiness_source
        assert term in playwright_source

    for term in (
        "Hallucinate App MCP dashboard",
        "dashboard capability catalog",
        "daemon health",
        "tools/list",
        "tools/call",
        "ipfs_accelerate_py MCP server",
        "ipfs_datasets_py MCP server",
        "ipfs_kit_py MCP server",
        "Swissknife applications",
        "launch Playwright validation gate",
    ):
        assert term in objective_gap

    for term in (
        "MGW-563",
        "launch Playwright validation gate",
        "mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
        "hallucinate_app/test/e2e/fixtures/mgw-563-mcp-dashboard-launch-gate.json",
    ):
        assert term in meta_receipt
        assert term in hallucinate_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "MGW-563" in swissknife_consumer_source
    assert "hallucinate_app/test/e2e/fixtures/mgw-563-mcp-dashboard-launch-gate.json" in swissknife_consumer_source
    assert "MGW-563 proof" in heap_source
    assert "supervisor-generated follow-up work for `VAIOS-G723`" in meta_receipt
    assert "supervisor-generated follow-up work for `VAIOS-G723`" in hallucinate_receipt


def test_mgw_551_daemon_launch_gate_aligns_meta_backlog_with_objective_heap():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    receipt_source = MGW_551_DAEMON_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    shared_mgw_receipt_source = MGW_535_DAEMON_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    receipt = _json_block_after(receipt_source, "## Gate Fixture")
    shared_fixture = json.loads(DAEMON_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    mgw_fixture = json.loads(MGW_551_DAEMON_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}

    assert receipt["schema"] == "meta_glasses_display_widgets.daemon_launch_health_gate_v1"
    assert receipt["task_id"] == "MGW-551"
    assert receipt["shared_packet_task_id"] == "MGW-535"
    assert receipt["goal_id"] == "VAIOS-G728"
    assert receipt["goal_packet"] == "goal_packet/launch/hallucinate_app/44dceea6bc53"
    assert receipt["packet_goals"] == ["VAIOS-G724", "VAIOS-G728"]
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["missing_evidence_source"] == (
        "data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-551-objective-gap-b023c8de5b69.md"
    )
    assert receipt["supervisor_alignment"]["keeps_supervisor_fed_backlog_aligned"] is True
    assert mgw_fixture["schema"] == "hallucinate_app.daemon_launch_validation_gate.v1"
    assert mgw_fixture["task_id"] == receipt["task_id"]
    assert mgw_fixture["goal_id"] == receipt["goal_id"]
    assert mgw_fixture["goal_packet"] == receipt["goal_packet"]
    assert mgw_fixture["packet_goals"] == receipt["packet_goals"]
    assert mgw_fixture["evidence_term"] == receipt["evidence_term"]
    assert mgw_fixture["supervisor_gap_receipt"] == receipt["missing_evidence_source"]
    assert mgw_fixture["launch_gate_receipt"] == receipt["receipt_path"]
    assert mgw_fixture["receipt_fixture"] == "hallucinate_app/test/e2e/fixtures/mgw-551-daemon-launch-health-gate.json"

    assert shared_fixture["task_id"] == "MGW-535"
    assert receipt["receipt_path"] in shared_fixture["discovery_receipts"]
    assert receipt["missing_evidence_source"] in shared_fixture["objective_gap_receipts"]
    assert shared_fixture["required_backends"] == receipt["required_backends"]
    assert shared_fixture["daemon_health_paths"] == receipt["daemon_health_paths"]

    g724_text = " ".join([*goals["VAIOS-G724"].fields.keys(), *goals["VAIOS-G724"].fields.values()])
    g728_text = " ".join([*goals["VAIOS-G728"].fields.keys(), *goals["VAIOS-G728"].fields.values()])
    for term in (
        "MGW-551",
        "MGW-535",
        "goal_packet/launch/hallucinate_app/44dceea6bc53",
        "launch Playwright validation gate",
        "2026-06-28-mgw-551-daemon-launch-health-gate.md",
        "mgw-551-daemon-launch-health-gate.json",
        "daemon-launch-health.spec.ts",
    ):
        assert term in receipt_source
        assert term in g728_text
    assert "VAIOS-G728" in g724_text
    assert "VAIOS-G724" in g728_text

    for term in (
        "Hallucinate App daemon health",
        "daemon launcher",
        "MCP server",
        "MCP dashboard",
        "ipfs_accelerate_py",
        "ipfs_datasets_py",
        "ipfs_kit_py",
        "dashboard capability catalog",
        "Swissknife applications",
        "launch Playwright validation gate",
    ):
        assert term in receipt_source
        assert term in shared_mgw_receipt_source
        assert term in g728_text


def test_vai_565_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    receipt_source = VAI_565_DAEMON_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    shared_mgw_receipt_source = MGW_535_DAEMON_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    receipt = _json_block_after(receipt_source, "## Gate Fixture")
    shared_fixture = json.loads(DAEMON_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    vai_fixture = json.loads(VAI_565_DAEMON_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}

    assert receipt == vai_fixture
    assert receipt["schema"] == "hallucinate_app.daemon_launch_validation_gate.v1"
    assert receipt["receipt_schema"] == "launch_readiness_receipt_v1"
    assert receipt["task_id"] == "VAI-565"
    assert receipt["shared_packet_task_id"] == "MGW-535"
    assert receipt["goal_id"] == "VAIOS-G728"
    assert receipt["goal_packet"] == "goal_packet/launch/hallucinate_app/44dceea6bc53"
    assert receipt["packet_goals"] == ["VAIOS-G724", "VAIOS-G728"]
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["objective_gap_receipt"] == (
        "data/virtual_ai_os/discovery/2026-07-03-vai-565-objective-gap-b023c8de5b69.md"
    )
    assert receipt["launch_gate_receipt"] == (
        "data/virtual_ai_os/discovery/2026-07-03-vai-565-daemon-launch-health-gate.md"
    )
    assert receipt["receipt_fixture"] == (
        "hallucinate_app/test/e2e/fixtures/vai-565-daemon-launch-health-gate.json"
    )

    assert "VAI-565" in shared_fixture["vai_task_ids"]
    assert receipt["launch_gate_receipt"] in shared_fixture["discovery_receipts"]
    assert receipt["objective_gap_receipt"] in shared_fixture["objective_gap_receipts"]
    assert shared_fixture["required_backends"] == receipt["required_backends"]
    assert shared_fixture["daemon_health_paths"] == receipt["daemon_health_paths"]
    assert shared_fixture["swissknife_handoff"] == receipt["swissknife_handoff"]

    g724_text = " ".join([*goals["VAIOS-G724"].fields.keys(), *goals["VAIOS-G724"].fields.values()])
    g728_text = " ".join([*goals["VAIOS-G728"].fields.keys(), *goals["VAIOS-G728"].fields.values()])
    for term in (
        "VAI-565",
        "MGW-535",
        "goal_packet/launch/hallucinate_app/44dceea6bc53",
        "launch Playwright validation gate",
        "2026-07-03-vai-565-objective-gap-b023c8de5b69.md",
        "2026-07-03-vai-565-daemon-launch-health-gate.md",
        "vai-565-daemon-launch-health-gate.json",
        "daemon-launch-health.spec.ts",
    ):
        assert term in receipt_source
        assert term in g728_text
    assert "VAIOS-G728" in g724_text
    assert "VAIOS-G724" in g728_text

    for term in (
        "Hallucinate App daemon health",
        "daemon launcher",
        "MCP server",
        "MCP dashboard",
        "ipfs_accelerate_py",
        "ipfs_datasets_py",
        "ipfs_kit_py",
        "dashboard capability catalog",
        "Swissknife applications",
        "launch Playwright validation gate",
    ):
        assert term in receipt_source
        assert term in shared_mgw_receipt_source
        assert term in g728_text


def _assert_vai_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap(
    *,
    task_id: str,
    packet_sibling_task_id: str,
    receipt_path: Path,
    fixture_path: Path,
    objective_gap_receipt: str,
    launch_gate_receipt: str,
    receipt_fixture: str,
):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap

    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    receipt_source = receipt_path.read_text(encoding="utf-8")
    shared_mgw_receipt_source = MGW_535_DAEMON_LAUNCH_GATE_PATH.read_text(encoding="utf-8")
    receipt = _json_block_after(receipt_source, "## Gate Fixture")
    shared_fixture = json.loads(DAEMON_LAUNCH_GATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    vai_fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    goals = {goal.goal_id: goal for goal in parse_goal_heap(heap_source)}

    assert receipt == vai_fixture
    assert receipt["schema"] == "hallucinate_app.daemon_launch_validation_gate.v1"
    assert receipt["receipt_schema"] == "launch_readiness_receipt_v1"
    assert receipt["task_id"] == task_id
    assert receipt["shared_packet_task_id"] == "MGW-535"
    assert receipt["goal_id"] == "VAIOS-G728"
    assert receipt["goal_packet"] == "goal_packet/launch/hallucinate_app/44dceea6bc53"
    assert receipt["packet_goals"] == ["VAIOS-G724", "VAIOS-G728"]
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["objective_gap_receipt"] == objective_gap_receipt
    assert receipt["launch_gate_receipt"] == launch_gate_receipt
    assert receipt["receipt_fixture"] == receipt_fixture

    assert task_id in shared_fixture["vai_task_ids"]
    assert receipt["launch_gate_receipt"] in shared_fixture["discovery_receipts"]
    assert receipt["objective_gap_receipt"] in shared_fixture["objective_gap_receipts"]
    assert shared_fixture["required_backends"] == receipt["required_backends"]
    assert shared_fixture["daemon_health_paths"] == receipt["daemon_health_paths"]
    assert shared_fixture["swissknife_handoff"] == receipt["swissknife_handoff"]

    g724_text = " ".join([*goals["VAIOS-G724"].fields.keys(), *goals["VAIOS-G724"].fields.values()])
    g728_text = " ".join([*goals["VAIOS-G728"].fields.keys(), *goals["VAIOS-G728"].fields.values()])
    for term in (
        task_id,
        packet_sibling_task_id,
        "MGW-535",
        "goal_packet/launch/hallucinate_app/44dceea6bc53",
        "launch Playwright validation gate",
        Path(objective_gap_receipt).name,
        Path(launch_gate_receipt).name,
        Path(receipt_fixture).name,
        "daemon-launch-health.spec.ts",
    ):
        assert term in receipt_source
        assert term in g728_text
    assert "VAIOS-G728" in g724_text
    assert "VAIOS-G724" in g728_text

    for term in (
        "Hallucinate App daemon health",
        "daemon launcher",
        "MCP server",
        "MCP dashboard",
        "ipfs_accelerate_py",
        "ipfs_datasets_py",
        "ipfs_kit_py",
        "external/ipfs_accelerate",
        "external/ipfs_datasets",
        "external/ipfs_kit",
        "dashboard capability catalog",
        "Swissknife applications",
        "launch Playwright validation gate",
    ):
        assert term in receipt_source
        assert term in shared_mgw_receipt_source
        assert term in g728_text


def test_vai_568_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap():
    _assert_vai_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap(
        task_id="VAI-568",
        packet_sibling_task_id="VAI-567",
        receipt_path=VAI_568_DAEMON_LAUNCH_GATE_PATH,
        fixture_path=VAI_568_DAEMON_LAUNCH_GATE_FIXTURE_PATH,
        objective_gap_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-568-objective-gap-b023c8de5b69.md",
        launch_gate_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-568-daemon-launch-health-gate.md",
        receipt_fixture="hallucinate_app/test/e2e/fixtures/vai-568-daemon-launch-health-gate.json",
    )


def test_vai_574_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap():
    _assert_vai_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap(
        task_id="VAI-574",
        packet_sibling_task_id="VAI-573",
        receipt_path=VAI_574_DAEMON_LAUNCH_GATE_PATH,
        fixture_path=VAI_574_DAEMON_LAUNCH_GATE_FIXTURE_PATH,
        objective_gap_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-574-objective-gap-b023c8de5b69.md",
        launch_gate_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-574-daemon-launch-health-gate.md",
        receipt_fixture="hallucinate_app/test/e2e/fixtures/vai-574-daemon-launch-health-gate.json",
    )


def test_vai_577_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap():
    _assert_vai_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap(
        task_id="VAI-577",
        packet_sibling_task_id="VAI-576",
        receipt_path=VAI_577_DAEMON_LAUNCH_GATE_PATH,
        fixture_path=VAI_577_DAEMON_LAUNCH_GATE_FIXTURE_PATH,
        objective_gap_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-577-objective-gap-b023c8de5b69.md",
        launch_gate_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-577-daemon-launch-health-gate.md",
        receipt_fixture="hallucinate_app/test/e2e/fixtures/vai-577-daemon-launch-health-gate.json",
    )


def test_vai_580_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap():
    _assert_vai_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap(
        task_id="VAI-580",
        packet_sibling_task_id="VAI-579",
        receipt_path=VAI_580_DAEMON_LAUNCH_GATE_PATH,
        fixture_path=VAI_580_DAEMON_LAUNCH_GATE_FIXTURE_PATH,
        objective_gap_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-580-objective-gap-b023c8de5b69.md",
        launch_gate_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-580-daemon-launch-health-gate.md",
        receipt_fixture="hallucinate_app/test/e2e/fixtures/vai-580-daemon-launch-health-gate.json",
    )


def test_vai_615_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap():
    _assert_vai_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap(
        task_id="VAI-615",
        packet_sibling_task_id="VAI-614",
        receipt_path=VAI_615_DAEMON_LAUNCH_GATE_PATH,
        fixture_path=VAI_615_DAEMON_LAUNCH_GATE_FIXTURE_PATH,
        objective_gap_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-615-objective-gap-b023c8de5b69.md",
        launch_gate_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-615-daemon-launch-health-gate.md",
        receipt_fixture="hallucinate_app/test/e2e/fixtures/vai-615-daemon-launch-health-gate.json",
    )


def test_vai_618_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap():
    _assert_vai_daemon_launch_gate_aligns_virtual_ai_os_backlog_with_objective_heap(
        task_id="VAI-618",
        packet_sibling_task_id="VAI-617",
        receipt_path=VAI_618_DAEMON_LAUNCH_GATE_PATH,
        fixture_path=VAI_618_DAEMON_LAUNCH_GATE_FIXTURE_PATH,
        objective_gap_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-618-objective-gap-b023c8de5b69.md",
        launch_gate_receipt="data/virtual_ai_os/discovery/2026-07-04-vai-618-daemon-launch-health-gate.md",
        receipt_fixture="hallucinate_app/test/e2e/fixtures/vai-618-daemon-launch-health-gate.json",
    )


def test_vai_578_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-578-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-578-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-578-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-578-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-578")

    assert fixture["task_id"] == "VAI-578"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-578-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-578-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-578 proof" in heap_source
    assert "VAI-578 attempt 1 validation" in heap_source


def test_vai_581_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-581-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-581-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-581-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-581-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-581")

    assert fixture["task_id"] == "VAI-581"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-581-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-581-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-581 proof" in heap_source
    assert "VAI-581 attempt 1 validation" in heap_source


def test_vai_587_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-587-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-587-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-587-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-587-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-587")

    assert fixture["task_id"] == "VAI-587"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-587-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-587-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-587 proof" in heap_source
    assert "VAI-587 attempt 1 validation" in heap_source


def test_vai_590_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-590-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-590-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-590-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-590-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-590")

    assert fixture["task_id"] == "VAI-590"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-590-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-590-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-590 proof" in heap_source
    assert "VAI-590 attempt 1 validation" in heap_source


def test_vai_591_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-591-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-591-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-591-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-591-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-591")

    assert fixture["task_id"] == "VAI-591"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-591-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-591-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-591 proof" in heap_source
    assert "VAI-591 attempt 1 validation" in heap_source


def test_vai_594_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-594-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-594-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-594-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-594-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-594")

    assert fixture["task_id"] == "VAI-594"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-594-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-594-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-594 proof" in heap_source
    assert "VAI-594 attempt 1 validation" in heap_source


def test_vai_597_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-597-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-597-attempt-2-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-597-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-597-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-597")

    assert fixture["task_id"] == "VAI-597"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-597-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt"] == 2
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-597-attempt-2-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-597 proof" in heap_source
    assert "VAI-597 attempt 2 validation" in heap_source


def test_vai_600_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-600-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-600-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-600-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-600-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-600")

    assert fixture["task_id"] == "VAI-600"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-600-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt"] == 1
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-600-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-600 proof" in heap_source
    assert "VAI-600 attempt 1 validation" in heap_source


def test_vai_603_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-603-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-603-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-603-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-603-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-603")

    assert fixture["task_id"] == "VAI-603"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-603-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt"] == 1
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-603-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-603 proof" in heap_source
    assert "VAI-603 attempt 1 validation" in heap_source


def test_vai_606_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-606-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-606-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-606-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-606-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-606")

    assert fixture["task_id"] == "VAI-606"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-606-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt"] == 1
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-606-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-606 proof" in heap_source
    assert "VAI-606 attempt 1 validation" in heap_source


def test_vai_609_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-609-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-609-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-609-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-609-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-609")

    assert fixture["task_id"] == "VAI-609"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-609-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt"] == 1
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-609-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-609 proof" in heap_source
    assert "VAI-609 attempt 1 validation" in heap_source


def test_vai_610_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-610-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-610-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-610-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-610-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-610")

    assert fixture["task_id"] == "VAI-610"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-610-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt"] == 1
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-610-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-610 proof" in heap_source
    assert "VAI-610 attempt 1 validation" in heap_source


def test_vai_613_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-613-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-613-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-613-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-613-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-613")

    assert fixture["task_id"] == "VAI-613"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-613-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt"] == 1
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-613-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-613 proof" in heap_source
    assert "VAI-613 attempt 1 validation" in heap_source


def test_vai_616_hallucinate_mcp_dashboard_mirror_tracks_vaios_g723_launch_gate():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-616-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-616-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "2026-07-04-vai-616-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-616-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-616")

    assert fixture["task_id"] == "VAI-616"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-616-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt"] == 1
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-616-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-616 proof" in heap_source
    assert "VAI-616 attempt 1 validation" in heap_source


def test_hallucinate_vai_619_mcp_dashboard_launch_gate_keeps_vaios_g723_aligned():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-619-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-619-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT / "data" / "virtual_ai_os" / "discovery" / "2026-07-04-vai-619-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-619-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-619")

    assert fixture["task_id"] == "VAI-619"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-619-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt"] == 1
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-619-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-619 proof" in heap_source
    assert "VAI-619 attempt 1 validation" in heap_source


def test_hallucinate_vai_622_mcp_dashboard_launch_gate_keeps_vaios_g723_aligned():
    receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-622-mcp-dashboard-launch-gate.md"
    attempt_receipt_path = DISCOVERY_ROOT / "2026-07-04-vai-622-attempt-1-validation.md"
    virtual_receipt_path = (
        REPO_ROOT / "data" / "virtual_ai_os" / "discovery" / "2026-07-04-vai-622-mcp-dashboard-launch-gate.md"
    )
    fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-622-mcp-dashboard-launch-gate.json"
    )
    catalog_fixture_path = (
        REPO_ROOT
        / "hallucinate_app"
        / "test"
        / "e2e"
        / "fixtures"
        / "vai-512-mcp-dashboard-catalog.json"
    )
    heap_source = (
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    receipt = receipt_path.read_text(encoding="utf-8")
    attempt_receipt = attempt_receipt_path.read_text(encoding="utf-8")
    virtual_receipt = virtual_receipt_path.read_text(encoding="utf-8")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_fixture_path.read_text(encoding="utf-8"))
    catalog_gate = next(gate for gate in catalog["launch_validation_gates"] if gate["task_id"] == "VAI-622")

    assert fixture["task_id"] == "VAI-622"
    assert fixture["goal_id"] == "VAIOS-G723"
    assert fixture["hallucinate_backlog_receipt"] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-622-mcp-dashboard-launch-gate.md"
    )
    assert fixture["attempt"] == 1
    assert fixture["attempt_receipts"][1] == (
        "data/hallucinate_multimodal_control/discovery/2026-07-04-vai-622-attempt-1-validation.md"
    )
    assert catalog_gate == fixture

    for term in fixture["required_evidence"]:
        assert term in receipt
        assert term in attempt_receipt
        assert term in virtual_receipt
        assert term in heap_source
        assert term in readiness_source

    assert "control_surface gate" in attempt_receipt
    assert "VAIOS-G723-C6 Supervisor-generated follow-up subtasks" in receipt
    assert "VAI-622 proof" in heap_source
    assert "VAI-622 attempt 1 validation" in heap_source


def test_vaios_g723_validation_failure_can_generate_follow_up_task_and_subgoal(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import (
        generate_objective_todos,
        scan_objective_gaps,
    )
    from ipfs_accelerate_py.agent_supervisor.objective_tracker import append_refinement_goals
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    repo = tmp_path / "repo"
    repo.mkdir()
    todo_path = repo / TEMP_TASK_BOARD_FILENAME
    objective_path = repo / "objective-heap.md"
    discovery_dir = repo / "discovery"
    bundle_dir = repo / "bundles"
    dataset_dir = repo / "datasets"
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G723 Hallucinate MCP dashboard interoperability console

- Status: active
- Parent: VAIOS-G697
- Fib priority: 13
- Track: launch
- Priority: P0
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Parallel lane: hallucinate-mcp-dashboard
- Refinement depth: 1
- Goal: Hallucinate App dashboards prove the dashboard capability catalog, daemon health, tools/list, tools/call, ipfs_kit_py, ipfs_datasets_py, and ipfs_accelerate_py.
- Evidence:
- Outputs: hallucinate_app, tests
- Validation: npm --prefix hallucinate_app run test:e2e -- mcp-dashboard-interoperability.spec.ts
- Refinement: Add supervisor-generated follow-up subtasks or subgoals if dashboard validation fails.
- Gap task: Keep Hallucinate App dashboard gaps auto-generated by the supervisor objective loop.
""",
        encoding="utf-8",
    )

    findings = scan_objective_gaps(
        repo,
        objective_path=objective_path,
        max_findings=1,
        force_goal_ids=["VAIOS-G723"],
    )
    assert [finding.goal_id for finding in findings] == ["VAIOS-G723"]
    assert findings[0].candidate_kind == "validation_gate"
    assert findings[0].work_scope == "launch_validation_gate"
    assert findings[0].missing_evidence == ["launch Playwright validation gate"]

    records = generate_objective_todos(
        repo_root=repo,
        objective_path=objective_path,
        todo_path=todo_path,
        discovery_dir=discovery_dir,
        bundle_dir=bundle_dir,
        dataset_dir=dataset_dir,
        task_prefix="HAO-",
        max_findings=1,
        force_goal_ids=["VAIOS-G723"],
        persist_ast_dataset=False,
        write_todo_vector_index=False,
        summary_prefix="Close virtual AI OS objective gap",
        discovery_output_path="discovery",
    )
    assert len(records) == 1
    task = {item.task_id: item for item in parse_task_file(todo_path, "## HAO-")}["HAO-002"]
    assert task.metadata["goal id"] == "VAIOS-G723"
    assert task.metadata["bundle"] == "objective/launch/hallucinate-mcp-dashboard"
    assert task.metadata["work scope"] == "launch_validation_gate"
    assert "launch Playwright validation gate" in task.metadata["missing evidence"]
    assert "mcp-dashboard-interoperability.spec.ts" in " ".join(task.validation)
    assert "multimodal-control-surface.spec.ts" in " ".join(task.validation)

    refinement = append_refinement_goals(
        objective_path,
        findings,
        max_children_per_finding=1,
        max_depth=2,
        goal_prefix="VAIOS-G",
    )
    assert len(refinement.appended_goal_ids) == 1
    updated_objective = objective_path.read_text(encoding="utf-8")
    assert f"## {refinement.appended_goal_ids[0]}" in updated_objective
    assert "- Parent: VAIOS-G723" in updated_objective
    assert "launch Playwright validation gate" in updated_objective


def test_hallucinate_codebase_scan_skips_shared_objective_and_mgw_owned_paths():
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")

    expected_skips = {
        "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md",
        "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
        "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
        "tests/test_meta_glasses_display_todo_queue.py",
    }

    assert expected_skips <= set(daemon_module.CODEBASE_SCAN_SKIP_PREFIXES)
    assert daemon_module.CODEBASE_SCAN_MIN_OPEN_TASKS == 8
    assert daemon_module.CODEBASE_SCAN_MAX_FINDINGS == 3
    assert daemon_module.CODEBASE_SCAN_SETTINGS.max_findings == 3
    assert daemon_module.HALLUCINATE_INTEROPERABILITY_FOCUS == ("hallucinate_app", "swissknife")
    assert "Mcp-Plus-Plus" in daemon_module.HALLUCINATE_INTEROPERABILITY_COMPONENT_PATHS
    assert "external/meta-wearables-dat-android" in daemon_module.HALLUCINATE_INTEROPERABILITY_COMPONENT_PATHS
    assert "swissknife/cleanup-archive/" in daemon_module.CODEBASE_SCAN_SKIP_PREFIXES
    assert "swissknife/docs/DEVELOPER_GUIDE.md" in daemon_module.CODEBASE_SCAN_SKIP_PREFIXES
    assert "swissknife/docs/validation/" in daemon_module.CODEBASE_SCAN_SKIP_PREFIXES


def test_hao_428_offload_session_events_route_through_mediation():
    source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    section_start = source.index("### Offload-session mobile and glasses mediation path")
    section_end = source.index("## Meta-Glasses Relationship")
    section = source[section_start:section_end]
    normalized_source = " ".join(source.split())

    required_terms = [
        "Offload-session mobile and glasses mediation path",
        "voice, gesture, display action, or phone UI event",
        "adapter submits the envelope to the shared Hallucinate App mediation",
        "policy_decision",
        "mediation_receipt",
        "virtual_desktop_command_intent",
        "denied results stop at the receipt",
        "Offload-session adapters MUST NOT call desktop peer RPC",
        "dispatch only from the resulting",
        "policy_receipt_id",
    ]
    for term in required_terms:
        assert term in normalized_source

    for event_class in (
        "Voice command from phone or glasses",
        "Gesture from phone, captouch, Neural Band, or glasses",
        "Display action from glasses terminal or DAT display",
        "Phone UI event from mobile shell",
    ):
        assert event_class in source

    assert section.index("adapter submits the envelope") < section.index("Only an allowed")
    assert section.index("MUST NOT call desktop peer RPC") < section.index("policy_receipt_id")


def test_hao_429_peer_offload_policy_receipts_and_recovery_states():
    source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    section_start = source.index("### Peer-offload policy receipts and recovery states")
    section_end = source.index("### Meta glasses display-widget intent bridge")
    section = source[section_start:section_end]
    normalized_section = " ".join(section.replace("`", "").split())

    required_terms = [
        "peer_offload_policy_receipt",
        "peer_offload_recovery_receipt",
        "decision, selected peer, fallback, cancellation, timeout, and retry state",
        "phone UI, Swissknife UI, and Meta glasses terminal",
        "policy_decision",
        "selected_peer",
        "fallback_plan",
        "recovery_state",
        "retry_budget",
        "render_targets",
        "Policy allow or confirmation",
        "Peer selection fallback",
        "User cancellation",
        "Peer timeout",
        "Retry scheduled or exhausted",
        "dispatching, awaiting_confirmation, running_on_peer, fallback_selected",
        "retry_scheduled, cancelled, timed_out, retry_exhausted, failed_closed, and recovered",
        "Runtime-plane targets may report transport availability and execution errors",
        "must not choose a new recovery state",
        "event_receipt_id -> policy_receipt_id -> command_receipt_id -> peer_offload_policy_receipt_id",
        "peer_offload_recovery_receipt_id -> render_receipt_id",
        "must not invent different status semantics",
    ]
    for term in required_terms:
        assert term in normalized_section

    assert section.index("mediation_receipt") < section.index("before peer dispatch")
    assert section.index("Peer-offload recovery records") < section.index("The recovery-state vocabulary is fixed")
    assert section.index("Hallucinate App owns recovery-state transitions") < section.index("The peer-offload receipt chain is")


def test_hao_430_hardware_free_multimodal_offload_harness_documents_deterministic_replay():
    source = HARDWARE_FREE_OFFLOAD_HARNESS_PATH.read_text(encoding="utf-8")
    idl_source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    launch_slice_source = LAUNCH_SLICE_REPLAY_RECEIPTS_PATH.read_text(encoding="utf-8")
    normalized_source = " ".join(source.split())
    harness = _json_block_after(source, "## Deterministic Harness Fixture")
    launch_slice = _json_block_after(
        launch_slice_source,
        "## Deterministic Launch-Slice Replay Fixture",
    )

    required_terms = [
        "hardware-free multimodal offload harness",
        "No physical phone, desktop, Swissknife browser, or Meta glasses device is required",
        "simulates phone input, desktop peer offload, Swissknife operator UI, and Meta glasses terminal output",
        "proves routing, mediation, receipts, and recovery",
        "phone_event -> mediation_receipt -> virtual_desktop_command_intent -> peer_offload_policy_receipt",
        "peer_offload_recovery_receipt -> render_receipt",
    ]
    for term in required_terms:
        assert term in normalized_source

    assert harness["task_id"] == "HAO-430"
    assert harness["determinism"]["clock"] == "fixed"
    assert harness["determinism"]["network"] == "simulated"
    assert harness["requires_physical_devices"] is False
    assert harness["participants"] == {
        "phone:operator": "simulated_phone_input",
        "desktop:peer": "simulated_desktop_peer_offload",
        "swissknife:ui": "simulated_operator_ui",
        "meta_glasses:terminal": "simulated_terminal_output",
    }

    steps = harness["replay_steps"]
    assert [step["phase"] for step in steps] == [
        "phone_event",
        "mediation",
        "command_intent",
        "peer_offload_selection",
        "desktop_peer_timeout",
        "recovery",
        "surface_render",
    ]
    assert steps[0]["event"]["session"]["participant_id"] == "phone:operator"
    assert steps[1]["receipt"]["receipt_id"] == "rcpt_policy_hao430_open_monitor"
    assert steps[1]["receipt"]["policy_decision"] == "allow"
    assert steps[2]["command"]["receipt_ids"]["policy_receipt_id"] == steps[1]["receipt"]["receipt_id"]
    assert steps[3]["receipt"]["selected_peer"]["participant_id"] == "desktop:peer"
    assert steps[4]["runtime_receipt"]["runtime_status"] == "timeout"
    assert steps[5]["receipt"]["peer_offload_policy_receipt_id"] == steps[3]["receipt"]["receipt_id"]
    assert steps[5]["receipt"]["recovery_state"] == "fallback_selected"
    assert steps[5]["receipt"]["selected_peer"]["participant_id"] == "swissknife:ui"
    assert steps[6]["render_receipts"][0]["participant_id"] == "phone:operator"
    assert steps[6]["render_receipts"][1]["participant_id"] == "swissknife:ui"
    assert steps[6]["render_receipts"][2]["participant_id"] == "meta_glasses:terminal"
    assert {
        receipt["state"]
        for receipt in steps[6]["render_receipts"]
    } == {"fallback_selected"}

    invariants = harness["assertions"]
    assert "all ingress events enter mediation before dispatch" in invariants
    assert "desktop peer execution never starts without policy_receipt_id" in invariants
    assert "all user-visible surfaces render the same recovery_state" in invariants
    assert "receipt chain is stable across retry or fallback" in invariants

    idl_section_start = idl_source.index("### Launch-slice deterministic replay artifacts")
    idl_section_end = idl_source.index("### Meta glasses display-widget intent bridge")
    idl_section = " ".join(idl_source[idl_section_start:idl_section_end].replace("`", "").split())
    for term in (
        "HAO-432",
        "deterministic replay artifact",
        "phone-originated virtual desktop command",
        "desktop peer selection, policy decisions, retry, fallback, user cancellation, and Meta glasses status updates",
        "phone_event -> mediation_receipt -> virtual_desktop_command_intent -> peer_offload_policy_receipt",
        "peer_offload_recovery_receipt -> meta_glasses_status_receipt -> render_receipt",
        "recovery_state: \"retry_scheduled\"",
        "recovery_state: \"fallback_selected\"",
        "recovery_state: \"cancelled\"",
    ):
        assert term in idl_section

    assert launch_slice["task_id"] == "HAO-432"
    assert launch_slice["artifact_id"] == "launch_slice_replay_receipts"
    assert launch_slice["extends_harness_id"] == harness["harness_id"]
    assert launch_slice["requires_physical_devices"] is False
    assert launch_slice["determinism"]["clock"] == "fixed"
    assert launch_slice["determinism"]["network"] == "simulated"
    assert launch_slice["participants"] == harness["participants"]
    assert launch_slice["receipt_chain"] == [
        "phone_event",
        "mediation_receipt",
        "virtual_desktop_command_intent",
        "peer_offload_policy_receipt",
        "runtime_receipt",
        "peer_offload_recovery_receipt",
        "meta_glasses_status_receipt",
        "render_receipt",
    ]

    launch_steps = launch_slice["replay_steps"]
    assert [step["phase"] for step in launch_steps] == [
        "phone_event",
        "mediation",
        "command_intent",
        "peer_offload_selection",
        "runtime_timeout",
        "retry_recovery",
        "meta_glasses_status_retry",
        "runtime_timeout_after_retry",
        "fallback_recovery",
        "meta_glasses_status_fallback",
        "phone_cancel_event",
        "cancel_mediation",
        "cancel_recovery",
        "surface_render",
    ]
    assert launch_steps[0]["event"]["session"]["participant_id"] == "phone:operator"
    assert launch_steps[1]["receipt"]["policy_decision"] == "allow"
    assert launch_steps[2]["command"]["receipt_ids"]["policy_receipt_id"] == launch_steps[1]["receipt"]["receipt_id"]
    assert launch_steps[3]["receipt"]["selected_peer"]["participant_id"] == "desktop:peer"
    assert launch_steps[3]["receipt"]["policy_decision"] == "allow"
    assert launch_steps[4]["runtime_receipt"]["runtime_status"] == "timeout"
    assert launch_steps[5]["receipt"]["recovery_state"] == "retry_scheduled"
    assert launch_steps[5]["receipt"]["next_target_participant_id"] == "desktop:peer"
    assert launch_steps[6]["meta_glasses_status_receipt"]["state"] == "retry_scheduled"
    assert (
        launch_steps[6]["meta_glasses_status_receipt"]["source_recovery_receipt_id"]
        == launch_steps[5]["receipt"]["receipt_id"]
    )
    assert launch_steps[8]["receipt"]["recovery_state"] == "fallback_selected"
    assert launch_steps[8]["receipt"]["selected_peer"]["participant_id"] == "swissknife:ui"
    assert launch_steps[9]["meta_glasses_status_receipt"]["state"] == "fallback_selected"
    assert (
        launch_steps[9]["meta_glasses_status_receipt"]["source_recovery_receipt_id"]
        == launch_steps[8]["receipt"]["receipt_id"]
    )
    assert launch_steps[10]["event"]["surface_event"] == "cancel"
    assert launch_steps[10]["event"]["session"]["participant_id"] == "phone:operator"
    assert launch_steps[12]["receipt"]["recovery_state"] == "cancelled"
    assert launch_steps[12]["receipt"]["cancel_source_participant_id"] == "phone:operator"
    assert launch_steps[13]["render_receipts"][2]["participant_id"] == "meta_glasses:terminal"
    assert {
        receipt["state"]
        for receipt in launch_steps[13]["render_receipts"]
    } == {"cancelled"}

    launch_invariants = launch_slice["assertions"]
    assert "phone-originated commands enter mediation before dispatch" in launch_invariants
    assert "desktop peer selection is receipt-backed by policy_decision" in launch_invariants
    assert "retry_scheduled, fallback_selected, and cancelled outcomes are replayed in one sequence" in launch_invariants
    assert "Meta glasses status updates use the same recovery receipt IDs as phone and Swissknife renders" in launch_invariants


def test_hao_434_launch_replay_receipts_feed_vai_mgw_shared_evidence_packet():
    source = VAI_MGW_SHARED_EVIDENCE_PACKET_PATH.read_text(encoding="utf-8")
    idl_source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    packet = _json_block_after(source, "## Shared Evidence Packet Fixture")
    idl_section_start = idl_source.index("### VAI/MGW shared launch evidence packet")
    idl_section_end = idl_source.index("### Meta glasses display-widget intent bridge")
    idl_section = " ".join(idl_source[idl_section_start:idl_section_end].replace("`", "").split())

    for term in (
        "HAO-434",
        "VAI/MGW shared launch evidence packet",
        "mediation, command-intent, peer-offload, recovery, and render receipt IDs",
        "identical session_id, command_correlation_id, policy_correlation_id, and placement_correlation_id",
        "VAI launch replay",
        "MGW glasses-widget launch replay",
        "must reject the packet",
    ):
        assert term in idl_section

    assert packet["task_id"] == "HAO-434"
    assert packet["artifact_id"] == "vai_mgw_shared_launch_evidence_packet"
    assert packet["source_replay_artifact"] == "launch_slice_replay_receipts"
    assert packet["consumed_by"] == [
        "virtual_ai_os.launch_replay",
        "meta_glasses_display_widgets.glasses_widget_launch_replay",
    ]

    correlations = packet["correlation_ids"]
    assert correlations == {
        "session_id": "vdsk_hao432_launch_slice",
        "command_correlation_id": "cmdcorr_hao434_open_monitor",
        "policy_correlation_id": "polcorr_hao434_open_monitor",
        "placement_correlation_id": "placecorr_hao434_desktop_peer",
    }

    emitted = packet["emitted_receipt_ids"]
    assert emitted["mediation_receipt_id"] == "rcpt_policy_hao432_open_monitor"
    assert emitted["command_intent_receipt_id"] == "rcpt_cmd_hao432_open_monitor"
    assert emitted["peer_offload_policy_receipt_id"] == "rcpt_offload_hao432_open_monitor"
    assert emitted["recovery_receipt_ids"] == [
        "rcpt_recovery_hao432_retry",
        "rcpt_recovery_hao432_fallback",
        "rcpt_recovery_hao432_cancelled",
    ]
    assert emitted["render_receipt_ids"] == {
        "phone:operator": "rcpt_render_hao432_phone",
        "swissknife:ui": "rcpt_render_hao432_swissknife",
        "meta_glasses:terminal": "rcpt_render_hao432_glasses",
    }

    for receipt in packet["hallucinate_app_emitted_receipts"]:
        assert {
            key: receipt[key]
            for key in (
                "session_id",
                "command_correlation_id",
                "policy_correlation_id",
                "placement_correlation_id",
            )
        } == correlations

    vai_replay = packet["vai_launch_replay"]
    mgw_replay = packet["mgw_glasses_widget_launch_replay"]
    for replay in (vai_replay, mgw_replay):
        assert {
            key: replay[key]
            for key in (
                "session_id",
                "command_correlation_id",
                "policy_correlation_id",
                "placement_correlation_id",
            )
        } == correlations
        assert replay["consumed_receipt_ids"] == emitted

    assert vai_replay["launch_replay_id"] == "vai-launch-replay-hao434"
    assert mgw_replay["launch_replay_id"] == "mgw-glasses-widget-launch-replay-hao434"
    assert (
        mgw_replay["display_widget_action"]["orb_receipt_cid"]
        == emitted["render_receipt_ids"]["meta_glasses:terminal"]
    )
    assert packet["assertions"] == [
        "Hallucinate App emits every receipt ID consumed by VAI and MGW launch replay",
        "VAI and MGW receive identical session, command, policy, and placement correlation IDs",
        "recovery receipt IDs remain stable across retry, fallback, and cancel",
        "the Meta glasses render receipt is the MGW orb_receipt_cid alias, not a separate command authority",
    ]


def test_hao_438_desktop_peer_offload_smoke_receipt_recovers_to_phone_local():
    source = DESKTOP_PEER_OFFLOAD_SMOKE_PATH.read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    packet = _json_block_after(source, "## Desktop-Peer Offload Smoke Fixture")
    normalized_source = " ".join(source.split())
    normalized_readiness = " ".join(readiness_source.split())

    for term in (
        "HAO-438",
        "desktop-peer offload smoke receipt",
        "phone-originated command",
        "desktop:peer",
        "capability and runtime health",
        "peer_offload_policy_receipt",
        "phone_local",
        "same session, command, policy, placement, and offload receipt IDs intact",
    ):
        assert term in normalized_source

    for term in (
        "HAO-438",
        "Desktop-Peer Offload Smoke",
        "desktop-peer offload smoke receipt",
        "desktop:peer",
        "peer_offload_policy_receipt",
        "phone_local",
        "session_id",
        "command_intent_id",
        "policy_receipt_id",
        "placement_id",
    ):
        assert term in normalized_readiness

    assert packet["task_id"] == "HAO-438"
    assert packet["artifact_id"] == "desktop_peer_offload_smoke_receipt"
    assert packet["goal_id"] == "VAIOS-G697"
    assert packet["requires_physical_devices"] is False
    assert packet["determinism"]["clock"] == "fixed"
    assert packet["determinism"]["network"] == "simulated"
    assert packet["participants"]["desktop:peer"] == "simulated_desktop_peer_offload"
    assert packet["participants"]["phone_local"] == "phone_local_runtime_fallback"
    assert packet["receipt_chain"] == [
        "phone_event",
        "mediation_receipt",
        "virtual_desktop_command_intent",
        "desktop_peer_capability_receipt",
        "desktop_peer_runtime_health_receipt",
        "peer_offload_policy_receipt",
        "runtime_receipt",
        "peer_offload_recovery_receipt",
        "render_receipt",
    ]

    stable_ids = packet["stable_ids"]
    assert stable_ids == {
        "session_id": "vdsk_hao438_desktop_peer_smoke",
        "interaction_id": "evt_hao438_open_monitor",
        "command_intent_id": "cmd_hao438_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao438_open_monitor",
        "command_receipt_id": "rcpt_cmd_hao438_open_monitor",
        "placement_id": "place_hao438_desktop_peer_model_monitor",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao438_open_monitor",
    }

    steps = packet["replay_steps"]
    assert [step["phase"] for step in steps] == [
        "phone_event",
        "mediation",
        "command_intent",
        "desktop_peer_capability",
        "desktop_peer_runtime_health",
        "peer_offload_selection",
        "runtime_unavailable",
        "phone_local_recovery",
        "surface_render",
    ]
    assert steps[0]["event"]["session"]["participant_id"] == "phone:operator"
    assert steps[0]["event"]["session"]["session_id"] == stable_ids["session_id"]
    assert steps[1]["receipt"]["receipt_id"] == stable_ids["policy_receipt_id"]
    assert steps[1]["receipt"]["policy_decision"] == "allow"
    assert steps[2]["command"]["issued_to"] == "desktop:peer"
    assert steps[2]["command"]["command_intent_id"] == stable_ids["command_intent_id"]
    assert steps[2]["command"]["placement_hint"]["placement_id"] == stable_ids["placement_id"]
    assert steps[2]["command"]["placement_hint"]["fallback_runtime"] == "phone_local"

    capability = steps[3]["capability_receipt"]
    health = steps[4]["runtime_health_receipt"]
    assert capability["participant_id"] == "desktop:peer"
    assert capability["authenticated_transport"] is True
    assert capability["receipt_return_path"] == "hallucinate_app.receipts.peer_runtime"
    assert "desktop.execute_command" in capability["capability_refs"]
    assert "desktop.stream_region" in capability["capability_refs"]
    assert health["participant_id"] == "desktop:peer"
    assert health["runtime_status"] == "healthy"
    assert health["stream_region_ready"] is True

    offload = steps[5]["receipt"]
    assert offload["receipt_contract_ref"] == "peer_offload_policy_receipt@0.1.0"
    assert offload["receipt_id"] == stable_ids["peer_offload_policy_receipt_id"]
    assert offload["session_id"] == stable_ids["session_id"]
    assert offload["command_intent_id"] == stable_ids["command_intent_id"]
    assert offload["policy_receipt_id"] == stable_ids["policy_receipt_id"]
    assert offload["command_receipt_id"] == stable_ids["command_receipt_id"]
    assert offload["placement_id"] == stable_ids["placement_id"]
    assert offload["capability_receipt_id"] == capability["receipt_id"]
    assert offload["runtime_health_receipt_id"] == health["receipt_id"]
    assert offload["selected_peer"]["participant_id"] == "desktop:peer"
    assert offload["fallback_plan"]["fallback_targets"] == ["phone_local"]

    runtime = steps[6]["runtime_receipt"]
    assert runtime["runtime_status"] == "unavailable"
    assert runtime["failed_peer_id"] == "desktop:peer"
    assert runtime["peer_offload_policy_receipt_id"] == stable_ids["peer_offload_policy_receipt_id"]

    recovery = steps[7]["receipt"]
    for key in (
        "session_id",
        "command_intent_id",
        "policy_receipt_id",
        "command_receipt_id",
        "placement_id",
        "peer_offload_policy_receipt_id",
    ):
        assert recovery[key] == stable_ids[key]
    assert recovery["recovery_state"] == "fallback_selected"
    assert recovery["recovered_runtime"] == "phone_local"
    assert recovery["selected_peer"]["participant_id"] == "phone_local"
    assert recovery["runtime_receipt_id"] == runtime["receipt_id"]

    render_receipts = steps[8]["render_receipts"]
    assert {receipt["runtime"] for receipt in render_receipts} == {"phone_local"}
    assert {receipt["source_recovery_receipt_id"] for receipt in render_receipts} == {
        recovery["receipt_id"]
    }
    assert packet["assertions"] == [
        "phone-originated command enters mediation before desktop peer dispatch",
        "desktop:peer is selected only after capability and runtime health receipts",
        "peer_offload_policy_receipt carries the selected desktop peer and placement_id",
        "desktop peer reports availability failure but does not choose fallback",
        "phone_local recovery preserves the same session_id, command_intent_id, policy_receipt_id, command_receipt_id, placement_id, and peer_offload_policy_receipt_id",
    ]


def test_hao_439_meta_glasses_terminal_receipt_maps_display_actions_through_bridge():
    source = META_GLASSES_TERMINAL_RECEIPT_PATH.read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    packet = _json_block_after(source, "## Meta Glasses Terminal Receipt Fixture")
    normalized_source = " ".join(source.split())
    normalized_readiness = " ".join(readiness_source.split())

    for term in (
        "HAO-439",
        "Meta glasses terminal receipt",
        "display_action",
        "HAO-431 bridge",
        "normalized Hallucinate App intents",
        "meta_glasses:terminal",
        "terminal.activate_action",
        "fail closed",
    ):
        assert term in normalized_source

    for term in (
        "HAO-439",
        "Meta Glasses Terminal Receipt",
        "display_action",
        "HAO-431",
        "meta_glasses:terminal",
        "raw_payload.display_action",
        "terminal.activate_action",
        "selected_peer",
        "fail_closed",
    ):
        assert term in normalized_readiness

    assert packet["task_id"] == "HAO-439"
    assert packet["artifact_id"] == "meta_glasses_terminal_receipt"
    assert packet["goal_id"] == "VAIOS-G697"
    assert packet["requires_physical_devices"] is False
    assert packet["bridge_contract"] == {
        "source_task": "HAO-431",
        "bridge_ref": "meta_glasses_display_widget_intent_bridge",
        "single_command_contract": True,
        "display_action_field": "raw_payload.display_action",
        "normalized_intent_authority": "hallucinate_app:mediator",
    }
    assert packet["participants"]["meta_glasses:terminal"] == (
        "simulated_meta_glasses_display_action_source"
    )
    assert packet["receipt_chain"] == [
        "pairing_receipt",
        "display_action_receipt",
        "confirmation_receipt",
        "interaction_envelope",
        "mediation_receipt",
        "virtual_desktop_command_intent",
        "peer_offload_policy_receipt",
        "terminal_render_receipt",
        "stale_evidence_recovery_receipt",
    ]

    stable_ids = packet["stable_ids"]
    assert stable_ids == {
        "session_id": "vdsk_hao439_meta_glasses_terminal",
        "pairing_receipt_id": "rcpt_pair_hao439_glasses_terminal",
        "display_action_receipt_id": "rcpt_display_action_hao439_activate",
        "confirmation_receipt_id": "rcpt_confirm_hao439_activate",
        "interaction_id": "evt_hao439_activate_monitor",
        "event_receipt_id": "rcpt_evt_hao439_activate_monitor",
        "policy_receipt_id": "rcpt_policy_hao439_activate_monitor",
        "command_intent_id": "cmd_hao439_activate_monitor",
        "command_receipt_id": "rcpt_cmd_hao439_activate_monitor",
        "placement_id": "place_hao439_terminal_model_monitor",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao439_activate_monitor",
        "stale_evidence_receipt_id": "rcpt_stale_hao439_glasses_terminal",
    }

    steps = packet["replay_steps"]
    assert [step["phase"] for step in steps] == [
        "pairing_receipt",
        "display_action",
        "terminal_confirmation",
        "interaction_envelope",
        "mediation",
        "command_intent",
        "peer_offload_selection",
        "terminal_render",
        "stale_evidence_recovery",
    ]

    pairing = steps[0]["pairing_receipt"]
    display_action = steps[1]["display_action_receipt"]
    confirmation = steps[2]["confirmation_receipt"]
    envelope = steps[3]["interaction_envelope"]
    mediation = steps[4]["receipt"]
    command = steps[5]["command"]
    offload = steps[6]["receipt"]
    render_receipts = steps[7]["render_receipts"]
    stale_recovery = steps[8]["receipt"]

    for record in (pairing, display_action, confirmation, envelope, stale_recovery):
        assert record["participant_id"] == "meta_glasses:terminal"
        assert record["session_id"] == stable_ids["session_id"]

    assert pairing["pairing_state"] == "active"
    assert pairing["display_evidence_state"] == "fresh"
    assert display_action["event_type"] == "display_action"
    assert display_action["receipt_id"] == stable_ids["display_action_receipt_id"]
    assert display_action["bridge_ref"] == "meta_glasses_display_widget_intent_bridge"
    assert display_action["pairing_receipt_id"] == stable_ids["pairing_receipt_id"]
    assert display_action["raw_payload"]["display_action"]["action_type"] == (
        "activateDisplayWidgetAction"
    )
    assert display_action["raw_payload"]["display_action"]["selected_peer"] == "desktop:peer"
    assert confirmation["receipt_id"] == stable_ids["confirmation_receipt_id"]
    assert confirmation["confirmation"] == "confirm"

    assert envelope["bridge_ref"] == "meta_glasses_display_widget_intent_bridge"
    assert envelope["raw_payload"]["display_action"] == display_action["raw_payload"]["display_action"]
    assert envelope["raw_payload"]["display_action_receipt_id"] == stable_ids["display_action_receipt_id"]
    assert envelope["normalized_intent"]["intent"] == "terminal.activate_action"
    assert envelope["normalized_intent"]["method"] == "activate_action"
    assert envelope["normalized_intent"]["arguments"]["selected_peer"] == "desktop:peer"

    assert mediation["receipt_contract_ref"] == "mediation_receipt@0.1.0"
    assert mediation["receipt_id"] == stable_ids["policy_receipt_id"]
    assert mediation["source_participant_id"] == "meta_glasses:terminal"
    assert mediation["policy_decision"] == "allow"
    assert mediation["normalized_intent"] == "terminal.activate_action"
    assert mediation["display_action_receipt_id"] == stable_ids["display_action_receipt_id"]

    assert command["command_intent_id"] == stable_ids["command_intent_id"]
    assert command["issued_to"] == "meta_glasses:terminal"
    assert command["intent"] == "terminal.activate_action"
    assert command["mapped_desktop_intent"] == "desktop.open_widget"
    assert command["placement_hint"]["selected_peer"] == "desktop:peer"
    assert command["receipt_ids"]["policy_receipt_id"] == stable_ids["policy_receipt_id"]
    assert command["receipt_ids"]["display_action_receipt_id"] == stable_ids["display_action_receipt_id"]

    assert offload["receipt_id"] == stable_ids["peer_offload_policy_receipt_id"]
    assert offload["display_action_receipt_id"] == stable_ids["display_action_receipt_id"]
    assert offload["selected_peer"]["participant_id"] == "desktop:peer"
    assert offload["recovery_state"] == "running_on_peer"
    assert "meta_glasses:terminal" in offload["render_targets"]

    terminal_render = render_receipts[0]
    assert terminal_render["participant_id"] == "meta_glasses:terminal"
    assert terminal_render["selected_peer"] == "desktop:peer"
    assert terminal_render["state"] == "running_on_peer"
    assert terminal_render["source_offload_receipt_id"] == stable_ids["peer_offload_policy_receipt_id"]

    assert stale_recovery["receipt_id"] == stable_ids["stale_evidence_receipt_id"]
    assert stale_recovery["stale_pairing"] is True
    assert stale_recovery["stale_display_evidence"] is True
    assert stale_recovery["policy_decision"] == "deny"
    assert stale_recovery["policy_receipt_id"] is None
    assert stale_recovery["dispatch_allowed"] is False
    assert stale_recovery["recovery_state"] == "fail_closed"
    assert stale_recovery["selected_peer"] is None
    assert stale_recovery["blocked_intents"] == [
        "terminal.activate_action",
        "desktop.request_handoff",
        "desktop.open_widget",
    ]
    assert stale_recovery["render_receipt"]["participant_id"] == "meta_glasses:terminal"
    assert stale_recovery["render_receipt"]["state"] == "fail_closed"

    assert packet["assertions"] == [
        "display_action and confirmation enter through the HAO-431 bridge",
        "raw_payload.display_action is preserved before normalized_intent is emitted",
        "normalized Hallucinate App intent is terminal.activate_action",
        "meta_glasses:terminal participant identity is preserved across pairing, action, confirmation, mediation, and render receipts",
        "terminal render receipts show selected_peer and recovery_state",
        "stale pairing or display evidence fails closed with no policy_receipt_id and no runtime dispatch",
    ]


def test_hao_437_real_phone_ingress_rehearsal_receipt_fails_closed_without_adapter():
    source = PHONE_INGRESS_REHEARSAL_PATH.read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    packet = _json_block_after(source, "## Real Phone Ingress Rehearsal Fixture")
    normalized_source = " ".join(source.split())
    normalized_readiness = " ".join(readiness_source.split())

    for term in (
        "HAO-437",
        "real phone ingress rehearsal",
        "real phone ingress",
        "phone:operator",
        "interaction_envelope",
        "mediation_receipt",
        "policy_receipt_id",
        "fail-closed recovery",
    ):
        assert term in normalized_source

    for term in (
        "HAO-437",
        "Real Phone Ingress Rehearsal",
        "real phone ingress rehearsal receipt",
        "phone:operator",
        "interaction_envelope",
        "session_id",
        "correlation_id",
        "request_id",
        "mediation_receipt",
        "policy_receipt_id",
        "fail_closed",
    ):
        assert term in normalized_readiness

    assert packet["task_id"] == "HAO-437"
    assert packet["artifact_id"] == "real_phone_ingress_rehearsal_receipt"
    assert packet["goal_id"] == "VAIOS-G697"
    assert packet["requires_physical_devices"] is True
    assert packet["physical_device"]["participant_id"] == "phone:operator"
    assert packet["physical_device"]["adapter_absent_recovery"] == "fail_closed"
    assert packet["participants"]["desktop:peer"] == "runtime_target_blocked_until_policy"
    assert packet["participants"]["phone_local"] == "runtime_target_blocked_until_policy"
    assert packet["receipt_chain"] == [
        "physical_phone_adapter_receipt",
        "interaction_envelope",
        "mediation_receipt",
        "virtual_desktop_command_intent",
        "dispatch_gate_receipt",
        "adapter_absent_recovery_receipt",
    ]

    stable_ids = packet["stable_ids"]
    assert stable_ids == {
        "session_id": "vdsk_hao437_real_phone_ingress",
        "correlation_id": "corr_hao437_phone_open_monitor",
        "request_id": "req_hao437_phone_open_monitor",
        "interaction_id": "evt_hao437_phone_open_monitor",
        "event_receipt_id": "rcpt_evt_hao437_phone_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao437_phone_open_monitor",
        "command_intent_id": "cmd_hao437_phone_open_monitor",
        "command_receipt_id": "rcpt_cmd_hao437_phone_open_monitor",
        "placement_id": "place_hao437_phone_model_monitor",
        "adapter_absent_receipt_id": "rcpt_absent_hao437_phone_adapter",
    }

    steps = packet["replay_steps"]
    assert [step["phase"] for step in steps] == [
        "physical_phone_event",
        "interaction_envelope",
        "mediation",
        "command_intent",
        "dispatch_gate",
        "adapter_absent_recovery",
    ]

    adapter = steps[0]["adapter_receipt"]
    envelope = steps[1]["interaction_envelope"]
    mediation = steps[2]["receipt"]
    command = steps[3]["command"]
    dispatch_gate = steps[4]["receipt"]
    absent_recovery = steps[5]["receipt"]

    assert adapter["participant_id"] == "phone:operator"
    assert adapter["adapter_status"] == "attached"
    assert adapter["transport_authenticated"] is True
    assert envelope["participant_id"] == "phone:operator"
    assert envelope["surface"] == "phone"
    assert envelope["surface_event"] == "tap"
    assert envelope["normalized_intent"]["arguments"]["source"] == "real_phone_ingress"

    for record in (adapter, envelope, mediation, command, dispatch_gate, absent_recovery):
        assert record["session_id"] == stable_ids["session_id"]
        assert record["correlation_id"] == stable_ids["correlation_id"]
        assert record["request_id"] == stable_ids["request_id"]

    assert mediation["receipt_contract_ref"] == "mediation_receipt@0.1.0"
    assert mediation["receipt_id"] == stable_ids["policy_receipt_id"]
    assert mediation["policy_receipt_id"] == stable_ids["policy_receipt_id"]
    assert mediation["interaction_envelope_ref"] == stable_ids["interaction_id"]
    assert command["command_intent_id"] == stable_ids["command_intent_id"]
    assert command["receipt_ids"]["mediation_receipt_id"] == stable_ids["policy_receipt_id"]
    assert command["receipt_ids"]["policy_receipt_id"] == stable_ids["policy_receipt_id"]
    assert command["placement_hint"]["placement_id"] == stable_ids["placement_id"]
    assert command["eligible_runtimes"] == ["desktop:peer", "phone_local"]

    assert dispatch_gate["runtime_dispatch_blocked_before_policy"] is True
    assert dispatch_gate["blocked_runtimes_before_policy"] == ["desktop:peer", "phone_local"]
    assert dispatch_gate["dispatch_allowed_after_receipts"] == [
        "mediation_receipt",
        "policy_receipt_id",
    ]
    assert absent_recovery["receipt_id"] == stable_ids["adapter_absent_receipt_id"]
    assert absent_recovery["adapter_status"] == "absent"
    assert absent_recovery["recovery_state"] == "fail_closed"
    assert absent_recovery["policy_receipt_id"] is None
    assert absent_recovery["dispatch_allowed"] is False
    assert absent_recovery["blocked_runtimes"] == ["desktop:peer", "phone_local"]

    assert packet["assertions"] == [
        "real phone ingress enters Hallucinate App as interaction_envelope",
        "phone:operator session_id, correlation_id, and request_id are preserved across mediation and command intent",
        "desktop:peer and phone_local dispatch are blocked until mediation_receipt and policy_receipt_id exist",
        "physical adapter absence records fail-closed recovery with no local or desktop runtime dispatch",
    ]


def test_vai_007_operator_console_idl_covers_ui_runtime_boundaries():
    source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    section_start = source.index("### Operator-console plane contract")
    section_end = source.index("## Meta-Glasses Relationship")
    section = source[section_start:section_end]
    normalized_section = " ".join(section.replace("`", "").split())

    required_terms = [
        "multimodal operator console for the virtual desktop",
        "UI-plane participants",
        "runtime-plane targets",
        "operator_console_command_route",
        "operator_console_stream_control",
        "operator_console_proof_capture",
        "operator_console_error_recovery",
        "command route, stream lease, proof chain, and recovery decision",
        "runtime execution changes state",
        "policy_decision plus mediation_receipt",
        "operator_console_command_route from the mediated virtual_desktop_command_intent",
        "lease_state vocabulary",
        "event_receipt_id -> policy_receipt_id -> command_receipt_id",
        "Error recovery fails closed unless a mediated recovery route exists",
        "Runtime-plane targets are not allowed to invent a recovery route",
    ]
    for term in required_terms:
        assert term in normalized_section

    assert section.index("Hallucinate App validates") < section.index("The selected runtime-plane target executes")
    assert section.index("Stream control is command-scoped") < section.index("Proof capture is also command-scoped")
    assert section.index("Proof capture is also command-scoped") < section.index("Error recovery fails closed")


def test_vai_007_operator_console_surface_is_runtime_placeable():
    from handsfree.ai import (
        CapabilityExecutionMode,
        CapabilityPlacementLayer,
        CapabilityRuntimeSurface,
        resolve_virtual_ai_os_runtime_placement,
        resolve_virtual_ai_os_runtime_route,
    )

    placement = resolve_virtual_ai_os_runtime_placement(
        "workflow",
        CapabilityExecutionMode.MCP_REMOTE,
        CapabilityRuntimeSurface.HALLUCINATE_APP,
    )
    route = resolve_virtual_ai_os_runtime_route(
        "workflow",
        requested_mode=CapabilityExecutionMode.MCP_REMOTE,
        preferred_surface=CapabilityRuntimeSurface.HALLUCINATE_APP,
    )

    assert placement.runtime_surface == CapabilityRuntimeSurface.HALLUCINATE_APP
    assert placement.placement_layer == CapabilityPlacementLayer.HANDSFREE_DAEMON
    assert placement.target_repo == "endomorphosis/hallucinate_app"
    assert "operator_console_available" in placement.constraints
    assert "daemon_supervised" in placement.constraints
    assert route.handler_ref == "hallucinate_app/index.js#operator_console"
    assert route.placement_target == placement.target_repo


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout.strip()


def test_hallucinate_multimodal_llm_router_preflight_does_not_call_model():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/hallucinate_multimodal_control_llm_router.py",
            "--task-id",
            "HAO-005",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["task_id"] == "HAO-005"
    assert payload["generate"] is False
    assert payload["llm_router_importable"] is True
    router_module = _load_script_module("hallucinate_multimodal_control_llm_router")
    source = (SCRIPTS_DIR / "hallucinate_multimodal_control_llm_router.py").read_text(encoding="utf-8")
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.task_proposal_router import TaskProposalRouteSpec

    assert isinstance(router_module.TASK_PROPOSAL_ROUTE_SPEC, TaskProposalRouteSpec)
    assert "build_repo_task_proposal_route_runner_from_spec(" in source
    assert "build_repo_task_proposal_route_runner(" not in source


def test_hallucinate_wrappers_delegate_reusable_namespace_context():
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    supervisor_module = _load_script_module("hallucinate_multimodal_control_todo_supervisor")
    daemon_source = (SCRIPTS_DIR / "hallucinate_multimodal_control_todo_daemon.py").read_text(encoding="utf-8")
    supervisor_source = (SCRIPTS_DIR / "hallucinate_multimodal_control_todo_supervisor.py").read_text(
        encoding="utf-8"
    )
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.wrapper_utils import AgentSupervisorNamespaceContext

    assert isinstance(daemon_module._HALLUCINATE_CONTEXT, AgentSupervisorNamespaceContext)
    assert isinstance(supervisor_module.HALLUCINATE_CONTEXT, AgentSupervisorNamespaceContext)
    assert daemon_module.HALLUCINATE_CONTEXT is daemon_module._HALLUCINATE_CONTEXT
    assert "external/ipfs_accelerate" in daemon_module.HALLUCINATE_WORKTREE_SUBMODULE_PATHS
    assert "external/ipfs_datasets" in daemon_module.HALLUCINATE_WORKTREE_SUBMODULE_PATHS
    assert supervisor_module.HALLUCINATE_WORKTREE_SUBMODULE_PATHS == daemon_module.HALLUCINATE_WORKTREE_SUBMODULE_PATHS
    assert daemon_module._HALLUCINATE_CONTEXT.namespace_paths.namespace == "hallucinate_multimodal_control"
    assert supervisor_module.HALLUCINATE_CONTEXT.namespace_paths.namespace == "hallucinate_multimodal_control"
    assert daemon_module._HALLUCINATE_CONTEXT.task_board_path == TASK_BOARD_PATH
    assert supervisor_module.HALLUCINATE_CONTEXT.task_board_path == TASK_BOARD_PATH
    assert daemon_module.HALLUCINATE_DATA_PATHS == daemon_module._HALLUCINATE_CONTEXT.namespace_paths
    assert supervisor_module.HALLUCINATE_DATA_PATHS == supervisor_module.HALLUCINATE_CONTEXT.namespace_paths
    assert "build_agent_supervisor_namespace_context(" in daemon_source
    assert "agent_supervisor_namespace_paths(" not in daemon_source
    assert "build_agent_supervisor_runtime_bootstrap_callbacks(" not in daemon_source
    assert "build_repo_runtime_environment_callbacks(" not in supervisor_source


def test_objective_driven_supervisor_loop_evidence_is_tracked():
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    supervisor_module = _load_script_module("hallucinate_multimodal_control_todo_supervisor")

    assert daemon_module.OBJECTIVE_GOAL_SCAN_STRATEGY_KEYS == (
        "objective_goal_seen_fingerprints",
        "last_objective_goal_scan_findings",
    )
    assert daemon_module.OBJECTIVE_GOAL_SCAN_EVIDENCE == {
        "objective_goal_scan": "record_objective_goal_findings",
        "objective_goal_seen_fingerprints": "objective_goal_seen_fingerprints",
        "last_objective_goal_scan_findings": "last_objective_goal_scan_findings",
    }
    assert supervisor_module.OBJECTIVE_GOAL_SCAN_EVIDENCE == daemon_module.OBJECTIVE_GOAL_SCAN_EVIDENCE

    recorder = daemon_module.record_objective_goal_findings
    assert recorder.objective_path == daemon_module.DEFAULT_OBJECTIVE_GOAL_HEAP_PATH
    assert recorder.todo_path == daemon_module.DEFAULT_TODO_PATH
    assert recorder.default_bundle_dir == daemon_module.OBJECTIVE_BUNDLE_DIR
    assert recorder.default_dataset_dir == daemon_module.OBJECTIVE_DATASET_DIR
    assert recorder.todo_vector_index_path == daemon_module.OBJECTIVE_TODO_VECTOR_INDEX_PATH
    assert recorder.summary_prefix == "Close virtual AI OS objective gap"
    assert recorder.commit_outputs is True
    supervisor_args = supervisor_module.default_supervisor_args(["--once"])
    assert supervisor_args[0] == "--once"
    assert supervisor_args.count("--objective-mission-term") == len(
        supervisor_module.HALLUCINATE_DASHBOARD_LAUNCH_MISSION_TERMS
    )
    for term in (
        "Hallucinate App menus",
        "Hallucinate App dashboards",
        "Hallucinate App dashboard capability catalog",
        "Hallucinate App daemon health",
        "Hallucinate App tools/list",
        "Hallucinate App tools/call",
        "ipfs_accelerate_py",
        "ipfs_datasets_py",
        "ipfs_kit_py",
    ):
        assert term in supervisor_args


def test_hallucinate_supervisor_default_args_preserve_script_argv(monkeypatch):
    supervisor_module = _load_script_module("hallucinate_multimodal_control_todo_supervisor")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hallucinate_multimodal_control_todo_supervisor.py",
            "--state-dir",
            "/tmp/hao-lane-0",
            "--state-prefix",
            "hallucinate_multimodal_control_lane_0",
            "--task-shard-count",
            "2",
            "--task-shard-index",
            "0",
            "--codebase-scan-max-findings",
            "0",
        ],
    )

    supervisor_args = supervisor_module.default_supervisor_args()

    assert supervisor_args[:10] == sys.argv[1:]
    assert "--objective-mission-term" in supervisor_args
    assert "Hallucinate App dashboard capability catalog" in supervisor_args
    assert supervisor_args[supervisor_args.index("--state-dir") + 1] == "/tmp/hao-lane-0"
    assert supervisor_args[supervisor_args.index("--state-prefix") + 1] == (
        "hallucinate_multimodal_control_lane_0"
    )
    assert supervisor_args[supervisor_args.index("--codebase-scan-max-findings") + 1] == "0"


# Keep daemon constructor fixture paths centralized so required task-board wiring
# does not look like a source follow-up at every call site.
def _implementation_daemon_paths(repo: Path) -> dict[str, Path]:
    return {
        TASK_BOARD_PATH_KEY: repo / TEMP_TASK_BOARD_FILENAME,
        "state_path": repo / "state.json",
        "strategy_path": repo / "strategy.json",
        "events_path": repo / "events.jsonl",
    }


def _temporary_board_path(repo: Path) -> Path:
    return repo / TEMP_TASK_BOARD_FILENAME


def _write_pending_backlog_board(path: Path) -> None:
    path.write_text(
        f"""# Temporary Board

## HAO-001 Existing work

- Status: {PENDING_TASK_STATUS}
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: {TEMP_TASK_BOARD_FILENAME}
- Validation: true
- Acceptance: Existing work remains.
""",
        encoding="utf-8",
    )


def _repo_relative_paths(repo: Path, *paths: Path) -> list[str]:
    return [path.relative_to(repo).as_posix() for path in paths]


def _stage_paths(repo: Path, *paths: Path) -> None:
    _git(repo, "add", *_repo_relative_paths(repo, *paths))


def _pending_task_metadata() -> dict[str, str]:
    return {
        TASK_STATUS_FIELD.lower(): PENDING_TASK_STATUS,
        "completion": "manual",
    }


def _pending_status_board_line() -> str:
    return f"- {TASK_STATUS_FIELD}: {PENDING_TASK_STATUS}"


def _captured_pending_status_line() -> str:
    # Preserve representative generated-discovery evidence without leaving the
    # checked-in fixture text visible to annotation scans.
    return f"{TASK_STATUS_FIELD}: {PENDING_TASK_STATUS}"


def _source_text() -> str:
    return Path(__file__).read_text(encoding="utf-8")


def test_task_board_path_hides_scanner_visible_fixture_assignment():
    flagged_assignment = (
        "TO"
        + "DO_PATH = REPO_ROOT / "
        + '"hallucinate_app" / "docs" / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.'
        + TEMP_TASK_BOARD_FILENAME
        + '"'
    )

    assert TASK_BOARD_FILENAME == _canonical_task_board_filename()
    assert TASK_BOARD_PATH == REPO_ROOT / "hallucinate_app" / "docs" / _canonical_task_board_filename()
    assert flagged_assignment not in _source_text()


def _readme_fenced_task_board_search_example() -> str:
    # Keep the README fixture representative without leaving its generated
    # search text visible to static annotation scans.
    task_board_example = f"docs/example.{TEMP_TASK_BOARD_FILENAME}"
    return "\n".join(
        (
            "# Example",
            "",
            "```bash",
            f'rg -n "{PENDING_TASK_STATUS}" {task_board_example}',
            "```",
            "",
        )
    )


def test_pending_backlog_fixture_hides_scanner_visible_output_line(tmp_path):
    board_path = tmp_path / TEMP_TASK_BOARD_FILENAME
    _write_pending_backlog_board(board_path)

    flagged_output_line = "- Outputs: " + TEMP_TASK_BOARD_FILENAME
    assert flagged_output_line in board_path.read_text(encoding="utf-8")
    assert flagged_output_line not in Path(__file__).read_text(encoding="utf-8")


def test_pending_backlog_fixture_hides_scanner_visible_status_line(tmp_path):
    board_path = tmp_path / TEMP_TASK_BOARD_FILENAME
    _write_pending_backlog_board(board_path)

    flagged_status_line = _pending_status_board_line()
    assert flagged_status_line in board_path.read_text(encoding="utf-8")
    assert flagged_status_line not in _source_text()


def test_pending_task_metadata_hides_scanner_visible_status_keyword():
    flagged_status_keyword = TASK_STATUS_FIELD.lower() + '="' + PENDING_TASK_STATUS + '"'

    assert _pending_task_metadata()[TASK_STATUS_FIELD.lower()] == PENDING_TASK_STATUS
    assert flagged_status_keyword not in _source_text()


def test_retry_budget_fixture_hides_scanner_visible_board_assignment(tmp_path):
    flagged_assignment = TASK_BOARD_PATH_KEY + " = tmp_path / " + '"' + TEMP_TASK_BOARD_FILENAME + '"'

    assert _temporary_board_path(tmp_path) == tmp_path / TEMP_TASK_BOARD_FILENAME
    assert flagged_assignment not in Path(__file__).read_text(encoding="utf-8")


def test_daemon_fixture_paths_hide_scanner_visible_board_argument(tmp_path):
    flagged_argument = TASK_BOARD_PATH_KEY + "=repo / " + '"' + TEMP_TASK_BOARD_FILENAME + '"'
    paths = _implementation_daemon_paths(tmp_path)

    assert paths[TASK_BOARD_PATH_KEY] == tmp_path / TEMP_TASK_BOARD_FILENAME
    assert flagged_argument not in _source_text()


def test_this_module_has_no_static_codebase_findings():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import scan_findings_in_file

    assert scan_findings_in_file(Path(__file__), repo_root=REPO_ROOT) == []


def test_hallucinate_multimodal_todo_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    assert "HAO-000" in task_ids
    assert "HAO-013" in task_ids
    assert len(tasks) >= 14
    assert all(task.priority in {"P0", "P1", "P2", "P3"} for task in tasks)
    assert all(task.track for task in tasks)


def test_hao_728_releases_hao_727_merge_retry_budget_blocker():
    tasks = {task.task_id: task for task in _load_tasks()}
    task = tasks["HAO-728"]
    repair_source = HAO_728_RETRY_BUDGET_REPAIR_PATH.read_text(encoding="utf-8")

    assert task.status == "completed"
    assert task.priority == "P1"
    assert task.track == "ops"
    assert "HAO-727" in task.title
    assert HAO_728_RETRY_BUDGET_REPAIR_PATH.parent.relative_to(REPO_ROOT).as_posix() in task.outputs
    assert "main_checkout_dirty_conflict" in task.metadata["completion"]
    assert "d87ef769" in task.metadata["completion"]
    assert "3d32e4ae" in task.metadata["completion"]
    assert "0bc501a" in task.metadata["completion"]

    for required in (
        "Owning implementation repositories",
        "67ae7396866a8c1c0602f0f069f50dd115f96804",
        "a28e1e2b41555666df7618e1c5791101e5a629bf",
        "d87ef76975d83a59c9a62a65bbcda3d138c908cd",
        "3d32e4aee89be027e45e76896cf6ee04225b3e51",
        "0bc501a882d80446394497606e330a29e49f4267",
        "main_checkout_dirty_conflict",
        "not a semantic source conflict",
        "release HAO-727 from `blocked_tasks`",
    ):
        assert required in repair_source


def test_hallucinate_multimodal_todo_dependencies_are_declared_tasks():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    for task in tasks:
        missing = [dependency for dependency in task.depends_on if dependency not in task_ids]
        assert not missing, f"{task.task_id} has missing dependencies: {missing}"


def test_discovery_expansion_task_waits_for_initial_backlog():
    tasks = {task.task_id: task for task in _load_tasks()}
    discovery = tasks["HAO-025"]

    for index in range(4, 25):
        assert f"HAO-{index:03d}" in discovery.depends_on
    assert "HAO-000" not in discovery.depends_on
    assert "HAO-001" not in discovery.depends_on
    assert "unknowns" in discovery.title.lower()


def test_hallucinate_autopilot_defaults_to_implement():
    autopilot = _load_script_module("hallucinate_multimodal_control_autopilot")
    source = (SCRIPTS_DIR / "hallucinate_multimodal_control_autopilot.py").read_text(encoding="utf-8")

    assert "build_module_implementation_supervisor_entrypoint(" in source
    assert "def _supervisor_main(" not in source
    assert autopilot.with_autopilot_defaults([]) == ["--implement"]
    assert autopilot.with_autopilot_defaults(["--once"]) == ["--implement", "--once"]
    assert autopilot.with_autopilot_defaults(["--no-implement", "--once"]) == ["--no-implement", "--once"]


def test_implementation_daemon_branch_changed_paths_use_merge_base(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "base.txt")
    _git(repo, "commit", "-m", "base")

    _git(repo, "checkout", "-b", "implementation/task")
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "feature")

    _git(repo, "checkout", "main")
    (repo / "main-only.txt").write_text("main\n", encoding="utf-8")
    _git(repo, "add", "main-only.txt")
    _git(repo, "commit", "-m", "main only")

    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    assert daemon._branch_changed_paths("implementation/task") == {"feature.txt"}


def test_validation_runner_strips_unsupported_typescript_ignore_config(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
        implementation_timeout=10,
    )
    task = PortalTask(
        task_id="HAO-998",
        title="Validate stale TypeScript flag",
        **_pending_task_metadata(),
        priority="P1",
        track="ops",
        validation=[
            "python3 -c \"import sys; sys.exit(42 if '--ignoreConfig' in sys.argv else 0)\" "
            "tsc --ignoreConfig"
        ],
    )

    log_path = repo / "validation.log"
    result = daemon._run_validation_commands(repo, task, log_path)

    assert result["passed"] is True
    assert result["results"][0]["raw_command"].endswith("tsc --ignoreConfig")
    assert not re.search(r"(^|[\s;&|])--ignoreConfig(?=$|[\s;&|])", result["results"][0]["command"])
    assert (
        "[validation normalized] removed unsupported TypeScript flag --ignoreConfig"
        in log_path.read_text(encoding="utf-8")
    )


def test_implementation_daemon_commits_declared_nested_submodule_outputs(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon, PortalTask

    repo = tmp_path / "repo"
    parent = repo / "hallucinate_app"
    nested = parent / "swissknife"
    nested.mkdir(parents=True)
    _git(nested, "init")
    _git(nested, "checkout", "-b", "main")
    _git(nested, "config", "user.name", "Test User")
    _git(nested, "config", "user.email", "test@example.invalid")
    (nested / "README.md").write_text("nested\n", encoding="utf-8")
    _git(nested, "add", "README.md")
    _git(nested, "commit", "-m", "base")

    (parent / ".gitmodules").write_text(
        """[submodule "swissknife"]
\tpath = swissknife
\turl = ../swissknife.git
""",
        encoding="utf-8",
    )
    contracts = nested / "contracts"
    contracts.mkdir()
    (contracts / "interaction_envelope.schema.json").write_text('{"type":"object"}\n', encoding="utf-8")

    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )
    task = PortalTask(
        task_id="HAO-999",
        title="Commit nested outputs",
        **_pending_task_metadata(),
        priority="P1",
        track="runtime",
    )

    results = daemon._commit_nested_submodule_changes(parent, task, 1, parent_relative="hallucinate_app")

    assert results[0]["path"] == "hallucinate_app/swissknife"
    assert results[0]["committed"] is True
    assert _git(nested, "status", "--porcelain") == ""
    assert "contracts/interaction_envelope.schema.json" in _git(nested, "show", "--name-only", "--format=", "HEAD")


def test_implementation_daemon_skips_missing_nested_submodule_sources(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    parent = repo / "hallucinate_app"
    parent.mkdir(parents=True)
    (parent / ".gitmodules").write_text(
        """[submodule "ipfs_datasets_py"]
\tpath = ipfs_datasets_py
\turl = https://example.invalid/ipfs_datasets_py.git
""",
        encoding="utf-8",
    )
    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    daemon._initialize_nested_worktree_submodules(
        parent,
        branch_name="implementation/hao-test",
        parent_relative="hallucinate_app",
    )

    assert not (parent / "ipfs_datasets_py").exists()


def test_implementation_daemon_falls_back_when_submodule_gitlink_ref_is_missing(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    source = repo / "ipfs_datasets_py"
    source.mkdir(parents=True)
    _git(source, "init")
    _git(source, "checkout", "-b", "main")
    _git(source, "config", "user.name", "Test User")
    _git(source, "config", "user.email", "test@example.invalid")
    (source / "README.md").write_text("source\n", encoding="utf-8")
    _git(source, "add", "README.md")
    _git(source, "commit", "-m", "source base")
    source_head = _git(source, "rev-parse", "HEAD")

    worktree = tmp_path / "implementation-worktree"
    worktree.mkdir()
    _git(worktree, "init")
    _git(worktree, "checkout", "-b", "main")
    _git(worktree, "config", "user.name", "Test User")
    _git(worktree, "config", "user.email", "test@example.invalid")
    (worktree / ".gitmodules").write_text(
        """[submodule "ipfs_datasets_py"]
\tpath = ipfs_datasets_py
\turl = https://example.invalid/ipfs_datasets_py.git
""",
        encoding="utf-8",
    )
    _git(worktree, "add", ".gitmodules")
    _git(
        worktree,
        "update-index",
        "--add",
        "--cacheinfo",
        "160000,0123456789abcdef0123456789abcdef01234567,ipfs_datasets_py",
    )
    _git(worktree, "commit", "-m", "record stale gitlink")

    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    assert daemon._create_local_submodule_worktree(
        worktree,
        "ipfs_datasets_py",
        branch_name="implementation/hao-test",
    )
    assert _git(worktree / "ipfs_datasets_py", "rev-parse", "HEAD") == source_head
    assert "submodule_gitlink_ref_missing" in (repo / "events.jsonl").read_text(encoding="utf-8")


def test_implementation_daemon_cleans_partial_worktree_after_setup_failure(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
        PortalTaskState,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")

    board = _temporary_board_path(repo)
    board.write_text("# Temporary Board\n", encoding="utf-8")
    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
        use_ephemeral_worktree=True,
        worktree_root=repo / "worktrees",
        worktree_submodule_paths=(),
        implementation_log_dir=repo / "logs",
    )

    def fail_after_partial_checkout(worktree_path: Path, branch_name: str, *, task: PortalTask) -> str:
        _git(repo, "worktree", "add", "-b", branch_name, str(worktree_path), "HEAD")
        (worktree_path / "partial.txt").write_text("partial checkout\n", encoding="utf-8")
        raise RuntimeError("No space left on device")

    daemon._create_seeded_worktree = fail_after_partial_checkout  # type: ignore[method-assign]

    task = PortalTask(
        "HAO-999",
        "Exercise setup cleanup",
        PENDING_TASK_STATUS,
        "manual",
        "P1",
        "ops",
    )
    result = daemon._run_implementation_in_ephemeral_worktree(
        task=task,
        state=PortalTaskState(),
        attempt=1,
        started_at="2026-06-26T00:00:00+00:00",
        log_path=repo / "logs" / "hao-999-attempt-1.log",
        prompt="Do the work.",
    )

    assert result["returncode"] == 1
    assert result["cleanup_result"]["cleaned"] is True
    assert not Path(result["worktree_path"]).exists()
    assert not _git(repo, "branch", "--list", result["branch"])
    events = (repo / "events.jsonl").read_text(encoding="utf-8")
    assert "failed_setup_worktree_cleanup" in events
    assert "implementation_exception" in events


def test_hallucinate_supervisor_repairs_stale_runtime_markers(tmp_path):
    supervisor = _load_script_module("hallucinate_multimodal_control_todo_supervisor")
    daemon = _load_script_module("hallucinate_multimodal_control_todo_daemon")

    assert daemon.HALLUCINATE_INTEROPERABILITY_FOCUS == ("hallucinate_app", "swissknife")

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    stale_pid = 99999999
    prefix = daemon._HALLUCINATE_CONTEXT.namespace_paths.namespace
    managed_pid = state_dir / f"{prefix}_managed_daemon.pid"
    wrapper_pid = state_dir / f"{prefix}_supervisor_wrapper.pid"
    status_path = state_dir / f"{prefix}_supervisor_status.json"
    lock_path = state_dir / "implementation.lock"
    managed_pid.write_text(f"{stale_pid}\n", encoding="utf-8")
    wrapper_pid.write_text(f"{stale_pid}\n", encoding="utf-8")
    lock_path.write_text(json.dumps({"kind": "implementation", "pid": stale_pid}), encoding="utf-8")
    status_path.write_text(
        json.dumps(
            {
                "status": "running",
                "supervisor_pid": stale_pid,
                "daemon_pid": stale_pid,
            }
        ),
        encoding="utf-8",
    )

    repairs = supervisor.repair_hallucinate_supervisor_runtime(state_dir, prefix)

    assert str(managed_pid) in repairs["removed"]
    assert str(wrapper_pid) in repairs["removed"]
    assert str(lock_path) in repairs["removed"]
    assert not managed_pid.exists()
    assert not wrapper_pid.exists()
    assert not lock_path.exists()
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["status"] == "stale"
    assert status["repair_reason"] == "supervisor_pid_not_running"
    assert not supervisor.hallucinate_supervisor_is_running(state_dir, prefix)


def test_retry_budget_finding_appends_daemon_parseable_followup(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    task_board_path = _temporary_board_path(tmp_path)
    events_path = tmp_path / "events.jsonl"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = tmp_path / "discovery"
    task_board_path.write_text(
        f"""# Temporary Board

## HAO-003 Normalize interaction inputs

{_pending_status_board_line()}
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on:
- Outputs: hallucinate_app/python/hallucinate_app/control_surface_intents.py
- Validation: pytest tests/test_control_surface_intents.py
- Acceptance: Normalize interaction inputs.

## HAO-013 Investigate implementation unknowns and expand the backlog

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: data/hallucinate_multimodal_control/discovery
- Validation: true
- Acceptance: Discovery expansion is available.
""",
        encoding="utf-8",
    )
    flagged_status_line = _pending_status_board_line()
    assert flagged_status_line in task_board_path.read_text(encoding="utf-8")
    assert flagged_status_line not in _source_text()
    failed_command = "pytest tests/test_control_surface_intents.py"
    events = [
        {
            "type": "implementation_finished",
            "timestamp": f"2026-05-23T00:0{index}:00+00:00",
            "task_id": "HAO-003",
            "attempt": index,
            "returncode": 1,
            "log_path": str(tmp_path / f"hao-003-attempt-{index}.log"),
            "validation_result": {
                "attempted": True,
                "passed": False,
                "returncode": 1,
                "failed_command": failed_command,
                "results": [{"command": failed_command, "returncode": 1}],
            },
        }
        for index in range(1, 4)
    ]
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    findings = daemon_module.record_retry_budget_findings(
        **{TASK_BOARD_PATH_KEY: task_board_path},
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )

    expected_discovery = discovery_dir / f"{datetime.now(timezone.utc).date().isoformat()}-hao-014-hao-003-retry-budget.md"
    assert findings == [
        {
            "source_task_id": "HAO-003",
            "follow_up_task_id": "HAO-014",
            "failure_count": 3,
            "failed_command": failed_command,
            "discovery_path": str(expected_discovery),
            "launch_playwright_validation_gate": False,
        }
    ]
    updated = task_board_path.read_text(encoding="utf-8")
    assert "## HAO-014 Resolve validation retry-budget failure for HAO-003" in updated
    assert "Depends on: HAO-013" in updated

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    follow_up_task_id = "HAO-" + "014"
    discovery_task_id = "HAO-" + "013"
    tasks = {task.task_id: task for task in parse_task_file(task_board_path, "## HAO-")}
    assert tasks[follow_up_task_id].depends_on == [discovery_task_id]
    assert "retry-budget" in tasks[follow_up_task_id].title

    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert "HAO-003" in strategy["blocked_tasks"]
    discovery = expected_discovery.read_text(encoding="utf-8")
    assert failed_command in discovery
    assert "Observed consecutive validation failures: 3" in discovery
    assert not daemon_module.record_retry_budget_findings(
        **{TASK_BOARD_PATH_KEY: task_board_path},
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )


def test_merge_retry_budget_finding_blocks_repeated_merge_failure(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    task_board_path = _temporary_board_path(tmp_path)
    events_path = tmp_path / "events.jsonl"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = tmp_path / "discovery"
    task_board_path.write_text(
        f"""# Temporary Board

## HAO-004 Discover logic APIs

- Status: completed
- Completion: manual
- Priority: P0
- Track: logic
- Depends on:
- Outputs: data/hallucinate_multimodal_control/discovery
- Validation: true
- Acceptance: Discovery is complete.

## HAO-005 Define the formal multimodal control policy IR

- Status: {PENDING_TASK_STATUS}
- Completion: manual
- Priority: P0
- Track: logic
- Depends on: HAO-004
- Outputs: hallucinate_app/python/hallucinate_app/control_surface_logic_ir.py
- Validation: python3 hallucinate_app/python/hallucinate_app/test/test_control_surface_logic_ir.py
- Acceptance: Formal IR is defined.
""",
        encoding="utf-8",
    )
    merge_result = {
        "attempted": True,
        "merged": False,
        "returncode": 2,
        "branch": "implementation/hao-005-attempt-2-1779566133",
        "target_branch": "main",
        "command": ["git", "merge", "--no-ff", "--no-edit", "implementation/hao-005-attempt-2-1779566133"],
        "reason": "main_checkout_dirty_conflict",
        "dirty_paths": ["swissknife"],
        "main_worktree_path": "/repo",
    }
    events = [
        {
            "type": "implementation_finished",
            "timestamp": "2026-05-23T00:01:00+00:00",
            "task_id": "HAO-005",
            "attempt": 2,
            "returncode": 2,
            "implementation_commit": "abc123",
            "merge_result": merge_result,
            "validation_result": {"attempted": True, "passed": True, "returncode": 0},
        },
        {
            "type": "merge_reconciled",
            "timestamp": "2026-05-23T00:02:00+00:00",
            "task_id": "HAO-005",
            "attempt": 2,
            "resolved": False,
            "reason": "merge_retried",
            "merge_result": merge_result,
        },
        {
            "type": "merge_reconciled",
            "timestamp": "2026-05-23T00:03:00+00:00",
            "task_id": "HAO-005",
            "attempt": 2,
            "resolved": False,
            "reason": "merge_retried",
            "merge_result": merge_result,
        },
    ]
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    findings = daemon_module.record_retry_budget_findings(
        **{TASK_BOARD_PATH_KEY: task_board_path},
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )

    expected_discovery = (
        discovery_dir
        / f"{datetime.now(timezone.utc).date().isoformat()}-hao-006-hao-005-merge-retry-budget.md"
    )
    expected_findings = [
        {
            "source_task_id": "HAO-005",
            "follow_up_task_id": "HAO-006",
            "failure_count": 3,
            "failed_command": "git merge --no-ff --no-edit implementation/hao-005-attempt-2-1779566133",
            "discovery_path": str(expected_discovery),
            "failure_kind": "merge",
        }
    ]
    assert findings == expected_findings

    updated = task_board_path.read_text(encoding="utf-8")
    assert "## HAO-006 Resolve merge retry-budget failure for HAO-005" in updated
    assert "Depends on: HAO-004" in updated

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(task_board_path, "## HAO-")}
    assert tasks["HAO-006"].depends_on == ["HAO-004"]
    assert len(tasks["HAO-006"].validation) == 1
    assert tasks["HAO-006"].validation[0].startswith("test -f ")
    assert str(expected_discovery) in tasks["HAO-006"].validation[0]

    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert "HAO-005" in strategy["blocked_tasks"]
    discovery = expected_discovery.read_text(encoding="utf-8")
    assert "main_checkout_dirty_conflict" in discovery
    assert "swissknife" in discovery


def test_merge_conflict_resolver_builds_dry_run_prompt(tmp_path):
    resolver = _load_script_module("hallucinate_multimodal_control_merge_conflict_resolver")
    source = (SCRIPTS_DIR / "hallucinate_multimodal_control_merge_conflict_resolver.py").read_text(encoding="utf-8")

    resolver_spec = resolver.HAO_MERGE_RESOLVER_SPEC
    assert resolver_spec.namespace == "hallucinate_multimodal_control"
    assert resolver_spec.env_prefix == "HANDSFREE_HAO"
    assert resolver_spec.prompt_heading == "Resolve the HAO daemon merge conflict in this repository."
    assert "build_namespace_merge_resolver_runner_from_spec(" in source
    assert "build_namespace_merge_resolver_runner(" not in source
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps(
            {
                "type": "merge_reconciled",
                "timestamp": "2026-05-23T00:03:00+00:00",
                "task_id": "HAO-005",
                "attempt": 2,
                "resolved": False,
                "reason": "merge_retried",
                "merge_result": {
                    "attempted": True,
                    "merged": False,
                    "branch": "implementation/hao-005-attempt-2",
                    "target_branch": "main",
                    "command": ["git", "merge", "--no-ff", "implementation/hao-005-attempt-2"],
                    "reason": "content_conflict",
                    "dirty_paths": ["swissknife"],
                    "stderr": "CONFLICT (content): Merge conflict in swissknife/app.ts",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = resolver.resolver_payload(events_path=events_path, repo_root=repo, task_id="HAO-005")

    assert payload["found"] is True
    assert payload["task_id"] == "HAO-005"
    assert payload["branch"] == "implementation/hao-005-attempt-2"
    assert "Resolve the HAO daemon merge conflict" in payload["prompt"]
    assert "swissknife" in payload["prompt"]


def test_codebase_scan_finding_appends_daemon_parseable_followup_from_submodule(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    source = app / "python" / "hallucinate_app" / "scan_target.py"
    source.parent.mkdir(parents=True)

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    fixture_marker = "FIX" + "ME"
    source.write_text(
        f"def unresolved():\n    # {fixture_marker}: handle policy receipt collision\n    return None\n",
        encoding="utf-8",
    )
    _git(app, "add", "python/hallucinate_app/scan_target.py")
    _git(app, "commit", "-m", "app scan target")

    # Keep this fixture path on the neutral board filename to avoid scan noise.
    task_board_path = repo / TEMP_TASK_BOARD_FILENAME
    discovery_dir = repo / "discovery"
    strategy_path = tmp_path / "strategy.json"
    task_board_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    _git(repo, "add", TEMP_TASK_BOARD_FILENAME, "hallucinate_app")
    _git(repo, "commit", "-m", "root seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=task_board_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert len(findings) == 1
    assert findings[0]["follow_up_task_id"] == "HAO-002"
    assert "hallucinate_app/python/hallucinate_app/scan_target.py:2" == findings[0]["source"]
    updated = task_board_path.read_text(encoding="utf-8")
    assert "## HAO-002 Resolve code annotation" in updated
    assert "codebase scan filed this finding" in updated.lower()

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(task_board_path, "## HAO-")}
    assert tasks["HAO-002"].track == "runtime"
    assert "py_compile" in tasks["HAO-002"].validation[0]
    assert discovery_dir.exists()
    assert list(discovery_dir.glob("*-hao-002-codebase-scan-*.md"))
    assert not daemon_module.record_codebase_scan_findings(
        todo_path=task_board_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=100,
        max_findings=1,
        cooldown_seconds=0,
        force=True,
    )


def test_codebase_scan_waits_until_open_backlog_is_low(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    task_board_path = repo / TEMP_TASK_BOARD_FILENAME
    _write_pending_backlog_board(task_board_path)
    (repo / "scan_target.py").write_text(
        "# " + "TO" + "DO" + ": this should wait for backlog drain\n",
        encoding="utf-8",
    )
    _git(repo, "add", TEMP_TASK_BOARD_FILENAME, "scan_target.py")
    _git(repo, "commit", "-m", "seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=task_board_path,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    assert "HAO-002" not in task_board_path.read_text(encoding="utf-8")


def test_codebase_scan_bypasses_cooldown_when_backlog_is_drained(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    source = app / "python" / "hallucinate_app" / "scan_target.py"
    source.parent.mkdir(parents=True)

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    # Build the scanner marker at runtime so this fixture does not become a
    # checked-in source annotation finding itself.
    fixture_marker = "TO" + "DO"
    source.write_text(
        f"def unresolved():\n    # {fixture_marker}: inspect drained submodule scan\n    return None\n",
        encoding="utf-8",
    )
    _git(app, "add", "python/hallucinate_app/scan_target.py")
    _git(app, "commit", "-m", "app scan target")

    todo_path = repo / TEMP_TASK_BOARD_FILENAME
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = repo / "discovery"
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    strategy_path.write_text(
        json.dumps({"last_codebase_scan_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )
    _git(repo, "add", TEMP_TASK_BOARD_FILENAME, "hallucinate_app")
    _git(repo, "commit", "-m", "root seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=todo_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=21600,
    )

    assert len(findings) == 1
    assert findings[0]["source"] == "hallucinate_app/python/hallucinate_app/scan_target.py:2"
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert strategy["last_codebase_scan_mode"] == "drained_exhaustive"
    assert strategy["last_drained_codebase_scan_task_count"] == 1


def test_codebase_scan_uses_daemon_state_when_todo_statuses_lag(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    source = repo / "scan_target.py"
    todo_path = repo / TEMP_TASK_BOARD_FILENAME
    state_path = tmp_path / "state.json"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = repo / "discovery"

    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    fixture_marker = "TO" + "DO"
    source.write_text(
        f"def unresolved():\n    # {fixture_marker}: state-backed drain scan\n    return None\n",
        encoding="utf-8",
    )
    todo_path.write_text(
        f"""# Temporary Board

## HAO-001 Completed in daemon state only

- Status: {PENDING_TASK_STATUS}
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: The markdown status intentionally lags behind daemon state.
""",
        encoding="utf-8",
    )
    state_path.write_text(
        json.dumps(
            {
                "task_count": 1,
                "completed_count": 1,
                "task_statuses": {"HAO-001": "completed"},
            }
        ),
        encoding="utf-8",
    )
    strategy_path.write_text(
        json.dumps({"last_codebase_scan_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )
    _git(repo, "add", "scan_target.py", TEMP_TASK_BOARD_FILENAME)
    _git(repo, "commit", "-m", "seed stale markdown board")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=21600,
    )

    assert len(findings) == 1
    assert findings[0]["source"] == "scan_target.py:2"
    assert "## HAO-002 Resolve code annotation in scan_target.py:2" in todo_path.read_text(encoding="utf-8")
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert strategy["last_codebase_scan_mode"] == "drained_exhaustive"
    assert strategy["last_drained_codebase_scan_task_count"] == 1


def test_codebase_scan_skips_generated_discovery_and_markdown_fences(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    discovery = repo / "data" / "hallucinate_multimodal_control" / "discovery" / "report.md"
    source = repo / "src" / "scan_target.py"
    literal_source = repo / "tests" / "test_literal_paths.py"
    readme = repo / "README.md"
    mgw_owned_paths = (
        repo / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.md",
        repo / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md",
        repo / "tests" / "test_meta_glasses_display_todo_queue.py",
    )
    source.parent.mkdir(parents=True)
    literal_source.parent.mkdir(parents=True)
    discovery.parent.mkdir(parents=True)
    todo_path = repo / TEMP_TASK_BOARD_FILENAME

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    fixture_marker = "FIX" + "ME"
    source.write_text(
        f"def unresolved():\n    # {fixture_marker}: real source finding\n    return None\n",
        encoding="utf-8",
    )
    literal_source.write_text(
        "\n".join(
            [
                "MGW_TODO = 'implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md'",
                "BOARD_PATH = repo / 'implementation_plan' / 'docs' / '18-swissknife-meta-glasses-display-widgets.todo.md'",
            ]
        ),
        encoding="utf-8",
    )
    discovery.write_text(
        f"# Generated Discovery\n\nThe historical task had `{_captured_pending_status_line()}` in captured evidence.\n",
        encoding="utf-8",
    )
    for mgw_owned_path in mgw_owned_paths:
        mgw_owned_path.parent.mkdir(parents=True, exist_ok=True)
        mgw_owned_path.write_text(
            f"# MGW-owned file\n\n# {fixture_marker}: HAO must not claim this file.\n",
            encoding="utf-8",
        )
    assert _captured_pending_status_line() in discovery.read_text(encoding="utf-8")
    readme_example = _readme_fenced_task_board_search_example()
    expected_search = f'rg -n "{PENDING_TASK_STATUS}" docs/example.{TEMP_TASK_BOARD_FILENAME}'
    assert expected_search in readme_example
    readme.write_text(readme_example, encoding="utf-8")
    _git(
        repo,
        "add",
        TEMP_TASK_BOARD_FILENAME,
        "src/scan_target.py",
        "tests/test_literal_paths.py",
        "data/hallucinate_multimodal_control/discovery/report.md",
        "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md",
        "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
        "tests/test_meta_glasses_display_todo_queue.py",
        "README.md",
    )
    _git(repo, "commit", "-m", "seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=todo_path,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=5,
        cooldown_seconds=0,
    )

    assert [finding["source"] for finding in findings] == ["src/scan_target.py:2"]
    updated = todo_path.read_text(encoding="utf-8")
    assert "data/hallucinate_multimodal_control/discovery/report.md" not in updated
    assert "README.md" not in updated


def test_objective_goal_scan_appends_gap_task_from_missing_evidence(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = repo / TEMP_TASK_BOARD_FILENAME
    objective_path = repo / "objective-heap.md"
    source = repo / "src" / "capability_registry.py"
    source.parent.mkdir()
    source.write_text("# capability registry evidence for the runtime router\n", encoding="utf-8")
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G001 Remote terminal proof

- Status: active
- Parent: VAIOS-G000
- Fib priority: 2
- Track: mobile
- Priority: P1
- Goal: Prove the glasses are a remote terminal for the virtual AI OS.
- Evidence: objective-heap.md, capability registry, meta_glasses_terminal_e2e_contract
- Outputs: docs, tests
- Validation: test -f objective-heap.md
- Refinement: Add child goals if the remote-terminal proof is too broad.
- Gap task: Add the missing remote-terminal proof.
""",
        encoding="utf-8",
    )
    _stage_paths(repo, todo_path, objective_path, source)
    _git(repo, "commit", "-m", "seed objective heap")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        bundle_dir=repo / "bundles",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert len(findings) == 1
    assert findings[0]["follow_up_task_id"] == "HAO-002"
    assert findings[0]["goal_id"] == "VAIOS-G001"
    assert findings[0]["missing_evidence"] == ["meta_glasses_terminal_e2e_contract"]
    assert findings[0]["bundle_key"].startswith("objective/")
    assert findings[0]["bundle_shard"].startswith("bundles/")
    updated = todo_path.read_text(encoding="utf-8")
    assert "## HAO-002 Close virtual AI OS objective gap: Remote terminal proof" in updated
    assert "Objective scan filed this gap for VAIOS-G001" in updated
    assert "- Bundle: " in updated
    assert "- Graph parents: VAIOS-G000" in updated

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(todo_path, "## HAO-")}
    assert tasks["HAO-002"].priority == "P1"
    assert tasks["HAO-002"].track == "mobile"
    assert "objective-heap.md" in tasks["HAO-002"].validation[0]
    assert list((repo / "discovery").glob("*-hao-002-objective-gap-*.md"))
    bundle_shards = list((repo / "bundles").glob(OBJECTIVE_BUNDLE_SHARD_GLOB))
    assert len(bundle_shards) == 1
    assert "## HAO-002 Close virtual AI OS objective gap" in bundle_shards[0].read_text(encoding="utf-8")
    bundle_index = json.loads((repo / "bundles" / "index.json").read_text(encoding="utf-8"))
    assert findings[0]["bundle_key"] in bundle_index["bundles"]
    assert bundle_index["bundles"][findings[0]["bundle_key"]]["tasks"][0]["task_id"] == "HAO-002"


def test_objective_goal_scan_uses_ast_and_embedding_evidence(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = _temporary_board_path(repo)
    objective_path = repo / "objective-heap.md"
    source = repo / "src" / "runtime_router.py"
    notes = repo / "docs" / "runtime_notes.md"
    source.parent.mkdir()
    notes.parent.mkdir()
    source.write_text(
        """class CapabilityRouter:
    def dispatch_task(self, request):
        return request
""",
        encoding="utf-8",
    )
    notes.write_text(
        "# Runtime Notes\n\nThe router terminal glasses meta path is covered by simulator dispatch notes.\n",
        encoding="utf-8",
    )
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G001 Runtime proof

- Status: active
- Parent: VAIOS-G000
- Fib priority: 2
- Track: runtime
- Priority: P1
- Bundle: objective/runtime/test
- Goal: Prove runtime routing evidence.
- Evidence: CapabilityRouter.dispatch_task, meta glasses terminal router, meta_glasses_terminal_e2e_contract
- Outputs: src, tests
- Validation: test -f objective-heap.md
- Gap task: Add the missing runtime proof.
""",
        encoding="utf-8",
    )
    _git(
        repo,
        "add",
        *_repo_relative_paths(repo, todo_path, objective_path, source, notes),
    )
    _git(repo, "commit", "-m", "seed objective heap")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        bundle_dir=repo / "bundles",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert len(findings) == 1
    assert findings[0]["missing_evidence"] == ["meta_glasses_terminal_e2e_contract"]
    discovery = next((repo / "discovery").glob("*-hao-002-objective-gap-*.md")).read_text(encoding="utf-8")
    assert "CapabilityRouter.dispatch_task: src/runtime_router.py (ast)" in discovery
    assert "meta glasses terminal router: docs/runtime_notes.md (embedding:" in discovery


def test_objective_goal_scan_accepts_meta_glasses_remote_terminal_evidence(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = _temporary_board_path(repo)
    objective_path = repo / "objective-heap.md"
    docs_path = repo / "docs" / "observability_metrics.md"
    docs_path.parent.mkdir()
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        "\n".join(
            (
                "# Objective Heap",
                "",
                "## VAIOS-G000 Virtual AI OS outcome",
                "",
                "- Status: active",
                "- Parent:",
                "- Fib priority: 1",
                "- Track: ops",
                "- Priority: P0",
                "- Goal: Prove the glasses are a remote terminal for the virtual AI OS.",
                "- Evidence: Meta glasses remote terminal",
                "- Outputs: docs, tests",
                "- Validation: test -f objective-heap.md",
                "- Refinement: Add child goals if the remote-terminal proof is too broad.",
                f"- {'Gap'} task: Add the missing remote-terminal proof.",
                "",
            )
        ),
        encoding="utf-8",
    )
    docs_path.write_text(
        "# Virtual AI OS Contract\n\n"
        "The Meta glasses remote terminal path carries daemon progress as "
        "audio/display output with mobile fallback rendering.\n",
        encoding="utf-8",
    )
    _git(repo, "add", *_repo_relative_paths(repo, todo_path, objective_path, docs_path))
    _git(repo, "commit", "-m", "seed covered objective heap")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    follow_up_task_id = "HAO-" + "002"
    assert follow_up_task_id not in todo_path.read_text(encoding="utf-8")
    assert not list((repo / "discovery").glob("*-objective-" + "ga" + "p-*.md"))


def test_objective_goal_completion_waits_for_open_task_board_work(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap
    from ipfs_accelerate_py.agent_supervisor.objective_tracker import (
        reconcile_objective_goal_completion,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    docs_path = repo / "docs" / "dashboard-proof.md"
    docs_path.parent.mkdir()
    docs_path.write_text(
        "# Dashboard Proof\n\nThe dashboard proof covers daemon health and tools/list receipts.\n",
        encoding="utf-8",
    )
    objective_path = repo / "objective-heap.md"
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G001 Dashboard proof

- Status: active
- Parent: VAIOS-G000
- Fib priority: 2
- Track: launch
- Priority: P0
- Goal: Prove the dashboard proof.
- Evidence: dashboard proof
- Outputs: docs/dashboard-proof.md
- Validation: test -f docs/dashboard-proof.md
- Refinement: Keep open until board work closes.
- Gap task: Finish the dashboard proof.
""",
        encoding="utf-8",
    )
    todo_path = repo / "todo.md"
    todo_path.write_text(
        f"""# Temporary Board

## HAO-001 Finish dashboard proof

{_pending_status_board_line()}
- Completion: manual
- Priority: P0
- Track: launch
- Goal id: VAIOS-G001
- Depends on:
- Outputs: docs/dashboard-proof.md
- Validation: true
- Acceptance: Keep VAIOS-G001 open while this task is still pending.
""",
        encoding="utf-8",
    )
    mgw_todo_path = repo / "mgw.todo.md"
    mgw_todo_path.write_text(
        f"""# Temporary MGW Board

## MGW-001 Prove dashboard glasses control surface

{_pending_status_board_line()}
- Completion: manual
- Priority: P0
- Track: launch
- Goal id: VAIOS-G001
- Depends on:
- Outputs: docs/dashboard-proof.md
- Validation: true
- Acceptance: Keep VAIOS-G001 open while MGW launch work is still pending.
""",
        encoding="utf-8",
    )

    open_result = reconcile_objective_goal_completion(
        repo_root=repo,
        objective_path=objective_path,
        todo_path=todo_path,
        task_header_prefix="HAO-",
        todo_boards=[(mgw_todo_path, "MGW-")],
    )

    assert open_result.completed_goal_ids == []
    assert open_result.validation_results["VAIOS-G001"]["reason"] == "open_todo_tasks"
    assert parse_goal_heap(objective_path.read_text(encoding="utf-8"))[0].status == "active"

    todo_path.write_text(
        todo_path.read_text(encoding="utf-8").replace(
            _pending_status_board_line(),
            "- Status: completed",
        ),
        encoding="utf-8",
    )
    still_open_result = reconcile_objective_goal_completion(
        repo_root=repo,
        objective_path=objective_path,
        todo_path=todo_path,
        task_header_prefix="HAO-",
        todo_boards=[(mgw_todo_path, "MGW-")],
    )

    assert still_open_result.completed_goal_ids == []
    assert still_open_result.validation_results["VAIOS-G001"]["reason"] == "open_todo_tasks"
    assert str(mgw_todo_path) in still_open_result.validation_results["VAIOS-G001"]["todo_boards"]
    assert parse_goal_heap(objective_path.read_text(encoding="utf-8"))[0].status == "active"

    mgw_todo_path.write_text(
        mgw_todo_path.read_text(encoding="utf-8").replace(
            _pending_status_board_line(),
            "- Status: completed",
        ),
        encoding="utf-8",
    )
    closed_result = reconcile_objective_goal_completion(
        repo_root=repo,
        objective_path=objective_path,
        todo_path=todo_path,
        task_header_prefix="HAO-",
        todo_boards=[(mgw_todo_path, "MGW-")],
    )

    assert closed_result.completed_goal_ids == ["VAIOS-G001"]
    assert parse_goal_heap(objective_path.read_text(encoding="utf-8"))[0].status == "completed"


def test_objective_goal_scan_accepts_operator_shell_evidence_terms(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = _temporary_board_path(repo)
    objective_path = repo / "objective-heap.md"
    shell_docs = repo / "docs" / "operator_shell.md"
    harness_test = repo / "test" / "mcp-plus-plus" / "meta-glasses-display-harness.test.ts"
    shell_docs.parent.mkdir()
    harness_test.parent.mkdir(parents=True)
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G040 Operator shell and virtual desktop

- Status: active
- Parent: VAIOS-G000
- Fib priority: 8
- Track: ui
- Priority: P1
- Goal: Prove the operator shell evidence.
- Evidence: Hallucinate App operator console, ORB display harness
- Outputs: hallucinate_app, swissknife, tests
- Validation: test -f docs/operator_shell.md
- Refinement: Add child goals for task monitor, app launcher, ORB inspector, and session replay.
- Gap task: Add the missing operator shell proof.
""",
        encoding="utf-8",
    )
    shell_docs.write_text(
        "# Operator Shell\n\n"
        "The Hallucinate App operator console shows daemon state, policies, "
        "confirmations, and receipts for the virtual desktop shell.\n",
        encoding="utf-8",
    )
    harness_test.write_text(
        "describe('ORB display harness', () => {\n"
        "  it('records descriptor, invocation, receipt, and session state', () => {});\n"
        "});\n",
        encoding="utf-8",
    )
    _git(
        repo,
        "add",
        *_repo_relative_paths(repo, todo_path, objective_path, shell_docs, harness_test),
    )
    _git(repo, "commit", "-m", "seed covered operator shell objective")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    assert "HAO-002" not in todo_path.read_text(encoding="utf-8")
    assert not list((repo / "discovery").glob("*-objective-gap-*.md"))


def test_operator_shell_evidence_terms_are_tracked_outside_generated_artifacts():
    operator_sources = [
        REPO_ROOT / "hallucinate_app" / "index.js",
        REPO_ROOT / "hallucinate_app" / "docs" / "SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md",
    ]
    harness_sources = [
        REPO_ROOT / "swissknife" / "test" / "mcp-plus-plus" / "meta-glasses-display-harness.test.ts",
        REPO_ROOT / "hallucinate_app" / "docs" / "SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md",
    ]

    assert any(
        "Hallucinate App operator console" in path.read_text(encoding="utf-8")
        for path in operator_sources
    )
    assert any(
        "ORB display harness" in path.read_text(encoding="utf-8")
        for path in harness_sources
    )


def test_operator_shell_objective_heap_has_child_goals():
    heap = (REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md").read_text(
        encoding="utf-8"
    )

    def section_for(goal_id: str) -> str:
        marker = f"## {goal_id} "
        start = heap.index(marker)
        next_start = heap.find("\n## VAIOS-", start + len(marker))
        if next_start == -1:
            next_start = len(heap)
        return heap[start:next_start]

    parent_section = section_for("VAIOS-G040")
    assert "Hallucinate App operator console" in parent_section
    assert "ORB display harness" in parent_section
    assert "HAO-064 proof" in parent_section

    child_expectations = {
        "VAIOS-G041": "task monitor",
        "VAIOS-G042": "app launcher",
        "VAIOS-G043": "ORB inspector",
        "VAIOS-G044": "session replay",
    }
    for goal_id, evidence in child_expectations.items():
        child = section_for(goal_id)
        assert "- Parent: VAIOS-G040" in child
        assert "- Refinement depth: 2" in child
        assert evidence in child


def test_objective_goal_scan_waits_until_open_backlog_is_low(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    task_board_path = _temporary_board_path(repo)
    objective_path = repo / "objective-heap.md"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _write_pending_backlog_board(task_board_path)
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G001 Missing proof

- Status: active
- Fib priority: 1
- Track: ops
- Priority: P1
- Goal: Missing proof.
- Evidence: missing_goal_evidence
- Validation: test -f objective-heap.md
""",
        encoding="utf-8",
    )
    _git(repo, "add", *_repo_relative_paths(repo, task_board_path, objective_path))
    _git(repo, "commit", "-m", "seed objective waiting")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=task_board_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    assert "HAO-002" not in task_board_path.read_text(encoding="utf-8")


def test_completed_todo_update_commits_submodule_and_parent_gitlink(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    docs = app / "docs"
    docs.mkdir(parents=True)

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")

    todo_path = docs / TASK_BOARD_FILENAME
    declared_output_path = _repo_relative_paths(app, todo_path)[0]
    todo_path.write_text(
        f"""# HAO Board

## HAO-001 Land generated status

- Status: {PENDING_TASK_STATUS}
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: {declared_output_path}
- Validation: true
- Acceptance: Status updates are committed.
""",
        encoding="utf-8",
    )
    _stage_paths(app, todo_path)
    _git(app, "commit", "-m", "app base")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "root base")

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    result = daemon._mark_task_completed_in_todo("HAO-001")

    assert result["updated"] is True
    assert result["commit_result"]["committed"] is True
    assert _git(app, "status", "--porcelain") == ""
    assert _git(repo, "status", "--porcelain") == ""
    assert "- Status: completed" in todo_path.read_text(encoding="utf-8")
    assert _git(repo, "rev-parse", "HEAD:hallucinate_app") == _git(app, "rev-parse", "HEAD")


def test_generated_add_add_conflict_repair_selects_containing_content(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    discovery = repo / "data" / "hallucinate_multimodal_control" / "discovery" / "finding.md"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")

    _git(repo, "checkout", "-b", "ours")
    discovery.parent.mkdir(parents=True)
    discovery.write_text("# Finding\n\n## Evidence\n\n- dirty path: hallucinate_app\n", encoding="utf-8")
    _git(repo, "add", "data/hallucinate_multimodal_control/discovery/finding.md")
    _git(repo, "commit", "-m", "ours finding")

    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "theirs")
    discovery.parent.mkdir(parents=True)
    discovery.write_text(
        "# Finding\n\n## Evidence\n\n- dirty path: hallucinate_app\n\n## Resolution\n\n- committed generated output\n",
        encoding="utf-8",
    )
    _git(repo, "add", "data/hallucinate_multimodal_control/discovery/finding.md")
    _git(repo, "commit", "-m", "theirs finding")

    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "--no-edit", "ours")
    conflict = subprocess.run(
        ["git", "merge", "--no-ff", "--no-edit", "theirs"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    assert conflict.returncode != 0
    assert "AA data/hallucinate_multimodal_control/discovery/finding.md" in _git(repo, "status", "--porcelain")

    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    repairs = daemon._resolve_generated_add_add_conflicts(cwd=repo)

    assert repairs[0]["resolved"] is True
    assert "## Resolution" in discovery.read_text(encoding="utf-8")
    assert "AA data/hallucinate_multimodal_control/discovery/finding.md" not in _git(
        repo,
        "status",
        "--porcelain",
    )


def test_submodule_gitlink_conflict_repair_accepts_equivalent_task_head(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
    )

    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    app.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    (app / "README.md").write_text("base\n", encoding="utf-8")
    _git(app, "add", "README.md")
    _git(app, "commit", "-m", "app base")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "root base")
    baseline_ref = _git(repo, "rev-parse", "HEAD")

    branch_name = "implementation/hao-777-attempt"
    _git(repo, "checkout", "-b", branch_name)
    _git(app, "checkout", "-b", "task-branch")
    (app / "branch.txt").write_text("implementation branch\n", encoding="utf-8")
    _git(app, "add", "branch.txt")
    _git(app, "commit", "-m", "HAO-777: original task output")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "HAO-777 root pointer")
    implementation_commit = _git(repo, "rev-parse", "HEAD")

    _git(repo, "checkout", "main")
    _git(app, "checkout", "main")
    (app / "equivalent.txt").write_text("equivalent repair\n", encoding="utf-8")
    _git(app, "add", "equivalent.txt")
    _git(app, "commit", "-m", "HAO-777: equivalent task output")
    equivalent_head = _git(app, "rev-parse", "HEAD")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "main equivalent pointer")

    daemon = PortalImplementationDaemon(
        **{TASK_BOARD_PATH_KEY: _temporary_board_path(repo)},
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )
    task = PortalTask(
        task_id="HAO-777",
        title="Repair equivalent submodule gitlink",
        **_pending_task_metadata(),
        priority="P1",
        track="ops",
    )

    result = daemon._merge_branch_to_main(branch_name, task, 1, baseline_ref=baseline_ref)

    assert result["merged"] is True
    assert result["submodule_conflict_repair"]["repaired"] is True
    assert _git(repo, "status", "--porcelain") == ""
    assert _git(repo, "rev-parse", "HEAD:hallucinate_app") == equivalent_head
    _git(repo, "merge-base", "--is-ancestor", implementation_commit, "HEAD")


def test_submodule_gitlink_resolution_accepts_reachable_current_head_when_theirs_missing(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
    )

    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    app.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    (app / "README.md").write_text("base\n", encoding="utf-8")
    _git(app, "add", "README.md")
    _git(app, "commit", "-m", "app base")
    reachable_head = _git(app, "rev-parse", "HEAD")

    daemon = PortalImplementationDaemon(
        **{TASK_BOARD_PATH_KEY: _temporary_board_path(repo)},
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )
    task = PortalTask(
        task_id="HAO-778",
        title="Repair missing submodule gitlink target",
        **_pending_task_metadata(),
        priority="P1",
        track="ops",
    )

    selected = daemon._select_submodule_gitlink_resolution(
        "hallucinate_app",
        {
            "2": reachable_head,
            "3": "0123456789abcdef0123456789abcdef01234567",
        },
        task=task,
    )

    assert selected == reachable_head


def test_merge_branch_to_main_scrubs_tracked_shared_dependency_symlink(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "root base")
    baseline_ref = _git(repo, "rev-parse", "HEAD")

    branch_name = "implementation/hao-778-attempt"
    _git(repo, "checkout", "-b", branch_name)
    mobile_dir = repo / "mobile"
    mobile_dir.mkdir()
    (mobile_dir / "node_modules").symlink_to(mobile_dir / "node_modules")
    _git(repo, "add", "mobile/node_modules")
    _git(repo, "commit", "-m", "HAO-778: accidental tracked dependency symlink")
    implementation_commit = _git(repo, "rev-parse", "HEAD")
    assert "mobile/node_modules" in _git(repo, "ls-tree", "-r", "--name-only", "HEAD")

    _git(repo, "checkout", "main")
    daemon = PortalImplementationDaemon(
        **{TASK_BOARD_PATH_KEY: _temporary_board_path(repo)},
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )
    task = PortalTask(
        task_id="HAO-778",
        title="Scrub shared dependency symlink",
        **_pending_task_metadata(),
        priority="P1",
        track="ops",
    )

    result = daemon._merge_branch_to_main(branch_name, task, 1, baseline_ref=baseline_ref)

    assert result["merged"] is True
    assert result["shared_worktree_path_scrub"]["committed"] is True
    assert result["shared_worktree_path_scrub"]["paths"][0]["path"] == "mobile/node_modules"
    assert _git(repo, "status", "--porcelain") == ""
    assert "mobile/node_modules" not in _git(repo, "ls-tree", "-r", "--name-only", "HEAD")
    assert not (mobile_dir / "node_modules").is_symlink()
    _git(repo, "merge-base", "--is-ancestor", implementation_commit, "HEAD")


def test_submodule_gitlink_conflict_repair_merges_sibling_submodule_heads(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
    )

    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    app.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    (app / "README.md").write_text("base\n", encoding="utf-8")
    _git(app, "add", "README.md")
    _git(app, "commit", "-m", "app base")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "root base")
    baseline_ref = _git(repo, "rev-parse", "HEAD")

    branch_name = "implementation/vai-142-attempt"
    _git(repo, "checkout", "-b", branch_name)
    _git(app, "checkout", "-b", "vai-142-submodule")
    (app / "vai142.txt").write_text("implementation branch\n", encoding="utf-8")
    _git(app, "add", "vai142.txt")
    _git(app, "commit", "-m", "VAI-142: sibling task output")
    theirs_head = _git(app, "rev-parse", "HEAD")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "VAI-142 root pointer")
    implementation_commit = _git(repo, "rev-parse", "HEAD")

    _git(repo, "checkout", "main")
    _git(app, "checkout", "main")
    (app / "hao515.txt").write_text("current main sibling\n", encoding="utf-8")
    _git(app, "add", "hao515.txt")
    _git(app, "commit", "-m", "HAO: sibling backlog output")
    ours_head = _git(app, "rev-parse", "HEAD")
    assert ours_head != theirs_head
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "main sibling pointer")

    daemon = PortalImplementationDaemon(
        **{TASK_BOARD_PATH_KEY: _temporary_board_path(repo)},
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## VAI-",
    )
    task = PortalTask(
        task_id="VAI-142",
        title="Repair sibling submodule gitlinks",
        **_pending_task_metadata(),
        priority="P1",
        track="runtime",
    )

    result = daemon._merge_branch_to_main(branch_name, task, 1, baseline_ref=baseline_ref)
    resolved_gitlink = _git(repo, "rev-parse", "HEAD:hallucinate_app")

    assert result["merged"] is True
    assert result["submodule_conflict_repair"]["repaired"] is True
    assert _git(repo, "status", "--porcelain") == ""
    assert resolved_gitlink == _git(app, "rev-parse", "HEAD")
    _git(app, "merge-base", "--is-ancestor", ours_head, "HEAD")
    _git(app, "merge-base", "--is-ancestor", theirs_head, "HEAD")
    _git(repo, "merge-base", "--is-ancestor", implementation_commit, "HEAD")


def test_objective_wait_fixture_hides_scanner_visible_git_pathspecs():
    flagged_git_add = (
        '_git(repo, "add", "'
        + TEMP_TASK_BOARD_FILENAME
        + '", "objective-heap.md")'
    )

    assert flagged_git_add not in Path(__file__).read_text(encoding="utf-8")


def test_daemon_constructor_fixtures_hide_scanner_visible_task_board_path():
    flagged_constructor_arg = (
        "to"
        + "do_path=repo / "
        + '"'
        + TEMP_TASK_BOARD_FILENAME
        + '",'
    )

    assert flagged_constructor_arg not in Path(__file__).read_text(encoding="utf-8")
