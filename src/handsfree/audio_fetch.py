"""Audio fetching module with security controls for production URIs.

Supports:
- Local file:// URIs for development
- HTTPS pre-signed URLs with safety controls for production
"""

import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

# Default allowed content types for audio
ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mpeg",
    "audio/mp3",
    "audio/opus",
    "audio/ogg",
    "audio/webm",
    "application/octet-stream",  # Some pre-signed URLs may use this
}


def _get_config():
    """Get configuration from environment variables.

    Returns:
        Tuple of (max_size_bytes, timeout_seconds, allowed_hosts, denied_hosts)
    """
    max_size = int(os.getenv("AUDIO_MAX_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10MB default
    timeout = int(os.getenv("AUDIO_FETCH_TIMEOUT_SECONDS", "30"))  # 30s default

    allowed_hosts_str = os.getenv("AUDIO_ALLOWED_HOSTS", "")
    allowed_hosts = [h.strip() for h in allowed_hosts_str.split(",") if h.strip()]

    denied_hosts_str = os.getenv("AUDIO_DENIED_HOSTS", "")
    denied_hosts = [h.strip() for h in denied_hosts_str.split(",") if h.strip()]

    return max_size, timeout, allowed_hosts, denied_hosts


def _is_host_allowed(
    hostname: str, allowed_hosts: list[str], denied_hosts: list[str]
) -> tuple[bool, str]:
    """Check if a hostname is allowed for audio fetching.

    Args:
        hostname: The hostname to check
        allowed_hosts: List of allowed host patterns
        denied_hosts: List of denied host patterns

    Returns:
        Tuple of (is_allowed, reason_message)
    """
    # Check denylist first
    if denied_hosts:
        for denied_pattern in denied_hosts:
            if denied_pattern and (
                hostname == denied_pattern or hostname.endswith(f".{denied_pattern}")
            ):
                return False, f"Host '{hostname}' is denied by security policy"

    # If allowlist is configured, hostname must be in it
    if allowed_hosts:
        for allowed_pattern in allowed_hosts:
            if allowed_pattern and (
                hostname == allowed_pattern or hostname.endswith(f".{allowed_pattern}")
            ):
                return True, ""
        return (
            False,
            f"Host '{hostname}' is not in the allowed list. "
            "Configure AUDIO_ALLOWED_HOSTS to allow this host.",
        )

    # No allowlist configured - allow all (except denied)
    return True, ""


def fetch_audio_data(uri: str) -> bytes:
    """Fetch audio data from URI with security controls.

    Supports:
    - file:// URIs and local paths for development
    - https:// URIs with host allowlist/denylist, size limits, and timeouts

    Args:
        uri: Audio URI (file://, https://, or local path)

    Returns:
        Audio data as bytes

    Raises:
        ValueError: If URI scheme is unsupported or host is not allowed
        FileNotFoundError: If local file doesn't exist
        httpx.HTTPError: If HTTP request fails
        RuntimeError: If audio exceeds size limit or has invalid content-type
    """
    parsed = urlparse(uri)

    # Support file:// URIs and plain paths (dev/test mode)
    if parsed.scheme in ("", "file"):
        # Extract path from file:// URI or use as-is
        path = parsed.path if parsed.scheme == "file" else uri

        # Convert to Path object and read
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        return file_path.read_bytes()

    # Support https:// URIs (production mode)
    elif parsed.scheme == "https":
        # Get configuration
        max_size, timeout, allowed_hosts, denied_hosts = _get_config()

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid HTTPS URI: missing hostname")

        # Check if host is allowed
        is_allowed, reason = _is_host_allowed(hostname, allowed_hosts, denied_hosts)
        if not is_allowed:
            raise ValueError(reason)

        # Fetch audio data with timeout and size limit
        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("GET", uri) as response:
                    response.raise_for_status()

                    # Check content-length header if present. If it claims the body is too large,
                    # still stream with a hard byte limit (to cap memory) and then reject.
                    content_length = response.headers.get("content-length")
                    content_length_int: int | None = None
                    oversize_declared = False
                    if content_length:
                        try:
                            content_length_int = int(content_length)
                            if content_length_int > max_size:
                                oversize_declared = True
                        except ValueError:
                            # Ignore invalid content-length; enforce by streaming size limit.
                            content_length_int = None

                    # Check content-type if present
                    content_type = (
                        response.headers.get("content-type", "").lower().split(";")[0].strip()
                    )
                    if content_type and content_type not in ALLOWED_AUDIO_CONTENT_TYPES:
                        raise RuntimeError(
                            f"Invalid audio content-type: {content_type}. "
                            f"Expected one of: {', '.join(sorted(ALLOWED_AUDIO_CONTENT_TYPES))}"
                        )

                    # Read response in chunks and enforce size limit
                    chunks: list[bytes] = []
                    total_size = 0
                    for chunk in response.iter_bytes(chunk_size=8192):
                        total_size += len(chunk)
                        if total_size > max_size:
                            raise RuntimeError(
                                f"Audio download exceeded size limit: {max_size} bytes"
                            )
                        chunks.append(chunk)

                    # If the declared content-length was too large but we didn't exceed the cap
                    # while streaming (e.g., mock/lying header), still reject.
                    if oversize_declared:
                        declared = (
                            content_length_int if content_length_int is not None else content_length
                        )
                        raise RuntimeError(
                            f"Audio file too large: {declared} bytes (max: {max_size} bytes)"
                        )

                    return b"".join(chunks)

        except httpx.TimeoutException as e:
            raise RuntimeError(f"Audio fetch timeout after {timeout} seconds") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"HTTP error fetching audio: {e.response.status_code} {e.response.reason_phrase}"
            ) from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Network error fetching audio: {str(e)}") from e

    # Unsupported scheme
    else:
        raise ValueError(
            f"Unsupported audio URI scheme: {parsed.scheme}. "
            f"Supported schemes: file:// (dev/test), https:// (production)"
        )
