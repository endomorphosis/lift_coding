import { decodeEnvelopeBase64 } from './peerEnvelope';

export function buildPeerBackendValidationResult(response) {
  if (!response || typeof response !== 'object') {
    throw new Error('Backend peer validation response is required');
  }

  let ackEnvelope = null;
  if (response.ack_frame_base64) {
    ackEnvelope = decodeEnvelopeBase64(response.ack_frame_base64);
  }

  return {
    ...response,
    ackEnvelope,
  };
}

export async function replayBackendAckFrame(peerBridge, peerRef, validationResult) {
  if (!peerBridge || typeof peerBridge.simulateFrameReceived !== 'function') {
    return false;
  }
  if (!peerRef || !validationResult?.ack_frame_base64) {
    return false;
  }

  await peerBridge.simulateFrameReceived(
    peerRef,
    validationResult.ack_frame_base64,
    validationResult.peer_id
  );
  return true;
}
