#!/usr/bin/env python3
"""Smoke test script for HandsFree Dev Companion API demo.

This script validates that the server is running and common endpoints
are responding correctly. It uses fixture-first approach and doesn't
require external services by default.

Usage:
    # Start the server first
    python -m handsfree.server &
    
    # Run the smoke test
    python scripts/smoke_demo.py
    
    # Or specify a custom base URL
    python scripts/smoke_demo.py --base-url http://localhost:8080

Exit codes:
    0 - All checks passed
    1 - One or more checks failed
"""

import argparse
import sys
import time
from typing import Any

try:
    import requests
except ImportError:
    print("Error: requests library is required. Install with: pip install requests")
    sys.exit(1)


class SmokeTest:
    """Smoke test runner for HandsFree API."""

    def __init__(self, base_url: str, verbose: bool = False):
        """Initialize smoke test runner.

        Args:
            base_url: Base URL of the API server (e.g., http://localhost:8080)
            verbose: Whether to print verbose output
        """
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with appropriate formatting.

        Args:
            message: Message to log
            level: Log level (info, success, error, warning)
        """
        if level == "success":
            print(f"✓ {message}")
        elif level == "error":
            print(f"✗ {message}")
        elif level == "warning":
            print(f"⚠ {message}")
        elif level == "info" and self.verbose:
            print(f"ℹ {message}")

    def check_status_endpoint(self) -> bool:
        """Check /v1/status endpoint.

        Returns:
            True if check passed, False otherwise
        """
        self.log("Checking /v1/status endpoint...")
        try:
            response = requests.get(f"{self.base_url}/v1/status", timeout=10)

            if response.status_code != 200:
                self.log(
                    f"/v1/status returned {response.status_code}, expected 200",
                    "error",
                )
                return False

            data = response.json()

            # Validate required fields
            required_fields = ["status", "timestamp"]
            for field in required_fields:
                if field not in data:
                    self.log(f"/v1/status missing required field: {field}", "error")
                    return False

            # Validate status value
            if data["status"] not in ["ok", "degraded", "unavailable"]:
                self.log(
                    f"/v1/status has invalid status: {data['status']}", "error"
                )
                return False

            self.log(f"/v1/status check passed (status={data['status']})", "success")
            return True

        except requests.exceptions.ConnectionError:
            self.log(
                f"Connection error: Cannot connect to {self.base_url}. "
                "Is the server running?",
                "error",
            )
            return False
        except requests.exceptions.Timeout:
            self.log("/v1/status request timed out", "error")
            return False
        except requests.exceptions.RequestException as e:
            self.log(f"/v1/status request failed: {e}", "error")
            return False
        except (KeyError, ValueError, requests.exceptions.JSONDecodeError) as e:
            self.log(f"/v1/status response parsing failed: {e}", "error")
            return False

    def check_tts_endpoint(self) -> bool:
        """Check /v1/tts endpoint.

        Returns:
            True if check passed, False otherwise
        """
        self.log("Checking /v1/tts endpoint...")
        try:
            payload = {"text": "Demo smoke test", "format": "wav"}
            response = requests.post(
                f"{self.base_url}/v1/tts", json=payload, timeout=10
            )

            if response.status_code != 200:
                self.log(
                    f"/v1/tts returned {response.status_code}, expected 200", "error"
                )
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        self.log(f"Error details: {error_data}", "error")
                    except Exception:
                        pass
                return False

            # Validate content type
            content_type = response.headers.get("content-type", "")
            if "audio/wav" not in content_type:
                self.log(
                    f"/v1/tts returned unexpected content-type: {content_type}",
                    "error",
                )
                return False

            # Validate non-empty audio payload
            if len(response.content) == 0:
                self.log("/v1/tts returned empty audio content", "error")
                return False

            self.log(
                f"/v1/tts check passed (audio size={len(response.content)} bytes)",
                "success",
            )
            return True

        except requests.exceptions.ConnectionError:
            self.log(
                f"Connection error: Cannot connect to {self.base_url}. "
                "Is the server running?",
                "error",
            )
            return False
        except requests.exceptions.Timeout:
            self.log("/v1/tts request timed out", "error")
            return False
        except requests.exceptions.RequestException as e:
            self.log(f"/v1/tts request failed: {e}", "error")
            return False
        except (ValueError, requests.exceptions.JSONDecodeError) as e:
            self.log(f"/v1/tts check failed: {e}", "error")
            return False

    def check_command_endpoint(self) -> bool:
        """Check /v1/command endpoint with a short text prompt.

        Returns:
            True if check passed, False otherwise
        """
        self.log("Checking /v1/command endpoint...")
        try:
            payload = {
                "input": {"type": "text", "text": "inbox"},
                "profile": "default",
                "client_context": {
                    "device": "smoke_test",
                    "locale": "en-US",
                    "timezone": "UTC",
                    "app_version": "0.1.0",
                },
                "idempotency_key": f"smoke-test-{int(time.time())}",
            }

            response = requests.post(
                f"{self.base_url}/v1/command", json=payload, timeout=10
            )

            if response.status_code != 200:
                self.log(
                    f"/v1/command returned {response.status_code}, expected 200",
                    "error",
                )
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        self.log(f"Error details: {error_data}", "error")
                    except Exception:
                        pass
                return False

            data = response.json()

            # Validate required fields
            required_fields = ["status", "intent", "spoken_text"]
            for field in required_fields:
                if field not in data:
                    self.log(f"/v1/command missing required field: {field}", "error")
                    return False

            # Validate status value
            valid_statuses = ["ok", "needs_confirmation", "error"]
            if data["status"] not in valid_statuses:
                self.log(
                    f"/v1/command has invalid status: {data['status']}", "error"
                )
                return False

            self.log(
                f"/v1/command check passed (status={data['status']})", "success"
            )
            return True

        except requests.exceptions.ConnectionError:
            self.log(
                f"Connection error: Cannot connect to {self.base_url}. "
                "Is the server running?",
                "error",
            )
            return False
        except requests.exceptions.Timeout:
            self.log("/v1/command request timed out", "error")
            return False
        except requests.exceptions.RequestException as e:
            self.log(f"/v1/command request failed: {e}", "error")
            return False
        except (KeyError, ValueError, requests.exceptions.JSONDecodeError) as e:
            self.log(f"/v1/command response parsing failed: {e}", "error")
            return False

    def check_notifications_endpoint(self) -> bool:
        """Check /v1/notifications endpoint (non-fatal if no subscriptions).

        Returns:
            True if check passed or non-fatal warning, False otherwise
        """
        self.log("Checking /v1/notifications endpoint...")
        try:
            response = requests.get(f"{self.base_url}/v1/notifications", timeout=10)

            if response.status_code == 200:
                data = response.json()
                
                # Handle both array and object responses
                notification_count = 0
                if isinstance(data, list):
                    notification_count = len(data)
                elif isinstance(data, dict) and "notifications" in data:
                    notification_count = len(data.get("notifications", []))
                else:
                    self.log(
                        "/v1/notifications returned unexpected response format", "warning"
                    )
                    self.warnings += 1
                    return True  # Non-fatal

                self.log(
                    f"/v1/notifications check passed ({notification_count} notifications)",
                    "success",
                )
                return True

            elif response.status_code == 404:
                # Endpoint might not be available in all configurations
                self.log(
                    "/v1/notifications endpoint not found (OK for minimal demo)",
                    "warning",
                )
                self.warnings += 1
                return True  # Non-fatal

            else:
                self.log(
                    f"/v1/notifications returned {response.status_code} "
                    "(non-fatal, might not be configured)",
                    "warning",
                )
                self.warnings += 1
                return True  # Non-fatal

        except requests.exceptions.ConnectionError:
            self.log(
                f"Connection error: Cannot connect to {self.base_url}. "
                "Is the server running?",
                "error",
            )
            return False
        except requests.exceptions.Timeout:
            self.log("/v1/notifications request timed out (non-fatal)", "warning")
            self.warnings += 1
            return True  # Non-fatal
        except requests.exceptions.RequestException as e:
            self.log(f"/v1/notifications request failed (non-fatal): {e}", "warning")
            self.warnings += 1
            return True  # Non-fatal

    def run_all_checks(self) -> bool:
        """Run all smoke tests.

        Returns:
            True if all checks passed, False otherwise
        """
        print(f"Running smoke tests against {self.base_url}")
        print("=" * 60)

        checks = [
            ("Status endpoint", self.check_status_endpoint),
            ("TTS endpoint", self.check_tts_endpoint),
            ("Command endpoint", self.check_command_endpoint),
            ("Notifications endpoint", self.check_notifications_endpoint),
        ]

        for name, check_func in checks:
            if check_func():
                self.passed += 1
            else:
                self.failed += 1

        print("=" * 60)
        print(f"Results: {self.passed} passed, {self.failed} failed", end="")
        if self.warnings > 0:
            print(f", {self.warnings} warnings")
        else:
            print()

        if self.failed > 0:
            print("\n✗ Smoke tests FAILED")
            return False
        else:
            print("\n✓ All smoke tests PASSED")
            return True


def main() -> int:
    """Main entry point for smoke test script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Smoke test script for HandsFree Dev Companion API"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8080",
        help="Base URL of the API server (default: http://localhost:8080)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=0,
        help="Wait N seconds before starting tests (useful when starting server)",
    )

    args = parser.parse_args()

    if args.wait > 0:
        print(f"Waiting {args.wait} seconds for server to start...")
        time.sleep(args.wait)

    smoke_test = SmokeTest(args.base_url, verbose=args.verbose)
    success = smoke_test.run_all_checks()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
