import {
  bindMobileOrbService,
  dispatchMobileOrbGlassesResponse,
  invokeMobileOrbService,
  publishMobileOrbGlassesEvent,
  registerMobileOrbEdgeCapabilities,
  revokeMobileOrbBinding,
  subscribeMobileOrbServiceUpdates,
} from '../api/client';

export function createMetaGlassesMobileOrbApiBackend() {
  return {
    registerEdgeCapabilities: registerMobileOrbEdgeCapabilities,
    publishGlassesEvent: publishMobileOrbGlassesEvent,
    bindService: bindMobileOrbService,
    invokeService: invokeMobileOrbService,
    subscribeServiceUpdates: subscribeMobileOrbServiceUpdates,
    dispatchGlassesResponse: dispatchMobileOrbGlassesResponse,
    revokeBinding: revokeMobileOrbBinding,
  };
}
