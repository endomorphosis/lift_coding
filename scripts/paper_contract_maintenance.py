"""Closed, local administrative repairs for a live reviewed paper owner.

The requester supplies no SQL, replacement argv, output paths, or status.
Only the exclusive owner computes a reviewed correction and commits its CAS.
The separate mode-0600 maintenance credential never grants Quack read clients
write authority. Request and response MACs bind the exact live owner generation.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
from itertools import islice
import os
from pathlib import Path
import secrets
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
STATE_ENV = "PAPER_OWNER_STATE_DIR"
SCHEMA = "paper-contract-maintenance/v1"
OPERATIONS = frozenset({"validation_argv", "snapshot_directory"})
MAX_BYTES = 64 * 1024
TTL_MS = 30_000
IDENTITY_FIELDS = ("server_id", "store_id", "database_uuid", "generation", "process_birth_id", "listen_uri")


class MaintenanceError(ValueError):
    pass


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sign(value, token):
    return hmac.new(token.encode(), wire(value), hashlib.sha256).hexdigest()


def atomic(path, value):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(wire(value))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def identity(value):
    return {key: value[key] for key in IDENTITY_FIELDS}


def submit(operation, task_cid, expected_revision, owner, *, state_dir=None, timeout=20):
    configured = state_dir or os.environ.get(STATE_ENV)
    if not configured:
        raise MaintenanceError("explicit paper owner state directory is required for maintenance")
    folder = Path(configured).resolve() / "paper-maintenance"
    token = (folder / "credential").read_text().strip()
    binding = identity(owner)
    ready = json.loads((folder.parent / "paper-owner.ready.json").read_text())
    if not ready.get("ready") or identity(ready["identity"]) != binding:
        raise MaintenanceError("maintenance directory does not belong to the exact live paper owner")
    request_id = uuid.uuid4().hex
    body = {"schema": SCHEMA, "request_id": request_id, "issued_at_ms": int(time.time() * 1000),
            "owner": binding, "operation": operation, "task_cid": task_cid, "expected_revision": expected_revision}
    request = {**body, "mac": sign(body, token)}
    request_digest = hashlib.sha256(wire(request)).hexdigest()
    request_path = folder / (request_id + ".request.json")
    response_path = folder / (request_id + ".done.json")
    atomic(request_path, request)
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if response_path.exists():
                with response_path.open("rb") as handle:
                    raw = handle.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise MaintenanceError("maintenance response exceeds its bound")
                response = json.loads(raw)
                mac = response.pop("mac", "")
                if (not hmac.compare_digest(mac, sign(response, token)) or
                        response.get("schema") != SCHEMA or response.get("request_id") != request_id or
                        response.get("request_sha256") != request_digest or response.get("owner") != binding):
                    raise MaintenanceError("maintenance response binding differs")
                if response.get("ok") is not True:
                    raise MaintenanceError("paper owner refused maintenance: " + response.get("error_code", "refused"))
                return response["result"]
            time.sleep(.05)
        raise MaintenanceError("maintenance outcome unknown; reobserve the task before retrying")
    finally:
        # A pending request may still settle: keep it for the owner to expire.
        response_path.unlink(missing_ok=True)


class OwnerMaintenance:
    def __init__(self, server, state_dir):
        self.server = server
        self.binding = identity(server.identity.to_dict())
        store = self.binding["store_id"]
        self.migration = load("paper_owner_reviewed_argv", "migrate_paper_validation_argv.py")
        self.repair = load("paper_owner_reviewed_outputs", "repair_paper_snapshot_outputs.py")
        self.paper = store.removeprefix("vericodegen-2026-")
        if store != "vericodegen-2026-" + self.paper or self.paper not in self.migration.MAT.PAPERS:
            raise MaintenanceError("maintenance is restricted to reviewed paper stores")
        self.population, provenance = self.migration.MAT.build_population(self.paper, ROOT)
        self.expected = {row["task_id"]: row for row in self.population["taskboard"]}
        self.seeds = {row["id"]: row for row in json.loads((ROOT / f"papers/completion/{self.paper}/tasks.json").read_text())["tasks"]}
        self.source_pins = provenance["source_sha256"]
        self.source_sizes = {relative: (ROOT / relative).stat().st_size for relative in self.source_pins}
        self.folder = Path(state_dir) / "paper-maintenance"
        self.folder.mkdir(exist_ok=True, mode=0o700)
        self.folder.chmod(0o700)
        self.token = secrets.token_hex(32)
        credential = self.folder / "credential"
        credential.unlink(missing_ok=True)
        with credential.open("x") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(self.token)

    def _check_sources(self):
        for relative, expected in self.source_pins.items():
            path = ROOT / relative
            if path.stat().st_size != self.source_sizes[relative]:
                raise MaintenanceError("reviewed_source_changed")
            with path.open("rb") as handle:
                actual = hashlib.file_digest(handle, "sha256").hexdigest()
            if actual != expected:
                raise MaintenanceError("reviewed_source_changed")

    def _apply(self, request):
        fields = {"schema", "request_id", "issued_at_ms", "owner", "operation", "task_cid", "expected_revision", "mac"}
        if set(request) != fields or request["schema"] != SCHEMA:
            raise MaintenanceError("closed_request_required")
        body = {key: value for key, value in request.items() if key != "mac"}
        if type(request["mac"]) is not str or not hmac.compare_digest(request["mac"], sign(body, self.token)):
            raise MaintenanceError("authentication_failed")
        issued = request["issued_at_ms"]
        if type(issued) is not int or not -5000 <= int(time.time()*1000)-issued <= TTL_MS:
            raise MaintenanceError("expired_request")
        if request["owner"] != self.binding or request["operation"] not in OPERATIONS:
            raise MaintenanceError("owner_or_operation_differs")
        revision = request["expected_revision"]
        if type(revision) is not int or revision < 1 or type(request["task_cid"]) is not str:
            raise MaintenanceError("exact_revision_required")
        from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository
        with self.server._lock:
            if self.server.identity is None or identity(self.server.identity.to_dict()) != self.binding:
                raise MaintenanceError("owner_generation_changed")
            if getattr(self.server.lifecycle, "value", "") != "ready":
                raise MaintenanceError("owner_not_ready")
            self._check_sources()
            connection = self.server._connection
            connection.execute("BEGIN TRANSACTION")
            try:
                repository = IntentRepository(bound_connection=connection, install_schema=False)
                records = [self.migration.plain(row) for row in repository.list_tasks(limit=1000)]
                if len(records) != len(self.expected) or {r["task_alias"] for r in records} != set(self.expected):
                    raise MaintenanceError("reviewed_population_differs")
                record = next((r for r in records if r["task_cid"] == request["task_cid"]), None)
                if record is None or record["revision"] != revision:
                    raise MaintenanceError("revision_conflict")
                if request["operation"] == "validation_argv":
                    # Recheck every record under the owner lock before mutation.
                    plans = {r["task_cid"]: self.migration.plan_record(r, self.expected[r["task_alias"]]) for r in records}
                    plan = plans[record["task_cid"]]
                    update = {"validations": [plan["validation"]]} if plan["change"] else None
                else:
                    for row in records:
                        expected = self.expected[row["task_alias"]]
                        if any(row[key] != expected[key] for key in
                               ("task_cid", "goal_cid", "plan_cid", "objective_id", "ordinal", "priority")) or set(row["dependencies"]) != set(expected["depends_on"]):
                            raise MaintenanceError("reviewed_task_binding_differs")
                    plans = {r["task_cid"]: self.repair.plan_record(self.paper, r, self.seeds[r["task_alias"]]) for r in records}
                    plan = plans[record["task_cid"]]
                    update = {"outputs": plan["outputs"]} if plan["action"] == "add_snapshot_directory" else None
                if update is None:
                    result = {"changed": False, "event": None}
                else:
                    payload = {key: record[key] for key in ("task_cid", "task_alias", "goal_cid", "ordinal", "status", "priority", "plan_cid", "objective_id", "body", "identity")}
                    event = repository.upsert_task(**payload, expected_revision=revision, **update)
                    observed = self.migration.plain(repository.get_task(record["task_cid"]))
                    preserve = self.migration.preserved_contract if request["operation"] == "validation_argv" else self.repair.preserved
                    if preserve(observed) != preserve(record) or observed["revision"] != revision + 1:
                        raise MaintenanceError("preserved_contract_changed")
                    if request["operation"] == "validation_argv":
                        expected_validations = self.migration.plain(record["validations"])
                        expected_validations[0]["argv"] = plan["validation"]["argv"]
                        if observed["validations"] != expected_validations:
                            raise MaintenanceError("reviewed_validation_differs")
                    elif [row["effect"] for row in observed["outputs"]] != plan["outputs"]:
                        raise MaintenanceError("reviewed_outputs_differ")
                    result = {"changed": True, "event": self.migration.plain(event.to_dict())}
                self._check_sources()
                connection.execute("COMMIT")
                return result
            except BaseException:
                connection.execute("ROLLBACK")
                raise

    def poll(self):
        # Only this owner process consumes the private, bounded inbox.
        entries = list(islice(self.folder.iterdir(), 4097))
        if len(entries) > 4096:
            return
        for path in sorted(path for path in entries if path.name.endswith(".request.json"))[:32]:
            request_id = path.name.removesuffix(".request.json")
            if len(request_id) != 32 or any(c not in "0123456789abcdef" for c in request_id):
                continue
            with path.open("rb") as handle:
                raw = handle.read(MAX_BYTES + 1)
            response = {"schema": SCHEMA, "request_id": request_id,
                        "request_sha256": hashlib.sha256(raw).hexdigest(), "owner": self.binding}
            try:
                if len(raw) > MAX_BYTES:
                    raise MaintenanceError("request_too_large")
                request = json.loads(raw)
                if request.get("request_id") != request_id:
                    raise MaintenanceError("request_identity_differs")
                response.update(ok=True, result=self._apply(request))
            except Exception as exc:
                response.update(ok=False, error_code=str(exc) if isinstance(exc, MaintenanceError) else type(exc).__name__)
            atomic(self.folder / (request_id + ".done.json"), {**response, "mac": sign(response, self.token)})
            path.unlink()

    def close(self):
        (self.folder / "credential").unlink(missing_ok=True)
