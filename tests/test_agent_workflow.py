"""End-to-end workflow test for agent orchestration."""

from fastapi.testclient import TestClient

from handsfree.api import app

client = TestClient(app)


def test_agent_workflow_complete():
    """Test complete agent workflow: delegate, check status, verify persistence."""
    # Step 1: Delegate a task to agent
    # Note: "ask agent to..." defaults to copilot provider (not mock)
    delegate_response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "ask agent to fix issue 500"},
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert delegate_response.status_code == 200
    delegate_data = delegate_response.json()

    # Verify delegation response
    assert delegate_data["status"] == "ok"
    assert delegate_data["intent"]["name"] == "agent.delegate"
    assert "delegated" in delegate_data["spoken_text"].lower()

    # Extract task ID from response
    task_id = delegate_data["intent"]["entities"]["task_id"]
    assert task_id is not None

    # Verify task details in cards
    assert len(delegate_data["cards"]) > 0
    task_card = delegate_data["cards"][0]
    assert "Agent Task Created" in task_card["title"]
    assert task_id[:8] in task_card["subtitle"]
    # Verify provider is copilot (new default behavior)
    assert "Provider: copilot" in task_card["lines"][0]

    # Step 2: Query agent status immediately
    status_response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "agent status"},
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert status_response.status_code == 200
    status_data = status_response.json()

    # Verify status response
    assert status_data["status"] == "ok"
    assert status_data["intent"]["name"] == "agent.status"  # Router uses agent.status
    assert "task" in status_data["spoken_text"].lower()
    # Copilot provider doesn't auto-advance - tasks stay in "created" state
    # until real orchestration is implemented
    assert "created" in status_data["spoken_text"].lower()

    # Should show the newly created task
    assert len(status_data["cards"]) > 0

    # Find our task in the cards
    our_task_found = False
    for card in status_data["cards"]:
        if task_id[:8] in card["title"]:
            our_task_found = True
            # Verify task details - copilot provider tasks stay in "created" state
            assert "created" in card["subtitle"].lower()
            assert "Instruction: fix" in card["lines"][0]
            break

    assert our_task_found, "Created task not found in agent status"

    # Step 3: Delegate another task
    delegate_response2 = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "ask agent to handle PR 200"},
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert delegate_response2.status_code == 200
    delegate_data2 = delegate_response2.json()
    assert delegate_data2["status"] == "ok"

    # Step 4: Query status again - should show both tasks
    status_response2 = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "agent status"},
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert status_response2.status_code == 200
    status_data2 = status_response2.json()

    # Should show multiple tasks
    assert status_data2["intent"]["entities"]["task_count"] >= 2


def test_agent_workflow_various_commands():
    """Test that agent intents are correctly identified from various phrasings."""
    test_cases = [
        ("ask agent to fix issue 123", "agent.delegate", 123, None),
        ("tell agent to handle PR 456", "agent.delegate", None, 456),
        ("ask agent to add tests", "agent.delegate", None, None),
        ("agent status", "agent.status", None, None),
        ("summarize agent progress", "agent.status", None, None),
        ("ask agent to fix the bug on issue 789", "agent.delegate", 789, None),
    ]

    for text, expected_intent, expected_issue, expected_pr in test_cases:
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": text},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["intent"]["name"] == expected_intent

        if expected_intent == "agent.delegate":
            entities = data["intent"]["entities"]
            if expected_issue:
                assert entities["issue_number"] == expected_issue
            if expected_pr:
                assert entities["pr_number"] == expected_pr
