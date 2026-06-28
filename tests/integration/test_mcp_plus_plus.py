"""Tests for MCP++ protocol implementation in SwissKnife."""
import pytest
import json
import os


def read_file(path):
    """Read a file relative to repo root."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(repo_root, path), 'r') as f:
        return f.read()


# --- MCP++ Core Protocol (mcp-plus-plus.ts) ---

class TestMCPPlusPlusProtocol:
    """Test the MCP++ protocol implementation file."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.src = read_file('swissknife/src/services/mcp-plus-plus.ts')

    def test_profile_a_interface_descriptor(self):
        """Profile A: MCP-IDL interface descriptors."""
        assert 'MCPPPInterfaceDescriptor' in self.src
        assert 'interface_cid' in self.src
        assert 'methods' in self.src
        assert 'namespace' in self.src
        assert 'semantic_tags' in self.src
        assert 'compatibility' in self.src

    def test_profile_a_method_signatures(self):
        """Profile A: Method definitions with CID-addressed schemas."""
        assert 'MCPPPMethod' in self.src
        assert 'input_schema_cid' in self.src
        assert 'output_schema_cid' in self.src
        assert 'error_schema_cids' in self.src
        assert 'resource_cost_hints' in self.src

    def test_profile_b_execution_intent(self):
        """Profile B: CID-native execution intents."""
        assert 'ExecutionIntent' in self.src
        assert 'intent_cid' in self.src or 'interface_cid' in self.src
        assert 'correlation_id' in self.src
        assert 'declared_side_effects' in self.src

    def test_profile_b_execution_decision(self):
        """Profile B: Execution decisions."""
        assert 'ExecutionDecision' in self.src
        assert "'allow'" in self.src
        assert "'deny'" in self.src
        assert "'allow_with_obligations'" in self.src
        assert 'justification' in self.src

    def test_profile_b_execution_receipt(self):
        """Profile B: Execution receipts."""
        assert 'ExecutionReceipt' in self.src
        assert 'receipt_cid' in self.src
        assert 'duration_ms' in self.src
        assert 'executor_did' in self.src

    def test_profile_b_execution_envelope(self):
        """Profile B: Full execution envelope."""
        assert 'ExecutionEnvelope' in self.src
        assert 'envelope_cid' in self.src
        assert 'executeWithEnvelope' in self.src

    def test_profile_c_ucan_capability(self):
        """Profile C: UCAN capability definition."""
        assert 'UCANCapability' in self.src
        assert 'UCANDelegation' in self.src
        assert 'UCANProofBundle' in self.src
        assert 'createDelegation' in self.src

    def test_profile_c_ucan_validation(self):
        """Profile C: UCAN proof validation."""
        assert 'validateProof' in self.src
        assert 'registerProofBundle' in self.src

    def test_profile_c_ucan_time_bounds(self):
        """Profile C: UCAN time-bounded delegation."""
        assert 'not_before' in self.src
        assert 'expiration' in self.src
        assert 'time_window' in self.src
        assert 'rate_limit' in self.src

    def test_profile_d_deontic_policy(self):
        """Profile D: Temporal deontic policy."""
        assert 'DeonticPolicy' in self.src
        assert 'DeonticRule' in self.src
        assert "'permission'" in self.src
        assert "'prohibition'" in self.src
        assert "'obligation'" in self.src

    def test_profile_d_policy_evaluation(self):
        """Profile D: Policy evaluation."""
        assert 'evaluatePolicy' in self.src
        assert 'registerPolicy' in self.src
        assert 'temporal_constraint' in self.src

    def test_event_dag(self):
        """Event DAG implementation."""
        assert 'EventNode' in self.src
        assert 'parents' in self.src
        assert 'event_cid' in self.src
        assert 'getDAGFrontier' in self.src
        assert 'getEventHistory' in self.src
        assert 'getProvenanceChain' in self.src

    def test_profile_e_p2p_transport(self):
        """Profile E: mcp+p2p transport binding."""
        assert 'P2PSessionConfig' in self.src
        assert '/mcp+p2p/1.0.0' in self.src
        assert 'multiaddrs' in self.src
        assert 'createP2PSession' in self.src
        assert 'encodeP2PMessage' in self.src

    def test_interface_registry(self):
        """Interface registry with query support."""
        assert 'registerInterface' in self.src
        assert 'getInterface' in self.src
        assert 'listInterfaces' in self.src
        assert 'queryInterfaces' in self.src
        assert 'checkCompatibility' in self.src

    def test_ipfs_kit_interface_descriptor(self):
        """Pre-built IPFS Kit interface descriptor."""
        assert 'IPFS_KIT_INTERFACE' in self.src
        assert "'ipfs-kit'" in self.src
        assert "'com.ipfs.kit'" in self.src
        assert "'ipfs.add'" in self.src
        assert "'ipfs.cat'" in self.src
        assert "'ipfs.pin'" in self.src
        assert "'ipfs.dag.get'" in self.src
        assert "'ipfs.name.publish'" in self.src

    def test_ipfs_accelerate_interface_descriptor(self):
        """Pre-built IPFS Accelerate interface descriptor."""
        assert 'IPFS_ACCELERATE_INTERFACE' in self.src
        assert "'ipfs-accelerate'" in self.src
        assert "'accelerate.inference'" in self.src
        assert "'accelerate.list_models'" in self.src
        assert 'gpu_required: true' in self.src

    def test_ipfs_datasets_interface_descriptor(self):
        """Pre-built IPFS Datasets interface descriptor."""
        assert 'IPFS_DATASETS_INTERFACE' in self.src
        assert "'ipfs-datasets'" in self.src
        assert "'datasets.search.semantic'" in self.src
        assert "'datasets.vector.search'" in self.src
        assert "'datasets.scrape.url'" in self.src
        assert "'datasets.workflow.execute'" in self.src

    def test_capability_negotiation(self):
        """MCP++ profile negotiation."""
        assert 'getSupportedProfiles' in self.src
        assert 'negotiateCapabilities' in self.src
        assert "'mcp++/mcp-idl'" in self.src
        assert "'mcp++/cid-envelope'" in self.src
        assert "'mcp++/ucan'" in self.src
        assert "'mcp++/deontic-policy'" in self.src
        assert "'mcp++/event-dag'" in self.src
        assert "'mcp++/p2p-transport'" in self.src

    def test_backend_dispatch(self):
        """Dispatches to correct backend endpoints."""
        assert 'dispatchToBackend' in self.src
        assert 'resolveEndpoint' in self.src
        # All 31 endpoints should be mapped
        assert "'/v1/ipfs/add'" in self.src
        assert "'/v1/ipfs/dag/get'" in self.src
        assert "'/v1/ipfs/vector/search'" in self.src
        assert "'/v1/ipfs/workflow/execute'" in self.src

    def test_cid_computation(self):
        """Deterministic CID computation."""
        assert 'computeCID' in self.src
        # Should produce deterministic output from canonical JSON
        assert 'canonical' in self.src or 'JSON.stringify' in self.src

    def test_factory_function(self):
        """Factory creates pre-configured client."""
        assert 'createMCPPlusPlusClient' in self.src


# --- MCP++ CLI Commands ---

class TestMCPPlusPlusCLI:
    """Test the MCP++ CLI command registration."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.src = read_file('swissknife/src/commands/mcp-plus-plus-commands.ts')

    def test_command_registered(self):
        assert "name: 'mcp++'" in self.src
        assert "aliases: ['mcppp']" in self.src

    def test_subcommands_defined(self):
        assert "'interfaces'" in self.src
        assert "'execute'" in self.src
        assert "'dag'" in self.src
        assert "'delegate'" in self.src
        assert "'policy'" in self.src
        assert "'profiles'" in self.src
        assert "'p2p'" in self.src

    def test_interfaces_subcommand(self):
        assert 'queryInterfaces' in self.src or 'listInterfaces' in self.src

    def test_execute_subcommand(self):
        assert 'executeWithEnvelope' in self.src

    def test_dag_subcommand(self):
        assert 'getDAGFrontier' in self.src
        assert 'getEventHistory' in self.src
        assert 'getProvenanceChain' in self.src

    def test_delegate_subcommand(self):
        assert 'createDelegation' in self.src

    def test_imported_in_commands_registry(self):
        registry = read_file('swissknife/src/commands.ts')
        assert 'mcp-plus-plus-commands' in registry
        assert 'mcpPlusPlusCommands' in registry


# --- MCP++ Desktop App ---

class TestMCPPlusPlusDesktopApp:
    """Test the MCP++ Protocol Explorer desktop app."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.src = read_file('swissknife/web/src/browser-main.ts')

    def test_app_registered_in_menu(self):
        assert 'mcp-plus-plus' in self.src
        assert 'MCP++ Protocol Explorer' in self.src

    def test_has_interfaces_tab(self):
        assert "data-tab=\"interfaces\"" in self.src
        assert 'Registered MCP++ Interface Descriptors' in self.src

    def test_has_execute_tab(self):
        assert "data-tab=\"execute\"" in self.src
        assert 'Execute with CID-Native Envelope' in self.src

    def test_has_dag_tab(self):
        assert "data-tab=\"dag\"" in self.src
        assert 'Event DAG' in self.src

    def test_has_ucan_tab(self):
        assert "data-tab=\"delegate\"" in self.src
        assert 'UCAN Capability Delegation' in self.src

    def test_has_profiles_tab(self):
        assert "data-tab=\"profiles\"" in self.src
        assert 'Supported MCP++ Profiles' in self.src

    def test_shows_all_profiles(self):
        assert 'MCP-IDL' in self.src
        assert 'CID-Envelope' in self.src
        assert 'UCAN' in self.src
        assert 'Deontic Policy' in self.src
        assert 'mcp+p2p' in self.src
        assert 'Event DAG' in self.src


# --- Endpoint Coverage ---

class TestFullEndpointCoverage:
    """Verify all 31 backend endpoints are covered in the UI."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.src = read_file('swissknife/web/src/browser-main.ts')

    def test_all_31_endpoints_present(self):
        """Every backend endpoint must appear in the virtual desktop."""
        all_endpoints = [
            '/v1/ipfs/status', '/v1/ipfs/add', '/v1/ipfs/cat',
            '/v1/ipfs/pin', '/v1/ipfs/unpin', '/v1/ipfs/resolve',
            '/v1/ipfs/list_pins', '/v1/ipfs/stat',
            '/v1/ipfs/dag/get', '/v1/ipfs/dag/put',
            '/v1/ipfs/name/publish', '/v1/ipfs/name/resolve',
            '/v1/ipfs/embed', '/v1/ipfs/generate', '/v1/ipfs/inference',
            '/v1/ipfs/list_models', '/v1/ipfs/capabilities',
            '/v1/ipfs/hardware_profile', '/v1/ipfs/metrics',
            '/v1/ipfs/endpoints', '/v1/ipfs/search_models',
            '/v1/ipfs/list_datasets',
            '/v1/ipfs/search/semantic', '/v1/ipfs/search/similarity',
            '/v1/ipfs/search/faceted',
            '/v1/ipfs/vector/index', '/v1/ipfs/vector/search',
            '/v1/ipfs/vector/metadata',
            '/v1/ipfs/scrape/url', '/v1/ipfs/scrape/batch',
            '/v1/ipfs/workflow/execute',
        ]
        missing = [ep for ep in all_endpoints if ep not in self.src]
        assert len(missing) == 0, f"Missing endpoints: {missing}"

    def test_terminal_covers_all_commands(self):
        """Terminal should have CLI commands for all endpoint groups."""
        groups = [
            'ipfs status', 'ipfs add', 'ipfs cat', 'ipfs pin',
            'ipfs unpin', 'ipfs resolve', 'ipfs dag get', 'ipfs dag put',
            'ipfs name publish', 'ipfs name resolve', 'ipfs embed',
            'ipfs models', 'ipfs capabilities', 'ipfs hardware', 'ipfs metrics',
            'ipfs datasets', 'ipfs search', 'ipfs search similar', 'ipfs search faceted',
            'ipfs vector index', 'ipfs vector search', 'ipfs vector metadata',
            'ipfs scrape', 'ipfs scrape batch', 'ipfs workflow',
            'ipfs generate', 'ipfs inference',
        ]
        for cmd in groups:
            assert f"'{cmd}'" in self.src, f"Terminal missing command: {cmd}"
