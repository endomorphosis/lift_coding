"""Receive fixed historical default registry deadline metadata using only stdlib bytes.

Factory/setup/model/help deadline identity and typed phase/lease custody are
reconciled declarations. This receiver never executes owner sources, native tools,
callbacks, models, databases or signatures and grants no current authority.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
import time
from hashlib import sha256
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-registry-operation-deadline-custody-input@1"
SCHEMA = "codebase-ir-registry-operation-deadline-custody@1"
PROFILE = "recorded-default-registry-deadlines@1"
MAX_FILE = 1024 * 1024
MAX_BYTES = 8 * 1024 * 1024
MAX_FILES = 32
MAX_MANIFEST = 128 * 1024
MAX_REPORT = 4 * 1024 * 1024
MAX_SECONDS = 120
MAX_DEPTH = 32
MAX_VALUES = 100000
ROLES = ('qualification',
 'source_evolution',
 'execution_freeze',
 'native_result',
 'native_command_result',
 'native_command',
 'phase_requests',
 'phase_launches',
 'phase_lifecycles',
 'phase_budgets',
 'phase_environments',
 'fixtures',
 'scheduler_configuration',
 'focused_test_result',
 'selected_test_result',
 'preservation_before',
 'preservation_after',
 'source_snapshot')
PUBLIC_PINS = {'qualification': 'fbc3214bce59e8d995a35eae9508429062e77c260ab083b3d3486045fe137de8',
 'source_evolution': '0018f3bf155dd8521f499caaca95c1c5fa8ea7f87e3f4f748667bb7ca962c4a6',
 'execution_freeze': 'de619cf62e78f71e445996b8f2ee12d947f953b979316b01a3a40e3257036fd5',
 'native_result': '3e3b91e4bc49143c6200f524977a0e127b1e9ab3ea66c9b440689c1061d16efc',
 'native_command_result': '1b24466436cee64187b0fb336e20584766354596e55c30306bacb51313169a11',
 'native_command': '7eeafbd4b971023c9d7892246203264fe2b8b0ae363243be4d470bdcc9293a0c',
 'phase_requests': 'a79f77b9e8b18637d046a232527b76bd68f0e29acf4837f6bf97fa2143af157d',
 'phase_launches': '92fbde088421a48c0cdb4f51b526a4b703af53ac645b44eae0ac381d28eb2329',
 'phase_lifecycles': '613a857ca3bc68b7d817d35f8ab9e1d4deaf9d7252ec1ff356652d27c7a87a63',
 'phase_budgets': '453dbafd14dc78107133b78d1007392f17f6c21eb7131cbbaf34704e84a29e34',
 'phase_environments': '678ea8d0298acb84504de1244aefbde135407dab56c93741b76fa9fe5d22131f',
 'fixtures': 'a998ef0170936c9f8dba42f4ed117ab3e0e5f0d8eaf69718ae0d6fc6291e34c7',
 'scheduler_configuration': '16330b7f1ff36025dd7f3b527588ab5e27368f83990ebf1e1844f9658efd7055',
 'focused_test_result': '2b5a6117dc11acebfcfb57bad8a8a0c9b663020729f71438315640a0ca0e55dc',
 'selected_test_result': '752fea0d41edabaf037aba0eae60057f32e506bfa5dc54b4ad1d5fddcdbee763',
 'preservation_before': 'bae35833a83f1524e0962271dc974fc056a256a0d0ad2ad02e22d2b854e586e7',
 'preservation_after': '520c63418f61c6223d839343a3a311c95886c4ce937947397dcbcdfe169771f7',
 'source_snapshot': '5b76810453b22240efcb908ad51e0b36a1595d3b1e2d8ae01452ab793f6351ae'}
ARTIFACT_KEYS = {'qualification': 'qualification.json',
 'source_evolution': 'source-evolution.json',
 'execution_freeze': 'execution-freeze.json',
 'native_result': 'native/result.json',
 'native_command_result': 'native-command-result.json',
 'native_command': 'native-command.json',
 'phase_requests': 'native/request-audit.json',
 'phase_launches': 'native/launch-audit.json',
 'phase_lifecycles': 'native/lifecycle-audit.json',
 'phase_budgets': 'native/phase-budget-audit.json',
 'phase_environments': 'native/apalache-environment-audit.json',
 'fixtures': 'native/fixtures.json',
 'scheduler_configuration': 'native/saved-scheduler-config.json',
 'focused_test_result': 'focused-initial.result.json',
 'selected_test_result': 'joined-selected.result.json',
 'preservation_before': 'preservation-before.json',
 'preservation_after': 'preservation-after.json',
 'source_snapshot': 'source-snapshot.json'}
TRUE_FLAGS = (
    "retained_registry_deadline_custody_conformance", "recorded_production_deadline_bindings_reconciled",
    "complete_factory_native_phase_population_reconciled", "historical_request_payload_preserved",
    "generic_unknown_authority_preserved", "recorded_lease_cleanup_reconciled",
    "historical_test_counts_overlap_preserved", "historical_source_preservation_declarations_retained",
    "no_benchmark_outer_scope_declaration_preserved", "input_files_unchanged",
)
FALSE_FLAGS = (
    "native_execution_performed", "training_executed", "current_authority_claimed", "owner_sources_imported",
    "owner_database_opened", "profile_keys_read", "network_access_performed", "git_executable_invoked",
    "source_execution_attested", "process_origin_attested", "live_cleanup_reobserved",
    "automatic_current_registry_behavior_qualified", "native_cancellation_execution_qualified",
    "hard_callback_preemption_qualified", "hard_aggregate_containment_qualified",
    "standalone_availability_propagation_verified", "other_native_adapter_propagation_verified",
    "installation_cancellation_qualified", "proof_authority", "model_truth_qualified",
    "source_semantics_verified", "source_bodies_authenticated", "selected_test_sources_authenticated",
    "tool_bodies_authenticated", "producer_authentication_verified", "signature_authentication_performed",
    "output_digest_algorithm_rederived", "semantic_counterexample_replay_qualified",
    "structural_counterexample_replay_requalified", "whole_host_resources_requalified",
    "throughput_qualified", "signed_worker_qualified", "production_default_activated",
)
ZERO_FIELDS = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")
CASE_IDS = ("registry-operation-budget:apalache:true", "registry-operation-budget:apalache:false")
SHAPES = {'attempt': ('artifact_digests',
             'attempt_id',
             'backend_id',
             'backend_version',
             'bounds',
             'diagnostics',
             'output_digest',
             'request_digest',
             'schema_version',
             'status',
             'usage'),
 'execution_freeze': ('benchmark_sha256',
                      'focused_regression_sha256',
                      'native_runner_sha256',
                      'native_sources',
                      'scope',
                      'selected_regression_sha256',
                      'selected_sources',
                      'source_evolution_sha256',
                      'static_preflight_sha256'),
 'fixture': ('apalache_config_digest',
             'apalache_config_text',
             'artifact_digest',
             'bounded',
             'bounds',
             'fairness_limitations',
             'interface_version',
             'liveness_properties',
             'losses',
             'model_digest',
             'model_text',
             'module_name',
             'safety_properties',
             'schema_version',
             'source_document_id',
             'source_kind',
             'source_map',
             'tlc_config_digest',
             'tlc_config_text',
             'translator',
             'unbounded_proof'),
 'fixtures': ('false', 'true'),
 'focused_test_result': ('after',
                         'argv',
                         'before',
                         'cwd',
                         'env_overrides',
                         'returncode',
                         'seconds',
                         'suite',
                         'test_snapshots'),
 'generic_authority': ('configuration_digest',
                       'evidence_digests',
                       'issuer',
                       'kind',
                       'method',
                       'schema_version',
                       'scope_digest'),
 'generic_payload': ('adapter_return_type', 'result', 'result_authority', 'result_status'),
 'generic_result': ('assumption_ids',
                    'attempt_digest',
                    'authority',
                    'backend_id',
                    'backend_version',
                    'bounds',
                    'claim_digest',
                    'declaration_id',
                    'diagnostics',
                    'obligation_digest',
                    'obligation_id',
                    'output_digest',
                    'payload',
                    'request_digest',
                    'result_id',
                    'result_type',
                    'schema_version',
                    'status',
                    'usage'),
 'lifecycle_request': ('argv',
                       'input_file_count',
                       'java_option_environment_absent',
                       'max_output_bytes',
                       'memory_bytes',
                       'output_path_count',
                       'resident_memory_bytes',
                       'stdin_is_empty',
                       'timeout_seconds'),
 'lifecycle_result': ('cancelled',
                      'command',
                      'elapsed_seconds',
                      'error',
                      'interface_version',
                      'output_files',
                      'output_truncated',
                      'pid',
                      'process_tree_terminated',
                      'resource_exhausted',
                      'returncode',
                      'runtime',
                      'stderr',
                      'stdout',
                      'termination_reason',
                      'timed_out',
                      'unavailable',
                      'workspace_cleaned',
                      'workspace_limit_exceeded'),
 'native_case': ('aggregate_scope_owner',
                 'ambient_scope_absent_before_and_after',
                 'attempt',
                 'attempt_digest',
                 'case',
                 'complete_artifact_equal',
                 'decoded_artifact',
                 'default_lazy_factory_used',
                 'dispatch',
                 'elapsed_seconds',
                 'factory_native_deadline_equal',
                 'factory_operations',
                 'factory_restored',
                 'native_phase_operations',
                 'operation_timeout_ms',
                 'original_outcome',
                 'original_return_observer_restored',
                 'phase_count',
                 'projection_checks',
                 'raw_witness',
                 'request',
                 'request_digest',
                 'result',
                 'selected_delegate_count',
                 'submitted_artifact',
                 'valid'),
 'native_checks': ('actual_counterexample_states_preserved',
                   'complete_artifact_preserved',
                   'conservative_structural_replay',
                   'exact_foreign_typed_payload',
                   'exact_two_serial_cases',
                   'expected_real_phases',
                   'java_selection_environment_restored',
                   'native_environments_sanitized',
                   'no_ambient_or_leaked_operation_scope',
                   'no_generic_authority_promotion',
                   'observer_and_factory_restored',
                   'owned_apalache_jvm_environments',
                   'owned_work_drained',
                   'production_scope_covers_factory_and_native',
                   'selected_tool_files_unchanged',
                   'shared_config_unchanged',
                   'sources_stable'),
 'native_command': ('argv', 'before', 'cwd', 'env_overrides', 'freeze_sha256'),
 'native_command_result': ('after',
                           'argv',
                           'before',
                           'cwd',
                           'env_overrides',
                           'freeze_sha256',
                           'returncode',
                           'seconds'),
 'native_result': ('audit_sha256',
                   'cases',
                   'checks',
                   'child_usage',
                   'dispatches',
                   'elapsed_seconds',
                   'launches',
                   'lifecycles',
                   'native_lifecycles',
                   'packaged_native_entries',
                   'phase_counts',
                   'prelaunch_lifecycles',
                   'runtime',
                   'schema',
                   'scope',
                   'shared_after',
                   'shared_before',
                   'shared_pool_compatibility',
                   'source_pins_after',
                   'source_pins_before',
                   'status',
                   'tool_files_after',
                   'tool_files_before',
                   'tool_selection'),
 'native_scope': ('aggregate_scope_owner',
                  'benchmark_operation_scope_injected',
                  'complete_serialized_artifact_preserved',
                  'cooperative_operation_boundary_only',
                  'default_registry_aggregate_budget_claim',
                  'factory_override',
                  'hard_aggregate_resource_guarantee',
                  'installation',
                  'jvm_probe_injected',
                  'native_transport_injected',
                  'native_v2_execution',
                  'new_proof_cache_or_replay',
                  'raw_counterexample_and_parsed_states',
                  'registry_route',
                  'semantic_counterexample_replay_claim',
                  'source_map_structural_check',
                  'throughput_scaling_claim',
                  'tlc_execution'),
 'original_outcome': ('artifacts', 'interface_version', 'receipt', 'request_digest', 'result'),
 'phase_budget': ('at_monotonic',
                  'case',
                  'deadline',
                  'phase',
                  'remaining_seconds',
                  'request_timeout_seconds'),
 'phase_environment': ('case',
                       'foreign_configuration_environment_absent',
                       'jvm_args',
                       'jvm_gc_args',
                       'phase',
                       'private_home_and_tmpdir'),
 'phase_launch': ('argv',
                  'at_monotonic',
                  'case',
                  'launch_lease_id',
                  'owned_leases',
                  'root_allocations',
                  'thread',
                  'waiting'),
 'phase_lease': ('acquired_at',
                 'cancelled',
                 'child_process_slots',
                 'cpu_slots',
                 'expires_at',
                 'gpu_memory_mb',
                 'heartbeat_at',
                 'lane',
                 'lease_id',
                 'lease_key',
                 'memory_mb',
                 'owner_birth_marker',
                 'owner_boot_id',
                 'owner_pid',
                 'parent_lease_id',
                 'request_id',
                 'requires_gpu',
                 'sequence',
                 'unified_memory_mb',
                 'wait_seconds'),
 'phase_lifecycle': ('case', 'request', 'result', 'shared_backoff_after'),
 'phase_limits': ('cpu_seconds',
                  'enforce_file_size_limit',
                  'max_argument_bytes',
                  'max_arguments',
                  'max_environment_bytes',
                  'max_file_bytes',
                  'max_input_bytes',
                  'max_output_bytes',
                  'max_output_files',
                  'max_path_bytes',
                  'max_workspace_bytes',
                  'memory_bytes',
                  'resident_memory_bytes',
                  'termination_grace_seconds',
                  'timeout_seconds'),
 'phase_request': ('argv', 'case', 'input_bytes', 'input_sha256', 'limits', 'output_paths'),
 'preservation_after': ('existing_test_files_changed',
                        'historical_hash_aliases_added',
                        'prior_artifacts',
                        'prior_qualifications',
                        'production_files_changed'),
 'preservation_before': ('prior_native_sources',
                         'prior_selected_sources',
                         'qualifications',
                         'source_evolution',
                         'verified_prior_artifacts'),
 'qualification': ('artifact_sha256',
                   'checks',
                   'deselected_legacy_native_tests',
                   'focused_tests',
                   'native_phases',
                   'native_seconds',
                   'native_success_cases',
                   'native_wrapper_seconds',
                   'new_cache_replay',
                   'new_codebase_smt_execution',
                   'new_operation_budget_tests',
                   'preservation',
                   'production_tasks_closed',
                   'recorded_at_utc',
                   'schema',
                   'selected_test_cases',
                   'selected_tests',
                   'status',
                   'test_attempts',
                   'test_counts_summed'),
 'qualification_checks': ('actual_counterexample_states_preserved',
                          'complete_artifact_preserved',
                          'conservative_structural_replay',
                          'exact_foreign_typed_payload',
                          'exact_two_serial_cases',
                          'expected_real_phases',
                          'java_selection_environment_restored',
                          'native_environments_sanitized',
                          'no_ambient_or_leaked_operation_scope',
                          'no_generic_authority_promotion',
                          'observer_and_factory_restored',
                          'owned_apalache_jvm_environments',
                          'owned_work_drained',
                          'production_scope_covers_factory_and_native',
                          'selected_tool_files_unchanged',
                          'shared_config_unchanged',
                          'sources_stable'),
 'request': ('assumption_ids',
             'bounds',
             'claim_digest',
             'claim_id',
             'declaration_id',
             'logic_family',
             'obligation_digest',
             'obligation_id',
             'payload',
             'query_kind',
             'request_id',
             'requested_backend_id',
             'schema_version'),
 'request_payload': ('artifacts',),
 'scheduler_configuration': ('allow_foreign_work',
                             'config',
                             'runtime',
                             'schema',
                             'state_before',
                             'state_path'),
 'selected_test_result': ('after',
                          'argv',
                          'before',
                          'cwd',
                          'env_overrides',
                          'returncode',
                          'seconds',
                          'suite',
                          'test_snapshots'),
 'source_evolution': ('/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/registry.py',),
 'source_snapshot': ('builder_sha256',
                     'documentation',
                     'native_sources',
                     'producer_inventories',
                     'retained_producer_result_sha256',
                     'selected_test_sources',
                     'selected_tools'),
 'typed_receipt': ('artifact_digest',
                   'bounded',
                   'capability',
                   'checked_liveness_properties',
                   'checked_safety_properties',
                   'command',
                   'configuration_digest',
                   'configuration_text',
                   'counterexample',
                   'elapsed_ms',
                   'executable',
                   'fairness_limitations',
                   'jvm_available',
                   'model_digest',
                   'output_truncated',
                   'reason',
                   'receipt_id',
                   'returncode',
                   'schema_version',
                   'status',
                   'stderr',
                   'stdout',
                   'timeout_seconds',
                   'tool',
                   'tool_version',
                   'unbounded_proof'),
 'typed_result': ('assumptions',
                  'authority',
                  'backend_id',
                  'backend_version',
                  'bounds',
                  'diagnostics',
                  'metadata',
                  'reason',
                  'result_id',
                  'result_type',
                  'schema_version',
                  'status',
                  'translation_ceiling',
                  'usage',
                  'witness')}
NATIVE_SCOPE = {'aggregate_scope_owner': 'production_registry',
 'benchmark_operation_scope_injected': False,
 'complete_serialized_artifact_preserved': True,
 'cooperative_operation_boundary_only': True,
 'default_registry_aggregate_budget_claim': True,
 'factory_override': 'Installed Apalache and Java selection, lazy_install=False only',
 'hard_aggregate_resource_guarantee': False,
 'installation': False,
 'jvm_probe_injected': False,
 'native_transport_injected': False,
 'native_v2_execution': False,
 'new_proof_cache_or_replay': False,
 'raw_counterexample_and_parsed_states': True,
 'registry_route': 'default_backend_registry/LazyMatrixProofBackend',
 'semantic_counterexample_replay_claim': False,
 'source_map_structural_check': True,
 'throughput_scaling_claim': False,
 'tlc_execution': False}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def same(left, right):
    """JSON type-sensitive equality, including bool/int and int/float distinctions."""
    return wire(left) == wire(right)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def bounded_canonical(value, maximum):
    chunks, size = [], 0
    for token in json.JSONEncoder(sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).iterencode(value):
        raw = token.encode("utf-8")
        require(size + len(raw) + 1 <= maximum, "serialized report allocation bound")
        chunks.append(raw)
        size += len(raw)
    return b"".join(chunks) + b"\n"


def document(raw):
    depth, quoted, escape, containers, tokens, bare = 0, False, False, 0, 0, False
    for token in raw:
        if quoted:
            if escape:
                escape = False
            elif token == 92:
                escape = True
            elif token == 34:
                quoted = False
        elif token == 34:
            quoted = True
            bare = False
            tokens += 1
        elif token in (91, 123):
            depth += 1
            containers += 1
            tokens += 1
            bare = False
            require(depth <= MAX_DEPTH and containers <= MAX_VALUES, "JSON structure allocation bound")
        elif token in (93, 125):
            depth -= 1
            bare = False
            require(depth >= 0, "JSON nesting mismatch")
        elif token in (9, 10, 13, 32, 44, 58):
            bare = False
        elif not bare:
            tokens += 1
            bare = True
        require(tokens <= MAX_VALUES, "JSON lexical value allocation bound")

    def pairs(items):
        value = {}
        for key, child in items:
            require(key not in value, "duplicate JSON key")
            value[key] = child
        return value

    def integer(token):
        require(len(token) <= 20, "JSON integer allocation bound")
        value = int(token)
        require(abs(value) <= 2**63 - 1, "JSON integer magnitude bound")
        return value

    def floating(token):
        require(len(token) <= 64, "JSON float allocation bound")
        value = float(token)
        require(math.isfinite(value), "nonfinite JSON number")
        return value

    def constant(_):
        raise ValueError("nonfinite JSON number")

    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                       parse_int=integer, parse_float=floating, parse_constant=constant)
    require(type(value) in (dict, list), "JSON object or array required")
    pending, count = [(value, 0)], 0
    while pending:
        child, level = pending.pop()
        count += 1
        require(count <= MAX_VALUES and level <= MAX_DEPTH, "JSON value allocation bound")
        if type(child) is str:
            require(len(child) <= MAX_FILE and "\x00" not in child and not any(0xD800 <= ord(char) <= 0xDFFF for char in child), "bounded JSON text required")
        elif type(child) is dict:
            pending.extend((key, level + 1) for key in child)
            pending.extend((item, level + 1) for item in child.values())
        elif type(child) is list:
            pending.extend((item, level + 1) for item in child)
    return value


def closed(value, keys, message):
    require(type(value) is dict and set(value) == set(keys), message)


def exact_int(value, maximum=2**63 - 1):
    require(type(value) is int and 0 <= value <= maximum, "bounded exact integer required")
    return value


def number(value):
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1e9, "bounded recorded number required")
    return value


def digest(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, "SHA-256 required")
    return value


def identity(value):
    require(type(value) is str and 0 < len(value) <= 1024 and "\x00" not in value
            and re.fullmatch(r"[A-Za-z0-9:_./-]+", value) is not None, "bounded declared identity required")
    return value


def lexical_path(value, *, absolute=True):
    require(type(value) is str and 0 < len(value) <= 8192 and "\x00" not in value, "bounded lexical path required")
    path = Path(value)
    require(path.is_absolute() is absolute and ".." not in path.parts and str(path) == value and value != ".",
            "canonical lexical path required")
    return path


def descriptor(value):
    closed(value, {"path", "sha256", "size_bytes"}, "closed file descriptor required")
    lexical_path(value["path"])
    digest(value["sha256"])
    exact_int(value["size_bytes"], MAX_FILE)
    return dict(value)


def declared_pin(root, value):
    closed(value, {"path", "sha256", "bytes"}, "closed declared descriptor required")
    return descriptor({"path": str(root / lexical_path(value["path"], absolute=False)),
                       "sha256": value["sha256"], "size_bytes": value["bytes"]})


class Capture:
    """Two separate caches receive only explicitly pinned regular bodies."""

    def __init__(self, remap=None, *, started=None):
        self.remap, self.files, self.total, self.identities, self.inodes = remap, {}, 0, {}, {}
        self.started = time.monotonic() if started is None else started

    def deadline(self):
        require(time.monotonic() - self.started <= MAX_SECONDS, "custody deadline")

    @staticmethod
    def fingerprint(path):
        row = path.lstat()
        return row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns

    @staticmethod
    def raw(path, maximum):
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical nonsymlink file required")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum, "bounded regular file required")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(maximum + 1)
            after, current = os.fstat(fd), path.lstat()
            def fingerprint(row):
                return row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns
            require(fingerprint(before) == fingerprint(after) == fingerprint(current) and len(raw) == before.st_size,
                    "file changed during bounded read")
            return raw
        finally:
            os.close(fd)

    def read(self, path, pin=None, *, mapped=True, maximum=MAX_FILE):
        self.deadline()
        logical = lexical_path(str(path))
        if self.remap is not None and mapped:
            require(str(logical) in self.remap, "explicit relocated member unavailable")
            physical = lexical_path(self.remap[str(logical)])
        else:
            physical = logical
        limit = maximum if pin is None else descriptor(pin)["size_bytes"]
        require(limit <= maximum, "preallocation file bound")
        if physical not in self.files:
            require(len(self.files) < MAX_FILES and self.total + limit <= MAX_BYTES, "preallocation aggregate bound")
            before = self.fingerprint(physical)
            require(before[:2] not in self.inodes, "distinct physical selected bodies")
            self.inodes[before[:2]] = physical
            self.files[physical] = self.raw(physical, limit)
            self.identities[physical] = self.fingerprint(physical)
            require(before == self.identities[physical], "file identity changed during capture")
            self.total += len(self.files[physical])
        raw = self.files[physical]
        if pin is not None:
            require(len(raw) == pin["size_bytes"] and sha256(raw).hexdigest() == pin["sha256"], "selected raw pin mismatch")
        return raw

    def stable(self):
        for path, raw in self.files.items():
            self.deadline()
            require(self.raw(path, len(raw)) == raw and self.fingerprint(path) == self.identities[path], "previously captured body or identity changed")
        return True


def scope():
    return {**dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False),
            **dict.fromkeys(ZERO_FIELDS, 0)}



def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            require(stream.write(raw) == len(raw), "complete owned write")
        os.fchmod(fd, 0o444)
    finally:
        os.close(fd)


def output_population(root, expected):
    require(root.is_absolute() and root.resolve(strict=True) == root and stat.S_ISDIR(root.lstat().st_mode),
            "canonical output directory")
    files, folders, pending = set(), set(), [root]
    while pending:
        folder = pending.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                relative = Path(entry.path).relative_to(root).as_posix()
                info = entry.stat(follow_symlinks=False)
                require(len(files) < MAX_FILES and len(folders) <= 1, "bounded owned output population")
                if stat.S_ISDIR(info.st_mode):
                    require(relative == "retained", "only expected retained directory")
                    folders.add(relative)
                    pending.append(Path(entry.path))
                else:
                    require(stat.S_ISREG(info.st_mode) and relative in expected, "exact regular owned output population")
                    files.add(relative)
    require(files == set(expected) and folders == {"retained"} and root.resolve(strict=True) == root,
            "exact final owned output population")


def shaped(value, kind):
    closed(value, SHAPES[kind], "closed recorded " + kind)


def metadata_digests(value, *, maximum=512):
    require(type(value) is dict and 0 < len(value) <= maximum, "bounded declared digest map")
    for path, pin in value.items():
        require(type(path) is str and 0 < len(path) <= 8192, "declared inert path text")
        digest(pin)
    return value


def recorded_number(value):
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1e12,
            "finite bounded recorded numeric observation")
    return value


def source_and_test_observations(docs, pins):
    q, freeze, snapshot = (docs[key] for key in ("qualification", "execution_freeze", "source_snapshot"))
    for role in ("qualification", "execution_freeze", "source_snapshot", "source_evolution",
                 "preservation_before", "preservation_after", "focused_test_result", "selected_test_result",
                 "native_command_result", "native_command"):
        shaped(docs[role], role)
    require(q["schema"] == "registry-operation-budget-qualification@1" and q["status"] == "passed_partial_scope",
            "historical partial-scope qualification")
    shaped(q["checks"], "qualification_checks")
    require(all(value is True for value in q["checks"].values()), "recorded complete qualification checks")
    require(q["test_counts_summed"] is False and q["new_cache_replay"] is False
            and q["new_codebase_smt_execution"] is False and q["production_tasks_closed"] == [],
            "test overlap and no new execution or production closure")
    for role in ROLES[1:]:
        require(q["artifact_sha256"].get(ARTIFACT_KEYS[role]) == pins[role]["sha256"], "qualification selected raw join")
    for key in ("benchmark_sha256", "focused_regression_sha256", "native_runner_sha256",
                "selected_regression_sha256", "source_evolution_sha256", "static_preflight_sha256"):
        digest(freeze[key])
    require(freeze["source_evolution_sha256"] == pins["source_evolution"]["sha256"], "frozen source evolution join")
    metadata_digests(freeze["native_sources"])
    metadata_digests(freeze["selected_sources"])
    require(len(freeze["native_sources"]) == 86 and len(freeze["selected_sources"]) == 166,
            "complete recorded owner and selected-test source inventories")
    require(same(snapshot["native_sources"], freeze["native_sources"])
            and same(snapshot["selected_test_sources"], freeze["selected_sources"]), "same recorded source inventories")
    command, executed = docs["native_command"], docs["native_command_result"]
    require(exact_int(executed["returncode"]) == 0 and same(executed["before"], executed["after"])
            and same(command["before"], executed["before"]) and same(command["argv"], executed["argv"])
            and same(command["env_overrides"], executed["env_overrides"]) and command["cwd"] == executed["cwd"]
            and command["freeze_sha256"] == executed["freeze_sha256"] == pins["execution_freeze"]["sha256"]
            and same(executed["before"], freeze["native_sources"]), "whole command and recorded source freeze joins")
    require(type(command["argv"]) is list and len(command["argv"]) == 4
            and all(type(value) is str for value in command["argv"]), "inert native command declaration")
    tests = {}
    closed(q["test_attempts"], {"focused-initial", "joined-selected"}, "two first recorded test attempts")
    for role, name, suite, count in (("focused_test_result", "focused-initial", "focused", 747),
                                    ("selected_test_result", "joined-selected", "joined", 2215)):
        value, observation = docs[role], q["test_attempts"][name]
        closed(observation, {"accepted", "counts", "returncode", "seconds", "sources_stable", "suite"},
               "closed recorded test observation")
        require(exact_int(value["returncode"]) == exact_int(observation["returncode"]) == 0
                and value["suite"] == observation["suite"] == suite and observation["accepted"] is True
                and observation["sources_stable"] is True and same(value["before"], value["after"])
                and same(value["before"], freeze["selected_sources"])
                and same(value["seconds"], observation["seconds"]), "recorded first test command/source joins")
        closed(observation["counts"], {"passed"}, "recorded test counts have only passing cases")
        require(exact_int(observation["counts"]["passed"]) == count, "exact recorded passing test count")
        tests[suite] = {"recorded_passed": count, "recorded_returncode": 0,
                        "recorded_seconds": recorded_number(value["seconds"]), "tests_reexecuted": False}
    ids = q["selected_test_cases"]
    require(type(ids) is list and len(ids) == 2215
            and all(type(value) is str and 0 < len(value) <= 4096 for value in ids)
            and len(set(ids)) == 2215, "complete unique selected test identities")
    interruption_ids = [value for value in ids if "tests.unit.logic.backends.test_registry_operation_control::" in value]
    require(len(interruption_ids) == exact_int(q["new_operation_budget_tests"]) == 126
            and exact_int(q["selected_tests"]) == 2215 and exact_int(q["focused_tests"]) == 747
            and exact_int(q["deselected_legacy_native_tests"]) == 15, "recorded complete operation-control population")
    before, after = docs["preservation_before"], docs["preservation_after"]
    closed(after, {"existing_test_files_changed", "historical_hash_aliases_added", "prior_artifacts",
                   "prior_qualifications", "production_files_changed"}, "closed preservation observation")
    require(exact_int(before["verified_prior_artifacts"]) == exact_int(after["prior_artifacts"]) == 1618
            and type(before["qualifications"]) is dict and len(before["qualifications"]) == exact_int(after["prior_qualifications"]) == 19
            and exact_int(after["production_files_changed"]) == 1 and exact_int(after["existing_test_files_changed"]) == 0
            and after["historical_hash_aliases_added"] is False and same(q["preservation"], after), "prior-body preservation declarations")
    require(sum(exact_int(row["verified_artifacts"]) for row in before["qualifications"].values()) == 1618,
            "declared prior artifact quantities independently summed")
    for row in before["qualifications"].values():
        closed(row, {"qualification_sha256", "report_sha256", "verified_artifacts"}, "closed prior qualification declaration")
        digest(row["qualification_sha256"])
        digest(row["report_sha256"])
    evolution = docs["source_evolution"]
    require(len(evolution) == 1 and set(evolution) == set(before["source_evolution"]), "one historical production source change")
    for path, row in evolution.items():
        closed(row, {"before_sha256", "after_sha256", "before_snapshot", "after_snapshot", "diff", "diff_sha256"},
               "closed source evolution declaration")
        prior = before["source_evolution"][path]
        closed(prior, {"before_sha256", "before_snapshot"}, "closed pre-change source declaration")
        require(same(prior, {key: row[key] for key in prior}), "pre-change source declaration preserved")
        require(path.endswith("/logic/backends/registry.py") and before["prior_native_sources"][path] == row["before_sha256"]
                and freeze["native_sources"][path] == row["after_sha256"], "source revision declaration joins")
        for field in ("before_sha256", "after_sha256", "diff_sha256"):
            digest(row[field])
        for field in ("before_snapshot", "after_snapshot", "diff"):
            lexical_path(row[field], absolute=False)
    return ({"focused": tests["focused"], "selected": tests["joined"], "recorded_new_control_cases": 126,
             "recorded_native_deselections": 15, "focused_and_selected_overlap": True, "counts_summed": False,
             "selected_case_id_count": len(ids), "selected_case_ids_sha256": sha256(wire(ids)).hexdigest(),
             "interruption_regression_ids_sha256": sha256(wire(interruption_ids)).hexdigest(),
             "native_interruption_execution_attested": False},
            {"recorded_prior_artifacts": 1618, "recorded_prior_qualifications": 19,
             "recorded_production_files_changed": 1, "recorded_existing_test_files_changed": 0,
             "historical_hash_aliases_added": False, "source_evolution": evolution,
             "native_source_fingerprint_count": len(freeze["native_sources"]),
             "selected_test_source_fingerprint_count": len(freeze["selected_sources"]),
             "all_named_source_tool_test_and_prior_bodies_opened": 0,
             "current_source_origin": "unknown_not_selected", "prior_deep_body_closure": "unknown_not_selected"})


def phase_observations(docs, native):
    require(all(type(docs[key]) is list and len(docs[key]) == 6 for key in
                ("phase_requests", "phase_launches", "phase_lifecycles", "phase_budgets")), "complete ordered six phases")
    require(type(docs["phase_environments"]) is list and len(docs["phase_environments"]) == 4, "four recorded JVM environments")
    rows, lease_ids, jvm_index = [], set(), 0
    for index, (request, launch, life, budget) in enumerate(zip(
            docs["phase_requests"], docs["phase_launches"], docs["phase_lifecycles"], docs["phase_budgets"], strict=True)):
        phase, case = ("setup", "model", "help")[index % 3], CASE_IDS[index // 3]
        for value, kind in ((request, "phase_request"), (launch, "phase_launch"), (life, "phase_lifecycle"),
                            (budget, "phase_budget"), (request["limits"], "phase_limits"),
                            (life["request"], "lifecycle_request"), (life["result"], "lifecycle_result")):
            shaped(value, kind)
        label = case + ":constructor" if phase == "setup" else case
        require(request["case"] == launch["case"] == life["case"] == label
                and budget["case"] == case and budget["phase"] == phase, "ordered case/phase identity")
        actual, envelope = life["result"], life["request"]
        require(type(request["argv"]) is list and request["argv"]
                and all(type(value) is str for value in request["argv"])
                and same(request["argv"], envelope["argv"]) and same(actual["command"], request["argv"])
                and type(launch["argv"]) is list and launch["argv"][-len(request["argv"]):] == request["argv"],
                "logical lifecycle and launched command suffix joins")
        require((request["argv"][-1] == "-version" if phase == "setup"
                 else ("check" in request["argv"] if phase == "model" else "version" in request["argv"])), "inert command phase classification")
        expected_exit = 12 if phase == "model" and index // 3 == 1 else 0
        expected_termination = "nonzero_exit" if expected_exit else "completed"
        require(exact_int(actual["returncode"]) == expected_exit and actual["workspace_cleaned"] is True
                and actual["error"] == "" and actual["termination_reason"] == expected_termination
                and actual["runtime"] == "jvm" and actual["interface_version"] == "bounded-tool-runner/v1"
                and all(actual[key] is False for key in (
                    "cancelled", "output_truncated", "process_tree_terminated", "resource_exhausted", "timed_out",
                    "unavailable", "workspace_limit_exceeded")), "normally completed cleaned phase metadata")
        require(type(actual["stdout"]) is type(actual["stderr"]) is str, "inert recorded phase output")
        recorded_number(actual["elapsed_seconds"])
        for key in ("deadline", "at_monotonic", "remaining_seconds", "request_timeout_seconds"):
            require(recorded_number(budget[key]) > 0, "positive finite recorded deadline quantities")
        require(abs(budget["deadline"] - budget["at_monotonic"] - budget["remaining_seconds"]) <= 0.02
                and budget["request_timeout_seconds"] <= budget["remaining_seconds"] + 0.02
                and same(budget["request_timeout_seconds"], request["limits"]["timeout_seconds"])
                and same(budget["request_timeout_seconds"], envelope["timeout_seconds"]), "finite remaining phase budget propagation")
        require(envelope["java_option_environment_absent"] is True and envelope["stdin_is_empty"] is True
                and request["limits"]["enforce_file_size_limit"] is True, "recorded phase environment and file limits")
        require(type(launch["owned_leases"]) is list and len(launch["owned_leases"]) == 1, "single recorded lease per phase")
        lease = launch["owned_leases"][0]
        shaped(lease, "phase_lease")
        require(lease["lease_id"] == launch["launch_lease_id"] and lease["lease_id"] not in lease_ids
                and lease["cancelled"] is False and lease["parent_lease_id"] is None
                and lease["requires_gpu"] is False and lease["lane"] == "validation"
                and exact_int(lease["sequence"]) == index + 1, "unique ordered unparented lease declarations")
        lease_ids.add(identity(lease["lease_id"]))
        profile = {"cpu_slots": 1, "memory_mb": 256 if phase == "setup" else 512,
                   "child_process_slots": 1 if phase == "setup" else 3}
        closed(launch["root_allocations"], profile, "closed recorded root allocation")
        for key, quantity in profile.items():
            require(exact_int(lease[key]) == quantity and exact_int(launch["root_allocations"][key]) >= quantity,
                    "exact phase lease and accounted root allocation")
        require(exact_int(envelope["resident_memory_bytes"]) == profile["memory_mb"] * 1024 * 1024
                and exact_int(envelope["memory_bytes"]) == 4294967296
                and same(envelope["resident_memory_bytes"], request["limits"]["resident_memory_bytes"]), "recorded distinct RSS/address-space limits")
        if phase != "setup":
            env = docs["phase_environments"][jvm_index]
            jvm_index += 1
            shaped(env, "phase_environment")
            require(env["case"] == case and env["phase"] == phase
                    and env["foreign_configuration_environment_absent"] is True and env["private_home_and_tmpdir"] is True
                    and "-Xmx256m" in env["jvm_args"].split() and "-XX:ActiveProcessorCount=1" in env["jvm_args"].split()
                    and env["jvm_gc_args"] == "-XX:+UseSerialGC", "recorded finite JVM profile")
        if phase == "model":
            fixture = docs["fixtures"]["true" if index // 3 == 0 else "false"]
            for path, text, pin in (("BoundedCounter.tla", "model_text", "model_digest"),
                                    ("apalache.cfg", "apalache_config_text", "apalache_config_digest")):
                require(request["input_sha256"].get(path) == fixture[pin]
                        and exact_int(request["input_bytes"].get(path)) == len(fixture[text].encode()), "inert phase input text raw digest join")
        rows.append({"case": case, "phase": phase, "recorded_lease_id": lease["lease_id"],
                     "recorded_sequence": index + 1, "recorded_returncode": expected_exit,
                     "recorded_deadline": budget["deadline"], "recorded_request_timeout_seconds": budget["request_timeout_seconds"],
                     "recorded_lease_profile": profile, "workspace_cleaned": True, "native_origin_authenticated": False})
    require(exact_int(native["native_lifecycles"]) == exact_int(native["launches"]) == exact_int(native["lifecycles"]) == 6
            and exact_int(native["prelaunch_lifecycles"]) == 0
            and same(native["phase_counts"], {"setup": 2, "model": 2, "help": 2}), "complete aggregate phase quantities")
    return rows


def deadline_case(case, index, docs, phases):
    shaped(case, "native_case")
    require(case["case"] == CASE_IDS[index] and case["valid"] is (index == 0)
            and case["aggregate_scope_owner"] == "production_registry"
            and exact_int(case["phase_count"]) == 3 and exact_int(case["selected_delegate_count"]) == 1
            and exact_int(case["operation_timeout_ms"]) == 30000 and all(case[key] is True for key in (
                "ambient_scope_absent_before_and_after", "factory_native_deadline_equal", "default_lazy_factory_used",
                "factory_restored", "original_return_observer_restored", "complete_artifact_equal")), "recorded production-created case scope")
    factory, observed = case["factory_operations"], case["native_phase_operations"]
    require(type(factory) is list and len(factory) == 2 and type(observed) is list and len(observed) == 3,
            "complete factory entry/return and setup/model/help population")
    closed(factory[0], {"at_monotonic", "deadline", "phase", "remaining_seconds"}, "closed factory entry")
    closed(factory[1], {"at_monotonic", "deadline", "phase", "same_operation_as_entry"}, "closed factory return")
    require(factory[0]["phase"] == "factory_entry" and factory[1]["phase"] == "factory_return"
            and factory[1]["same_operation_as_entry"] is True, "factory operation identity declaration")
    start, end = recorded_number(factory[0]["at_monotonic"]), recorded_number(factory[1]["at_monotonic"])
    deadline = recorded_number(factory[0]["deadline"])
    require(start <= end < deadline and same(factory[1]["deadline"], deadline)
            and 0 < recorded_number(factory[0]["remaining_seconds"]) <= 30
            and abs(deadline - start - factory[0]["remaining_seconds"]) <= 0.02, "one finite factory deadline")
    wanted = docs["phase_budgets"][index * 3:index * 3 + 3]
    require(same(observed, wanted) and all(same(row["deadline"], deadline) for row in observed),
            "factory and all three native phase deadlines exact")
    require(start <= wanted[0]["at_monotonic"] <= end <= wanted[1]["at_monotonic"] <= wanted[2]["at_monotonic"] < deadline,
            "recorded factory/setup/model/help order")
    require(type(case["dispatch"]) is dict and recorded_number(case["dispatch"]["at_monotonic"]) < start,
            "advisory dispatch precedes production API entry")
    fixture = docs["fixtures"]["true" if index == 0 else "false"]
    shaped(fixture, "fixture")
    request, attempt, result, original = (case[key] for key in ("request", "attempt", "result", "original_outcome"))
    for value, kind in ((request, "request"), (attempt, "attempt"), (result, "generic_result"), (original, "original_outcome"),
                        (request["payload"], "request_payload"), (result["payload"], "generic_payload"),
                        (result["authority"], "generic_authority"), (original["result"], "typed_result"),
                        (original["receipt"], "typed_receipt")):
        shaped(value, kind)
    require(same(case["submitted_artifact"], fixture) and same(case["decoded_artifact"], fixture)
            and same(request["payload"]["artifacts"], fixture), "whole submitted/decoded/request inert artifact unchanged")
    for stem in ("model", "apalache_config", "tlc_config"):
        require(type(fixture[stem + "_text"]) is str
                and sha256(fixture[stem + "_text"].encode()).hexdigest() == digest(fixture[stem + "_digest"]), "inert fixture text digest")
    request_pin, attempt_pin = sha256(wire(request)).hexdigest(), sha256(wire(attempt)).hexdigest()
    require(case["request_digest"] == original["request_digest"] == attempt["request_digest"] == result["request_digest"] == request_pin
            and case["attempt_digest"] == result["attempt_digest"] == attempt_pin, "complete request and attempt numeric wire identities")
    require(request["schema_version"] == "proof-backend-request/v1" and attempt["schema_version"] == "proof-backend-attempt/v1"
            and result["schema_version"] == "bounded-result/v1" and request["requested_backend_id"] == "apalache"
            and request["query_kind"] == "satisfiability" and request["logic_family"] == "state_transition"
            and attempt["status"] == "succeeded" and result["status"] == "unknown", "generic unknown outcome remains unknown")
    for value in (attempt, result):
        closed(value["usage"], {"elapsed_ms", "output_bytes", "peak_memory_bytes", "steps"}, "complete typed generic zero usage")
        closed(value["bounds"], {"max_memory_bytes", "max_output_bytes", "max_steps", "timeout_ms"}, "closed historical bounds")
        require(same(value["bounds"], request["bounds"]) and type(value["usage"]) is dict
                and all(exact_int(count) == 0 for count in value["usage"].values())
                and value["diagnostics"] == ["foreign outcome recorded without authority upgrade; generic conclusions remain non-conclusive"],
                "generic original bounds/zero usage/non-upgrade diagnostics")
    require(same(request["bounds"], {"max_memory_bytes": 536870912, "max_output_bytes": 65536,
                                   "max_steps": 100000, "timeout_ms": 30000}), "unchanged complete original request bounds")
    authority = result["authority"]
    require(authority["schema_version"] == "result-authority/v1" and authority["kind"] == "satisfiability"
            and authority["issuer"] == "apalache" and authority["method"] == "proof-backend-adapter/v1"
            and authority["scope_digest"] == request_pin and authority["evidence_digests"] == [], "generic descriptive authority ceiling")
    digest(authority["configuration_digest"])
    typed, receipt, payload = original["result"], original["receipt"], result["payload"]
    status = "satisfied" if index == 0 else "violated"
    require(same(payload["result"], typed) and payload["adapter_return_type"] == "ModelCheckOutcome"
            and typed["status"] == payload["result_status"] == status
            and typed["authority"] == payload["result_authority"] == "model_check"
            and typed["translation_ceiling"] == "bounded" and receipt["bounded"] is True and receipt["unbounded_proof"] is False,
            "historical exact bounded typed model-check payload")
    model_life = docs["phase_lifecycles"][index * 3 + 1]["result"]
    for field in ("command", "stdout", "stderr", "returncode"):
        require(same(receipt[field], model_life[field]), "typed receipt exact native phase output")
    require(attempt["output_digest"] == result["output_digest"] and attempt["artifact_digests"] == [], "recorded output digest without algorithm claim")
    digest(result["output_digest"])
    return {"case": case["case"], "recorded_scope_owner": "production_registry",
            "recorded_operation_timeout_ms": 30000, "recorded_shared_deadline": deadline,
            "factory_operations": factory, "native_phase_operations": observed, "phase_count": len(phases),
            "advisory_dispatch_at_monotonic": case["dispatch"]["at_monotonic"], "advisory_dispatch_outside_api_deadline": True,
            "request_sha256_rederived": request_pin, "attempt_sha256_rederived": attempt_pin,
            "generic_attempt_status": "succeeded", "generic_result_status": "unknown",
            "typed_result_status": status, "typed_authority": "model_check",
            "complete_typed_payload_sha256": sha256(wire(typed)).hexdigest(), "recorded_output_digest": result["output_digest"],
            "deadline_origin_authenticated": False, "native_interruption_exercised": False,
            "structural_and_semantic_counterexample_replay_requalified": False}


def derive(docs, pins):
    tests, preservation = source_and_test_observations(docs, pins)
    native = docs["native_result"]
    shaped(native, "native_result")
    shaped(native["scope"], "native_scope")
    shaped(native["checks"], "native_checks")
    require(native["schema"] == "tla-registry-operation-budget-benchmark@1" and native["status"] == "passed"
            and same(native["scope"], NATIVE_SCOPE) and all(value is True for value in native["checks"].values()),
            "recorded native cooperative production-scope declaration")
    require(type(native["cases"]) is list and len(native["cases"]) == 2, "complete two normally completed native cases")
    require(same(native["source_pins_before"], native["source_pins_after"])
            and same(native["source_pins_before"], docs["execution_freeze"]["native_sources"])
            and same(native["tool_files_before"], native["tool_files_after"]), "recorded native source/tool observations stable")
    metadata_digests(native["tool_files_before"])
    for role, leaf in (("phase_requests", "request-audit.json"), ("phase_launches", "launch-audit.json"),
                       ("phase_lifecycles", "lifecycle-audit.json"), ("phase_budgets", "phase-budget-audit.json"),
                       ("phase_environments", "apalache-environment-audit.json")):
        require(native["audit_sha256"].get(leaf) == pins[role]["sha256"], "native phase audit raw commitment")
    phases = phase_observations(docs, native)
    cases = [deadline_case(value, index, docs, phases[index * 3:index * 3 + 3]) for index, value in enumerate(native["cases"])]
    require(cases[0]["recorded_shared_deadline"] != cases[1]["recorded_shared_deadline"], "separate production deadline per serial case")
    shared, saved = native["shared_after"], docs["scheduler_configuration"]
    shaped(saved, "scheduler_configuration")
    require(saved["schema"] == "codebase-saved-scheduler-config@1" and saved["allow_foreign_work"] is True
            and same(saved["config"], native["shared_before"]["config"]) and same(saved["config"], shared["config"]),
            "recorded shared scheduler config unchanged")
    for key in ("active_leases", "waiting_requests", "owned_active_leases", "owned_waiting_requests"):
        require(exact_int(shared[key]) == 0, "recorded scoped scheduler drain")
    require(exact_int(shared["next_sequence"]) == 7, "six recorded lease acquisitions and releases")
    final_counters = native["cases"][1]["dispatch"]["capacity_snapshot"]["counters"]
    require(exact_int(final_counters["acquisitions_total"]) == exact_int(final_counters["releases_total"]) == 3,
            "separate second predispatch snapshot after first case drain")
    for field, expected in (("native_phases", 6), ("native_success_cases", 2)):
        require(exact_int(docs["qualification"][field]) == expected, "qualified aggregate native observation count")
    require(same(docs["qualification"]["native_seconds"], native["elapsed_seconds"])
            and same(docs["qualification"]["native_wrapper_seconds"], docs["native_command_result"]["seconds"]),
            "recorded native and wrapper durations kept distinct")
    recorded_number(native["elapsed_seconds"])
    return {"deadline_cases": cases, "phase_population": phases,
            "resources": {"recorded_acquisition_count": 6, "recorded_release_count": 6, "recorded_next_sequence": 7,
                          "recorded_zero_owned_leases_and_waiters": True, "recorded_shared_config": saved["config"],
                          "advisory_predispatch_separate_from_api_deadline": True, "live_cleanup_reobserved": False,
                          "hard_containment_requalified": False},
            "test_observations": tests, "source_preservation": preservation,
            "unfollowed_body_closure": dict.fromkeys(("production_source", "selected_test_sources", "tools",
                                                     "prior_qualification_bodies", "model_database_or_keys"), "unknown_not_selected"),
            "production_tasks_closed": []}


def audit(manifest, output, *, relocated_sources=None):
    started = time.monotonic()
    original, copies = Capture(relocated_sources, started=started), Capture(started=started)
    manifest, output = lexical_path(str(manifest)), lexical_path(str(output))
    require(output.parent.resolve(strict=True) == output.parent and not output.exists() and not output.is_symlink(),
            "fresh canonical output directory")
    raw_manifest = original.read(manifest, maximum=MAX_MANIFEST)
    selection = document(raw_manifest)
    closed(selection, {"schema", "selected_profile", "selected_files"}, "closed deadline input manifest")
    require(selection["schema"] == INPUT_SCHEMA and selection["selected_profile"] == PROFILE
            and type(selection["selected_files"]) is list and len(selection["selected_files"]) == len(ROLES),
            "fixed selected profile and population")
    pins = {}
    for role, row in zip(ROLES, selection["selected_files"], strict=True):
        closed(row, {"role", "path", "sha256", "size_bytes"}, "closed selected descriptor")
        require(row["role"] == role, "fixed ordered selected roles")
        pins[role] = descriptor({key: row[key] for key in ("path", "sha256", "size_bytes")})
        require(pins[role]["sha256"] == PUBLIC_PINS[role], "fixed independent retained public selection")
    paths = {pin["path"] for pin in pins.values()}
    require(len(paths) == len(ROLES) and str(manifest) not in paths, "disjoint original input population")
    if relocated_sources is not None:
        require(type(relocated_sources) is dict and set(relocated_sources) == {str(manifest), *paths},
                "closed explicit relocated input population")
        require(len(set(relocated_sources.values())) == len(relocated_sources), "distinct relocated physical inputs")
    physical = [Path(relocated_sources.get(path, path)) if relocated_sources else Path(path) for path in [str(manifest), *paths]]
    require(all(output != path and output not in path.parents and path not in output.parents for path in physical),
            "disjoint physical inputs and owned output")
    bodies = {role: original.read(Path(pins[role]["path"]), pins[role]) for role in ROLES}
    docs = {role: document(raw) for role, raw in bodies.items()}
    findings = derive(docs, pins)
    original.stable()
    output.mkdir(mode=0o755)
    root_identity = (output.lstat().st_dev, output.lstat().st_ino)
    retained = output / "retained"
    retained.mkdir(mode=0o755)
    retained_identity = (retained.lstat().st_dev, retained.lstat().st_ino)
    copy_rows, members = [], ["retained/input.json"]
    write_new(retained / "input.json", raw_manifest)
    copies.read(retained / "input.json", maximum=MAX_MANIFEST)
    for index, role in enumerate(ROLES):
        path = retained / (f"{index:02}-" + role + ".json")
        write_new(path, bodies[role])
        pin = {"path": str(path), "sha256": pins[role]["sha256"], "size_bytes": pins[role]["size_bytes"]}
        require(copies.read(path, pin) == bodies[role], "original and retained copy raw bytes")
        copy_rows.append({"role": role, **pins[role], "retained_copy": pin})
        members.append(path.relative_to(output).as_posix())
    nested = {"schema": "codebase-ir-registry-operation-deadline-selected-custody@1", "status": "passed", "qualified": True,
              "selected_files": copy_rows, "manifest_sha256": sha256(raw_manifest).hexdigest(), "scope": scope(),
              "original_capture_bytes": original.total, "copy_capture_bytes": copies.total, **findings}
    nested_path = output / "selected_custody.json"
    nested_raw = bounded_canonical(nested, MAX_REPORT)
    write_new(nested_path, nested_raw)
    nested_identity = Capture.fingerprint(nested_path)
    members.append(nested_path.name)
    report = {"schema": SCHEMA, "workflow": "registry_operation_deadline_custody", "selected_profile": PROFILE,
              "status": "passed", "qualified": True, "selected_files": copy_rows,
              "selected_file_count": len(ROLES), "selected_input_bytes": sum(pin["size_bytes"] for pin in pins.values()),
              "manifest_sha256": sha256(raw_manifest).hexdigest(), **{role + "_sha256": pins[role]["sha256"] for role in ROLES},
              **scope(), "scope": scope(), **findings,
              "limits": {"max_file_bytes": MAX_FILE, "max_original_bytes": MAX_BYTES, "max_copy_bytes": MAX_BYTES,
                         "max_files_per_cache": MAX_FILES, "max_manifest_bytes": MAX_MANIFEST, "max_report_bytes": MAX_REPORT,
                         "max_seconds": MAX_SECONDS, "max_depth": MAX_DEPTH, "max_values": MAX_VALUES},
              "custody": {"original_file_count": len(original.files), "copy_file_count": len(copies.files),
                          "original_capture_bytes": original.total, "copy_capture_bytes": copies.total,
                          "local_receipt": {"path": str(nested_path), "sha256": sha256(nested_raw).hexdigest(), "size_bytes": len(nested_raw)}},
              "elapsed_seconds": time.monotonic() - started}
    report_path = output / "registry_operation_deadline_custody.json"
    report_raw = bounded_canonical(report, MAX_REPORT)
    write_new(report_path, report_raw)
    report_identity = Capture.fingerprint(report_path)
    members.append(report_path.name)
    original.stable()
    copies.stable()
    require(Capture.raw(nested_path, len(nested_raw)) == nested_raw and same(document(nested_raw), nested), "final local nested raw body")
    require(Capture.raw(report_path, len(report_raw)) == report_raw and same(document(report_raw), report), "final main raw report body")
    require((output.lstat().st_dev, output.lstat().st_ino) == root_identity, "owned output directory identity unchanged")
    output_population(output, members)
    # This is bounded filesystem custody, not an atomic filesystem snapshot.
    # Reopen every selected body after population observations, including the
    # receipts already read above, so late observed drift cannot be accepted.
    for _ in range(2):
        output_population(output, members)
        original.stable()
        copies.stable()
        require(Capture.raw(nested_path, len(nested_raw)) == nested_raw, "closing nested raw body")
        require(Capture.raw(report_path, len(report_raw)) == report_raw, "closing main raw body")
        require(Capture.fingerprint(nested_path) == nested_identity
                and Capture.fingerprint(report_path) == report_identity, "closing receipt identities unchanged")
        require((output.lstat().st_dev, output.lstat().st_ino) == root_identity,
                "closing output directory identity unchanged")
        require((retained.lstat().st_dev, retained.lstat().st_ino) == retained_identity,
                "closing retained directory identity unchanged")
    original.deadline()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = audit(args.manifest, args.output)
    print(json.dumps({"qualified": report["qualified"], "report": str(args.output / "registry_operation_deadline_custody.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
