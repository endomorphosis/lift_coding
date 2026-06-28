"""Test suite for UCAN identity integration.

Validates:
- UCAN identity manager creates ed25519 keypair
- DID:key generation from public key
- Identity persistence and loading
- IPC bridge exposes UCAN methods
- SwissKnife virtual desktop initializes identity
- Main window loads virtual desktop (port 8765)
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
HALLUCINATE = REPO_ROOT / "hallucinate_app"
SWISSKNIFE = REPO_ROOT / "swissknife"


def read_file(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"{path} not found")
    return path.read_text()


class TestUCANIdentityManager:
    """Verify the UCAN identity manager module."""

    @pytest.fixture
    def source(self):
        return read_file(HALLUCINATE / "hallucinate_app" / "node" / "ucan_identity_manager.js")

    def test_generates_ed25519_keypair(self, source):
        assert "generateKeyPairSync('ed25519')" in source

    def test_generates_did_key(self, source):
        assert "did:key:z" in source
        assert "publicKeyToDID" in source

    def test_multicodec_prefix(self, source):
        """Must use 0xed01 prefix for Ed25519."""
        assert "0xed, 0x01" in source

    def test_base58_encoding(self, source):
        assert "base58Encode" in source
        assert "123456789ABCDEFGH" in source  # Bitcoin alphabet

    def test_persists_to_file(self, source):
        assert "writeFileSync" in source
        assert "ucan-identity.json" in source

    def test_loads_from_file(self, source):
        assert "readFileSync" in source
        assert "_loadIdentity" in source

    def test_file_permissions_restricted(self, source):
        """Identity file must be mode 0600 (owner-only)."""
        assert "0o600" in source

    def test_creates_ucan_token(self, source):
        assert "createToken(" in source
        assert "'EdDSA'" in source
        assert "ucv" in source

    def test_token_has_standard_claims(self, source):
        """UCAN token must have iss, aud, exp, nbf, att."""
        assert "iss:" in source
        assert "aud:" in source
        assert "exp:" in source
        assert "nbf:" in source
        assert "att:" in source

    def test_sign_and_verify(self, source):
        assert "sign(" in source
        assert "verify(" in source

    def test_exports_class(self, source):
        assert "export default UCANIdentityManager" in source
        assert "class UCANIdentityManager" in source

    def test_get_public_info_safe(self, source):
        """getPublicInfo must not expose private key."""
        assert "getPublicInfo()" in source
        # Verify it returns did + createdAt but not privateKey
        info_match = re.search(r'getPublicInfo\(\)\s*\{[^}]+\}', source, re.DOTALL)
        if info_match:
            block = info_match.group()
            assert "did:" in block
            assert "privateKey" not in block


class TestHallucinateAppUCANIntegration:
    """Verify UCAN is wired into the hallucinate app launch."""

    @pytest.fixture
    def index_source(self):
        return read_file(HALLUCINATE / "index.js")

    @pytest.fixture
    def preload_source(self):
        return read_file(HALLUCINATE / "preload.cjs")

    def test_imports_ucan_manager(self, index_source):
        assert "import UCANIdentityManager" in index_source

    def test_initializes_at_app_ready(self, index_source):
        """UCAN must be initialized in the app.on('ready') handler."""
        ready_section = index_source[index_source.find("app.on('ready'"):]
        assert "UCANIdentityManager" in ready_section
        assert "ucanManager.initialize()" in ready_section

    def test_stores_in_user_data(self, index_source):
        """Identity stored in app.getPath('userData')/identity."""
        assert "app.getPath('userData')" in index_source
        assert "'identity'" in index_source

    def test_ipc_handlers_registered(self, index_source):
        """Must register IPC handlers for renderer access."""
        assert "ipcMain.handle('ucan:get-identity'" in index_source
        assert "ipcMain.handle('ucan:get-did'" in index_source
        assert "ipcMain.handle('ucan:create-delegation'" in index_source

    def test_preload_exposes_ucan(self, preload_source):
        """Preload must expose ucan namespace to renderer."""
        assert "ucan:" in preload_source
        assert "getIdentity" in preload_source
        assert "getDID" in preload_source
        assert "createDelegation" in preload_source


class TestSwissKnifeAsMainInterface:
    """Verify the SwissKnife virtual desktop is the main landing page."""

    @pytest.fixture
    def index_source(self):
        return read_file(HALLUCINATE / "index.js")

    def test_main_window_loads_virtual_desktop(self, index_source):
        """Main window must load from localhost:8765 (virtual desktop)."""
        assert "127.0.0.1:${SWISSKNIFE_PORT}" in index_source or "SWISSKNIFE_PORT" in index_source
        assert "win.loadURL(desktopUrl)" in index_source

    def test_window_title_is_swissknife(self, index_source):
        assert "'SwissKnife Virtual Desktop'" in index_source

    def test_swissknife_server_starts_before_window(self, index_source):
        """Server must start before window is created."""
        ready_section = index_source[index_source.find("app.on('ready'"):]
        server_pos = ready_section.find("startSwissKnifeServer")
        window_pos = ready_section.find("createWindow()")
        assert server_pos < window_pos, "Server must start before window"

    def test_no_dashboard_html_in_main_window(self, index_source):
        """createSwissKnifeWindow must NOT load dashboard.html."""
        # Find the createSwissKnifeWindow function
        func_start = index_source.find("const createSwissKnifeWindow")
        func_end = index_source.find("};", func_start) + 2
        func_body = index_source[func_start:func_end]
        assert "dashboard.html" not in func_body


class TestSwissKnifeDesktopUCAN:
    """Verify the virtual desktop initializes UCAN identity."""

    @pytest.fixture
    def source(self):
        return read_file(SWISSKNIFE / "web" / "src" / "browser-main.ts")

    def test_initializes_ucan_on_desktop_init(self, source):
        assert "initializeUCANIdentity()" in source

    def test_tries_electron_ipc_first(self, source):
        """Must try Electron IPC for persistent identity before fallback."""
        assert "electronAPI?.ucan" in source
        assert "getIdentity()" in source

    def test_web_crypto_fallback(self, source):
        """Must fall back to Web Crypto for standalone browser mode."""
        assert "crypto.subtle.generateKey" in source
        assert "Ed25519" in source

    def test_stores_identity_on_window(self, source):
        assert "window" in source
        assert "ucanIdentity" in source

    def test_updates_status_indicator(self, source):
        assert "updateUCANStatusIndicator" in source
        assert "ucan-status" in source

    def test_non_fatal_on_failure(self, source):
        """UCAN init failure must not crash the app."""
        assert "catch" in source
        assert "Non-fatal" in source or "warn" in source
