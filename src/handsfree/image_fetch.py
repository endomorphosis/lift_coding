"""Image fetching module with security controls for production URIs.

Supports:
- Local file:// URIs for development
- HTTPS pre-signed URLs with safety controls for production
"""

import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

# Default allowed content types for images
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/octet-stream",  # Some pre-signed URLs may use this
}


def _get_config():
    """Get configuration from environment variables.

    Returns:
        Tuple of (max_size_bytes, timeout_seconds, allowed_hosts, denied_hosts)
    """
    max_size = int(os.getenv("IMAGE_MAX_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10MB default
    timeout = int(os.getenv("IMAGE_FETCH_TIMEOUT_SECONDS", "30"))  # 30s default

    allowed_hosts_str = os.getenv("IMAGE_ALLOWED_HOSTS", "")
    allowed_hosts = [h.strip() for h in allowed_hosts_str.split(",") if h.strip()]

    denied_hosts_str = os.getenv("IMAGE_DENIED_HOSTS", "")
    denied_hosts = [h.strip() for h in denied_hosts_str.split(",") if h.strip()]

    return max_size, timeout, allowed_hosts, denied_hosts


def _is_host_allowed(
    hostname: str, allowed_hosts: list[str], denied_hosts: list[str]
) -> tuple[bool, str]:
    """Check if a hostname is allowed for image fetching.

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
            "Configure IMAGE_ALLOWED_HOSTS to allow this host.",
        )

    # No allowlist configured - default deny for production safety
    # This prevents SSRF attacks when the service is misconfigured
    return (
        False,
        f"Host '{hostname}' is not allowed. "
        "Configure IMAGE_ALLOWED_HOSTS to specify allowed hosts for image fetching.",
    )


def fetch_image_data(uri: str) -> bytes:
    """Fetch image data from URI with security controls.

    Supports:
    - file:// URIs and local paths for development
    - https:// URIs with host allowlist/denylist, size limits, and timeouts

    Args:
        uri: Image URI (file://, https://, or local path)

    Returns:
        Image data as bytes

    Raises:
        ValueError: If URI scheme is unsupported or host is not allowed
        FileNotFoundError: If local file doesn't exist
        httpx.HTTPError: If HTTP request fails
        RuntimeError: If image exceeds size limit or has invalid content-type
    """
    parsed = urlparse(uri)

    # Support file:// URIs and plain paths (dev/test mode)
    if parsed.scheme in ("", "file"):
        # Local file access is gated behind an explicit env flag to avoid
        # arbitrary file reads in production.
        allow_local = os.getenv("HANDSFREE_ALLOW_LOCAL_IMAGE_URIS", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if not allow_local:
            raise ValueError(
                "Local file image URIs are disabled. "
                "Set HANDSFREE_ALLOW_LOCAL_IMAGE_URIS=1 to enable for dev/test."
            )

        # Extract path from file:// URI or use as-is
        path = parsed.path if parsed.scheme == "file" else uri

        # Convert to Path object and read with size limit
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")

        # Apply the same max-size protection used for HTTPS downloads
        max_size, _, _, _ = _get_config()
        try:
            file_size = file_path.stat().st_size
        except OSError:
            # If we cannot stat the file, fall back to reading and checking size
            data = file_path.read_bytes()
            if len(data) > max_size:
                raise RuntimeError(
                    f"Local image size {len(data)} bytes exceeds maximum "
                    f"allowed size of {max_size} bytes"
                )
            return data

        if file_size > max_size:
            raise RuntimeError(
                f"Local image size {file_size} bytes exceeds maximum "
                f"allowed size of {max_size} bytes"
            )

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

        # Fetch image data with timeout and size limit
        # Note: This uses user-provided URI but with SSRF mitigations:
        # - Only HTTPS is allowed (not http, file, etc.)
        # - Host allowlist/denylist enforced above
        # - Timeout and size limits
        # - Content-type validation
        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("GET", uri) as response:
                    response.raise_for_status()

                    # Check content-length header if present
                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            content_length_int = int(content_length)
                            # Fail fast if declared size exceeds limit
                            if content_length_int > max_size:
                                raise RuntimeError(
                                    f"Image file too large: {content_length_int} bytes (max: {max_size} bytes)"
                                )
                        except ValueError:
                            # Invalid content-length header, continue without it
                            pass

                    # Check content-type if present
                    content_type = (
                        response.headers.get("content-type", "").lower().split(";")[0].strip()
                    )
                    if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                        raise RuntimeError(
                            f"Invalid image content-type: {content_type}. "
                            f"Expected one of: {', '.join(sorted(ALLOWED_IMAGE_CONTENT_TYPES))}"
                        )

                    # Read response in chunks and enforce size limit
                    chunks: list[bytes] = []
                    total_size = 0
                    for chunk in response.iter_bytes(chunk_size=8192):
                        total_size += len(chunk)
                        if total_size > max_size:
                            raise RuntimeError(
                                f"Image download exceeded size limit: {max_size} bytes"
                            )
                        chunks.append(chunk)

                    return b"".join(chunks)

        except httpx.TimeoutException as e:
            raise RuntimeError(f"Image fetch timeout after {timeout} seconds") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"HTTP error fetching image: {e.response.status_code} {e.response.reason_phrase}"
            ) from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Network error fetching image: {str(e)}") from e

    # Unsupported scheme
    else:
        raise ValueError(
            f"Unsupported image URI scheme: {parsed.scheme}. "
            f"Supported schemes: file:// (dev/test), https:// (production)"
        )
