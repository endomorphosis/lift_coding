import { createAckEnvelope, encodeEnvelopeBase64 } from '../peerEnvelope';
import { buildPeerBackendValidationResult, replayBackendAckFrame } from '../peerDiagnostics';

describe('peerDiagnostics', () => {
  it('decodes backend ack frames into envelopes', () => {
    const ackEnvelope = createAckEnvelope({
      peerId: '12D3KooWpeer',
      sessionId: 'session-1',
      ackedMessageId: 'message-123',
    });
    const result = buildPeerBackendValidationResult({
      accepted: true,
      peer_ref: 'peer://demo',
      peer_id: '12D3KooWpeer',
      kind: 'message',
      session_id: 'session-1',
      message_id: 'message-123',
      ack_frame_base64: encodeEnvelopeBase64(ackEnvelope),
    });

    expect(result.accepted).toBe(true);
    expect(result.ackEnvelope.kind).toBe('ack');
    expect(result.ackEnvelope.acked_message_id).toBe('message-123');
  });

  it('replays backend ack frames through the peer bridge when supported', async () => {
    const simulateFrameReceived = jest.fn().mockResolvedValue(undefined);
    const validationResult = {
      peer_id: '12D3KooWpeer',
      ack_frame_base64: 'ack-frame',
    };

    await expect(
      replayBackendAckFrame({ simulateFrameReceived }, 'peer://demo', validationResult)
    ).resolves.toBe(true);

    expect(simulateFrameReceived).toHaveBeenCalledWith(
      'peer://demo',
      'ack-frame',
      '12D3KooWpeer'
    );
  });

  it('returns false when replay prerequisites are missing', async () => {
    await expect(replayBackendAckFrame({}, 'peer://demo', {})).resolves.toBe(false);
    await expect(replayBackendAckFrame(null, 'peer://demo', null)).resolves.toBe(false);
  });
});
