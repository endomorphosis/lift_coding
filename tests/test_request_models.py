from handsfree.models import (
    AgentTaskMediaAttachRequest,
    DevAudioUploadRequest,
    DevMediaUploadRequest,
)


def test_dev_audio_upload_request_resolves_primary_payload_and_format():
    request = DevAudioUploadRequest(data_base64="  abc123  ", format="WAV")

    assert request.resolved_data_base64() == "abc123"
    assert request.resolved_format() == "wav"


def test_dev_audio_upload_request_falls_back_to_alias_payload():
    request = DevAudioUploadRequest(audio_base64="  xyz789  ")

    assert request.resolved_data_base64() == "xyz789"
    assert request.resolved_format() == "m4a"


def test_dev_audio_upload_request_returns_none_for_missing_payload():
    request = DevAudioUploadRequest(data_base64=None, audio_base64=None)

    assert request.resolved_data_base64() is None


def test_dev_media_upload_request_normalizes_kind_and_format_defaults():
    request = DevMediaUploadRequest(media_kind="VIDEO", format=None)

    assert request.resolved_media_kind() == "video"
    assert request.resolved_format("video") == "mp4"


def test_dev_media_upload_request_resolves_stripped_payload():
    request = DevMediaUploadRequest(data_base64="  media  ")

    assert request.resolved_data_base64() == "media"


def test_agent_task_media_attach_request_resolves_uri_and_kind():
    request = AgentTaskMediaAttachRequest(uri="  file:///tmp/demo.jpg  ", media_kind="AUDIO")

    assert request.resolved_uri() == "file:///tmp/demo.jpg"
    assert request.resolved_media_kind() == "audio"


def test_agent_task_media_attach_request_resolves_none_for_empty_uri():
    request = AgentTaskMediaAttachRequest(uri="   ")

    assert request.resolved_uri() is None
