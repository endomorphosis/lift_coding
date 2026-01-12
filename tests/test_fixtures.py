"""Tests using transcript fixtures."""

from pathlib import Path

import pytest

from handsfree.commands.intent_parser import IntentParser


@pytest.fixture
def parser() -> IntentParser:
    """Create an intent parser instance."""
    return IntentParser()


@pytest.fixture
def fixtures_dir() -> Path:
    """Get the fixtures directory."""
    return Path(__file__).parent / "fixtures" / "transcripts"


class TestCleanTranscripts:
    """Test parser with clean transcript fixtures."""

    def test_inbox_list_fixtures(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test inbox.list with clean fixtures."""
        fixture_file = fixtures_dir / "clean" / "inbox_list.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "inbox.list", f"Failed to parse '{line}' as inbox.list"
                assert result.confidence >= 0.9

    def test_pr_summarize_fixtures(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test pr.summarize with clean fixtures."""
        fixture_file = fixtures_dir / "clean" / "pr_summarize.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "pr.summarize", f"Failed to parse '{line}' as pr.summarize"
                assert result.confidence >= 0.9

    def test_system_repeat_fixtures(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test system.repeat with clean fixtures."""
        fixture_file = fixtures_dir / "clean" / "system_repeat.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "system.repeat", f"Failed to parse '{line}' as system.repeat"
                assert result.confidence >= 0.9

    def test_system_confirm_fixtures(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test system.confirm with clean fixtures."""
        fixture_file = fixtures_dir / "clean" / "system_confirm.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "system.confirm", (
                    f"Failed to parse '{line}' as system.confirm"
                )
                assert result.confidence >= 0.9

    def test_system_cancel_fixtures(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test system.cancel with clean fixtures."""
        fixture_file = fixtures_dir / "clean" / "system_cancel.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "system.cancel", f"Failed to parse '{line}' as system.cancel"
                assert result.confidence >= 0.9

    def test_pr_request_review_fixtures(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test pr.request_review with clean fixtures."""
        fixture_file = fixtures_dir / "clean" / "pr_request_review.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "pr.request_review", (
                    f"Failed to parse '{line}' as pr.request_review"
                )
                assert result.confidence >= 0.9
                assert "reviewers" in result.entities

    def test_agent_delegate_fixtures(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test agent.delegate with clean fixtures."""
        fixture_file = fixtures_dir / "clean" / "agent_delegate.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "agent.delegate", (
                    f"Failed to parse '{line}' as agent.delegate"
                )
                assert result.confidence >= 0.9


class TestNoisyTranscripts:
    """Test parser with noisy transcript fixtures."""

    def test_inbox_list_noisy(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test inbox.list with noisy fixtures."""
        fixture_file = fixtures_dir / "noisy" / "inbox_list.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "inbox.list", f"Failed to parse noisy '{line}' as inbox.list"
                # Noisy transcripts may have slightly lower confidence
                assert result.confidence >= 0.8

    def test_pr_summarize_noisy(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test pr.summarize with noisy fixtures."""
        fixture_file = fixtures_dir / "noisy" / "pr_summarize.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "pr.summarize", (
                    f"Failed to parse noisy '{line}' as pr.summarize"
                )
                assert result.confidence >= 0.8

    def test_system_repeat_noisy(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test system.repeat with noisy fixtures."""
        fixture_file = fixtures_dir / "noisy" / "system_repeat.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "system.repeat", (
                    f"Failed to parse noisy '{line}' as system.repeat"
                )
                assert result.confidence >= 0.8

    def test_system_confirm_noisy(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test system.confirm with noisy fixtures."""
        fixture_file = fixtures_dir / "noisy" / "system_confirm.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "system.confirm", (
                    f"Failed to parse noisy '{line}' as system.confirm"
                )
                assert result.confidence >= 0.8

    def test_system_cancel_noisy(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test system.cancel with noisy fixtures."""
        fixture_file = fixtures_dir / "noisy" / "system_cancel.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "system.cancel", (
                    f"Failed to parse noisy '{line}' as system.cancel"
                )
                assert result.confidence >= 0.8


class TestNegativeTranscripts:
    """Test parser with negative examples (should not match)."""

    def test_unknown_transcripts(self, parser: IntentParser, fixtures_dir: Path) -> None:
        """Test that random phrases don't match known intents."""
        fixture_file = fixtures_dir / "negative" / "unknown.txt"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        for line in fixture_file.read_text().strip().split("\n"):
            if line.strip():
                result = parser.parse(line.strip())
                assert result.name == "unknown", f"Should not match known intent for '{line}'"
                assert result.confidence == 0.0


class TestDeterministicParsing:
    """Test that parsing is deterministic."""

    def test_same_input_same_output(self, parser: IntentParser) -> None:
        """Test that parsing the same input multiple times gives same result."""
        text = "summarize pr 123"

        results = [parser.parse(text) for _ in range(5)]

        # All results should be identical
        first = results[0]
        for result in results[1:]:
            assert result.name == first.name
            assert result.confidence == first.confidence
            assert result.entities == first.entities
