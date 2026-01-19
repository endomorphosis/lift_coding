"""OCR/vision abstraction layer.

Provides an interface for OCR providers with a safe stub implementation for CI/dev.
"""

import logging
import os
from typing import Protocol

logger = logging.getLogger(__name__)


class OCRProvider(Protocol):
    """Protocol for OCR providers."""

    def extract_text(self, image_data: bytes, content_type: str) -> str:
        """Extract text from image data.

        Args:
            image_data: Raw image data bytes
            content_type: MIME type of the image (e.g., image/jpeg, image/png)

        Returns:
            Extracted text from the image

        Raises:
            NotImplementedError: If OCR is not enabled/available
            ValueError: If image format is unsupported
        """
        ...


def get_ocr_provider() -> OCRProvider:
    """Get the configured OCR provider.

    Returns the appropriate OCR provider based on environment configuration:
    - If HANDSFREE_OCR_PROVIDER=stub or unset: returns StubOCRProvider
    - If HANDSFREE_OCR_ENABLED=false: returns disabled StubOCRProvider

    Returns:
        An OCRProvider instance

    Environment variables:
        HANDSFREE_OCR_PROVIDER: Provider type (default: "stub", options: "stub")
        HANDSFREE_OCR_ENABLED: Whether OCR is enabled (default: "true")
    """
    provider_type = os.environ.get("HANDSFREE_OCR_PROVIDER", "stub").lower()
    enabled = os.environ.get("HANDSFREE_OCR_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
    )

    if provider_type == "stub":
        from handsfree.ocr.stub_provider import StubOCRProvider

        return StubOCRProvider(enabled=enabled)
    else:
        # Unknown provider - fall back to stub
        logger.warning("Unknown OCR provider '%s', falling back to stub", provider_type)
        from handsfree.ocr.stub_provider import StubOCRProvider

        return StubOCRProvider(enabled=enabled)
