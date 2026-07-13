"""CID-addressed public artifact persistence."""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Protocol

from .canonical import assert_public, canonical_json, cid_for


class ArtifactStore(Protocol):
    def put(self, artifact: dict[str, Any]) -> str: ...
    def get(self, cid: str) -> dict[str, Any] | None: ...


class FileCIDArtifactStore:
    """Atomic local block store suitable as an IPFS adapter boundary."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def put(self, artifact: dict[str, Any]) -> str:
        assert_public(artifact)
        raw = canonical_json(artifact)
        cid = cid_for(artifact)
        target = self.root / cid
        with self._lock:
            if target.exists():
                if target.read_bytes() != raw:
                    raise OSError("CID collision or corrupt artifact")
                return cid
            fd, temporary = tempfile.mkstemp(prefix=".profile-h-", dir=self.root)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return cid

    def get(self, cid: str) -> dict[str, Any] | None:
        import json

        if not cid.startswith("b") or not cid[1:].isalnum() or cid.lower() != cid:
            raise ValueError("invalid artifact CID")
        target = self.root / cid
        if not target.exists():
            return None
        value = json.loads(target.read_text(encoding="utf-8"))
        if cid_for(value) != cid:
            raise OSError("artifact CID does not match stored content")
        return value


class IPFSArtifactStore:
    """Adapter for an IPFS-like client exposing ``add_bytes`` and ``cat``."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def put(self, artifact: dict[str, Any]) -> str:
        assert_public(artifact)
        expected = cid_for(artifact)
        returned = self.client.add_bytes(canonical_json(artifact))
        actual = returned.get("Hash") if isinstance(returned, dict) else returned
        if actual != expected:
            raise OSError(f"artifact provider returned unexpected CID: {actual}")
        return expected

    def get(self, cid: str) -> dict[str, Any] | None:
        import json

        try:
            raw = self.client.cat(cid)
        except (KeyError, FileNotFoundError):
            return None
        value = json.loads(bytes(raw).decode("utf-8"))
        if cid_for(value) != cid:
            raise OSError("artifact CID does not match stored content")
        return value
