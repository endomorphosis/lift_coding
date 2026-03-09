import {
  getOutboxMessageIdsByState,
  getSelectedOutboxPreview,
  normalizePeerChatOutboxSummary,
  selectNextOutboxMessageId,
} from '../peerChatOutbox';

describe('peerChatOutbox', () => {
  const response = {
    queued_total: 2,
    queued_urgent: 1,
    queued_normal: 1,
    deliverable_now: 1,
    held_now: 1,
    delivery_mode: 'long_retry',
    preview_messages: [
      {
        outbox_message_id: 'msg-1',
        state: 'leased',
        text: 'first',
      },
      {
        outbox_message_id: 'msg-2',
        state: 'held_by_policy',
        text: 'second',
      },
    ],
  };

  it('normalizes backend outbox responses into a stable shape', () => {
    expect(normalizePeerChatOutboxSummary(response)).toEqual(response);
    expect(normalizePeerChatOutboxSummary(null)).toBeNull();
  });

  it('retains the selected message when it still exists', () => {
    const summary = normalizePeerChatOutboxSummary(response);

    expect(selectNextOutboxMessageId(summary, 'msg-2')).toBe('msg-2');
  });

  it('falls back to the first preview message when the current selection is missing', () => {
    const summary = normalizePeerChatOutboxSummary(response);

    expect(selectNextOutboxMessageId(summary, 'missing')).toBe('msg-1');
    expect(selectNextOutboxMessageId(summary, null)).toBe('msg-1');
    expect(selectNextOutboxMessageId(normalizePeerChatOutboxSummary({}), 'missing')).toBeNull();
  });

  it('returns the selected preview row when present', () => {
    const summary = normalizePeerChatOutboxSummary(response);

    expect(getSelectedOutboxPreview(summary, 'msg-2')).toEqual(
      expect.objectContaining({ outbox_message_id: 'msg-2', state: 'held_by_policy' })
    );
    expect(getSelectedOutboxPreview(summary, 'missing')).toBeNull();
  });

  it('collects outbox message ids by state', () => {
    const summary = normalizePeerChatOutboxSummary(response);

    expect(getOutboxMessageIdsByState(summary, 'leased')).toEqual(['msg-1']);
    expect(getOutboxMessageIdsByState(summary, 'held_by_policy')).toEqual(['msg-2']);
    expect(getOutboxMessageIdsByState(summary, 'deliverable')).toEqual([]);
  });
});
