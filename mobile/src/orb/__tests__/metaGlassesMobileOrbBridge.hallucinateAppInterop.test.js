import {
  DISPLAY_WIDGET_BRIDGE_OPERATIONS,
  MOBILE_ORB_BRIDGE_OPERATIONS,
  HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
  HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE,
  HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR,
} from '../metaGlassesOrbDescriptors';
import { MetaGlassesMobileOrbBridge } from '../metaGlassesMobileOrbBridge';

/**
 * VAIOS-G707 (`interface contract hallucinate_app mobile`): proves the mobile
 * ORB bridge can consume the normalized handoff envelope emitted by the
 * Hallucinate App desktop search surface
 * (`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
 * ::buildHallucinateAppMobileSearchHandoff) and complete a real
 * invoke_service -> dispatch_glasses_response runtime handoff.
 */
function buildHallucinateAppSearchHandoff(query, options = {}) {
  const filter = options.filter || {};
  const correlationId = options.correlation_id || 'hallucinate-app-mobile-search-test';
  return {
    contract_id: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.contract_id,
    source_surface: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.source_surface,
    target_surface: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.target_surface,
    route: '/v1/mobile/orb/invoke_service',
    operation: 'invoke_service',
    control_surface_contract_ref: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.control_surface_contract_ref,
    correlation_id: correlationId,
    issued_at: options.issued_at || '2026-07-08T00:00:00.000Z',
    payload: {
      intent: 'hallucinate_app.content_browser.search',
      query,
      filter,
      result_target: options.result_target || 'mobile_card',
    },
    normalized_intent: {
      intent: 'hallucinate_app.content_browser.search',
      method: 'invoke_service',
      target_ref: 'handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service',
      arguments: {
        query,
        filter,
        result_target: options.result_target || 'mobile_card',
      },
      confidence: 1.0,
    },
  };
}

describe('HALLUCINATE_APP_MOBILE_INTEROP descriptor', () => {
  it('advertises the interface contract hallucinate_app mobile shared with the desktop surface', () => {
    expect(HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.contract_id).toBe(
      'interface contract hallucinate_app mobile'
    );
    expect(HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.source_surface).toBe('hallucinate_app');
    expect(HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.target_surface).toBe('mobile');
    expect(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE.objective_goals).toEqual(['VAIOS-G707']);
    expect(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE.methods.map((m) => m.name)).toEqual([
      ...MOBILE_ORB_BRIDGE_OPERATIONS,
      ...DISPLAY_WIDGET_BRIDGE_OPERATIONS,
    ]);
    expect(HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR.runtime_handoff.source_surface).toBe(
      'hallucinate_app'
    );
    expect(HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR.runtime_handoff.target_surface).toBe('mobile');
    expect(HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR.validation.task_id).toBe('MGW-579');
    expect(HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR.validation.goal_id).toBe('VAIOS-G707');
    expect(HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR.validation.evidence).toBe(
      'objective validation repair'
    );
  });

  it('is advertised during edge capability registration', async () => {
    const backend = {
      registerEdgeCapabilities: jest.fn(async (payload) => ({
        edge_session_id: 'edge-session-1',
        accepted_interface_cids: payload.local_interface_cids,
        policy_cid: 'sha256:policy',
      })),
    };
    const bridge = new MetaGlassesMobileOrbBridge({ backend });
    await bridge.registerEdgeCapabilities({ capabilities: { session: true } });

    const [payload] = backend.registerEdgeCapabilities.mock.calls[0];
    const hallucinateAppDescriptor = payload.descriptors.find(
      (descriptor) => descriptor.interop_descriptor === HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR
    );
    expect(hallucinateAppDescriptor).toBeDefined();
    expect(hallucinateAppDescriptor.name).toBe(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE.name);
  });
});

describe('MetaGlassesMobileOrbBridge#handleHallucinateAppMobileSearchHandoff', () => {
  it('runs a real invoke_service -> dispatch_glasses_response handoff for a hallucinate_app search', async () => {
    const backend = {
      registerEdgeCapabilities: jest.fn(async () => ({
        edge_session_id: 'edge-session-1',
        accepted_interface_cids: ['sha256:mobile', 'sha256:display'],
        policy_cid: 'sha256:policy',
      })),
      invokeService: jest.fn(async (payload) => ({
        ok: true,
        service_result: {
          query: payload.arguments.query,
          results: [{ cid: 'bafy-result-1', title: 'Matching content' }],
        },
        output_refs: ['sha256:search-output'],
        provenance_refs: [],
        receipt_cid: 'sha256:invoke-receipt',
      })),
      dispatchGlassesResponse: jest.fn(async (payload) => ({
        dispatched_actions: [],
        display_widget_action: null,
        spoken_text: null,
        receipt_cid: 'sha256:dispatch-receipt',
        result: payload.result,
      })),
    };
    const bridge = new MetaGlassesMobileOrbBridge({ backend });
    await bridge.registerEdgeCapabilities({ capabilities: { session: true } });

    const handoff = buildHallucinateAppSearchHandoff('stable diffusion checkpoints', {
      correlation_id: 'hallucinate-app-mobile-search-1',
    });

    const result = await bridge.handleHallucinateAppMobileSearchHandoff(handoff);

    expect(backend.invokeService).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: 'invoke_service',
        arguments: expect.objectContaining({ query: 'stable diffusion checkpoints' }),
        correlation_id: 'hallucinate-app-mobile-search-1',
      })
    );
    expect(backend.dispatchGlassesResponse).toHaveBeenCalledWith(
      expect.objectContaining({
        render_targets: ['mobile_card'],
        correlation_id: 'hallucinate-app-mobile-search-1',
      })
    );
    expect(result.contract_id).toBe('interface contract hallucinate_app mobile');
    expect(result.invocation.response.receipt_cid).toBe('sha256:invoke-receipt');
    expect(result.dispatch.response.receipt_cid).toBe('sha256:dispatch-receipt');
  });

  it('rejects handoff envelopes carrying an unsupported contract id', async () => {
    const bridge = new MetaGlassesMobileOrbBridge({
      backend: {
        registerEdgeCapabilities: jest.fn(async () => ({
          edge_session_id: 'edge-session-1',
          accepted_interface_cids: [],
        })),
      },
    });
    await bridge.registerEdgeCapabilities({ capabilities: { session: true } });

    await expect(
      bridge.handleHallucinateAppMobileSearchHandoff({ contract_id: 'not-a-real-contract' })
    ).rejects.toThrow(/Unsupported hallucinate_app mobile handoff contract/);
  });

  it('requires an active edge session before handling a handoff', async () => {
    const bridge = new MetaGlassesMobileOrbBridge({
      backend: { registerEdgeCapabilities: jest.fn() },
    });

    await expect(
      bridge.handleHallucinateAppMobileSearchHandoff(buildHallucinateAppSearchHandoff('query'))
    ).rejects.toThrow(/edge session is not registered/);
  });
});
