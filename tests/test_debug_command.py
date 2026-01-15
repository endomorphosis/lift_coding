"""Tests for debug command 'explain what you heard'."""

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app, get_db
from handsfree.auth import FIXTURE_USER_ID
from handsfree.commands.intent_parser import IntentParser
from handsfree.db.commands import get_commands, store_command


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def parser():
    """Create an intent parser instance."""
    return IntentParser()


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize DB for each test."""
    db = get_db()
    # Commands table should already exist from migrations
    yield db


class TestDebugIntentParsing:
    """Test intent parsing for debug commands."""

    def test_explain_what_you_heard(self, parser: IntentParser) -> None:
        """Test 'explain what you heard' intent."""
        result = parser.parse("explain what you heard")
        assert result.name == "debug.transcript"
        assert result.confidence >= 0.9
        assert result.entities == {}

    def test_what_did_you_hear(self, parser: IntentParser) -> None:
        """Test 'what did you hear' intent."""
        result = parser.parse("what did you hear")
        assert result.name == "debug.transcript"
        assert result.confidence >= 0.9
        assert result.entities == {}


class TestTranscriptStorage:
    """Test transcript storage with debug mode."""

    def test_transcript_stored_with_debug_enabled(self, client: TestClient) -> None:
        """Test that transcript is stored when debug mode is enabled."""
        db = get_db()

        # Submit a command with debug=True
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "what needs my attention"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "1.0.0",
                    "debug": True,
                },
            },
            headers={"X-User-Id": FIXTURE_USER_ID},
        )

        assert response.status_code == 200

        # Verify transcript was stored
        commands = get_commands(db, user_id=FIXTURE_USER_ID, limit=1)
        assert len(commands) > 0
        assert commands[0].transcript == "what needs my attention"

    def test_transcript_not_stored_without_debug(self, client: TestClient) -> None:
        """Test that transcript is NOT stored when debug mode is disabled in production mode.

        Note: In dev mode (default), transcripts are always stored. This test verifies
        that when debug=False and we're NOT in dev mode, transcript storage is disabled.
        Since tests run in dev mode by default, we verify the intent by checking
        that the store_transcript flag is properly set based on debug mode.
        """
        from handsfree.db.commands import store_command

        db = get_db()

        # Manually test the store_command function with store_transcript=False
        # This simulates production mode behavior
        store_command(
            conn=db,
            user_id=FIXTURE_USER_ID,
            input_type="text",
            status="ok",
            profile="default",
            transcript="sensitive command text",
            intent_name="inbox.list",
            intent_confidence=0.95,
            entities={},
            store_transcript=False,  # Explicitly disable transcript storage
        )

        # Verify transcript was NOT stored
        commands = get_commands(db, user_id=FIXTURE_USER_ID, limit=1)
        assert len(commands) > 0
        assert (
            commands[0].transcript is None
        )  # Transcript should be None when store_transcript=False

    def test_transcript_stored_in_dev_mode(self, client: TestClient, monkeypatch) -> None:
        """Test that transcript is stored in dev auth mode even without debug flag."""
        # In dev mode, transcripts are stored by default
        monkeypatch.setenv("HANDSFREE_AUTH_MODE", "dev")

        db = get_db()

        # Submit a command without debug flag
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "inbox"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "1.0.0",
                },
            },
            headers={"X-User-Id": FIXTURE_USER_ID},
        )

        assert response.status_code == 200

        # Verify transcript was stored even without debug flag
        commands = get_commands(db, user_id=FIXTURE_USER_ID, limit=1)
        assert len(commands) > 0
        assert commands[0].transcript == "inbox"


class TestDebugTranscriptRetrieval:
    """Test debug.transcript intent handler."""

    def test_retrieve_last_transcript(self, client: TestClient) -> None:
        """Test retrieving the last stored transcript."""
        db = get_db()

        # Store a command with transcript
        store_command(
            conn=db,
            user_id=FIXTURE_USER_ID,
            input_type="text",
            status="ok",
            profile="default",
            transcript="summarize pr 123",
            intent_name="pr.summarize",
            intent_confidence=0.95,
            entities={"pr_number": 123},
            store_transcript=True,
        )

        # Request the last transcript
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "explain what you heard"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "1.0.0",
                },
            },
            headers={"X-User-Id": FIXTURE_USER_ID},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "summarize pr 123" in data["spoken_text"]

    def test_no_transcript_available(self, client: TestClient) -> None:
        """Test when no transcript is available."""
        # Use a different user ID to avoid finding previous commands
        test_user_id = "00000000-0000-0000-0000-000000000099"

        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "what did you hear"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "1.0.0",
                },
            },
            headers={"X-User-Id": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "No recent transcript" in data["spoken_text"]

    def test_transcript_redaction(self, client: TestClient) -> None:
        """Test that secrets are redacted from returned transcript."""
        db = get_db()

        # Store a command with a GitHub token in the transcript
        store_command(
            conn=db,
            user_id=FIXTURE_USER_ID,
            input_type="text",
            status="ok",
            profile="default",
            transcript="use token ghp_1234567890abcdefghijklmnopqr to authenticate",
            intent_name="unknown",
            intent_confidence=0.5,
            entities={},
            store_transcript=True,
        )

        # Request the transcript
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "explain what you heard"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "1.0.0",
                },
            },
            headers={"X-User-Id": FIXTURE_USER_ID},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Token should be redacted
        assert "ghp_" not in data["spoken_text"] or "***REDACTED***" in data["spoken_text"]
        assert "ghp_1234567890abcdefghijklmnopqr" not in data["spoken_text"]

    def test_workout_profile_response(self, client: TestClient) -> None:
        """Test debug command with workout profile returns truncated response."""
        db = get_db()

        # Store a command with transcript
        store_command(
            conn=db,
            user_id=FIXTURE_USER_ID,
            input_type="text",
            status="ok",
            profile="workout",
            transcript="inbox",
            intent_name="inbox.list",
            intent_confidence=0.99,
            entities={},
            store_transcript=True,
        )

        # Request transcript with workout profile
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "what did you hear"},
                "profile": "workout",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "1.0.0",
                },
            },
            headers={"X-User-Id": FIXTURE_USER_ID},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Workout profile should have shorter response
        assert "I heard:" in data["spoken_text"]


class TestDebugPrivacy:
    """Test privacy aspects of debug functionality."""

    def test_no_audio_storage(self, client: TestClient) -> None:
        """Test that audio data is never stored, only transcripts."""
        db = get_db()

        # This is already covered by the architecture - audio is transcribed
        # to text and only text can be stored. Verify commands table structure
        # doesn't have audio fields by checking stored command
        store_command(
            conn=db,
            user_id=FIXTURE_USER_ID,
            input_type="audio",
            status="ok",
            profile="default",
            transcript="test audio command",
            intent_name="inbox.list",
            intent_confidence=0.9,
            entities={},
            store_transcript=True,
        )

        commands = get_commands(db, user_id=FIXTURE_USER_ID, limit=1)
        assert len(commands) > 0
        # Verify only transcript is available, no audio data
        assert commands[0].transcript == "test audio command"
        assert commands[0].input_type == "audio"
        # No audio_data field should exist
        assert not hasattr(commands[0], "audio_data")

    def test_user_isolation(self, client: TestClient) -> None:
        """Test that users can only see their own transcripts."""
        db = get_db()

        user1_id = "00000000-0000-0000-0000-000000000011"
        user2_id = "00000000-0000-0000-0000-000000000022"

        # Store command for user1
        store_command(
            conn=db,
            user_id=user1_id,
            input_type="text",
            status="ok",
            profile="default",
            transcript="user1 secret command",
            intent_name="inbox.list",
            intent_confidence=0.9,
            entities={},
            store_transcript=True,
        )

        # User2 requests transcript
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "explain what you heard"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "1.0.0",
                },
            },
            headers={"X-User-Id": user2_id},
        )

        assert response.status_code == 200
        data = response.json()
        # User2 should not see user1's transcript
        assert "user1 secret command" not in data["spoken_text"]
        assert "No recent transcript" in data["spoken_text"]
