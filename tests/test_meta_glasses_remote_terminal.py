"""Tests for Meta glasses remote terminal endpoint routing."""

from handsfree.meta_glasses_remote_terminal import (
    REMOTE_TERMINAL_CONTRACT_ID,
    build_meta_glasses_remote_terminal_route,
    get_meta_glasses_remote_terminal_endpoint,
    list_meta_glasses_remote_terminal_endpoints,
    route_audio_endpoint,
    route_display_endpoint,
)


def test_remote_terminal_contract_lists_audio_and_display_endpoints() -> None:
    endpoints = {
        endpoint.endpoint_id: endpoint
        for endpoint in list_meta_glasses_remote_terminal_endpoints()
    }

    assert set(endpoints) == {
        "meta_glasses_audio_input",
        "meta_glasses_audio_output",
        "meta_glasses_display_widget",
    }
    assert endpoints["meta_glasses_audio_input"].channel == "audio"
    assert endpoints["meta_glasses_audio_input"].direction == "input"
    assert endpoints["meta_glasses_audio_output"].fallback_target == "phone_speaker"
    assert endpoints["meta_glasses_display_widget"].channel == "display"
    assert endpoints["meta_glasses_display_widget"].fallback_target == (
        "display_webapp_or_mobile_card"
    )


def test_remote_terminal_route_manifest_filters_requested_targets() -> None:
    default_route = build_meta_glasses_remote_terminal_route()
    route = build_meta_glasses_remote_terminal_route(
        payload={"task_id": "VAI-008"},
        render_targets=("audio", "display_widget_rendering"),
    )

    assert [endpoint["endpoint_id"] for endpoint in default_route["endpoints"]] == [
        "meta_glasses_audio_input",
        "meta_glasses_audio_output",
        "meta_glasses_display_widget",
    ]
    assert route["contract_id"] == REMOTE_TERMINAL_CONTRACT_ID
    assert route["surface_id"] == "mobile_glasses"
    assert route["payload"] == {"task_id": "VAI-008"}
    assert [endpoint["endpoint_id"] for endpoint in route["endpoints"]] == [
        "meta_glasses_audio_input",
        "meta_glasses_audio_output",
        "meta_glasses_display_widget",
    ]


def test_remote_terminal_audio_and_display_route_helpers_are_separate() -> None:
    audio_route = route_audio_endpoint({"spoken_text": "Task ready."})
    display_route = route_display_endpoint({"widget_id": "task-progress"})

    assert [endpoint["channel"] for endpoint in audio_route["endpoints"]] == [
        "audio",
        "audio",
    ]
    assert [endpoint["endpoint_id"] for endpoint in display_route["endpoints"]] == [
        "meta_glasses_display_widget"
    ]
    assert get_meta_glasses_remote_terminal_endpoint(
        "meta_glasses_display_widget"
    ).role == "display_widget_rendering"
