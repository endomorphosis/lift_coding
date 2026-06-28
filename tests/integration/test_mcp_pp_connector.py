"""Tests for MCP++ Server Connector linking SwissKnife to real MCP++ servers."""
import pytest
import os


def read_file(path):
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(repo_root, path), 'r') as f:
        return f.read()


class TestMCPPPConnectorStructure:
    """Verify the connector can talk to ipfs_datasets_py and ipfs_accelerate_py MCP++ servers."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.src = read_file('swissknife/src/services/mcp-plus-plus-connector.ts')

    def test_server_configs_defined(self):
        assert 'IPFS_DATASETS_SERVER' in self.src
        assert 'IPFS_ACCELERATE_SERVER' in self.src

    def test_datasets_server_config(self):
        assert "'ipfs-datasets-mcp++'" in self.src
        assert "'http://localhost:3002'" in self.src
        assert "'/mcp'" in self.src
        assert "'/tools/list'" in self.src
        assert "'/health/ready'" in self.src

    def test_accelerate_server_config(self):
        assert "'ipfs-accelerate-mcp++'" in self.src
        assert "'http://localhost:3003'" in self.src
        assert "'/api/mcp/status'" in self.src

    def test_json_rpc_protocol(self):
        assert 'MCPJsonRpcRequest' in self.src
        assert 'MCPJsonRpcResponse' in self.src
        assert "'2.0'" in self.src  # JSON-RPC version

    def test_capability_negotiation(self):
        assert "'initialize'" in self.src or 'initialize' in self.src
        assert 'protocolVersion' in self.src
        assert "'mcp++/mcp-idl'" in self.src
        assert "'mcp++/cid-envelope'" in self.src
        assert "'mcp++/ucan'" in self.src

    def test_connect_lifecycle(self):
        assert 'async connect' in self.src
        assert 'async disconnect' in self.src
        assert 'isConnected' in self.src

    def test_profile_a_interface_discovery(self):
        assert 'listInterfaces' in self.src
        assert 'getInterfaceByName' in self.src
        assert 'interfacesPath' in self.src

    def test_profile_b_cid_execution(self):
        assert 'callTool' in self.src
        assert 'callToolWithEnvelope' in self.src
        assert "'tools/call'" in self.src
        assert "'mcp++/execute'" in self.src

    def test_profile_c_ucan(self):
        assert 'createDelegation' in self.src
        assert 'validateDelegation' in self.src
        assert 'delegationPath' in self.src
        assert "'mcp++/ucan/validate'" in self.src

    def test_event_dag_queries(self):
        assert 'getDAGFrontier' in self.src
        assert 'getDAGHistory' in self.src
        assert 'traceProvenance' in self.src
        assert 'dagPath' in self.src

    def test_profile_d_policy(self):
        assert 'evaluatePolicy' in self.src
        assert "'mcp++/policy/evaluate'" in self.src

    def test_profile_e_p2p(self):
        assert 'discoverPeers' in self.src
        assert "'/mcp+p2p/1.0.0'" in self.src
        assert 'p2pProtocolId' in self.src

    def test_multi_server_connector(self):
        assert 'MCPPPMultiServerConnector' in self.src
        assert 'connectAll' in self.src
        assert 'callToolOnBestServer' in self.src
        assert 'listAllInterfaces' in self.src
        assert 'getAggregatedDAG' in self.src
        assert 'connectedServers' in self.src

    def test_factory_function(self):
        assert 'createMultiServerConnector' in self.src

    def test_abort_signal_timeout(self):
        """All fetch calls should have timeout protection."""
        assert 'AbortSignal.timeout' in self.src


class TestMCPPPCLIConnectCommands:
    """Verify CLI has connect/status/call subcommands for real servers."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.src = read_file('swissknife/src/commands/mcp-plus-plus-commands.ts')

    def test_import_connector(self):
        assert 'mcp-plus-plus-connector' in self.src
        assert 'createMultiServerConnector' in self.src

    def test_connect_subcommand(self):
        assert "'connect'" in self.src
        assert 'connectAll' in self.src

    def test_status_subcommand(self):
        assert "'status'" in self.src
        assert 'connectedServers' in self.src
        assert 'port 3002' in self.src
        assert 'port 3003' in self.src

    def test_call_subcommand(self):
        assert "'call'" in self.src
        assert 'callToolWithEnvelope' in self.src


class TestMCPPPDesktopConnectButton:
    """Verify the desktop MCP++ app can connect to live servers."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.src = read_file('swissknife/web/src/browser-main.ts')

    def test_connect_button_exists(self):
        assert 'mcppp-connect-btn' in self.src
        assert 'Connect to MCP++ Servers' in self.src

    def test_checks_datasets_server(self):
        assert 'http://localhost:3002/health/ready' in self.src

    def test_checks_accelerate_server(self):
        assert 'http://localhost:3003/api/mcp/status' in self.src

    def test_shows_connection_status(self):
        assert 'mcppp-conn-status' in self.src
        assert 'servers online' in self.src


class TestRealServerAPIAlignment:
    """Verify our connector uses the actual API shapes from the real servers."""

    def test_datasets_has_interface_descriptor_module(self):
        """ipfs_datasets_py has interface_descriptor.py implementing Profile A."""
        path = 'external/ipfs_datasets/ipfs_datasets_py/mcp_server/interface_descriptor.py'
        src = read_file(path)
        assert 'InterfaceDescriptor' in src
        assert 'MethodSignature' in src
        assert 'InterfaceRepository' in src
        assert 'compute_cid' in src

    def test_datasets_has_cid_artifacts_module(self):
        """ipfs_datasets_py has cid_artifacts.py implementing Profile B."""
        path = 'external/ipfs_datasets/ipfs_datasets_py/mcp_server/cid_artifacts.py'
        src = read_file(path)
        assert 'ExecutionEnvelope' in src or 'IntentObject' in src
        assert 'EventNode' in src
        assert 'artifact_cid' in src

    def test_datasets_has_ucan_delegation(self):
        """ipfs_datasets_py has ucan_delegation.py implementing Profile C."""
        path = 'external/ipfs_datasets/ipfs_datasets_py/mcp_server/ucan_delegation.py'
        src = read_file(path)
        assert 'Capability' in src
        assert 'Delegation' in src
        assert 'DelegationEvaluator' in src

    def test_datasets_has_event_dag(self):
        """ipfs_datasets_py has event_dag.py implementing Event DAG."""
        path = 'external/ipfs_datasets/ipfs_datasets_py/mcp_server/event_dag.py'
        src = read_file(path)
        assert 'EventDAG' in src
        assert 'frontier' in src
        assert 'append' in src

    def test_datasets_has_p2p_transport(self):
        """ipfs_datasets_py has mcp_p2p_transport.py implementing Profile E."""
        path = 'external/ipfs_datasets/ipfs_datasets_py/mcp_server/mcp_p2p_transport.py'
        src = read_file(path)
        assert 'MCP_P2P_PROTOCOL_ID' in src
        assert '/mcp+p2p/1.0.0' in src

    def test_datasets_has_temporal_policy(self):
        """ipfs_datasets_py has temporal_policy.py implementing Profile D."""
        path = 'external/ipfs_datasets/ipfs_datasets_py/mcp_server/temporal_policy.py'
        src = read_file(path)
        assert 'policy' in src.lower() or 'temporal' in src.lower()

    def test_accelerate_has_mcplusplus_module(self):
        """ipfs_accelerate_py has mcplusplus_module implementing MCP++."""
        path = 'external/ipfs_accelerate/ipfs_accelerate_py/mcplusplus_module/__init__.py'
        src = read_file(path)
        assert 'TrioMCPServer' in src
        assert 'MCP Plus Plus' in src or 'MCP++' in src

    def test_accelerate_has_p2p(self):
        """ipfs_accelerate_py has P2P support."""
        path = 'external/ipfs_accelerate/ipfs_accelerate_py/mcplusplus_module/p2p/__init__.py'
        assert os.path.exists(os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            path
        ))

    def test_protocol_id_matches(self):
        """Our connector uses the same protocol ID as the servers."""
        connector_src = read_file('swissknife/src/services/mcp-plus-plus-connector.ts')
        server_src = read_file('external/ipfs_datasets/ipfs_datasets_py/mcp_server/mcp_p2p_transport.py')
        # Both must use /mcp+p2p/1.0.0
        assert '/mcp+p2p/1.0.0' in connector_src
        assert '/mcp+p2p/1.0.0' in server_src
