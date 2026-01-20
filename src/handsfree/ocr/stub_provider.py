"""Stub OCR provider that returns deterministic responses for testing.

This is the default implementation used in CI and dev environments.
It doesn't require any external dependencies or API keys.
"""


class StubOCRProvider:
    """Stub OCR provider that returns deterministic responses for testing.

    This is the default implementation used in CI and dev environments.
    It doesn't require any external dependencies or API keys.
    """

    def __init__(self, enabled: bool = True):
        """Initialize stub OCR provider.

        Args:
            enabled: Whether OCR is enabled. If False, raises NotImplementedError.
        """
        self.enabled = enabled

    def extract_text(self, image_data: bytes, content_type: str) -> str:
        """Return a deterministic text extraction for testing.

        Args:
            image_data: Raw image data bytes (currently unused)
            content_type: MIME type of the image (e.g., image/jpeg, image/png)

        Returns:
            Deterministic text for testing purposes

        Raises:
            NotImplementedError: If OCR is disabled
            ValueError: If content_type is unsupported
        """
        if not self.enabled:
            raise NotImplementedError(
                "Image OCR is disabled. Set HANDSFREE_OCR_ENABLED=true to enable."
            )

        # Validate content type
        supported_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
        if content_type and content_type.lower() not in supported_types:
            raise ValueError(
                f"Unsupported image format: {content_type}. "
                f"Supported formats: {', '.join(supported_types)}"
            )

        # Always return a known, parseable command for deterministic testing.
        # This ensures tests are stable and the output can be routed through
        # intent parsing successfully.
        return "show my inbox"
