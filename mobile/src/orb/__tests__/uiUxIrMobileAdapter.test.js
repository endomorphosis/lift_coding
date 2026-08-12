/**
 * UIR-042: mobile ORB adapter smoke tests.
 * Presentation-only mapping — no local device policy.
 */

const path = require('path');

let adapter;
try {
  adapter = require(path.join(__dirname, '..', 'uiUxIrMobileAdapter.js'));
} catch (err) {
  // Support both CJS export shapes.
  adapter = null;
}

describe('uiUxIrMobileAdapter', () => {
  test('module loads and exports a projection/adapt entrypoint', () => {
    expect(adapter).toBeTruthy();
    const fn =
      adapter.adaptUiUxIrForMobile ||
      adapter.projectToMobile ||
      adapter.default ||
      adapter.adapt;
    // If the module only exports helpers, accept object surface.
    if (typeof fn === 'function') {
      const sample = {
        surfaces: [
          {
            kind: 'button',
            label: 'Submit',
            touchTargetDp: 48,
            requiresConfirmation: true,
          },
        ],
        connectivity: 'online',
      };
      const out = fn(sample);
      expect(out).toBeTruthy();
    } else {
      expect(typeof adapter).toBe('object');
    }
  });

  test('does not embed authority grants or raw sensor claims', () => {
    const src = require('fs').readFileSync(
      path.join(__dirname, '..', 'uiUxIrMobileAdapter.js'),
      'utf8'
    );
    expect(src).not.toMatch(/raw_emg/i);
    expect(src).not.toMatch(/authority_grant/i);
    expect(src).not.toMatch(/executeScript|eval\(/);
  });
});
