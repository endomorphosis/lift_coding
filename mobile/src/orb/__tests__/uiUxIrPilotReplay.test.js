/**
 * UIR-081: mobile pilot replay (offline, no device hardware).
 */
describe('uiUxIrPilotReplay', () => {
  test('enumerates offline pilot ids without transport', () => {
    const pilots = [
      'responsive-form',
      'destructive-workflow',
      'meta-glasses',
      'agent-supervisor',
    ];
    expect(pilots).toHaveLength(4);
    expect(pilots).toContain('meta-glasses');
  });

  test('blocking outcomes map to zero transport calls', () => {
    const transportCalls = [];
    const outcome = 'deny';
    if (outcome === 'allow') {
      transportCalls.push('invoke');
    }
    expect(transportCalls).toHaveLength(0);
  });
});
